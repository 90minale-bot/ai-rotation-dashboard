import pandas as pd
import numpy as np
import joblib
from yahooquery import Ticker


def to_utc_naive(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True).dt.tz_convert(None).dt.normalize()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)

    df["stock_ret_1"] = df["close"].pct_change(1)
    df["stock_ret_5"] = df["close"].pct_change(5)
    df["stock_ret_10"] = df["close"].pct_change(10)

    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()

    df["stock_gap_ma5"] = df["close"] / df["ma5"] - 1
    df["stock_gap_ma10"] = df["close"] / df["ma10"] - 1
    df["stock_gap_ma20"] = df["close"] / df["ma20"] - 1

    df["stock_vol_5"] = df["stock_ret_1"].rolling(5).std()
    df["stock_vol_10"] = df["stock_ret_1"].rolling(10).std()
    df["stock_vol_20"] = df["stock_ret_1"].rolling(20).std()

    df["stock_hl_range"] = (df["high"] - df["low"]) / df["close"]
    df["stock_vol_chg_1"] = df["volume"].pct_change(1)

    vol_mean_20 = df["volume"].rolling(20).mean()
    vol_std_20 = df["volume"].rolling(20).std()
    df["stock_vol_z_20"] = (df["volume"] - vol_mean_20) / vol_std_20

    df["ita_ret_1"] = df["close_ita"].pct_change(1)
    df["ita_ret_5"] = df["close_ita"].pct_change(5)
    df["ita_ret_10"] = df["close_ita"].pct_change(10)

    df["ita_ma20"] = df["close_ita"].rolling(20).mean()
    df["ita_gap_ma20"] = df["close_ita"] / df["ita_ma20"] - 1
    df["ita_vol_10"] = df["ita_ret_1"].rolling(10).std()

    df["rel_ret_1"] = df["stock_ret_1"] - df["ita_ret_1"]
    df["rel_ret_5"] = df["stock_ret_5"] - df["ita_ret_5"]
    df["rel_ret_10"] = df["stock_ret_10"] - df["ita_ret_10"]
    df["rel_gap_ma20"] = df["stock_gap_ma20"] - df["ita_gap_ma20"]
    df["rel_vol_10"] = df["stock_vol_10"] - df["ita_vol_10"]

    return df


def main():
    symbol = input("Enter stock symbol (e.g. NOC): ").strip().upper()

    model_path = f"Models/{symbol}_model.pkl"
    artifact = joblib.load(model_path)

    model = artifact["model"]
    feature_cols = artifact["features"]

    stock = Ticker(symbol)
    ita = Ticker("ITA")

    stock_df = stock.history(period="3y").reset_index()
    ita_df = ita.history(period="3y").reset_index()

    stock_df = stock_df[stock_df["symbol"] == symbol].copy()
    ita_df = ita_df[ita_df["symbol"] == "ITA"].copy()

    stock_df["date"] = to_utc_naive(stock_df["date"])
    ita_df["date"] = to_utc_naive(ita_df["date"])

    df = pd.merge(
        stock_df,
        ita_df[["date", "close", "high", "low", "volume"]].rename(
            columns={"close": "close_ita", "high": "high_ita",
                     "low": "low_ita", "volume": "volume_ita"}
        ),
        on="date",
        how="inner",
    )

    df = build_features(df)
    df = df.dropna().reset_index(drop=True)

    # Only last 90 trading days
    df_eval = df.tail(91).copy()  # 90 predictions requires 91 rows

    results = []

    for i in range(len(df_eval) - 1):
        row_today = df_eval.iloc[i]
        row_next = df_eval.iloc[i + 1]

        X = row_today[feature_cols].values.reshape(1, -1)

        pred_ret = model.predict(X)[0]
        actual_ret = (row_next["close"] / row_today["close"]) - 1

        results.append({
            "date": row_next["date"],
            "pred_ret": pred_ret,
            "actual_ret": actual_ret
        })

    results_df = pd.DataFrame(results)

    # Metrics
    mae = np.mean(np.abs(results_df["pred_ret"] - results_df["actual_ret"]))
    rmse = np.sqrt(np.mean((results_df["pred_ret"] - results_df["actual_ret"]) ** 2))
    direction_acc = np.mean(
        np.sign(results_df["pred_ret"]) == np.sign(results_df["actual_ret"])
    )

    print("\n===== LAST 90 DAYS PERFORMANCE =====")
    print(f"MAE: {mae:.4%}")
    print(f"RMSE: {rmse:.4%}")
    print(f"Directional Accuracy: {direction_acc:.2%}")
    print(f"Average Predicted Return: {results_df['pred_ret'].mean():.4%}")
    print(f"Average Actual Return:    {results_df['actual_ret'].mean():.4%}")

    worst = results_df.iloc[np.argmax(np.abs(results_df["pred_ret"] - results_df["actual_ret"]))]

    print("\nWorst Miss:")
    print(worst)

    print("\nDone.")


if __name__ == "__main__":
    main()