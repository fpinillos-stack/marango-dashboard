"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — NARRATIVE SENTIMENT
═══════════════════════════════════════════════════════════════
Composite sentiment score (-100 .. +100) from EODHD data.
Inspired by Ingenio's "Narrative Sentiment" panel.

Components (weighted):
  · Analyst Recommendations (40%) — from AnalystRatings
  · Earnings Surprise       (30%) — beat/miss vs estimate
  · Price Momentum          (30%) — vs 50/200-day moving avgs
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timedelta

import requests

EODHD_BASE = "https://eodhd.com/api"


def _f(v):
    if v in (None, "NA", "", "null", "None"):
        return None
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def _eodhd_key():
    try:
        import streamlit as st
        k = st.secrets.get("EODHD_API_KEY", "")
    except Exception:
        k = ""
    return k or os.environ.get("EODHD_API_KEY", "")


def _years(period_dict, n=8):
    if not isinstance(period_dict, dict):
        return []
    items = [(k, v) for k, v in period_dict.items() if isinstance(v, dict)]
    items.sort(key=lambda x: x[0], reverse=True)
    return items[:n]


# ───────────────────────────────────────────────────────────────
# COMPONENT SCORES (each returns -100..+100)
# ───────────────────────────────────────────────────────────────

def _analyst_score(fund: dict):
    """From EODHD AnalystRatings block → -100..+100 + detail."""
    ar = fund.get("AnalystRatings") or {}
    sb = _f(ar.get("StrongBuy")) or 0
    b = _f(ar.get("Buy")) or 0
    h = _f(ar.get("Hold")) or 0
    s = _f(ar.get("Sell")) or 0
    ss = _f(ar.get("StrongSell")) or 0
    total = sb + b + h + s + ss
    if total <= 0:
        rating = _f(ar.get("Rating"))
        if rating is not None:
            # EODHD Rating: 1 (strong buy) .. 5 (strong sell)
            score = (3 - rating) / 2 * 100
            return max(-100, min(100, score)), "Consensus rating {:.1f}/5".format(rating), 0
        return 0.0, "no analyst coverage", 0
    # weighted: StrongBuy +100, Buy +50, Hold 0, Sell -50, StrongSell -100
    score = (sb * 100 + b * 50 + h * 0 + s * -50 + ss * -100) / total
    detail = "{:.0f} analysts — {:.0f} buy / {:.0f} hold / {:.0f} sell".format(
        total, sb + b, h, s + ss)
    return max(-100, min(100, score)), detail, int(total)


def _earnings_surprise_score(fund: dict):
    """Average EPS beat/miss over last 4 quarters → -100..+100 + detail."""
    eh = (fund.get("Earnings") or {}).get("History") or {}
    rows = _years(eh, 4)
    surprises = []
    for _, r in rows:
        act = _f(r.get("epsActual"))
        est = _f(r.get("epsEstimate"))
        if act is not None and est is not None and est != 0:
            surprises.append((act - est) / abs(est))
    if not surprises:
        return 0.0, "no earnings-surprise data", 0
    avg = sum(surprises) / len(surprises)
    # +20% avg beat → +100 ; flat → 0 ; -20% miss → -100
    score = max(-100, min(100, avg * 500))
    detail = "Avg surprise {:+.1f}% over {} quarters".format(avg * 100, len(surprises))
    return score, detail, len(surprises)


def _momentum_score(eod: list):
    """Price vs 50/200-day MA from EOD bars → -100..+100 + detail."""
    if not eod or len(eod) < 60:
        return 0.0, "insufficient price history", None
    closes = []
    for b in eod:
        c = _f(b.get("adjusted_close") or b.get("close"))
        if c is not None:
            closes.append(c)
    if len(closes) < 60:
        return 0.0, "insufficient price history", None
    price = closes[-1]
    ma50 = sum(closes[-50:]) / 50
    ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else sum(closes) / len(closes)
    above50 = (price / ma50 - 1) if ma50 else 0
    above200 = (price / ma200 - 1) if ma200 else 0
    # blend: +20% above 200MA → ~+100
    score = max(-100, min(100, (above50 * 1.5 + above200 * 2.5) * 100))
    detail = "Price {:+.1f}% vs 50MA, {:+.1f}% vs 200MA".format(
        above50 * 100, above200 * 100)
    return score, detail, price


# ───────────────────────────────────────────────────────────────
# PUBLIC
# ───────────────────────────────────────────────────────────────

def compute_sentiment(fund: dict, eod: list = None) -> dict:
    """
    Composite narrative-sentiment score.
    `fund` = EODHD fundamentals payload (has AnalystRatings + Earnings).
    `eod`  = optional list of EOD bars for price momentum.
    Returns {ok, score (-100..+100), label, color, components}.
    """
    if not isinstance(fund, dict) or "_error" in fund:
        return {"ok": False, "error": (fund or {}).get("_error", "no data")}

    a_score, a_detail, a_n = _analyst_score(fund)
    e_score, e_detail, e_n = _earnings_surprise_score(fund)
    m_score, m_detail, m_price = _momentum_score(eod or [])

    # Re-weight: drop momentum weight onto the others if no price data
    if eod:
        w_a, w_e, w_m = 0.40, 0.30, 0.30
    else:
        w_a, w_e, w_m = 0.57, 0.43, 0.0

    composite = a_score * w_a + e_score * w_e + m_score * w_m

    comp = {
        "Analyst Recommendations": (round(a_score, 1), w_a, a_detail, a_n),
        "Earnings Surprise": (round(e_score, 1), w_e, e_detail, e_n),
        "Price Momentum": (round(m_score, 1), w_m, m_detail, m_price),
    }

    if composite >= 30:
        label, color = "BULLISH", "#10b981"
    elif composite >= 10:
        label, color = "IMPROVING", "#06b6d4"
    elif composite > -10:
        label, color = "NEUTRAL", "#9ca3af"
    elif composite > -30:
        label, color = "WEAKENING", "#f59e0b"
    else:
        label, color = "BEARISH", "#ef4444"

    return {"ok": True, "score": round(composite, 1), "label": label,
            "color": color, "components": comp}


def fetch_eod(ticker: str, days: int = 400) -> list:
    """Fetch recent EOD bars for momentum (used only in single-ticker deep dive)."""
    key = _eodhd_key()
    if not key:
        return []
    from_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        r = requests.get(EODHD_BASE + "/eod/" + ticker,
                         params={"api_token": key, "fmt": "json", "from": from_date},
                         timeout=20)
        r.raise_for_status()
        d = r.json()
        return d if isinstance(d, list) else []
    except Exception:
        return []
