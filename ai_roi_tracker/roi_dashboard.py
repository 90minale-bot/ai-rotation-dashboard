import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import yfinance as yf

from keyword_lists import POSITIVE_AI_TERMS, NEUTRAL_AI_TERMS, NEGATIVE_AI_ROI_TERMS


# ============================================================
# Page Setup
# ============================================================

st.set_page_config(
    page_title="AI ROI Tracker",
    page_icon="🤖",
    layout="wide",
)


# ============================================================
# Top AI Stock List
# ============================================================

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


# ============================================================
# Text Scoring Engine
# ============================================================

def scan_terms(text_lower, term_dict):
    hits = []
    score = 0

    for term, weight in term_dict.items():
        if term in text_lower:
            hits.append({"term": term, "weight": weight})
            score += weight

    return hits, score


def analyze_text(text):
    text_lower = text.lower()

    positive_hits, positive_score = scan_terms(text_lower, POSITIVE_AI_TERMS)
    neutral_hits, neutral_score = scan_terms(text_lower, NEUTRAL_AI_TERMS)
    negative_hits, negative_score = scan_terms(text_lower, NEGATIVE_AI_ROI_TERMS)

    roi_risk_score = negative_score - positive_score

    phase_scores = {
        "BUILDOUT / EXPANSION": positive_score,
        "OPTIMIZATION / ROI SCRUTINY": neutral_score,
        "SLOWDOWN / ROI DISAPPOINTMENT": negative_score,
    }

    dominant_phase = max(phase_scores, key=phase_scores.get)

    if negative_score >= 8 and negative_score > positive_score:
        signal = "HIGH AI ROI RISK"
        interpretation = (
            "AI commentary shows strong signs of ROI concern, slowing capex, "
            "capacity digestion, or weakening demand."
        )
    elif negative_score >= 4 and negative_score > positive_score:
        signal = "MODERATE AI ROI RISK"
        interpretation = (
            "There are meaningful warning signs around AI ROI, spending discipline, "
            "or demand moderation."
        )
    elif positive_score >= 6 and positive_score > negative_score:
        signal = "AI SPEND MOMENTUM POSITIVE"
        interpretation = (
            "AI demand and investment language remains constructive, with limited "
            "evidence of ROI pushback."
        )
    elif neutral_score >= 4 and neutral_score >= positive_score and neutral_score >= negative_score:
        signal = "AI OPTIMIZATION PHASE"
        interpretation = (
            "Language suggests the market may be shifting from raw AI buildout toward "
            "ROI measurement, utilization, efficiency, and production deployment."
        )
    else:
        signal = "NEUTRAL / MIXED"
        interpretation = (
            "AI commentary is balanced or not strong enough to confirm a clear phase."
        )

    return {
        "signal": signal,
        "interpretation": interpretation,
        "roi_risk_score": roi_risk_score,
        "dominant_phase": dominant_phase,
        "phase_scores": phase_scores,
        "positive_score": positive_score,
        "neutral_score": neutral_score,
        "negative_score": negative_score,
        "positive_hits": positive_hits,
        "neutral_hits": neutral_hits,
        "negative_hits": negative_hits,
    }


# ============================================================
# Earnings Data
# ============================================================

@st.cache_data(ttl=3600)
def get_earnings_dates(ai_stocks, limit=8):
    rows = []

    for stock in ai_stocks:
        ticker = stock["Ticker"]

        try:
            yf_ticker = yf.Ticker(ticker)
            earnings = yf_ticker.get_earnings_dates(limit=limit)

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

            for _, row in earnings.iterrows():
                earnings_date = pd.to_datetime(row[date_col], errors="coerce")

                if pd.isna(earnings_date):
                    continue

                if earnings_date.tzinfo is not None:
                    earnings_date = earnings_date.tz_localize(None)

                today = pd.Timestamp.today().tz_localize(None)

                quarter_type = "Upcoming" if earnings_date >= today else "Historical"

                rows.append(
                    {
                        "Ticker": ticker,
                        "Company": stock["Company"],
                        "AI Role": stock["AI Role"],
                        "Earnings Date": earnings_date.strftime("%Y-%m-%d"),
                        "Quarter Type": quarter_type,
                    }
                )

        except Exception as e:
            rows.append(
                {
                    "Ticker": ticker,
                    "Company": stock["Company"],
                    "AI Role": stock["AI Role"],
                    "Earnings Date": f"Error: {e}",
                    "Quarter Type": "Error",
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# Dashboard
# ============================================================

st.title("AI ROI Tracker")
st.caption(
    "Tracks AI investment momentum, ROI scrutiny, and earnings timing for major AI-linked stocks."
)

st.markdown("---")


# ============================================================
# Top 10 AI Stocks
# ============================================================

st.header("Top 10 Major AI Stocks")

ai_stock_df = pd.DataFrame(AI_STOCKS)

st.dataframe(ai_stock_df, use_container_width=True)


# ============================================================
# Earnings Calendar
# ============================================================

st.header("Quarterly Earnings Release Dates")

earnings_df = get_earnings_dates(AI_STOCKS, limit=8)

if earnings_df.empty:
    st.warning("No earnings data available.")
else:
    st.dataframe(earnings_df, use_container_width=True)

    upcoming_df = earnings_df[earnings_df["Quarter Type"] == "Upcoming"]

    if not upcoming_df.empty:
        st.subheader("Upcoming AI Earnings")
        upcoming_df = upcoming_df.sort_values("Earnings Date")
        st.dataframe(upcoming_df, use_container_width=True)

st.markdown("---")


# ============================================================
# AI Commentary Scanner
# ============================================================

st.header("AI Earnings Commentary Scanner")

sample_text = st.text_area(
    "Paste earnings call text, management commentary, or AI-related news text here:",
    height=250,
)

if st.button("Analyze AI ROI Commentary"):
    if not sample_text.strip():
        st.warning("Please paste text before analyzing.")
    else:
        result = analyze_text(sample_text)

        st.subheader("AI ROI Tracker Result")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Signal", result["signal"])

        with col2:
            st.metric("Dominant Phase", result["dominant_phase"])

        with col3:
            st.metric("ROI Risk Score", result["roi_risk_score"])

        with col4:
            st.metric("Slowdown Score", result["negative_score"])

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

        st.subheader("Positive AI Terms Found")
        st.dataframe(pd.DataFrame(result["positive_hits"]), use_container_width=True)

        st.subheader("Neutral / Optimization Terms Found")
        st.dataframe(pd.DataFrame(result["neutral_hits"]), use_container_width=True)

        st.subheader("Negative AI ROI Risk Terms Found")
        st.dataframe(pd.DataFrame(result["negative_hits"]), use_container_width=True)


st.markdown("---")
st.caption("For research and education only. Not financial advice.")
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