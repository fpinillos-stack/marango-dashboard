"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — VALUATION MODULE (Reverse DCF)
═══════════════════════════════════════════════════════════════
Two-stage Reverse DCF powered by EODHD fundamentals.
Inspired by AlphaMarketTools' /companies/[ticker] surface.
"""
from __future__ import annotations

import os
import streamlit as st
import pandas as pd
import requests


EODHD_BASE = "https://eodhd.com/api"


# ============================================
# EODHD CLIENT
# ============================================

def _eodhd_key() -> str:
    """Read EODHD API key from Streamlit secrets or environment."""
    try:
        k = st.secrets.get("EODHD_API_KEY", "")
    except Exception:
        k = ""
    return k or os.environ.get("EODHD_API_KEY", "")


def _normalize_ticker(ticker: str) -> str:
    """Append .US suffix if no exchange suffix is present."""
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    if "." not in t:
        t = f"{t}.US"
    return t


@st.cache_data(ttl=3600, show_spinner=False)
def eodhd_fundamentals(ticker: str) -> dict:
    """Fetch fundamentals from EODHD. Returns {'_error': ...} on failure."""
    key = _eodhd_key()
    if not key:
        return {"_error": "no_api_key"}
    t = _normalize_ticker(ticker)
    if not t:
        return {"_error": "empty_ticker"}
    url = f"{EODHD_BASE}/fundamentals/{t}"
    try:
        r = requests.get(url, params={"api_token": key}, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            return {"_error": f"unexpected_response_type: {type(data).__name__}"}
        return data
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:200]}"}


@st.cache_data(ttl=900, show_spinner=False)
def eodhd_real_time(ticker: str) -> dict:
    """Fetch real-time quote from EODHD."""
    key = _eodhd_key()
    if not key:
        return {"_error": "no_api_key"}
    t = _normalize_ticker(ticker)
    url = f"{EODHD_BASE}/real-time/{t}"
    try:
        r = requests.get(url, params={"api_token": key, "fmt": "json"}, timeout=15)
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:200]}"}


# ============================================
# REVERSE DCF — TWO-STAGE MODEL
# ============================================

def reverse_dcf_implied_growth(price, eps0, horizon_years,
                                terminal_pe=15.0, cost_of_equity=0.10,
                                tol=1e-4, max_iter=200):
    """
    Two-stage Reverse DCF — solve for the constant EPS growth rate g such that:

        Price = Σ_{t=1..H} [EPS₀·(1+g)^t / (1+r)^t]
              + TerminalPE · EPS₀·(1+g)^H / (1+r)^H

    where r = cost_of_equity, H = horizon_years.

    Returns implied annualised growth as decimal (e.g. 0.15 = 15%), or None.
    """
    try:
        if eps0 is None or price is None:
            return None
        eps0 = float(eps0)
        price = float(price)
        if eps0 <= 0 or price <= 0:
            return None
    except Exception:
        return None

    r = float(cost_of_equity)
    H = int(horizon_years)
    tpe = float(terminal_pe)

    def pv(g):
        total = 0.0
        for t in range(1, H + 1):
            total += eps0 * (1 + g) ** t / (1 + r) ** t
        eps_h = eps0 * (1 + g) ** H
        terminal = tpe * eps_h / (1 + r) ** H
        return total + terminal

    lo, hi = -0.50, 2.00
    f_lo = pv(lo) - price
    f_hi = pv(hi) - price
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if f_lo * f_hi > 0:
        return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = pv(mid) - price
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid
    return (lo + hi) / 2


def reverse_dcf_classify(g):
    """Return (label, hex_color) classifying implied growth."""
    if g is None:
        return ("N/A", "#64748b")
    if g > 0.25:
        return ("HEROIC", "#dc2626")
    if g > 0.15:
        return ("DEMANDING", "#ea580c")
    if g > 0.08:
        return ("REASONABLE", "#059669")
    if g > 0.0:
        return ("CHEAP", "#2563eb")
    return ("DEEP VALUE", "#7c3aed")


def _eps_and_price_from_eodhd(fund: dict, rt: dict):
    """Extract trailing EPS and current price from EODHD payloads."""
    price = None
    eps = None
    try:
        c = rt.get("close")
        if c not in (None, "NA", "", "null"):
            price = float(c)
    except Exception:
        pass
    if price is None or price == 0:
        try:
            mc = fund.get("Highlights", {}).get("MarketCapitalization")
            so = fund.get("SharesStats", {}).get("SharesOutstanding")
            if mc and so:
                price = float(mc) / float(so)
        except Exception:
            pass
    try:
        eps_raw = fund.get("Highlights", {}).get("EarningsShare")
        if eps_raw not in (None, "NA", "", "null"):
            eps = float(eps_raw)
    except Exception:
        pass
    return eps, price


# ============================================
# UI — VALUATION TAB
# ============================================

def display_valuation_tab():
    """Reverse DCF — implied EPS growth at 3y/5y/10y horizons."""
    st.markdown("""
    <div style="margin: 1rem 0 1.5rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #ea580c;
                    font-size: 1.5rem; font-weight: 700; letter-spacing: 0.05em;">
            REVERSE DCF
        </div>
        <div style="color: #64748b; font-size: 0.85rem; letter-spacing: 0.05em;
                    text-transform: uppercase;">
            Implied EPS growth · Two-stage model · Powered by EODHD
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not _eodhd_key():
        st.warning("EODHD_API_KEY not configured.")
        st.caption("Add this line to `.streamlit/secrets.toml` (and to Streamlit Cloud → Settings → Secrets):")
        st.code('EODHD_API_KEY = "your_eodhd_token_here"', language="toml")
        return

    col_in1, col_in2, col_in3, col_in4 = st.columns([2, 1, 1, 1])
    with col_in1:
        ticker = st.text_input(
            "Ticker",
            value="AAPL",
            help="e.g. AAPL, MSFT, AMZN. .US suffix is auto-applied to US stocks.",
            key="rev_dcf_ticker",
        ).upper().strip()
    with col_in2:
        terminal_pe = st.slider("Terminal P/E", 8.0, 25.0, 15.0, 0.5, key="rev_dcf_tpe")
    with col_in3:
        coe = st.slider("Cost of Equity", 0.06, 0.15, 0.10, 0.005,
                        format="%.3f", key="rev_dcf_coe")
    with col_in4:
        st.write("")
        st.write("")
        st.button("RUN", use_container_width=True, type="primary", key="rev_dcf_run")

    if not ticker:
        st.info("Enter a ticker to compute implied growth.")
        return

    with st.spinner(f"Fetching {ticker} from EODHD…"):
        fund = eodhd_fundamentals(ticker)
        rt = eodhd_real_time(ticker)

    if "_error" in fund:
        st.error(f"Fundamentals error for {ticker}: {fund['_error']}")
        return
    if "_error" in rt:
        st.warning(f"Real-time price unavailable: {rt['_error']}. Using fundamentals fallback.")

    eps, price = _eps_and_price_from_eodhd(fund, rt)
    if eps is None or price is None:
        st.error(f"Could not extract EPS/price for {ticker}. EPS={eps}, Price={price}")
        with st.expander("Raw EODHD payload (debug)"):
            st.json({"Highlights": fund.get("Highlights"), "real_time": rt})
        return

    pe = price / eps if eps > 0 else None
    name = (fund.get("General") or {}).get("Name", ticker)
    sector = (fund.get("General") or {}).get("Sector", "—")
    industry = (fund.get("General") or {}).get("Industry", "—")
    currency = (fund.get("General") or {}).get("CurrencyCode", "USD")

    st.markdown(f"""
    <div style="margin: 0.5rem 0 1rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #1e293b;
                    font-size: 1.1rem; font-weight: 600;">{name}</div>
        <div style="color: #64748b; font-size: 0.8rem;">
            {sector} · {industry} · {currency}
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Price", f"{price:,.2f} {currency}")
    with c2:
        st.metric("EPS (TTM)", f"{eps:,.2f}")
    with c3:
        pe_str = f"{pe:.1f}x" if (pe is not None and pe > 0) else "N/A"
        st.metric("P/E", pe_str)
    with c4:
        st.metric("Terminal P/E", f"{terminal_pe:.1f}x")

    if eps <= 0:
        st.warning("EPS is zero or negative — Reverse DCF assumes positive earnings. "
                   "Try a profitable company or wait until EPS turns positive.")
        return

    g3 = reverse_dcf_implied_growth(price, eps, 3, terminal_pe, coe)
    g5 = reverse_dcf_implied_growth(price, eps, 5, terminal_pe, coe)
    g10 = reverse_dcf_implied_growth(price, eps, 10, terminal_pe, coe)

    st.markdown("### Implied EPS growth (annualised)")
    cc1, cc2, cc3 = st.columns(3)
    for col, label, g in [(cc1, "3-YEAR", g3), (cc2, "5-YEAR", g5), (cc3, "10-YEAR", g10)]:
        with col:
            cls_label, cls_color = reverse_dcf_classify(g)
            g_str = f"{g*100:+.1f}%" if g is not None else "N/A"
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.92); padding: 1.5rem;
                        border-radius: 0.75rem; border: 1px solid {cls_color}55;
                        text-align: center; backdrop-filter: blur(12px);">
                <div style="color: #64748b; font-size: 0.7rem; letter-spacing: 0.15em;
                            text-transform: uppercase; font-family: 'JetBrains Mono', monospace;">
                    {label} HORIZON
                </div>
                <div style="color: {cls_color}; font-family: 'JetBrains Mono', monospace;
                            font-size: 2.5rem; font-weight: 700; margin: 0.5rem 0;
                            letter-spacing: -0.02em;">
                    {g_str}
                </div>
                <div style="color: {cls_color}; font-family: 'JetBrains Mono', monospace;
                            font-size: 0.8rem; letter-spacing: 0.15em; font-weight: 600;">
                    {cls_label}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Sensitivity — 5-year implied growth")
    st.caption("Rows = Cost of Equity · Columns = Terminal P/E")
    pe_grid = [10, 12, 15, 18, 20, 25]
    coe_grid = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
    rows = []
    for c in coe_grid:
        row = {"COE": f"{c*100:.0f}%"}
        for p in pe_grid:
            g = reverse_dcf_implied_growth(price, eps, 5, p, c)
            row[f"P/E {p}x"] = f"{g*100:+.1f}%" if g is not None else "—"
        rows.append(row)
    sens_df = pd.DataFrame(rows)
    st.dataframe(sens_df, hide_index=True, use_container_width=True)

    with st.expander("Methodology"):
        st.markdown("""
**Two-stage Reverse DCF.** Solves for the constant EPS growth rate `g`
that justifies today's price under these assumptions:

1. EPS grows at `g` for `H` years
2. At year `H`, the multiple reverts to a fair Terminal P/E
3. Future cash flows discounted at Cost of Equity

```
Price = Σ [EPS₀·(1+g)ᵗ / (1+r)ᵗ]  +  TerminalPE · EPS_H / (1+r)^H
```

`g` is solved via bisection. Higher implied `g` = market is demanding more growth.

**Reading the badges:**
- `DEEP VALUE` (g ≤ 0%) — market pricing in decline
- `CHEAP` (0–8%) — modest growth expectations
- `REASONABLE` (8–15%) — solid but achievable
- `DEMANDING` (15–25%) — needs strong execution
- `HEROIC` (>25%) — bar is very high

Inspired by AlphaMarketTools' Reverse DCF surface.
        """)
