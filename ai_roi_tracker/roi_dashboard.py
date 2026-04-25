import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "ai_roi_tracker"))

from roi_tracker import analyze_text

st.set_page_config(page_title="AI ROI Tracker", layout="wide")

HISTORY_FILE = ROOT_DIR / "ai_roi_tracker" / "roi_history.csv"

st.title("AI ROI Tracker")
st.caption("AI Momentum vs ROI Pressure (Positive = Strong AI, Rising Pressure = Risk)")

sample_text = """Management noted strong AI demand but said customers are increasingly focused on AI ROI and optimization of AI spend."""

company = st.text_input("Company / Source", value="Manual Entry")

text = st.text_area(
    "Paste AI commentary here",
    value=sample_text,
    height=250,
)


def save_result(company, result):
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company": company,
        "signal": result["signal"],
        "dominant_phase": result["dominant_phase"],
        "roi_risk_score": result["roi_risk_score"],
        "buildout_score": result["positive_score"],
        "optimization_score": result["neutral_score"],
        "slowdown_score": result["negative_score"],
    }

    new_df = pd.DataFrame([row])

    if HISTORY_FILE.exists():
        old_df = pd.read_csv(HISTORY_FILE)
        out_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        out_df = new_df

    out_df.to_csv(HISTORY_FILE, index=False)


if st.button("Analyze and Save"):
    result = analyze_text(text)
    save_result(company, result)

    ai_momentum = result["positive_score"] - result["negative_score"]
    roi_pressure = result["neutral_score"] + result["negative_score"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signal", result["signal"])
    col2.metric("AI Momentum", ai_momentum)
    col3.metric("ROI Pressure", roi_pressure)
    col4.metric("Dominant Phase", result["dominant_phase"])

    st.info(result["interpretation"])


st.divider()
st.header("AI Cycle Trend Chart")

if HISTORY_FILE.exists():
    hist = pd.read_csv(HISTORY_FILE)
    hist["timestamp"] = pd.to_datetime(hist["timestamp"])
    hist = hist.sort_values("timestamp")

    company_filter = st.selectbox(
        "Filter by company/source",
        ["All"] + sorted(hist["company"].dropna().unique().tolist()),
    )

    if company_filter != "All":
        chart_df = hist[hist["company"] == company_filter].copy()
    else:
        chart_df = hist.copy()

    if chart_df.empty:
        st.info("No saved history for this company/source yet.")
    else:
        # NEW metrics
        chart_df["AI Momentum"] = chart_df["buildout_score"] - chart_df["slowdown_score"]
        chart_df["ROI Pressure"] = chart_df["optimization_score"] + chart_df["slowdown_score"]
        chart_df["Optimization Score"] = chart_df["optimization_score"]

        # Dynamic scaling
        max_val = max(
            chart_df["AI Momentum"].abs().max(),
            chart_df["ROI Pressure"].abs().max(),
            chart_df["Optimization Score"].abs().max(),
        )

        y_range = max_val * 1.3 if max_val > 0 else 10

        fig = go.Figure()

        # Background zones
        fig.add_hrect(y0=0, y1=y_range, fillcolor="green", opacity=0.05, line_width=0)
        fig.add_hrect(y0=-y_range, y1=0, fillcolor="red", opacity=0.05, line_width=0)

        # AI Momentum (main signal)
        fig.add_trace(
            go.Scatter(
                x=chart_df["timestamp"],
                y=chart_df["AI Momentum"],
                mode="lines+markers",
                name="AI Momentum",
                line=dict(width=3),
            )
        )

        # ROI Pressure (cycle maturity)
        fig.add_trace(
            go.Scatter(
                x=chart_df["timestamp"],
                y=chart_df["ROI Pressure"],
                mode="lines+markers",
                name="ROI Pressure",
                line=dict(dash="dot"),
            )
        )

        # Optimization trend
        fig.add_trace(
            go.Scatter(
                x=chart_df["timestamp"],
                y=chart_df["Optimization Score"],
                mode="lines+markers",
                name="Optimization",
                line=dict(dash="dash"),
            )
        )

        # Zero line
        fig.add_trace(
            go.Scatter(
                x=chart_df["timestamp"],
                y=[0] * len(chart_df),
                mode="lines",
                name="Neutral",
                line=dict(dash="dash"),
            )
        )

        fig.update_layout(
            title="AI Cycle: Momentum vs ROI Pressure",
            xaxis_title="Date / Time",
            yaxis_title="Score",
            yaxis=dict(range=[-y_range, y_range]),
            template="plotly_dark",
        )

        st.plotly_chart(fig, width="stretch")

        # Regime classification
        latest = chart_df.iloc[-1]

        if latest["AI Momentum"] > 0 and latest["ROI Pressure"] < 10:
            regime = "EARLY / STRONG AI"
        elif latest["AI Momentum"] > 0 and latest["ROI Pressure"] >= 10:
            regime = "MID-CYCLE (OPTIMIZATION)"
        elif latest["AI Momentum"] < 0 and latest["ROI Pressure"] >= 10:
            regime = "LATE-CYCLE / RISK"
        else:
            regime = "NEUTRAL"

        st.metric("AI Cycle Regime", regime)

        st.caption(
            "AI Momentum = Buildout - Slowdown. "
            "ROI Pressure = Optimization + Slowdown. "
            "Rising pressure with falling momentum = risk."
        )

        with st.expander("View saved ROI history"):
            display_df = chart_df.copy()
            st.dataframe(display_df, width="stretch")

else:
    st.info("No saved AI ROI history yet. Click Analyze and Save at least once.")