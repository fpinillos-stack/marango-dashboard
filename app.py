import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import ta
from datetime import datetime, timedelta
import json

st.set_page_config(
    page_title="Marango Equity Fund - Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
.main{background-color:#030712}
.block-container{padding:1rem 2rem}
.stMetric label{color:#6b7280;font-size:10px;text-transform:uppercase;letter-spacing:1px}
.stMetric [data-testid="stMetricValue"]{font-family:monospace;font-weight:bold}
div[data-testid="stHorizontalBlock"]{gap:8px}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# PORTFOLIO DATA
# ═══════════════════════════════════════════════════════
PORTFOLIO = {
    "GOOGL":  {"n":"Alphabet Inc","s":"Technology","w":6.7,"P1":95.8,"P2":90.3,"P3":100,"P4":82,"P5":65,"P6":44.9,"fs":92,"fv":340,"b1":"BUY"},
    "MSFT":   {"n":"Microsoft Corp","s":"Technology","w":6.6,"P1":95.8,"P2":75.3,"P3":81.4,"P4":83.8,"P5":41.7,"P6":53.7,"fs":82,"fv":600,"b1":"BUY"},
    "BN":     {"n":"Brookfield Corp","s":"Financials","w":5.8,"P1":29.1,"P2":96.3,"P3":37.3,"P4":51.2,"P5":37.4,"P6":24.7,"fs":51,"fv":54,"b1":"UNDERWEIGHT"},
    "V":      {"n":"Visa Inc","s":"Financials","w":5.7,"P1":100,"P2":90.3,"P3":85.8,"P4":85.8,"P5":23.4,"P6":43.3,"fs":84,"fv":323,"b1":"HOLD"},
    "SPGI":   {"n":"S&P Global","s":"Financials","w":5.3,"P1":80.4,"P2":85,"P3":80.4,"P4":91,"P5":37.4,"P6":38,"fs":80,"fv":570,"b1":"HOLD"},
    "AMZN":   {"n":"Amazon.com","s":"Technology","w":4.9,"P1":91.3,"P2":94,"P3":80.4,"P4":51.4,"P5":35.7,"P6":19.8,"fs":77,"fv":260,"b1":"BUY"},
    "TSM":    {"n":"Taiwan Semi","s":"Technology","w":4.3,"P1":95.8,"P2":100,"P3":100,"P4":52.3,"P5":59.9,"P6":48.4,"fs":91,"fv":428,"b1":"STRONG BUY"},
    "GE":     {"n":"GE Aerospace","s":"Industrials","w":4.1,"P1":100,"P2":100,"P3":79.8,"P4":89.2,"P5":15.4,"P6":46.3,"fs":85,"fv":293,"b1":"BUY"},
    "SAF.PA": {"n":"Safran SA","s":"Industrials","w":4.1,"P1":85,"P2":95.5,"P3":85,"P4":89.2,"P5":34,"P6":69,"fs":87,"fv":367,"b1":"BUY"},
    "META":   {"n":"Meta Platforms","s":"Technology","w":4.0,"P1":95.8,"P2":100,"P3":100,"P4":82.8,"P5":53.1,"P6":44.9,"fs":91,"fv":850,"b1":"STRONG BUY"},
    "NVDA":   {"n":"NVIDIA Corp","s":"Technology","w":3.9,"P1":100,"P2":100,"P3":100,"P4":92.1,"P5":48,"P6":19.8,"fs":93,"fv":240,"b1":"STRONG BUY"},
    "OR.PA":  {"n":"L'Oreal SA","s":"Consumer","w":3.8,"P1":94.8,"P2":92,"P3":85.2,"P4":84.3,"P5":34,"P6":71.2,"fs":87,"fv":419,"b1":"HOLD"},
    "MCO":    {"n":"Moody's Corp","s":"Financials","w":3.7,"P1":100,"P2":85,"P3":94.8,"P4":85.8,"P5":17.4,"P6":42.7,"fs":87,"fv":550,"b1":"HOLD"},
    "MA":     {"n":"Mastercard","s":"Financials","w":3.6,"P1":100,"P2":96.3,"P3":85.8,"P4":94.8,"P5":23.4,"P6":43.3,"fs":88,"fv":550,"b1":"HOLD"},
    "SU.PA":  {"n":"Schneider Elec","s":"Industrials","w":3.5,"P1":75.2,"P2":86,"P3":73.8,"P4":77.1,"P5":48,"P6":66.1,"fs":81,"fv":250,"b1":"BUY"},
    "ASML":   {"n":"ASML Holding","s":"Technology","w":3.0,"P1":100,"P2":87.3,"P3":91,"P4":58.6,"P5":42,"P6":59.7,"fs":87,"fv":1000,"b1":"HOLD"},
    "RMS.PA": {"n":"Hermes Intl","s":"Consumer","w":3.0,"P1":100,"P2":87.3,"P3":100,"P4":82,"P5":10.7,"P6":42.4,"fs":86,"fv":1580,"b1":"HOLD"},
    "FER":    {"n":"Ferrovial","s":"Industrials","w":3.0,"P1":56,"P2":63.5,"P3":53.7,"P4":59.8,"P5":21.7,"P6":66.1,"fs":59,"fv":60,"b1":"UNDERWEIGHT"},
    "LLY":    {"n":"Eli Lilly","s":"Healthcare","w":2.8,"P1":100,"P2":100,"P3":64.8,"P4":82,"P5":16.8,"P6":65.7,"fs":86,"fv":870,"b1":"BUY"},
    "DG.PA":  {"n":"Vinci SA","s":"Industrials","w":2.5,"P1":74.5,"P2":76.3,"P3":55.2,"P4":70.3,"P5":88.3,"P6":81.8,"fs":81,"fv":133,"b1":"HOLD"},
    "SYK":    {"n":"Stryker Corp","s":"Healthcare","w":2.3,"P1":70.9,"P2":71.5,"P3":69,"P4":85,"P5":48,"P6":47.4,"fs":77,"fv":316,"b1":"BUY"},
    "ISRG":   {"n":"Intuitive Surg","s":"Healthcare","w":2.1,"P1":80.4,"P2":91.5,"P3":100,"P4":85.8,"P5":11.4,"P6":5.8,"fs":82,"fv":378,"b1":"HOLD"},
    "IDXX":   {"n":"IDEXX Labs","s":"Healthcare","w":2.0,"P1":100,"P2":71.5,"P3":75.1,"P4":85.8,"P5":16.8,"P6":26.1,"fs":80,"fv":470,"b1":"HOLD"},
    "TSLA":   {"n":"Tesla Inc","s":"Technology","w":1.4,"P1":39.5,"P2":65,"P3":100,"P4":79.7,"P5":0,"P6":5.8,"fs":54,"fv":400,"b1":"UNDERWEIGHT"},
    "ASTS":   {"n":"AST SpaceMobile","s":"Technology","w":1.3,"P1":0,"P2":75.5,"P3":30,"P4":11.2,"P5":100,"P6":5.8,"fs":27,"fv":80,"b1":"HOLD"},
    "MRVL":   {"n":"Marvell Tech","s":"Technology","w":1.1,"P1":67.5,"P2":82,"P3":75.2,"P4":68.7,"P5":41.7,"P6":27.4,"fs":67,"fv":130,"b1":"BUY (Value)"},
    "BE":     {"n":"Bloom Energy","s":"Industrials","w":0.9,"P1":11.2,"P2":100,"P3":46.8,"P4":36.2,"P5":0,"P6":5.1,"fs":33,"fv":60,"b1":"SELL"},
}

REGIME = {"ov":58,"lbl":"RISK-OFF (Override Activo)","ovrOn":True,"ovrR":"Breadth Collapse","se":67,"te":41,"li":67,"vix":23.51,"spx":6716.09,"br":48}

MARKET_SYMS = {
    "Indices": {"^GSPC":"S&P 500","^IXIC":"NASDAQ","^DJI":"Dow Jones","^RUT":"Russell 2000","^STOXX50E":"Euro Stoxx 50","^FTSE":"FTSE 100","^GDAXI":"DAX","^N225":"Nikkei 225","^VIX":"VIX"},
    "Divisas": {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","DX-Y.NYB":"DXY"},
    "Materias Primas": {"CL=F":"WTI Oil","BZ=F":"Brent","GC=F":"Gold","SI=F":"Silver","HG=F":"Copper"},
    "Treasuries": {"^TNX":"US 10Y","^TYX":"US 30Y","^FVX":"US 5Y","TLT":"20Y ETF"},
    "Crypto": {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum"},
}

SECTOR_COLORS = {"Technology":"#3b82f6","Financials":"#f59e0b","Industrials":"#10b981","Healthcare":"#06b6d4","Consumer":"#ec4899"}

# ═══════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════
@st.cache_data(ttl=120)
def fetch_holdings_prices():
    tickers = list(PORTFOLIO.keys())
    try:
        data = yf.download(tickers, period="1d", group_by="ticker", progress=False)
        prices = {}
        for t in tickers:
            try:
                if len(tickers) > 1 and t in data.columns.get_level_values(0):
                    close = data[t]["Close"].iloc[-1]
                    prices[t] = float(close) if pd.notna(close) else 0
                elif len(tickers) == 1:
                    close = data["Close"].iloc[-1]
                    prices[t] = float(close) if pd.notna(close) else 0
            except Exception:
                prices[t] = 0
        return prices
    except Exception:
        return {t: 0 for t in tickers}

@st.cache_data(ttl=120)
def fetch_market_data():
    all_syms = []
    for cat_syms in MARKET_SYMS.values():
        all_syms.extend(cat_syms.keys())
    try:
        data = yf.download(all_syms, period="5d", group_by="ticker", progress=False)
        result = {}
        for sym in all_syms:
            try:
                if sym in data.columns.get_level_values(0):
                    closes = data[sym]["Close"].dropna()
                    if len(closes) >= 2:
                        price = float(closes.iloc[-1])
                        prev = float(closes.iloc[-2])
                        chg = ((price / prev) - 1) * 100 if prev > 0 else 0
                        result[sym] = {"price": price, "chg": chg}
            except Exception:
                pass
        return result
    except Exception:
        return {}

@st.cache_data(ttl=300)
def fetch_chart_data(ticker, period="3mo"):
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            return None
        # Flatten multi-level columns if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Add technical indicators
        if len(df) > 14:
            df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
            df["SMA20"] = ta.trend.SMAIndicator(df["Close"], window=20).sma_indicator()
            df["SMA50"] = ta.trend.SMAIndicator(df["Close"], window=50).sma_indicator()
            bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
            df["BB_upper"] = bb.bollinger_hband()
            df["BB_lower"] = bb.bollinger_lband()
            macd_ind = ta.trend.MACD(df["Close"])
            df["MACD"] = macd_ind.macd()
            df["MACD_signal"] = macd_ind.macd_signal()
            df["MACD_hist"] = macd_ind.macd_diff()
        return df
    except Exception:
        return None

@st.cache_data(ttl=600)
def fetch_news(ticker):
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if news:
            return news[:8]
    except Exception:
        pass
    return []

# ═══════════════════════════════════════════════════════
# SIGNAL COMPUTATION
# ═══════════════════════════════════════════════════════
def compute_signals(prices):
    eff = 35 if REGIME["ovrOn"] else REGIME["ov"]
    is_bear = eff < 40
    results = []
    for ticker, info in PORTFOLIO.items():
        q = info["fs"]
        price = prices.get(ticker, 0)
        fv = info["fv"]
        up = ((fv / price) - 1) * 100 if price > 0 else info.get("up", 0)
        b1 = info["b1"]
        is_bad = "UNDER" in b1 or "SELL" in b1
        is_b1_buy = "BUY" in b1

        if is_bad:
            sig = "SELL" if "SELL" in b1 else "REDUCE"
        elif q >= 75 and up > 10 and is_b1_buy and is_bear:
            sig = "STRONG BUY"
        elif q >= 75 and up > 0 and is_b1_buy:
            sig = "BUY"
        elif q >= 65 and up > 15 and is_bear:
            sig = "BUY"
        elif q >= 75 and up <= 0:
            sig = "HOLD +"
        elif q >= 75:
            sig = "HOLD +"
        elif q >= 55 and up >= 0:
            sig = "HOLD"
        elif q >= 55 and up < 0:
            sig = "HOLD -"
        elif q < 55 and up < -20:
            sig = "REDUCE"
        else:
            sig = "HOLD"

        results.append({
            "Ticker": ticker, "Nombre": info["n"], "Sector": info["s"],
            "Peso": info["w"], "Precio": price, "Fair Value": fv,
            "Upside": round(up, 1), "Quality": q,
            "P1": info["P1"], "P2": info["P2"], "P3": info["P3"],
            "P4": info["P4"], "P5": info["P5"], "P6": info["P6"],
            "B1": b1, "Signal": sig
        })
    return pd.DataFrame(results)

# ═══════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════

# Header
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("### 🟠 MARANGO EQUITY FUND")
    st.caption("ES0166932006 | Renta 4 SGIIC | Quality x Regime Dashboard")
with col_h2:
    st.metric("Portfolio Quality", f"{82}/100")
    st.metric("Regimen", f"{REGIME['ov']}/100", delta=REGIME['lbl'])

# Fetch data
prices = fetch_holdings_prices()
df = compute_signals(prices)

# Metrics row
c1, c2, c3, c4, c5, c6 = st.columns(6)
buy_count = len(df[df["Signal"].str.contains("BUY")])
c1.metric("NAV", "€17.87M")
c2.metric("Quality", str(82))
c3.metric("Regimen", str(REGIME["ov"]))
c4.metric("VIX", str(REGIME["vix"]))
c5.metric("Posiciones", str(len(df)))
c6.metric("BUY Signals", str(buy_count))

# Tabs
tab_markets, tab_matrix, tab_quality, tab_regime, tab_technical, tab_news = st.tabs(
    ["📈 Markets", "🎯 Decision Matrix", "💎 Quality Analysis", "🌐 Market Regime", "📊 Technical Analysis", "📰 News"]
)

# ══ MARKETS TAB ══
with tab_markets:
    mkt_data = fetch_market_data()
    for cat, syms in MARKET_SYMS.items():
        st.markdown(f"**{cat}**")
        cols = st.columns(len(syms))
        for i, (sym, name) in enumerate(syms.items()):
            with cols[i]:
                md = mkt_data.get(sym, {"price": 0, "chg": 0})
                price_str = f"{md['price']:,.2f}" if md["price"] > 0 else "---"
                delta_str = f"{md['chg']:+.2f}%"
                st.metric(name, price_str, delta=delta_str)

    # Mini charts for key indices
    st.markdown("---")
    st.markdown("**Graficos Intraday (3 meses)**")
    chart_cols = st.columns(3)
    key_charts = ["^GSPC", "^VIX", "GC=F"]
    key_names = ["S&P 500", "VIX", "Gold"]
    for i, (sym, name) in enumerate(zip(key_charts, key_names)):
        with chart_cols[i]:
            cdata = fetch_chart_data(sym, "3mo")
            if cdata is not None and not cdata.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=cdata.index, y=cdata["Close"], mode="lines", name=name, line=dict(color="#f97316", width=2)))
                if "SMA20" in cdata.columns:
                    fig.add_trace(go.Scatter(x=cdata.index, y=cdata["SMA20"], mode="lines", name="SMA20", line=dict(color="#3b82f6", width=1, dash="dash")))
                fig.update_layout(title=name, template="plotly_dark", height=250, margin=dict(l=0,r=0,t=30,b=0), showlegend=False, paper_bgcolor="#030712", plot_bgcolor="#111827")
                st.plotly_chart(fig, use_container_width=True)

# ══ DECISION MATRIX TAB ══
with tab_matrix:
    # Signal distribution
    sig_counts = df["Signal"].value_counts()
    sig_cols = st.columns(7)
    sig_order = ["STRONG BUY", "BUY", "HOLD +", "HOLD", "HOLD -", "REDUCE", "SELL"]
    sig_colors_map = {"STRONG BUY":"🟢","BUY":"🟢","HOLD +":"🟡","HOLD":"🟡","HOLD -":"🟠","REDUCE":"🔴","SELL":"🔴"}
    for i, sig in enumerate(sig_order):
        with sig_cols[i]:
            count = int(sig_counts.get(sig, 0))
            st.metric(sig, count)

    # Sector filter
    sector_filter = st.selectbox("Filtrar por sector", ["All"] + list(df["Sector"].unique()))
    filtered = df if sector_filter == "All" else df[df["Sector"] == sector_filter]

    # Format and display
    display_df = filtered[["Ticker","Nombre","Sector","Peso","Precio","Upside","Quality","P1","P2","P3","P4","P5","P6","B1","Signal"]].copy()
    display_df = display_df.sort_values("Quality", ascending=False)
    st.dataframe(
        display_df.style.background_gradient(subset=["Quality"], cmap="RdYlGn", vmin=20, vmax=100)
            .background_gradient(subset=["Upside"], cmap="RdYlGn", vmin=-50, vmax=50)
            .format({"Peso":"{:.1f}%","Precio":"${:.2f}","Upside":"{:+.1f}%"}),
        use_container_width=True, height=600
    )

# ══ QUALITY ANALYSIS TAB ══
with tab_quality:
    col_list, col_detail = st.columns([1, 2])
    with col_list:
        selected = st.selectbox("Selecciona valor", df.sort_values("Quality", ascending=False)["Ticker"].tolist())

    with col_detail:
        if selected:
            row = df[df["Ticker"] == selected].iloc[0]
            st.markdown(f"### {row['Ticker']} — {row['Nombre']}")
            st.caption(f"{row['Sector']} | Peso: {row['Peso']}% | {row['Signal']} | FV: ${row['Fair Value']} | Upside: {row['Upside']:+.1f}%")

            # Radar chart
            pillars = ["P1","P2","P3","P4","P5","P6"]
            pillar_names = ["Rentabilidad","Crecimiento","Salud Fin.","Valoracion","Accionista","Momentum"]
            values = [row[p] for p in pillars]
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=values + [values[0]], theta=pillar_names + [pillar_names[0]], fill="toself", fillcolor="rgba(249,115,22,0.2)", line=dict(color="#f97316", width=2)))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100], gridcolor="#374151"), angularaxis=dict(gridcolor="#374151"), bgcolor="#111827"), template="plotly_dark", height=350, margin=dict(l=40,r=40,t=20,b=20), paper_bgcolor="#030712", showlegend=False)
            st.plotly_chart(fig_radar, use_container_width=True)

            # Pillar bars
            for p, pn in zip(pillars, pillar_names):
                val = row[p]
                color = "#22c55e" if val >= 75 else "#facc15" if val >= 55 else "#ef4444"
                st.progress(int(val), text=f"{pn}: {val:.0f}")

    # Scatter plot
    st.markdown("---")
    st.markdown("**Quality vs Valoracion (P4)**")
    fig_scatter = px.scatter(df, x="P4", y="Quality", size="Peso", color="Sector",
        color_discrete_map=SECTOR_COLORS, hover_data=["Ticker","Signal","Upside"],
        labels={"P4":"Valoracion (P4) →","Quality":"← Quality Score"})
    fig_scatter.update_layout(template="plotly_dark", height=400, paper_bgcolor="#030712", plot_bgcolor="#111827")
    st.plotly_chart(fig_scatter, use_container_width=True)

# ══ MARKET REGIME TAB ══
with tab_regime:
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.markdown("### Regimen de Mercado")
        st.metric("Score Combinado", f"{REGIME['ov']}/100")
        st.error(REGIME["lbl"])
        st.caption(f"Override: {REGIME['ovrR']}")

        st.markdown("**Sub-scores**")
        st.progress(REGIME["se"], text=f"Sentimiento: {REGIME['se']}/100")
        st.progress(REGIME["te"], text=f"Tecnico: {REGIME['te']}/100")
        st.progress(REGIME["li"], text=f"Liquidez: {REGIME['li']}/100")

    with col_r2:
        st.markdown("### Indicadores")
        indicators = {
            "S&P 500": f"{REGIME['spx']:,.0f}", "VIX": f"{REGIME['vix']:.2f}",
            "Breadth": f"{REGIME['br']}%", "RSI": "48.85", "MACD": "-8.63",
            "HY Spread": "317 bps", "WTI": "$93.71", "US 10Y": "4.20%", "DXY": "100.5"
        }
        for name, val in indicators.items():
            st.text(f"{name}: {val}")

    with col_r3:
        st.markdown("### Triggers")
        triggers = [
            ("VIX Spike", "VIX > 25", False), ("Credit Stress", "HY > 400bps", False),
            ("Fear Extreme", "P/C > 1.2", False), ("Breadth Collapse", "Breadth < 50%", True),
            ("Oil Shock", "WTI >= $100", False), ("Rate Shock", "10Y >= 4.5%", True),
        ]
        for name, cond, active in triggers:
            if active:
                st.error(f"🔴 {name}: {cond}")
            else:
                st.success(f"✅ {name}: {cond}")

        st.info("**Nota Contrarian**: Risk-Off = OPORTUNIDAD en calidad alta. STRONG BUY en Final >= 75 con Upside > 10%.")

# ══ TECHNICAL ANALYSIS TAB ══
with tab_technical:
    tech_ticker = st.selectbox("Ticker para analisis tecnico", list(PORTFOLIO.keys()), key="tech_sel")
    tech_period = st.selectbox("Periodo", ["1mo","3mo","6mo","1y","2y"], index=1, key="tech_period")

    chart_data = fetch_chart_data(tech_ticker, tech_period)
    if chart_data is not None and not chart_data.empty:
        # Candlestick chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data["Open"], high=chart_data["High"], low=chart_data["Low"], close=chart_data["Close"], name="Price"))
        if "SMA20" in chart_data.columns:
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["SMA20"], mode="lines", name="SMA20", line=dict(color="#3b82f6", width=1)))
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["SMA50"], mode="lines", name="SMA50", line=dict(color="#f59e0b", width=1)))
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["BB_upper"], mode="lines", name="BB Upper", line=dict(color="#6b7280", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data["BB_lower"], mode="lines", name="BB Lower", line=dict(color="#6b7280", width=1, dash="dot")))

        info = PORTFOLIO[tech_ticker]
        fig.add_hline(y=info["fv"], line_dash="dash", line_color="#22c55e", annotation_text=f"Fair Value: ${info['fv']}")
        fig.update_layout(title=f"{tech_ticker} — {info['n']}", template="plotly_dark", height=500, xaxis_rangeslider_visible=False, paper_bgcolor="#030712", plot_bgcolor="#111827")
        st.plotly_chart(fig, use_container_width=True)

        # RSI + MACD
        if "RSI" in chart_data.columns:
            col_rsi, col_macd = st.columns(2)
            with col_rsi:
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=chart_data.index, y=chart_data["RSI"], mode="lines", name="RSI", line=dict(color="#a855f7", width=2)))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ef4444")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="#22c55e")
                fig_rsi.update_layout(title="RSI (14)", template="plotly_dark", height=200, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor="#030712", plot_bgcolor="#111827")
                st.plotly_chart(fig_rsi, use_container_width=True)
            with col_macd:
                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(x=chart_data.index, y=chart_data["MACD"], mode="lines", name="MACD", line=dict(color="#3b82f6", width=2)))
                fig_macd.add_trace(go.Scatter(x=chart_data.index, y=chart_data["MACD_signal"], mode="lines", name="Signal", line=dict(color="#f97316", width=1)))
                colors = ["#22c55e" if v >= 0 else "#ef4444" for v in chart_data["MACD_hist"].fillna(0)]
                fig_macd.add_trace(go.Bar(x=chart_data.index, y=chart_data["MACD_hist"], name="Histogram", marker_color=colors))
                fig_macd.update_layout(title="MACD", template="plotly_dark", height=200, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor="#030712", plot_bgcolor="#111827")
                st.plotly_chart(fig_macd, use_container_width=True)
    else:
        st.warning("No se pudieron cargar datos para este ticker")

# ══ NEWS TAB ══
with tab_news:
    news_ticker = st.selectbox("Ticker para noticias", list(PORTFOLIO.keys()), key="news_sel")
    news_items = fetch_news(news_ticker)
    if news_items:
        for item in news_items:
            title = item.get("title", "Sin titulo")
            link = item.get("link", "#")
            publisher = item.get("publisher", "")
            pub_time = item.get("providerPublishTime", 0)
            time_str = datetime.fromtimestamp(pub_time).strftime("%d %b %H:%M") if pub_time else ""
            st.markdown(f"**[{title}]({link})**")
            st.caption(f"{publisher} — {time_str}")
            st.markdown("---")
    else:
        st.info("No hay noticias recientes para este ticker")

# Footer
st.markdown("---")
st.caption(f"MARANGO EQUITY FUND, FI — ES0166932006 — Quality x Regime Dashboard — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
