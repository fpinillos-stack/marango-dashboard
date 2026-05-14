"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — MOAT SCORE
═══════════════════════════════════════════════════════════════
Competitive-moat score (0-100) from EODHD fundamentals.
Inspired by AlphaMarketTools / Ingenio "Competitive Moat" panel.

Components:
  · Margin Trend      (25) — is gross margin expanding?
  · Margin Level      (25) — absolute gross margin = pricing power
  · R&D Intensity     (20) — investment in the moat
  · Margin Stability  (15) — operating-margin consistency
  · Return on Capital (15) — ROIC = durable advantage
"""
from __future__ import annotations

import math
import statistics


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


def _years(period_dict, n=5):
    if not isinstance(period_dict, dict):
        return []
    items = [(k, v) for k, v in period_dict.items() if isinstance(v, dict)]
    items.sort(key=lambda x: x[0], reverse=True)
    return items[:n]


def compute_moat(fund: dict) -> dict:
    """Return {ok, score, label, color, components:{name:(points,max,detail)}}."""
    if not isinstance(fund, dict) or "_error" in fund:
        return {"ok": False, "error": (fund or {}).get("_error", "no data")}

    fin = fund.get("Financials") or {}
    inc = _years((fin.get("Income_Statement") or {}).get("yearly") or {})
    bs = _years((fin.get("Balance_Sheet") or {}).get("yearly") or {})
    hl = fund.get("Highlights") or {}

    if len(inc) < 2:
        return {"ok": False, "error": "Insufficient income-statement history."}

    comp = {}

    # Gross margins per year (newest first)
    gms = []
    for _, r in inc:
        gp = _f(r.get("grossProfit"))
        rev = _f(r.get("totalRevenue"))
        gms.append((gp / rev) if (gp is not None and rev and rev > 0) else None)
    gms_valid = [g for g in gms if g is not None]

    # 1) Margin Trend (25) — newest vs oldest available gross margin
    if len(gms_valid) >= 2:
        newest, oldest = gms_valid[0], gms_valid[-1]
        delta_pp = (newest - oldest) * 100
        # +8pp → 25 ; flat → 12 ; -8pp → 2
        pts = max(0.0, min(25.0, 12.0 + delta_pp * 1.6))
        comp["Margin Trend"] = (round(pts, 1), 25,
                                "Gross margin {:.1f}% → {:.1f}% ({:+.1f}pp)".format(
                                    oldest * 100, newest * 100, delta_pp))
    else:
        comp["Margin Trend"] = (12.0, 25, "insufficient data — neutral")

    # 2) Margin Level (25) — absolute gross margin
    gm_now = gms_valid[0] if gms_valid else _f(hl.get("ProfitMargin"))
    if gm_now is not None:
        # 70%+ → 25 ; 50% → 18 ; 30% → 11 ; 10% → 4
        pts = max(0.0, min(25.0, gm_now * 100 * 0.36))
        comp["Margin Level"] = (round(pts, 1), 25,
                                "Gross margin {:.1f}%".format(gm_now * 100))
    else:
        comp["Margin Level"] = (12.0, 25, "no margin data — neutral")

    # 3) R&D Intensity (20) — R&D / revenue
    rd = _f(inc[0][1].get("researchDevelopment"))
    rev0 = _f(inc[0][1].get("totalRevenue"))
    if rd is not None and rev0 and rev0 > 0:
        rd_int = rd / rev0
        # 15%+ → 20 ; 8% → 13 ; 3% → 6 ; 0% → 2
        pts = max(2.0, min(20.0, rd_int * 100 * 1.33 + 2))
        comp["R&D Intensity"] = (round(pts, 1), 20,
                                 "R&D {:.1f}% of revenue".format(rd_int * 100))
    else:
        # No R&D line — common for financials/consumer; give a modest neutral
        comp["R&D Intensity"] = (8.0, 20, "no R&D line reported — neutral")

    # 4) Margin Stability (15) — operating-margin consistency
    op_margins = []
    for _, r in inc:
        oi = _f(r.get("operatingIncome"))
        rev = _f(r.get("totalRevenue"))
        if oi is not None and rev and rev > 0:
            op_margins.append(oi / rev)
    if len(op_margins) >= 3:
        sd = statistics.pstdev(op_margins)
        # sd 0 → 15 ; sd 5pp → ~9 ; sd 15pp → ~0
        pts = max(0.0, min(15.0, 15.0 - sd * 100))
        comp["Margin Stability"] = (round(pts, 1), 15,
                                    "Op-margin σ = {:.1f}pp".format(sd * 100))
    else:
        comp["Margin Stability"] = (7.5, 15, "insufficient history — neutral")

    # 5) Return on Capital (15) — ROIC proxy
    i0 = inc[0][1]
    b0 = bs[0][1] if bs else {}
    op_inc = _f(i0.get("operatingIncome"))
    pretax = _f(i0.get("incomeBeforeTax"))
    tax = _f(i0.get("incomeTaxExpense"))
    tax_rate = (tax / pretax) if (tax is not None and pretax and pretax > 0) else 0.21
    tax_rate = min(max(tax_rate, 0.0), 0.50)
    equity = _f(b0.get("totalStockholderEquity"))
    ltd = _f(b0.get("longTermDebt")) or 0.0
    std = _f(b0.get("shortLongTermDebt")) or 0.0
    cash = _f(b0.get("cash")) or _f(b0.get("cashAndShortTermInvestments")) or 0.0
    roic = None
    if op_inc is not None and equity is not None:
        invested = equity + ltd + std - cash
        if invested and invested > 0:
            roic = op_inc * (1 - tax_rate) / invested
    if roic is not None:
        # 30%+ → 15 ; 15% → 9 ; 8% → 5 ; 0% → 1
        pts = max(1.0, min(15.0, roic * 100 * 0.5))
        comp["Return on Capital"] = (round(pts, 1), 15,
                                     "ROIC {:.1f}%".format(roic * 100))
    else:
        comp["Return on Capital"] = (7.5, 15, "ROIC not computable — neutral")

    score = sum(v[0] for v in comp.values())
    if score >= 75:
        label, color = "WIDE MOAT", "#10b981"
    elif score >= 55:
        label, color = "NARROW MOAT", "#06b6d4"
    elif score >= 35:
        label, color = "LIMITED MOAT", "#f59e0b"
    else:
        label, color = "NO MOAT", "#ef4444"

    return {"ok": True, "score": round(score, 1), "label": label,
            "color": color, "components": comp}
