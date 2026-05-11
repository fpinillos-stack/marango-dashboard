"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — PEER COMPARISON MODULE
═══════════════════════════════════════════════════════════════
Side-by-side fundamental comparison of up to 6 tickers.
Color-codes best/worst per row (green/red).
"""
from __future__ import annotations

import os

import streamlit as st
import pandas as pd
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


def _extract_metrics(fund: dict, ticker: str) -> dict:
    """Pull a normalized dict of metrics from EODHD fundamentals payload."""
    gen = fund.get("General") or {}
    hl = fund.get("Highlights") or {}
    val = fund.get("Valuation") or {}
    tech = fund.get("Technicals") or {}
    splits = fund.get("SplitsDividends") or {}

    out = {
        "Ticker": ticker.upper(),
        "Name": gen.get("Name", "—"),
        "Sector": gen.get("Sector", "—"),
        "Currency": gen.get("CurrencyCode", "USD"),
        "Market Cap": _f(hl.get("MarketCapitalization")),
        "Price": _f(tech.get("52WeekHigh")) and _f(hl.get("PERatio")) and None,  # placeholder
        "P/E": _f(hl.get("PERatio")),
        "Forward P/E": _f(val.get("ForwardPE")),
        "P/S": _f(hl.get("PriceSalesTTM")),
        "P/B": _f(hl.get("PriceBookMRQ")),
        "EV/EBITDA": _f(hl.get("EVToEbitda")) or _f(val.get("EnterpriseValueEbitda")),
        "Gross Margin": _f(hl.get("GrossProfitTTM")) and _f(hl.get("RevenueTTM"))
            and (_f(hl.get("GrossProfitTTM")) / _f(hl.get("RevenueTTM"))) or _f(hl.get("ProfitMargin")),
        "Operating Margin": _f(hl.get("OperatingMarginTTM")),
        "Net Margin": _f(hl.get("ProfitMargin")),
        "ROA": _f(hl.get("ReturnOnAssetsTTM")),
        "ROE": _f(hl.get("ReturnOnEquityTTM")),
        "Revenue Growth (YoY)": _f(hl.get("QuarterlyRevenueGrowthYOY")),
        "EPS Growth (YoY)": _f(hl.get("QuarterlyEarningsGrowthYOY")),
        "Div Yield": _f(splits.get("ForwardAnnualDividendYield")),
        "Payout Ratio": _f(splits.get("PayoutRatio")),
        "Beta": _f(tech.get("Beta")),
        "52W High": _f(tech.get("52WeekHigh")),
        "52W Low": _f(tech.get("52WeekLow")),
    }
    return out


# Higher-is-better vs lower-is-better metrics
HIGHER_BETTER = {
    "Gross Margin", "Operating Margin", "Net Margin",
    "ROA", "ROE",
    "Revenue Growth (YoY)", "EPS Growth (YoY)",
    "Div Yield",
    "Market Cap",  # ambiguous but treat as bigger=better for size
}
LOWER_BETTER = {
    "P/E", "Forward P/E", "P/S", "P/B", "EV/EBITDA",
    "Payout Ratio", "Beta",
}
PERCENT_FORMAT = {
    "Gross Margin", "Operating Margin", "Net Margin",
    "ROA", "ROE",
    "Revenue Growth (YoY)", "EPS Growth (YoY)",
    "Div Yield", "Payout Ratio",
}


def _format_value(metric: str, v):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    if metric == "Market Cap":
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"
    if metric in PERCENT_FORMAT:
        return f"{v*100:+.2f}%" if metric.endswith("(YoY)") else f"{v*100:.2f}%"
    if metric in {"P/E", "Forward P/E", "P/S", "P/B", "EV/EBITDA"}:
        return f"{v:.1f}x"
    if metric in {"52W High", "52W Low"}:
        return f"${v:,.2f}"
    if metric == "Beta":
        return f"{v:.2f}"
    return f"{v:,.2f}"


def display_peers_tab():
    """Peer comparison tab."""
    st.markdown("""
    <div style="margin: 1rem 0 1.5rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #f97316;
                    font-size: 1.5rem; font-weight: 700; letter-spacing: 0.05em;">
            PEER COMPARISON
        </div>
        <div style="color: #9ca3af; font-size: 0.85rem; letter-spacing: 0.05em;
                    text-transform: uppercase;">
            Side-by-side fundamentals · Best/Worst color-coded · Powered by EODHD
        </div>
    </div>
    """, unsafe_allow_html=True)

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
        st.button("RUN", use_container_width=True, type="primary",
                  key="peers_run")

    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()][:6]
    if not tickers:
        st.info("Enter at least one ticker.")
        return

    rows = []
    with st.spinner(f"Fetching {len(tickers)} companies…"):
        for t in tickers:
            fund = _fundamentals_p(t)
            if "_error" in fund:
                st.warning(f"{t}: {fund['_error']}")
                continue
            rows.append(_extract_metrics(fund, t))

    if not rows:
        st.error("No data fetched.")
        return

    # Build comparison table — rows = metrics, columns = tickers
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
    tickers_in_data = [r["Ticker"] for r in rows]

    table = {"Metric": metric_order}
    for r in rows:
        table[r["Ticker"]] = [r.get(m) for m in metric_order]
    df = pd.DataFrame(table)

    # Compute best/worst index per row (only for numeric metrics where ranking applies)
    def style_row(row):
        m = row["Metric"]
        if m not in HIGHER_BETTER and m not in LOWER_BETTER:
            return [""] * len(row)
        values = []
        for t in tickers_in_data:
            v = row[t]
            if v is None or (isinstance(v, float) and v != v):
                values.append(None)
            else:
                try:
                    values.append(float(v))
                except Exception:
                    values.append(None)
        valids = [v for v in values if v is not None]
        if len(valids) < 2:
            return [""] * len(row)

        if m in HIGHER_BETTER:
            best_v = max(valids)
            worst_v = min(valids)
        else:
            best_v = min(valids)
            worst_v = max(valids)

        styles = ["color: #9ca3af;"]  # Metric column
        for v in values:
            if v == best_v:
                styles.append("color: #10b981; font-weight: 700;")
            elif v == worst_v:
                styles.append("color: #ef4444; font-weight: 700;")
            else:
                styles.append("")
        return styles

    # Format values for display
    display_df = df.copy()
    for t in tickers_in_data:
        display_df[t] = [
            _format_value(m, v) for m, v in zip(metric_order, df[t])
        ]

    styled = display_df.style.apply(
        lambda row: style_row(df.iloc[row.name]),
        axis=1,
    )

    st.dataframe(styled, hide_index=True, use_container_width=True,
                 height=min(36 * (len(metric_order) + 1) + 4, 800))

    st.caption("Green = best in group · Red = worst in group · "
               "Higher-is-better for margins/returns/growth; "
               "lower-is-better for valuation multiples.")

    with st.expander("Methodology"):
        st.markdown("""
**Peer comparison.** Up to 6 companies fetched from EODHD fundamentals and laid out side-by-side. For each metric:
- Higher-is-better (margins, returns, growth, dividend yield): green = max, red = min
- Lower-is-better (P/E, P/S, EV/EBITDA, payout, beta): green = min, red = max

Color-coding ignores missing values. Best/worst is computed within the displayed peer set — not vs sector or market.

**Picking peers.** EODHD doesn't auto-suggest peers, so you choose them. Look at the same sector/industry, similar market cap, similar business model. Don't compare a hyper-grower like NVDA against a mature utility — multiples will look distorted.
        """)
