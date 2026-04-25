import pandas as pd
import numpy as np
import joblib
from yahooquery import Ticker


def to_utc_naive(s: pd.Series) -> pd.Series:
    """
    Convert a datetime-like series to UTC then drop timezone (tz-naive) and normalize to date.
    This avoids pandas errors when yahooquery returns tz-aware timestamps.
    """
    return pd.to_datetime(s, utc=True).dt.tz_convert(None).dt.normalize()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature set consistent with your Stock Analytics project:
    - Stock: returns, MA gaps, volatility, optional range/volume features
    - ITA: returns, MA gap, volatility
    - Relative strength: stock - ITA features
    """
    df = df.sort_values("date").reset_index(drop=True)

    # --- STOCK RETURNS ---
    df["stock_ret_1"] = df["close"].pct_change(1)
    df["stock_ret_5"] = df["close"].pct_change(5)
    df["stock_ret_10"] = df["close"].pct_change(10)

    # --- STOCK MOVING AVERAGES / GAPS ---
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()

    df["stock_gap_ma5"] = df["close"] / df["ma5"] - 1
    df["stock_gap_ma10"] = df["close"] / df["ma10"] - 1
    df["stock_gap_ma20"] = df["close"] / df["ma20"] - 1

    # --- STOCK VOLATILITY ---
    df["stock_vol_5"] = df["stock_ret_1"].rolling(5).std()
    df["stock_vol_10"] = df["stock_ret_1"].rolling(10).std()
    df["stock_vol_20"] = df["stock_ret_1"].rolling(20).std()

    # --- OPTIONAL STOCK FEATURES (your model expects these) ---
    # Intraday range scaled by close
    df["stock_hl_range"] = (df["high"] - df["low"]) / df["close"]

    # 1-day volume change
    df["stock_vol_chg_1"] = df["volume"].pct_change(1)

    # 20-day volume z-score
    vol_mean_20 = df["volume"].rolling(20).mean()
    vol_std_20 = df["volume"].rolling(20).std()
    df["stock_vol_z_20"] = (df["volume"] - vol_mean_20) / vol_std_20

    # --- ITA RETURNS ---
    df["ita_ret_1"] = df["close_ita"].pct_change(1)
    df["ita_ret_5"] = df["close_ita"].pct_change(5)
    df["ita_ret_10"] = df["close_ita"].pct_change(10)

    # --- ITA GAP / VOL ---
    df["ita_ma20"] = df["close_ita"].rolling(20).mean()
    df["ita_gap_ma20"] = df["close_ita"] / df["ita_ma20"] - 1
    df["ita_vol_10"] = df["ita_ret_1"].rolling(10).std()

    # --- RELATIVE STRENGTH ---
    df["rel_ret_1"] = df["stock_ret_1"] - df["ita_ret_1"]
    df["rel_ret_5"] = df["stock_ret_5"] - df["ita_ret_5"]
    df["rel_ret_10"] = df["stock_ret_10"] - df["ita_ret_10"]
    df["rel_gap_ma20"] = df["stock_gap_ma20"] - df["ita_gap_ma20"]
    df["rel_vol_10"] = df["stock_vol_10"] - df["ita_vol_10"]

    return df


def main():
    # -----------------------------
    # USER INPUT
    # -----------------------------
    symbol = input("Enter stock symbol (e.g. NOC): ").strip().upper()
    pred_date_input = input("Enter prediction date (YYYY-MM-DD): ").strip()

    try:
        pred_date = pd.to_datetime(pred_date_input).normalize()
    except Exception:
        raise ValueError("Could not parse date. Use format YYYY-MM-DD (e.g. 2026-03-02).")

    # -----------------------------
    # LOAD MODEL ARTIFACT
    # -----------------------------
    model_path = f"Models/{symbol}_model.pkl"
    artifact = joblib.load(model_path)

    if not isinstance(artifact, dict) or "model" not in artifact or "features" not in artifact:
        raise ValueError(
            f"Unexpected model artifact format in {model_path}. Expected dict with keys: model, features."
        )

    model = artifact["model"]
    feature_cols = artifact["features"]

    print(f"\nLoaded model: {model_path}")
    print(f"Feature count expected: {len(feature_cols)}")

    # -----------------------------
    # DOWNLOAD DATA
    # -----------------------------
    stock = Ticker(symbol)
    ita = Ticker("ITA")

    stock_df = stock.history(period="3y").reset_index()
    ita_df = ita.history(period="3y").reset_index()

    # Filter down to just the correct symbols
    stock_df = stock_df[stock_df["symbol"] == symbol].copy()
    ita_df = ita_df[ita_df["symbol"] == "ITA"].copy()

    if stock_df.empty:
        raise ValueError(f"No history returned for {symbol}. Check the ticker symbol.")
    if ita_df.empty:
        raise ValueError("No history returned for ITA. Check yahooquery connectivity.")

    # Normalize dates (tz-safe)
    stock_df["date"] = to_utc_naive(stock_df["date"])
    ita_df["date"] = to_utc_naive(ita_df["date"])

    # -----------------------------
    # MERGE ON DATE
    # -----------------------------
    df = pd.merge(
        stock_df,
        ita_df[["date", "close", "high", "low", "volume"]].rename(
            columns={"close": "close_ita", "high": "high_ita", "low": "low_ita", "volume": "volume_ita"}
        ),
        on="date",
        how="inner",
    )

    if df.empty:
        raise ValueError("Merged dataframe is empty. Dates may not overlap between stock and ITA.")

    # -----------------------------
    # BUILD FEATURES
    # -----------------------------
    df = build_features(df)

    # Drop rows with NaNs introduced by rolling windows
    df = df.dropna().reset_index(drop=True)

    # -----------------------------
    # DEBUG: DATE DIAGNOSTICS
    # -----------------------------
    print("\n===== DATE DEBUG =====")
    print(f"Target date entered: {pred_date.strftime('%Y-%m-%d')}")
    print(f"Data date range: {df['date'].min().strftime('%Y-%m-%d')} -> {df['date'].max().strftime('%Y-%m-%d')}")
    print("Last 10 available trading dates:", df["date"].tail(10).dt.strftime("%Y-%m-%d").tolist())
    print("======================\n")

    # -----------------------------
    # FIND "AS-OF" DATE (PREVIOUS TRADING DAY)
    # -----------------------------
    available_dates = df["date"]
    asof_date = available_dates[available_dates < pred_date].max()

    if pd.isna(asof_date):
        raise ValueError(
            f"No prior trading day found before {pred_date.date()} in your dataset. "
            "Try increasing history period or checking the date."
        )

    print(f"Prediction for {pred_date.date()} would have been generated using features as-of: {asof_date.date()}")

    row = df[df["date"] == asof_date]
    if row.empty:
        raise ValueError("Internal error: as-of row not found after filtering.")

    # -----------------------------
    # FEATURE MISMATCH CHECK
    # -----------------------------
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Model expects features not found in rebuilt dataframe:\n"
            f"{missing}\n\n"
            "This means your main.py feature engineering differs from this recovery script."
        )

    X = row[feature_cols]

    # -----------------------------
    # PREDICT
    # -----------------------------
    pred_ret = float(model.predict(X)[0])
    close_prev = float(row["close"].values[0])
    pred_close = close_prev * (1 + pred_ret)

    print("\n----- MODEL OUTPUT -----")
    print(f"Predicted next-day return: {pred_ret:.4%}")
    print(f"Previous close (as-of):    {close_prev:.2f}")
    print(f"Implied next close:        {pred_close:.2f}")

    # -----------------------------
    # ACTUAL (IF AVAILABLE)
    # -----------------------------
    actual_row = df[df["date"] == pred_date]
    if not actual_row.empty:
        actual_close = float(actual_row["close"].values[0])
        actual_ret = (actual_close / close_prev) - 1

        print("\n----- ACTUAL RESULT -----")
        print(f"Actual next-day return:    {actual_ret:.4%}")
        print(f"Actual next close:         {actual_close:.2f}")
        print(f"Prediction error (ret):    {(pred_ret - actual_ret):.4%}")
    else:
        print("\nActual data not available for that date in the pulled history (market closed or date too recent).")

    print("\nDone.")


if __name__ == "__main__":
    main()