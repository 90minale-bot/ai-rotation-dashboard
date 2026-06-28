import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


ROOT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT_DIR / "ai_roi_tracker"
if str(PACKAGE_DIR) not in sys.path:
    sys.path.append(str(PACKAGE_DIR))

from roi_tracker import analyze_text


HISTORY_FILE = PACKAGE_DIR / "roi_history.csv"

AI_STOCKS = [
    {"Ticker": "NVDA", "Company": "NVIDIA", "AI Role": "AI GPUs / Data Center"},
    {"Ticker": "MSFT", "Company": "Microsoft", "AI Role": "Azure AI / Copilot"},
    {"Ticker": "GOOGL", "Company": "Alphabet", "AI Role": "Gemini / Google Cloud"},
    {"Ticker": "AMZN", "Company": "Amazon", "AI Role": "AWS AI / Cloud"},
    {"Ticker": "META", "Company": "Meta Platforms", "AI Role": "Llama / AI Ads"},
    {"Ticker": "AVGO", "Company": "Broadcom", "AI Role": "AI Networking / Custom Silicon"},
    {"Ticker": "AMD", "Company": "Advanced Micro Devices", "AI Role": "AI GPUs"},
    {"Ticker": "ORCL", "Company": "Oracle", "AI Role": "AI Cloud Infrastructure"},
    {"Ticker": "PLTR", "Company": "Palantir", "AI Role": "Enterprise AI / AIP"},
    {"Ticker": "TSM", "Company": "Taiwan Semiconductor", "AI Role": "AI Chip Manufacturing"},
]

SAMPLE_TEXT = (
    "Management noted strong AI demand but said customers are increasingly "
    "focused on AI ROI and optimization of AI spend."
)


st.set_page_config(
    page_title="AI ROI Tracker",
    page_icon="AI",
    layout="wide",
)


@st.cache_data(ttl=3600)
def get_earnings_dates(ai_stocks: list[dict], limit: int = 8) -> pd.DataFrame:
    rows = []

    for stock in ai_stocks:
        ticker = stock["Ticker"]

        try:
            earnings = yf.Ticker(ticker).get_earnings_dates(limit=limit)
        except Exception as exc:
            rows.append(
                {
                    "Ticker": ticker,
                    "Company": stock["Company"],
                    "AI Role": stock["AI Role"],
                    "Earnings Date": f"Error: {exc}",
                    "Quarter Type": "Error",
                }
            )
            continue

        if earnings is None or earnings.empty:
            rows.append(
                {
                    "Ticker": ticker,
                    "Company": stock["Company"],
                    "AI Role": stock["AI Role"],
                    "Earnings Date": "Not available",
                    "Quarter Type": "N/A",
                }
            )
            continue

        earnings = earnings.reset_index()
        date_col = earnings.columns[0]
        today = pd.Timestamp.today().tz_localize(None)

        for _, row in earnings.iterrows():
            earnings_date = pd.to_datetime(row[date_col], errors="coerce")

            if pd.isna(earnings_date):
                continue

            if earnings_date.tzinfo is not None:
                earnings_date = earnings_date.tz_localize(None)

            rows.append(
                {
                    "Ticker": ticker,
                    "Company": stock["Company"],
                    "AI Role": stock["AI Role"],
                    "Earnings Date": earnings_date.strftime("%Y-%m-%d"),
                    "Quarter Type": "Upcoming"
                    if earnings_date >= today
                    else "Historical",
                }
            )

    return pd.DataFrame(rows)


def save_result(company: str, result: dict) -> None:
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company": company.strip() or "Manual Entry",
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


def add_cycle_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["AI Momentum"] = df["buildout_score"] - df["slowdown_score"]
    df["ROI Pressure"] = df["optimization_score"] + df["slowdown_score"]
    df["Optimization Score"] = df["optimization_score"]
    return df


def render_analysis_result(result: dict) -> None:
    ai_momentum = result["positive_score"] - result["negative_score"]
    roi_pressure = result["neutral_score"] + result["negative_score"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signal", result["signal"])
    col2.metric("AI Momentum", ai_momentum)
    col3.metric("ROI Pressure", roi_pressure)
    col4.metric("Dominant Phase", result["dominant_phase"])

    st.info(result["interpretation"])

    score_df = pd.DataFrame(
        [
            {"Category": "Buildout / Expansion", "Score": result["positive_score"]},
            {"Category": "Optimization / ROI Scrutiny", "Score": result["neutral_score"]},
            {"Category": "Slowdown / ROI Disappointment", "Score": result["negative_score"]},
        ]
    )

    st.subheader("Phase Scores")
    st.dataframe(score_df, use_container_width=True)

    tab1, tab2, tab3 = st.tabs(
        ["Positive AI Terms", "Optimization Terms", "Negative ROI Terms"]
    )

    with tab1:
        st.dataframe(pd.DataFrame(result["positive_hits"]), use_container_width=True)
    with tab2:
        st.dataframe(pd.DataFrame(result["neutral_hits"]), use_container_width=True)
    with tab3:
        st.dataframe(pd.DataFrame(result["negative_hits"]), use_container_width=True)


def render_cycle_chart(history: pd.DataFrame) -> None:
    history = history.copy()
    history["timestamp"] = pd.to_datetime(history["timestamp"], errors="coerce")
    history = history.dropna(subset=["timestamp"]).sort_values("timestamp")

    company_filter = st.selectbox(
        "Filter by company/source",
        ["All"] + sorted(history["company"].dropna().unique().tolist()),
    )

    if company_filter != "All":
        chart_df = history[history["company"] == company_filter].copy()
    else:
        chart_df = history.copy()

    if chart_df.empty:
        st.info("No saved history for this company/source yet.")
        return

    chart_df = add_cycle_metrics(chart_df)

    max_val = max(
        chart_df["AI Momentum"].abs().max(),
        chart_df["ROI Pressure"].abs().max(),
        chart_df["Optimization Score"].abs().max(),
    )
    y_range = max_val * 1.3 if max_val > 0 else 10

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=y_range, fillcolor="green", opacity=0.05, line_width=0)
    fig.add_hrect(y0=-y_range, y1=0, fillcolor="red", opacity=0.05, line_width=0)

    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["AI Momentum"],
            mode="lines+markers",
            name="AI Momentum",
            line=dict(width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ROI Pressure"],
            mode="lines+markers",
            name="ROI Pressure",
            line=dict(dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["Optimization Score"],
            mode="lines+markers",
            name="Optimization",
            line=dict(dash="dash"),
        )
    )
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

    st.plotly_chart(fig, use_container_width=True)

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
        "AI Momentum = Buildout - Slowdown. ROI Pressure = Optimization + Slowdown. "
        "Rising pressure with falling momentum = risk."
    )

    with st.expander("View saved ROI history"):
        st.dataframe(chart_df, use_container_width=True)


st.title("AI ROI Tracker")
st.caption(
    "Tracks AI investment momentum, ROI scrutiny, and earnings timing for major AI-linked stocks."
)

st.header("Top 10 Major AI Stocks")
st.dataframe(pd.DataFrame(AI_STOCKS), use_container_width=True)

st.header("Quarterly Earnings Release Dates")
earnings_df = get_earnings_dates(AI_STOCKS, limit=8)

if earnings_df.empty:
    st.warning("No earnings data available.")
else:
    st.dataframe(earnings_df, use_container_width=True)

    upcoming_df = earnings_df[earnings_df["Quarter Type"] == "Upcoming"]
    if not upcoming_df.empty:
        st.subheader("Upcoming AI Earnings")
        st.dataframe(upcoming_df.sort_values("Earnings Date"), use_container_width=True)

st.divider()
st.header("AI Earnings Commentary Scanner")

company = st.text_input("Company / Source", value="Manual Entry")
text = st.text_area(
    "Paste earnings call text, management commentary, or AI-related news text here:",
    value=SAMPLE_TEXT,
    height=250,
)

analyze_only, analyze_and_save = st.columns(2)

with analyze_only:
    run_analysis = st.button("Analyze")
with analyze_and_save:
    run_save = st.button("Analyze and Save")

if run_analysis or run_save:
    if not text.strip():
        st.warning("Please paste text before analyzing.")
    else:
        analysis = analyze_text(text)
        if run_save:
            save_result(company, analysis)
            st.success("Saved analysis to ROI history.")
        render_analysis_result(analysis)

st.divider()
st.header("AI Cycle Trend Chart")

if HISTORY_FILE.exists():
    history_df = pd.read_csv(HISTORY_FILE)
    if history_df.empty:
        st.info("No saved AI ROI history yet. Click Analyze and Save at least once.")
    else:
        render_cycle_chart(history_df)
else:
    st.info("No saved AI ROI history yet. Click Analyze and Save at least once.")

st.divider()
st.caption("For research and education only. Not financial advice.")
