import os
import pandas as pd
import streamlit as st


RESULTS_FILE = "squeeze_results.csv"
SKIPPED_FILE = "squeeze_skipped.csv"


st.set_page_config(
    page_title="Short Squeeze Dashboard",
    page_icon="📈",
    layout="wide"
)


st.title("📈 Short Squeeze Dashboard")

st.markdown("""
This dashboard shows **everything loaded from `squeeze_results.csv`**.

If HTZ is in the CSV, this version will show it.
""")


if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


@st.cache_data
def load_csv(path):
    return pd.read_csv(path)


if not os.path.exists(RESULTS_FILE):
    st.error(f"Could not find `{RESULTS_FILE}`.")
    st.info("Run your `.bat` file and choose option 1 or 2 to generate fresh results.")
    st.stop()


df = load_csv(RESULTS_FILE)

if df.empty:
    st.warning("The results file exists, but it is empty.")
    st.stop()


if "symbol" in df.columns:
    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()


numeric_cols = [
    "last_price",
    "short_float_pct",
    "days_to_cover",
    "shares_short",
    "float_shares",
    "market_cap",
    "last_volume",
    "avg_volume_5",
    "avg_volume_20",
    "volume_ratio",
    "volume_ratio_5",
    "volume_ratio_20",
    "volume_zscore_20",
    "float_turnover_pct",
    "ret_5d_pct",
    "ret_20d_pct",
    "pct_from_20d_high",
    "pct_from_20d_low",
    "squeeze_score",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


st.sidebar.header("Filters")

search = st.sidebar.text_input("Search ticker or reason", "")

show_all = st.sidebar.checkbox("Show ALL loaded CSV rows", value=True)

ratings = sorted(df["squeeze_rating"].dropna().unique()) if "squeeze_rating" in df.columns else []
selected_ratings = st.sidebar.multiselect(
    "Squeeze Rating",
    ratings,
    default=ratings
)

signals = sorted(df["signal"].dropna().unique()) if "signal" in df.columns else []
selected_signals = st.sidebar.multiselect(
    "Signal",
    signals,
    default=signals
)

max_score_value = 200
if "squeeze_score" in df.columns and not df["squeeze_score"].dropna().empty:
    max_score_value = int(max(df["squeeze_score"].max(), 1))

min_score = st.sidebar.slider(
    "Minimum Squeeze Score",
    min_value=0,
    max_value=max_score_value,
    value=0,
    step=5
)

min_volume_ratio = st.sidebar.slider(
    "Minimum Volume Ratio",
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.1
)

min_short_float = st.sidebar.slider(
    "Minimum Short Float %",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=1.0
)


filtered = df.copy()

if search:
    search_upper = search.upper().strip()
    filtered = filtered[
        filtered.astype(str).apply(
            lambda row: row.str.upper().str.contains(search_upper, na=False).any(),
            axis=1
        )
    ]

if not show_all:
    if "squeeze_rating" in filtered.columns and selected_ratings:
        filtered = filtered[filtered["squeeze_rating"].isin(selected_ratings)]

    if "signal" in filtered.columns and selected_signals:
        filtered = filtered[filtered["signal"].isin(selected_signals)]

    if "squeeze_score" in filtered.columns:
        filtered = filtered[filtered["squeeze_score"].fillna(0) >= min_score]

    if "volume_ratio" in filtered.columns:
        filtered = filtered[filtered["volume_ratio"].fillna(0) >= min_volume_ratio]

    if "short_float_pct" in filtered.columns:
        filtered = filtered[filtered["short_float_pct"].fillna(0) >= min_short_float]


st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Rows in CSV", len(df))

with col2:
    st.metric("Rows Displayed", len(filtered))

with col3:
    if "squeeze_score" in df.columns:
        st.metric("Top Score", round(df["squeeze_score"].max(), 1))
    else:
        st.metric("Top Score", "N/A")

with col4:
    if "volume_ratio" in df.columns:
        st.metric("Top Volume Ratio", round(df["volume_ratio"].max(), 2))
    else:
        st.metric("Top Volume Ratio", "N/A")


st.divider()

st.subheader("🔍 HTZ / Ticker Debug")

ticker_lookup = st.text_input("Enter ticker to inspect", value="HTZ")

if ticker_lookup:
    ticker_lookup = ticker_lookup.upper().strip()

    if "symbol" not in df.columns:
        st.error("No `symbol` column found in CSV.")
    else:
        ticker_df = df[df["symbol"] == ticker_lookup]

        st.write(f"{ticker_lookup} in loaded CSV?", ticker_lookup in df["symbol"].values)

        if ticker_df.empty:
            st.warning(f"{ticker_lookup} was NOT found in `{RESULTS_FILE}`.")

            if os.path.exists(SKIPPED_FILE):
                skipped_df = pd.read_csv(SKIPPED_FILE)

                if "symbol" in skipped_df.columns:
                    skipped_df["symbol"] = skipped_df["symbol"].astype(str).str.upper().str.strip()

                    skipped_match = skipped_df[skipped_df["symbol"] == ticker_lookup]

                    if not skipped_match.empty:
                        st.error(f"{ticker_lookup} was skipped during the scan.")
                        st.dataframe(skipped_match, use_container_width=True)
                    else:
                        st.info(f"{ticker_lookup} was not found in skipped file either.")
        else:
            st.success(f"{ticker_lookup} found in loaded CSV.")
            st.dataframe(ticker_df, use_container_width=True)


st.divider()

st.subheader("📊 All Loaded Squeeze Results")

display_cols = [
    "symbol",
    "last_price",
    "squeeze_score",
    "squeeze_rating",
    "signal",
    "status",
    "reason",
    "short_float_pct",
    "days_to_cover",
    "volume_ratio",
    "volume_ratio_5",
    "volume_ratio_20",
    "volume_zscore_20",
    "float_turnover_pct",
    "ret_5d_pct",
    "ret_20d_pct",
    "pct_from_20d_high",
    "pct_from_20d_low",
    "last_volume",
    "avg_volume_5",
    "avg_volume_20",
    "shares_short",
    "float_shares",
    "market_cap",
    "scan_date",
]

existing_cols = [c for c in display_cols if c in filtered.columns]

table_df = filtered.copy()

if "squeeze_score" in table_df.columns:
    table_df = table_df.sort_values("squeeze_score", ascending=False)

st.dataframe(
    table_df[existing_cols],
    use_container_width=True,
    height=700
)


st.divider()

with st.expander("⚠️ Skipped Tickers"):
    if os.path.exists(SKIPPED_FILE):
        skipped_df = pd.read_csv(SKIPPED_FILE)

        if skipped_df.empty:
            st.success("No skipped tickers.")
        else:
            st.dataframe(skipped_df, use_container_width=True)
    else:
        st.info("No skipped ticker file found yet.")


with st.expander("How to read this dashboard"):
    st.markdown("""
### Important

If **Show ALL loaded CSV rows** is checked, the dashboard ignores rating, signal, score, volume, and short-float filters.

That means if HTZ is in `squeeze_results.csv`, it should appear.

### Key Fields

**squeeze_score**  
Overall weighted score based on short interest, days to cover, volume spike, float turnover, and price momentum.

**squeeze_rating**  
Simple label based on score.

**volume_ratio**  
The larger of:
- `volume_ratio_5`
- `volume_ratio_20`

**reason**  
Plain-English explanation of why the ticker ranked the way it did.

**Skipped Tickers**  
Shows tickers that failed because of missing or insufficient price/volume data.
""")