import pandas as pd
import numpy as np
import joblib
from yahooquery import Ticker


# -----------------------------
# Helpers
# -----------------------------
def to_utc_naive(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce").dt.tz_convert(None).dt.normalize()


def normalize_history(hist: pd.DataFrame, label: str) -> pd.DataFrame:
    if hist is None or getattr(hist, "empty", True):
        raise ValueError(f"No data found for {label}")

    hist = hist.reset_index()

    date_col = None
    for c in ["date", "Date", "datetime"]:
        if c in hist.columns:
            date_col = c
            break

    if not date_col:
        raise ValueError(f"No date column found for {label}")

    hist[date_col] = pd.to_datetime(hist[date_col], utc=True, errors="coerce").dt.tz_convert(None)
    if date_col != "date":
        hist = hist.rename(columns={date_col: "date"})

    # lowercase columns
    hist = hist.rename(columns={c: c.lower() for c in hist.columns})

    if "close" not in hist.columns:
        raise ValueError(f"No close column found for {label}")

    # normalize to trading date
    hist["date"] = to_utc_naive(hist["date"])
    return hist.sort_values("date").copy()


# -----------------------------
# Feature Engineering (MATCHES your dashboard file)
# -----------------------------
def add_features(df: pd.DataFrame, close_col: str, prefix: str) -> pd.DataFrame:
    df[f"{prefix}ret_1"] = df[close_col].pct_change()
    df[f"{prefix}ret_5"] = df[close_col].pct_change(5)
    df[f"{prefix}ret_10"] = df[close_col].pct_change(10)

    df[f"{prefix}ma_5"] = df[close_col].rolling(5).mean()
    df[f"{prefix}ma_10"] = df[close_col].rolling(10).mean()
    df[f"{prefix}ma_20"] = df[close_col].rolling(20).mean()

    df[f"{prefix}gap_ma5"] = (df[close_col] / df[f"{prefix}ma_5"]) - 1
    df[f"{prefix}gap_ma10"] = (df[close_col] / df[f"{prefix}ma_10"]) - 1
    df[f"{prefix}gap_ma20"] = (df[close_col] / df[f"{prefix}ma_20"]) - 1

    df[f"{prefix}vol_5"] = df[f"{prefix}ret_1"].rolling(5).std()
    df[f"{prefix}vol_10"] = df[f"{prefix}ret_1"].rolling(10).std()
    df[f"{prefix}vol_20"] = df[f"{prefix}ret_1"].rolling(20).std()

    # Optional stock-only
    if prefix == "stock_":
        if "high" in df.columns and "low" in df.columns:
            # NOTE: This matches your dashboard: (high/low)-1
            # If your training used (high-low)/close, change it here AND in dashboard.
            df["stock_hl_range"] = (df["high"] / df["low"]) - 1

        if "volume" in df.columns:
            df["stock_vol_chg_1"] = df["volume"].pct_change()
            df["stock_vol_z_20"] = (
                (df["volume"] - df["volume"].rolling(20).mean())
                / df["volume"].rolling(20).std()
            )

    return df


def add_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    df["rel_ret_1"] = df["stock_ret_1"] - df["ita_ret_1"]
    df["rel_ret_5"] = df["stock_ret_5"] - df["ita_ret_5"]
    df["rel_ret_10"] = df["stock_ret_10"] - df["ita_ret_10"]
    df["rel_gap_ma20"] = df["stock_gap_ma20"] - df["ita_gap_ma20"]
    df["rel_vol_10"] = df["stock_vol_10"] - df["ita_vol_10"]
    return df


# -----------------------------
# Strength series
# -----------------------------
def strength_percentile_series(preds: np.ndarray) -> np.ndarray:
    """
    Expanding percentile: strength[i] = percentile rank of preds[i] vs preds[:i+1]
    Range 0-100.
    """
    out = np.zeros(len(preds), dtype=float)
    for i in range(len(preds)):
        hist = preds[: i + 1]
        out[i] = (hist <= preds[i]).mean() * 100.0
    return out


# -----------------------------
# Main
# -----------------------------
def main():
    symbol = input("Enter stock symbol (e.g. NOC): ").strip().upper()
    days = input("How many trading days to evaluate? (default 90): ").strip()
    n_days = int(days) if days else 90

    model_path = f"Models/{symbol}_model.pkl"
    artifact = joblib.load(model_path)
    if not isinstance(artifact, dict) or "model" not in artifact or "features" not in artifact:
        raise ValueError(f"Unexpected model artifact format in {model_path}")

    model = artifact["model"]
    feature_cols = artifact["features"]

    # Pull data (use 1y which is enough for 90-day + roll windows)
    stock_hist = normalize_history(Ticker(symbol).history(period="1y"), symbol)
    ita_hist = normalize_history(Ticker("ITA").history(period="1y"), "ITA")

    # Keep ITA close only
    ita_hist = ita_hist[["date", "close"]].rename(columns={"close": "close_ita"})

    df = stock_hist.merge(ita_hist, on="date", how="left")
    df["close_ita"] = df["close_ita"].ffill()

    # Build features
    df = add_features(df, "close", "stock_")
    df = add_features(df, "close_ita", "ita_")
    df = add_relative_features(df)

    df = df.dropna().sort_values("date").reset_index(drop=True)

    # Feature mismatch check
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Model expects features not found in rebuilt dataframe:\n"
            f"{missing}\n\n"
            "This means your training feature engineering differs from this script/dashboard."
        )

    # Need n_days predictions => n_days + 1 rows
    df_eval = df.tail(n_days + 1).copy()
    if len(df_eval) < n_days + 1:
        raise ValueError(f"Not enough rows to evaluate {n_days} days. Try a longer history period.")

    preds = []
    actuals = []
    dates = []

    # Predict day i -> compare to day i+1 actual return
    for i in range(len(df_eval) - 1):
        row_today = df_eval.iloc[i]
        row_next = df_eval.iloc[i + 1]

        X = row_today[feature_cols].to_numpy().reshape(1, -1)
        pred_ret = float(model.predict(X)[0])
        actual_ret = float((row_next["close"] / row_today["close"]) - 1)

        dates.append(row_next["date"])
        preds.append(pred_ret)
        actuals.append(actual_ret)

    out = pd.DataFrame(
        {
            "date": dates,
            "pred_ret": preds,
            "actual_ret": actuals,
        }
    )

    out["strength_pct"] = strength_percentile_series(out["pred_ret"].to_numpy())
    out["actual_up"] = out["actual_ret"] > 0
    out["pred_up"] = out["pred_ret"] > 0

    # Overall stats
    corr = float(np.corrcoef(out["strength_pct"], out["actual_ret"])[0, 1])
    corr_rank = float(np.corrcoef(out["strength_pct"], out["actual_ret"].rank(pct=True))[0, 1])

    print("\n==============================")
    print(f"{symbol} Strength vs Next-Day Actual ({n_days} trading days)")
    print("==============================")
    print(f"Correlation(strength_pct, actual_ret): {corr:.4f}")
    print(f"Correlation(strength_pct, rank(actual_ret)): {corr_rank:.4f}")

    # Bucket analysis
    # buckets: 0-20,20-40,...,80-100
    bins = [0, 20, 40, 60, 80, 100]
    labels = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    out["strength_bucket"] = pd.cut(out["strength_pct"], bins=bins, labels=labels, include_lowest=True)

    bucket = (
        out.groupby("strength_bucket", observed=False)
        .agg(
            days=("actual_ret", "count"),
            avg_actual_ret=("actual_ret", "mean"),
            median_actual_ret=("actual_ret", "median"),
            up_rate=("actual_up", "mean"),
            avg_pred_ret=("pred_ret", "mean"),
        )
        .reset_index()
    )

    # Format nicely
    bucket["avg_actual_ret"] = bucket["avg_actual_ret"].map(lambda x: f"{x:.4%}")
    bucket["median_actual_ret"] = bucket["median_actual_ret"].map(lambda x: f"{x:.4%}")
    bucket["up_rate"] = bucket["up_rate"].map(lambda x: f"{x:.1%}")
    bucket["avg_pred_ret"] = bucket["avg_pred_ret"].map(lambda x: f"{x:.4%}")

    print("\n--- Bucket Summary (Strength -> Next-Day Actual) ---")
    print(bucket.to_string(index=False))

    # Top strength days
    top = out.sort_values("strength_pct", ascending=False).head(10).copy()
    top["pred_ret"] = top["pred_ret"].map(lambda x: f"{x:.4%}")
    top["actual_ret"] = top["actual_ret"].map(lambda x: f"{x:.4%}")
    top["strength_pct"] = top["strength_pct"].map(lambda x: f"{x:.0f}")
    print("\n--- Top 10 Strength Days ---")
    print(top[["date", "strength_pct", "pred_ret", "actual_ret"]].to_string(index=False))

    # Save CSV
    out.to_csv(f"{symbol}_strength_vs_actual_last_{n_days}.csv", index=False)
    print(f"\nSaved: {symbol}_strength_vs_actual_last_{n_days}.csv")
    print("Done.")


if __name__ == "__main__":
    main()