"""
dashboard.py

AI vs Value Rotation Analytics Dashboard
"""

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from yahooquery import Ticker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

PUBLICATION_NAME = "Rotation Clock Weekly"
PUBLICATION_TAGLINE = (
    "A two-clock read on AI/growth leadership, tactical value rotation, "
    "and when not to chase the trade."
)
DEFAULT_SIGNUP_URL = "https://financenow11.substack.com"
FIRST_ARTICLE_URL = "https://financenow11.substack.com/p/why-i-built-a-two-clock-dashboard"
FIRST_ARTICLE_TITLE = "Why I Built a Two-Clock Dashboard for AI vs Value Rotation"

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
    from value_ai_rotation.rotation_20_predictive import (
        build_20d_model_dataset,
        predict_latest_20d,
        predict_recent_20d,
    )
except Exception as e:
    build_20d_model_dataset = None
    predict_latest_20d = None
    predict_recent_20d = None
    ROTATION_20D_IMPORT_ERROR = e
else:
    ROTATION_20D_IMPORT_ERROR = None

try:
    from value_ai_rotation.rotation_60_predictive import (
        build_60d_model_dataset,
        predict_latest_60d,
        predict_recent_60d,
    )
except Exception as e:
    build_60d_model_dataset = None
    predict_latest_60d = None
    predict_recent_60d = None
    ROTATION_60D_IMPORT_ERROR = e
else:
    ROTATION_60D_IMPORT_ERROR = None

try:
    from value_ai_rotation.rotation_continuous_predictive import (
        build_model_agreement,
        build_qqq_direction_agreement,
    )
except Exception as e:
    build_model_agreement = None
    build_qqq_direction_agreement = None
    CONTINUOUS_MODEL_IMPORT_ERROR = e
else:
    CONTINUOUS_MODEL_IMPORT_ERROR = None

try:
    from value_ai_rotation.rotation_history import (
        build_clock_snapshot,
        get_history_path,
        read_clock_history,
        upsert_clock_snapshot,
    )
except Exception as e:
    build_clock_snapshot = None
    get_history_path = None
    read_clock_history = None
    upsert_clock_snapshot = None
    ROTATION_HISTORY_IMPORT_ERROR = e
else:
    ROTATION_HISTORY_IMPORT_ERROR = None


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


def get_newsletter_signup_url() -> str:
    env_url = os.getenv("NEWSLETTER_SIGNUP_URL")
    if env_url:
        return env_url

    try:
        return st.secrets.get("NEWSLETTER_SIGNUP_URL", DEFAULT_SIGNUP_URL)
    except Exception:
        return DEFAULT_SIGNUP_URL


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


@st.cache_data(ttl=3600)
def get_20d_prediction_data() -> dict:
    prices = download_rotation_prices(period="5y")
    dataset = build_20d_model_dataset(prices)
    return predict_latest_20d(dataset)


def get_clock_trend_data(lookback_days: int = 30) -> pd.DataFrame:
    prices = download_rotation_prices(period="5y")

    dataset_20d = build_20d_model_dataset(prices)
    trend_20d = predict_recent_20d(dataset_20d, lookback_days=lookback_days)

    dataset_60d = build_60d_model_dataset(prices)
    trend_60d = predict_recent_60d(dataset_60d, lookback_days=lookback_days)

    if trend_20d.empty and trend_60d.empty:
        return pd.DataFrame()

    combined = pd.DataFrame(index=trend_20d.index.union(trend_60d.index))

    if not trend_20d.empty:
        combined["rotation_score"] = trend_20d["rotation_score"]
        combined["20D Signal"] = trend_20d["signal_20d"]
        combined["20D Favors Value"] = trend_20d["value_probability_20d"]
        combined["20D Favors AI"] = trend_20d["ai_probability_20d"]
        combined["20D Expected Rel"] = trend_20d["expected_relative_20d"]
        combined["20D Matched Obs"] = trend_20d["matched_observations"]

    if not trend_60d.empty:
        combined["rotation_score"] = combined.get("rotation_score", trend_60d["rotation_score"])
        combined["60D Signal"] = trend_60d["signal_60d"]
        combined["60D Favors Value"] = trend_60d["value_probability_60d"]
        combined["60D Favors AI"] = trend_60d["ai_probability_60d"]
        combined["60D Expected Rel"] = trend_60d["expected_relative_60d"]
        combined["60D Matched Obs"] = trend_60d["matched_observations"]

    saved_history = get_saved_clock_history()
    if not saved_history.empty:
        combined = pd.concat([combined, saved_history], axis=0)
        combined = combined.sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]

    combined.index = pd.to_datetime(combined.index)
    return combined.sort_index().tail(lookback_days)


@st.cache_data(ttl=3600)
def get_model_agreement_data() -> dict:
    prices = download_rotation_prices(period="5y")
    return build_model_agreement(prices)


@st.cache_data(ttl=3600)
def get_qqq_direction_data() -> dict:
    prices = download_rotation_prices(period="5y")
    return build_qqq_direction_agreement(prices)


def get_saved_clock_history() -> pd.DataFrame:
    if read_clock_history is None:
        return pd.DataFrame()

    history = read_clock_history()
    if history.empty:
        return pd.DataFrame()

    trend = history.copy()
    trend["Date"] = pd.to_datetime(trend["Date"], errors="coerce")
    trend = trend.dropna(subset=["Date"]).set_index("Date")

    if "Score" in trend.columns:
        trend["rotation_score"] = trend["Score"]
        trend = trend.drop(columns=["Score"])

    numeric_cols = [
        "rotation_score",
        "20D Favors Value",
        "20D Favors AI",
        "20D Expected Rel",
        "20D Matched Obs",
        "60D Favors Value",
        "60D Favors AI",
        "60D Expected Rel",
        "60D Matched Obs",
    ]
    for col in numeric_cols:
        if col in trend.columns:
            trend[col] = pd.to_numeric(trend[col], errors="coerce")

    return trend.sort_index()


def save_current_clock_snapshot() -> tuple[pd.DataFrame, Path | None]:
    if build_clock_snapshot is None or upsert_clock_snapshot is None or get_history_path is None:
        return pd.DataFrame(), None

    prediction_20d = get_20d_prediction_data()
    prediction_60d = get_60d_prediction_data()
    agreement = get_model_agreement_data() if build_model_agreement is not None else {}
    direction = get_qqq_direction_data() if build_qqq_direction_agreement is not None else {}

    snapshot = build_clock_snapshot(
        prediction_20d=prediction_20d,
        prediction_60d=prediction_60d,
        agreement=agreement,
        direction=direction,
    )
    history = upsert_clock_snapshot(snapshot)
    return history, get_history_path()


def format_model_agreement_table(models: pd.DataFrame) -> pd.DataFrame:
    if models.empty:
        return pd.DataFrame()

    rows = []
    for _, row in models.iterrows():
        available = bool(row.get("available", False))
        if available:
            rows.append(
                {
                    "Model": row.get("model", "N/A"),
                    "Read": f"Favors {row.get('favored_side', 'N/A')}",
                    "Value Prob": f"{row.get('value_probability', np.nan):.1%}",
                    "AI Prob": f"{row.get('ai_probability', np.nan):.1%}",
                    "Edge": f"{row.get('edge', np.nan):.1%}",
                    "Rows": f"{int(row.get('training_rows', 0)):,}",
                    "Features": f"{int(row.get('feature_count', 0)):,}",
                }
            )
        else:
            rows.append(
                {
                    "Model": row.get("model", "N/A"),
                    "Read": "Unavailable",
                    "Value Prob": "N/A",
                    "AI Prob": "N/A",
                    "Edge": "N/A",
                    "Rows": f"{int(row.get('training_rows', 0)):,}" if pd.notna(row.get("training_rows", np.nan)) else "N/A",
                    "Features": "N/A",
                }
            )

    return pd.DataFrame(rows)


def format_direction_table(models: pd.DataFrame) -> pd.DataFrame:
    if models.empty:
        return pd.DataFrame()

    rows = []
    for _, row in models.iterrows():
        available = bool(row.get("available", False))
        if available:
            rows.append(
                {
                    "Model": row.get("model", "N/A"),
                    "Read": f"QQQ {row.get('favored_side', 'N/A')}",
                    "Up Prob": f"{row.get('up_probability', np.nan):.1%}",
                    "Down Prob": f"{row.get('down_probability', np.nan):.1%}",
                    "Edge": f"{row.get('edge', np.nan):.1%}",
                    "Expected Return": f"{row.get('expected_return', np.nan):.2%}",
                    "Rows": f"{int(row.get('training_rows', 0)):,}",
                }
            )
        else:
            rows.append(
                {
                    "Model": row.get("model", "N/A"),
                    "Read": "Unavailable",
                    "Up Prob": "N/A",
                    "Down Prob": "N/A",
                    "Edge": "N/A",
                    "Expected Return": "N/A",
                    "Rows": f"{int(row.get('training_rows', 0)):,}" if pd.notna(row.get("training_rows", np.nan)) else "N/A",
                }
            )

    return pd.DataFrame(rows)


def agreement_meaning(label: str) -> str:
    if label == "VALUE AGREEMENT":
        return "continuous models agree that value has the edge."
    if label == "AI AGREEMENT":
        return "continuous models agree that AI/growth has the edge."
    if label == "MIXED":
        return "continuous models disagree, so confidence should be lower."
    return "not enough model history is available for an agreement read."


def direction_meaning(label: str) -> str:
    if label == "QQQ UP AGREEMENT":
        return "continuous direction models agree that QQQ has positive forward-return odds."
    if label == "QQQ DOWN AGREEMENT":
        return "continuous direction models agree that QQQ has negative forward-return risk."
    if label == "MIXED":
        return "direction models disagree, so QQQ direction confidence should be lower."
    return "not enough model history is available for a QQQ direction read."


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


def get_favored_read(value_probability: float | None, ai_probability: float | None, clock: str) -> dict:
    if value_probability is None or ai_probability is None:
        return {
            "side": "Neutral",
            "title": f"{clock} Neutral",
            "probability": None,
            "color": "#777777",
            "bg_color": "#f2f2f2",
            "border_color": "#777777",
        }

    if pd.isna(value_probability) or pd.isna(ai_probability):
        return {
            "side": "Neutral",
            "title": f"{clock} Neutral",
            "probability": None,
            "color": "#777777",
            "bg_color": "#f2f2f2",
            "border_color": "#777777",
        }

    if value_probability >= ai_probability:
        return {
            "side": "Value",
            "title": f"{clock} Favors Value",
            "probability": value_probability,
            "color": "#1f8f4d",
            "bg_color": "#e9f7ef",
            "border_color": "#1f8f4d",
        }

    return {
        "side": "AI",
        "title": f"{clock} Favors AI",
        "probability": ai_probability,
        "color": "#1f77b4",
        "bg_color": "#eef5fb",
        "border_color": "#1f77b4",
    }


def plot_clock_trend(trend_df: pd.DataFrame):
    fig = go.Figure()

    value_color = "#1f8f4d"
    ai_color = "#1f77b4"

    fig.add_trace(
        go.Scatter(
            x=[trend_df.index[0]],
            y=[0],
            mode="markers",
            name="Marker: favors Value",
            visible="legendonly",
            marker={"size": 10, "color": value_color},
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[trend_df.index[0]],
            y=[0],
            mode="markers",
            name="Marker: favors AI",
            visible="legendonly",
            marker={"size": 10, "color": ai_color},
            hoverinfo="skip",
        )
    )

    if {"20D Favors Value", "20D Favors AI"}.issubset(trend_df.columns):
        favors_value = trend_df["20D Favors Value"] >= trend_df["20D Favors AI"]
        favored_probability = trend_df[["20D Favors Value", "20D Favors AI"]].max(axis=1)
        fig.add_trace(
            go.Scatter(
                x=[trend_df.index[0]],
                y=[favored_probability.iloc[0] * 100],
                mode="lines+markers",
                name="20D Clock",
                visible="legendonly",
                line={"color": "#111111", "width": 3},
                marker={"size": 8, "color": "#111111"},
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=trend_df.index,
                y=favored_probability * 100,
                mode="lines+markers",
                name="20D Clock",
                showlegend=False,
                line={"color": "#111111", "width": 3},
                marker={
                    "size": 8,
                    "color": [value_color if side else ai_color for side in favors_value],
                    "line": {"color": "white", "width": 1},
                },
                customdata=[
                    ["Value" if side else "AI"] for side in favors_value
                ],
                hovertemplate="%{x|%b %d, %Y}<br>20D favors %{customdata[0]}<br>Probability: %{y:.1f}%<extra></extra>",
            )
        )

    if {"60D Favors Value", "60D Favors AI"}.issubset(trend_df.columns):
        favors_value = trend_df["60D Favors Value"] >= trend_df["60D Favors AI"]
        favored_probability = trend_df[["60D Favors Value", "60D Favors AI"]].max(axis=1)
        fig.add_trace(
            go.Scatter(
                x=[trend_df.index[0]],
                y=[favored_probability.iloc[0] * 100],
                mode="lines+markers",
                name="60D Clock",
                visible="legendonly",
                line={"color": "#777777", "width": 3, "dash": "dash"},
                marker={"size": 8, "color": "#777777"},
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=trend_df.index,
                y=favored_probability * 100,
                mode="lines+markers",
                name="60D Clock",
                showlegend=False,
                line={"color": "#777777", "width": 3, "dash": "dash"},
                marker={
                    "size": 8,
                    "color": [value_color if side else ai_color for side in favors_value],
                    "line": {"color": "white", "width": 1},
                },
                customdata=[
                    ["Value" if side else "AI"] for side in favors_value
                ],
                hovertemplate="%{x|%b %d, %Y}<br>60D favors %{customdata[0]}<br>Probability: %{y:.1f}%<extra></extra>",
            )
        )

    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="#777777",
        annotation_text="50% line",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="30D Clock Trend",
        xaxis_title="As-of Date",
        yaxis_title="Probability",
        yaxis={"range": [0, 100], "ticksuffix": "%"},
        height=420,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        margin={"l": 40, "r": 20, "t": 80, "b": 40},
    )

    return fig


def plot_probability_meter(
    probability: float | None,
    title: str,
    label: str,
    bar_color: str,
):
    value = None
    if probability is not None and pd.notna(probability):
        value = max(0, min(100, probability * 100))

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value if value is not None else 0,
            number={"suffix": "%", "font": {"size": 34}},
            title={
                "text": f"<b>{title}</b><br><span style='font-size:0.85em;color:#666'>{label}</span>",
                "font": {"size": 16},
            },
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#777"},
                "bar": {"color": bar_color, "thickness": 0.28},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "#dddddd",
                "steps": [
                    {"range": [0, 40], "color": "#f2f2f2"},
                    {"range": [40, 60], "color": "#fff4d6"},
                    {"range": [60, 100], "color": "#e8f2ff"},
                ],
                "threshold": {
                    "line": {"color": "#333333", "width": 3},
                    "thickness": 0.75,
                    "value": 50,
                },
            },
        )
    )

    fig.update_layout(
        height=285,
        margin={"l": 25, "r": 25, "t": 90, "b": 15},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#30313f"},
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


def get_20d_quality_meaning(signal: str) -> dict:
    if signal == "20D HIGH-CONVICTION VALUE ROTATION":
        return {
            "meaning": "20D quality read: the rotation score is high and AI internals are not breaking down. Historically, this has been the strongest tactical value-rotation setup.",
            "use": "Use this as the highest-quality short-term value/quality/defensive tilt signal.",
        }

    if signal == "20D ROTATION SIGNAL QUALITY WARNING":
        return {
            "meaning": "20D quality read: the rotation score is high, but semiconductors are weakening versus broader growth. Historically, that has made the tactical value signal less reliable.",
            "use": "Use smaller position sizing, wait for confirmation, or avoid chasing the value trade.",
        }

    if signal == "20D VALUE ROTATION WATCH":
        return {
            "meaning": "20D quality read: rotation pressure is visible, but the setup is not yet high-conviction.",
            "use": "Use this as a watch/partial-tilt signal rather than a full tactical rotation call.",
        }

    if signal == "20D VALUE ROTATION MIXED":
        return {
            "meaning": "20D quality read: the score is elevated but signal quality is mixed.",
            "use": "Wait for better breadth, credit, volatility, or AI-internals confirmation before increasing exposure.",
        }

    if signal == "20D EARLY ROTATION":
        return {
            "meaning": "20D quality read: rotation is beginning but is still early.",
            "use": "Monitor value, breadth, and quality leadership before treating this as confirmed.",
        }

    return {
        "meaning": "20D quality read: AI/growth dominance or insufficient rotation evidence.",
        "use": "Do not use this as a value-rotation entry signal.",
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

signup_url = get_newsletter_signup_url()

st.sidebar.markdown("---")
st.sidebar.subheader(PUBLICATION_NAME)
st.sidebar.caption(PUBLICATION_TAGLINE)
st.sidebar.markdown(f"[Join the free weekly note]({signup_url})")
st.sidebar.markdown(f"[Read the first article]({FIRST_ARTICLE_URL})")

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

with st.expander(f"{PUBLICATION_NAME}: weekly market note", expanded=True):
    st.markdown(
        f"""
**{PUBLICATION_TAGLINE}**

The weekly note turns the dashboard into a short market brief:

- 20D tactical rotation pressure
- 20D signal quality and AI internals
- 60D rotation-extension or AI-reassertion risk
- the news that explains what moved the signal

Free subscribers get the weekly dashboard read and the plain-English bottom line.
"""
    )

    st.markdown(f"**First article:** [{FIRST_ARTICLE_TITLE}]({FIRST_ARTICLE_URL})")

    st.markdown(f"[Join the free weekly note]({signup_url})")


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

        st.subheader("20D Rotation Meter")

        if (
            download_rotation_prices is None
            or build_20d_model_dataset is None
            or predict_latest_20d is None
        ):
            st.warning(f"20D model import failed: {ROTATION_20D_IMPORT_ERROR}")
        else:
            try:
                prediction_20d = get_20d_prediction_data()

                signal_20d = prediction_20d.get("signal_20d", "NO 20D DATA")
                value_probability_20d = prediction_20d.get("value_probability_20d", None)
                ai_probability_20d = prediction_20d.get("ai_probability_20d", None)
                expected_20d = prediction_20d.get("expected_relative_20d", None)
                matched_rows_20d = prediction_20d.get("matched_observations", 0)
                ai_internals_weak = prediction_20d.get("ai_internals_weak", False)

                signal_display_20d = {
                    "20D HIGH-CONVICTION VALUE ROTATION": "HIGH CONV",
                    "20D ROTATION SIGNAL QUALITY WARNING": "QUALITY WARN",
                    "20D VALUE ROTATION WATCH": "WATCH",
                    "20D VALUE ROTATION MIXED": "MIXED",
                    "20D EARLY ROTATION": "EARLY",
                    "20D AI / GROWTH DOMINANCE": "AI/GROWTH",
                    "NO 20D DATA": "NO DATA",
                }.get(signal_20d, signal_20d)

                q1, q2, q3, q4 = st.columns(4)

                with q1:
                    st.metric("20D Signal", signal_display_20d)

                with q2:
                    st.metric(
                        "Value Prob",
                        f"{value_probability_20d:.0%}" if pd.notna(value_probability_20d) else "N/A",
                    )

                with q3:
                    st.metric(
                        "AI Prob",
                        f"{ai_probability_20d:.0%}" if pd.notna(ai_probability_20d) else "N/A",
                    )

                with q4:
                    st.metric(
                        "Expected Rel",
                        f"{expected_20d:.2%}" if pd.notna(expected_20d) else "N/A",
                    )

                favored_20d = get_favored_read(
                    value_probability_20d,
                    ai_probability_20d,
                    "20D",
                )
                bg_color_20d = favored_20d["bg_color"]
                border_color_20d = favored_20d["border_color"]

                meaning_20d = get_20d_quality_meaning(signal_20d)

                st.plotly_chart(
                    plot_probability_meter(
                        favored_20d["probability"],
                        favored_20d["title"],
                        "Short-term read",
                        favored_20d["color"],
                    ),
                    use_container_width=True,
                )

                st.markdown(
                    f"""
<div class="signal-box" style="
    background-color:{bg_color_20d};
    border-left:7px solid {border_color_20d};
">
<b>20D Signal:</b> {signal_20d}<br>
<b>Meaning:</b> {meaning_20d["meaning"]}<br>
<b>How to Use:</b> {meaning_20d["use"]}<br>
<b>Score / Probability Note:</b> The value probability is the historical hit rate for similar 20D setups. In walk-forward testing, raw score >= 7 had a 53.75% value hit rate; score >= 7 with AI internals OK improved to 62.26%. Current score {score} / {max_score} maps to {f"{value_probability_20d:.0%}" if pd.notna(value_probability_20d) else "N/A"} across {matched_rows_20d:,} matched observations.<br>
<b>Matched Observations:</b> {matched_rows_20d:,}<br>
<b>AI Internals:</b> {"Weak" if ai_internals_weak else "OK"}
</div>
""",
                    unsafe_allow_html=True,
                )

            except Exception as e:
                st.warning(f"20D quality model could not load: {e}")

        st.subheader("60D Rotation Meter")
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

                favored_60d = get_favored_read(
                    value_probability_60d,
                    ai_probability_60d,
                    "60D",
                )
                bg_color_60d = favored_60d["bg_color"]
                border_color_60d = favored_60d["border_color"]

                meaning_60d = get_60d_signal_meaning(signal_60d)
                combined_meaning = get_two_clock_meaning(signal, signal_60d)

                st.plotly_chart(
                    plot_probability_meter(
                        favored_60d["probability"],
                        favored_60d["title"],
                        "Longer-term read",
                        favored_60d["color"],
                    ),
                    use_container_width=True,
                )

                st.markdown(
                    f"""
<div class="signal-box" style="
    background-color:{bg_color_60d};
    border-left:7px solid {border_color_60d};
">
<b>60D Signal:</b> {signal_60d}<br>
<b>Meaning:</b> {meaning_60d["meaning"]}<br>
<b>How to Use:</b> {meaning_60d["use"]}<br>
<b>Score / Probability Note:</b> The 60D probabilities are empirical hit rates from matched historical score buckets. In walk-forward testing, score >= 5 favored AI/growth 87.14% of the time, while score >= 7 favored AI/growth 96.25% of the time.<br>
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

        st.subheader("Predictive Model Agreement")

        if download_rotation_prices is None or build_model_agreement is None:
            st.warning(f"Continuous model import failed: {CONTINUOUS_MODEL_IMPORT_ERROR}")
        else:
            try:
                agreement = get_model_agreement_data()
                agreement_20d = agreement.get("agreement_20d", "NO MODEL")
                agreement_60d = agreement.get("agreement_60d", "NO MODEL")
                models_20d = agreement.get("models_20d", pd.DataFrame())
                models_60d = agreement.get("models_60d", pd.DataFrame())

                a1, a2 = st.columns(2)

                with a1:
                    st.metric("20D Agreement", agreement_20d)
                    st.caption(agreement_meaning(agreement_20d))
                    st.dataframe(
                        format_model_agreement_table(models_20d),
                        use_container_width=True,
                        hide_index=True,
                    )

                with a2:
                    st.metric("60D Agreement", agreement_60d)
                    st.caption(agreement_meaning(agreement_60d))
                    st.dataframe(
                        format_model_agreement_table(models_60d),
                        use_container_width=True,
                        hide_index=True,
                    )

                st.caption(
                    "This layer uses continuous features and logistic models. It is a model-agreement check, "
                    "not a replacement for the bucket backtest or the two-clock interpretation."
                )

            except Exception as e:
                st.warning(f"Predictive model agreement could not load: {e}")

        st.subheader("QQQ Direction Model")

        if download_rotation_prices is None or build_qqq_direction_agreement is None:
            st.warning(f"QQQ direction model import failed: {CONTINUOUS_MODEL_IMPORT_ERROR}")
        else:
            try:
                direction = get_qqq_direction_data()
                agreement_5d = direction.get("agreement_5d", "NO MODEL")
                agreement_20d = direction.get("agreement_20d", "NO MODEL")
                models_5d = direction.get("models_5d", pd.DataFrame())
                models_20d = direction.get("models_20d", pd.DataFrame())

                d1, d2 = st.columns(2)

                with d1:
                    st.metric("QQQ 5D Direction", agreement_5d)
                    st.caption(direction_meaning(agreement_5d))
                    st.dataframe(
                        format_direction_table(models_5d),
                        use_container_width=True,
                        hide_index=True,
                    )

                with d2:
                    st.metric("QQQ 20D Direction", agreement_20d)
                    st.caption(direction_meaning(agreement_20d))
                    st.dataframe(
                        format_direction_table(models_20d),
                        use_container_width=True,
                        hide_index=True,
                    )

                st.caption(
                    "This panel predicts QQQ up/down direction. It is separate from the leadership model, "
                    "which predicts AI/growth versus value relative performance."
                )

            except Exception as e:
                st.warning(f"QQQ direction model could not load: {e}")

        st.subheader("30D Clock Trend")

        if (
            download_rotation_prices is None
            or build_20d_model_dataset is None
            or build_60d_model_dataset is None
            or predict_recent_20d is None
            or predict_recent_60d is None
        ):
            st.warning("Clock trend model could not load because one or more predictive modules failed to import.")
        else:
            try:
                saved_history, history_path = save_current_clock_snapshot()
                clock_trend = get_clock_trend_data(lookback_days=30)

                if clock_trend.empty:
                    st.info("Not enough history to build the 30D clock trend.")
                else:
                    st.plotly_chart(plot_clock_trend(clock_trend), use_container_width=True)

                    history_note = (
                        f"Saved daily history rows: {len(saved_history):,}. "
                        f"History file: {history_path}."
                        if history_path is not None
                        else "Daily history storage is not available in this environment."
                    )
                    st.caption(
                        "The chart starts with backdated reads, then keeps a saved daily record as time progresses. "
                        "Green means the clock favors value; blue means the clock favors AI/growth. "
                        f"{history_note}"
                    )

                    display_trend = clock_trend.reset_index()
                    display_trend = display_trend.rename(columns={display_trend.columns[0]: "Date"})
                    display_trend["Date"] = display_trend["Date"].dt.strftime("%Y-%m-%d")

                    percent_cols = [
                        "20D Favors Value",
                        "20D Favors AI",
                        "20D Expected Rel",
                        "60D Favors Value",
                        "60D Favors AI",
                        "60D Expected Rel",
                    ]
                    for col in percent_cols:
                        if col in display_trend.columns:
                            display_trend[col] = display_trend[col].map(
                                lambda value: f"{value:.2%}" if pd.notna(value) else "N/A"
                            )

                    if "rotation_score" in display_trend.columns:
                        display_trend["rotation_score"] = display_trend["rotation_score"].map(
                            lambda value: f"{value:.0f}" if pd.notna(value) else "N/A"
                        )
                        display_trend = display_trend.rename(columns={"rotation_score": "Score"})

                    st.dataframe(display_trend, use_container_width=True, hide_index=True)

            except Exception as e:
                st.warning(f"30D clock trend could not load: {e}")

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
