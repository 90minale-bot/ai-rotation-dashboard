# main.py
# AI-sector upgraded trainer:
# - Trains a model for a given AI / growth stock symbol (e.g., NVDA)
# - Adds sector context from SMH (VanEck Semiconductor ETF)
# - Adds relative-strength features (stock minus sector proxy)
# - Uses TimeSeriesSplit CV + Ridge regression in a scaling pipeline
# - Saves a single artifact {model, features, meta} to Models/<SYMBOL>_model.pkl

import os
import argparse
from typing import List, Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd
from yahooquery import Ticker
import joblib

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _normalize_date_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    df[col] = pd.to_datetime(df[col], utc=True, errors="coerce").dt.tz_convert(None)
    if col != "date":
        df = df.rename(columns={col: "date"})
    return df


def _history_1y(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
    t = Ticker(symbol)
    hist = t.history(period=period)

    if hist is None or getattr(hist, "empty", True):
        return None

    hist = hist.reset_index()

    date_col = None
    for c in ("date", "Date", "datetime"):
        if c in hist.columns:
            date_col = c
            break

    if date_col is None:
        return None

    hist = _normalize_date_col(hist, date_col)

    col_map = {}
    for c in hist.columns:
        lc = c.lower()
        if lc in {"close", "high", "low", "open", "volume"} and c != lc:
            col_map[c] = lc

    if col_map:
        hist = hist.rename(columns=col_map)

    if "close" not in hist.columns:
        return None

    hist = hist.sort_values("date").dropna(subset=["date", "close"]).copy()
    return hist


def add_stock_features(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    df = df.sort_values("date").copy()

    c = "close"

    df[f"{prefix}ret_1"] = df[c].pct_change()
    df[f"{prefix}ret_5"] = df[c].pct_change(5)
    df[f"{prefix}ret_10"] = df[c].pct_change(10)

    df[f"{prefix}ma_5"] = df[c].rolling(5).mean()
    df[f"{prefix}ma_10"] = df[c].rolling(10).mean()
    df[f"{prefix}ma_20"] = df[c].rolling(20).mean()

    df[f"{prefix}gap_ma5"] = (df[c] / df[f"{prefix}ma_5"]) - 1
    df[f"{prefix}gap_ma10"] = (df[c] / df[f"{prefix}ma_10"]) - 1
    df[f"{prefix}gap_ma20"] = (df[c] / df[f"{prefix}ma_20"]) - 1

    df[f"{prefix}vol_5"] = df[f"{prefix}ret_1"].rolling(5).std()
    df[f"{prefix}vol_10"] = df[f"{prefix}ret_1"].rolling(10).std()
    df[f"{prefix}vol_20"] = df[f"{prefix}ret_1"].rolling(20).std()

    if "high" in df.columns and "low" in df.columns:
        df[f"{prefix}hl_range"] = (df["high"] / df["low"]) - 1

    if "volume" in df.columns:
        df[f"{prefix}vol_chg_1"] = df["volume"].pct_change()
        df[f"{prefix}vol_z_20"] = (
            (df["volume"] - df["volume"].rolling(20).mean())
            / df["volume"].rolling(20).std()
        )

    return df


def add_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    These columns still use the ita_ prefix for backward compatibility.
    In the AI model, ita_ means sector proxy features from SMH by default.
    """
    df = df.copy()

    pairs = [
        ("stock_ret_1", "ita_ret_1", "rel_ret_1"),
        ("stock_ret_5", "ita_ret_5", "rel_ret_5"),
        ("stock_ret_10", "ita_ret_10", "rel_ret_10"),
        ("stock_gap_ma20", "ita_gap_ma20", "rel_gap_ma20"),
        ("stock_vol_10", "ita_vol_10", "rel_vol_10"),
    ]

    for a, b, out in pairs:
        if a in df.columns and b in df.columns:
            df[out] = df[a] - df[b]

    return df


def make_target_next_day_return(df: pd.DataFrame, close_col: str = "close") -> pd.DataFrame:
    df = df.sort_values("date").copy()
    df["target_next_ret_1"] = df[close_col].pct_change().shift(-1)
    return df


def train_ridge_timeseries(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    n_splits: int = 5,
) -> Tuple[Pipeline, Dict[str, Any], float]:

    X = df[feature_cols].to_numpy(dtype=float)
    y = df[target_col].to_numpy(dtype=float)

    tscv = TimeSeriesSplit(n_splits=n_splits)

    pipe = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", Ridge()),
        ]
    )

    param_grid = {"model__alpha": np.logspace(-4, 3, 20)}

    search = GridSearchCV(
        estimator=pipe,
        param_grid=param_grid,
        cv=tscv,
        scoring="neg_mean_squared_error",
        n_jobs=-1,
    )

    search.fit(X, y)

    return search.best_estimator_, search.best_params_, float(search.best_score_)


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float((np.sign(y_true) == np.sign(y_pred)).mean())


def evaluate_holdout(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model: Pipeline,
    holdout: int = 60,
) -> Dict[str, float]:

    df = df.copy()

    if len(df) <= holdout + 10:
        holdout = max(10, len(df) // 5)

    train_df = df.iloc[:-holdout]
    test_df = df.iloc[-holdout:]

    X_train = train_df[feature_cols].to_numpy(dtype=float)
    y_train = train_df[target_col].to_numpy(dtype=float)
    X_test = test_df[feature_cols].to_numpy(dtype=float)
    y_test = test_df[target_col].to_numpy(dtype=float)

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mse = float(np.mean((y_test - y_pred) ** 2))
    da = directional_accuracy(y_test, y_pred)

    return {
        "holdout_mse": mse,
        "holdout_directional_acc": da,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Train AI-sector stock model with sector context."
    )

    parser.add_argument(
        "--symbol",
        required=True,
        help="Stock symbol to train, e.g., NVDA, MSFT, META, AMD, AVGO",
    )

    parser.add_argument(
        "--sector",
        default="SMH",
        help="AI sector ETF proxy symbol. Default is SMH.",
    )

    parser.add_argument(
        "--period",
        default="1y",
        help="History period for yahooquery. Default is 1y.",
    )

    parser.add_argument(
        "--models_dir",
        default="Models",
        help="Where to save models. Default is Models.",
    )

    parser.add_argument(
        "--n_splits",
        type=int,
        default=5,
        help="TimeSeries CV splits. Default is 5.",
    )

    parser.add_argument(
        "--holdout_days",
        type=int,
        default=60,
        help="Holdout size for sanity evaluation. Default is 60.",
    )

    args = parser.parse_args()

    symbol = args.symbol.upper().strip()
    sector_symbol = args.sector.upper().strip()

    print(
        f"[INFO] Training AI-sector model for stock={symbol} "
        f"with sector_proxy={sector_symbol} period={args.period}"
    )

    stock = _history_1y(symbol, period=args.period)
    if stock is None or stock.empty:
        raise SystemExit(f"[ERROR] No stock data found for {symbol}")

    sector = _history_1y(sector_symbol, period=args.period)
    if sector is None or sector.empty:
        raise SystemExit(f"[ERROR] No sector data found for {sector_symbol}")

    sector = sector[["date", "close"]].rename(columns={"close": "close_ita"}).copy()

    df = stock.merge(sector, on="date", how="left")
    df["close_ita"] = df["close_ita"].ffill()

    df_stock = df[
        ["date", "close"] + [c for c in df.columns if c in ("high", "low", "volume")]
    ].copy()

    df_stock = add_stock_features(df_stock, prefix="stock_")

    df_sector = df[["date", "close_ita"]].rename(columns={"close_ita": "close"}).copy()
    df_sector = add_stock_features(df_sector, prefix="ita_")
    df_sector = df_sector.rename(columns={"close": "close_ita"})

    df_feat = df_stock.merge(
        df_sector.drop(columns=["close_ita"], errors="ignore"),
        on="date",
        how="left",
    )

    df_feat = make_target_next_day_return(df_feat, close_col="close")
    df_feat = add_relative_features(df_feat)

    feature_cols = [
        "stock_ret_1",
        "stock_ret_5",
        "stock_ret_10",
        "stock_gap_ma5",
        "stock_gap_ma10",
        "stock_gap_ma20",
        "stock_vol_5",
        "stock_vol_10",
        "stock_vol_20",
        "ita_ret_1",
        "ita_ret_5",
        "ita_ret_10",
        "ita_gap_ma20",
        "ita_vol_10",
        "rel_ret_1",
        "rel_ret_5",
        "rel_ret_10",
        "rel_gap_ma20",
        "rel_vol_10",
    ]

    optional = [
        "stock_hl_range",
        "stock_vol_chg_1",
        "stock_vol_z_20",
    ]

    for c in optional:
        if c in df_feat.columns:
            feature_cols.append(c)

    feature_cols = [c for c in feature_cols if c in df_feat.columns]

    target_col = "target_next_ret_1"

    df_train = df_feat.dropna(subset=feature_cols + [target_col]).copy()

    if len(df_train) < 120:
        raise SystemExit(
            f"[ERROR] Not enough clean training rows after feature engineering "
            f"({len(df_train)}). Try --period 2y or reduce features."
        )

    best_model, best_params, best_score = train_ridge_timeseries(
        df_train,
        feature_cols=feature_cols,
        target_col=target_col,
        n_splits=args.n_splits,
    )

    eval_metrics = evaluate_holdout(
        df_train,
        feature_cols=feature_cols,
        target_col=target_col,
        model=best_model,
        holdout=args.holdout_days,
    )

    print("[INFO] Best params:", best_params)
    print("[INFO] Best CV score (neg MSE):", best_score)
    print("[INFO] Holdout metrics:", eval_metrics)

    X_all = df_train[feature_cols].to_numpy(dtype=float)
    y_all = df_train[target_col].to_numpy(dtype=float)

    best_model.fit(X_all, y_all)

    _ensure_dir(args.models_dir)

    out_path = os.path.join(args.models_dir, f"{symbol}_model.pkl")

    artifact = {
        "model": best_model,
        "features": feature_cols,
        "target": target_col,
        "meta": {
            "stock_symbol": symbol,
            "sector_symbol": sector_symbol,
            "sector_proxy_name": "SMH / AI semiconductor proxy",
            "model_theme": "AI / growth / infrastructure",
            "period": args.period,
            "best_params": best_params,
            "best_cv_score_neg_mse": best_score,
            "eval_metrics": eval_metrics,
            "rows_used": int(len(df_train)),
            "date_min": str(df_train["date"].min()),
            "date_max": str(df_train["date"].max()),
            "feature_note": (
                "ita_ feature prefix retained for backward compatibility; "
                "it represents the selected sector proxy, SMH by default."
            ),
        },
    }

    joblib.dump(artifact, out_path)

    print(f"[OK] Saved model artifact to: {out_path}")


if __name__ == "__main__":
    main()