# allocation_dashboard.py
# Portfolio Allocation Dashboard (No LTI)

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="AI vs Value Allocation Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 AI vs Value Allocation Dashboard")

st.markdown(
    "This dashboard converts your AI, value, and ROI signals into a recommended portfolio allocation."
)

# ------------------------------------------------------------
# 1. Portfolio Value
# ------------------------------------------------------------

st.header("1. Portfolio Value")

portfolio_value = st.number_input(
    "Current Portfolio Value",
    min_value=0.0,
    value=2000000.0,
    step=10000.0,
    format="%.2f",
)

st.metric("Total Portfolio", f"${portfolio_value:,.2f}")

# ------------------------------------------------------------
# 2. Signal Inputs
# ------------------------------------------------------------

st.header("2. Signal Inputs")

s1, s2, s3 = st.columns(3)

with s1:
    ai_momentum = st.slider("AI Momentum", -1.0, 1.0, 0.40, 0.05)

with s2:
    value_momentum = st.slider("Value Momentum", -1.0, 1.0, 0.10, 0.05)

with s3:
    ai_roi_score = st.slider("AI ROI Signal", -1.0, 1.0, 0.20, 0.05)

# ------------------------------------------------------------
# 3. Allocation Engine
# ------------------------------------------------------------

st.header("3. Allocation Engine")

allocation_score = (
    0.50 * ai_momentum
    + 0.30 * value_momentum
    + 0.20 * ai_roi_score
)

if allocation_score > 0.50:
    ai_alloc, value_alloc, cash_alloc = 0.80, 0.15, 0.05
    regime = "Strong AI"
elif allocation_score > 0.20:
    ai_alloc, value_alloc, cash_alloc = 0.65, 0.25, 0.10
    regime = "Moderate AI"
elif allocation_score >= -0.20:
    ai_alloc, value_alloc, cash_alloc = 0.50, 0.35, 0.15
    regime = "Balanced"
elif allocation_score >= -0.50:
    ai_alloc, value_alloc, cash_alloc = 0.35, 0.45, 0.20
    regime = "Value Rotation"
else:
    ai_alloc, value_alloc, cash_alloc = 0.20, 0.50, 0.30
    regime = "Risk-Off"

c1, c2, c3 = st.columns(3)

c1.metric("Allocation Score", f"{allocation_score:.2f}")
c2.metric("Regime", regime)
c3.metric("AI Allocation", f"{ai_alloc:.0%}")

# ------------------------------------------------------------
# 4. Target Allocation
# ------------------------------------------------------------

st.header("4. Target Allocation")

allocation_df = pd.DataFrame({
    "Bucket": ["AI / Growth", "Value", "Cash"],
    "Target %": [ai_alloc, value_alloc, cash_alloc],
    "Target $": [
        portfolio_value * ai_alloc,
        portfolio_value * value_alloc,
        portfolio_value * cash_alloc,
    ],
})

st.dataframe(
    allocation_df.style.format({
        "Target %": "{:.0%}",
        "Target $": "${:,.0f}",
    }),
    use_container_width=True,
)

st.bar_chart(allocation_df.set_index("Bucket")["Target %"])

# ------------------------------------------------------------
# 5. Suggested Holdings
# ------------------------------------------------------------

st.header("5. Suggested Holdings")

tab1, tab2, tab3 = st.tabs(["AI / Growth", "Value", "Cash"])

with tab1:
    st.write(["FBGRX", "AMZN", "PLTR", "QQQ", "NVDA", "MSFT"])

with tab2:
    st.write(["VTV", "XLI", "XLF", "XLE", "NOC"])

with tab3:
    st.write(["Money Market", "Short-term bonds", "Treasury bills"])

# ------------------------------------------------------------
# 6. Rebalance Rules
# ------------------------------------------------------------

st.header("6. Rebalance Rules")

rebalance_text = f"""
Current Regime: {regime}
Allocation Score: {allocation_score:.2f}

Rebalance when:
- Allocation score changes regime
- Allocation drifts greater than 10%
- AI ROI turns negative
- Value momentum overtakes AI
"""

st.code(rebalance_text, language="text")