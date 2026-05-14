"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — COMPOSITE SIGNAL  (the SIGNALS tab)
═══════════════════════════════════════════════════════════════
Ingenio-style unified per-stock score across the whole universe.

Composite = 0.40·Quality + 0.25·Moat + 0.20·Valuation + 0.15·SentimentNorm

  · Quality   — SA Score from portfolio_engine (sector-adjusted)
  · Moat      — competitive-moat score (moat.py)
  · Valuation — sector-relative valuation pillar (engine P5)
  · Sentiment — analyst + earnings-surprise narrative score (sentiment.py)

Plus a per-ticker deep dive: decomposed valuation, moat breakdown,
sentiment breakdown.
"""
from __future__ import annotations

import math

import streamlit as st
import pandas as pd

from portfolio_engine import UNIVERSE, fetch_fundamentals, build_portfolio
from moat import compute_moat
from sentiment import compute_sentiment, fetch_eod


def _f(v):
    try:
        if v is None:
            return None
        x = float(v)
        return None if (math.isnan(x) or math.isinf(x)) else x
    except Exception:
        return None


def _sentiment_norm(s):
    """Map sentiment -100..+100 → 0..100."""
    if s is None:
        return 50.0
    return max(0.0, min(100.0, 50.0 + s / 2.0))


def composite_score(quality, moat, valuation, sentiment) -> float:
    q = quality if quality is not None else 50.0
    m = moat if moat is not None else 50.0
    v = valuation if valuation is not None else 50.0
    s = _sentiment_norm(sentiment)
    return 0.40 * q + 0.25 * m + 0.20 * v + 0.15 * s


def composite_signal(score: float) -> str:
    if score >= 72:
        return "🚀 STRONG BUY"
    if score >= 62:
        return "✅ BUY"
    if score >= 52:
        return "⚠️ HOLD"
    if score >= 42:
        return "🟠 UNDERWEIGHT"
    return "🔴 SELL"


def valuation_decomposed(engine_row: dict) -> dict:
    """Break the valuation pillar into its sub-components + a PEG read."""
    comp = {}
    s_pe = _f(engine_row.get("S.PE"))
    s_ev = _f(engine_row.get("S.EVEB"))
    s_fcf = _f(engine_row.get("S.PFCF"))
    comp["Fwd P/E vs sector"] = (s_pe, _f(engine_row.get("Fwd P/E")))
    comp["EV/EBITDA vs sector"] = (s_ev, _f(engine_row.get("EV/EBITDA")))
    comp["P/FCF vs sector"] = (s_fcf, _f(engine_row.get("P/FCF")))

    # PEG = Fwd P/E / (EPS growth 3Y, in %)
    fpe = _f(engine_row.get("Fwd P/E"))
    epsg = _f(engine_row.get("m_EPSGr3Y"))
    peg = None
    peg_score = None
    if fpe and epsg and epsg > 0:
        peg = fpe / (epsg * 100)
        # PEG 1.0 → 65 ; 0.5 → 100 ; 2.0 → 30 ; 3.0+ → 10
        peg_score = max(10.0, min(100.0, 130 - peg * 65))
    comp["PEG ratio"] = (peg_score, peg)

    vals = [c[0] for c in comp.values() if c[0] is not None]
    score = sum(vals) / len(vals) if vals else 50.0
    return {"score": round(score, 1), "components": comp}


@st.cache_data(ttl=86400, show_spinner=False)
def build_signals_table() -> pd.DataFrame:
    """
    Full universe with Quality / Moat / Valuation / Sentiment / Composite.
    Reuses portfolio_engine's cached fundamentals — no extra API calls.
    """
    base = build_portfolio()
    if base is None or base.empty:
        return pd.DataFrame()

    out = []
    for _, r in base.iterrows():
        company = r.get("Company")
        ticker_full = UNIVERSE.get(company, (r.get("Ticker", "") + ".US",))[0]
        quality = _f(r.get("Quality_Score"))
        valuation = _f(r.get("P5"))

        fund = fetch_fundamentals(ticker_full)
        moat_res = compute_moat(fund)
        moat = moat_res["score"] if moat_res.get("ok") else None
        sent_res = compute_sentiment(fund)  # no momentum in bulk pass
        sentiment = sent_res["score"] if sent_res.get("ok") else None

        comp = composite_score(quality, moat, valuation, sentiment)
        out.append({
            "Company": company,
            "Ticker": r.get("Ticker"),
            "GICS Sector": r.get("GICS Sector"),
            "Marango_Holding": r.get("Marango_Holding", False),
            "Quality": round(quality, 1) if quality is not None else None,
            "Moat": round(moat, 1) if moat is not None else None,
            "Valuation": round(valuation, 1) if valuation is not None else None,
            "Sentiment": round(sentiment, 1) if sentiment is not None else None,
            "Composite": round(comp, 1),
            "Signal": composite_signal(comp),
        })
    df = pd.DataFrame(out).sort_values("Composite", ascending=False).reset_index(drop=True)
    return df


# ───────────────────────────────────────────────────────────────
# UI HELPERS
# ───────────────────────────────────────────────────────────────

def _score_color(v, lo=40, hi=70):
    if v is None:
        return "#6b7280"
    if v >= hi:
        return "#10b981"
    if v >= (lo + hi) / 2:
        return "#06b6d4"
    if v >= lo:
        return "#f59e0b"
    return "#ef4444"


def _sent_color(v):
    if v is None:
        return "#6b7280"
    if v >= 20:
        return "#10b981"
    if v > -20:
        return "#9ca3af"
    return "#ef4444"


def _cell(text, color, weight="400", align="right"):
    return ('<td style="padding:0.45rem 0.7rem;color:' + color +
            ';font-family:JetBrains Mono,monospace;font-size:0.8rem;'
            'border-bottom:1px solid rgba(255,255,255,0.05);text-align:' + align +
            ';font-weight:' + weight + ';white-space:nowrap;">' + text + '</td>')


def _universe_table_html(df: pd.DataFrame) -> str:
    headers = ["#", "Ticker", "Company", "Sector", "Signal",
               "Composite", "Quality", "Moat", "Valuation", "Sentiment"]
    head = "".join(
        '<th style="padding:0.6rem 0.7rem;color:#9ca3af;'
        'background:rgba(255,255,255,0.02);font-family:JetBrains Mono,monospace;'
        'font-size:0.68rem;letter-spacing:0.08em;text-transform:uppercase;'
        'text-align:' + ("left" if h in ("Ticker", "Company", "Sector", "Signal") else "right") +
        ';border-bottom:2px solid rgba(249,115,22,0.3);">' + h + '</th>'
        for h in headers)

    body = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        mk = ' <span style="color:#f97316;">●</span>' if r.get("Marango_Holding") else ""
        comp = r.get("Composite")
        cells = [
            _cell(str(i), "#6b7280", align="right"),
            _cell(str(r.get("Ticker", "")) + mk, "#e5e7eb", "700", "left"),
            _cell(str(r.get("Company", ""))[:24], "#9ca3af", "400", "left"),
            _cell(str(r.get("GICS Sector", ""))[:20], "#6b7280", "400", "left"),
            _cell(str(r.get("Signal", "")), "#e5e7eb", "600", "left"),
            _cell("{:.1f}".format(comp) if comp is not None else "—",
                  _score_color(comp, 45, 65), "700"),
            _cell("{:.0f}".format(r["Quality"]) if r.get("Quality") is not None else "—",
                  _score_color(r.get("Quality"))),
            _cell("{:.0f}".format(r["Moat"]) if r.get("Moat") is not None else "—",
                  _score_color(r.get("Moat"))),
            _cell("{:.0f}".format(r["Valuation"]) if r.get("Valuation") is not None else "—",
                  _score_color(r.get("Valuation"))),
            _cell("{:+.0f}".format(r["Sentiment"]) if r.get("Sentiment") is not None else "—",
                  _sent_color(r.get("Sentiment"))),
        ]
        body.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div style="background:rgba(15,15,25,0.8);border-radius:0.75rem;'
        'border:1px solid rgba(255,255,255,0.05);overflow-x:auto;max-height:560px;'
        'overflow-y:auto;backdrop-filter:blur(12px);">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead style="position:sticky;top:0;">' + "<tr>" + head + "</tr></thead>"
        '<tbody>' + "".join(body) + '</tbody></table></div>'
    )


def _bar(label, value, maxv, color, detail=""):
    pct = max(0, min(100, (value / maxv * 100) if maxv else 0))
    return (
        '<div style="margin-bottom:0.5rem;">'
        '<div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.15rem;">'
        '<span style="color:#e5e7eb;">' + label + '</span>'
        '<span style="color:' + color + ';font-weight:700;font-family:JetBrains Mono,monospace;">'
        + "{:.1f}".format(value) + '/' + str(maxv) + '</span></div>'
        '<div style="background:rgba(255,255,255,0.06);border-radius:3px;height:10px;overflow:hidden;">'
        '<div style="background:' + color + ';width:' + str(pct) + '%;height:100%;"></div></div>'
        + ('<div style="color:#6b7280;font-size:0.68rem;margin-top:0.1rem;">' + detail + '</div>' if detail else "")
        + '</div>'
    )


# ───────────────────────────────────────────────────────────────
# MAIN TAB
# ───────────────────────────────────────────────────────────────

def display_signals_tab():
    st.markdown(
        '<div style="margin:1rem 0 1.5rem 0;">'
        '<div style="font-family:JetBrains Mono,monospace;color:#f97316;'
        'font-size:1.5rem;font-weight:700;letter-spacing:0.05em;">COMPOSITE SIGNALS</div>'
        '<div style="color:#9ca3af;font-size:0.85rem;letter-spacing:0.05em;'
        'text-transform:uppercase;">Quality × Moat × Valuation × Sentiment — ranked universe · Powered by EODHD</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        from portfolio_engine import _eodhd_key
        if not _eodhd_key():
            st.warning("EODHD_API_KEY not configured.")
            return
    except Exception:
        pass

    with st.spinner("Scoring universe… (first load builds the cache, ~30-60s)"):
        df = build_signals_table()

    if df is None or df.empty:
        st.error("Could not build the signals table.")
        return

    # ── filters ──
    c1, c2, c3 = st.columns([1.2, 1.4, 1.4])
    with c1:
        marango_only = st.checkbox("Marango holdings only", value=False, key="sig_marango")
    with c2:
        sectors = ["All"] + sorted(df["GICS Sector"].dropna().unique().tolist())
        sec = st.selectbox("Sector", sectors, key="sig_sector")
    with c3:
        sort_by = st.selectbox("Rank by", ["Composite", "Quality", "Moat",
                                           "Valuation", "Sentiment"], key="sig_sort")

    view = df.copy()
    if marango_only:
        view = view[view["Marango_Holding"] == True]
    if sec != "All":
        view = view[view["GICS Sector"] == sec]
    view = view.sort_values(sort_by, ascending=False).reset_index(drop=True)

    # ── KPI strip ──
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Universe", len(view))
    k2.metric("Avg Composite", "{:.1f}".format(view["Composite"].mean()) if len(view) else "—")
    strong = (view["Signal"].str.contains("STRONG BUY", na=False)).sum()
    k3.metric("Strong Buys", int(strong))
    marango_n = int(view["Marango_Holding"].sum())
    k4.metric("Marango holdings", marango_n)

    st.markdown("### Universe — ranked by " + sort_by)
    st.markdown(_universe_table_html(view), unsafe_allow_html=True)
    st.caption("Orange ● = Marango Equity Fund holding · "
               "green = strong / red = weak · Sentiment is −100..+100")

    # ── per-ticker deep dive ──
    st.divider()
    st.markdown("### Deep Dive")
    options = [r["Ticker"] + " — " + str(r["Company"]) for _, r in view.iterrows()]
    if not options:
        return
    pick = st.selectbox("Select a company", options, key="sig_pick")
    sel_ticker = pick.split(" — ")[0]
    sel_row = view[view["Ticker"] == sel_ticker].iloc[0].to_dict()
    company = sel_row["Company"]
    ticker_full = UNIVERSE.get(company, (sel_ticker + ".US",))[0]

    # engine row (full, with sub-scores) + fundamentals + eod for momentum
    base = build_portfolio()
    engine_row = base[base["Company"] == company]
    engine_row = engine_row.iloc[0].to_dict() if len(engine_row) else {}
    fund = fetch_fundamentals(ticker_full)
    with st.spinner("Loading price momentum…"):
        eod = fetch_eod(ticker_full)
    moat_res = compute_moat(fund)
    sent_res = compute_sentiment(fund, eod)
    val_res = valuation_decomposed(engine_row)

    # recompute composite with momentum-aware sentiment
    comp = composite_score(sel_row.get("Quality"), sel_row.get("Moat"),
                           sel_row.get("Valuation"),
                           sent_res["score"] if sent_res.get("ok") else None)
    sig = composite_signal(comp)
    sig_color = _score_color(comp, 45, 65)

    st.markdown(
        '<div style="background:rgba(15,15,25,0.8);border:1px solid ' + sig_color +
        '55;border-radius:0.75rem;padding:1.2rem 1.5rem;margin:0.5rem 0 1rem 0;'
        'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">'
        '<div><div style="font-family:JetBrains Mono,monospace;color:#e5e7eb;'
        'font-size:1.2rem;font-weight:700;">' + sel_ticker + ' · ' + str(company) + '</div>'
        '<div style="color:#9ca3af;font-size:0.8rem;">' + str(sel_row.get("GICS Sector", "")) + '</div></div>'
        '<div style="text-align:right;"><div style="font-family:JetBrains Mono,monospace;'
        'color:' + sig_color + ';font-size:2.2rem;font-weight:700;">' + "{:.1f}".format(comp) + '</div>'
        '<div style="color:' + sig_color + ';font-size:0.9rem;font-weight:600;">' + sig + '</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # four sub-score chips
    cc = st.columns(4)
    for col, (lbl, val, is_sent) in zip(cc, [
        ("QUALITY", sel_row.get("Quality"), False),
        ("MOAT", sel_row.get("Moat"), False),
        ("VALUATION", val_res["score"], False),
        ("SENTIMENT", sent_res["score"] if sent_res.get("ok") else None, True),
    ]):
        color = _sent_color(val) if is_sent else _score_color(val)
        disp = ("{:+.0f}".format(val) if (is_sent and val is not None)
                else ("{:.0f}".format(val) if val is not None else "—"))
        col.markdown(
            '<div style="background:rgba(15,15,25,0.8);padding:0.9rem;border-radius:0.6rem;'
            'border:1px solid ' + color + '44;text-align:center;">'
            '<div style="color:#9ca3af;font-size:0.65rem;letter-spacing:0.1em;'
            'font-family:JetBrains Mono,monospace;">' + lbl + '</div>'
            '<div style="color:' + color + ';font-family:JetBrains Mono,monospace;'
            'font-size:1.8rem;font-weight:700;">' + disp + '</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")
    d1, d2 = st.columns(2)

    # Valuation decomposed
    with d1:
        st.markdown("#### Valuation — decomposed")
        for label, (sc, raw) in val_res["components"].items():
            if sc is None:
                st.markdown('<div style="color:#6b7280;font-size:0.78rem;margin-bottom:0.5rem;">'
                            + label + ' — n/a</div>', unsafe_allow_html=True)
                continue
            detail = ""
            if raw is not None:
                detail = ("PEG {:.2f}".format(raw) if "PEG" in label
                          else "{:.1f}x".format(raw))
            st.markdown(_bar(label, sc, 100, _score_color(sc), detail),
                        unsafe_allow_html=True)

    # Moat breakdown
    with d2:
        st.markdown("#### Moat — breakdown")
        if moat_res.get("ok"):
            for label, (pts, mx, detail) in moat_res["components"].items():
                st.markdown(_bar(label, pts, mx, moat_res["color"], detail),
                            unsafe_allow_html=True)
        else:
            st.warning(moat_res.get("error", "n/a"))

    # Sentiment breakdown
    st.markdown("#### Narrative Sentiment — breakdown")
    if sent_res.get("ok"):
        scols = st.columns(3)
        for col, (label, (sc, w, detail, n)) in zip(scols, sent_res["components"].items()):
            color = _sent_color(sc)
            col.markdown(
                '<div style="background:rgba(15,15,25,0.8);padding:0.8rem;border-radius:0.6rem;'
                'border:1px solid rgba(255,255,255,0.06);">'
                '<div style="color:#9ca3af;font-size:0.7rem;letter-spacing:0.05em;">'
                + label + ' <span style="color:#6b7280;">(w ' + "{:.0%}".format(w) + ')</span></div>'
                '<div style="color:' + color + ';font-family:JetBrains Mono,monospace;'
                'font-size:1.5rem;font-weight:700;">' + "{:+.0f}".format(sc) + '</div>'
                '<div style="color:#6b7280;font-size:0.68rem;">' + str(detail) + '</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.warning(sent_res.get("error", "n/a"))

    with st.expander("Methodology"):
        st.markdown(
            "**Composite** = 0.40·Quality + 0.25·Moat + 0.20·Valuation + 0.15·SentimentNorm\n\n"
            "- **Quality** — sector-adjusted SA Score (portfolio engine, 6 pillars)\n"
            "- **Moat** — margin trend, margin level, R&D intensity, margin stability, ROIC\n"
            "- **Valuation** — sector-relative valuation pillar; decomposed into Fwd P/E, "
            "EV/EBITDA, P/FCF (all vs sector thresholds) and PEG\n"
            "- **Sentiment** — analyst recommendations + earnings surprise + price momentum, "
            "scaled −100..+100, normalised to 0-100 for the blend\n\n"
            "The universe table uses sentiment without momentum (no extra API calls); the "
            "deep dive recomputes sentiment with price momentum. Not investment advice."
        )
