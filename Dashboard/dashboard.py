"""
dashboard.py

AI vs Value Rotation Analytics Dashboard
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from yahooquery import Ticker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

try:
    from value_ai_rotation.rotation_v2 import (
        download_rotation_prices,
        get_rotation_dashboard_data,
        get_rotation_trend,
    )
except Exception as e:
    download_rotation_prices = None
    get_rotation_dashboard_data = None
    get_rotation_trend = None
    ROTATION_IMPORT_ERROR = e
else:
    ROTATION_IMPORT_ERROR = None

try:
    from value_ai_rotation.rotation_60_predictive import (
        build_60d_model_dataset,
        predict_latest_60d,
    )
except Exception as e:
    build_60d_model_dataset = None
    predict_latest_60d = None
    ROTATION_60D_IMPORT_ERROR = e
else:
    ROTATION_60D_IMPORT_ERROR = None


st.set_page_config(
    page_title="AI vs Value Rotation Analytics",
    page_icon="🔄",
    layout="wide",
)


# ============================================================
# Balanced Styling - prevents metric cutoff
# ============================================================

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-size: 16px !important;
    }

    h1 { font-size: 34px !important; }
    h2 { font-size: 26px !important; }
    h3 { font-size: 22px !important; }

    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 22px !important;
        white-space: nowrap;
    }

    [data-testid="stMetricDelta"] {
        font-size: 14px !important;
    }

    button[role="tab"] {
        font-size: 14px !important;
    }

    .stDataFrame {
        font-size: 14px !important;
    }

    .signal-box {
        font-size: 18px;
        padding: 18px;
        border-radius: 12px;
        line-height: 1.55;
        margin-bottom: 16px;
    }

    .recommendation-box {
        font-size: 17px;
        padding: 18px;
        border-radius: 12px;
        line-height: 1.55;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Helpers
# ============================================================

def get_query_symbol(default_symbol="QQQ"):
    try:
        return st.query_params.get("symbol", default_symbol).upper()
    except Exception:
        return default_symbol


@st.cache_data(ttl=3600)
def download_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    ticker = Ticker(symbol)
    hist = ticker.history(period=period)

    if hist is None or hist.empty:
        return pd.DataFrame()

    df = hist.copy()

    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()

    if "date" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
    return df.sort_values("date")


@st.cache_data(ttl=3600)
def get_60d_prediction_data() -> dict:
    prices = download_rotation_prices(period="5y")
    dataset = build_60d_model_dataset(prices)
    return predict_latest_60d(dataset)


def plot_price_chart(df: pd.DataFrame, symbol: str):
    df = df.copy()
    price_col = "adjclose" if "adjclose" in df.columns else "close"

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df[price_col],
            mode="lines",
            name=f"{symbol} Price",
        )
    )

    if "close" in df.columns:
        df["MA20"] = df["close"].rolling(20).mean()
        df["MA50"] = df["close"].rolling(50).mean()

        fig.add_trace(
            go.Scatter(x=df["date"], y=df["MA20"], mode="lines", name="20-Day MA")
        )
        fig.add_trace(
            go.Scatter(x=df["date"], y=df["MA50"], mode="lines", name="50-Day MA")
        )

    fig.update_layout(
        title=f"{symbol} Price Trend",
        xaxis_title="Date",
        yaxis_title="Price",
        height=500,
    )

    return fig


def classify_price_trend(df: pd.DataFrame):
    if df.empty or "close" not in df.columns or len(df) < 60:
        return "Not enough data"

    df = df.copy()
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()

    close = df["close"].iloc[-1]
    ma20 = df["MA20"].iloc[-1]
    ma50 = df["MA50"].iloc[-1]

    if close > ma20 > ma50:
        return "Bullish"
    elif close < ma20 < ma50:
        return "Bearish"
    else:
        return "Mixed"


def get_signal_meaning(signal: str) -> str:
    if signal == "AI / GROWTH DOMINANCE":
        return "20D tactical read: AI/growth is still leading. Rotation into value has not confirmed yet."
    if signal == "EARLY ROTATION":
        return "20D tactical read: some rotation signals are starting to appear, but confirmation is still early."
    if signal == "CONFIRMED ROTATION":
        return "20D tactical read: multiple signals suggest money is rotating away from AI/growth toward value, quality, or defensive areas."
    if signal == "STRONG VALUE / DEFENSIVE ROTATION":
        return "20D tactical read: rotation is broad and strong. Value, defensives, and risk-off signals are leading."
    return "Not enough data to classify the regime."


def get_60d_signal_meaning(signal: str) -> dict:
    if signal == "ROTATION EXTENDED / AI REASSERTION RISK":
        return {
            "meaning": "60D strategic read: the value rotation may already be mature. Historically, elevated rotation scores have often been followed by AI/growth reasserting over the next 60 trading days.",
            "use": "Use this as a trim, hedge, or avoid-chasing warning for value/defensive exposure. Watch AI internals for re-entry confirmation.",
        }

    if signal == "60D AI / GROWTH REASSERTION":
        return {
            "meaning": "60D strategic read: the setup favors AI/growth over value for the next 60 trading days.",
            "use": "Use this as support for rebuilding AI/growth exposure or reducing extended value tilts.",
        }

    if signal == "60D VALUE ROTATION PERSISTENCE":
        return {
            "meaning": "60D strategic read: the rotation setup has enough historical support to suggest value may keep outperforming AI/growth.",
            "use": "Use this as support for holding value, quality, or defensive tilts longer, while still monitoring risk appetite.",
        }

    return {
        "meaning": "60D strategic read: no strong historical edge is present for either value persistence or AI/growth reassertion.",
        "use": "Use the 20D tactical signal for shorter-term positioning, but avoid making a large 60D bet from this read alone.",
    }


def get_two_clock_meaning(signal: str, signal_60d: str) -> str:
    if (
        signal in {"CONFIRMED ROTATION", "STRONG VALUE / DEFENSIVE ROTATION"}
        and signal_60d == "ROTATION EXTENDED / AI REASSERTION RISK"
    ):
        return (
            "Combined read: value may still be working tactically, but the 60D layer warns "
            "that the move is mature. This is a harvest/trim/watch-AI-reentry setup, not a chase-value setup."
        )

    if signal in {"EARLY ROTATION", "CONFIRMED ROTATION"} and signal_60d == "NO 60D EDGE":
        return (
            "Combined read: rotation pressure is visible tactically, but there is not enough "
            "60D evidence to extend that view into a longer holding-period call."
        )

    if signal == "AI / GROWTH DOMINANCE":
        return (
            "Combined read: AI/growth remains the primary leadership regime. Treat value signals "
            "as watchlist evidence until rotation broadens."
        )

    return (
        "Combined read: use the 20D layer for tactical rotation pressure and the 60D layer "
        "as the longer-term persistence or exhaustion check."
    )


def shorten_signal(signal: str) -> str:
    mapping = {
        "AI / GROWTH DOMINANCE": "AI / GROWTH",
        "EARLY ROTATION": "EARLY ROT",
        "CONFIRMED ROTATION": "CONF ROT",
        "STRONG VALUE / DEFENSIVE ROTATION": "VALUE / DEF",
        "NO DATA": "NO DATA",
    }
    return mapping.get(signal, signal)


def shorten_trend(trend: str) -> str:
    mapping = {
        "AI DOMINANCE STRENGTHENING": "AI ↑↑",
        "ROTATION STRENGTHENING": "ROT ↑↑",
        "ROTATION IMPROVING": "ROT ↑",
        "ROTATION WEAKENING": "ROT ↓",
        "UNCHANGED": "FLAT",
        "NO DATA": "NO DATA",
    }
    return mapping.get(trend, trend)


def get_recommendation(signal: str, trend_label: str) -> dict:
    if signal == "AI / GROWTH DOMINANCE" and "AI DOMINANCE STRENGTHENING" in trend_label:
        return {
            "title": "Stay AI/Growth Biased",
            "bias": "Aggressive / Growth",
            "action": "AI/growth leadership is strong and rotation signals are weakening. Favor AI/growth exposure, semiconductors, and momentum setups.",
            "risk": "Crowded AI trade or sudden reversal.",
        }

    if signal == "AI / GROWTH DOMINANCE" and "ROTATION" in trend_label:
        return {
            "title": "Stay Growth, Watch Rotation",
            "bias": "Growth with Rotation Watch",
            "action": "AI/growth is still leading, but rotation pressure is improving. Monitor value, breadth, quality, and credit for confirmation.",
            "risk": "Early rotation signs may fail.",
        }

    if signal == "EARLY ROTATION":
        return {
            "title": "Begin Partial Rotation",
            "bias": "Balanced / Transition",
            "action": "Some rotation signals are appearing. Gradually reduce speculative AI exposure and add quality, value, industrials, or international value.",
            "risk": "Rotation is not fully confirmed.",
        }

    if signal == "CONFIRMED ROTATION":
        return {
            "title": "Favor Value / Quality",
            "bias": "Value / Quality Tilt",
            "action": "Multiple signals suggest leadership is shifting away from AI/growth. Favor value, quality, industrials, financials, and broader market exposure.",
            "risk": "Growth leadership may reassert.",
        }

    if signal == "STRONG VALUE / DEFENSIVE ROTATION":
        return {
            "title": "Defensive Rotation Mode",
            "bias": "Defensive / Value",
            "action": "Rotation is broad and defensive. Favor value, quality, bonds, lower-volatility assets, and reduce speculative growth exposure.",
            "risk": "Defensive positioning can lag if risk appetite rebounds.",
        }

    return {
        "title": "No Clear Recommendation",
        "bias": "Neutral",
        "action": "Not enough signal strength to make a clear regime-based recommendation.",
        "risk": "Insufficient or noisy data.",
    }


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("AI vs Value Rotation")

default_symbol = get_query_symbol("QQQ")

symbol = st.sidebar.text_input("Market Proxy / Ticker", value=default_symbol).upper()

period = st.sidebar.selectbox(
    "Price History Period",
    ["3mo", "6mo", "1y", "2y", "5y"],
    index=2,
)

st.sidebar.markdown("---")
st.sidebar.subheader("Rotation Tracker")

rotation_period = st.sidebar.selectbox(
    "Rotation History Period",
    ["3mo", "6mo", "1y", "2y", "5y"],
    index=3,
)

trend_lookback = st.sidebar.selectbox(
    "Trend Lookback",
    [5, 10, 20, 60],
    index=2,
)


# ============================================================
# Header
# ============================================================

st.title("AI vs Value Rotation Analytics")
st.caption(
    "Market regime dashboard tracking AI/growth versus value, cyclicals, quality, credit, and breadth."
)


# ============================================================
# Market Proxy Section
# ============================================================

st.header(f"{symbol} Market Proxy Overview")

stock_df = download_stock_data(symbol, period=period)

if stock_df.empty:
    st.warning(f"No market data found for {symbol}.")
else:
    price_col = "adjclose" if "adjclose" in stock_df.columns else "close"

    latest = stock_df.iloc[-1]
    prior = stock_df.iloc[-2] if len(stock_df) > 1 else latest

    latest_close = latest.get(price_col, None)
    prior_close = prior.get(price_col, None)

    daily_change = None
    if latest_close is not None and prior_close not in [None, 0]:
        daily_change = (latest_close / prior_close - 1) * 100

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Latest Close",
            f"${latest_close:,.2f}" if latest_close is not None else "N/A",
        )

    with col2:
        st.metric(
            "Daily Change",
            f"{daily_change:.2f}%" if daily_change is not None else "N/A",
        )

    with col3:
        st.metric("Trend", classify_price_trend(stock_df))

    st.plotly_chart(plot_price_chart(stock_df, symbol), use_container_width=True)

    with st.expander("Recent Price Data"):
        st.dataframe(stock_df.tail(20), use_container_width=True)


# ============================================================
# Value vs AI Rotation Tracker
# ============================================================

st.markdown("---")
st.header("Value vs AI Rotation Tracker")

st.caption(
    "Tracks whether market leadership is favoring AI/growth or rotating toward value, cyclicals, quality, bonds, and broader participation."
)

if get_rotation_dashboard_data is None:
    st.error(f"Rotation tracker import failed: {ROTATION_IMPORT_ERROR}")

else:
    try:
        rotation_features, rotation_score = get_rotation_dashboard_data(
            period=rotation_period
        )

        score = rotation_score.get("rotation_score", 0)
        max_score = rotation_score.get("max_score", 9)
        signal = rotation_score.get("signal", "NO DATA")
        as_of = rotation_score.get("as_of", "N/A")

        rotation_trend = get_rotation_trend(
            rotation_features,
            lookback_days=trend_lookback,
        )

        trend_label = rotation_trend.get("trend", "NO DATA")
        trend_display = shorten_trend(trend_label)
        signal_display = shorten_signal(signal)

        score_change = rotation_trend.get("score_change", 0)
        prior_score = rotation_trend.get("prior_score", "N/A")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Signal", signal_display)

        with col2:
            st.metric("Score", f"{score} / {max_score}")

        with col3:
            st.metric(
                f"{trend_lookback}D Trend",
                trend_display,
                delta=f"{score_change:+.0f}" if pd.notna(score_change) else None,
            )

        with col4:
            st.metric("As Of", str(as_of)[:10])

        meaning = get_signal_meaning(signal)
        recommendation = get_recommendation(signal, trend_label)

        st.subheader("Current Regime Interpretation")

        if "AI / GROWTH" in signal:
            bg_color = "#eaf3ff"
            border_color = "#0066cc"
        elif "ROTATION" in signal:
            bg_color = "#fff4e6"
            border_color = "#ff9900"
        else:
            bg_color = "#f2f2f2"
            border_color = "#777777"

        st.markdown(
            f"""
<div class="signal-box" style="
    background-color:{bg_color};
    border-left:7px solid {border_color};
">
<b>Signal:</b> {signal}<br>
<b>Trend:</b> {trend_label}<br>
<b>Meaning:</b> {meaning}
</div>
""",
            unsafe_allow_html=True,
        )

        st.subheader("Recommendation Layer")

        st.markdown(
            f"""
<div class="recommendation-box" style="
    background-color:#f6f6f6;
    border-left:7px solid #444444;
">
<b>Recommendation:</b> {recommendation["title"]}<br>
<b>Portfolio Bias:</b> {recommendation["bias"]}<br>
<b>Action:</b> {recommendation["action"]}<br>
<b>Risk Note:</b> {recommendation["risk"]}
</div>
""",
            unsafe_allow_html=True,
        )

        if max_score and max_score > 0:
            st.progress(min(score / max_score, 1.0))

        st.caption(
            f"Trend compares current score {score} against prior score {prior_score} from {trend_lookback} trading days ago."
        )

        st.subheader("60D Predictive Layer")
        signal_60d = "NO 60D EDGE"
        combined_meaning = get_two_clock_meaning(signal, signal_60d)

        if (
            download_rotation_prices is None
            or build_60d_model_dataset is None
            or predict_latest_60d is None
        ):
            st.warning(f"60D model import failed: {ROTATION_60D_IMPORT_ERROR}")
        else:
            try:
                prediction_60d = get_60d_prediction_data()

                signal_60d = prediction_60d.get("signal_60d", "NO 60D EDGE")
                value_probability_60d = prediction_60d.get("value_probability_60d", None)
                ai_probability_60d = prediction_60d.get("ai_probability_60d", None)
                expected_60d = prediction_60d.get("expected_relative_60d", None)
                train_rows_60d = prediction_60d.get("train_rows", 0)
                matched_rows_60d = prediction_60d.get("matched_observations", 0)
                as_of_60d = prediction_60d.get("as_of", "N/A")
                signal_display_60d = {
                    "60D VALUE ROTATION PERSISTENCE": "VALUE PERSIST",
                    "60D AI / GROWTH REASSERTION": "AI REASSERT",
                    "ROTATION EXTENDED / AI REASSERTION RISK": "AI RISK",
                    "ROTATION EXTENDED / REVERSAL RISK": "REVERSAL RISK",
                    "NO 60D EDGE": "NO EDGE",
                }.get(signal_60d, signal_60d)

                p1, p2, p3, p4 = st.columns(4)

                with p1:
                    st.metric("60D Signal", signal_display_60d)

                with p2:
                    st.metric(
                        "Value Prob",
                        f"{value_probability_60d:.0%}" if pd.notna(value_probability_60d) else "N/A",
                    )

                with p3:
                    st.metric(
                        "AI Prob",
                        f"{ai_probability_60d:.0%}" if pd.notna(ai_probability_60d) else "N/A",
                    )

                with p4:
                    st.metric(
                        "Expected Rel",
                        f"{expected_60d:.2%}" if pd.notna(expected_60d) else "N/A",
                    )

                if "PERSISTENCE" in signal_60d:
                    bg_color_60d = "#e9f7ef"
                    border_color_60d = "#1f8f4d"
                elif "REASSERTION" in signal_60d or "REVERSAL" in signal_60d:
                    bg_color_60d = "#fff0f0"
                    border_color_60d = "#cc3333"
                else:
                    bg_color_60d = "#f2f2f2"
                    border_color_60d = "#777777"

                meaning_60d = get_60d_signal_meaning(signal_60d)
                combined_meaning = get_two_clock_meaning(signal, signal_60d)

                st.markdown(
                    f"""
<div class="signal-box" style="
    background-color:{bg_color_60d};
    border-left:7px solid {border_color_60d};
">
<b>60D Model:</b> {signal_60d}<br>
<b>Meaning:</b> {meaning_60d["meaning"]}<br>
<b>How to Use:</b> {meaning_60d["use"]}<br>
<b>As Of:</b> {str(as_of_60d)[:10]}<br>
<b>Matched Observations:</b> {matched_rows_60d:,}<br>
<b>Training Rows:</b> {train_rows_60d:,}<br>
<b>Training Window:</b> 5Y
</div>
""",
                    unsafe_allow_html=True,
                )

            except Exception as e:
                st.warning(f"60D predictive model could not load: {e}")

        st.subheader("Two-Clock Interpretation")

        if "ROTATION" in signal or "VALUE" in signal:
            bg_color_combined = "#f7f3e8"
            border_color_combined = "#8a6d1d"
        else:
            bg_color_combined = "#eef5fb"
            border_color_combined = "#336699"

        st.markdown(
            f"""
<div class="recommendation-box" style="
    background-color:{bg_color_combined};
    border-left:7px solid {border_color_combined};
">
<b>20D Clock:</b> tactical rotation pressure.<br>
<b>60D Clock:</b> longer-term persistence or exhaustion check.<br>
<b>Current Meaning:</b> {combined_meaning}
</div>
""",
            unsafe_allow_html=True,
        )

        st.subheader("Signal Details")

        details = rotation_score.get("details", {})
        detail_df = pd.DataFrame(
            [{"Signal": k, "Triggered": v} for k, v in details.items()]
        )

        st.dataframe(detail_df, use_container_width=True)

        st.subheader("Core Rotation Ratios")

        ratio_groups = {
            "Value / Cyclicals vs AI": {
                "description": """
**How to read this tab:**  
These ratios compare value-oriented and real-economy sectors against AI/growth.

- Rising lines mean value, industrials, energy, or international value are outperforming AI/growth.
- Falling lines mean AI/growth is still leading.
- Broad movement higher across several lines can indicate rotation away from AI.
                """,
                "cols": [
                    "value_vs_ai_ratio",
                    "industrials_vs_ai_ratio",
                    "energy_vs_ai_ratio",
                    "international_value_vs_ai_ratio",
                ],
            },
            "Quality / Breadth": {
                "description": """
**How to read this tab:**  
This shows whether investors are favoring profitable, higher-quality companies and broader market participation.

- `quality_vs_speculation_ratio` = QUAL / ARKK
- `market_breadth_ratio` = RSP / SPY

Rising lines suggest investors are moving toward quality and broader participation.  
Falling lines suggest speculation and mega-cap growth are still leading.
                """,
                "cols": [
                    "quality_vs_speculation_ratio",
                    "market_breadth_ratio",
                ],
            },
            "Credit / Risk Appetite": {
                "description": """
**How to read this tab:**  
This measures risk appetite in the credit market.

- `credit_risk_appetite_ratio` = JNK / IEF

Rising means investors are more willing to take risk, which can support AI/growth.  
Falling means investors are moving toward safety, which can warn of weakening risk appetite.
                """,
                "cols": ["credit_risk_appetite_ratio"],
            },
            "AI Internals": {
                "description": """
**How to read this tab:**  
This checks whether AI infrastructure is still leading broader growth.

- `semis_vs_growth_ratio` = SMH / QQQ

Rising means semiconductors are outperforming broader tech, which suggests AI strength remains healthy.  
Falling means AI leadership may be weakening under the surface.
                """,
                "cols": ["semis_vs_growth_ratio"],
            },
        }

        tabs = st.tabs(list(ratio_groups.keys()))

        for tab, (group_name, group_info) in zip(tabs, ratio_groups.items()):
            with tab:
                st.markdown(group_info["description"])

                available_cols = [
                    c for c in group_info["cols"] if c in rotation_features.columns
                ]

                if available_cols:
                    st.line_chart(
                        rotation_features[available_cols].dropna(),
                        use_container_width=True,
                    )
                else:
                    st.info("No ratio data available for this section.")

        st.subheader("Standalone Momentum Signals")

        st.caption(
            "These show 20-day returns for the individual ETFs/indexes used in the rotation model."
        )

        momentum_cols = [
            "QQQ_ret_20",
            "SMH_ret_20",
            "VTV_ret_20",
            "XLI_ret_20",
            "XLE_ret_20",
            "EFV_ret_20",
            "TLT_ret_20",
            "VIX_ret_20",
        ]

        available_momentum_cols = [
            c for c in momentum_cols if c in rotation_features.columns
        ]

        if available_momentum_cols:
            latest_momentum = (
                rotation_features[available_momentum_cols]
                .dropna(how="all")
                .tail(1)
                .T
                .reset_index()
            )

            latest_momentum.columns = ["Signal", "20-Day Return"]

            latest_momentum["20-Day Return"] = latest_momentum[
                "20-Day Return"
            ].apply(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "N/A")

            st.dataframe(latest_momentum, use_container_width=True)

        with st.expander("Raw Rotation Data"):
            st.dataframe(rotation_features.tail(50), use_container_width=True)

    except Exception as e:
        st.warning(f"Rotation tracker could not load: {e}")


st.markdown("---")
st.caption("Signals are for research and education only. They are not financial advice.")
