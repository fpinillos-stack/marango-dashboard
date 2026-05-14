"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — RETURN ATTRIBUTION MODULE
═══════════════════════════════════════════════════════════════
Decomposes total return into:
  · EPS growth contribution
  · P/E (multiple) expansion contribution
  · Dividend contribution
  · Residual (currency, splits, rounding)

Inspired by AlphaMarketTools' /companies/[ticker] return decomposition.
"""
from __future__ import annotations

import os
import math
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests


EODHD_BASE = "https://eodhd.com/api"


# ============================================
# EODHD CLIENT
# ============================================

def _eodhd_key() -> str:
    try:
        k = st.secrets.get("EODHD_API_KEY", "")
    except Exception:
        k = ""
    return k or os.environ.get("EODHD_API_KEY", "")


def _norm(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    if "." not in t:
        t = f"{t}.US"
    return t


@st.cache_data(ttl=3600, show_spinner=False)
def eodhd_fundamentals_attr(ticker: str) -> dict:
    """Fundamentals (full payload — we want Earnings.History and General)."""
    key = _eodhd_key()
    if not key:
        return {"_error": "no_api_key"}
    t = _norm(ticker)
    url = f"{EODHD_BASE}/fundamentals/{t}"
    try:
        r = requests.get(url, params={"api_token": key}, timeout=20)
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:200]}"}


@st.cache_data(ttl=3600, show_spinner=False)
def eodhd_eod(ticker: str, from_date: str, to_date: str) -> list:
    """End-of-day OHLC. Returns list of dicts with date/close/adjusted_close."""
    key = _eodhd_key()
    if not key:
        return []
    t = _norm(ticker)
    url = f"{EODHD_BASE}/eod/{t}"
    try:
        r = requests.get(
            url,
            params={"api_token": key, "fmt": "json",
                    "from": from_date, "to": to_date},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def eodhd_dividends(ticker: str, from_date: str, to_date: str) -> list:
    """Dividend history."""
    key = _eodhd_key()
    if not key:
        return []
    t = _norm(ticker)
    url = f"{EODHD_BASE}/div/{t}"
    try:
        r = requests.get(
            url,
            params={"api_token": key, "fmt": "json",
                    "from": from_date, "to": to_date},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ============================================
# CORE MATH
# ============================================

def _ttm_eps_as_of(earnings_history: dict, as_of: datetime) -> float | None:
    """
    Given EODHD's Earnings.History dict (keyed by report date YYYY-MM-DD),
    return the trailing-12-month EPS using the 4 most recent quarters
    whose reportDate is <= as_of.
    """
    if not isinstance(earnings_history, dict):
        return None
    rows = []
    for k, v in earnings_history.items():
        if not isinstance(v, dict):
            continue
        rd = v.get("reportDate") or v.get("date") or k
        try:
            rd_dt = datetime.strptime(rd, "%Y-%m-%d")
        except Exception:
            continue
        eps = v.get("epsActual")
        if eps in (None, "NA", "", "null"):
            continue
        try:
            eps = float(eps)
        except Exception:
            continue
        if rd_dt <= as_of:
            rows.append((rd_dt, eps))
    if len(rows) < 4:
        return None
    rows.sort(key=lambda x: x[0], reverse=True)
    last4 = rows[:4]
    return sum(e for _, e in last4)


def _bar_at(eod: list, target: datetime, prefer: str = "after") -> dict | None:
    """Return EOD bar nearest target. prefer='after' => first bar >= target;
    prefer='before' => last bar <= target."""
    if not eod:
        return None
    bars = []
    for b in eod:
        d = b.get("date")
        if not d:
            continue
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            continue
        bars.append((dt, b))
    if not bars:
        return None
    bars.sort(key=lambda x: x[0])
    if prefer == "after":
        for dt, b in bars:
            if dt >= target:
                return b
        return bars[-1][1]
    else:
        result = None
        for dt, b in bars:
            if dt <= target:
                result = b
            else:
                break
        return result or bars[0][1]


def return_attribution(ticker: str, years: float):
    """
    Compute the return attribution for `ticker` over the last `years` years.

    Decomposition (annualised):
        TotalReturn ≈ EPSgrowth + MultipleExpansion + Dividends + Residual

    Returns dict with keys:
        ok, error, name, currency, years,
        date_0, date_1, price_0, price_1, eps_0, eps_1, pe_0, pe_1,
        ann_total, ann_eps, ann_pe, ann_div, ann_residual
    """
    out = {"ok": False, "error": None}
    fund = eodhd_fundamentals_attr(ticker)
    if "_error" in fund:
        out["error"] = f"Fundamentals: {fund['_error']}"
        return out

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=int(round(365.25 * years)))

    # Pull a wider EOD window so we can find the closest bar
    eod = eodhd_eod(
        ticker,
        (start_dt - timedelta(days=10)).strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
    )
    if not eod:
        out["error"] = "No EOD data returned."
        return out

    bar0 = _bar_at(eod, start_dt, prefer="after")
    bar1 = _bar_at(eod, end_dt, prefer="before")
    if not bar0 or not bar1:
        out["error"] = "Could not anchor bars on requested dates."
        return out

    try:
        close_0 = float(bar0.get("close"))
        close_1 = float(bar1.get("close"))
        adj_0 = float(bar0.get("adjusted_close") or bar0.get("close"))
        adj_1 = float(bar1.get("adjusted_close") or bar1.get("close"))
        date_0 = bar0.get("date")
        date_1 = bar1.get("date")
    except Exception as e:
        out["error"] = f"Bar parsing: {e}"
        return out

    eh = (fund.get("Earnings") or {}).get("History") or {}
    eps_0 = _ttm_eps_as_of(eh, datetime.strptime(date_0, "%Y-%m-%d"))
    eps_1 = _ttm_eps_as_of(eh, datetime.strptime(date_1, "%Y-%m-%d"))

    if eps_0 is None or eps_1 is None or eps_0 <= 0 or eps_1 <= 0:
        out["error"] = (f"Insufficient or non-positive TTM EPS: "
                        f"start={eps_0}, end={eps_1}. "
                        "Attribution requires positive earnings at both endpoints.")
        return out

    pe_0 = close_0 / eps_0
    pe_1 = close_1 / eps_1

    # Annualised contributions (geometric)
    n = max(years, 0.01)

    def _ann(ratio):
        if ratio <= 0:
            return None
        return ratio ** (1.0 / n) - 1.0

    ann_total = _ann(adj_1 / adj_0)               # total return w/ divs reinvested
    ann_price = _ann(close_1 / close_0)           # price-only (raw close)
    ann_eps = _ann(eps_1 / eps_0)
    ann_pe = _ann(pe_1 / pe_0)

    # Dividend contribution = total - price (annualised)
    ann_div = (ann_total - ann_price) if (ann_total is not None and ann_price is not None) else 0.0

    # Residual = total - EPS - PE - Divs
    parts = [ann_eps or 0, ann_pe or 0, ann_div or 0]
    ann_residual = (ann_total or 0) - sum(parts)

    out.update({
        "ok": True,
        "name": (fund.get("General") or {}).get("Name", ticker),
        "currency": (fund.get("General") or {}).get("CurrencyCode", "USD"),
        "years": years,
        "date_0": date_0,
        "date_1": date_1,
        "price_0": close_0,
        "price_1": close_1,
        "eps_0": eps_0,
        "eps_1": eps_1,
        "pe_0": pe_0,
        "pe_1": pe_1,
        "ann_total": ann_total,
        "ann_eps": ann_eps,
        "ann_pe": ann_pe,
        "ann_div": ann_div,
        "ann_residual": ann_residual,
    })
    return out


# ============================================
# UI
# ============================================

def _pct(x):
    return f"{x*100:+.2f}%" if x is not None else "—"


def _waterfall_chart(ann_eps, ann_pe, ann_div, ann_residual, ann_total):
    """Plotly waterfall showing the additive decomposition."""
    labels = ["EPS growth", "P/E expansion", "Dividends", "Residual", "Total"]
    measures = ["relative", "relative", "relative", "relative", "total"]
    values = [
        (ann_eps or 0) * 100,
        (ann_pe or 0) * 100,
        (ann_div or 0) * 100,
        (ann_residual or 0) * 100,
        0,
    ]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        text=[f"{v:+.2f}%" for v in values[:-1]] + [f"{(ann_total or 0)*100:+.2f}%"],
        textposition="outside",
        connector={"line": {"color": "rgba(15,23,42,0.13)"}},
        increasing={"marker": {"color": "#059669"}},
        decreasing={"marker": {"color": "#dc2626"}},
        totals={"marker": {"color": "#ea580c"}},
    ))
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="JetBrains Mono, monospace", color="#1e293b", size=11),
        yaxis=dict(title="Annualised %", gridcolor="rgba(15,23,42,0.07)",
                   zeroline=True, zerolinecolor="rgba(15,23,42,0.16)"),
        xaxis=dict(showgrid=False),
        showlegend=False,
    )
    return fig


def display_attribution_tab():
    """Return Attribution tab — decompose TR into EPS · P/E · Dividends · Residual."""
    st.markdown("""
    <div style="margin: 1rem 0 1.5rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #ea580c;
                    font-size: 1.5rem; font-weight: 700; letter-spacing: 0.05em;">
            RETURN ATTRIBUTION
        </div>
        <div style="color: #64748b; font-size: 0.85rem; letter-spacing: 0.05em;
                    text-transform: uppercase;">
            EPS growth · Multiple expansion · Dividends · Residual — Powered by EODHD
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not _eodhd_key():
        st.warning("EODHD_API_KEY not configured.")
        st.code('EODHD_API_KEY = "your_eodhd_token_here"', language="toml")
        return

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker = st.text_input(
            "Ticker", value="AAPL", key="attr_ticker",
            help=".US suffix is auto-applied to US tickers.",
        ).upper().strip()
    with col2:
        horizons_pick = st.multiselect(
            "Horizons",
            ["1y", "3y", "5y", "10y"],
            default=["1y", "3y", "5y"],
            key="attr_horizons",
        )
    with col3:
        st.write("")
        st.write("")
        st.button("RUN", use_container_width=True, type="primary", key="attr_run")

    if not ticker or not horizons_pick:
        st.info("Enter a ticker and pick at least one horizon.")
        return

    horizon_map = {"1y": 1.0, "3y": 3.0, "5y": 5.0, "10y": 10.0}
    horizons = [horizon_map[h] for h in horizons_pick]

    results = {}
    with st.spinner(f"Fetching {ticker} from EODHD…"):
        for label, yrs in zip(horizons_pick, horizons):
            results[label] = return_attribution(ticker, yrs)

    # If all failed, show first error
    if not any(r.get("ok") for r in results.values()):
        first = next(iter(results.values()))
        st.error(first.get("error") or "Attribution failed.")
        return

    # Header card with ticker info from first successful
    first_ok = next((r for r in results.values() if r.get("ok")), None)
    if first_ok:
        st.markdown(f"""
        <div style="margin: 0.5rem 0 1rem 0;">
            <div style="font-family: 'JetBrains Mono', monospace; color: #1e293b;
                        font-size: 1.1rem; font-weight: 600;">{first_ok['name']}</div>
            <div style="color: #64748b; font-size: 0.8rem;">
                Currency: {first_ok['currency']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Per-horizon decomposition
    for label in horizons_pick:
        r = results[label]
        with st.expander(f"  {label.upper()} HORIZON  —  "
                         f"{'OK' if r.get('ok') else 'FAILED'}",
                         expanded=(label == horizons_pick[0])):
            if not r.get("ok"):
                st.error(r.get("error") or "unknown error")
                continue

            cA, cB, cC, cD, cE = st.columns(5)
            cA.metric("Total Return (ann)", _pct(r["ann_total"]))
            cB.metric("EPS growth", _pct(r["ann_eps"]))
            cC.metric("P/E expansion", _pct(r["ann_pe"]))
            cD.metric("Dividends", _pct(r["ann_div"]))
            cE.metric("Residual", _pct(r["ann_residual"]))

            st.plotly_chart(
                _waterfall_chart(r["ann_eps"], r["ann_pe"],
                                 r["ann_div"], r["ann_residual"],
                                 r["ann_total"]),
                use_container_width=True,
            )

            st.caption(
                f"From {r['date_0']} (price {r['price_0']:.2f}, "
                f"EPS {r['eps_0']:.2f}, P/E {r['pe_0']:.1f}x) "
                f"to {r['date_1']} (price {r['price_1']:.2f}, "
                f"EPS {r['eps_1']:.2f}, P/E {r['pe_1']:.1f}x)."
            )

    # Summary table
    st.markdown("### Summary")
    rows = []
    for label in horizons_pick:
        r = results[label]
        if r.get("ok"):
            rows.append({
                "Horizon": label.upper(),
                "Total (ann)": _pct(r["ann_total"]),
                "EPS growth": _pct(r["ann_eps"]),
                "P/E expansion": _pct(r["ann_pe"]),
                "Dividends": _pct(r["ann_div"]),
                "Residual": _pct(r["ann_residual"]),
            })
        else:
            rows.append({"Horizon": label.upper(), "Total (ann)": "—",
                         "EPS growth": "—", "P/E expansion": "—",
                         "Dividends": "—", "Residual": "—"})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.expander("Methodology"):
        st.markdown("""
**Decomposition.** For each horizon `H`, we compute (annualised, geometric):

```
TotalReturn  ≈  EPSgrowth + MultipleExpansion + Dividends + Residual
```

Specifically:
- **TotalReturn** = `(adj_close_end / adj_close_start) ^ (1/H) − 1` — uses adjusted close which reinvests dividends and accounts for splits
- **EPS growth** = `(EPS_TTM_end / EPS_TTM_start) ^ (1/H) − 1` — TTM EPS reconstructed by summing the 4 most recent reported quarters as of each endpoint date
- **P/E expansion** = `(PE_end / PE_start) ^ (1/H) − 1` — PE = unadjusted close ÷ TTM EPS (subject to split distortions over very long horizons)
- **Dividends** = TotalReturn − Price-only return (annualised)
- **Residual** = TotalReturn − (EPS + PE + Dividends) — captures rounding, currency, and the geometric-vs-arithmetic gap

**Reading the waterfall.** A green bar means that driver added to your return; red means it subtracted. The orange total bar is the annualised total return. If `EPS growth` is large and positive but `P/E expansion` is large and negative, the business improved but the market re-rated it down — a classic "good company, getting cheaper" pattern.

**Caveats.** Requires positive TTM EPS at both endpoints. Goodwill impairments, one-off charges, and share-count changes can distort EPS. Not investment advice.
        """)
