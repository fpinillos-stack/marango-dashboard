"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — PORTFOLIO ENGINE
═══════════════════════════════════════════════════════════════
Replicates the Bloque 1 sector-adjusted scoring model using live
EODHD fundamentals — no Excel dependency.

Pipeline: 18 metrics → sector scoring (T1-T6 thresholds) →
6 pillars (sector-weighted) → SA Score → SIGNAL.
"""
from __future__ import annotations

import os
import math

import streamlit as st
import pandas as pd
import requests

from scoring_params import PILLAR_WEIGHTS, SUB_WEIGHTS, METRIC_THRESHOLDS

EODHD_BASE = "https://eodhd.com/api"
SCORE_FLOOR = 5.0

# ───────────────────────────────────────────────────────────────
# UNIVERSE — company → (ticker, GICS sector, is_marango_holding)
# 97 from the Bloque 1 Excel + Schrödinger (Marango holding).
# ───────────────────────────────────────────────────────────────
UNIVERSE = {
    "NVIDIA Corp": ("NVDA.US", "Information Technology", True),
    "Johnson & Johnson": ("JNJ.US", "Health Care", False),
    "Exxon Mobil Corp": ("XOM.US", "Energy", False),
    "Berkshire Hathaway": ("BRK-B.US", "Financials", False),
    "NextEra Energy": ("NEE.US", "Utilities", False),
    "Apple Inc": ("AAPL.US", "Information Technology", False),
    "Amazon.com Inc": ("AMZN.US", "Consumer Discretionary", True),
    "Alphabet Inc": ("GOOGL.US", "Communication Services", True),
    "Procter & Gamble": ("PG.US", "Consumer Staples", False),
    "Caterpillar Inc": ("CAT.US", "Industrials", False),
    "Linde plc": ("LIN.US", "Materials", False),
    "Prologis Inc": ("PLD.US", "Real Estate", False),
    "UnitedHealth Group": ("UNH.US", "Health Care", False),
    "JPMorgan Chase": ("JPM.US", "Financials", False),
    "Chevron Corp": ("CVX.US", "Energy", False),
    "Microsoft Corp": ("MSFT.US", "Information Technology", True),
    "Visa Inc": ("V.US", "Financials", True),
    "Eli Lilly & Co": ("LLY.US", "Health Care", True),
    "McDonald's Corp": ("MCD.US", "Consumer Discretionary", False),
    "Costco Wholesale": ("COST.US", "Consumer Staples", False),
    "American Tower": ("AMT.US", "Real Estate", False),
    "Duke Energy": ("DUK.US", "Utilities", False),
    "Union Pacific": ("UNP.US", "Industrials", False),
    "Freeport-McMoRan": ("FCX.US", "Materials", False),
    "T-Mobile US": ("TMUS.US", "Communication Services", False),
    "Meta Platforms": ("META.US", "Communication Services", True),
    "AbbVie Inc": ("ABBV.US", "Health Care", False),
    "Texas Instruments": ("TXN.US", "Information Technology", False),
    "Home Depot": ("HD.US", "Consumer Discretionary", False),
    "Broadcom Inc": ("AVGO.US", "Information Technology", True),
    "Walmart Inc": ("WMT.US", "Consumer Staples", False),
    "ConocoPhillips": ("COP.US", "Energy", False),
    "Goldman Sachs": ("GS.US", "Financials", False),
    "Honeywell Intl": ("HON.US", "Industrials", False),
    "Southern Company": ("SO.US", "Utilities", False),
    "GE Vernova": ("GEV.US", "Industrials", False),
    "Bloom Energy": ("BE.US", "Industrials", True),
    "Vertiv Holdings": ("VRT.US", "Industrials", False),
    "Eaton Corp": ("ETN.US", "Industrials", False),
    "IREN Ltd": ("IREN.US", "Information Technology", True),
    "Core Scientific": ("CORZ.US", "Information Technology", False),
    "Kraken Robotics": ("PNG.TO", "Industrials", False),
    "Brookfield Corp": ("BN.US", "Financials", True),
    "S&P Global Inc": ("SPGI.US", "Financials", True),
    "Safran SA": ("SAF.PA", "Industrials", True),
    "General Electric Co": ("GE.US", "Industrials", True),
    "Taiwan Semiconductor": ("TSM.US", "Information Technology", True),
    "Moody's Corp": ("MCO.US", "Financials", True),
    "L'Oreal SA": ("OR.PA", "Consumer Staples", True),
    "Mastercard Inc": ("MA.US", "Financials", True),
    "Schneider Electric SE": ("SU.PA", "Industrials", True),
    "Stryker Corp": ("SYK.US", "Health Care", False),
    "Hermes International": ("RMS.PA", "Consumer Discretionary", True),
    "ASML Holding NV": ("ASML.US", "Information Technology", True),
    "Vinci SA": ("DG.PA", "Industrials", True),
    "Ferrovial SE": ("FER.MC", "Industrials", True),
    "Tesla Inc": ("TSLA.US", "Consumer Discretionary", True),
    "Intuitive Surgical Inc": ("ISRG.US", "Health Care", True),
    "IDEXX Laboratories Inc": ("IDXX.US", "Health Care", False),
    "AST SpaceMobile Inc": ("ASTS.US", "Communication Services", True),
    "Palantir Technologies Inc": ("PLTR.US", "Information Technology", False),
    "SK Hynix": ("000660.KO", "Information Technology", False),
    "Lumentum Holdings": ("LITE.US", "Information Technology", False),
    "ARISTA Networks": ("ANET.US", "Information Technology", False),
    "Credo Technology": ("CRDO.US", "Information Technology", False),
    "Marvell Technology": ("MRVL.US", "Information Technology", False),
    "NBIUS Group": ("NBIS.US", "Information Technology", False),
    "Coherent": ("COHR.US", "Information Technology", False),
    "CoreWeave": ("CRWV.US", "Information Technology", False),
    "Lam Research": ("LRCX.US", "Information Technology", False),
    "Rocket Lab": ("RKLB.US", "Industrials", False),
    "Applied Optoelectronics": ("AAOI.US", "Information Technology", False),
    "Applied Materials": ("AMAT.US", "Information Technology", False),
    "EssilorLuxottica": ("EL.PA", "Health Care", False),
    "Intel Corporation": ("INTC.US", "Information Technology", False),
    "Astera Labs": ("ALAB.US", "Information Technology", False),
    "ARM Holdings": ("ARM.US", "Information Technology", False),
    "MercadoLibre": ("MELI.US", "Consumer Discretionary", False),
    "Robinhood Markets": ("HOOD.US", "Financials", False),
    "Cadence Design Systems": ("CDNS.US", "Information Technology", True),
    "Fair Isaac Corporation": ("FICO.US", "Information Technology", False),
    "Adyen NV": ("ADYEN.AS", "Financials", False),
    "MSCI": ("MSCI.US", "Financials", False),
    "Applovin Corporation": ("APP.US", "Communication Services", False),
    "Seagate Technology Holdings": ("STX.US", "Information Technology", False),
    "CrowdStrike": ("CRWD.US", "Information Technology", False),
    "Roper Technologies": ("ROP.US", "Information Technology", False),
    "CME Group": ("CME.US", "Financials", False),
    "Salesforce": ("CRM.US", "Information Technology", False),
    "Shopify": ("SHOP.US", "Information Technology", False),
    "Palo Alto Networks": ("PANW.US", "Information Technology", False),
    "ServiceNow": ("NOW.US", "Information Technology", False),
    "Prysmian SPA": ("PRY.MI", "Industrials", False),
    "Topicus.com": ("TOI.V", "Information Technology", False),
    "Fortinet": ("FTNT.US", "Information Technology", False),
    "Docusign": ("DOCU.US", "Information Technology", False),
    "Hims & Hers Health, Inc.": ("HIMS.US", "Health Care", False),
    "Schrodinger Inc": ("SDGR.US", "Health Care", True),
}

PILLAR_NAMES = {
    "P1": "Profitability", "P2": "Growth", "P3": "Fin. Strength",
    "P4": "Cash Flow", "P5": "Valuation", "P6": "Shareholder",
}

# metric_key → (Excel metric column, Excel sub-score column, value_is_percent)
EXCEL_COL_MAP = {
    "ROE": ("ROE (%)", "S.ROE", True),
    "ROIC": ("ROIC (%)", "S.ROIC", True),
    "NetMargin": ("Net Margin (%)", "S.NM", True),
    "RevGr3Y": ("Rev Gr 3Y (%)", "S.RevGr", True),
    "EPSGr3Y": ("EPS Gr 3Y (%)", "S.EPSGr", True),
    "OpLev": ("Op Lev (x)", "S.OpLev", False),
    "NDEBITDA": ("ND/EBITDA", "S.Debt", False),
    "CurrRatio": ("Curr Ratio", "S.CR", False),
    "IntCov": ("Int Cov (x)", "S.IC", False),
    "FCFMargin": ("FCF Mar (%)", "S.FCFm", True),
    "FCFNI": ("FCF/NI (x)", "S.FCFni", False),
    "CapexRev": ("Capex/Rev (%)", "S.Capex", True),
    "FwdPE": ("Fwd P/E", "S.PE", False),
    "EVEBITDA": ("EV/EBITDA", "S.EVEB", False),
    "PFCF": ("P/FCF", "S.PFCF", False),
    "DivYield": ("Div Yield (%)", "S.DivY", True),
    "Payout": ("Payout (%)", "S.Payout", True),
    "Buyback": ("Buyback (%)", "S.Buyb", True),
}


def _eodhd_key() -> str:
    try:
        k = st.secrets.get("EODHD_API_KEY", "")
    except Exception:
        k = ""
    return k or os.environ.get("EODHD_API_KEY", "")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fundamentals(ticker: str) -> dict:
    """Fetch full fundamentals payload from EODHD (cached 24h)."""
    key = _eodhd_key()
    if not key:
        return {"_error": "no_api_key"}
    try:
        r = requests.get(f"{EODHD_BASE}/fundamentals/{ticker}",
                         params={"api_token": key}, timeout=25)
        r.raise_for_status()
        d = r.json()
        return d if isinstance(d, dict) else {"_error": "bad_response"}
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:150]}"}


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


def _latest_years(period_dict, n=5):
    if not isinstance(period_dict, dict):
        return []
    items = [(k, v) for k, v in period_dict.items() if isinstance(v, dict)]
    items.sort(key=lambda x: x[0], reverse=True)
    return items[:n]


# ───────────────────────────────────────────────────────────────
# 18-METRIC EXTRACTION
# ───────────────────────────────────────────────────────────────

def compute_metrics(fund: dict) -> dict:
    """Extract the 18 scoring metrics from an EODHD fundamentals payload."""
    hl = fund.get("Highlights") or {}
    val = fund.get("Valuation") or {}
    sd = fund.get("SplitsDividends") or {}
    fin = fund.get("Financials") or {}
    inc_y = _latest_years((fin.get("Income_Statement") or {}).get("yearly") or {})
    bs_y = _latest_years((fin.get("Balance_Sheet") or {}).get("yearly") or {})
    cf_y = _latest_years((fin.get("Cash_Flow") or {}).get("yearly") or {})

    i0 = inc_y[0][1] if len(inc_y) > 0 else {}
    i1 = inc_y[1][1] if len(inc_y) > 1 else {}
    b0 = bs_y[0][1] if len(bs_y) > 0 else {}
    c0 = cf_y[0][1] if len(cf_y) > 0 else {}

    m = {}

    # --- P1: Profitability ---
    m["ROE"] = _f(hl.get("ReturnOnEquityTTM"))
    m["NetMargin"] = _f(hl.get("ProfitMargin"))

    op_inc = _f(i0.get("operatingIncome"))
    pretax = _f(i0.get("incomeBeforeTax"))
    tax = _f(i0.get("incomeTaxExpense"))
    tax_rate = (tax / pretax) if (tax is not None and pretax not in (None, 0) and pretax > 0) else 0.21
    tax_rate = min(max(tax_rate, 0.0), 0.50)
    equity = _f(b0.get("totalStockholderEquity"))
    ltd = _f(b0.get("longTermDebt")) or 0.0
    std = _f(b0.get("shortLongTermDebt")) or 0.0
    cash = _f(b0.get("cash")) or _f(b0.get("cashAndShortTermInvestments")) or 0.0
    if op_inc is not None and equity is not None:
        invested = equity + ltd + std - cash
        m["ROIC"] = (op_inc * (1 - tax_rate) / invested) if invested and invested > 0 else None
    else:
        m["ROIC"] = None

    # --- P2: Growth ---
    revs = [_f(r.get("totalRevenue")) for _, r in inc_y]
    nis = [_f(r.get("netIncome")) for _, r in inc_y]

    def _cagr(series, yrs):
        if len(series) > yrs and series[0] and series[yrs] and series[yrs] > 0 and series[0] > 0:
            return (series[0] / series[yrs]) ** (1.0 / yrs) - 1.0
        return None

    m["RevGr3Y"] = _cagr(revs, 3)
    m["EPSGr3Y"] = _cagr(nis, 3)

    oi0 = _f(i0.get("operatingIncome"))
    oi1 = _f(i1.get("operatingIncome"))
    rv0 = _f(i0.get("totalRevenue"))
    rv1 = _f(i1.get("totalRevenue"))
    if all(x is not None for x in [oi0, oi1, rv0, rv1]) and oi1 not in (0,) and rv1 not in (0,):
        d_oi = (oi0 - oi1) / abs(oi1)
        d_rv = (rv0 - rv1) / abs(rv1)
        m["OpLev"] = (d_oi / d_rv) if d_rv not in (0, None) else None
    else:
        m["OpLev"] = None

    # --- P3: Financial Strength ---
    ebitda = _f(i0.get("ebitda")) or _f(hl.get("EBITDA"))
    if ebitda is None and op_inc is not None:
        da = _f(i0.get("depreciationAndAmortization"))
        ebitda = (op_inc + da) if da is not None else None
    net_debt = (ltd + std) - cash
    m["NDEBITDA"] = (net_debt / ebitda) if (ebitda and ebitda > 0) else (0.0 if net_debt <= 0 else None)

    ca = _f(b0.get("totalCurrentAssets"))
    cl = _f(b0.get("totalCurrentLiabilities"))
    m["CurrRatio"] = (ca / cl) if (ca is not None and cl not in (None, 0)) else None

    int_exp = _f(i0.get("interestExpense"))
    if int_exp is not None and int_exp != 0 and op_inc is not None:
        m["IntCov"] = abs(op_inc / int_exp)
    else:
        m["IntCov"] = 25.0 if op_inc and op_inc > 0 else None

    # --- P4: Cash Flow ---
    cfo = _f(c0.get("totalCashFromOperatingActivities"))
    capex = _f(c0.get("capitalExpenditures"))
    fcf = (cfo + capex) if (cfo is not None and capex is not None) else None
    rev0 = revs[0] if revs else None
    ni0 = nis[0] if nis else None
    m["FCFMargin"] = (fcf / rev0) if (fcf is not None and rev0 and rev0 > 0) else None
    m["FCFNI"] = (fcf / ni0) if (fcf is not None and ni0 and ni0 > 0) else None
    m["CapexRev"] = (abs(capex) / rev0) if (capex is not None and rev0 and rev0 > 0) else None

    # --- P5: Valuation ---
    m["FwdPE"] = _f(val.get("ForwardPE")) or _f(hl.get("PERatio"))
    m["EVEBITDA"] = _f(val.get("EnterpriseValueEbitda")) or _f(hl.get("EVToEbitda"))
    mcap = _f(hl.get("MarketCapitalization"))
    m["PFCF"] = (mcap / fcf) if (mcap and fcf and fcf > 0) else None

    # --- P6: Shareholder ---
    m["DivYield"] = _f(hl.get("DividendYield")) or _f(sd.get("ForwardAnnualDividendYield")) or 0.0
    m["Payout"] = _f(sd.get("PayoutRatio")) or 0.0
    buyback_cf = _f(c0.get("salePurchaseOfStock"))
    if buyback_cf is not None and mcap and mcap > 0:
        m["Buyback"] = max(0.0, -buyback_cf) / mcap
    else:
        m["Buyback"] = 0.0

    return m


# ───────────────────────────────────────────────────────────────
# SECTOR SCORING
# ───────────────────────────────────────────────────────────────

def score_metric(value, sector: str, metric_key: str) -> float:
    """Map a raw metric value to 0-100 using sector T1-T6 thresholds."""
    if value is None:
        return 50.0
    table = METRIC_THRESHOLDS.get(metric_key, {})
    direction = table.get("direction", "higher")
    pairs = table.get(sector)
    if not pairs:
        return 50.0

    if direction == "higher":
        for t, s in pairs:
            if value >= t:
                return float(s)
        return SCORE_FLOOR
    elif direction == "lower":
        for t, s in pairs:
            if value <= t:
                return float(s)
        return SCORE_FLOOR
    else:  # sweetspot — interpolate along sorted threshold curve
        sp = sorted(pairs, key=lambda p: p[0])
        ts = [p[0] for p in sp]
        ss = [p[1] for p in sp]
        if value <= ts[0]:
            return float(ss[0])
        if value >= ts[-1]:
            return float(ss[-1])
        for i in range(len(ts) - 1):
            if ts[i] <= value <= ts[i + 1]:
                frac = (value - ts[i]) / (ts[i + 1] - ts[i]) if ts[i + 1] != ts[i] else 0
                return float(ss[i] + frac * (ss[i + 1] - ss[i]))
        return 50.0


def compute_pillars(metric_scores: dict, sector: str) -> dict:
    pillars = {}
    for pkey, subw in SUB_WEIGHTS.items():
        total_w = 0.0
        acc = 0.0
        for mkey, w in subw.items():
            sc = metric_scores.get(mkey)
            if sc is not None:
                acc += sc * w
                total_w += w
        pillars[pkey] = (acc / total_w) if total_w > 0 else 50.0
    return pillars


def compute_sa_score(pillars: dict, sector: str) -> float:
    weights = PILLAR_WEIGHTS.get(sector)
    if not weights:
        weights = {p: 1.0 / 6 for p in pillars}
    total_w = sum(weights.values())
    acc = sum(pillars.get(p, 50.0) * weights.get(p, 0) for p in weights)
    return acc / total_w if total_w > 0 else 50.0


def signal_from_score(score: float) -> str:
    if score >= 80:
        return "🚀 STRONG BUY"
    if score >= 70:
        return "✅ BUY"
    if score >= 60:
        return "⚠️ HOLD"
    if score >= 50:
        return "🟠 UNDERWEIGHT"
    return "🔴 SELL"


# ───────────────────────────────────────────────────────────────
# PORTFOLIO BUILD
# ───────────────────────────────────────────────────────────────

def score_one(company: str, ticker: str, sector: str, marango: bool) -> dict:
    """Fetch + score a single company. Returns a flat dict row."""
    fund = fetch_fundamentals(ticker)
    row = {
        "Company": company, "Ticker": ticker.split(".")[0],
        "GICS Sector": sector, "Marango_Holding": marango,
    }
    if "_error" in fund:
        row["_error"] = fund["_error"]
        row["Quality_Score"] = None
        return row

    metrics = compute_metrics(fund)
    mscores = {k: score_metric(metrics.get(k), sector, k) for k in METRIC_THRESHOLDS}
    pillars = compute_pillars(mscores, sector)
    sa = compute_sa_score(pillars, sector)

    row.update({
        "Quality_Score": round(sa, 1),
        "P1": round(pillars["P1"], 1), "P2": round(pillars["P2"], 1),
        "P3": round(pillars["P3"], 1), "P4": round(pillars["P4"], 1),
        "P5": round(pillars["P5"], 1), "P6": round(pillars["P6"], 1),
        "SIGNAL": signal_from_score(sa),
    })
    for k, v in metrics.items():
        row["m_" + k] = round(v, 4) if v is not None else None
    for mkey, (mcol, scol, is_pct) in EXCEL_COL_MAP.items():
        raw = metrics.get(mkey)
        if raw is None:
            row[mcol] = None
        elif is_pct:
            row[mcol] = round(raw * 100, 2)
        else:
            row[mcol] = round(raw, 3)
        row[scol] = round(mscores.get(mkey, 50.0), 1)
    return row


@st.cache_data(ttl=86400, show_spinner=False)
def build_portfolio() -> pd.DataFrame:
    """Score the whole universe from EODHD. Cached 24h."""
    rows = []
    for company, (ticker, sector, marango) in UNIVERSE.items():
        try:
            rows.append(score_one(company, ticker, sector, marango))
        except Exception as e:
            rows.append({
                "Company": company, "Ticker": ticker.split(".")[0],
                "GICS Sector": sector, "Marango_Holding": marango,
                "Quality_Score": None, "_error": type(e).__name__ + ": " + str(e),
            })
    return pd.DataFrame(rows)
