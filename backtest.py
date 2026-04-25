import pandas as pd
import numpy as np
from yahooquery import Ticker
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import matplotlib.pyplot as plt

# ==============================
# SETTINGS
# ==============================
SYMBOL = input("Enter stock symbol (default NOC): ").strip().upper() or "NOC"
SECTOR = "ITA"
START_DATE = "2025-01-01"
PERIOD = "5y"  # use more history for a 2025 backtest

# Strategy: trade only strongest signals (top quartile by default)
SIGNAL_QUANTILE = 0.75  # try 0.60 / 0.75 / 0.85


def history_single(symbol: str, period: str) -> pd.DataFrame:
    """
    Returns a clean dataframe for ONE symbol with columns:
      date, close, high, low, volume (if present)
    Handles yahooquery multi-index / multi-symbol output.
    """
    hist = Ticker(symbol).history(period=period)
    if hist is None or getattr(hist, "empty", True):
        raise RuntimeError(f"No data returned for {symbol}")

    # yahooquery often returns multiindex with levels: (symbol, date)
    # If so, slice to this symbol only.
    if isinstance(hist.index, pd.MultiIndex):
        # first level is typically 'symbol'
        if "symbol" in hist.index.names:
            try:
                hist = hist.xs(symbol, level="symbol", drop_level=False)
            except Exception:
                pass
            # after xs, it may still be multiindex; drop symbol level
            if isinstance(hist.index, pd.MultiIndex) and "symbol" in hist.index.names:
                hist = hist.droplevel("symbol")
        else:
            # fallback: take first level as symbol
            try:
                hist = hist.xs(symbol, level=0)
            except Exception:
                pass

    hist = hist.reset_index()

    # normalize date column name
    date_col = None
    for c in ("date", "Date", "datetime"):
        if c in hist.columns:
            date_col = c
            break
    if date_col is None:
        # sometimes it's 'index' after reset_index
        if "index" in hist.columns:
            date_col = "index"
        else:
            raise RuntimeError(f"No date column found for {symbol}. Columns={list(hist.columns)}")

    hist[date_col] = pd.to_datetime(hist[date_col], utc=True, errors="coerce").dt.tz_convert(None)
    if date_col != "date":
        hist = hist.rename(columns={date_col: "date"})

    # standardize OHLCV lowercase
    rename_map = {}
    for c in hist.columns:
        lc = c.lower()
        if lc in {"open", "high", "low", "close", "volume"} and c != lc:
            rename_map[c] = lc
    if rename_map:
        hist = hist.rename(columns=rename_map)

    # keep only one symbol's rows if symbol column exists
    if "symbol" in hist.columns:
        hist = hist[hist["symbol"].astype(str).str.upper() == symbol.upper()].copy()

    if "close" not in hist.columns:
        raise RuntimeError(f"No close column for {symbol}. Columns={list(hist.columns)}")

    hist = hist.sort_values("date").dropna(subset=["date", "close"]).copy()
    return hist


def add_features(df: pd.DataFrame, close_col: str, prefix: str) -> pd.DataFrame:
    df = df.sort_values("date").copy()

    # returns
    df[f"{prefix}ret_1"] = df[close_col].pct_change()
    df[f"{prefix}ret_5"] = df[close_col].pct_change(5)
    df[f"{prefix}ret_10"] = df[close_col].pct_change(10)

    # ma20 + gap
    df[f"{prefix}ma_20"] = df[close_col].rolling(20).mean()
    df[f"{prefix}gap_ma20"] = (df[close_col] / df[f"{prefix}ma_20"]) - 1

    # vol10
    df[f"{prefix}vol_10"] = df[f"{prefix}ret_1"].rolling(10).std()

    # optional: stock-only volume/high-low (only if those columns exist)
    if prefix == "stock_":
        if "high" in df.columns and "low" in df.columns:
            df["stock_hl_range"] = (df["high"] / df["low"]) - 1
        if "volume" in df.columns:
            df["stock_vol_chg_1"] = df["volume"].pct_change()
            df["stock_vol_z_20"] = (df["volume"] - df["volume"].rolling(20).mean()) / df["volume"].rolling(20).std()

    return df


def add_relative(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rel_ret_1"] = df["stock_ret_1"] - df["ita_ret_1"]
    df["rel_ret_5"] = df["stock_ret_5"] - df["ita_ret_5"]
    df["rel_ret_10"] = df["stock_ret_10"] - df["ita_ret_10"]
    df["rel_gap_ma20"] = df["stock_gap_ma20"] - df["ita_gap_ma20"]
    df["rel_vol_10"] = df["stock_vol_10"] - df["ita_vol_10"]
    return df


# ==============================
# LOAD + PREP DATA
# ==============================
print("Loading data...")
stock = history_single(SYMBOL, PERIOD)
ita = history_single(SECTOR, PERIOD)[["date", "close"]].rename(columns={"close": "close_ita"})

df = stock.merge(ita, on="date", how="left")
df["close_ita"] = df["close_ita"].ffill()

df = add_features(df, "close", "stock_")
df = add_features(df, "close_ita", "ita_")
df = add_relative(df)

# target: next day return
df["target"] = df["close"].pct_change().shift(-1)

df = df.dropna().copy()

features = [c for c in df.columns if c.startswith(("stock_", "ita_", "rel_"))]

# start index at or after START_DATE
start_date = pd.to_datetime(START_DATE)
start_pos = df.index[df["date"] >= start_date]
if len(start_pos) == 0:
    raise RuntimeError(
        f"START_DATE {START_DATE} is after available data range. Last date: {df['date'].max()}"
    )
start_idx = start_pos[0]

print("Starting walk-forward backtest...\n")

# ==============================
# WALK-FORWARD BACKTEST
# ==============================
results = []
start_loc = df.index.get_loc(start_idx)

for i in range(start_loc, len(df) - 1):
    train = df.iloc[:i]
    test = df.iloc[i:i+1]

    X_train = train[features].to_numpy(dtype=float)
    y_train = train["target"].to_numpy(dtype=float)

    X_test = test[features].to_numpy(dtype=float)
    actual = float(test["target"].iloc[0])

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=1.0)),
    ])
    model.fit(X_train, y_train)

    pred = float(model.predict(X_test)[0])

    results.append({
        "date": test["date"].iloc[0],
        "pred": pred,
        "actual": actual,
        "correct": (np.sign(pred) == np.sign(actual)),
    })

results = pd.DataFrame(results)

print("Rows backtested:", len(results))
print("Direction accuracy:", results["correct"].mean())

# ==============================
# STRATEGY: TRADE ONLY STRONG SIGNALS
# ==============================
results["signal_strength"] = results["pred"].abs()

threshold = results["signal_strength"].quantile(SIGNAL_QUANTILE)
print(f"Signal-strength threshold ({int(SIGNAL_QUANTILE*100)}th pct):", threshold)

# Trade only strongest signals (otherwise stay cash)
results["strategy_ret"] = np.where(
    results["signal_strength"] > threshold,
    results["actual"],
    0.0
)

# Buy & hold baseline
results["buy_hold_ret"] = results["actual"]

# Equity curves
results["strategy_equity"] = (1 + results["strategy_ret"]).cumprod()
results["buy_hold_equity"] = (1 + results["buy_hold_ret"]).cumprod()

print("\nFinal equity (Strategy, thresholded):", results["strategy_equity"].iloc[-1])
print("Final equity (Buy&Hold):", results["buy_hold_equity"].iloc[-1])

print("\nLast 5 rows:")
print(results.tail())

# ==============================
# CHARTS
# ==============================

# --- Equity Curve ---
plt.figure(figsize=(12, 6))
plt.plot(results["date"], results["strategy_equity"], label="Model Strategy (thresholded)")
plt.plot(results["date"], results["buy_hold_equity"], label="Buy & Hold")
plt.title(f"Equity Curve: {SYMBOL} Backtest (Thresholded Signals)")
plt.xlabel("Date")
plt.ylabel("Growth of $1")
plt.legend()
plt.grid(True)
plt.show()

# --- Signal Strength ---
plt.figure(figsize=(12, 5))
plt.plot(results["date"], results["signal_strength"])
plt.title("Model Signal Strength (|Predicted Return|)")
plt.xlabel("Date")
plt.ylabel("Signal Magnitude")
plt.grid(True)
plt.show()

# --- Signal Strength Overlay on Equity ---
plt.figure(figsize=(14, 7))
plt.plot(
    results["date"],
    results["strategy_equity"],
    color="black",
    linewidth=2,
    label="Strategy Equity (thresholded)"
)

scatter = plt.scatter(
    results["date"],
    results["strategy_equity"],
    c=results["signal_strength"],
    cmap="coolwarm",
    alpha=0.85,
    s=25
)

plt.colorbar(scatter, label="Signal Strength (|pred|)")
plt.title("Model Equity Curve with Signal Strength Overlay (Thresholded Strategy)")
plt.xlabel("Date")
plt.ylabel("Growth of $1")
plt.grid(True)
plt.legend()
plt.show()