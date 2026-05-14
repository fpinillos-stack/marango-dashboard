"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — QUALITY SCORES MODULE
═══════════════════════════════════════════════════════════════
Three academic financial quality scores computed from EODHD
fundamentals:

  · Piotroski F-Score (9 points) — financial strength signal
  · Altman Z-Score          — bankruptcy / distress signal
  · Beneish M-Score (8 var) — earnings manipulation signal
"""
from __future__ import annotations

import os
import math

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
def _fundamentals_q(ticker: str) -> dict:
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


def _last_two_years(period_dict: dict):
    """Return (curr_dict, prev_dict) for the two most recent fiscal years."""
    if not isinstance(period_dict, dict):
        return None, None
    dates = sorted(period_dict.keys(), reverse=True)
    if len(dates) < 2:
        return (period_dict.get(dates[0]) if dates else None), None
    return period_dict.get(dates[0]), period_dict.get(dates[1])


# ============================================
# PIOTROSKI F-SCORE
# ============================================

def piotroski_f_score(fund: dict) -> dict:
    """
    9-point Piotroski F-Score. Each criterion = 1 point if passed.
    Returns dict with details and total score.
    """
    inc = ((fund.get("Financials") or {}).get("Income_Statement") or {}).get("yearly") or {}
    bs = ((fund.get("Financials") or {}).get("Balance_Sheet") or {}).get("yearly") or {}
    cf = ((fund.get("Financials") or {}).get("Cash_Flow") or {}).get("yearly") or {}

    i0, i1 = _last_two_years(inc)
    b0, b1 = _last_two_years(bs)
    c0, c1 = _last_two_years(cf)

    if not all([i0, i1, b0, b1, c0]):
        return {"ok": False, "error": "Insufficient annual data for Piotroski (need 2y)."}

    # Pull metrics
    ni0, ni1 = _f(i0.get("netIncome")), _f(i1.get("netIncome"))
    rev0, rev1 = _f(i0.get("totalRevenue")), _f(i1.get("totalRevenue"))
    gp0, gp1 = _f(i0.get("grossProfit")), _f(i1.get("grossProfit"))
    ta0, ta1 = _f(b0.get("totalAssets")), _f(b1.get("totalAssets"))
    ltd0, ltd1 = _f(b0.get("longTermDebt")), _f(b1.get("longTermDebt"))
    ca0, ca1 = _f(b0.get("totalCurrentAssets")), _f(b1.get("totalCurrentAssets"))
    cl0, cl1 = _f(b0.get("totalCurrentLiabilities")), _f(b1.get("totalCurrentLiabilities"))
    shares0 = _f(b0.get("commonStockSharesOutstanding"))
    shares1 = _f(b1.get("commonStockSharesOutstanding"))
    cfo0 = _f(c0.get("totalCashFromOperatingActivities"))

    checks = []

    def add(label, cond, detail=""):
        passed = bool(cond) if cond is not None else False
        checks.append({"criterion": label, "passed": passed, "detail": detail})

    # PROFITABILITY (4)
    add("Net Income > 0", (ni0 is not None and ni0 > 0),
        f"NI = {ni0:,.0f}" if ni0 is not None else "n/a")
    add("Operating CF > 0", (cfo0 is not None and cfo0 > 0),
        f"CFO = {cfo0:,.0f}" if cfo0 is not None else "n/a")

    roa0 = (ni0 / ta0) if (ni0 is not None and ta0 not in (None, 0)) else None
    roa1 = (ni1 / ta1) if (ni1 is not None and ta1 not in (None, 0)) else None
    add("ROA improving YoY",
        (roa0 is not None and roa1 is not None and roa0 > roa1),
        f"ROA {roa0*100:.1f}% vs {roa1*100:.1f}%" if (roa0 is not None and roa1 is not None) else "n/a")

    accruals_ok = (cfo0 is not None and ni0 is not None and cfo0 > ni0)
    add("CFO > Net Income (quality)", accruals_ok,
        f"CFO {cfo0:,.0f} vs NI {ni0:,.0f}" if (cfo0 is not None and ni0 is not None) else "n/a")

    # LEVERAGE / LIQUIDITY / SOURCE OF FUNDS (3)
    ltd_ok = (ltd0 is not None and ltd1 is not None and ltd0 < ltd1)
    add("LT Debt decreasing YoY", ltd_ok,
        f"LTD {ltd0:,.0f} vs {ltd1:,.0f}" if (ltd0 is not None and ltd1 is not None) else "n/a")

    cr0 = (ca0 / cl0) if (ca0 is not None and cl0 not in (None, 0)) else None
    cr1 = (ca1 / cl1) if (ca1 is not None and cl1 not in (None, 0)) else None
    add("Current Ratio improving",
        (cr0 is not None and cr1 is not None and cr0 > cr1),
        f"CR {cr0:.2f} vs {cr1:.2f}" if (cr0 is not None and cr1 is not None) else "n/a")

    shares_ok = (shares0 is not None and shares1 is not None and shares0 <= shares1 * 1.01)
    add("No share issuance", shares_ok,
        f"Shares {shares0:,.0f} vs {shares1:,.0f}" if (shares0 is not None and shares1 is not None) else "n/a")

    # OPERATING EFFICIENCY (2)
    gm0 = (gp0 / rev0) if (gp0 is not None and rev0 not in (None, 0)) else None
    gm1 = (gp1 / rev1) if (gp1 is not None and rev1 not in (None, 0)) else None
    add("Gross Margin improving",
        (gm0 is not None and gm1 is not None and gm0 > gm1),
        f"GM {gm0*100:.1f}% vs {gm1*100:.1f}%" if (gm0 is not None and gm1 is not None) else "n/a")

    at0 = (rev0 / ta0) if (rev0 is not None and ta0 not in (None, 0)) else None
    at1 = (rev1 / ta1) if (rev1 is not None and ta1 not in (None, 0)) else None
    add("Asset Turnover improving",
        (at0 is not None and at1 is not None and at0 > at1),
        f"AT {at0:.2f} vs {at1:.2f}" if (at0 is not None and at1 is not None) else "n/a")

    total = sum(1 for c in checks if c["passed"])
    return {"ok": True, "score": total, "max": 9, "checks": checks}


# ============================================
# ALTMAN Z-SCORE
# ============================================

def altman_z_score(fund: dict) -> dict:
    """
    Altman Z-Score (public manufacturer formula):
    Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
    where:
      A = Working Capital / Total Assets
      B = Retained Earnings / Total Assets
      C = EBIT / Total Assets
      D = Market Cap / Total Liabilities
      E = Sales / Total Assets
    """
    inc = ((fund.get("Financials") or {}).get("Income_Statement") or {}).get("yearly") or {}
    bs = ((fund.get("Financials") or {}).get("Balance_Sheet") or {}).get("yearly") or {}
    hl = fund.get("Highlights") or {}

    i0, _ = _last_two_years(inc)
    b0, _ = _last_two_years(bs)

    if not all([i0, b0]):
        return {"ok": False, "error": "Insufficient data for Altman Z."}

    ta = _f(b0.get("totalAssets"))
    tl = _f(b0.get("totalLiab"))
    re = _f(b0.get("retainedEarnings"))
    ca = _f(b0.get("totalCurrentAssets"))
    cl = _f(b0.get("totalCurrentLiabilities"))
    rev = _f(i0.get("totalRevenue"))
    op_inc = _f(i0.get("operatingIncome"))
    ebit = op_inc  # approximation
    mcap = _f(hl.get("MarketCapitalization"))

    if not all([ta and ta > 0, tl and tl > 0, ca is not None, cl is not None,
                re is not None, ebit is not None, rev is not None, mcap and mcap > 0]):
        return {"ok": False, "error": "Required fields missing for Altman Z."}

    wc = ca - cl
    A = wc / ta
    B = re / ta
    C = ebit / ta
    D = mcap / tl
    E = rev / ta

    z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E

    if z > 2.99:
        zone = "SAFE"
        color = "#059669"
    elif z >= 1.81:
        zone = "GREY"
        color = "#ea580c"
    else:
        zone = "DISTRESS"
        color = "#dc2626"

    return {
        "ok": True,
        "z": z,
        "zone": zone,
        "color": color,
        "components": {
            "WC/TA (A)": A, "RE/TA (B)": B,
            "EBIT/TA (C)": C, "MCap/TL (D)": D,
            "Sales/TA (E)": E,
        },
    }


# ============================================
# BENEISH M-SCORE
# ============================================

def beneish_m_score(fund: dict) -> dict:
    """
    Beneish M-Score (8 variables). M > -1.78 = likely manipulator.
    M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
    """
    inc = ((fund.get("Financials") or {}).get("Income_Statement") or {}).get("yearly") or {}
    bs = ((fund.get("Financials") or {}).get("Balance_Sheet") or {}).get("yearly") or {}
    cf = ((fund.get("Financials") or {}).get("Cash_Flow") or {}).get("yearly") or {}

    i0, i1 = _last_two_years(inc)
    b0, b1 = _last_two_years(bs)
    c0, _ = _last_two_years(cf)

    if not all([i0, i1, b0, b1, c0]):
        return {"ok": False, "error": "Insufficient data for Beneish M."}

    def g(d, k): return _f(d.get(k))

    # DSRI = (Receivables_t / Sales_t) / (Receivables_t-1 / Sales_t-1)
    rec0, rec1 = g(b0, "netReceivables"), g(b1, "netReceivables")
    rev0, rev1 = g(i0, "totalRevenue"), g(i1, "totalRevenue")
    if not all(x and x > 0 for x in [rec0, rec1, rev0, rev1]):
        return {"ok": False, "error": "Missing receivables/sales for DSRI."}
    dsri = (rec0 / rev0) / (rec1 / rev1)

    # GMI = GM_t-1 / GM_t
    gp0, gp1 = g(i0, "grossProfit"), g(i1, "grossProfit")
    if not all(x is not None for x in [gp0, gp1]):
        return {"ok": False, "error": "Missing gross profit for GMI."}
    gm0 = gp0 / rev0
    gm1 = gp1 / rev1
    if gm0 == 0:
        return {"ok": False, "error": "Gross margin zero — GMI undefined."}
    gmi = gm1 / gm0

    # AQI = ((1 - (CA + PPE)/TA)_t) / ((1 - (CA + PPE)/TA)_t-1)
    ca0, ca1 = g(b0, "totalCurrentAssets"), g(b1, "totalCurrentAssets")
    ppe0, ppe1 = g(b0, "propertyPlantEquipment"), g(b1, "propertyPlantEquipment")
    ta0, ta1 = g(b0, "totalAssets"), g(b1, "totalAssets")
    if not all(x is not None and x > 0 for x in [ta0, ta1]) or any(x is None for x in [ca0, ca1, ppe0, ppe1]):
        return {"ok": False, "error": "Missing balance sheet items for AQI."}
    aqi_num = 1 - (ca0 + ppe0) / ta0
    aqi_den = 1 - (ca1 + ppe1) / ta1
    aqi = aqi_num / aqi_den if aqi_den != 0 else 1.0

    # SGI = Sales_t / Sales_t-1
    sgi = rev0 / rev1

    # DEPI = (D&A_t-1 / (D&A_t-1 + PPE_t-1)) / (D&A_t / (D&A_t + PPE_t))
    da0, da1 = g(i0, "depreciationAndAmortization"), g(i1, "depreciationAndAmortization")
    if not all(x is not None and x >= 0 for x in [da0, da1]):
        return {"ok": False, "error": "Missing D&A for DEPI."}
    depi_num = da1 / (da1 + ppe1) if (da1 + ppe1) != 0 else 0
    depi_den = da0 / (da0 + ppe0) if (da0 + ppe0) != 0 else 0
    depi = depi_num / depi_den if depi_den != 0 else 1.0

    # SGAI = (SGA_t / Sales_t) / (SGA_t-1 / Sales_t-1)
    sga0, sga1 = g(i0, "sellingGeneralAdministrative"), g(i1, "sellingGeneralAdministrative")
    if sga0 is None or sga1 is None or sga1 == 0:
        sgai = 1.0
    else:
        sgai = (sga0 / rev0) / (sga1 / rev1)

    # LVGI = (LTD + CurrentLiab)_t / TA_t  ÷  (LTD + CurrentLiab)_t-1 / TA_t-1
    ltd0, ltd1 = g(b0, "longTermDebt") or 0, g(b1, "longTermDebt") or 0
    cl0, cl1 = g(b0, "totalCurrentLiabilities") or 0, g(b1, "totalCurrentLiabilities") or 0
    lvgi_num = (ltd0 + cl0) / ta0
    lvgi_den = (ltd1 + cl1) / ta1
    lvgi = lvgi_num / lvgi_den if lvgi_den != 0 else 1.0

    # TATA = (NI - CFO) / TA
    ni0 = g(i0, "netIncome")
    cfo0 = g(c0, "totalCashFromOperatingActivities")
    if ni0 is None or cfo0 is None:
        return {"ok": False, "error": "Missing NI/CFO for TATA."}
    tata = (ni0 - cfo0) / ta0

    m = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
         + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)

    if m > -1.78:
        zone = "LIKELY MANIPULATOR"
        color = "#dc2626"
    elif m > -2.22:
        zone = "GREY"
        color = "#ea580c"
    else:
        zone = "UNLIKELY"
        color = "#059669"

    return {
        "ok": True,
        "m": m,
        "zone": zone,
        "color": color,
        "components": {
            "DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi,
            "DEPI": depi, "SGAI": sgai, "LVGI": lvgi, "TATA": tata,
        },
    }


# ============================================
# UI
# ============================================

def _piotroski_color(score):
    if score is None:
        return "#64748b"
    if score >= 7:
        return "#059669"
    if score >= 4:
        return "#ea580c"
    return "#dc2626"


def _piotroski_label(score):
    if score is None:
        return "N/A"
    if score >= 7:
        return "STRONG"
    if score >= 4:
        return "MIXED"
    return "WEAK"


def display_quality_tab():
    """Quality scores tab — Piotroski, Altman, Beneish."""
    st.markdown("""
    <div style="margin: 1rem 0 1.5rem 0;">
        <div style="font-family: 'JetBrains Mono', monospace; color: #ea580c;
                    font-size: 1.5rem; font-weight: 700; letter-spacing: 0.05em;">
            QUALITY SCORES
        </div>
        <div style="color: #64748b; font-size: 0.85rem; letter-spacing: 0.05em;
                    text-transform: uppercase;">
            Piotroski F · Altman Z · Beneish M · Powered by EODHD
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not _eodhd_key():
        st.warning("EODHD_API_KEY not configured.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Ticker", value="AAPL",
                               key="q_ticker").upper().strip()
    with col2:
        st.write("")
        st.write("")
        st.button("RUN", use_container_width=True, type="primary", key="q_run")

    if not ticker:
        return

    with st.spinner(f"Fetching {ticker}…"):
        fund = _fundamentals_q(ticker)
    if "_error" in fund:
        st.error(fund["_error"])
        return

    name = (fund.get("General") or {}).get("Name", ticker)
    st.markdown(f"**{name}**")

    piotroski = piotroski_f_score(fund)
    altman = altman_z_score(fund)
    beneish = beneish_m_score(fund)

    c1, c2, c3 = st.columns(3)

    with c1:
        if piotroski["ok"]:
            sc, mx = piotroski["score"], piotroski["max"]
            col = _piotroski_color(sc)
            lbl = _piotroski_label(sc)
        else:
            sc, mx, col, lbl = "—", 9, "#64748b", "ERROR"
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.92); padding: 1.2rem;
                    border-radius: 0.75rem; border: 1px solid {col}55;
                    text-align: center;">
            <div style="color: #64748b; font-size: 0.7rem; letter-spacing: 0.1em;
                        text-transform: uppercase; font-family: 'JetBrains Mono', monospace;">
                PIOTROSKI F
            </div>
            <div style="color: {col}; font-family: 'JetBrains Mono', monospace;
                        font-size: 2.5rem; font-weight: 700;">
                {sc}<span style="font-size:1.2rem; color: #64748b;">/{mx}</span>
            </div>
            <div style="color: {col}; font-family: 'JetBrains Mono', monospace;
                        font-size: 0.75rem; letter-spacing: 0.15em; font-weight: 600;">
                {lbl}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        if altman["ok"]:
            z = altman["z"]; zone = altman["zone"]; col = altman["color"]
            z_str = f"{z:.2f}"
        else:
            z_str, zone, col = "—", "ERROR", "#64748b"
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.92); padding: 1.2rem;
                    border-radius: 0.75rem; border: 1px solid {col}55;
                    text-align: center;">
            <div style="color: #64748b; font-size: 0.7rem; letter-spacing: 0.1em;
                        text-transform: uppercase; font-family: 'JetBrains Mono', monospace;">
                ALTMAN Z
            </div>
            <div style="color: {col}; font-family: 'JetBrains Mono', monospace;
                        font-size: 2.5rem; font-weight: 700;">
                {z_str}
            </div>
            <div style="color: {col}; font-family: 'JetBrains Mono', monospace;
                        font-size: 0.75rem; letter-spacing: 0.15em; font-weight: 600;">
                {zone}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        if beneish["ok"]:
            m = beneish["m"]; zone = beneish["zone"]; col = beneish["color"]
            m_str = f"{m:.2f}"
        else:
            m_str, zone, col = "—", "ERROR", "#64748b"
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.92); padding: 1.2rem;
                    border-radius: 0.75rem; border: 1px solid {col}55;
                    text-align: center;">
            <div style="color: #64748b; font-size: 0.7rem; letter-spacing: 0.1em;
                        text-transform: uppercase; font-family: 'JetBrains Mono', monospace;">
                BENEISH M
            </div>
            <div style="color: {col}; font-family: 'JetBrains Mono', monospace;
                        font-size: 2.5rem; font-weight: 700;">
                {m_str}
            </div>
            <div style="color: {col}; font-family: 'JetBrains Mono', monospace;
                        font-size: 0.65rem; letter-spacing: 0.1em; font-weight: 600;">
                {zone}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Details
    st.markdown("### Piotroski F-Score breakdown")
    if piotroski.get("ok"):
        rows = [{
            "Criterion": c["criterion"],
            "Pass": "✓" if c["passed"] else "✗",
            "Detail": c["detail"],
        } for c in piotroski["checks"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.warning(piotroski.get("error", "n/a"))

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("### Altman Z components")
        if altman.get("ok"):
            rows = [{"Variable": k, "Value": f"{v:.3f}"}
                    for k, v in altman["components"].items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True,
                         use_container_width=True)
        else:
            st.warning(altman.get("error", "n/a"))
    with cc2:
        st.markdown("### Beneish M components")
        if beneish.get("ok"):
            rows = [{"Variable": k, "Value": f"{v:.3f}"}
                    for k, v in beneish["components"].items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True,
                         use_container_width=True)
        else:
            st.warning(beneish.get("error", "n/a"))

    with st.expander("Methodology"):
        st.markdown("""
**Piotroski F-Score (0-9).** 9 binary checks across profitability, leverage, and operating efficiency. Higher = stronger fundamentals. `≥7` is strong, `≤3` is weak.

**Altman Z-Score.** Predictor of bankruptcy risk for manufacturers:
- `Z > 2.99` = Safe zone
- `1.81 ≤ Z ≤ 2.99` = Grey zone
- `Z < 1.81` = Distress zone

Less reliable for banks, REITs, and asset-light tech firms.

**Beneish M-Score.** Detects earnings manipulation through 8 financial ratios. `M > -1.78` suggests potential manipulation; `M < -2.22` is unlikely. Note: this is a STATISTICAL signal — not proof of fraud. Use as a red flag for further investigation.
        """)
