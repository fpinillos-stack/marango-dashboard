"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — HISTORICAL MULTIPLES MODULE
═══════════════════════════════════════════════════════════════
Historical valuation multiples (P/E, EV/EBITDA, P/S, P/FCF) over
the last 10 fiscal years, with current value vs its own history
percentile marker.

Inspired by Koyfin / Bloomberg valuation history surfaces.
"""
from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests


EODHD_BASE = "https://eodhd.com/api"


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
def _fundamentals(ticker: str) -> dict:
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


@st.cache_data(ttl=3600, show_spinner=False)
def _eod_10y(ticker: str) -> list:
    key = _eodhd_key()
    if not key:
        return []
    t = _norm(ticker)
    from_date = (datetime.utcnow().replace(year=datetime.utcnow().year - 11)
                 ).strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{EODHD_BASE}/eod/{t}",
                         params={"api_token": key, "fmt": "json",
                                 "from": from_date}, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _safe_float(v):
    if v in (None, "NA", "", "null"):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _price_near(eod: list, target_date_str: str):
    """Return close price on or before target_date_str, else nearest after."""
    if not eod or not target_date_str:
        return None
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d")
    except Exception:
        return None
    before, after = None, None
    for b in eod:
        d = b.get("date")
        if not d:
            continue
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            continue
        if dt <= target:
            before = b
        elif after is None:
            after = b
            break
    bar = before or after
    if bar is None:
        return None
    c = _safe_float(bar.get("close"))
    return c


def build_multiples_history(ticker: str) -> dict:
    """Return dict with rows=year, cols=multiples + current snapshot."""
    out = {"ok": False}
    fund = _fundamentals(ticker)
    if "_error" in fund:
        out["error"] = fund["_error"]
        return out

    inc = ((fund.get("Financials") or {}).get("Income_Statement") or {}).get("yearly") or {}
    bs = ((fund.get("Financials") or {}).get("Balance_Sheet") or {}).get("yearly") or {}
    cf = ((fund.get("Financials") or {}).get("Cash_Flow") or {}).get("yearly") or {}
    shares_stats = fund.get("SharesStats") or {}
    hl = fund.get("Highlights") or {}
    gen = fund.get("General") or {}

    eod = _eod_10y(ticker)

    # Get all fiscal year-end dates available, take last 10
    dates = sorted(set(inc.keys()) & set(bs.keys()), reverse=True)[:10]
    if not dates:
        out["error"] = "No financial history available."
        return out

    rows = []
    for d in dates:
        irow = inc.get(d, {}) or {}
        brow = bs.get(d, {}) or {}
        crow = cf.get(d, {}) or {}

        revenue = _safe_float(irow.get("totalRevenue"))
        net_inc = _safe_float(irow.get("netIncome"))
        ebitda = _safe_float(irow.get("ebitda"))
        op_inc = _safe_float(irow.get("operatingIncome"))
        dep_amort = _safe_float(irow.get("depreciationAndAmortization"))
        # If ebitda missing, try to reconstruct
        if ebitda is None and op_inc is not None and dep_amort is not None:
            ebitda = op_inc + dep_amort

        cfo = _safe_float(crow.get("totalCashFromOperatingActivities"))
        capex = _safe_float(crow.get("capitalExpenditures"))
        fcf = None
        if cfo is not None and capex is not None:
            # capex usually negative; FCF = CFO + capex (since capex is negative)
            fcf = cfo + capex

        lt_debt = _safe_float(brow.get("longTermDebt")) or 0
        st_debt = _safe_float(brow.get("shortLongTermDebt")) or 0
        cash = _safe_float(brow.get("cash")) or _safe_float(brow.get("cashAndShortTermInvestments")) or 0
        shares = _safe_float(brow.get("commonStockSharesOutstanding"))
        if shares is None:
            shares = _safe_float(shares_stats.get("SharesOutstanding"))

        # Price at fiscal year-end
        price = _price_near(eod, d)
        if price is None or shares in (None, 0):
            market_cap = None
        else:
            market_cap = price * shares

        ev = None
        if market_cap is not None:
            ev = market_cap + (lt_debt + st_debt) - cash

        pe = (market_cap / net_inc) if (market_cap and net_inc and net_inc > 0) else None
        ps = (market_cap / revenue) if (market_cap and revenue and revenue > 0) else None
        ev_ebitda = (ev / ebitda) if (ev and ebitda and ebitda > 0) else None
        p_fcf = (market_cap / fcf) if (market_cap and fcf and fcf > 0) else None

        rows.append({
            "date": d,
            "price": price,
            "market_cap": market_cap,
            "revenue": revenue,
            "net_income": net_inc,
            "ebitda": ebitda,
            "fcf": fcf,
            "P/E": pe,
            "P/S": ps,
            "EV/EBITDA": ev_ebitda,
            "P/FCF": p_fcf,
        })

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    # Current snapshot from Highlights (most recent)
    cur_pe = _safe_float(hl.get("PERatio"))
    cur_ps = _safe_float(hl.get("PriceSalesTTM"))
    cur_pb = _safe_float(hl.get("PriceBookMRQ"))
    cur_ev_ebitda = _safe_float(hl.get("EVToEbitda"))
    out.update({
        "ok": True,
        "name": gen.get("Name", ticker),
        "currency": gen.get("CurrencyCode", "USD"),
        "df": df,
        "current": {
            "P/E": cur_pe,
            "P/S": cur_ps,
            "EV/EBITDA": cur_ev_ebitda,
            "P/FCF": (df["P/FCF"].iloc[-1] if "P/FCF" in df.columns and len(df) else None),
        },
    })
    return out


def percentile_of(value, series):
    """Return percentile (0-100) of value within series (ignoring NaN/None)."""
    if value is None:
        return None
    vals = [v for v in series if v is not None and v == v]  # filter NaN
    if len(vals) < 2:
        return None
    n_below = sum(1 for v in vals if v < value)
    return 100.0 * n_below / len(vals)


def _band_chart(df: pd.DataFrame, metric: str, current_value, currency: str):
    """Line chart of historical multiple with current marker."""
    vals = df[metric].tolist()
    dates = df["date"].tolist()
    valid_idx = [i for i, v in enumerate(vals) if v is not None and v == v]
    if len(valid_idx) < 2:
        fig = go.Figure()
        fig.add_annotation(text=f"Insufficient {metric} history",
                           xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(color="#64748b"))
        fig.update_layout(height=240, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        return fig

    valid_vals = [vals[i] for i in valid_idx]
    valid_dates = [dates[i] for i in valid_idx]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid_dates, y=valid_vals, mode="lines+markers",
        line=dict(color="#ea580c", width=2),
        marker=dict(size=6, color="#ea580c"),
        name=metric, hovertemplate="%{x}<br>%{y:.1f}x<extra></extra>",
    ))

    # Median & quartile bands
    s = pd.Series(valid_vals)
    p25, p50, p75 = s.quantile([0.25, 0.5, 0.75])
    for lvl, color, label in [(p50, "#0891b2", "Median"),
                               (p25, "#059669", "25th"),
                               (p75, "#dc2626", "75th")]:
        fig.add_hline(y=lvl, line_dash="dot",
                      line_color=color, opacity=0.5,
                      annotation_text=f"{label} {lvl:.1f}x",
                      annotation_position="right",
                      annotation_font_color=color,
                      annotation_font_size=10)

    if current_value is not None and current_value == current_value:
        fig.add_hline(y=current_value, line_dash="solid",
                      line_color="#f59e0b", line_width=2,
                      annotation_text=f"NOW {current_value:.1f}x",
                      annotation_position="left",
                      annotation_font_color="#f59e0b",
                      annotation_font_size=11)

    fig.update_layout(
        title=dict(text=metric, font=dict(size=12, color="#ea580c",
                                           family="JetBrains Mono, monospace")),
        height=240,
        margin=dict(l=10, r=80, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="JetBrains Mono, monospace", color="#1e293b", size=10),
        xaxis=dict(showgrid=False, color="#64748b"),
        yaxis=dict(gridcolor="rgba(15,23,42,0.07)", zeroline=False,
                   color="#64748b"),
        showlegend=False,
    )
    return fig


def display_multiples_tab():
    """Historical multiples band chart."""
    st.markdown("""
    <div style="margin: 1rem 0 1.5rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #ea580c;
                    font-size: 1.5rem; font-weight: 700; letter-spacing: 0.05em;">
            HISTORICAL MULTIPLES
        </div>
        <div style="color: #64748b; font-size: 0.85rem; letter-spacing: 0.05em;
                    text-transform: uppercase;">
            10-year valuation history · Percentile vs own history · Powered by EODHD
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not _eodhd_key():
        st.warning("EODHD_API_KEY not configured.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Ticker", value="AAPL",
                               key="mult_ticker").upper().strip()
    with col2:
        st.write("")
        st.write("")
        st.button("RUN", use_container_width=True, type="primary",
                  key="mult_run")

    if not ticker:
        return

    with st.spinner(f"Fetching {ticker}…"):
        data = build_multiples_history(ticker)

    if not data.get("ok"):
        st.error(data.get("error", "Failed to load."))
        return

    df = data["df"]
    cur = data["current"]
    st.markdown(f"""
    <div style="margin: 0.5rem 0 1rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #1e293b;
                    font-size: 1.1rem; font-weight: 600;">{data['name']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Percentile summary row
    metrics = ["P/E", "P/S", "EV/EBITDA", "P/FCF"]
    cols = st.columns(4)
    for i, m in enumerate(metrics):
        cur_v = cur.get(m)
        # Fall back to most recent valid historical value if current missing
        if cur_v is None and len(df):
            non_null = df[m].dropna()
            if len(non_null):
                cur_v = float(non_null.iloc[-1])
        pct = percentile_of(cur_v, df[m].tolist())
        with cols[i]:
            badge_color = "#64748b"
            badge_label = "—"
            if pct is not None:
                if pct >= 80:
                    badge_color, badge_label = "#dc2626", "EXPENSIVE"
                elif pct >= 60:
                    badge_color, badge_label = "#ea580c", "ABOVE AVG"
                elif pct >= 40:
                    badge_color, badge_label = "#f59e0b", "AVERAGE"
                elif pct >= 20:
                    badge_color, badge_label = "#059669", "BELOW AVG"
                else:
                    badge_color, badge_label = "#2563eb", "CHEAP"
            v_str = f"{cur_v:.1f}x" if cur_v is not None else "N/A"
            pct_str = f"{pct:.0f}th pctile" if pct is not None else ""
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.92); padding: 1rem;
                        border-radius: 0.75rem; border: 1px solid {badge_color}55;
                        text-align: center;">
                <div style="color: #64748b; font-size: 0.7rem; letter-spacing: 0.1em;
                            text-transform: uppercase; font-family: 'JetBrains Mono', monospace;">
                    {m}
                </div>
                <div style="color: #1e293b; font-family: 'JetBrains Mono', monospace;
                            font-size: 1.6rem; font-weight: 700; margin: 0.3rem 0;">
                    {v_str}
                </div>
                <div style="color: {badge_color}; font-family: 'JetBrains Mono', monospace;
                            font-size: 0.7rem; letter-spacing: 0.1em; font-weight: 600;">
                    {badge_label}
                </div>
                <div style="color: #64748b; font-family: 'JetBrains Mono', monospace;
                            font-size: 0.65rem;">
                    {pct_str}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### History")
    g1, g2 = st.columns(2)
    g1.plotly_chart(_band_chart(df, "P/E", cur.get("P/E"), data["currency"]),
                    use_container_width=True)
    g2.plotly_chart(_band_chart(df, "P/S", cur.get("P/S"), data["currency"]),
                    use_container_width=True)
    g3, g4 = st.columns(2)
    g3.plotly_chart(_band_chart(df, "EV/EBITDA", cur.get("EV/EBITDA"),
                                 data["currency"]),
                    use_container_width=True)
    g4.plotly_chart(_band_chart(df, "P/FCF", cur.get("P/FCF"),
                                 data["currency"]),
                    use_container_width=True)

    with st.expander("Raw data"):
        show_df = df.copy()
        for c in ["price", "market_cap", "revenue", "net_income", "ebitda", "fcf"]:
            if c in show_df.columns:
                show_df[c] = show_df[c].apply(
                    lambda v: f"{v:,.0f}" if v is not None and v == v else "—"
                )
        for c in metrics:
            show_df[c] = show_df[c].apply(
                lambda v: f"{v:.1f}x" if v is not None and v == v else "—"
            )
        st.dataframe(show_df, hide_index=True, use_container_width=True)

    with st.expander("Methodology"):
        st.markdown("""
**Historical multiples.** For each of the last 10 fiscal year-ends:
- **P/E** = (Market Cap at FY-end) / Net Income
- **P/S** = (Market Cap at FY-end) / Revenue
- **EV/EBITDA** = (Market Cap + Debt − Cash) / EBITDA
- **P/FCF** = (Market Cap at FY-end) / FCF (CFO + CapEx)

The current value is overlaid as a yellow line; quartile reference lines (25th/50th/75th) are shown. The badge classifies the current value's percentile within its own 10y history — `EXPENSIVE` means trading rich vs its history; `CHEAP` means trading at a discount.

**Caveats.** Negative earnings periods are excluded (multiples undefined). Industry shifts and one-offs can distort history; always check the underlying data.
        """)
