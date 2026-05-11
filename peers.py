"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — PEER COMPARISON MODULE
═══════════════════════════════════════════════════════════════
Side-by-side fundamental comparison of up to 6 tickers.
Color-codes best/worst per row (green/red) via inline HTML.
"""
from __future__ import annotations

import os

import streamlit as st
import requests


EODHD_BASE = "https://eodhd.com/api"


def _eodhd_key() -> str:
    try:
        k = st.secrets.get("EODHD_API_KEY", "")
    except Exception:
        k = ""
    return k or os.environ.get("EODHD_API_KEY", "")


def _norm(t):
    t = (t or "").strip().upper()
    if not t:
        return ""
    if "." not in t:
        t = f"{t}.US"
    return t


@st.cache_data(ttl=3600, show_spinner=False)
def _fundamentals_p(ticker: str) -> dict:
    key = _eodhd_key()
    if not key:
        return {"_error": "no_api_key"}
    t = _norm(ticker)
    try:
        r = requests.get(f"{EODHD_BASE}/fundamentals/{t}",
                         params={"api_token": key}, timeout=20)
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:200]}"}


def _f(v):
    if v in (None, "NA", "", "null"):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _extract_metrics(fund: dict, ticker: str) -> dict:
    gen = fund.get("General") or {}
    hl = fund.get("Highlights") or {}
    val = fund.get("Valuation") or {}
    tech = fund.get("Technicals") or {}
    splits = fund.get("SplitsDividends") or {}

    gp_ttm = _f(hl.get("GrossProfitTTM"))
    rev_ttm = _f(hl.get("RevenueTTM"))
    gross_margin = _safe_div(gp_ttm, rev_ttm)

    return {
        "Ticker": ticker.upper(),
        "Name": gen.get("Name", "—"),
        "Sector": gen.get("Sector", "—"),
        "Currency": gen.get("CurrencyCode", "USD"),
        "Market Cap": _f(hl.get("MarketCapitalization")),
        "P/E": _f(hl.get("PERatio")) or _f(val.get("TrailingPE")),
        "Forward P/E": _f(val.get("ForwardPE")),
        "P/S": _f(hl.get("PriceSalesTTM")) or _f(val.get("PriceSalesTTM")),
        "P/B": _f(hl.get("PriceBookMRQ")) or _f(val.get("PriceBookMRQ")),
        "EV/EBITDA": _f(val.get("EnterpriseValueEbitda")) or _f(hl.get("EVToEbitda")),
        "Gross Margin": gross_margin,
        "Operating Margin": _f(hl.get("OperatingMarginTTM")),
        "Net Margin": _f(hl.get("ProfitMargin")),
        "ROA": _f(hl.get("ReturnOnAssetsTTM")),
        "ROE": _f(hl.get("ReturnOnEquityTTM")),
        "Revenue Growth (YoY)": _f(hl.get("QuarterlyRevenueGrowthYOY")),
        "EPS Growth (YoY)": _f(hl.get("QuarterlyEarningsGrowthYOY")),
        "Div Yield": _f(hl.get("DividendYield")) or _f(splits.get("ForwardAnnualDividendYield")),
        "Payout Ratio": _f(splits.get("PayoutRatio")),
        "Beta": _f(tech.get("Beta")),
        "52W High": _f(tech.get("52WeekHigh")),
        "52W Low": _f(tech.get("52WeekLow")),
    }


HIGHER_BETTER = {
    "Gross Margin", "Operating Margin", "Net Margin",
    "ROA", "ROE",
    "Revenue Growth (YoY)", "EPS Growth (YoY)",
    "Div Yield",
}
LOWER_BETTER = {
    "P/E", "Forward P/E", "P/S", "P/B", "EV/EBITDA",
    "Payout Ratio",
}
PERCENT_FORMAT = {
    "Gross Margin", "Operating Margin", "Net Margin",
    "ROA", "ROE",
    "Revenue Growth (YoY)", "EPS Growth (YoY)",
    "Div Yield", "Payout Ratio",
}
TEXT_METRICS = {"Name", "Sector"}


def _format_value(metric, v):
    if metric in TEXT_METRICS:
        return str(v) if v not in (None, "") else "—"
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    if metric == "Market Cap":
        if v >= 1e12: return "${:.2f}T".format(v/1e12)
        if v >= 1e9:  return "${:.2f}B".format(v/1e9)
        if v >= 1e6:  return "${:.0f}M".format(v/1e6)
        return "${:,.0f}".format(v)
    if metric in PERCENT_FORMAT:
        return "{:+.2f}%".format(v*100) if metric.endswith("(YoY)") else "{:.2f}%".format(v*100)
    if metric in {"P/E", "Forward P/E", "P/S", "P/B", "EV/EBITDA"}:
        return "{:.1f}x".format(v)
    if metric in {"52W High", "52W Low"}:
        return "${:,.2f}".format(v)
    if metric == "Beta":
        return "{:.2f}".format(v)
    return "{:,.2f}".format(v)


def _row_html(metric, values_by_ticker, tickers):
    color_for = {t: "#e5e7eb" for t in tickers}
    if metric in HIGHER_BETTER or metric in LOWER_BETTER:
        nums = [(t, float(v)) for t in tickers
                for v in [values_by_ticker.get(t)]
                if v is not None and isinstance(v, (int, float)) and v == v]
        if len(nums) >= 2:
            vals = [v for _, v in nums]
            if metric in HIGHER_BETTER:
                best_v, worst_v = max(vals), min(vals)
            else:
                best_v, worst_v = min(vals), max(vals)
            for t, v in nums:
                if v == best_v:
                    color_for[t] = "#10b981"
                elif v == worst_v:
                    color_for[t] = "#ef4444"

    label_color = "#9ca3af" if metric in TEXT_METRICS else "#f97316"
    label_style = ("padding:0.5rem 0.75rem;color:" + label_color +
                   ";font-family:JetBrains Mono,monospace;font-size:0.78rem;"
                   "border-bottom:1px solid rgba(255,255,255,0.05);"
                   "text-align:left;font-weight:600;white-space:nowrap;")
    cells = ['<td style="' + label_style + '">' + metric + '</td>']
    for t in tickers:
        v = values_by_ticker.get(t)
        formatted = _format_value(metric, v)
        weight = "700" if color_for[t] in ("#10b981", "#ef4444") else "400"
        cell_style = ("padding:0.5rem 0.75rem;color:" + color_for[t] +
                      ";font-family:JetBrains Mono,monospace;font-size:0.82rem;"
                      "border-bottom:1px solid rgba(255,255,255,0.05);"
                      "text-align:right;font-weight:" + weight +
                      ";white-space:nowrap;")
        cells.append('<td style="' + cell_style + '">' + formatted + '</td>')
    return "<tr>" + "".join(cells) + "</tr>"


def display_peers_tab():
    st.markdown(
        '<div style="margin:1rem 0 1.5rem 0;">'
        '<div style="font-family:JetBrains Mono,monospace;color:#f97316;'
        'font-size:1.5rem;font-weight:700;letter-spacing:0.05em;">PEER COMPARISON</div>'
        '<div style="color:#9ca3af;font-size:0.85rem;letter-spacing:0.05em;'
        'text-transform:uppercase;">Side-by-side fundamentals · Best/Worst color-coded · Powered by EODHD</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not _eodhd_key():
        st.warning("EODHD_API_KEY not configured.")
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        raw = st.text_input(
            "Tickers (comma-separated, max 6)",
            value="AAPL, MSFT, GOOGL, META, AMZN, NVDA",
            help="e.g. AAPL, MSFT, GOOGL — .US suffix auto-applied.",
            key="peers_tickers",
        )
    with col2:
        st.write("")
        st.write("")
        st.button("RUN", use_container_width=True, type="primary", key="peers_run")

    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()][:6]
    if not tickers:
        st.info("Enter at least one ticker.")
        return

    rows_data = []
    with st.spinner("Fetching " + str(len(tickers)) + " companies…"):
        for t in tickers:
            fund = _fundamentals_p(t)
            if "_error" in fund:
                st.warning(t + ": " + str(fund["_error"]))
                continue
            try:
                rows_data.append(_extract_metrics(fund, t))
            except Exception as e:
                st.warning(t + ": extraction failed — " + type(e).__name__ + ": " + str(e))

    if not rows_data:
        st.error("No data fetched for any ticker.")
        return

    tickers_in_data = [r["Ticker"] for r in rows_data]
    metric_order = [
        "Name", "Sector",
        "Market Cap",
        "P/E", "Forward P/E", "P/S", "P/B", "EV/EBITDA",
        "Gross Margin", "Operating Margin", "Net Margin",
        "ROA", "ROE",
        "Revenue Growth (YoY)", "EPS Growth (YoY)",
        "Div Yield", "Payout Ratio",
        "Beta", "52W High", "52W Low",
    ]

    values_by_metric = {}
    for m in metric_order:
        values_by_metric[m] = {r["Ticker"]: r.get(m) for r in rows_data}

    header_cells = [
        '<th style="padding:0.6rem 0.75rem;color:#9ca3af;'
        'background:rgba(255,255,255,0.02);'
        'font-family:JetBrains Mono,monospace;font-size:0.7rem;'
        'letter-spacing:0.1em;text-transform:uppercase;text-align:left;'
        'border-bottom:2px solid rgba(249,115,22,0.3);">Metric</th>'
    ]
    for t in tickers_in_data:
        header_cells.append(
            '<th style="padding:0.6rem 0.75rem;color:#f97316;'
            'background:rgba(255,255,255,0.02);'
            'font-family:JetBrains Mono,monospace;font-size:0.78rem;'
            'letter-spacing:0.05em;text-align:right;'
            'border-bottom:2px solid rgba(249,115,22,0.3);'
            'font-weight:700;">' + t + '</th>'
        )
    header_html = "<tr>" + "".join(header_cells) + "</tr>"

    body_rows = [_row_html(m, values_by_metric[m], tickers_in_data) for m in metric_order]
    body_html = "".join(body_rows)

    table_html = (
        '<div style="background:rgba(15,15,25,0.8);border-radius:0.75rem;'
        'border:1px solid rgba(255,255,255,0.05);overflow-x:auto;'
        'backdrop-filter:blur(12px);">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead>' + header_html + '</thead>'
        '<tbody>' + body_html + '</tbody>'
        '</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    st.caption("Green = best in group · Red = worst in group · "
               "Higher-is-better for margins/returns/growth/yield; "
               "lower-is-better for valuation multiples.")

    with st.expander("Methodology"):
        st.markdown(
            "**Peer comparison.** Up to 6 companies fetched from EODHD fundamentals "
            "and laid out side-by-side. For each metric:\n"
            "- Higher-is-better (margins, returns, growth, dividend yield): "
            "green = max, red = min\n"
            "- Lower-is-better (P/E, P/S, EV/EBITDA, payout): "
            "green = min, red = max\n\n"
            "Color-coding ignores missing values. Best/worst is computed within "
            "the displayed peer set — not vs sector or market.\n\n"
            "**Picking peers.** EODHD doesn't auto-suggest peers, so you choose them. "
            "Look at the same sector/industry, similar market cap, similar business model."
        )
