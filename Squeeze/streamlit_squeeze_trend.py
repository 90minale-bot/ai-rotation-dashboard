import os
import glob
from datetime import datetime

import pandas as pd
import yfinance as yf
from yahooquery import Ticker
import streamlit as st


st.set_page_config(
    page_title="Short Interest / Squeeze Screener",
    layout="wide"
)

DATA_DIR = "data"

DEFAULT_WATCHLIST = [
    "GME", "AMC", "BYND", "CVNA", "PLTR",
    "CAR", "HTZ", "SOUN", "NVAX", "NTLA",
    "W", "CHTR", "MRNA", "WOLF", "PLUG",
    "APLD", "RIVN", "LCID", "MARA", "RIOT",
    "AI", "UPST", "BBAI", "IONQ"
]


def safe_get(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def safe_number(value):
    try:
        if value is None:
            return None
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except Exception:
        return None


def get_short_data(symbol):
    try:
        t = Ticker(symbol)
        stats = t.key_stats.get(symbol, {})

        short_percent_float = safe_number(safe_get(stats, "shortPercentOfFloat"))
        short_ratio = safe_number(safe_get(stats, "shortRatio"))
        shares_short = safe_number(safe_get(stats, "sharesShort"))
        float_shares = safe_number(safe_get(stats, "floatShares"))

        return {
            "symbol": symbol,
            "short_float_pct": round(short_percent_float * 100, 2) if short_percent_float is not None else None,
            "days_to_cover": round(short_ratio, 2) if short_ratio is not None else None,
            "shares_short": int(shares_short) if shares_short is not None else None,
            "float_shares": int(float_shares) if float_shares is not None else None,
        }

    except Exception:
        return {
            "symbol": symbol,
            "short_float_pct": None,
            "days_to_cover": None,
            "shares_short": None,
            "float_shares": None,
        }


def get_price_volume_data(symbol):
    try:
        data = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
            group_by="column"
        )

        if data.empty or len(data) < 25:
            return {
                "last_price": None,
                "volume_ratio": None,
                "ret_5d_pct": None,
                "ret_20d_pct": None,
            }

        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"][symbol]
            volume = data["Volume"][symbol]
        else:
            close = data["Close"]
            volume = data["Volume"]

        close = close.dropna()
        volume = volume.dropna()

        last_price = safe_number(close.iloc[-1])
        avg_vol_20 = safe_number(volume.tail(20).mean())
        last_vol = safe_number(volume.iloc[-1])

        ret_5d = safe_number(((close.iloc[-1] / close.iloc[-6]) - 1) * 100) if len(close) > 6 else None
        ret_20d = safe_number(((close.iloc[-1] / close.iloc[-21]) - 1) * 100) if len(close) > 21 else None

        return {
            "last_price": round(last_price, 2) if last_price is not None else None,
            "volume_ratio": round(last_vol / avg_vol_20, 2) if last_vol is not None and avg_vol_20 not in [None, 0] else None,
            "ret_5d_pct": round(ret_5d, 2) if ret_5d is not None else None,
            "ret_20d_pct": round(ret_20d, 2) if ret_20d is not None else None,
        }

    except Exception:
        return {
            "last_price": None,
            "volume_ratio": None,
            "ret_5d_pct": None,
            "ret_20d_pct": None,
        }


def score_stock(row):
    score = 0

    if row.get("short_float_pct") is not None:
        score += min(row["short_float_pct"], 60) * 1.5

    if row.get("days_to_cover") is not None:
        score += min(row["days_to_cover"], 10) * 6

    if row.get("volume_ratio") is not None:
        score += min(row["volume_ratio"], 5) * 8

    if row.get("ret_5d_pct") is not None and row["ret_5d_pct"] > 0:
        score += min(row["ret_5d_pct"], 40)

    if row.get("ret_20d_pct") is not None and row["ret_20d_pct"] > 0:
        score += min(row["ret_20d_pct"], 60) * 0.5

    return round(score, 1)


def classify(row):
    short_float = row.get("short_float_pct") or 0
    days_to_cover = row.get("days_to_cover") or 0
    volume_ratio = row.get("volume_ratio") or 0
    ret_5d = row.get("ret_5d_pct") or 0

    if short_float >= 30 and days_to_cover >= 5 and volume_ratio >= 2 and ret_5d > 5:
        return "HIGH SQUEEZE SETUP"
    elif short_float >= 20 and days_to_cover >= 3 and volume_ratio >= 1.5:
        return "WATCHLIST"
    elif short_float >= 20:
        return "HIGH SHORT INTEREST"
    else:
        return "LOW / NORMAL"


@st.cache_data(ttl=900)
def run_screen(watchlist):
    today = datetime.now().strftime("%Y-%m-%d")
    rows = []

    for symbol in watchlist:
        symbol = symbol.strip().upper()
        if not symbol:
            continue

        short_data = get_short_data(symbol)
        market_data = get_price_volume_data(symbol)

        row = {**short_data, **market_data}
        row["run_date"] = today
        row["squeeze_score"] = score_stock(row)
        row["signal"] = classify(row)

        rows.append(row)

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(
            by=["squeeze_score", "short_float_pct", "volume_ratio"],
            ascending=False,
            na_position="last"
        )

    os.makedirs(DATA_DIR, exist_ok=True)
    output_file = os.path.join(DATA_DIR, f"short_squeeze_screen_{today}.csv")
    df.to_csv(output_file, index=False)

    return df


def load_score_history():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "short_squeeze_screen_*.csv")))

    if not files:
        return pd.DataFrame()

    latest_files = files[-3:]

    frames = []
    for file in latest_files:
        try:
            df = pd.read_csv(file)

            if "run_date" not in df.columns:
                date_part = os.path.basename(file).replace("short_squeeze_screen_", "").replace(".csv", "")
                df["run_date"] = date_part

            frames.append(df)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    history = pd.concat(frames, ignore_index=True)

    history["run_date"] = pd.to_datetime(history["run_date"], errors="coerce")
    history = history.dropna(subset=["run_date"])

    return history


def add_three_day_trend(current_df, history_df):
    if current_df.empty or history_df.empty:
        current_df["score_3day_change"] = None
        current_df["score_trend"] = "NO HISTORY"
        return current_df

    trend_rows = []

    for _, row in current_df.iterrows():
        symbol = row["symbol"]

        hist = history_df[history_df["symbol"] == symbol].copy()
        hist = hist.sort_values("run_date")

        if len(hist) < 2:
            change = None
            trend = "NO HISTORY"
        else:
            first_score = hist["squeeze_score"].iloc[0]
            last_score = hist["squeeze_score"].iloc[-1]
            change = round(last_score - first_score, 1)

            if change >= 10:
                trend = "RISING FAST"
            elif change > 0:
                trend = "RISING"
            elif change <= -10:
                trend = "FALLING FAST"
            elif change < 0:
                trend = "FALLING"
            else:
                trend = "FLAT"

        new_row = row.to_dict()
        new_row["score_3day_change"] = change
        new_row["score_trend"] = trend
        trend_rows.append(new_row)

    return pd.DataFrame(trend_rows)


st.title("Short Interest / Squeeze Screener")

st.write(
    """
    This dashboard ranks stocks using short interest, days to cover, volume spike,
    and recent price momentum. It also tracks the squeeze score trend over the
    latest three saved runs.
    """
)

with st.sidebar:
    st.header("Settings")

    ticker_text = st.text_area(
        "Watchlist tickers",
        value=", ".join(DEFAULT_WATCHLIST),
        height=175
    )

    run_button = st.button("Run Screener")

    st.markdown("---")
    st.write("Signal guide:")
    st.write("**HIGH SQUEEZE SETUP** = high short interest + covering risk + momentum")
    st.write("**WATCHLIST** = high short interest with improving activity")
    st.write("**HIGH SHORT INTEREST** = heavily shorted, but no strong squeeze trigger yet")

watchlist = [x.strip().upper() for x in ticker_text.replace("\n", ",").split(",") if x.strip()]

if run_button:
    with st.spinner("Pulling short interest and price data..."):
        current_df = run_screen(watchlist)
else:
    history_df = load_score_history()
    if not history_df.empty:
        latest_date = history_df["run_date"].max()
        current_df = history_df[history_df["run_date"] == latest_date].copy()
        current_df["run_date"] = current_df["run_date"].dt.strftime("%Y-%m-%d")
    else:
        current_df = pd.DataFrame()

history_df = load_score_history()

if current_df.empty:
    st.warning("No results yet. Click **Run Screener** to create your first daily file.")
else:
    current_df = add_three_day_trend(current_df, history_df)

    top = current_df.iloc[0]

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Top Ticker", top["symbol"])
    col2.metric("Top Score", top["squeeze_score"])
    col3.metric("3-Day Change", top.get("score_3day_change"))
    col4.metric("Short Float %", top.get("short_float_pct"))
    col5.metric("Volume Ratio", top.get("volume_ratio"))

    st.subheader("Ranked Results with 3-Day Trend")

    display_cols = [
        "symbol",
        "squeeze_score",
        "score_3day_change",
        "score_trend",
        "signal",
        "short_float_pct",
        "days_to_cover",
        "volume_ratio",
        "ret_5d_pct",
        "ret_20d_pct",
        "last_price",
        "shares_short",
        "float_shares",
        "run_date",
    ]

    existing_cols = [c for c in display_cols if c in current_df.columns]

    st.dataframe(
        current_df[existing_cols],
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Top Squeeze Candidates")

    squeeze_df = current_df[current_df["signal"].isin(["HIGH SQUEEZE SETUP", "WATCHLIST"])]

    if squeeze_df.empty:
        st.info("No high-quality squeeze setups found in this watchlist right now.")
    else:
        st.dataframe(
            squeeze_df[existing_cols],
            use_container_width=True,
            hide_index=True
        )

    st.subheader("Current Score Chart")

    chart_df = current_df[["symbol", "squeeze_score"]].dropna().set_index("symbol")
    st.bar_chart(chart_df)

    st.subheader("3-Day Score Trend")

    if history_df.empty or history_df["run_date"].nunique() < 2:
        st.info("Run the screener on multiple days to build a visible trend.")
    else:
        trend_df = history_df[history_df["symbol"].isin(current_df["symbol"])].copy()
        trend_df = trend_df.sort_values("run_date")
        trend_pivot = trend_df.pivot_table(
            index="run_date",
            columns="symbol",
            values="squeeze_score",
            aggfunc="last"
        )

        st.line_chart(trend_pivot)

    today = datetime.now().strftime("%Y-%m-%d")
    csv = current_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Current CSV",
        data=csv,
        file_name=f"short_squeeze_screen_{today}.csv",
        mime="text/csv"
    )

st.markdown("---")

st.caption(
    "Note: exchange-reported short interest is not truly daily. "
    "This combines the latest available short interest with daily price and volume movement. "
    "The 3-day trend uses your locally saved screener runs."
)