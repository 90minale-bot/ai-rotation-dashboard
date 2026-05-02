import os
import glob
import pandas as pd
import streamlit as st


DEFAULT_RESULTS_FILE = "squeeze_results.csv"
SKIPPED_FILE = "squeeze_skipped.csv"


st.set_page_config(
    page_title="Short Squeeze Dashboard",
    page_icon="📈",
    layout="wide"
)


st.title("📈 Short Squeeze Dashboard")

st.markdown("""
Choose the CSV file to load, then use the filters on the left.  
This version includes both your original **squeeze score** and the new **pro squeeze score**.
""")


def load_csv(path):
    return pd.read_csv(path)


# -----------------------------
# CSV selector
# -----------------------------
st.sidebar.header("Data Source")

csv_files = sorted(glob.glob("*.csv"))

if not csv_files:
    st.error("No CSV files found in this folder.")
    st.info("Run your `.bat` file and choose option 1 or 2 to generate results.")
    st.stop()

if "selected_csv" not in st.session_state:
    st.session_state.selected_csv = (
        DEFAULT_RESULTS_FILE if DEFAULT_RESULTS_FILE in csv_files else csv_files[0]
    )

if st.session_state.selected_csv not in csv_files:
    st.session_state.selected_csv = csv_files[0]

selected_file = st.sidebar.selectbox(
    "Select CSV file to load",
    csv_files,
    index=csv_files.index(st.session_state.selected_csv),
    key="selected_csv_selectbox"
)

st.session_state.selected_csv = selected_file

if st.button("🔄 Refresh Data"):
    st.rerun()

selected_file = st.session_state.selected_csv

if not os.path.exists(selected_file):
    st.error(f"Could not find `{selected_file}`.")
    st.stop()

file_modified = pd.Timestamp(os.path.getmtime(selected_file), unit="s")

st.info(f"📂 Loaded CSV: `{selected_file}`")
st.info(f"🕒 Last modified: `{file_modified}`")


df = load_csv(selected_file)

if df.empty:
    st.warning("The selected CSV exists, but it is empty.")
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
    "pro_squeeze_score",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("Filters")

search = st.sidebar.text_input("Search ticker or reason", "")

ratings = sorted(df["squeeze_rating"].dropna().unique()) if "squeeze_rating" in df.columns else []
selected_ratings = st.sidebar.multiselect(
    "Squeeze Rating",
    ratings,
    default=ratings
)

pro_ratings = sorted(df["pro_squeeze_rating"].dropna().unique()) if "pro_squeeze_rating" in df.columns else []
selected_pro_ratings = st.sidebar.multiselect(
    "Pro Squeeze Rating",
    pro_ratings,
    default=pro_ratings
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

max_pro_score_value = 200
if "pro_squeeze_score" in df.columns and not df["pro_squeeze_score"].dropna().empty:
    max_pro_score_value = int(max(df["pro_squeeze_score"].max(), 1))

min_pro_score = st.sidebar.slider(
    "Minimum Pro Squeeze Score",
    min_value=0,
    max_value=max_pro_score_value,
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

if "squeeze_rating" in filtered.columns and selected_ratings:
    filtered = filtered[filtered["squeeze_rating"].isin(selected_ratings)]

if "pro_squeeze_rating" in filtered.columns and selected_pro_ratings:
    filtered = filtered[filtered["pro_squeeze_rating"].isin(selected_pro_ratings)]

if "signal" in filtered.columns and selected_signals:
    filtered = filtered[filtered["signal"].isin(selected_signals)]

if "squeeze_score" in filtered.columns:
    filtered = filtered[filtered["squeeze_score"].fillna(0) >= min_score]

if "pro_squeeze_score" in filtered.columns:
    filtered = filtered[filtered["pro_squeeze_score"].fillna(0) >= min_pro_score]

if "volume_ratio" in filtered.columns:
    filtered = filtered[filtered["volume_ratio"].fillna(0) >= min_volume_ratio]

if "short_float_pct" in filtered.columns:
    filtered = filtered[filtered["short_float_pct"].fillna(0) >= min_short_float]


# -----------------------------
# Metrics
# -----------------------------
st.divider()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Rows in CSV", len(df))

with col2:
    st.metric("Rows After Filters", len(filtered))

with col3:
    if "squeeze_score" in filtered.columns and not filtered.empty:
        st.metric("Top Score", round(filtered["squeeze_score"].max(), 1))
    else:
        st.metric("Top Score", "N/A")

with col4:
    if "pro_squeeze_score" in filtered.columns and not filtered.empty:
        st.metric("Top Pro Score", round(filtered["pro_squeeze_score"].max(), 1))
    else:
        st.metric("Top Pro Score", "N/A")

with col5:
    if "volume_ratio" in filtered.columns and not filtered.empty:
        st.metric("Top Volume Ratio", round(filtered["volume_ratio"].max(), 2))
    else:
        st.metric("Top Volume Ratio", "N/A")


# -----------------------------
# Filtered top 10
# -----------------------------
st.subheader("🏆 Filtered Top 10 by Original Squeeze Score")

if filtered.empty:
    st.warning("No rows match the current filters.")
else:
    if "squeeze_score" in filtered.columns:
        top_cols = [
            "symbol",
            "squeeze_score",
            "squeeze_rating",
            "pro_squeeze_score",
            "pro_squeeze_rating",
            "signal",
            "last_price",
            "short_float_pct",
            "days_to_cover",
            "volume_ratio",
        ]

        top_existing_cols = [c for c in top_cols if c in filtered.columns]

        st.dataframe(
            filtered.sort_values("squeeze_score", ascending=False)[top_existing_cols].head(10),
            use_container_width=True
        )


st.subheader("🎯 Filtered Top 10 by Pro Squeeze Score")

if filtered.empty:
    st.warning("No rows match the current filters.")
else:
    if "pro_squeeze_score" in filtered.columns:
        pro_top_cols = [
            "symbol",
            "pro_squeeze_score",
            "pro_squeeze_rating",
            "squeeze_score",
            "squeeze_rating",
            "signal",
            "last_price",
            "short_float_pct",
            "days_to_cover",
            "volume_ratio",
            "volume_zscore_20",
            "float_turnover_pct",
            "ret_5d_pct",
            "ret_20d_pct",
        ]

        pro_top_existing_cols = [c for c in pro_top_cols if c in filtered.columns]

        st.dataframe(
            filtered.sort_values("pro_squeeze_score", ascending=False)[pro_top_existing_cols].head(10),
            use_container_width=True
        )
    else:
        st.warning("This CSV does not have a `pro_squeeze_score` column. Re-run `squeeze.py` first.")


# -----------------------------
# Ticker debug
# -----------------------------
st.divider()

st.subheader("🔍 Ticker Debug")

ticker_lookup = st.text_input("Enter ticker to inspect", value="HTZ")

if ticker_lookup:
    ticker_lookup = ticker_lookup.upper().strip()

    if "symbol" not in df.columns:
        st.error("No `symbol` column found in CSV.")
    else:
        ticker_df = df[df["symbol"] == ticker_lookup]

        st.write(f"{ticker_lookup} in loaded CSV?", ticker_lookup in df["symbol"].values)

        if ticker_df.empty:
            st.warning(f"{ticker_lookup} was NOT found in `{selected_file}`.")

            if os.path.exists(SKIPPED_FILE) and os.path.getsize(SKIPPED_FILE) > 0:
                try:
                    skipped_df = pd.read_csv(SKIPPED_FILE)

                    if "symbol" in skipped_df.columns:
                        skipped_df["symbol"] = skipped_df["symbol"].astype(str).str.upper().str.strip()

                        skipped_match = skipped_df[skipped_df["symbol"] == ticker_lookup]

                        if not skipped_match.empty:
                            st.error(f"{ticker_lookup} was skipped during the scan.")
                            st.dataframe(skipped_match, use_container_width=True)
                        else:
                            st.info(f"{ticker_lookup} was not found in skipped file either.")
                except pd.errors.EmptyDataError:
                    st.info("Skipped ticker file is empty.")
                except Exception as e:
                    st.warning(f"Could not read skipped ticker file: {e}")
        else:
            st.success(f"{ticker_lookup} found in loaded CSV.")
            st.dataframe(ticker_df, use_container_width=True)


# -----------------------------
# Full filtered table
# -----------------------------
st.divider()

st.subheader("📊 Filtered Squeeze Results")

display_cols = [
    "symbol",
    "last_price",
    "squeeze_score",
    "squeeze_rating",
    "pro_squeeze_score",
    "pro_squeeze_rating",
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

sort_choice = st.selectbox(
    "Sort table by",
    [
        "pro_squeeze_score",
        "squeeze_score",
        "volume_ratio",
        "short_float_pct",
        "days_to_cover",
        "ret_5d_pct",
    ],
    index=0
)

if sort_choice in table_df.columns:
    table_df = table_df.sort_values(sort_choice, ascending=False)

st.dataframe(
    table_df[existing_cols],
    use_container_width=True,
    height=700
)


# -----------------------------
# Skipped tickers
# -----------------------------
st.divider()

with st.expander("⚠️ Skipped Tickers"):
    if os.path.exists(SKIPPED_FILE) and os.path.getsize(SKIPPED_FILE) > 0:
        try:
            skipped_df = pd.read_csv(SKIPPED_FILE)

            if skipped_df.empty:
                st.success("No skipped tickers.")
            else:
                st.dataframe(skipped_df, use_container_width=True)

        except pd.errors.EmptyDataError:
            st.success("No skipped tickers.")
        except Exception as e:
            st.warning(f"Could not read skipped ticker file: {e}")
    else:
        st.success("No skipped tickers.")


with st.expander("How to read this dashboard"):
    st.markdown("""
### Original vs Pro Score

**squeeze_score**  
Your broader scoring model. It is good for finding anything interesting.

**pro_squeeze_score**  
A stricter confirmation score. It rewards:
- high short float
- higher days to cover
- real volume spikes
- abnormal volume z-score
- float turnover
- positive price confirmation
- proximity to 20-day highs

### How to Use

High **squeeze_score** but low **pro_squeeze_score**  
= interesting but less confirmed.

High **squeeze_score** and high **pro_squeeze_score**  
= stronger setup.

High **pro_squeeze_score**  
= more selective setup with better confirmation.
""")