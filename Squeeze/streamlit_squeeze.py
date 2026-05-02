import os
import glob
import pandas as pd
import streamlit as st

from squeeze import (
    DEFAULT_WATCHLIST,
    get_all_us_tickers,
    run_screen,
)


DEFAULT_RESULTS_FILE = "squeeze_results.csv"
SKIPPED_FILE = "squeeze_skipped.csv"


st.set_page_config(
    page_title="Live Short Squeeze Dashboard",
    page_icon="📈",
    layout="wide"
)


st.title("📈 Live Short Squeeze Dashboard")

st.markdown("""
Run the short squeeze scanner directly from this web app.

No `.bat` file required.
""")


def safe_read_csv(path):
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

    return pd.DataFrame()


def clean_numeric_columns(df):
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

    if "symbol" in df.columns:
        df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    return df


# -----------------------------
# Sidebar scanner controls
# -----------------------------
st.sidebar.header("Live Scanner")

scan_mode = st.sidebar.radio(
    "Scan Mode",
    [
        "Default Watchlist",
        "Custom Tickers",
        "All US Stocks - limited",
    ]
)

custom_tickers_text = ""

if scan_mode == "Custom Tickers":
    custom_tickers_text = st.sidebar.text_area(
        "Enter tickers separated by commas",
        value="HTZ, SOUN, BYND, GME, AMC, MARA"
    )

max_symbols = st.sidebar.number_input(
    "Max symbols to scan",
    min_value=1,
    max_value=500,
    value=50,
    step=10
)

st.sidebar.caption("For Streamlit Cloud, keep this under 100 for faster loading.")

run_live_scan = st.sidebar.button("🚀 Run Live Scan")


# -----------------------------
# Run scanner
# -----------------------------
if run_live_scan:
    if scan_mode == "Default Watchlist":
        symbols = DEFAULT_WATCHLIST

    elif scan_mode == "Custom Tickers":
        symbols = [
            t.strip().upper()
            for t in custom_tickers_text.replace("\n", ",").split(",")
            if t.strip()
        ]

    else:
        with st.spinner("Loading US ticker universe..."):
            symbols = get_all_us_tickers()

    symbols = symbols[:max_symbols]

    st.info(f"Running live scan on {len(symbols)} symbols...")

    with st.spinner("Scanning stocks. This may take a minute..."):
        df = run_screen(symbols, max_symbols=None)

    if df is None or df.empty:
        st.warning("Live scan completed, but no results were returned.")
        df = pd.DataFrame()
    else:
        df = clean_numeric_columns(df)
        st.success("Live scan complete.")

else:
    df = safe_read_csv(DEFAULT_RESULTS_FILE)

    if not df.empty:
        df = clean_numeric_columns(df)
        st.info(f"Loaded existing `{DEFAULT_RESULTS_FILE}`. Use **Run Live Scan** to refresh.")
    else:
        st.warning("No existing results found. Use **Run Live Scan** in the sidebar.")


if df.empty:
    st.stop()


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
    st.metric("Rows Scanned", len(df))

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
# Top tables
# -----------------------------
st.subheader("🏆 Top 10 by Original Squeeze Score")

if filtered.empty:
    st.warning("No rows match the current filters.")
else:
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


st.subheader("🎯 Top 10 by Pro Squeeze Score")

if not filtered.empty and "pro_squeeze_score" in filtered.columns:
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


# -----------------------------
# Ticker debug
# -----------------------------
st.divider()

st.subheader("🔍 Ticker Lookup")

ticker_lookup = st.text_input("Enter ticker to inspect", value="HTZ")

if ticker_lookup:
    ticker_lookup = ticker_lookup.upper().strip()

    if "symbol" in df.columns:
        ticker_df = df[df["symbol"] == ticker_lookup]

        if ticker_df.empty:
            st.warning(f"{ticker_lookup} was not found in the current scan.")
        else:
            st.success(f"{ticker_lookup} found.")
            st.dataframe(ticker_df, use_container_width=True)


# -----------------------------
# Full table
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

sort_options = [
    c for c in [
        "pro_squeeze_score",
        "squeeze_score",
        "volume_ratio",
        "short_float_pct",
        "days_to_cover",
        "ret_5d_pct",
    ]
    if c in filtered.columns
]

sort_choice = st.selectbox(
    "Sort table by",
    sort_options,
    index=0 if sort_options else None
)

table_df = filtered.copy()

if sort_choice:
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
    skipped_df = safe_read_csv(SKIPPED_FILE)

    if skipped_df.empty:
        st.success("No skipped tickers.")
    else:
        st.dataframe(skipped_df, use_container_width=True)


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

### Cloud Usage

For Streamlit Cloud:
- Use **Default Watchlist** or **Custom Tickers**
- Keep max symbols around 25–100
- Avoid large all-stock scans unless you are okay waiting
""")