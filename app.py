"""
═══════════════════════════════════════════════════════════════
MARANGO TERMINAL — v5.0
Bloomberg/FactSet-Style Dashboard
═══════════════════════════════════════════════════════════════
Modernized UI with glassmorphism, dark theme, monospace fonts.
All original functionality preserved with Bloomberg-style aesthetics.

Features:
✅ Terminal-style header with live status
✅ Custom KPI cards with colored indicators (collapsible)
✅ Bloomberg dark theme (black #f7f8fa + orange accents)
✅ Monospace font for all data/numbers
✅ Glassmorphism cards with backdrop blur
✅ 6 comprehensive tabs with improved charts
✅ Real-time market data + Claude AI analysis
✅ Live regime score (Yahoo Finance) with Excel fallback
✅ Holdings filters (sector, signal, search)
═══════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import traceback
import json
import os
import yfinance as yf

# Valuation module (Reverse DCF + EODHD)
from valuation import display_valuation_tab
# Attribution module (Return decomposition + EODHD)
from attribution import display_attribution_tab
# Historical multiples module
from multiples import display_multiples_tab
# Quality scores module (Piotroski / Altman / Beneish)
from quality import display_quality_tab
# Peer comparison module
from peers import display_peers_tab
# Composite Signals module (Quality x Moat x Valuation x Sentiment)
from composite import display_signals_tab

# Anthropic API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ============================================
# PAGE CONFIGURATION (MUST BE FIRST)
# ============================================

st.set_page_config(
    page_title="Marango Terminal v5.0",
    page_icon="⌨️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CUSTOM CSS - BLOOMBERG DARK TERMINAL
# ============================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Main background */
    .main {
        background: #f7f8fa;
        color: #1e293b;
    }

    .stApp {
        background: #f7f8fa;
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'JetBrains Mono', monospace;
        color: #ea580c;
        font-weight: 700;
    }

    /* Data/Numbers */
    .monospace-text {
        font-family: 'JetBrains Mono', monospace;
    }

    /* Cards/Containers */
    .stMarkdown, .stDataFrame, [data-testid="stMetric"] {
        background: rgba(255,255,255,0.92);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(15,23,42,0.07);
        border-radius: 0.75rem;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: transparent;
        border-bottom: 1px solid rgba(15,23,42,0.07);
        padding: 0;
    }

    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        background: transparent;
        color: #64748b;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        padding: 0 1.5rem;
        border: none;
        border-bottom: 2px solid transparent;
        transition: all 0.2s;
    }

    .stTabs [aria-selected="true"] {
        background: transparent;
        color: #ea580c;
        border-bottom: 2px solid #ea580c;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #ea580c;
        border-bottom: 2px solid rgba(249, 115, 22, 0.5);
    }

    /* DataFrames — Bloomberg-style */
    .dataframe, [data-testid="stDataFrame"] > div {
        font-size: 0.85rem;
        background: #ffffff;
        color: #1e293b;
        border-radius: 6px;
    }

    .dataframe thead th,
    [data-testid="stDataFrame"] th {
        background: #eef2f6 !important;
        color: #ea580c !important;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        padding: 0.6rem 0.75rem;
        border-bottom: 2px solid rgba(249, 115, 22, 0.3) !important;
        font-family: 'JetBrains Mono', monospace;
    }

    .dataframe tbody td,
    [data-testid="stDataFrame"] td {
        padding: 0.55rem 0.75rem;
        border-bottom: 1px solid rgba(15,23,42,0.05);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
    }

    .dataframe tbody tr:nth-child(even),
    [data-testid="stDataFrame"] tr:nth-child(even) {
        background: rgba(15,23,42,0.035);
    }

    .dataframe tbody tr:hover,
    [data-testid="stDataFrame"] tr:hover {
        background: rgba(249, 115, 22, 0.06);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid rgba(15,23,42,0.07);
    }

    [data-testid="stSidebarContent"] {
        background: transparent;
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        transition: all 0.3s;
    }

    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(249, 115, 22, 0.3);
    }

    /* Divider */
    hr {
        border-color: rgba(15,23,42,0.07);
        margin: 2rem 0;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: #ea580c;
        text-shadow: 0 0 10px rgba(249, 115, 22, 0.3);
    }

    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }

    /* Info/Warning/Error boxes */
    .stInfo, .stWarning, .stError, .stSuccess {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(15,23,42,0.07);
        border-radius: 0.5rem;
        backdrop-filter: blur(12px);
    }

    /* Text */
    p, .stText {
        color: #1e293b;
    }

    /* Caption */
    .stCaption {
        color: #64748b;
        font-size: 0.8rem;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(249, 115, 22, 0.05);
        border: 1px solid rgba(249, 115, 22, 0.2);
    }

    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #ea580c, #0891b2);
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# INGENIO-STYLE LIGHT REFINEMENT (override layer)
# ============================================
st.markdown("""
<style>
.stApp, .main { background: #f7f8fa !important; color: #1e293b !important; }
.block-container { padding: 2.2rem 2.6rem 3rem 2.6rem !important; max-width: 1480px !important; }

h1,h2,h3,h4,h5,h6 { color: #1e293b !important; font-weight: 600 !important; letter-spacing: -0.01em !important; }
h1 { font-size: 1.7rem !important; }
h2 { font-size: 1.3rem !important; margin-top: 0.4rem !important; }
h3 { font-size: 1.05rem !important; color: #334155 !important; }
h4 { font-size: 0.88rem !important; color: #475569 !important; text-transform: uppercase; letter-spacing: 0.06em !important; }

p, span, label, .stText { color: #334155; }
.stCaption, [data-testid="stCaptionContainer"] { color: #94a3b8 !important; }

/* plain markdown text is NOT a card — kills the empty white spacer boxes */
.stMarkdown { background: transparent !important; border: none !important; box-shadow: none !important; }

[data-testid="stMetric"], [data-testid="stExpander"] {
  background: #ffffff !important;
  border: 1px solid #e7ebf0 !important;
  border-radius: 12px !important;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.03) !important;
  backdrop-filter: none !important;
}
[data-testid="stMetric"] { padding: 0.85rem 1.05rem !important; }
[data-testid="stMetricValue"] { color: #0f172a !important; font-size: 1.5rem !important; text-shadow: none !important; }
[data-testid="stMetricLabel"] { color: #64748b !important; }
.stDataFrame { border: 1px solid #e7ebf0 !important; border-radius: 12px !important; backdrop-filter: none !important; }

/* Tabs — generous breathing room */
.stTabs [data-baseweb="tab-list"] { gap: 1.6rem !important; border-bottom: 1px solid #e7ebf0 !important; padding-bottom: 0 !important; }
.stTabs [data-baseweb="tab"] {
  color: #64748b !important; font-weight: 600 !important; font-size: 0.8rem !important;
  letter-spacing: 0.04em !important; padding: 0.5rem 0.15rem !important; margin: 0 !important;
  background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #334155 !important; }
.stTabs [aria-selected="true"] { color: #ea580c !important; border-bottom: 2px solid #ea580c !important; }

.stTextInput input, .stNumberInput input { background: #ffffff !important; color: #1e293b !important; border: 1px solid #d8dee6 !important; }
[data-baseweb="select"] > div { background: #ffffff !important; border: 1px solid #d8dee6 !important; }

.stButton button {
  background: #ea580c !important; color: #ffffff !important; border: none !important;
  border-radius: 8px !important; font-weight: 600 !important; box-shadow: none !important;
}
.stButton button:hover { background: #c2410c !important; transform: none !important; box-shadow: 0 2px 8px rgba(234,88,12,0.25) !important; }

[data-testid="stDataFrame"] th { background: #f1f5f9 !important; color: #475569 !important; border-bottom: 2px solid #e2e8f0 !important; }
[data-testid="stDataFrame"] td { color: #334155 !important; }

[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e7ebf0 !important; }
hr { border-color: #e7ebf0 !important; margin: 1.4rem 0 !important; }
.streamlit-expanderHeader, [data-testid="stExpander"] summary { background: #f8fafc !important; color: #475569 !important; }
.stAlert { border-radius: 10px !important; }

/* tighten vertical rhythm — less dead space between blocks */
[data-testid="stVerticalBlock"] { gap: 0.65rem !important; }
</style>
""", unsafe_allow_html=True)


# ============================================
# DATA LOADING FUNCTIONS (UNCHANGED)
# ============================================

def safe_str(val, default=''):
    """Return default if val is NaN/None, else str(val)"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    s = str(val).strip()
    return default if s.lower() == 'nan' or s == '' else s

@st.cache_data(ttl=900)
def load_bloque1():
    """Portfolio scoring — EODHD-driven via portfolio_engine, Excel fallback."""
    # Primary: live EODHD-driven scoring engine
    try:
        from portfolio_engine import build_portfolio
        df = build_portfolio()
        if df is not None and not df.empty and df['Quality_Score'].notna().any():
            return df
    except Exception as e:
        st.warning(f"EODHD scoring unavailable — using Excel fallback. ({str(e)[:120]})")

    # Fallback: original Excel
    try:
        df = pd.read_excel(
            'Bloque_1_Financial_Scoring_Generic_V4.xlsx',
            sheet_name='Generic Scoring',
            header=2
        )
        df = df[df['Company'].notna()]
        df = df[df['SA SCORE'].notna()]
        df = df.rename(columns={
            'SA SCORE': 'Quality_Score',
            'P1.Adj': 'P1',
            'P2.Adj': 'P2',
            'P3.Adj': 'P3',
            'P4.Adj': 'P4',
            'P5.Val': 'P5',
            'P6.Adj': 'P6'
        })
        return df
    except Exception as e:
        st.error(f"Error loading Bloque 1: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=900)
def load_regime():
    """Load Market Regime — tries live Yahoo Finance first, falls back to Excel Bridge"""
    # Try live data first
    try:
        live = get_live_regime()
        if live is not None:
            active_triggers = [t for t in live.get('triggers', []) if t.get('triggered') == 'YES']
            cb_text = ', '.join([t['trigger'] for t in active_triggers]) if active_triggers else 'None'
            return {
                'combined': live.get('combined_score', 0),
                'status': live.get('combined_status', 'Unknown'),
                'technical': live.get('tech_score', 0),
                'sentiment': live.get('sentiment_score', 0),
                'liquidity': live.get('liq_score', 0),
                'circuit_breaker': cb_text,
                'date': pd.Timestamp.now().strftime('%Y-%m-%d')
            }
    except Exception:
        pass

    # Fallback to Excel
    try:
        bridge_df = pd.read_excel(
            'Bloque_5_Market_Regime_V5.xlsx',
            sheet_name='🔗 B1↔B5 Bridge',
            header=None
        )

        regime = {
            'combined': float(bridge_df.iloc[6, 1]),
            'status': str(bridge_df.iloc[7, 1]),
            'technical': float(bridge_df.iloc[9, 1]),
            'sentiment': float(bridge_df.iloc[8, 1]),
            'liquidity': float(bridge_df.iloc[10, 1]),
            'circuit_breaker': str(bridge_df.iloc[11, 1]),
            'date': bridge_df.iloc[12, 1]
        }

        return regime

    except Exception as e:
        st.error(f"Error loading Regime: {str(e)}")
        return {
            'combined': 0,
            'status': 'Unknown',
            'technical': 0,
            'sentiment': 0,
            'liquidity': 0,
            'circuit_breaker': '',
            'date': None
        }

@st.cache_data(ttl=900)
def get_live_regime():
    """Calculate live regime indicators from Yahoo Finance + FRED"""
    try:
        # Helper: safely convert to float, replacing NaN with default
        def safe_float(val, default=0.0):
            try:
                v = float(val)
                if pd.isna(v) or np.isnan(v):
                    return default
                return v
            except (ValueError, TypeError):
                return default

        # ── SENTIMENT & SYSTEMIC ──────────────────────────────
        # Download VIX, VIX3M, S&P 500, HY Bond ETF
        sentiment_tickers = ['^VIX', '^VIX3M', '^GSPC', 'HYG', 'LQD']
        sent_data = yf.download(sentiment_tickers, period='1y', progress=False)['Close']

        if sent_data.empty:
            return None

        latest = sent_data.iloc[-1]
        vix = safe_float(latest.get('^VIX', 20), 20)
        vix3m = safe_float(latest.get('^VIX3M', 20), 20)
        spx = safe_float(latest.get('^GSPC', 5000), 5000)

        # VIX Term Structure
        vix_term = vix / vix3m if vix3m > 0 else 1.0

        # HY Spread proxy: LQD/HYG ratio (higher = wider spreads)
        hyg = safe_float(latest.get('HYG', 75), 75)
        lqd = safe_float(latest.get('LQD', 105), 105)
        hy_spread_proxy = (lqd / hyg - 1) * 10000  # bps approximation

        # Market breadth: % of S&P 500 components above 200-day MA
        # Approximate using SPY ETF RSI as proxy
        spy_data = sent_data['^GSPC'].dropna()

        # Sentiment indicators
        sentiment_indicators = []

        # 1. VIX scoring: <15=100, 15-22=70, 22-35=40, >35=10
        if vix < 15:
            vix_score = 100
            vix_status = 'Risk-On'
        elif vix < 22:
            vix_score = 70
            vix_status = 'Neutral'
        elif vix < 35:
            vix_score = 40
            vix_status = 'Elevated'
        else:
            vix_score = 10
            vix_status = 'Risk-Off'
        sentiment_indicators.append({
            'indicator': 'VIX (Volatility Index)',
            'value': vix, 'risk_on': '< 15', 'neutral': '15 - 22',
            'risk_off': '> 35', 'direction': 'Lower = Better',
            'status': vix_status, 'score': vix_score
        })

        # 2. VIX Term Structure: <0.85=100, 0.85-1.0=60, >1.0=20
        if vix_term < 0.85:
            vt_score = 100
            vt_status = 'Risk-On (Contango)'
        elif vix_term < 1.0:
            vt_score = 60
            vt_status = 'Neutral'
        else:
            vt_score = 20
            vt_status = 'Risk-Off (Backwardation)'
        sentiment_indicators.append({
            'indicator': 'VIX Term Structure (VIX/VIX3M)',
            'value': vix_term, 'risk_on': '< 0.85', 'neutral': '0.85 - 1.0',
            'risk_off': '> 1.2', 'direction': 'Lower = Better',
            'status': vt_status, 'score': vt_score
        })

        # 3. HY Spread proxy
        if hy_spread_proxy < 200:
            hy_score = 90
            hy_status = 'Risk-On'
        elif hy_spread_proxy < 400:
            hy_score = 60
            hy_status = 'Neutral'
        else:
            hy_score = 20
            hy_status = 'Risk-Off'
        sentiment_indicators.append({
            'indicator': 'HY Spread Proxy (LQD/HYG bps)',
            'value': hy_spread_proxy, 'risk_on': '< 200', 'neutral': '200 - 400',
            'risk_off': '> 600', 'direction': 'Lower = Better',
            'status': hy_status, 'score': hy_score
        })

        # Sentiment composite
        sent_weights = [0.40, 0.30, 0.30]
        sent_scores = [vix_score, vt_score, hy_score]
        sentiment_score = sum(w * s for w, s in zip(sent_weights, sent_scores))

        # ── TECHNICAL INDICATORS ──────────────────────────────
        tech_indicators = []
        spy_close = spy_data.values

        # S&P 500 vs 200-day MA
        if len(spy_close) >= 200:
            ma200 = float(np.mean(spy_close[-200:]))
            spx_vs_ma200 = ((spx / ma200) - 1) * 100
            if spx_vs_ma200 > 3:
                ma200_score = 90
            elif spx_vs_ma200 > 0:
                ma200_score = 60
            elif spx_vs_ma200 > -5:
                ma200_score = 30
            else:
                ma200_score = 10
            tech_indicators.append({
                'indicator': 'S&P 500 vs MA-200',
                'value': spx, 'reference': ma200,
                'score': ma200_score, 'weight': 0.25
            })
        else:
            ma200 = spx
            ma200_score = 50

        # S&P 500 vs 50-day MA
        if len(spy_close) >= 50:
            ma50 = float(np.mean(spy_close[-50:]))
            spx_vs_ma50 = ((spx / ma50) - 1) * 100
            if spx_vs_ma50 > 2:
                ma50_score = 85
            elif spx_vs_ma50 > 0:
                ma50_score = 55
            elif spx_vs_ma50 > -3:
                ma50_score = 25
            else:
                ma50_score = 10
            tech_indicators.append({
                'indicator': 'S&P 500 vs MA-50',
                'value': spx, 'reference': ma50,
                'score': ma50_score, 'weight': 0.20
            })
        else:
            ma50 = spx
            ma50_score = 50

        # Golden/Death Cross
        if len(spy_close) >= 200:
            cross_score = 80 if ma50 > ma200 else 15
            cross_label = 'Golden Cross' if ma50 > ma200 else 'Death Cross'
            tech_indicators.append({
                'indicator': f'MA Cross ({cross_label})',
                'value': ma50, 'reference': ma200,
                'score': cross_score, 'weight': 0.10
            })
        else:
            cross_score = 50

        # RSI (14-day)
        if len(spy_close) >= 15:
            deltas = np.diff(spy_close[-15:])
            gains = np.mean([d for d in deltas if d > 0]) if any(d > 0 for d in deltas) else 0
            losses = abs(np.mean([d for d in deltas if d < 0])) if any(d < 0 for d in deltas) else 0.001
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
            if rsi > 70:
                rsi_score = 30  # Overbought
            elif rsi > 55:
                rsi_score = 80
            elif rsi > 30:
                rsi_score = 50
            else:
                rsi_score = 15  # Oversold
            tech_indicators.append({
                'indicator': 'RSI (14-Day)',
                'value': rsi, 'reference': 50,
                'score': rsi_score, 'weight': 0.25
            })
        else:
            rsi = 50
            rsi_score = 50

        # MACD
        if len(spy_close) >= 26:
            ema12 = pd.Series(spy_close).ewm(span=12).mean().iloc[-1]
            ema26 = pd.Series(spy_close).ewm(span=26).mean().iloc[-1]
            macd_val = ema12 - ema26
            signal_line = pd.Series(spy_close).ewm(span=12).mean().diff().ewm(span=9).mean().iloc[-1]
            if macd_val > 0 and macd_val > signal_line:
                macd_score = 85
            elif macd_val > 0:
                macd_score = 60
            elif macd_val > -50:
                macd_score = 30
            else:
                macd_score = 10
            tech_indicators.append({
                'indicator': 'MACD (12,26,9)',
                'value': macd_val, 'reference': 0,
                'score': macd_score, 'weight': 0.20
            })
        else:
            macd_score = 50

        # Technical composite
        tech_total_weight = sum(t['weight'] for t in tech_indicators)
        tech_score = sum(t['score'] * t['weight'] for t in tech_indicators) / tech_total_weight if tech_total_weight > 0 else 50

        # ── LIQUIDITY (from Yahoo Finance proxies) ────────────
        liq_tickers = ['DX-Y.NYB', 'GLD', '^TNX', '^IRX', 'TLT']
        liq_data = yf.download(liq_tickers, period='3mo', progress=False)['Close']

        liq_indicators = []
        liq_scores = []
        dxy = 100.0  # default if data unavailable

        if not liq_data.empty:
            liq_latest = liq_data.iloc[-1]

            # DXY Dollar Index
            dxy = safe_float(liq_latest.get('DX-Y.NYB', 100), 100)
            if dxy < 95:
                dxy_score = 85
                dxy_status = 'Risk-On'
            elif dxy < 105:
                dxy_score = 55
                dxy_status = 'Neutral'
            else:
                dxy_score = 20
                dxy_status = 'Risk-Off'
            liq_indicators.append({
                'indicator': 'DXY (Dollar Index)', 'value': dxy,
                'risk_on': '< 95', 'neutral': '95 - 105', 'risk_off': '> 105',
                'direction': 'Lower = Better', 'status': dxy_status, 'score': dxy_score
            })
            liq_scores.append(dxy_score * 0.20)

            # 10Y Yield
            y10 = safe_float(liq_latest.get('^TNX', 4.0), 4.0)
            if y10 < 3.5:
                y10_score = 80
                y10_status = 'Supportive'
            elif y10 < 4.5:
                y10_score = 55
                y10_status = 'Neutral'
            else:
                y10_score = 20
                y10_status = 'Restrictive'
            liq_indicators.append({
                'indicator': '10Y Treasury Yield (%)', 'value': y10,
                'risk_on': '< 3.5%', 'neutral': '3.5% - 4.5%', 'risk_off': '> 4.5%',
                'direction': 'Lower = Better', 'status': y10_status, 'score': y10_score
            })
            liq_scores.append(y10_score * 0.20)

            # Yield Curve (10Y - 3M)
            y3m = safe_float(liq_latest.get('^IRX', 4.0), 4.0)
            curve = y10 - y3m
            if curve > 1.0:
                curve_score = 85
                curve_status = 'Risk-On (Steep)'
            elif curve > 0:
                curve_score = 55
                curve_status = 'Neutral'
            else:
                curve_score = 20
                curve_status = 'Risk-Off (Inverted)'
            liq_indicators.append({
                'indicator': 'Yield Curve 10Y-3M (%)', 'value': curve,
                'risk_on': '> 1.0%', 'neutral': '0% - 1.0%', 'risk_off': '< 0% (inverted)',
                'direction': 'Higher = Better', 'status': curve_status, 'score': curve_score
            })
            liq_scores.append(curve_score * 0.25)

            # Gold/SPX Ratio (fear gauge)
            gold = safe_float(liq_latest.get('GLD', 200), 200)
            gold_spx = gold / spx if spx > 0 else 0
            if gold_spx < 0.035:
                gld_score = 80
                gld_status = 'Risk-On'
            elif gold_spx < 0.045:
                gld_score = 55
                gld_status = 'Neutral'
            else:
                gld_score = 25
                gld_status = 'Risk-Off (Fear)'
            liq_indicators.append({
                'indicator': 'Gold/SPX Ratio', 'value': gold_spx,
                'risk_on': '< 0.035', 'neutral': '0.035 - 0.045', 'risk_off': '> 0.045',
                'direction': 'Lower = Better', 'status': gld_status, 'score': gld_score
            })
            liq_scores.append(gld_score * 0.15)

            # TLT momentum (bond flight)
            if len(liq_data) >= 21:
                tlt_now = safe_float(liq_latest.get('TLT', 90), 90)
                tlt_1m = safe_float(liq_data['TLT'].iloc[-21], tlt_now) if 'TLT' in liq_data.columns else tlt_now
                tlt_chg = ((tlt_now / tlt_1m) - 1) * 100 if tlt_1m > 0 else 0
                if tlt_chg < -2:
                    tlt_score = 75  # Selling bonds = risk-on
                    tlt_status = 'Risk-On (Bond sell-off)'
                elif tlt_chg < 2:
                    tlt_score = 50
                    tlt_status = 'Neutral'
                else:
                    tlt_score = 25
                    tlt_status = 'Risk-Off (Flight to safety)'
                liq_indicators.append({
                    'indicator': 'TLT 1M Change (%)', 'value': tlt_chg,
                    'risk_on': '< -2%', 'neutral': '-2% to 2%', 'risk_off': '> 2%',
                    'direction': 'Lower = Better', 'status': tlt_status, 'score': tlt_score
                })
                liq_scores.append(tlt_score * 0.20)

        liq_score = sum(liq_scores) / (sum([0.20, 0.20, 0.25, 0.15, 0.20])) if liq_scores else 50

        # ── COMBINED SCORE ────────────────────────────────────
        combined = sentiment_score * 0.35 + tech_score * 0.35 + liq_score * 0.30

        # Regime classification
        if combined >= 70:
            regime_status = 'RISK-ON'
        elif combined >= 55:
            regime_status = 'MODERATE — Normal positioning'
        elif combined >= 45:
            regime_status = 'CAUTION — Increase quality'
        else:
            regime_status = 'RISK-OFF — Defensive positioning'

        # Check triggers
        triggers = []
        triggers.append({
            'trigger': 'VIX Spike', 'condition': 'VIX > 25',
            'current': f'{vix:.1f}',
            'triggered': 'YES' if vix > 25 else 'NO',
            'action': 'Reduce tech exposure, increase hedges'
        })
        triggers.append({
            'trigger': 'Death Cross', 'condition': 'MA50 < MA200',
            'current': f'MA50={ma50:,.0f} MA200={ma200:,.0f}',
            'triggered': 'YES' if ma50 < ma200 else 'NO',
            'action': 'Rotate to defensives, raise cash'
        })
        triggers.append({
            'trigger': 'RSI Oversold', 'condition': 'RSI < 30',
            'current': f'{rsi:.1f}',
            'triggered': 'YES' if rsi < 30 else 'NO',
            'action': 'Potential bounce — watch for reversal'
        })
        triggers.append({
            'trigger': 'Strong Dollar', 'condition': 'DXY > 105',
            'current': f'{dxy:.1f}',
            'triggered': 'YES' if dxy > 105 else 'NO',
            'action': 'Headwind for international earnings'
        })

        # Divergence
        gap = abs(sentiment_score - tech_score)
        if gap > 30:
            div_status = 'MAJOR DIVERGENCE'
            div_guidance = 'Reduce conviction — Wait for alignment before full sizing'
        elif gap > 15:
            div_status = 'MODERATE DIVERGENCE'
            div_guidance = 'Monitor closely — Partial positions only'
        else:
            div_status = 'ALIGNED'
            div_guidance = 'Macro and technicals agree — Normal conviction'

        # Override check
        active_triggers = [t for t in triggers if t['triggered'] == 'YES']
        if len(active_triggers) >= 2:
            override = f'Circuit Breaker — {len(active_triggers)} triggers active: ' + ', '.join([t['trigger'] for t in active_triggers])
            action = 'Reduce risk exposure. Raise cash 10-15%. Rotate to defensives.'
        elif len(active_triggers) == 1:
            override = f'Warning — {active_triggers[0]["trigger"]} active'
            action = active_triggers[0]['action']
        else:
            override = ''
            action = 'Normal positioning per regime score'

        return {
            'sentiment_indicators': sentiment_indicators,
            'sentiment_score': sentiment_score,
            'sentiment_regime': regime_status,
            'regime_change_prob': f'{gap:.0f}pt divergence',
            'tech_indicators': tech_indicators,
            'tech_score': tech_score,
            'tech_regime': f'Technical Score: {tech_score:.0f}/100',
            'liq_indicators': liq_indicators,
            'liq_score': liq_score,
            'liq_regime': f'Liquidity Score: {liq_score:.0f}/100',
            'combined_score': combined,
            'combined_status': regime_status,
            'override': override,
            'action': action,
            'triggers': triggers,
            'divergence_status': div_status,
            'divergence_guidance': div_guidance,
            'sectors': [],  # Sector rotation comes from Excel
            'favor': '', 'neutral_sectors': '', 'avoid': '',
            'marango_action': '',
            'live': True
        }

    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def load_regime_full():
    """Load all Market Regime indicators from B5 sheet (fallback if live fails)"""
    try:
        df = pd.read_excel(
            'Bloque_5_Market_Regime_V5.xlsx',
            sheet_name='B5 - Market Regime',
            header=None
        )

        data = {}

        # Sentiment indicators (rows 6-10)
        sentiment_indicators = []
        for i in range(6, 11):
            row = df.iloc[i]
            if pd.notna(row[1]):
                sentiment_indicators.append({
                    'indicator': safe_str(row[1]),
                    'value': row[2],
                    'risk_on': safe_str(row[3]),
                    'neutral': safe_str(row[4]),
                    'risk_off': safe_str(row[5]),
                    'direction': safe_str(row[6]),
                    'status': safe_str(row[7])
                })
        data['sentiment_indicators'] = sentiment_indicators
        # Sentiment composite score is in row 12, col 8
        data['sentiment_score'] = float(df.iloc[12, 8]) if pd.notna(df.iloc[12, 8]) else 0

        # Regime classification
        data['sentiment_regime'] = safe_str(df.iloc[15, 2])
        data['regime_change_prob'] = safe_str(df.iloc[17, 2])

        # Risk-off triggers (rows 26-31)
        triggers = []
        for i in range(26, 32):
            row = df.iloc[i]
            if pd.notna(row[0]) and pd.notna(row[1]):
                triggers.append({
                    'trigger': safe_str(row[0]),
                    'condition': safe_str(row[1]),
                    'current': safe_str(row[2]),
                    'triggered': safe_str(row[3]),
                    'action': safe_str(row[4])
                })
        data['triggers'] = triggers

        # Technical indicators (rows 40-45)
        tech_indicators = []
        for i in range(40, 46):
            row = df.iloc[i]
            if pd.notna(row[0]):
                tech_indicators.append({
                    'indicator': safe_str(row[0]),
                    'value': row[1],
                    'reference': row[2],
                    'score': row[5] if pd.notna(row[5]) else 0,
                    'weight': row[6] if pd.notna(row[6]) else 0
                })
        data['tech_indicators'] = tech_indicators
        # Technical composite score is in row 46, col 5
        data['tech_score'] = float(df.iloc[46, 5]) if pd.notna(df.iloc[46, 5]) else 0
        data['tech_regime'] = safe_str(df.iloc[49, 2])

        # Liquidity indicators (rows 55-65)
        liq_indicators = []
        for i in range(55, 66):
            row = df.iloc[i]
            if pd.notna(row[1]):
                liq_indicators.append({
                    'indicator': safe_str(row[1]),
                    'value': row[2],
                    'risk_on': safe_str(row[3]),
                    'neutral': safe_str(row[4]),
                    'risk_off': safe_str(row[5]),
                    'direction': safe_str(row[6]),
                    'status': safe_str(row[7])
                })
        data['liq_indicators'] = liq_indicators
        # Liquidity composite score is in row 66, col 8
        data['liq_score'] = float(df.iloc[66, 8]) if pd.notna(df.iloc[66, 8]) else 0
        data['liq_regime'] = safe_str(df.iloc[69, 2])

        # Combined score (rows 78-83)
        data['combined_score'] = float(df.iloc[81, 2]) if pd.notna(df.iloc[81, 2]) else 0
        data['combined_status'] = safe_str(df.iloc[81, 8])
        data['override'] = safe_str(df.iloc[82, 2])
        data['action'] = safe_str(df.iloc[83, 2])

        # Divergence (rows 86-89)
        data['divergence_status'] = safe_str(df.iloc[87, 1])
        data['divergence_guidance'] = safe_str(df.iloc[89, 1])

        # Sector rotation (rows 95-104)
        sectors = []
        for i in range(95, 105):
            row = df.iloc[i]
            if pd.notna(row[1]):
                sectors.append({
                    'sector': safe_str(row[1]),
                    'beta': safe_str(row[2]),
                    'signal': safe_str(row[7])
                })
        data['sectors'] = sectors

        # Positioning summary (rows 107-110)
        data['favor'] = safe_str(df.iloc[107, 1])
        data['neutral_sectors'] = safe_str(df.iloc[108, 1])
        data['avoid'] = safe_str(df.iloc[109, 1])
        data['marango_action'] = safe_str(df.iloc[110, 1])

        return data

    except Exception as e:
        st.error(f"Error loading Regime Full: {str(e)}")
        return None

@st.cache_data(ttl=900)
def load_bridge_data():
    """Load Bridge actionable picks"""
    try:
        bridge_df = pd.read_excel(
            'Bloque_5_Market_Regime_V5.xlsx',
            sheet_name='🔗 B1↔B5 Bridge',
            header=None
        )

        zones = []
        for row in range(6, 13):
            zone_data = {
                'zone': str(bridge_df.iloc[row, 3]),
                'score_range': str(bridge_df.iloc[row, 4]),
                'cash_pct': str(bridge_df.iloc[row, 5]),
                'action': str(bridge_df.iloc[row, 6]),
                'buy_filter': str(bridge_df.iloc[row, 7]),
            }
            zones.append(zone_data)

        zones_df = pd.DataFrame(zones)

        picks_df = bridge_df.iloc[19:, 0:10].copy()
        picks_df.columns = ['Ticker', 'Company', 'Sector', 'B1_Score',
                            'Band', 'Upside', 'B1_Signal', 'Regime_Action',
                            'Size', 'Rationale']

        picks_df = picks_df.dropna(subset=['Ticker'])
        picks_df = picks_df[picks_df['Ticker'].astype(str).str.len() > 0]
        picks_df['B1_Score'] = pd.to_numeric(picks_df['B1_Score'], errors='coerce')
        picks_df['Upside'] = pd.to_numeric(picks_df['Upside'], errors='coerce')
        # Fix mixed types in Size column (pyarrow ArrowTypeError)
        picks_df['Size'] = picks_df['Size'].astype(str).replace('nan', '—')

        if picks_df['Upside'].max() <= 1:
            picks_df['Upside'] = (picks_df['Upside'] * 100).round(1)
        picks_df = picks_df.rename(columns={'Upside': 'Upside %'})

        return zones_df, picks_df

    except Exception as e:
        st.error(f"Error loading Bridge data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=300)
def get_market_indices():
    """Get major market indices from Yahoo Finance — grouped by region"""
    regions = {
        'Americas': {
            'S&P 500': '^GSPC',
            'Nasdaq': '^IXIC',
            'Dow Jones': '^DJI',
            'S&P/TSX': '^GSPTSE',
            'Bovespa': '^BVSP',
        },
        'EMEA': {
            'Euro Stoxx 50': '^STOXX50E',
            'FTSE 100': '^FTSE',
            'DAX': '^GDAXI',
            'CAC 40': '^FCHI',
            'IBEX 35': '^IBEX',
        },
        'Asia/Pacific': {
            'Nikkei 225': '^N225',
            'Hang Seng': '^HSI',
            'Shanghai': '000001.SS',
            'ASX 200': '^AXJO',
        },
        'Macro': {
            'VIX': '^VIX',
            'EUR/USD': 'EURUSD=X',
            '10Y Treasury': '^TNX',
            'Gold': 'GC=F',
            'Oil (WTI)': 'CL=F',
        }
    }

    all_tickers = {}
    for region, tickers in regions.items():
        for name, symbol in tickers.items():
            all_tickers[name] = {'symbol': symbol, 'region': region}

    fallback_result = {}
    for name, info in all_tickers.items():
        fallback_result[name] = {'value': 0, 'change': 0, 'change_pct': 0, 'region': info['region'], 'sparkline': []}

    try:
        symbols = [info['symbol'] for info in all_tickers.values()]
        data = yf.download(symbols, period='5d', group_by='ticker', progress=False)

        result = {}
        for name, info in all_tickers.items():
            symbol = info['symbol']
            try:
                if len(symbols) > 1:
                    ticker_data = data[symbol]['Close'].dropna()
                else:
                    ticker_data = data['Close'].dropna()

                if len(ticker_data) >= 2:
                    current = float(ticker_data.iloc[-1])
                    previous = float(ticker_data.iloc[-2])
                    change = current - previous
                    change_pct = (change / previous) * 100
                    result[name] = {
                        'value': round(current, 2),
                        'change': round(change, 2),
                        'change_pct': round(change_pct, 2),
                        'region': info['region'],
                        'sparkline': ticker_data.tolist()
                    }
                else:
                    result[name] = fallback_result.get(name)
            except Exception:
                result[name] = fallback_result.get(name)

        return result
    except Exception:
        return fallback_result

@st.cache_data(ttl=300)
def get_sector_performance():
    """Get sector ETF performance from Yahoo Finance"""
    sector_tickers = {
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financials': 'XLF',
        'Consumer Discret.': 'XLY',
        'Industrials': 'XLI',
        'Energy': 'XLE',
        'Materials': 'XLB',
        'Utilities': 'XLU',
        'Real Estate': 'XLRE',
        'Cons. Staples': 'XLP',
        'Communication': 'XLC'
    }

    fallback = {k: {'ticker': v, 'change': 0.0} for k, v in sector_tickers.items()}

    try:
        symbols = list(sector_tickers.values())
        data = yf.download(symbols, period='5d', group_by='ticker', progress=False)

        result = {}
        for name, ticker in sector_tickers.items():
            try:
                ticker_data = data[ticker]['Close'].dropna()
                if len(ticker_data) >= 2:
                    current = float(ticker_data.iloc[-1])
                    previous = float(ticker_data.iloc[-2])
                    change_pct = ((current - previous) / previous) * 100
                    result[name] = {'ticker': ticker, 'change': round(change_pct, 2)}
                else:
                    result[name] = {'ticker': ticker, 'change': 0.0}
            except Exception:
                result[name] = {'ticker': ticker, 'change': 0.0}

        return result
    except Exception:
        return fallback

@st.cache_data(ttl=900)
def load_score_history():
    """Load Score History from Excel"""
    try:
        df = pd.read_excel(
            'Bloque_1_Financial_Scoring_Generic_V4.xlsx',
            sheet_name='Score History',
            header=1
        )
        df = df[df['Company'].notna()]

        quarter_cols = [c for c in df.columns if c not in ['Company', 'Current Score'] and isinstance(c, str)]

        data = []
        for _, row in df.iterrows():
            company = row['Company']
            for qcol in quarter_cols:
                score = row[qcol]
                if pd.notna(score):
                    try:
                        score = float(score)
                        data.append({
                            'Date': pd.to_datetime(qcol, format='%b %Y', errors='coerce') or pd.to_datetime(qcol, errors='coerce'),
                            'Company': company,
                            'Quality_Score': score
                        })
                    except (ValueError, TypeError):
                        continue

        if data:
            result = pd.DataFrame(data)
            result = result[result['Date'].notna()]
            return result

        fallback_data = []
        for _, row in df.iterrows():
            if pd.notna(row.get('Current Score')):
                fallback_data.append({
                    'Date': pd.Timestamp.now(),
                    'Company': row['Company'],
                    'Quality_Score': float(row['Current Score'])
                })
        return pd.DataFrame(fallback_data)

    except Exception as e:
        try:
            b1 = load_bloque1()
            top = b1.nlargest(10, 'Quality_Score')
            data = []
            dates = pd.date_range(end=pd.Timestamp.now(), periods=4, freq='QE')
            for _, row in top.iterrows():
                base = row['Quality_Score']
                for date in dates:
                    score = base + np.random.randn() * 3
                    data.append({'Date': date, 'Company': row['Company'], 'Quality_Score': np.clip(score, 50, 100)})
            return pd.DataFrame(data)
        except:
            return pd.DataFrame(columns=['Date', 'Company', 'Quality_Score'])


@st.cache_data(ttl=300)
def get_live_prices(tickers):
    """Get live prices + 5-day sparkline data for portfolio holdings"""
    if not tickers or len(tickers) == 0:
        return {}

    try:
        clean_tickers = [t.strip() for t in tickers if isinstance(t, str) and t.strip()]
        if not clean_tickers:
            return {}

        data = yf.download(clean_tickers, period='5d', group_by='ticker', progress=False)

        prices = {}
        for ticker in clean_tickers:
            try:
                if len(clean_tickers) > 1:
                    ticker_data = data[ticker]['Close'].dropna()
                else:
                    ticker_data = data['Close'].dropna()

                if len(ticker_data) >= 2:
                    current = float(ticker_data.iloc[-1])
                    previous = float(ticker_data.iloc[-2])
                    change_pct = ((current - previous) / previous) * 100
                    sparkline = ticker_data.tolist()
                    prices[ticker] = {
                        'price': round(current, 2),
                        'change_pct': round(change_pct, 2),
                        'sparkline': sparkline
                    }
            except Exception:
                continue

        return prices
    except Exception:
        return {}

# ============================================
# DEXTER-INSPIRED DATA FUNCTIONS
# ============================================

@st.cache_data(ttl=900)
def get_insider_trades(ticker):
    """Get recent insider transactions for a ticker via yfinance"""
    if not ticker or not isinstance(ticker, str) or len(ticker.strip()) == 0:
        return {'net': 0, 'buys': 0, 'sells': 0, 'label': '—'}
    try:
        t = yf.Ticker(ticker)
        insiders = t.insider_transactions
        if insiders is None or insiders.empty:
            return {'net': 0, 'buys': 0, 'sells': 0, 'label': '—'}
        # Last 90 days
        if 'Start Date' in insiders.columns:
            insiders['Start Date'] = pd.to_datetime(insiders['Start Date'], errors='coerce')
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=90)
            insiders = insiders[insiders['Start Date'] >= cutoff]
        buys = 0
        sells = 0
        if 'Transaction' in insiders.columns:
            for _, row in insiders.iterrows():
                txn = str(row.get('Transaction', '')).lower()
                if 'purchase' in txn or 'buy' in txn:
                    buys += 1
                elif 'sale' in txn or 'sell' in txn:
                    sells += 1
        net = buys - sells
        if net > 0:
            label = f'🟢 Net Buy ({buys}B/{sells}S)'
        elif net < 0:
            label = f'🔴 Net Sell ({buys}B/{sells}S)'
        elif buys + sells > 0:
            label = f'⚪ Neutral ({buys}B/{sells}S)'
        else:
            label = '—'
        return {'net': net, 'buys': buys, 'sells': sells, 'label': label}
    except Exception:
        return {'net': 0, 'buys': 0, 'sells': 0, 'label': '—'}


@st.cache_data(ttl=900)
def get_analyst_data(ticker):
    """Get analyst price targets and consensus for a ticker"""
    if not ticker or not isinstance(ticker, str) or len(ticker.strip()) == 0:
        return {'target_mean': None, 'upside': None, 'recommendation': '—', 'num_analysts': 0,
                'pe_forward': None, 'pe_trailing': None, 'target_low': None, 'target_high': None, 'current': None}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        target_mean = info.get('targetMeanPrice', None)
        target_low = info.get('targetLowPrice', None)
        target_high = info.get('targetHighPrice', None)
        current = info.get('currentPrice', None) or info.get('regularMarketPrice', None)
        rec = info.get('recommendationKey', '').upper() or '—'
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        pe_forward = info.get('forwardPE', None)
        pe_trailing = info.get('trailingPE', None)

        upside = None
        if target_mean and current and current > 0:
            upside = ((target_mean - current) / current) * 100

        return {
            'target_mean': target_mean,
            'target_low': target_low,
            'target_high': target_high,
            'current': current,
            'upside': upside,
            'recommendation': rec,
            'num_analysts': num_analysts,
            'pe_forward': pe_forward,
            'pe_trailing': pe_trailing,
        }
    except Exception:
        return {'target_mean': None, 'upside': None, 'recommendation': '—', 'num_analysts': 0,
                'pe_forward': None, 'pe_trailing': None, 'target_low': None, 'target_high': None, 'current': None}


@st.cache_data(ttl=900)
def get_earnings_info(ticker):
    """Get earnings dates and basic financials for a ticker"""
    if not ticker or not isinstance(ticker, str) or len(ticker.strip()) == 0:
        return {'revenue': None, 'net_income': None, 'eps_trailing': None, 'eps_forward': None,
                'market_cap': None, 'dividend_yield': None, 'gross_margins': None, 'ebitda': None,
                'next_earnings': None, 'last_earnings': None}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        result = {
            'revenue': info.get('totalRevenue', None),
            'net_income': info.get('netIncomeToCommon', None),
            'eps_trailing': info.get('trailingEps', None),
            'eps_forward': info.get('forwardEps', None),
            'market_cap': info.get('marketCap', None),
            'dividend_yield': info.get('dividendYield', None),
            'gross_margins': info.get('grossMargins', None),
            'ebitda': info.get('ebitda', None),
            'next_earnings': None,
            'last_earnings': None,
        }
        # Try to get earnings dates
        try:
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                now = pd.Timestamp.now(tz='UTC') if ed.index.tz else pd.Timestamp.now()
                future = ed[ed.index >= now]
                past = ed[ed.index < now]
                if not future.empty:
                    result['next_earnings'] = future.index.min().strftime('%Y-%m-%d')
                if not past.empty:
                    result['last_earnings'] = past.index.max().strftime('%Y-%m-%d')
        except Exception:
            pass
        return result
    except Exception:
        return {'revenue': None, 'net_income': None, 'eps_trailing': None, 'eps_forward': None,
                'market_cap': None, 'dividend_yield': None, 'gross_margins': None, 'ebitda': None,
                'next_earnings': None, 'last_earnings': None}


# ============================================
# COMPANY → TICKER MAPPING (fallback when Excel has no Ticker data)
# ============================================

COMPANY_TICKER_MAP = {
    'NVIDIA Corp': 'NVDA', 'Apple Inc': 'AAPL', 'Microsoft Corp': 'MSFT',
    'Meta Platforms': 'META', 'Alphabet Inc': 'GOOGL', 'Amazon.com Inc': 'AMZN',
    'Broadcom Inc': 'AVGO', 'Tesla Inc': 'TSLA', 'ASML Holding NV': 'ASML',
    'SK Hynix': '000660.KS', 'Taiwan Semiconductor': 'TSM',
    'Salesforce': 'CRM', 'ServiceNow': 'NOW', 'Palo Alto Networks': 'PANW',
    'CrowdStrike': 'CRWD', 'Shopify': 'SHOP', 'ARM Holdings': 'ARM',
    'Applied Materials': 'AMAT', 'Lam Research': 'LRCX', 'Caterpillar Inc': 'CAT',
    'Eaton Corp': 'ETN', 'Docusign': 'DOCU', 'Astera Labs': 'ALAB',
    'Fair Isaac Corpora': 'FICO', 'Fortinet': 'FTNT', 'Topicus.com': 'TOI.V',
    'Palantir Technolog': 'PLTR', 'Seagate Technology': 'STX',
    'Cresto Technology': 'CRDO', 'Marvell Technology': 'MRVL',
    'Cadence Design Sys': 'CDNS', 'Texas Instruments': 'TXN',
    'Coherent': 'COHR', 'IREN Ltd': 'IREN', 'Intel Corporation': 'INTC',
    'Applied Optoelectr': 'AAOI', 'CoreWeave': 'CRWV', 'NIBUS Group': 'NBU',
    'Rocket Lab': 'RKLB', 'Bloom Energy': 'BE',
    'Safran SA': 'SAF.PA', 'Prysmian SPA': 'PRY.MI', 'Union Pacific': 'UNP',
    'General Electric C': 'GE', 'GE Vernova': 'GEV', 'Eaton Corp': 'ETN',
    'Kraken Robotics': 'KRKNF', 'Ferrari': 'RACE',
    'JPMorgan Chase': 'JPM', "Moody's Corp": 'MCO', 'Adyen NV': 'ADYEN.AS',
    'Mastercard Inc': 'MA', 'Visa Inc': 'V', 'Goldman Sachs': 'GS',
    'MSCI': 'MSCI', 'S&P Global Inc': 'SPGI', 'Berkshire Hathaway': 'BRK-B',
    'Robinhood Markets': 'HOOD', 'Brookfield Corp': 'BN',
    'Intuitive Surgical': 'ISRG', 'AbbVie Inc': 'ABBV',
    'UnitedHealth Group': 'UNH', 'Freeport McMoRan': 'FCX',
    'Alphabet Inc': 'GOOGL', 'Applovin Corporati': 'APP',
    'T-Mobile US': 'TMUS', 'AT&T SpaceMobile In': 'ASTS',
    'ConocoPhillips': 'COP', 'Exxon Mobil Corp': 'XOM',
    'Chevron Corp': 'CVX', 'NextEra Energy': 'NEE',
    'Dominion Energy': 'D', 'Duke Energy': 'DUK',
    'Amazon.com Inc': 'AMZN', "McDonald's Corp": 'MCD',
    'Home Depot': 'HD', 'Costco Wholesale': 'COST',
    'Walmart Inc': 'WMT', "L'Oreal SA": 'OR.PA',
    'Procter & Gamble': 'PG',
    'Freeport McMoRan': 'FCX', 'Linde plc': 'LIN',
    'Prologis Inc': 'PLD',
    'Freeport-McMoRan': 'FCX',
}


def resolve_ticker(company, row_data, df_columns):
    """Resolve ticker from Excel data or company name mapping"""
    # Try Excel column first
    for col_name in ['Ticker', 'TICKER', 'ticker', 'Symbol', 'SYMBOL']:
        if col_name in df_columns:
            raw_val = row_data.get(col_name, '')
            t = safe_str(raw_val)
            if t:
                return t
    # Fallback: company name mapping
    company_str = safe_str(company)
    if company_str in COMPANY_TICKER_MAP:
        return COMPANY_TICKER_MAP[company_str]
    # Partial match
    for name, tick in COMPANY_TICKER_MAP.items():
        if name.lower() in company_str.lower() or company_str.lower() in name.lower():
            return tick
    return ''


# ============================================
# AI HELPER FUNCTIONS
# ============================================

def load_ai_cache():
    """Load cached AI analysis results"""
    AI_CACHE_FILE = "ai_analysis_cache.json"
    if os.path.exists(AI_CACHE_FILE):
        try:
            with open(AI_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_ai_cache(cache):
    """Save AI analysis results to cache"""
    AI_CACHE_FILE = "ai_analysis_cache.json"
    try:
        with open(AI_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2, default=str)
    except Exception:
        pass

def get_stock_summary(ticker_symbol):
    """Get stock data summary from Yahoo Finance for AI analysis"""
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        hist = stock.history(period="1mo")

        summary = {
            "ticker": ticker_symbol,
            "name": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "price": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
            "market_cap": info.get("marketCap", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "peg_ratio": info.get("pegRatio", "N/A"),
            "price_to_book": info.get("priceToBook", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "revenue_growth": info.get("revenueGrowth", "N/A"),
            "earnings_growth": info.get("earningsGrowth", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A"),
            "roe": info.get("returnOnEquity", "N/A"),
            "debt_to_equity": info.get("debtToEquity", "N/A"),
            "free_cash_flow": info.get("freeCashflow", "N/A"),
            "beta": info.get("beta", "N/A"),
            "52w_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52w_low": info.get("fiftyTwoWeekLow", "N/A"),
            "50d_avg": info.get("fiftyDayAverage", "N/A"),
            "200d_avg": info.get("twoHundredDayAverage", "N/A"),
            "analyst_target": info.get("targetMeanPrice", "N/A"),
            "recommendation": info.get("recommendationKey", "N/A"),
        }

        if not hist.empty:
            summary["1m_return"] = round(((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100, 2)
            summary["1m_volatility"] = round(hist['Close'].pct_change().std() * (252**0.5) * 100, 2)

        return summary
    except Exception as e:
        return {"ticker": ticker_symbol, "error": str(e)}

def analyze_with_claude(ticker_symbol, stock_data, b1_score=None, signal=None):
    """Run AI analysis using Claude API"""
    try:
        api_key = None
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
        except Exception:
            pass
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"error": "API key not configured"}

        client = anthropic.Anthropic(api_key=api_key)

        b1_info = ""
        if b1_score is not None:
            b1_info = f"\nMarango B1 Quality Score: {b1_score}/100"
        if signal:
            b1_info += f"\nMarango Signal: {signal}"

        prompt = f"""Analyze this stock for an investment fund portfolio. Be concise and actionable.

STOCK DATA:
{json.dumps(stock_data, indent=2, default=str)}
{b1_info}

Provide your analysis in this EXACT format (use these exact headers):
SIGNAL: [STRONG BUY / BUY / HOLD / UNDERWEIGHT / SELL]
CONFIDENCE: [HIGH / MEDIUM / LOW]
TARGET: [your 12-month price target]
SUMMARY: [2-3 sentence analysis covering fundamentals, technicals, and risk]
KEY_RISKS: [top 2 risks, comma separated]
CATALYSTS: [top 2 positive catalysts, comma separated]"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        result = {
            "ticker": ticker_symbol,
            "analysis": response_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("SIGNAL:"):
                result["signal"] = line.replace("SIGNAL:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                result["confidence"] = line.replace("CONFIDENCE:", "").strip()
            elif line.startswith("TARGET:"):
                result["target"] = line.replace("TARGET:", "").strip()
            elif line.startswith("SUMMARY:"):
                result["summary"] = line.replace("SUMMARY:", "").strip()
            elif line.startswith("KEY_RISKS:"):
                result["risks"] = line.replace("KEY_RISKS:", "").strip()
            elif line.startswith("CATALYSTS:"):
                result["catalysts"] = line.replace("CATALYSTS:", "").strip()

        return result

    except Exception as e:
        return {"ticker": ticker_symbol, "error": str(e)}

# ============================================
# DISPLAY MODULES
# ============================================

def render_kpi_strip():
    """Render terminal-style KPI strip"""
    df = load_bloque1()
    # Use live regime (Yahoo Finance) with Excel fallback — load_regime() tries live first internally
    regime = load_regime()
    live_prices = {}

    if 'Ticker' in df.columns:
        tickers_list = df['Ticker'].dropna().unique().tolist()
        live_prices = get_live_prices(tickers_list)

        if live_prices:
            df['Live_Price'] = df['Ticker'].map(lambda t: live_prices.get(t, {}).get('price', None) if isinstance(t, str) else None)
            df['Daily_Change'] = df['Ticker'].map(lambda t: live_prices.get(t, {}).get('change_pct', 0) if isinstance(t, str) else 0)

    avg_quality = df['Quality_Score'].mean()
    num_holdings = len(df)

    # Use actual SIGNAL column from Excel
    if 'SIGNAL' in df.columns:
        buy_signals = len(df[df['SIGNAL'].str.contains('BUY|STRONG BUY', case=False, na=False)])
        hold_signals = len(df[df['SIGNAL'].str.contains('HOLD', case=False, na=False)])
        underweight_signals = len(df[df['SIGNAL'].str.contains('UNDERWEIGHT', case=False, na=False)])
        sell_signals = len(df[df['SIGNAL'].str.contains('SELL', case=False, na=False) & ~df['SIGNAL'].str.contains('BUY', case=False, na=False)])
    else:
        buy_signals = len(df[df['Quality_Score'] >= 80])
        hold_signals = len(df[(df['Quality_Score'] >= 65) & (df['Quality_Score'] < 80)])
        underweight_signals = 0
        sell_signals = len(df[df['Quality_Score'] < 65])

    # KPI Cards - Bloomberg style HTML (4 cards, no portfolio value)
    def kpi_card(label, value, delta, delta_positive=True, accent_color="#ea580c"):
        d_color = "#059669" if delta_positive else "#dc2626"
        arrow = "&#9650;" if delta_positive else "&#9660;"
        return f"""
        <div style="background:rgba(255,255,255,0.95);border:1px solid rgba(15,23,42,0.07);
                    border-top:2px solid {accent_color};border-radius:0.5rem;padding:1rem;
                    text-align:center;backdrop-filter:blur(8px);">
            <div style="color:#64748b;font-size:0.65rem;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:0.4rem;font-family:JetBrains Mono;">{label}</div>
            <div style="color:#1e293b;font-size:1.4rem;font-weight:700;
                        font-family:JetBrains Mono;margin-bottom:0.3rem;">{value}</div>
            <div style="color:{d_color};font-size:0.75rem;font-family:JetBrains Mono;">
                {arrow} {delta}</div>
        </div>"""

    regime_ok = regime['combined'] < 60

    cards_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;">'
    cards_html += kpi_card("QUALITY AVG", f"{avg_quality:.1f}", "/ 100", avg_quality >= 70, "#0891b2")
    cards_html += kpi_card("REGIME", f"{regime['combined']:.0f}", f"{regime['combined'] - 60:+.0f} vs neutral", regime_ok, "#059669" if regime_ok else "#dc2626")
    cards_html += kpi_card("HOLDINGS", f"{num_holdings}", f"{buy_signals} BUY | {hold_signals} HOLD", True, "#0891b2")
    cards_html += kpi_card("SIGNALS", f"{buy_signals}B | {hold_signals}H | {sell_signals}S", f"{underweight_signals} UW | {sell_signals} SELL", sell_signals == 0, "#ea580c")
    cards_html += '</div>'

    st.markdown(cards_html, unsafe_allow_html=True)

def display_bridge_tab():
    """Bridge: Quality × Regime × Momentum"""
    st.markdown("<h2>QUALITY × REGIME × MOMENTUM BRIDGE</h2>", unsafe_allow_html=True)
    st.caption("Three-factor signal: Fundamental Quality (B1) × Market Regime (B5) × Sector Momentum (B4)")

    regime = load_regime()
    zones_df, picks_df = load_bridge_data()
    momentum = get_sector_momentum()

    # ── THREE-FACTOR DASHBOARD ───────────────────────────────────
    col_regime, col_momentum, col_combined = st.columns(3)

    with col_regime:
        r_score = regime['combined']
        if r_score <= 35:
            r_color, r_label = '#059669', 'RISK-ON'
        elif r_score <= 60:
            r_color, r_label = '#0891b2', 'NEUTRAL'
        elif r_score <= 80:
            r_color, r_label = '#d97706', 'CAUTIOUS'
        else:
            r_color, r_label = '#dc2626', 'RISK-OFF'
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.05); border:1px solid {r_color}40; border-radius:8px; padding:1rem; text-align:center;">
            <div style="color:#64748b; font-size:0.75rem; text-transform:uppercase;">Market Regime</div>
            <div style="font-family:JetBrains Mono; font-size:2rem; font-weight:700; color:{r_color};">{r_score:.0f}</div>
            <div style="color:{r_color}; font-size:0.9rem; font-weight:600;">{r_label}</div>
            <div style="color:#94a3b8; font-size:0.7rem; margin-top:0.3rem;">Tech {regime['technical']:.0f} | Sent {regime['sentiment']:.0f} | Liq {regime['liquidity']:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_momentum:
        # Overall market momentum (average of all sectors)
        if momentum:
            avg_mom = sum(m['momentum_score'] for m in momentum) / len(momentum)
            tailwinds = sum(1 for m in momentum if m['momentum_score'] > 2)
            headwinds = sum(1 for m in momentum if m['momentum_score'] < -2)
        else:
            avg_mom, tailwinds, headwinds = 0, 0, 0
        if avg_mom > 2:
            m_color = '#059669'
        elif avg_mom > -2:
            m_color = '#d97706'
        else:
            m_color = '#dc2626'
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.05); border:1px solid {m_color}40; border-radius:8px; padding:1rem; text-align:center;">
            <div style="color:#64748b; font-size:0.75rem; text-transform:uppercase;">Sector Momentum</div>
            <div style="font-family:JetBrains Mono; font-size:2rem; font-weight:700; color:{m_color};">{avg_mom:+.1f}</div>
            <div style="color:{m_color}; font-size:0.9rem; font-weight:600;">{'POSITIVE' if avg_mom > 2 else 'NEGATIVE' if avg_mom < -2 else 'MIXED'}</div>
            <div style="color:#94a3b8; font-size:0.7rem; margin-top:0.3rem;">{tailwinds} tailwinds | {headwinds} headwinds</div>
        </div>
        """, unsafe_allow_html=True)

    with col_combined:
        cb_active = '🚨' in str(regime.get('circuit_breaker', ''))
        if cb_active:
            bridge_color, bridge_label = '#dc2626', 'DEFENSIVE'
        elif r_score <= 35 and avg_mom > 0:
            bridge_color, bridge_label = '#059669', 'FULL OFFENSE'
        elif r_score <= 60 and avg_mom > 0:
            bridge_color, bridge_label = '#0891b2', 'SELECTIVE BUY'
        elif r_score <= 60:
            bridge_color, bridge_label = '#d97706', 'HOLD / ROTATE'
        elif r_score <= 80:
            bridge_color, bridge_label = '#d97706', 'REDUCE RISK'
        else:
            bridge_color, bridge_label = '#dc2626', 'DEFENSIVE'
        st.markdown(f"""
        <div style="background:rgba(249,115,22,0.06); border:1px solid {bridge_color}40; border-radius:8px; padding:1rem; text-align:center;">
            <div style="color:#ea580c; font-size:0.75rem; text-transform:uppercase; font-weight:700;">Bridge Signal</div>
            <div style="font-family:JetBrains Mono; font-size:1.6rem; font-weight:700; color:{bridge_color}; margin:0.3rem 0;">{bridge_label}</div>
            <div style="color:#94a3b8; font-size:0.7rem;">Quality × Regime × Momentum</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── REGIME ACTION ZONES ──────────────────────────────────────
    if not zones_df.empty:
        st.markdown("<h3>REGIME ACTION ZONES</h3>", unsafe_allow_html=True)
        st.dataframe(zones_df, width='stretch', hide_index=True)
        st.divider()

    # ── PICKS WITH MOMENTUM OVERLAY ──────────────────────────────
    st.markdown("<h3>FILTERED PICKS — WITH MOMENTUM</h3>", unsafe_allow_html=True)
    st.caption("Regime Action from B1×B5 | Momentum Wind shows sector tailwind/headwind from B4")

    if not picks_df.empty and momentum:
        # Build sector momentum lookup
        sector_mom = {m['sector']: m['momentum_score'] for m in momentum}

        # Add momentum columns to picks
        picks_df['Mom_Score'] = picks_df['Sector'].map(
            lambda s: sector_mom.get(s, 0) if isinstance(s, str) else 0
        )
        picks_df['Wind'] = picks_df['Mom_Score'].map(
            lambda m: '🟢 Tailwind' if m > 2 else '🔴 Headwind' if m < -2 else '🟡 Neutral'
        )

        # Conviction: combine regime action + momentum
        def calc_conviction(row):
            action = str(row.get('Regime_Action', ''))
            mom = row.get('Mom_Score', 0)
            if '✅' in action or 'BUY' in action.upper():
                if mom > 2:
                    return '🟢🟢 HIGH CONVICTION BUY'
                elif mom < -2:
                    return '🟡 BUY (headwind)'
                return '🟢 BUY'
            elif '🔴' in action or 'TRIM' in action.upper():
                if mom < -2:
                    return '🔴🔴 STRONG TRIM'
                elif mom > 2:
                    return '🟡 TRIM (tailwind)'
                return '🔴 TRIM'
            else:
                if mom > 2:
                    return '🟢 HOLD → watch for upgrade'
                elif mom < -2:
                    return '🟡 HOLD → watch for downgrade'
                return '⚠️ HOLD'

        picks_df['Conviction'] = picks_df.apply(calc_conviction, axis=1)

        # Tabs by conviction
        buy_picks = picks_df[picks_df['Conviction'].str.contains('BUY', case=False, na=False)]
        hold_picks = picks_df[picks_df['Conviction'].str.contains('HOLD', case=False, na=False)]
        trim_picks = picks_df[picks_df['Conviction'].str.contains('TRIM', case=False, na=False)]

        subtab1, subtab2, subtab3 = st.tabs([
            f"BUY ({len(buy_picks)})",
            f"HOLD ({len(hold_picks)})",
            f"TRIM ({len(trim_picks)})"
        ])

        display_cols = [c for c in ['Company', 'Sector', 'B1_Score', 'Upside %', 'Wind', 'Conviction', 'Rationale']
                        if c in picks_df.columns]

        bridge_col_config = {
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Sector": st.column_config.TextColumn("Sector", width="small"),
            "B1_Score": st.column_config.NumberColumn("Quality", format="%d", width="small"),
            "Upside %": st.column_config.NumberColumn("Upside", format="%+.1f%%", width="small"),
            "Wind": st.column_config.TextColumn("Momentum", width="small"),
            "Conviction": st.column_config.TextColumn("Signal", width="medium"),
            "Rationale": st.column_config.TextColumn("Rationale", width="medium"),
        }

        with subtab1:
            if len(buy_picks) > 0:
                st.dataframe(buy_picks[display_cols].sort_values('B1_Score', ascending=False),
                             column_config=bridge_col_config, width='stretch', hide_index=True)
            else:
                st.info("No BUY signals in current regime")

        with subtab2:
            if len(hold_picks) > 0:
                st.dataframe(hold_picks[display_cols].sort_values('B1_Score', ascending=False),
                             column_config=bridge_col_config, width='stretch', hide_index=True)
            else:
                st.info("No HOLD signals")

        with subtab3:
            if len(trim_picks) > 0:
                st.dataframe(trim_picks[display_cols].sort_values('B1_Score', ascending=False),
                             column_config=bridge_col_config, width='stretch', hide_index=True)
            else:
                st.info("No trim recommendations")

    elif not picks_df.empty:
        # Fallback: no momentum data, show original picks
        buy_picks = picks_df[picks_df['Regime_Action'].str.contains('✅|BUY', case=False, na=False)]
        hold_picks = picks_df[picks_df['Regime_Action'].str.contains('⚠️|HOLD', case=False, na=False)]
        trim_picks = picks_df[picks_df['Regime_Action'].str.contains('🔴|TRIM', case=False, na=False)]

        subtab1, subtab2, subtab3 = st.tabs([
            f"BUY ({len(buy_picks)})", f"HOLD ({len(hold_picks)})", f"TRIM ({len(trim_picks)})"
        ])
        with subtab1:
            st.dataframe(buy_picks, width='stretch', hide_index=True) if len(buy_picks) > 0 else st.info("No BUY signals")
        with subtab2:
            st.dataframe(hold_picks, width='stretch', hide_index=True) if len(hold_picks) > 0 else st.info("No HOLD signals")
        with subtab3:
            st.dataframe(trim_picks, width='stretch', hide_index=True) if len(trim_picks) > 0 else st.info("No trim recommendations")

def display_markets_tab():
    """Markets: Global Indices by Region"""
    st.markdown("<h2>MARKET OVERVIEW</h2>", unsafe_allow_html=True)

    indices = get_market_indices()

    # Market Indices by Region
    region_order = ['Americas', 'EMEA', 'Asia/Pacific', 'Macro']
    for region in region_order:
        region_indices = {k: v for k, v in indices.items() if v.get('region') == region}
        if not region_indices:
            continue

        st.markdown(f"<h3>{region.upper()}</h3>", unsafe_allow_html=True)

        # Build table data for this region
        table_data = []
        for name, data in region_indices.items():
            chg = data.get('change_pct', 0)
            color = '#059669' if chg >= 0 else '#dc2626'
            arrow = '▲' if chg >= 0 else '▼'
            table_data.append({
                'Index': name,
                'Value': data.get('value', 0),
                'Net Chg': data.get('change', 0),
                '%Chg': chg,
                'Sparkline': data.get('sparkline', [])
            })

        region_df = pd.DataFrame(table_data)
        st.dataframe(
            region_df,
            column_config={
                "Index": st.column_config.TextColumn("Market", width="medium"),
                "Value": st.column_config.NumberColumn("Value", format="%.2f"),
                "Net Chg": st.column_config.NumberColumn("Net Chg", format="%+.2f"),
                "%Chg": st.column_config.NumberColumn("%Chg", format="%+.2f%%"),
                "Sparkline": st.column_config.LineChartColumn("5D Trend", width="small", y_min=None, y_max=None),
            },
            width='stretch',
            hide_index=True
        )


def display_scores_tab():
    """Scores: Select a company to see quality radar chart and pillar breakdown"""
    st.markdown("<h2>QUALITY SCORES</h2>", unsafe_allow_html=True)

    b1_df = load_bloque1()

    if b1_df.empty:
        st.info("No scoring data available")
        return

    # Pillar definitions
    pillar_info = {
        'P1': {'name': 'Profitability', 'icon': 'P1', 'metrics': ['ROE (%)', 'ROIC (%)', 'Net Margin (%)'], 'scores': ['S.ROE', 'S.ROIC', 'S.NM']},
        'P2': {'name': 'Growth', 'icon': 'P2', 'metrics': ['Rev Gr 3Y (%)', 'EPS Gr 3Y (%)', 'Op Lev (x)'], 'scores': ['S.RevGr', 'S.EPSGr', 'S.OpLev']},
        'P3': {'name': 'Financial Health', 'icon': 'P3', 'metrics': ['ND/EBITDA', 'Curr Ratio', 'Int Cov (x)'], 'scores': ['S.Debt', 'S.CR', 'S.IC']},
        'P4': {'name': 'Cash Flow', 'icon': 'P4', 'metrics': ['FCF Mar (%)', 'FCF/NI (x)', 'Capex/Rev (%)'], 'scores': ['S.FCFm', 'S.FCFni', 'S.Capex']},
        'P5': {'name': 'Valuation', 'icon': 'P5', 'metrics': ['Fwd P/E', 'EV/EBITDA', 'P/FCF'], 'scores': ['S.PE', 'S.EVEB', 'S.PFCF']},
        'P6': {'name': 'Shareholder Return', 'icon': 'P6', 'metrics': ['Div Yield (%)', 'Payout (%)', 'Buyback (%)'], 'scores': ['S.DivY', 'S.Payout', 'S.Buyb']},
    }

    # Build company list sorted by score
    sorted_df = b1_df.sort_values('Quality_Score', ascending=False).reset_index(drop=True)
    company_options = []
    for _, r in sorted_df.iterrows():
        r_company = safe_str(r.get('Company', ''), 'N/A')
        r_ticker = resolve_ticker(r_company, r, sorted_df.columns)
        r_score = r.get('Quality_Score', 0)
        r_signal = safe_str(r.get('SIGNAL', ''))
        label = f"{r_ticker} — {r_company}  [{r_score:.0f}]  {r_signal}" if r_ticker else f"{r_company}  [{r_score:.0f}]  {r_signal}"
        company_options.append(label)

    # Company selector
    selected = st.selectbox("Select a company", company_options, index=0, key="scores_company_select")

    # Get selected row
    selected_idx = company_options.index(selected)
    row = sorted_df.iloc[selected_idx]

    company = safe_str(row.get('Company', ''), 'N/A')
    sector = safe_str(row.get('GICS Sector', ''), 'N/A')
    score = row.get('Quality_Score', 0)
    signal = safe_str(row.get('SIGNAL', ''), 'N/A')

    # Resolve ticker from Excel or company name mapping
    ticker = resolve_ticker(company, row, sorted_df.columns)

    # Score color
    if score >= 80:
        score_color = "#059669"
    elif score >= 65:
        score_color = "#0891b2"
    elif score >= 50:
        score_color = "#d97706"
    else:
        score_color = "#dc2626"

    # Header card with company info
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, rgba(249,115,22,0.08), rgba(6,182,212,0.05));
                border:1px solid rgba(249,115,22,0.3); border-radius:12px; padding:1.2rem 1.5rem; margin:0.8rem 0 1.2rem 0;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <div>
                <span style="font-family:JetBrains Mono; font-size:1.4rem; font-weight:700; color:#ea580c;">{ticker}</span>
                <span style="color:#64748b; font-size:1rem; margin-left:0.8rem;">{company}</span>
                <br><span style="color:#94a3b8; font-size:0.85rem;">{sector}</span>
            </div>
            <div style="text-align:right;">
                <span style="font-family:JetBrains Mono; font-size:2rem; font-weight:700; color:{score_color};">{score:.0f}</span>
                <span style="color:#64748b; font-size:0.9rem;">/100</span>
                <br><span style="font-size:1rem;">{signal}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── EARNINGS & ANALYST SUMMARY (Dexter-inspired) ────────────
    # Show panels for all companies — uses yfinance when ticker available
    if True:
      try:
        earn_col1, earn_col2 = st.columns(2)
        with earn_col1:
            earnings = get_earnings_info(ticker)
            analyst = get_analyst_data(ticker)

            def fmt_big(val):
                if val is None:
                    return '—'
                if abs(val) >= 1e12:
                    return f"${val/1e12:.1f}T"
                if abs(val) >= 1e9:
                    return f"${val/1e9:.1f}B"
                if abs(val) >= 1e6:
                    return f"${val/1e6:.0f}M"
                return f"${val:,.0f}"

            rev_str = fmt_big(earnings.get('revenue'))
            ni_str = fmt_big(earnings.get('net_income'))
            ebitda_str = fmt_big(earnings.get('ebitda'))
            mcap_str = fmt_big(earnings.get('market_cap'))
            gm = earnings.get('gross_margins')
            gm_str = f"{gm*100:.1f}%" if gm else '—'
            eps_t = earnings.get('eps_trailing')
            eps_f = earnings.get('eps_forward')
            eps_t_str = f"${eps_t:.2f}" if eps_t else '—'
            eps_f_str = f"${eps_f:.2f}" if eps_f else '—'
            next_e = earnings.get('next_earnings', '—') or '—'
            last_e = earnings.get('last_earnings', '—') or '—'

            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.05); border:1px solid rgba(15,23,42,0.08);
                        border-radius:8px; padding:1rem; margin-bottom:0.5rem;">
                <div style="font-weight:700; color:#0891b2; font-size:0.95rem; margin-bottom:0.6rem;">
                    EARNINGS & FUNDAMENTALS
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.3rem 1.5rem; font-size:0.82rem;">
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Revenue</span><span style="color:#1e293b;font-family:JetBrains Mono;">{rev_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Market Cap</span><span style="color:#1e293b;font-family:JetBrains Mono;">{mcap_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Net Income</span><span style="color:#1e293b;font-family:JetBrains Mono;">{ni_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">EBITDA</span><span style="color:#1e293b;font-family:JetBrains Mono;">{ebitda_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Gross Margin</span><span style="color:#1e293b;font-family:JetBrains Mono;">{gm_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">EPS (TTM)</span><span style="color:#1e293b;font-family:JetBrains Mono;">{eps_t_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">EPS (Fwd)</span><span style="color:#1e293b;font-family:JetBrains Mono;">{eps_f_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Next Earnings</span><span style="color:#ea580c;font-family:JetBrains Mono;">{next_e}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Last Earnings</span><span style="color:#1e293b;font-family:JetBrains Mono;">{last_e}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with earn_col2:
            target_m = analyst.get('target_mean')
            target_l = analyst.get('target_low')
            target_h = analyst.get('target_high')
            cur_price = analyst.get('current')
            upside = analyst.get('upside')
            rec = analyst.get('recommendation', '—')
            n_analysts = analyst.get('num_analysts', 0)
            fwd_pe = analyst.get('pe_forward')
            trail_pe = analyst.get('pe_trailing')

            target_str = f"${target_m:.0f}" if target_m else '—'
            range_str = f"${target_l:.0f} — ${target_h:.0f}" if target_l and target_h else '—'
            cur_str = f"${cur_price:.2f}" if cur_price else '—'
            fwd_pe_str = f"{fwd_pe:.1f}x" if fwd_pe else '—'
            trail_pe_str = f"{trail_pe:.1f}x" if trail_pe else '—'

            if upside is not None:
                if upside > 10:
                    up_color = "#059669"
                elif upside > 0:
                    up_color = "#0891b2"
                else:
                    up_color = "#dc2626"
                up_str = f"{upside:+.1f}%"
            else:
                up_color = "#94a3b8"
                up_str = '—'

            rec_colors = {'BUY': '#059669', 'STRONG_BUY': '#059669', 'OUTPERFORM': '#059669', 'OVERWEIGHT': '#059669',
                          'HOLD': '#d97706', 'NEUTRAL': '#d97706', 'EQUAL-WEIGHT': '#d97706',
                          'SELL': '#dc2626', 'UNDERPERFORM': '#dc2626', 'UNDERWEIGHT': '#dc2626'}
            rec_color = rec_colors.get(rec, '#64748b')

            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.05); border:1px solid rgba(15,23,42,0.08);
                        border-radius:8px; padding:1rem; margin-bottom:0.5rem;">
                <div style="font-weight:700; color:#0891b2; font-size:0.95rem; margin-bottom:0.6rem;">
                    ANALYST CONSENSUS ({n_analysts} analysts)
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <div>
                        <span style="font-family:JetBrains Mono; font-size:1.5rem; font-weight:700; color:{rec_color};">{rec}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#64748b;font-size:0.8rem;">Target</span>
                        <span style="font-family:JetBrains Mono; font-size:1.3rem; font-weight:700; color:#1e293b;"> {target_str}</span>
                        <span style="font-family:JetBrains Mono; font-size:1.1rem; font-weight:700; color:{up_color};"> ({up_str})</span>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.3rem 1.5rem; font-size:0.82rem;">
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Current Price</span><span style="color:#1e293b;font-family:JetBrains Mono;">{cur_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Target Range</span><span style="color:#1e293b;font-family:JetBrains Mono;">{range_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Fwd P/E</span><span style="color:#1e293b;font-family:JetBrains Mono;">{fwd_pe_str}</span></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Trail P/E</span><span style="color:#1e293b;font-family:JetBrains Mono;">{trail_pe_str}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

      except Exception as e:
        st.caption(f"Analyst/earnings data unavailable: {str(e)[:80]}")

    # Layout: Radar chart left, pillar bars right
    col_radar, col_bars = st.columns([3, 2])

    with col_radar:
        # Radar chart with 6 quality pillars
        pillar_keys = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
        pillar_values = []
        pillar_labels = []
        for pk in pillar_keys:
            val = row.get(pk, 0)
            if pd.isna(val):
                val = 0
            pillar_values.append(float(val))
            pillar_labels.append(pillar_info[pk]['name'])

        # Close the polygon
        radar_values = pillar_values + [pillar_values[0]]
        radar_labels = pillar_labels + [pillar_labels[0]]

        fig_radar = go.Figure()

        # Portfolio average benchmark (subtle)
        avg_values = []
        for pk in pillar_keys:
            avg_v = b1_df[pk].mean() if pk in b1_df.columns else 50
            avg_values.append(float(avg_v))
        avg_values_r = avg_values + [avg_values[0]]

        fig_radar.add_trace(go.Scatterpolar(
            r=avg_values_r,
            theta=radar_labels,
            fill='toself',
            fillcolor='rgba(107,114,128,0.05)',
            line=dict(color='rgba(107,114,128,0.3)', width=1, dash='dot'),
            marker=dict(size=0),
            name='Portfolio Avg',
            hoverinfo='skip'
        ))

        # Company data
        fig_radar.add_trace(go.Scatterpolar(
            r=radar_values,
            theta=radar_labels,
            fill='toself',
            fillcolor='rgba(249,115,22,0.12)',
            line=dict(color='#ea580c', width=2),
            marker=dict(size=6, color='#ea580c', line=dict(color='#f7f8fa', width=1)),
            name=company[:20]
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                               gridcolor='rgba(15,23,42,0.08)',
                               tickvals=[25, 50, 75, 100],
                               tickfont=dict(size=8, color='#94a3b8'),
                               linecolor='rgba(15,23,42,0.05)'),
                angularaxis=dict(gridcolor='rgba(15,23,42,0.10)',
                                tickfont=dict(size=10, color='#334155'),
                                linecolor='rgba(15,23,42,0.07)'),
                bgcolor='rgba(0,0,0,0)'
            ),
            template='plotly_white', height=420,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='JetBrains Mono', color='#1e293b'),
            margin=dict(l=60, r=60, t=30, b=30),
            showlegend=False
        )
        st.plotly_chart(fig_radar, width='stretch')
        st.caption("Solid = company  |  Dotted = portfolio average")

    with col_bars:
        # Horizontal bar chart of pillars
        st.markdown("<h4 style='margin-top:0;'>PILLAR SCORES</h4>", unsafe_allow_html=True)
        for pk in pillar_keys:
            pinfo = pillar_info[pk]
            val = row.get(pk, 0)
            if pd.isna(val):
                val = 0
            val = float(val)
            # Color based on value
            if val >= 80:
                bar_color = "#059669"
            elif val >= 60:
                bar_color = "#0891b2"
            elif val >= 40:
                bar_color = "#d97706"
            else:
                bar_color = "#dc2626"
            pct = min(val, 100)
            st.markdown(f"""
            <div style="margin-bottom:0.6rem;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.2rem;">
                    <span style="color:#1e293b;">{pinfo['name']}</span>
                    <span style="color:{bar_color}; font-weight:700; font-family:JetBrains Mono;">{val:.0f}</span>
                </div>
                <div style="background:rgba(15,23,42,0.08); border-radius:4px; height:14px; overflow:hidden;">
                    <div style="background:{bar_color}; width:{pct}%; height:100%; border-radius:4px; transition:width 0.3s;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Detailed sub-scores by pillar
    st.markdown("<h3>DETAIL — SUB-SCORES</h3>", unsafe_allow_html=True)

    detail_cols = st.columns(3)
    for i, pk in enumerate(pillar_keys):
        pinfo = pillar_info[pk]
        col_idx = i % 3
        with detail_cols[col_idx]:
            p_val = row.get(pk, 0)
            if pd.isna(p_val):
                p_val = 0
            if p_val >= 80:
                p_color = "#059669"
            elif p_val >= 60:
                p_color = "#0891b2"
            elif p_val >= 40:
                p_color = "#d97706"
            else:
                p_color = "#dc2626"

            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.05); border:1px solid rgba(15,23,42,0.08);
                        border-radius:8px; padding:0.8rem; margin-bottom:0.8rem;">
                <div style="font-weight:700; color:{p_color}; font-size:0.95rem; margin-bottom:0.5rem;">
                    {pinfo['name']} — <span style="font-family:JetBrains Mono;">{p_val:.0f}/100</span>
                </div>
            """, unsafe_allow_html=True)

            for metric, score_col in zip(pinfo['metrics'], pinfo['scores']):
                s_val = row.get(score_col, None)
                m_val = row.get(metric, None)
                s_display = f"{s_val:.0f}" if s_val is not None and pd.notna(s_val) else "—"
                m_display = f"{m_val:.1f}" if m_val is not None and pd.notna(m_val) else "—"
                # Sub-score color
                if s_val is not None and pd.notna(s_val):
                    if float(s_val) >= 75:
                        s_color = "#059669"
                    elif float(s_val) >= 50:
                        s_color = "#0891b2"
                    elif float(s_val) >= 25:
                        s_color = "#d97706"
                    else:
                        s_color = "#dc2626"
                else:
                    s_color = "#94a3b8"

                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; padding:0.15rem 0; font-size:0.82rem;
                            border-bottom:1px solid rgba(15,23,42,0.06);">
                    <span style="color:#64748b;">{metric}</span>
                    <span><span style="color:#94a3b8; margin-right:0.5rem;">{m_display}</span>
                    <span style="color:{s_color}; font-weight:600; font-family:JetBrains Mono;">{s_display}</span></span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    # ── SECTOR TREEMAP ──────────────────────────────────────────
    st.divider()
    st.markdown("<h3>SECTOR TREEMAP</h3>", unsafe_allow_html=True)
    st.caption("Size = Quality Score  |  Color = Signal")

    treemap_df = b1_df[['Company', 'GICS Sector', 'Quality_Score', 'SIGNAL']].copy()
    treemap_df['Company'] = treemap_df['Company'].apply(lambda x: safe_str(x, 'N/A'))
    treemap_df['GICS Sector'] = treemap_df['GICS Sector'].apply(lambda x: safe_str(x, 'Other'))
    treemap_df['SIGNAL'] = treemap_df['SIGNAL'].apply(lambda x: safe_str(x, 'N/A'))
    treemap_df['Quality_Score'] = treemap_df['Quality_Score'].fillna(0)

    # Map signals to numeric for coloring
    signal_color_map = {
        '🚀 STRONG BUY': 2, '✅ BUY': 1, '⚠️ HOLD': 0,
        '🟠 UNDERWEIGHT': -1, '🔴 SELL': -2
    }
    treemap_df['Signal_Num'] = treemap_df['SIGNAL'].map(signal_color_map).fillna(0)

    # Short label for display
    treemap_df['Label'] = treemap_df['Company'].apply(lambda x: x[:18] if len(x) > 18 else x)

    fig_tree = px.treemap(
        treemap_df,
        path=['GICS Sector', 'Label'],
        values='Quality_Score',
        color='Signal_Num',
        color_continuous_scale=['#dc2626', '#ea580c', '#94a3b8', '#0891b2', '#059669'],
        range_color=[-2, 2],
        hover_data={'Company': True, 'Quality_Score': ':.0f', 'SIGNAL': True, 'Signal_Num': False, 'Label': False}
    )
    fig_tree.update_layout(
        template='plotly_white', height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='JetBrains Mono', color='#1e293b'),
        margin=dict(l=5, r=5, t=30, b=5),
        coloraxis_showscale=False
    )
    fig_tree.update_traces(
        textinfo='label+value',
        textfont=dict(size=11),
        hovertemplate='<b>%{customdata[0]}</b><br>Score: %{customdata[1]:.0f}<br>Signal: %{customdata[2]}<extra></extra>'
    )
    st.plotly_chart(fig_tree, width='stretch')


def display_regime_tab():
    """Market Regime — Full indicator dashboard from Bloque 5"""
    st.markdown("<h2>MARKET REGIME DASHBOARD</h2>", unsafe_allow_html=True)

    # Try live data first, fall back to static Excel
    data = get_live_regime()
    is_live = data is not None and data.get('live', False)

    if data is None:
        data = load_regime_full()
        is_live = False

    if data is None:
        st.info("No regime data available")
        return

    # Merge sector rotation from Excel (not available from live feeds)
    if is_live:
        try:
            excel_data = load_regime_full()
            if excel_data:
                data['sectors'] = excel_data.get('sectors', [])
                data['favor'] = excel_data.get('favor', '')
                data['neutral_sectors'] = excel_data.get('neutral_sectors', '')
                data['avoid'] = excel_data.get('avoid', '')
                data['marango_action'] = excel_data.get('marango_action', '')
        except Exception:
            pass

    # Data source badge
    src_label = "LIVE — Yahoo Finance" if is_live else "STATIC — Excel Data"
    src_color = "#059669" if is_live else "#d97706"
    st.markdown(f"""
    <div style="text-align:right; margin-bottom:0.5rem;">
        <span style="background:{src_color}22; color:{src_color}; border:1px solid {src_color}44;
                     border-radius:4px; padding:2px 10px; font-size:0.75rem; font-family:JetBrains Mono;">
            {src_label}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── COMBINED SCORE HEADER ──────────────────────────────────
    combined = data.get('combined_score', 0)
    try:
        combined = float(combined) if combined and not pd.isna(combined) else 0
    except (ValueError, TypeError):
        combined = 0
    if combined >= 70:
        c_color = "#059669"
    elif combined >= 55:
        c_color = "#0891b2"
    elif combined >= 45:
        c_color = "#d97706"
    else:
        c_color = "#dc2626"

    override_text = data.get('override', '')
    action_text = data.get('action', '')

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, rgba(249,115,22,0.08), rgba(6,182,212,0.05));
                border:1px solid rgba(249,115,22,0.3); border-radius:12px; padding:1.2rem 1.5rem; margin-bottom:1.2rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
            <div>
                <span style="color:#64748b; font-size:0.85rem; text-transform:uppercase;">Combined Regime Score</span><br>
                <span style="font-family:JetBrains Mono; font-size:2.5rem; font-weight:700; color:{c_color};">{combined:.0f}</span>
                <span style="color:#94a3b8; font-size:1rem;">/100</span>
            </div>
            <div style="text-align:right; max-width:60%;">
                <span style="font-size:1rem; font-weight:600; color:{c_color};">{safe_str(data.get('combined_status', ''))}</span><br>
                <span style="color:#d97706; font-size:0.85rem;">{override_text}</span>
            </div>
        </div>
        {'<div style="margin-top:0.8rem; padding-top:0.8rem; border-top:1px solid rgba(15,23,42,0.10); color:#1e293b; font-size:0.85rem;"><b>Action:</b> ' + action_text + '</div>' if action_text else ''}
    </div>
    """, unsafe_allow_html=True)

    # ── THREE SCORE GAUGES ─────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    scores = [
        ('Sentiment', data.get('sentiment_score', 0), data.get('sentiment_regime', ''), 'SNT'),
        ('Technical', data.get('tech_score', 0), data.get('tech_regime', ''), 'TEC'),
        ('Liquidity', data.get('liq_score', 0), data.get('liq_regime', ''), 'LIQ'),
    ]

    for col, (name, score_val, regime_text, icon) in zip([col1, col2, col3], scores):
        with col:
            try:
                score_val = float(score_val) if score_val and not pd.isna(score_val) else 50
            except (ValueError, TypeError):
                score_val = 50
            if score_val >= 70:
                s_color = "#059669"
            elif score_val >= 55:
                s_color = "#0891b2"
            elif score_val >= 45:
                s_color = "#d97706"
            else:
                s_color = "#dc2626"

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score_val,
                title={'text': name.upper(), 'font': {'size': 12, 'color': '#64748b', 'family': 'JetBrains Mono'}},
                number={'font': {'color': s_color, 'family': 'JetBrains Mono', 'size': 28}},
                gauge={
                    'axis': {'range': [0, 100], 'tickcolor': '#94a3b8', 'tickwidth': 1,
                             'tickfont': {'size': 9, 'color': '#94a3b8'}},
                    'bar': {'color': s_color, 'thickness': 0.75},
                    'bgcolor': 'rgba(15,23,42,0.04)',
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, 45], 'color': 'rgba(239,68,68,0.06)'},
                        {'range': [45, 55], 'color': 'rgba(245,158,11,0.06)'},
                        {'range': [55, 70], 'color': 'rgba(6,182,212,0.06)'},
                        {'range': [70, 100], 'color': 'rgba(16,185,129,0.06)'}
                    ]
                }
            ))
            fig.update_layout(
                template='plotly_white', height=200,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='JetBrains Mono', color='#1e293b'),
                margin=dict(l=15, r=15, t=35, b=5)
            )
            st.plotly_chart(fig, width='stretch')
            st.markdown(f"<div style='text-align:center; color:#64748b; font-size:0.8rem; margin-top:-0.5rem;'>{regime_text}</div>", unsafe_allow_html=True)

    # ── DIVERGENCE ALERT ───────────────────────────────────────
    div_status = data.get('divergence_status', '')
    div_guidance = data.get('divergence_guidance', '')
    if div_status:
        st.markdown(f"""
        <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2);
                    border-radius:8px; padding:0.8rem 1rem; margin:0.5rem 0;">
            <span style="font-weight:700; color:#d97706;">DIVERGENCE:</span>
            <span style="color:#1e293b;"> {div_status}</span><br>
            <span style="color:#64748b; font-size:0.85rem;">{div_guidance}</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── INDICATOR TABLES ───────────────────────────────────────
    def render_indicator_table(title, indicators, has_thresholds=True):
        st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
        for ind in indicators:
            status = ind.get('status', '')
            if '✅' in status or 'Risk-On' in status:
                status_color = "#059669"
            elif '🔴' in status or 'Risk-Off' in status:
                status_color = "#dc2626"
            else:
                status_color = "#d97706"

            val = ind.get('value', '')
            if isinstance(val, (int, float)):
                try:
                    if pd.isna(val):
                        val_str = '—'
                    elif abs(val) < 10:
                        val_str = f"{val:.2f}"
                    elif abs(val) < 1000:
                        val_str = f"{val:.1f}"
                    else:
                        val_str = f"{val:,.0f}"
                except (ValueError, TypeError):
                    val_str = '—'
            else:
                val_str = safe_str(val) if val else '—'

            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0;
                        border-bottom:1px solid rgba(15,23,42,0.06); font-size:0.88rem;">
                <span style="color:#1e293b; flex:2;">{ind.get('indicator', '')}</span>
                <span style="color:#ea580c; font-family:JetBrains Mono; font-weight:600; flex:1; text-align:center;">{val_str}</span>
                <span style="color:{status_color}; flex:1; text-align:right;">{status}</span>
            </div>
            """, unsafe_allow_html=True)

    # Two columns: Sentiment + Technical left, Liquidity + Triggers right
    col_left, col_right = st.columns(2)

    with col_left:
        render_indicator_table("SENTIMENT & SYSTEMIC RISK", data.get('sentiment_indicators', []))
        st.markdown("")
        # Technical as simpler table
        st.markdown("<h3>TECHNICAL INDICATORS — S&P 500</h3>", unsafe_allow_html=True)
        for ind in data.get('tech_indicators', []):
            score_val = ind.get('score', 0)
            try:
                if isinstance(score_val, (int, float)) and not pd.isna(score_val):
                    if score_val >= 60:
                        s_col = "#059669"
                    elif score_val >= 30:
                        s_col = "#d97706"
                    else:
                        s_col = "#dc2626"
                    score_str = f"{score_val:.0f}"
                else:
                    s_col = "#94a3b8"
                    score_str = "—"
            except (ValueError, TypeError):
                s_col = "#94a3b8"
                score_str = "—"

            val = ind.get('value', '')
            if isinstance(val, (int, float)):
                try:
                    if pd.isna(val):
                        val_str = '—'
                    elif abs(val) < 100:
                        val_str = f"{val:.2f}"
                    else:
                        val_str = f"{val:,.0f}"
                except (ValueError, TypeError):
                    val_str = '—'
            else:
                val_str = safe_str(val) if val else '—'

            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0;
                        border-bottom:1px solid rgba(15,23,42,0.06); font-size:0.88rem;">
                <span style="color:#1e293b; flex:2;">{ind.get('indicator', '')}</span>
                <span style="color:#ea580c; font-family:JetBrains Mono; font-weight:600; flex:1; text-align:center;">{val_str}</span>
                <span style="color:{s_col}; font-family:JetBrains Mono; font-weight:700; flex:1; text-align:right;">{score_str}/100</span>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        render_indicator_table("LIQUIDITY MONITOR", data.get('liq_indicators', []))

    st.divider()

    # ── RISK-OFF TRIGGERS ──────────────────────────────────────
    st.markdown("<h3>RISK-OFF TRIGGERS</h3>", unsafe_allow_html=True)

    trigger_cols = st.columns(3)
    for i, trig in enumerate(data.get('triggers', [])):
        col_idx = i % 3
        triggered = trig.get('triggered', '')
        is_active = '🔴' in triggered or 'YES' in triggered.upper()
        border_color = 'rgba(239,68,68,0.4)' if is_active else 'rgba(15,23,42,0.08)'
        bg = 'rgba(239,68,68,0.08)' if is_active else 'rgba(15,23,42,0.04)'

        with trigger_cols[col_idx]:
            st.markdown(f"""
            <div style="background:{bg}; border:1px solid {border_color};
                        border-radius:8px; padding:0.8rem; margin-bottom:0.6rem; min-height:120px;">
                <div style="font-weight:700; color:{'#dc2626' if is_active else '#1e293b'}; font-size:0.9rem; margin-bottom:0.3rem;">
                    {trig.get('trigger', '')} {triggered}
                </div>
                <div style="color:#64748b; font-size:0.8rem;">
                    Condition: {trig.get('condition', '')}<br>
                    Current: <span style="color:#ea580c; font-family:JetBrains Mono;">{trig.get('current', '')}</span>
                </div>
                <div style="color:#94a3b8; font-size:0.75rem; margin-top:0.3rem;">{trig.get('action', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── SECTOR ROTATION ────────────────────────────────────────
    st.markdown("<h3>SECTOR ROTATION SIGNALS</h3>", unsafe_allow_html=True)

    for sec in data.get('sectors', []):
        signal = sec.get('signal', '')
        if '✅' in signal or 'Overweight' in signal:
            sig_color = "#059669"
        elif '🔴' in signal or 'Underweight' in signal or 'Avoid' in signal:
            sig_color = "#dc2626"
        else:
            sig_color = "#d97706"

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0;
                    border-bottom:1px solid rgba(15,23,42,0.06); font-size:0.88rem;">
            <span style="color:#1e293b; flex:2;">{sec.get('sector', '')}</span>
            <span style="color:#94a3b8; flex:1; text-align:center;">Beta: {sec.get('beta', '')}</span>
            <span style="color:{sig_color}; font-weight:600; flex:1; text-align:right;">{signal}</span>
        </div>
        """, unsafe_allow_html=True)

    # Positioning summary
    st.markdown(f"""
    <div style="background:rgba(249,115,22,0.06); border:1px solid rgba(249,115,22,0.2);
                border-radius:8px; padding:1rem; margin-top:1rem;">
        <div style="font-weight:700; color:#ea580c; margin-bottom:0.5rem;">CURRENT POSITIONING</div>
        <div style="color:#059669; font-size:0.9rem; margin-bottom:0.2rem;"><b>FAVOR:</b> {data.get('favor', '')}</div>
        <div style="color:#d97706; font-size:0.9rem; margin-bottom:0.2rem;"><b>NEUTRAL:</b> {data.get('neutral_sectors', '')}</div>
        <div style="color:#dc2626; font-size:0.9rem; margin-bottom:0.2rem;"><b>AVOID:</b> {data.get('avoid', '')}</div>
        <div style="color:#1e293b; font-size:0.9rem; margin-top:0.5rem; border-top:1px solid rgba(15,23,42,0.10); padding-top:0.5rem;">
            <b>MARANGO:</b> {data.get('marango_action', '')}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# SECTOR ETF MAPPING FOR MOMENTUM
# ============================================

SECTOR_ETFS = {
    'Information Technology': 'XLK',
    'Health Care': 'XLV',
    'Financials': 'XLF',
    'Consumer Discretionary': 'XLY',
    'Communication Services': 'XLC',
    'Industrials': 'XLI',
    'Consumer Staples': 'XLP',
    'Energy': 'XLE',
    'Utilities': 'XLU',
    'Materials': 'XLB',
    'Real Estate': 'XLRE'
}

# Top holdings per sector ETF (SPDR, ~15-25 largest per sector = covers ~80%+ of each ETF)
SECTOR_HOLDINGS = {
    'Information Technology': ['AAPL','MSFT','NVDA','AVGO','CRM','ADBE','AMD','CSCO','ACN','ORCL','INTC','TXN','QCOM','INTU','AMAT','NOW','IBM','ADI','LRCX','KLAC','SNPS','CDNS','PANW','MCHP','FTNT'],
    'Health Care': ['LLY','UNH','JNJ','ABBV','MRK','TMO','ABT','DHR','AMGN','PFE','ISRG','BSX','SYK','MDT','GILD','VRTX','ELV','REGN','ZTS','BDX','CI','HCA','IDXX','EW','A'],
    'Financials': ['BRK-B','JPM','V','MA','BAC','WFC','GS','SPGI','MS','AXP','BLK','C','SCHW','PGR','CB','MMC','ICE','CME','AON','MCO','MET','AFL','TRV','AIG','USB'],
    'Consumer Discretionary': ['AMZN','TSLA','HD','MCD','NKE','LOW','BKNG','SBUX','TJX','ABNB','CMG','ORLY','MAR','GM','F','DHI','ROST','LEN','YUM','EBAY','GRMN','ULTA','DRI','POOL','BBY'],
    'Communication Services': ['META','GOOGL','GOOG','NFLX','DIS','CMCSA','T','VZ','TMUS','CHTR','EA','TTWO','WBD','MTCH','LYV','OMC','PARA','FOXA','FOX','IPG','NWSA','NWS'],
    'Industrials': ['GE','CAT','RTX','UNP','HON','BA','DE','LMT','UPS','ADP','ETN','ITW','NOC','WM','GD','CSX','EMR','NSC','PH','TDG','CARR','JCI','FAST','PCAR','CTAS'],
    'Consumer Staples': ['PG','KO','PEP','COST','WMT','PM','MDLZ','MO','CL','TGT','KMB','GIS','SYY','ADM','STZ','HSY','KHC','KDP','CLX','MKC','SJM','CHD','CAG','HRL','K'],
    'Energy': ['XOM','CVX','COP','EOG','SLB','MPC','PSX','PXD','VLO','OXY','WMB','HES','DVN','HAL','KMI','FANG','BKR','TRGP','OKE','CTRA','MRO','APA','EQT','DINO','MTDR'],
    'Utilities': ['NEE','SO','DUK','CEG','SRE','AEP','D','EXC','XEL','ED','PEG','WEC','ES','AWK','EIX','DTE','FE','PPL','AEE','CMS','CNP','EVRG','ATO','NI','LNT'],
    'Materials': ['LIN','APD','SHW','FCX','ECL','NEM','NUE','VMC','MLM','DOW','DD','PPG','CTVA','CF','IFF','CE','ALB','LYB','BALL','PKG','IP','EMN','FMC','MOS','SEE'],
    'Real Estate': ['PLD','AMT','EQIX','CCI','PSA','SPG','O','WELL','DLR','VICI','AVB','SBAC','EQR','WY','ARE','VTR','MAA','ESS','UDR','HST','PEAK','CPT','KIM','REG','BXP']
}

@st.cache_data(ttl=3600)
def get_sector_breadth():
    """Calculate sector breadth: % of stocks above 200-DMA and 50-DMA for each sector"""
    try:
        all_tickers = []
        for tickers in SECTOR_HOLDINGS.values():
            all_tickers.extend(tickers)
        all_tickers = list(set(all_tickers))

        # Download 1 year of data for all stocks
        data = yf.download(all_tickers, period='1y', progress=False)['Close']
        if data.empty:
            return None

        results = []
        for sector, tickers in SECTOR_HOLDINGS.items():
            above_200 = 0
            above_50 = 0
            golden_cross = 0
            valid = 0

            for ticker in tickers:
                if ticker not in data.columns:
                    continue
                prices = data[ticker].dropna()
                if len(prices) < 200:
                    continue
                valid += 1
                current = prices.iloc[-1]
                ma200 = prices.rolling(200).mean().iloc[-1]
                ma50 = prices.rolling(50).mean().iloc[-1]

                if current > ma200:
                    above_200 += 1
                if current > ma50:
                    above_50 += 1
                if ma50 > ma200:
                    golden_cross += 1

            if valid == 0:
                continue

            pct_200 = (above_200 / valid) * 100
            pct_50 = (above_50 / valid) * 100
            pct_gc = (golden_cross / valid) * 100

            # Pillar 1B score: Breadth & Volume Confirmation (from B4 framework)
            if pct_200 >= 80:
                breadth_score = 90
                breadth_signal = 'Broad participation — sustainable rally'
            elif pct_200 >= 60:
                breadth_score = 60
                breadth_signal = 'Healthy breadth — trend intact'
            elif pct_200 >= 40:
                breadth_score = 20
                breadth_signal = 'Mixed signals — narrowing leadership'
            elif pct_200 >= 20:
                breadth_score = -25
                breadth_signal = 'Deteriorating breadth — trend weakening'
            else:
                breadth_score = -75
                breadth_signal = 'Washout — potential bottoming signal'

            results.append({
                'sector': sector,
                'etf': SECTOR_ETFS.get(sector, ''),
                'stocks_analyzed': valid,
                'above_200dma': above_200,
                'pct_above_200dma': round(pct_200, 1),
                'above_50dma': above_50,
                'pct_above_50dma': round(pct_50, 1),
                'golden_cross_pct': round(pct_gc, 1),
                'breadth_score': breadth_score,
                'breadth_signal': breadth_signal
            })

        return sorted(results, key=lambda x: x['pct_above_200dma'], reverse=True)

    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_sector_momentum():
    """Calculate sector relative strength vs S&P 500 over multiple timeframes"""
    try:
        # Download SPY + all sector ETFs
        tickers = ['SPY'] + list(SECTOR_ETFS.values())
        data = yf.download(tickers, period='1y', progress=False)['Close']

        if data.empty:
            return None

        results = []
        spy = data['SPY']

        for sector, etf in SECTOR_ETFS.items():
            if etf not in data.columns:
                continue
            etf_data = data[etf]

            # Calculate returns over different periods
            def calc_return(series, days):
                if len(series) < days:
                    return None
                return ((series.iloc[-1] / series.iloc[-days]) - 1) * 100

            ret_1m = calc_return(etf_data, 21)
            ret_3m = calc_return(etf_data, 63)
            ret_6m = calc_return(etf_data, 126)
            ret_12m = calc_return(etf_data, 252)

            spy_1m = calc_return(spy, 21)
            spy_3m = calc_return(spy, 63)
            spy_6m = calc_return(spy, 126)
            spy_12m = calc_return(spy, 252)

            # Relative strength = sector return - SPY return
            rel_1m = (ret_1m - spy_1m) if ret_1m is not None and spy_1m is not None else None
            rel_3m = (ret_3m - spy_3m) if ret_3m is not None and spy_3m is not None else None
            rel_6m = (ret_6m - spy_6m) if ret_6m is not None and spy_6m is not None else None
            rel_12m = (ret_12m - spy_12m) if ret_12m is not None and spy_12m is not None else None

            # Momentum score: weighted average of relative strength
            scores = []
            if rel_3m is not None:
                scores.append(rel_3m * 0.40)
            if rel_6m is not None:
                scores.append(rel_6m * 0.35)
            if rel_12m is not None:
                scores.append(rel_12m * 0.25)
            momentum_score = sum(scores) if scores else 0

            # Sparkline data (last 60 trading days of relative performance)
            if len(etf_data) > 60 and len(spy) > 60:
                rel_perf = (etf_data / spy).iloc[-60:].tolist()
            else:
                rel_perf = []

            results.append({
                'sector': sector,
                'etf': etf,
                'ret_1m': ret_1m,
                'ret_3m': ret_3m,
                'ret_6m': ret_6m,
                'ret_12m': ret_12m,
                'rel_1m': rel_1m,
                'rel_3m': rel_3m,
                'rel_6m': rel_6m,
                'rel_12m': rel_12m,
                'momentum_score': momentum_score,
                'sparkline': rel_perf
            })

        return sorted(results, key=lambda x: x['momentum_score'], reverse=True)

    except Exception as e:
        st.error(f"Error loading sector momentum: {str(e)}")
        return None


def display_momentum_tab():
    """Industry Momentum — Sector relative strength vs S&P 500"""
    st.markdown("<h2>INDUSTRY MOMENTUM — BLOQUE 4</h2>", unsafe_allow_html=True)
    st.caption("Sector relative strength vs S&P 500 | Tailwinds & Headwinds")

    momentum = get_sector_momentum()
    if momentum is None:
        st.info("Loading sector momentum data...")
        return

    # Portfolio sector weights from B1
    b1_df = load_bloque1()
    sector_counts = {}
    if not b1_df.empty and 'GICS Sector' in b1_df.columns:
        sector_counts = b1_df['GICS Sector'].value_counts().to_dict()
    total_holdings = sum(sector_counts.values()) if sector_counts else 1

    # Summary cards: Tailwinds vs Headwinds
    tailwinds = [m for m in momentum if m['momentum_score'] > 2]
    headwinds = [m for m in momentum if m['momentum_score'] < -2]

    col_tw, col_hw = st.columns(2)
    with col_tw:
        tw_text = ', '.join([m['sector'] for m in tailwinds]) if tailwinds else 'None'
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3);
                    border-radius:8px; padding:1rem; margin-bottom:1rem;">
            <div style="color:#059669; font-weight:700; font-size:1rem; margin-bottom:0.3rem;">TAILWINDS ({len(tailwinds)})</div>
            <div style="color:#1e293b; font-size:0.9rem;">{tw_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hw:
        hw_text = ', '.join([m['sector'] for m in headwinds]) if headwinds else 'None'
        st.markdown(f"""
        <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3);
                    border-radius:8px; padding:1rem; margin-bottom:1rem;">
            <div style="color:#dc2626; font-weight:700; font-size:1rem; margin-bottom:0.3rem;">HEADWINDS ({len(headwinds)})</div>
            <div style="color:#1e293b; font-size:0.9rem;">{hw_text}</div>
        </div>
        """, unsafe_allow_html=True)

    # Momentum bar chart
    sectors = [m['sector'] for m in momentum]
    scores = [m['momentum_score'] for m in momentum]
    colors = ['#059669' if s > 2 else '#dc2626' if s < -2 else '#d97706' for s in scores]

    fig = go.Figure(go.Bar(
        y=sectors,
        x=scores,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{s:+.1f}" for s in scores],
        textposition='outside',
        textfont=dict(family='JetBrains Mono', size=11)
    ))
    fig.add_vline(x=0, line_color='rgba(15,23,42,0.16)', line_width=1)
    fig.update_layout(
        template='plotly_white', height=400,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='JetBrains Mono', color='#1e293b'),
        margin=dict(l=10, r=60, t=30, b=10),
        xaxis=dict(title='Momentum Score (Relative Strength)', gridcolor='rgba(15,23,42,0.07)'),
        yaxis=dict(autorange='reversed'),
        showlegend=False
    )
    st.plotly_chart(fig, width='stretch')

    st.divider()

    # Detailed table
    st.markdown("<h3>SECTOR DETAIL</h3>", unsafe_allow_html=True)

    for m in momentum:
        sector = m['sector']
        score = m['momentum_score']
        holdings = sector_counts.get(sector, 0)
        weight = (holdings / total_holdings * 100) if total_holdings > 0 else 0

        if score > 5:
            signal = 'STRONG TAILWIND'
            sig_color = '#059669'
        elif score > 2:
            signal = 'TAILWIND'
            sig_color = '#059669'
        elif score > -2:
            signal = 'NEUTRAL'
            sig_color = '#d97706'
        elif score > -5:
            signal = 'HEADWIND'
            sig_color = '#dc2626'
        else:
            signal = 'STRONG HEADWIND'
            sig_color = '#dc2626'

        def fmt_ret(val):
            if val is None:
                return '—'
            color = '#059669' if val > 0 else '#dc2626'
            return f"<span style='color:{color};font-family:JetBrains Mono;'>{val:+.1f}%</span>"

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0;
                    border-bottom:1px solid rgba(15,23,42,0.08); font-size:0.88rem;">
            <div style="flex:2;">
                <span style="color:#1e293b; font-weight:600;">{sector}</span>
                <span style="color:#94a3b8; font-size:0.8rem; margin-left:0.5rem;">({m['etf']}) · {holdings} holdings · {weight:.0f}%</span>
            </div>
            <div style="flex:3; display:flex; gap:1rem; justify-content:center;">
                <span style="color:#64748b; font-size:0.8rem;">1M:</span>{fmt_ret(m['rel_1m'])}
                <span style="color:#64748b; font-size:0.8rem;">3M:</span>{fmt_ret(m['rel_3m'])}
                <span style="color:#64748b; font-size:0.8rem;">6M:</span>{fmt_ret(m['rel_6m'])}
                <span style="color:#64748b; font-size:0.8rem;">12M:</span>{fmt_ret(m['rel_12m'])}
            </div>
            <div style="flex:1; text-align:right;">
                <span style="color:{sig_color}; font-weight:600;">{signal}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── SECTOR BREADTH ANALYSIS (Pillar 1B from B4 framework) ──
    st.markdown("<h3>SECTOR BREADTH ANALYSIS</h3>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-size:0.85rem; margin-bottom:1rem;'>Full sector breadth: % of ALL stocks in each SPDR sector ETF above key moving averages. Based on ~25 largest holdings per sector.</div>", unsafe_allow_html=True)

    breadth = get_sector_breadth()
    if breadth:
        # Overall market breadth summary
        avg_200 = sum(b['pct_above_200dma'] for b in breadth) / len(breadth)
        avg_50 = sum(b['pct_above_50dma'] for b in breadth) / len(breadth)
        strong_sectors = len([b for b in breadth if b['pct_above_200dma'] >= 60])
        weak_sectors = len([b for b in breadth if b['pct_above_200dma'] < 40])

        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        for col, label, val, fmt, ref in [
            (col_b1, 'AVG BREADTH 200-DMA', avg_200, f'{avg_200:.0f}%', 'of stocks'),
            (col_b2, 'AVG BREADTH 50-DMA', avg_50, f'{avg_50:.0f}%', 'of stocks'),
            (col_b3, 'STRONG SECTORS', strong_sectors, str(strong_sectors), '>60% above 200-DMA'),
            (col_b4, 'WEAK SECTORS', weak_sectors, str(weak_sectors), '<40% above 200-DMA')
        ]:
            color = '#059669' if (isinstance(val, (int,float)) and ((label.startswith('AVG') and val >= 60) or (label == 'STRONG SECTORS' and val >= 6))) else '#dc2626' if (isinstance(val, (int,float)) and ((label.startswith('AVG') and val < 40) or (label == 'WEAK SECTORS' and val >= 4))) else '#d97706'
            with col:
                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.04); border:1px solid rgba(15,23,42,0.10);
                            border-radius:8px; padding:0.8rem; text-align:center;">
                    <div style="color:#64748b; font-size:0.75rem; text-transform:uppercase;">{label}</div>
                    <div style="font-family:JetBrains Mono; font-size:1.5rem; font-weight:700; color:{color};">{fmt}</div>
                    <div style="color:#94a3b8; font-size:0.7rem;">{ref}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("")

        # Breadth horizontal bar chart
        b_sectors = [b['sector'].replace('Information Technology', 'Info Tech').replace('Consumer Discretionary', 'Cons Disc').replace('Consumer Staples', 'Cons Staples').replace('Communication Services', 'Comm Services') for b in breadth]
        b_200 = [b['pct_above_200dma'] for b in breadth]
        b_50 = [b['pct_above_50dma'] for b in breadth]

        fig_b = go.Figure()
        fig_b.add_trace(go.Bar(
            y=b_sectors, x=b_200, orientation='h', name='Above 200-DMA',
            marker=dict(color='rgba(249,115,22,0.8)'),
            text=[f"{v:.0f}%" for v in b_200], textposition='inside',
            textfont=dict(family='JetBrains Mono', size=10, color='white')
        ))
        fig_b.add_trace(go.Bar(
            y=b_sectors, x=b_50, orientation='h', name='Above 50-DMA',
            marker=dict(color='rgba(6,182,212,0.6)'),
            text=[f"{v:.0f}%" for v in b_50], textposition='inside',
            textfont=dict(family='JetBrains Mono', size=10, color='white')
        ))
        fig_b.add_vline(x=60, line_dash='dash', line_color='rgba(16,185,129,0.4)', line_width=1,
                        annotation_text='Healthy (60%)', annotation_position='top',
                        annotation=dict(font=dict(size=9, color='#059669')))
        fig_b.add_vline(x=40, line_dash='dash', line_color='rgba(239,68,68,0.4)', line_width=1,
                        annotation_text='Weak (40%)', annotation_position='bottom',
                        annotation=dict(font=dict(size=9, color='#dc2626')))
        fig_b.update_layout(
            template='plotly_white', height=380, barmode='group',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='JetBrains Mono', color='#1e293b'),
            margin=dict(l=10, r=30, t=30, b=10),
            xaxis=dict(title='% of Stocks', range=[0, 105], gridcolor='rgba(15,23,42,0.07)'),
            yaxis=dict(autorange='reversed'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=10))
        )
        st.plotly_chart(fig_b, width='stretch')

        # Detailed breadth table
        for b in breadth:
            pct200 = b['pct_above_200dma']
            pct50 = b['pct_above_50dma']
            gc = b['golden_cross_pct']
            score = b['breadth_score']

            c200 = '#059669' if pct200 >= 60 else '#dc2626' if pct200 < 40 else '#d97706'
            c50 = '#059669' if pct50 >= 60 else '#dc2626' if pct50 < 40 else '#d97706'
            c_score = '#059669' if score >= 50 else '#dc2626' if score < 0 else '#d97706'

            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0;
                        border-bottom:1px solid rgba(15,23,42,0.06); font-size:0.85rem;">
                <span style="color:#1e293b; font-weight:600; flex:2;">{b['sector']} <span style="color:#94a3b8; font-size:0.75rem;">({b['etf']} · {b['stocks_analyzed']} stocks)</span></span>
                <span style="flex:1; text-align:center;"><span style="color:#64748b; font-size:0.75rem;">200-DMA:</span> <span style="color:{c200}; font-family:JetBrains Mono; font-weight:700;">{pct200:.0f}%</span></span>
                <span style="flex:1; text-align:center;"><span style="color:#64748b; font-size:0.75rem;">50-DMA:</span> <span style="color:{c50}; font-family:JetBrains Mono; font-weight:700;">{pct50:.0f}%</span></span>
                <span style="flex:1; text-align:center;"><span style="color:#64748b; font-size:0.75rem;">Golden Cross:</span> <span style="color:#0891b2; font-family:JetBrains Mono;">{gc:.0f}%</span></span>
                <span style="flex:1; text-align:right; color:{c_score}; font-family:JetBrains Mono; font-weight:700;">{score:+d}/100</span>
            </div>
            """, unsafe_allow_html=True)

        # Pillar 1 composite score explanation
        st.markdown("""
        <div style="margin-top:1rem; padding:0.8rem; background:rgba(249,115,22,0.06); border:1px solid rgba(249,115,22,0.15); border-radius:8px;">
            <div style="color:#ea580c; font-weight:700; font-size:0.85rem; margin-bottom:0.3rem;">PILLAR 1 METHODOLOGY (Bloque 4)</div>
            <div style="color:#64748b; font-size:0.8rem;">
                Breadth Score: >80% above 200-DMA = +90 | 60-80% = +60 | 40-60% = +20 | 20-40% = -25 | <20% = -75<br>
                Pillar 1 = (Relative Strength x 60%) + (Breadth x 40%) | Updated hourly from Yahoo Finance
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Loading sector breadth data...")


def display_analytics_tab():
    """Portfolio Analytics — Concentration, exposure, diversification"""
    st.markdown("<h2>PORTFOLIO ANALYTICS</h2>", unsafe_allow_html=True)

    df = load_bloque1()
    if df.empty:
        st.info("No portfolio data available")
        return

    total = len(df)

    # ── SECTOR CONCENTRATION ──────────────────────────────────
    col_pie, col_bars = st.columns([1, 1])

    with col_pie:
        st.markdown("<h3>SECTOR ALLOCATION</h3>", unsafe_allow_html=True)
        sector_counts = df['GICS Sector'].value_counts()
        fig = px.pie(
            values=sector_counts.values,
            names=sector_counts.index,
            color_discrete_sequence=['#ea580c', '#0891b2', '#059669', '#9333ea', '#db2777',
                                     '#d97706', '#0d9488', '#4f46e5', '#dc2626', '#65a30d', '#64748b']
        )
        fig.update_layout(
            template='plotly_white', height=380,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='JetBrains Mono', color='#1e293b'),
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(font=dict(size=10))
        )
        fig.update_traces(textinfo='label+percent', textfont_size=10)
        st.plotly_chart(fig, width='stretch')

    with col_bars:
        st.markdown("<h3>QUALITY BY SECTOR</h3>", unsafe_allow_html=True)
        sector_avg = df.groupby('GICS Sector')['Quality_Score'].mean().sort_values(ascending=True)
        colors = ['#059669' if v >= 70 else '#0891b2' if v >= 60 else '#d97706' if v >= 50 else '#dc2626' for v in sector_avg.values]
        fig = go.Figure(go.Bar(
            y=sector_avg.index,
            x=sector_avg.values,
            orientation='h',
            marker=dict(color=colors),
            text=[f"{v:.0f}" for v in sector_avg.values],
            textposition='outside',
            textfont=dict(family='JetBrains Mono', size=11)
        ))
        fig.update_layout(
            template='plotly_white', height=380,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='JetBrains Mono', color='#1e293b'),
            margin=dict(l=10, r=50, t=10, b=10),
            xaxis=dict(range=[0, 100], gridcolor='rgba(15,23,42,0.07)'),
            showlegend=False
        )
        st.plotly_chart(fig, width='stretch')

    st.divider()

    # ── CONCENTRATION METRICS ──────────────────────────────────
    st.markdown("<h3>CONCENTRATION ANALYSIS</h3>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    # Top sector weight
    top_sector = sector_counts.index[0]
    top_sector_pct = sector_counts.values[0] / total * 100

    # Herfindahl index (sector concentration)
    weights = (sector_counts.values / total)
    hhi = (weights ** 2).sum() * 10000  # Scale to 0-10000

    # Effective number of sectors
    eff_sectors = 1 / (weights ** 2).sum() if (weights ** 2).sum() > 0 else 0

    with col1:
        st.metric("Total Holdings", f"{total}")
    with col2:
        st.metric("Sectors", f"{len(sector_counts)}")
    with col3:
        st.metric("Top Sector", f"{top_sector}", delta=f"{top_sector_pct:.0f}%")
    with col4:
        hhi_label = "High" if hhi > 2500 else "Moderate" if hhi > 1500 else "Low"
        st.metric("Concentration (HHI)", f"{hhi:.0f}", delta=hhi_label)

    st.divider()

    # ── SIGNAL DISTRIBUTION ────────────────────────────────────
    st.markdown("<h3>SIGNAL BREAKDOWN</h3>", unsafe_allow_html=True)

    if 'SIGNAL' in df.columns:
        col_sig, col_quality = st.columns(2)

        with col_sig:
            # Signal by sector heatmap-style
            signal_sector = pd.crosstab(df['GICS Sector'], df['SIGNAL'])
            for sig_col in signal_sector.columns:
                signal_sector[sig_col] = signal_sector[sig_col]

            st.dataframe(
                signal_sector,
                width='stretch'
            )

        with col_quality:
            # Quality distribution histogram
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=df['Quality_Score'], nbinsx=15,
                marker=dict(color='#ea580c'),
                name='All'
            ))
            fig.add_vline(x=df['Quality_Score'].mean(), line_dash="dash", line_color="#0891b2",
                          annotation_text=f"Avg: {df['Quality_Score'].mean():.1f}")
            fig.add_vline(x=df['Quality_Score'].median(), line_dash="dot", line_color="#059669",
                          annotation_text=f"Median: {df['Quality_Score'].median():.1f}")
            fig.update_layout(
                template='plotly_white', height=300,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='JetBrains Mono', color='#1e293b'),
                xaxis_title="Quality Score", yaxis_title="Count",
                margin=dict(l=0, r=0, t=30, b=40),
                showlegend=False
            )
            st.plotly_chart(fig, width='stretch')

    st.divider()

    # ── TOP & BOTTOM HOLDINGS ──────────────────────────────────
    st.markdown("<h3>TOP 10 vs BOTTOM 10</h3>", unsafe_allow_html=True)

    col_top, col_bot = st.columns(2)

    with col_top:
        st.markdown("**TOP 10 — Highest Quality**")
        top10 = df.nlargest(10, 'Quality_Score')
        for i, (_, row) in enumerate(top10.iterrows(), 1):
            ticker = safe_str(row.get('Ticker', ''))
            company = safe_str(row.get('Company', ''), 'N/A')
            score = row.get('Quality_Score', 0)
            signal = safe_str(row.get('SIGNAL', ''))
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:0.3rem 0;
                        border-bottom:1px solid rgba(15,23,42,0.06); font-size:0.85rem;">
                <span style="color:#94a3b8; width:1.5rem;">{i}.</span>
                <span style="color:#ea580c; font-family:JetBrains Mono; width:4rem;">{ticker}</span>
                <span style="color:#1e293b; flex:1;">{company[:22]}</span>
                <span style="color:#059669; font-family:JetBrains Mono; font-weight:600;">{score:.0f}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_bot:
        st.markdown("**BOTTOM 10 — Review Required**")
        bot10 = df.nsmallest(10, 'Quality_Score')
        for i, (_, row) in enumerate(bot10.iterrows(), 1):
            ticker = safe_str(row.get('Ticker', ''))
            company = safe_str(row.get('Company', ''), 'N/A')
            score = row.get('Quality_Score', 0)
            signal = safe_str(row.get('SIGNAL', ''))
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:0.3rem 0;
                        border-bottom:1px solid rgba(15,23,42,0.06); font-size:0.85rem;">
                <span style="color:#94a3b8; width:1.5rem;">{i}.</span>
                <span style="color:#ea580c; font-family:JetBrains Mono; width:4rem;">{ticker}</span>
                <span style="color:#1e293b; flex:1;">{company[:22]}</span>
                <span style="color:#dc2626; font-family:JetBrains Mono; font-weight:600;">{score:.0f}</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── PILLAR AVERAGES ────────────────────────────────────────
    st.markdown("<h3>PORTFOLIO PILLAR AVERAGES</h3>", unsafe_allow_html=True)

    pillar_names = {'P1': 'Profitability', 'P2': 'Growth', 'P3': 'Fin. Health',
                    'P4': 'Cash Flow', 'P5': 'Valuation', 'P6': 'Shareholder Ret.'}
    pillar_cols = [p for p in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'] if p in df.columns]

    if pillar_cols:
        avgs = [df[p].mean() for p in pillar_cols]
        labels = [pillar_names.get(p, p) for p in pillar_cols]
        # Close polygon
        avgs_r = avgs + [avgs[0]]
        labels_r = labels + [labels[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=avgs_r, theta=labels_r,
            fill='toself',
            fillcolor='rgba(249,115,22,0.15)',
            line=dict(color='#ea580c', width=2.5),
            marker=dict(size=8, color='#ea580c'),
            name='Portfolio Avg'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                               gridcolor='rgba(15,23,42,0.10)',
                               tickvals=[20, 40, 60, 80, 100],
                               tickfont=dict(size=9, color='#94a3b8')),
                angularaxis=dict(gridcolor='rgba(15,23,42,0.10)',
                                tickfont=dict(size=11, color='#1e293b')),
                bgcolor='rgba(0,0,0,0)'
            ),
            template='plotly_white', height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='JetBrains Mono', color='#1e293b'),
            margin=dict(l=60, r=60, t=40, b=40),
            showlegend=False
        )
        st.plotly_chart(fig, width='stretch')

        # Pillar stats
        pcols = st.columns(len(pillar_cols))
        for i, p in enumerate(pillar_cols):
            with pcols[i]:
                avg = df[p].mean()
                mn = df[p].min()
                mx = df[p].max()
                color = '#059669' if avg >= 65 else '#0891b2' if avg >= 50 else '#d97706' if avg >= 35 else '#dc2626'
                st.markdown(f"""
                <div style="text-align:center;">
                    <div style="color:#64748b; font-size:0.75rem;">{pillar_names.get(p, p)}</div>
                    <div style="color:{color}; font-family:JetBrains Mono; font-size:1.3rem; font-weight:700;">{avg:.0f}</div>
                    <div style="color:#94a3b8; font-size:0.7rem;">{mn:.0f} — {mx:.0f}</div>
                </div>
                """, unsafe_allow_html=True)


def display_holdings_tab():
    """Holdings with sparklines, insider trades, analyst consensus, and fundamental filters"""
    st.markdown("<h2>PORTFOLIO HOLDINGS</h2>", unsafe_allow_html=True)

    df = load_bloque1()
    live_prices = {}

    # Resolve tickers from Excel or company name mapping
    if 'Company' in df.columns:
        df['Ticker'] = df.apply(lambda r: resolve_ticker(safe_str(r.get('Company', '')), r, df.columns), axis=1)

    if 'Ticker' in df.columns:
        tickers_list = df['Ticker'].dropna().unique().tolist()
        tickers_list = [t for t in tickers_list if isinstance(t, str) and len(t.strip()) > 0]
        live_prices = get_live_prices(tickers_list)

        if live_prices:
            df['Live_Price'] = df['Ticker'].map(lambda t: live_prices.get(t, {}).get('price', None) if isinstance(t, str) else None)
            df['Daily_Change'] = df['Ticker'].map(lambda t: live_prices.get(t, {}).get('change_pct', 0) if isinstance(t, str) else 0)
            df['5D_Trend'] = df['Ticker'].map(lambda t: live_prices.get(t, {}).get('sparkline', []) if isinstance(t, str) else [])

    # ── FILTERS ──────────────────────────────────────────────────
    filter_row1_c1, filter_row1_c2, filter_row1_c3, filter_row1_c4 = st.columns([2, 2, 1, 1])
    with filter_row1_c1:
        sectors = ['All'] + sorted(df['GICS Sector'].dropna().unique().tolist()) if 'GICS Sector' in df.columns else ['All']
        selected_sector = st.selectbox("Sector", sectors, key="holdings_sector")
    with filter_row1_c2:
        if 'SIGNAL' in df.columns:
            signals = ['All'] + sorted(df['SIGNAL'].dropna().unique().tolist())
            selected_signal = st.selectbox("Signal", signals, key="holdings_signal")
        else:
            selected_signal = 'All'
    with filter_row1_c3:
        search_ticker = st.text_input("Search", placeholder="Ticker...", key="holdings_search")
    with filter_row1_c4:
        st.write("")
        st.write("")
        marango_only = st.checkbox("Marango only", value=False, key="holdings_marango",
                                   help="Show only actual Marango Equity Fund positions")

    # Fundamental screener filters (Dexter-inspired — uses Excel data for speed)
    with st.expander("Fundamental Screener", expanded=False):
        fund_c1, fund_c2, fund_c3, fund_c4 = st.columns(4)
        with fund_c1:
            min_quality = st.slider("Min Quality Score", 0, 100, 0, key="hf_min_quality")
        with fund_c2:
            min_p1 = st.slider("Min Profitability (P1)", 0, 100, 0, key="hf_min_p1")
        with fund_c3:
            min_p3 = st.slider("Min Financial Health (P3)", 0, 100, 0, key="hf_min_p3")
        with fund_c4:
            min_p5 = st.slider("Min Valuation (P5)", 0, 100, 0, key="hf_min_p5")
        st.caption("Tip: For detailed Analyst Consensus, Insider Trades & Earnings data, select a company in the SCORES tab.")

    # Apply filters
    filtered_df = df.copy()
    if selected_sector != 'All' and 'GICS Sector' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['GICS Sector'] == selected_sector]
    if selected_signal != 'All' and 'SIGNAL' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['SIGNAL'] == selected_signal]
    if search_ticker and 'Ticker' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Ticker'].str.contains(search_ticker.upper(), case=False, na=False) |
                                  filtered_df['Company'].str.contains(search_ticker, case=False, na=False)]
    if marango_only and 'Marango_Holding' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Marango_Holding'] == True]

    # Fundamental screener filters
    if min_quality > 0 and 'Quality_Score' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Quality_Score'] >= min_quality]
    if min_p1 > 0 and 'P1' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['P1'].fillna(0) >= min_p1]
    if min_p3 > 0 and 'P3' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['P3'].fillna(0) >= min_p3]
    if min_p5 > 0 and 'P5' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['P5'].fillna(0) >= min_p5]

    # ── COLUMN SETUP ─────────────────────────────────────────────
    holdings_cols = ['Company', 'GICS Sector', 'Quality_Score', 'SIGNAL', 'P1', 'P2', 'P3', 'P4', 'P5']
    col_config = {
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "Marango_Holding": st.column_config.CheckboxColumn("Marango", width="small"),
        "GICS Sector": st.column_config.TextColumn("Sector", width="small"),
        "Quality_Score": st.column_config.ProgressColumn(
            "Quality",
            min_value=0,
            max_value=100,
            format="%d",
            width="small"
        ),
        "SIGNAL": st.column_config.TextColumn("Signal", width="small"),
        "P1": st.column_config.NumberColumn("P1", format="%d", width="small"),
        "P2": st.column_config.NumberColumn("P2", format="%d", width="small"),
        "P3": st.column_config.NumberColumn("P3", format="%d", width="small"),
        "P4": st.column_config.NumberColumn("P4", format="%d", width="small"),
        "P5": st.column_config.NumberColumn("P5", format="%d", width="small"),
    }

    if 'Ticker' in filtered_df.columns:
        holdings_cols.insert(1, 'Ticker')
        col_config["Ticker"] = st.column_config.TextColumn("Ticker", width="small")
    if 'Marango_Holding' in filtered_df.columns:
        holdings_cols.insert(2, 'Marango_Holding')
    if 'Live_Price' in filtered_df.columns and filtered_df['Live_Price'].notna().any():
        holdings_cols.insert(2, 'Live_Price')
        holdings_cols.insert(3, 'Daily_Change')
        col_config["Live_Price"] = st.column_config.NumberColumn("Price ($)", format="%.2f", width="small")
        col_config["Daily_Change"] = st.column_config.NumberColumn("Day %", format="%+.2f%%", width="small")
    if '5D_Trend' in filtered_df.columns:
        idx = 4 if 'Live_Price' in filtered_df.columns else 2
        holdings_cols.insert(idx, '5D_Trend')
        col_config["5D_Trend"] = st.column_config.LineChartColumn(
            "5D Trend",
            width="small",
            y_min=None,
            y_max=None
        )

    holdings_cols = [c for c in holdings_cols if c in filtered_df.columns]

    # Timestamp and status
    update_time = datetime.now().strftime('%H:%M:%S')
    if live_prices:
        st.caption(f"Live prices: {len(live_prices)}/{len(df)} tickers | Showing {len(filtered_df)}/{len(df)} | Refresh: {update_time}")
    else:
        st.caption(f"Showing {len(filtered_df)}/{len(df)} holdings")

    st.dataframe(
        filtered_df[holdings_cols].sort_values('Quality_Score', ascending=False),
        column_config=col_config,
        width='stretch',
        hide_index=True,
        height=500
    )

    # Color-coded top movers section
    if live_prices and 'Daily_Change' in df.columns:
        st.divider()
        st.markdown("<h3>TODAY'S MOVERS</h3>", unsafe_allow_html=True)

        movers_df = df[df['Daily_Change'].notna() & (df['Daily_Change'] != 0)].copy()
        if not movers_df.empty and 'Company' in movers_df.columns:
            col_top, col_bottom = st.columns(2)
            with col_top:
                st.markdown("**TOP GAINERS**")
                top5 = movers_df.nlargest(5, 'Daily_Change')
                for _, row in top5.iterrows():
                    ticker = safe_str(row.get('Ticker', ''))
                    company = safe_str(row.get('Company', ''))[:20]
                    chg = row['Daily_Change']
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:0.3rem 0;'
                        f'border-bottom:1px solid rgba(15,23,42,0.05);font-size:0.85rem;">'
                        f'<span style="color:#1e293b;font-family:JetBrains Mono;">{ticker}</span>'
                        f'<span style="color:#059669;font-weight:600;">+{chg:.2f}%</span></div>',
                        unsafe_allow_html=True
                    )
            with col_bottom:
                st.markdown("**TOP LOSERS**")
                bottom5 = movers_df.nsmallest(5, 'Daily_Change')
                for _, row in bottom5.iterrows():
                    ticker = safe_str(row.get('Ticker', ''))
                    company = safe_str(row.get('Company', ''))[:20]
                    chg = row['Daily_Change']
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:0.3rem 0;'
                        f'border-bottom:1px solid rgba(15,23,42,0.05);font-size:0.85rem;">'
                        f'<span style="color:#1e293b;font-family:JetBrains Mono;">{ticker}</span>'
                        f'<span style="color:#dc2626;font-weight:600;">{chg:.2f}%</span></div>',
                        unsafe_allow_html=True
                    )

def display_ai_tab():
    """AI Analysis - Claude Powered + Portfolio Summary"""
    st.markdown("<h2>AI ANALYSIS — POWERED BY CLAUDE</h2>", unsafe_allow_html=True)

    # Always show portfolio summary first
    df = load_bloque1()
    regime = load_regime()

    if not df.empty:
        st.markdown("<h3>PORTFOLIO SNAPSHOT</h3>", unsafe_allow_html=True)

        # Signal distribution
        if 'SIGNAL' in df.columns:
            signal_counts = df['SIGNAL'].value_counts()
            col_pie, col_summary = st.columns([1, 2])

            with col_pie:
                fig = px.pie(
                    values=signal_counts.values,
                    names=signal_counts.index,
                    title="SIGNAL DISTRIBUTION",
                    color_discrete_sequence=['#059669', '#0891b2', '#ea580c', '#dc2626', '#64748b']
                )
                fig.update_layout(
                    template='plotly_white', height=350,
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='JetBrains Mono', color='#1e293b')
                )
                st.plotly_chart(fig, width='stretch')

            with col_summary:
                st.markdown("**REGIME STATUS**")
                st.markdown(f"Combined Score: **{regime['combined']:.0f}** — {regime['status']}")
                st.markdown(f"Technical: {regime['technical']:.0f} | Sentiment: {regime['sentiment']:.0f} | Liquidity: {regime['liquidity']:.0f}")
                st.markdown("")
                st.markdown("**TOP QUALITY HOLDINGS**")
                top5 = df.nlargest(5, 'Quality_Score')
                for _, row in top5.iterrows():
                    ticker = safe_str(row.get('Ticker', ''))
                    company = safe_str(row.get('Company', ''), 'N/A')
                    score = row.get('Quality_Score', 0)
                    signal = safe_str(row.get('SIGNAL', ''))
                    st.markdown(f"**{ticker}** {company[:25]} — Score: {score:.0f} — {signal}")

                st.markdown("")
                st.markdown("**WEAKEST HOLDINGS**")
                bottom3 = df.nsmallest(3, 'Quality_Score')
                for _, row in bottom3.iterrows():
                    ticker = safe_str(row.get('Ticker', ''))
                    company = safe_str(row.get('Company', ''), 'N/A')
                    score = row.get('Quality_Score', 0)
                    signal = safe_str(row.get('SIGNAL', ''))
                    st.markdown(f"**{ticker}** {company[:25]} — Score: {score:.0f} — {signal}")

        # Sector breakdown
        if 'GICS Sector' in df.columns:
            st.divider()
            st.markdown("<h3>SECTOR ALLOCATION</h3>", unsafe_allow_html=True)
            sector_counts = df['GICS Sector'].value_counts()
            fig_sector = px.bar(
                x=sector_counts.values, y=sector_counts.index,
                orientation='h', title="Holdings by Sector",
                color=sector_counts.values,
                color_continuous_scale=['#0891b2', '#ea580c']
            )
            fig_sector.update_layout(
                template='plotly_white', height=350,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='JetBrains Mono', color='#1e293b'),
                showlegend=False, xaxis_title="Count", yaxis_title="",
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_sector, width='stretch')

    st.divider()

    # Claude AI section
    st.markdown("<h3>CLAUDE AI ANALYSIS</h3>", unsafe_allow_html=True)

    # Check API availability
    api_key = None
    if ANTHROPIC_AVAILABLE:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
        except Exception:
            pass
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")

    if not ANTHROPIC_AVAILABLE:
        st.info("Para activar el analisis AI, instala el SDK: `pip install anthropic`")
    elif not api_key:
        st.info("Para activar el analisis AI con Claude, configura ANTHROPIC_API_KEY en Streamlit Secrets (Settings > Secrets)")
    else:
        # Load cache
        ai_cache = load_ai_cache()
        cache_date = ai_cache.get("date", "Never")

        st.caption(f"Last analysis: {cache_date}")

        # Get portfolio tickers from Bloque 1
        df = load_bloque1()
        tickers = []
        if not df.empty and 'Ticker' in df.columns:
            tickers = df[df['Ticker'].notna()]['Ticker'].unique().tolist()

        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            run_analysis = st.button("RUN AI ANALYSIS", type="primary")
        with col_btn2:
            if tickers:
                st.caption(f"{len(tickers)} tickers in portfolio")

        if run_analysis and tickers:
            ai_cache = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "results": {}}
            progress = st.progress(0, text="Analyzing portfolio...")

            for i, ticker in enumerate(tickers[:30]):
                progress.progress((i + 1) / min(len(tickers), 30),
                                  text=f"Analyzing {ticker}... ({i+1}/{min(len(tickers), 30)})")

                b1_score = None
                signal = None
                ticker_row = df[df['Ticker'] == ticker]
                if not ticker_row.empty:
                    b1_score = ticker_row['Quality_Score'].values[0] if 'Quality_Score' in ticker_row.columns else None
                    signal = ticker_row['SIGNAL'].values[0] if 'SIGNAL' in ticker_row.columns else None

                stock_data = get_stock_summary(ticker)
                result = analyze_with_claude(ticker, stock_data, b1_score, signal)
                ai_cache["results"][ticker] = result

            progress.empty()
            save_ai_cache(ai_cache)
            st.success(f"Analysis complete! {len(ai_cache['results'])} tickers analyzed")

        # Display cached results
        results = ai_cache.get("results", {}) if isinstance(ai_cache, dict) else {}

        if results:
            # Summary table
            summary_data = []
            for ticker, res in results.items():
                if "error" not in res:
                    signal_emoji = {
                        "STRONG BUY": "+", "BUY": "+",
                        "HOLD": "=", "UNDERWEIGHT": "-", "SELL": "-"
                    }
                    sig = res.get("signal", "N/A")
                    emoji = signal_emoji.get(sig, "")
                    summary_data.append({
                        "Ticker": ticker,
                        "AI Signal": f"{emoji} {sig}",
                        "Confidence": res.get("confidence", "N/A"),
                        "Target": res.get("target", "N/A"),
                        "Summary": res.get("summary", "N/A")[:100] + "...",
                    })

            if summary_data:
                st.markdown("<h3>PORTFOLIO AI SIGNALS</h3>", unsafe_allow_html=True)
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, width='stretch', hide_index=True)

                col_chart1, col_chart2 = st.columns(2)

                with col_chart1:
                    signal_counts = summary_df['AI Signal'].value_counts()
                    fig = px.pie(
                        values=signal_counts.values,
                        names=signal_counts.index,
                        title="SIGNAL DISTRIBUTION",
                        color_discrete_sequence=['#059669', '#0891b2', '#ea580c', '#dc2626', '#64748b']
                    )
                    fig.update_layout(
                        template='plotly_white',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='JetBrains Mono', color='#1e293b')
                    )
                    st.plotly_chart(fig, width='stretch')

                with col_chart2:
                    conf_counts = summary_df['Confidence'].value_counts()
                    fig2 = px.bar(
                        x=conf_counts.index,
                        y=conf_counts.values,
                        title="CONFIDENCE DISTRIBUTION",
                        color=conf_counts.values,
                        color_continuous_scale='Oranges'
                    )
                    fig2.update_layout(
                        template='plotly_white',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='JetBrains Mono', color='#1e293b'),
                        showlegend=False,
                        xaxis_title="",
                        yaxis_title="Count"
                    )
                    st.plotly_chart(fig2, width='stretch')

                # Detailed analysis per ticker
                st.divider()
                st.markdown("<h3>DETAILED ANALYSIS</h3>", unsafe_allow_html=True)

                for ticker, res in results.items():
                    if "error" not in res:
                        with st.expander(f"{ticker} — {res.get('signal', 'N/A')}"):
                            col_d1, col_d2, col_d3 = st.columns(3)
                            col_d1.metric("AI SIGNAL", res.get("signal", "N/A"))
                            col_d2.metric("CONFIDENCE", res.get("confidence", "N/A"))
                            col_d3.metric("TARGET", res.get("target", "N/A"))
                            st.write(f"**Summary:** {res.get('summary', 'N/A')}")
                            st.write(f"**Risks:** {res.get('risks', 'N/A')}")
                            st.write(f"**Catalysts:** {res.get('catalysts', 'N/A')}")
                            st.caption(f"Analyzed: {res.get('timestamp', 'N/A')}")
        else:
            st.info("No results. Click 'RUN AI ANALYSIS' to analyze portfolio with Claude AI")

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0; text-align: center;
                border-bottom: 1px solid rgba(15,23,42,0.07);">
        <div style="font-family: 'JetBrains Mono'; font-size: 1.2rem;
                    font-weight: 700; color: #ea580c;">
            MARANGO
        </div>
        <div style="font-size: 0.75rem; color: #64748b;
                    text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.5rem;">
            Terminal v5.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("REFRESH", width='stretch'):
            st.cache_data.clear()
            st.success("Cache cleared")
            st.rerun()

    with col2:
        st.caption(f"Loaded: {datetime.now().strftime('%H:%M')}")

    st.divider()

    st.markdown(f"""
    <div style="font-size: 0.8rem; color: #64748b; line-height: 1.6;">
        <strong>Quality x Regime</strong><br>
        Investment System v5.0<br><br>
        <strong style="color:#ea580c;">Data Sources:</strong><br>
        Yahoo Finance (live)<br>
        Excel (scoring)<br>
        Claude AI (analysis)<br><br>
        <strong style="color:#ea580c;">Last Refresh:</strong><br>
        {datetime.now().strftime('%H:%M:%S %Z')}
    </div>
    """, unsafe_allow_html=True)

# ============================================
# MAIN APP
# ============================================

# Load data
df = load_bloque1()
# Use live regime (Yahoo Finance) with Excel fallback — load_regime() tries live first internally
regime = load_regime()

if df.empty:
    st.error("Could not load portfolio data. Check Excel files.")
    st.stop()

# Terminal Header — Bloomberg Pro Style
regime_score = regime.get('combined', 0)
regime_status_text = regime.get('status', 'Unknown')
if regime_score >= 70:
    regime_dot = '#059669'
    regime_label = 'RISK-ON'
elif regime_score >= 55:
    regime_dot = '#0891b2'
    regime_label = 'MODERATE'
elif regime_score >= 45:
    regime_dot = '#d97706'
    regime_label = 'CAUTION'
else:
    regime_dot = '#dc2626'
    regime_label = 'RISK-OFF'

header_time = datetime.now().strftime('%H:%M')
header_date = datetime.now().strftime('%d %b %Y').upper()

st.markdown(f"""
<div style="background:linear-gradient(180deg, #ffffff 0%, #f7f8fa 100%);
            border-top:3px solid #ea580c; border-bottom:1px solid rgba(249,115,22,0.2);
            padding:0.6rem 1.5rem; font-family:'JetBrains Mono',monospace;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.3rem;">
        <div style="display:flex; align-items:center; gap:1rem;">
            <span style="font-size:1.1rem; font-weight:700; color:#ea580c; letter-spacing:0.12em;">MARANGO</span>
            <span style="color:#94a3b8; font-size:0.7rem; border-left:1px solid #e2e8f0; padding-left:0.8rem;">TERMINAL v5.0</span>
            <span style="color:#94a3b8; font-size:0.7rem; border-left:1px solid #e2e8f0; padding-left:0.8rem;">Quality × Regime × Momentum</span>
        </div>
        <div style="display:flex; align-items:center; gap:1.2rem; font-size:0.75rem;">
            <span style="color:#64748b;">{header_date}</span>
            <span style="color:#ea580c; font-weight:600;">{header_time}</span>
            <span style="display:inline-flex; align-items:center; gap:0.3rem;
                         background:rgba({','.join([str(int(regime_dot[i:i+2],16)) for i in (1,3,5)])},0.1);
                         border:1px solid {regime_dot}40; border-radius:4px; padding:0.15rem 0.5rem;">
                <span style="width:6px; height:6px; border-radius:50%; background:{regime_dot}; display:inline-block;"></span>
                <span style="color:{regime_dot}; font-weight:600;">{regime_label} {regime_score:.0f}</span>
            </span>
            <span style="display:inline-flex; align-items:center; gap:0.3rem;">
                <span style="width:6px; height:6px; border-radius:50%; background:#059669; display:inline-block; animation:pulse 2s infinite;"></span>
                <span style="color:#059669; font-weight:600;">LIVE</span>
            </span>
        </div>
    </div>
</div>
<style>
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.3; }}
    }}
</style>
""", unsafe_allow_html=True)

# Ticker Marquee — Bloomberg TV Style
def render_ticker_marquee():
    """Render scrolling ticker tape like Bloomberg TV"""
    try:
        indices = get_market_indices()
        ticker_items = []
        for name, data in indices.items():
            if data.get('value', 0) == 0:
                continue
            chg = data.get('change_pct', 0)
            net = data.get('change', 0)
            color = '#059669' if chg >= 0 else '#dc2626'
            arrow = '&#9650;' if chg >= 0 else '&#9660;'
            ticker_items.append(
                f'<span style="display:inline-flex; align-items:center; margin-right:1.8rem; gap:0.4rem;">'
                f'<span style="color:#ea580c; font-weight:600; font-size:0.72rem;">{name}</span>'
                f'<span style="color:#1e293b; font-weight:700; font-size:0.78rem;">{data["value"]:,.2f}</span>'
                f'<span style="color:{color}; font-size:0.72rem;">{arrow}{net:+.2f}</span>'
                f'<span style="color:{color}; font-weight:600; font-size:0.72rem;">({chg:+.2f}%)</span>'
                f'<span style="color:rgba(15,23,42,0.10); margin:0 0.2rem;">|</span>'
                f'</span>'
            )
        marquee_content = ''.join(ticker_items)
        st.markdown(f"""
        <div style="overflow:hidden; background:linear-gradient(90deg, #f7f8fa, #f7f8fa, #f7f8fa);
                    border-bottom:1px solid rgba(249,115,22,0.15);
                    padding:0.45rem 0; font-family:'JetBrains Mono',monospace;
                    white-space:nowrap;">
            <div style="display:inline-block; animation:marquee 55s linear infinite;">
                {marquee_content}{marquee_content}
            </div>
        </div>
        <style>
            @keyframes marquee {{
                0% {{ transform: translateX(0); }}
                100% {{ transform: translateX(-50%); }}
            }}
        </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"Market data loading... ({type(e).__name__})")

render_ticker_marquee()

# KPI Strip — collapsible to save vertical space
with st.expander("KPI DASHBOARD", expanded=True):
    render_kpi_strip()

st.divider()

# ============================================
# TABS
# ============================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "MARKETS",
    "SCORES",
    "REGIME",
    "MOMENTUM",
    "BRIDGE",
    "HOLDINGS",
    "RESEARCH",
    "SIGNALS"
])

with tab1:
    try:
        display_markets_tab()
    except Exception as e:
        st.error(f"Markets tab error: {str(e)}")
        st.code(traceback.format_exc())

with tab2:
    try:
        display_scores_tab()
    except Exception as e:
        st.error(f"Scores tab error: {str(e)}")
        st.code(traceback.format_exc())

with tab3:
    try:
        display_regime_tab()
    except Exception as e:
        st.error(f"Regime tab error: {str(e)}")
        st.code(traceback.format_exc())

with tab4:
    try:
        display_momentum_tab()
    except Exception as e:
        st.error(f"Momentum tab error: {str(e)}")
        st.code(traceback.format_exc())

with tab5:
    try:
        display_bridge_tab()
    except Exception as e:
        st.error(f"Bridge tab error: {str(e)}")
        st.code(traceback.format_exc())

with tab6:
    try:
        display_holdings_tab()
    except Exception as e:
        st.error(f"Holdings tab error: {str(e)}")
        st.code(traceback.format_exc())

with tab7:
    # RESEARCH — single-stock deep dive (sub-tabs)
    sub1, sub2, sub3, sub4, sub5 = st.tabs([
        "Valuation (Reverse DCF)",
        "Return Attribution",
        "Historical Multiples",
        "Quality Scores",
        "Peer Comparison",
    ])
    with sub1:
        try:
            display_valuation_tab()
        except Exception as e:
            st.error(f"Valuation error: {str(e)}")
            st.code(traceback.format_exc())
    with sub2:
        try:
            display_attribution_tab()
        except Exception as e:
            st.error(f"Attribution error: {str(e)}")
            st.code(traceback.format_exc())
    with sub3:
        try:
            display_multiples_tab()
        except Exception as e:
            st.error(f"Multiples error: {str(e)}")
            st.code(traceback.format_exc())
    with sub4:
        try:
            display_quality_tab()
        except Exception as e:
            st.error(f"Quality error: {str(e)}")
            st.code(traceback.format_exc())
    with sub5:
        try:
            display_peers_tab()
        except Exception as e:
            st.error(f"Peers error: {str(e)}")
            st.code(traceback.format_exc())

with tab8:
    try:
        display_signals_tab()
    except Exception as e:
        st.error(f"Signals tab error: {str(e)}")
        st.code(traceback.format_exc())

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.75rem;
            text-transform: uppercase; letter-spacing: 0.05em; padding: 1rem 0;">
    Marango Terminal v5.0 | Quality × Regime × Momentum | Marango Fund
</div>
""", unsafe_allow_html=True)
 