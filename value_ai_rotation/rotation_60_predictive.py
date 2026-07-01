"""
Predictive 60-day rotation layer.

The tactical rotation score has shown useful short-term behavior, but the
60-day backtest is contrarian: elevated rotation scores have often meant the
value trade is already extended. This module keeps the 60-day read empirical
and transparent instead of forcing a single score to mean the same thing at
every horizon.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from value_ai_rotation.rotation_backtest import (
        DEFAULT_AI_BASKET,
        DEFAULT_VALUE_BASKET,
        build_rotation_backtest,
    )
    from value_ai_rotation.rotation_v2 import download_rotation_prices
except ImportError:
    from rotation_backtest import DEFAULT_AI_BASKET, DEFAULT_VALUE_BASKET, build_rotation_backtest
    from rotation_v2 import download_rotation_prices


HORIZON_DAYS = 60
MIN_TRAIN_ROWS = 500

SCORE_BUCKETS = [
    (0, 2, "0-2 AI / Growth"),
    (3, 4, "3-4 Early Rotation"),
    (5, 6, "5-6 Confirmed Rotation"),
    (7, 9, "7-9 Strong Rotation"),
]


def add_60d_predictive_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    score = out["rotation_score"]

    out["score_change_5"] = score - score.shift(5)
    out["score_change_20"] = score - score.shift(20)
    out["score_ge5_count_20"] = (score >= 5).rolling(20).sum()
    out["score_ge7_count_20"] = (score >= 7).rolling(20).sum()

    value_vs_ai_q75 = out["value_vs_ai_ret_20"].rolling(252).quantile(0.75)
    out["rotation_exhaustion"] = (
        (out["rotation_score"] >= 7)
        & (out["value_vs_ai_ret_20"] > value_vs_ai_q75)
    ).astype(float)

    out["ai_reacceleration"] = (
        (out["semis_vs_growth_ret_20"] > 0)
        & (out["semis_vs_growth_ret_5"] > 0)
    ).astype(float)

    out["risk_recovery"] = (
        (out["credit_risk_appetite_ret_20"] > 0)
        & (out["VIX_ret_20"] < 0)
    ).astype(float)

    return out


def build_60d_model_dataset(
    prices: pd.DataFrame,
    value_basket: Iterable[str] = DEFAULT_VALUE_BASKET,
    ai_basket: Iterable[str] = DEFAULT_AI_BASKET,
) -> pd.DataFrame:
    results, features = build_rotation_backtest(
        prices=prices,
        horizons=(HORIZON_DAYS,),
        value_basket=value_basket,
        ai_basket=ai_basket,
    )
    dataset = results.join(features, how="left", rsuffix="_feature")
    dataset = add_60d_predictive_features(dataset)

    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    target_col = f"value_outperformed_{HORIZON_DAYS}d"
    dataset["target_60d"] = dataset[target_col].astype(float)
    dataset.loc[dataset[relative_col].isna(), "target_60d"] = np.nan

    return dataset


def score_bucket(score: float) -> str:
    if pd.isna(score):
        return "NO DATA"

    score_int = int(score)
    for low, high, label in SCORE_BUCKETS:
        if low <= score_int <= high:
            return label

    return "OUT OF RANGE"


def matching_score_history(train: pd.DataFrame, score: float) -> pd.DataFrame:
    if pd.isna(score):
        return train.iloc[0:0]

    score_int = int(score)
    for low, high, _ in SCORE_BUCKETS:
        if low <= score_int <= high:
            return train[
                (train["rotation_score"] >= low)
                & (train["rotation_score"] <= high)
            ]

    return train.iloc[0:0]


def classify_60d_signal(
    value_probability: float,
    expected_relative_return: float,
    rotation_score: float,
) -> str:
    if pd.notna(rotation_score) and rotation_score >= 5:
        return "ROTATION EXTENDED / AI REASSERTION RISK"

    return "NO 60D EDGE"


def empirical_60d_prediction(train: pd.DataFrame, row: pd.Series) -> dict:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    hit_col = f"value_outperformed_{HORIZON_DAYS}d"

    train = train.dropna(subset=["rotation_score", relative_col]).copy()
    subset = matching_score_history(train, row["rotation_score"])

    if len(subset) < 30:
        subset = train

    if subset.empty:
        value_probability = np.nan
        expected_relative_return = np.nan
        observations = 0
    else:
        value_probability = float(subset[hit_col].mean())
        expected_relative_return = float(subset[relative_col].mean())
        observations = int(len(subset))

    signal = classify_60d_signal(
        value_probability,
        expected_relative_return,
        row["rotation_score"],
    )

    return {
        "score_bucket": score_bucket(row["rotation_score"]),
        "value_probability_60d": value_probability,
        "ai_probability_60d": 1 - value_probability if pd.notna(value_probability) else np.nan,
        "expected_relative_60d": expected_relative_return,
        "signal_60d": signal,
        "matched_observations": observations,
    }


def walk_forward_60d_model(
    dataset: pd.DataFrame,
    min_train_rows: int = MIN_TRAIN_ROWS,
) -> pd.DataFrame:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    hit_col = f"value_outperformed_{HORIZON_DAYS}d"

    model_df = dataset.dropna(subset=["rotation_score", relative_col, "target_60d"]).copy()

    rows = []
    for i in range(min_train_rows + HORIZON_DAYS, len(model_df)):
        train_end = i - HORIZON_DAYS
        train = model_df.iloc[:train_end]
        test = model_df.iloc[i]

        prediction = empirical_60d_prediction(train, test)
        rows.append(
            {
                "date": model_df.index[i],
                "rotation_score": test["rotation_score"],
                f"relative_forward_{HORIZON_DAYS}d": test[relative_col],
                f"value_outperformed_{HORIZON_DAYS}d": test[hit_col],
                **prediction,
                "rotation_exhaustion": test["rotation_exhaustion"],
                "ai_reacceleration": test["ai_reacceleration"],
                "risk_recovery": test["risk_recovery"],
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).set_index("date")


def _summarize_subset(name: str, subset: pd.DataFrame) -> dict:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    hit_col = f"value_outperformed_{HORIZON_DAYS}d"

    if subset.empty:
        return {
            "rule": name,
            "observations": 0,
            "value_hit_rate": np.nan,
            "ai_hit_rate": np.nan,
            "avg_relative_return": np.nan,
            "median_relative_return": np.nan,
        }

    value_hit_rate = float(subset[hit_col].mean())
    return {
        "rule": name,
        "observations": int(len(subset)),
        "value_hit_rate": value_hit_rate,
        "ai_hit_rate": 1 - value_hit_rate,
        "avg_relative_return": float(subset[relative_col].mean()),
        "median_relative_return": float(subset[relative_col].median()),
    }


def summarize_60d_model(predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame()

    rows = [
        _summarize_subset(
            "raw score >= 7",
            predictions[predictions["rotation_score"] >= 7],
        ),
        _summarize_subset(
            "raw score >= 5",
            predictions[predictions["rotation_score"] >= 5],
        ),
        _summarize_subset(
            "model AI reassertion risk",
            predictions[
                predictions["signal_60d"]
                == "ROTATION EXTENDED / AI REASSERTION RISK"
            ],
        ),
    ]

    return pd.DataFrame(rows)


def predict_latest_60d(dataset: pd.DataFrame) -> dict:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"

    train = dataset.dropna(subset=["rotation_score", relative_col]).copy()
    latest = dataset.dropna(subset=["rotation_score"]).iloc[-1]
    prediction = empirical_60d_prediction(train, latest)

    return {
        "as_of": latest.name,
        "rotation_score": float(latest["rotation_score"]),
        "train_rows": int(len(train)),
        **prediction,
    }


def predict_recent_60d(dataset: pd.DataFrame, lookback_days: int = 30) -> pd.DataFrame:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"

    usable = dataset.dropna(subset=["rotation_score"]).copy()
    rows = []

    for as_of, row in usable.tail(lookback_days).iterrows():
        row_position = dataset.index.get_loc(as_of)
        if isinstance(row_position, slice):
            row_position = row_position.stop - 1

        train_end = max(0, int(row_position) - HORIZON_DAYS)
        train = dataset.iloc[:train_end].dropna(subset=["rotation_score", relative_col]).copy()

        prediction = empirical_60d_prediction(train, row)
        rows.append(
            {
                "date": as_of,
                "rotation_score": float(row["rotation_score"]),
                "train_rows": int(len(train)),
                **prediction,
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).set_index("date")


def format_percent_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary

    out = summary.copy()
    for col in [
        "value_hit_rate",
        "ai_hit_rate",
        "avg_relative_return",
        "median_relative_return",
    ]:
        if col in out.columns:
            out[col] = out[col].map(lambda value: f"{value:.2%}" if pd.notna(value) else "N/A")
    return out


def save_60d_outputs(out_dir: Path, predictions: pd.DataFrame, summary: pd.DataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(out_dir / "rotation_60d_model_predictions.csv")
    summary.to_csv(out_dir / "rotation_60d_model_summary.csv", index=False)


def run_60d_model(period: str = "5y") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    prices = download_rotation_prices(period=period)
    if prices.empty:
        raise RuntimeError("No price data returned for 60-day model.")

    dataset = build_60d_model_dataset(prices)
    predictions = walk_forward_60d_model(dataset)
    summary = summarize_60d_model(predictions)
    latest = predict_latest_60d(dataset)
    return predictions, summary, latest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest an empirical 60-day rotation persistence layer."
    )
    parser.add_argument("--period", default="5y", help="Yahoo history period. Default: 5y.")
    parser.add_argument("--out-dir", default=None, help="Optional CSV output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Downloading rotation history for period={args.period}...")
    predictions, summary, latest = run_60d_model(period=args.period)

    print(f"Walk-forward prediction rows: {len(predictions):,}")
    if not predictions.empty:
        print(f"Prediction range: {predictions.index.min().date()} to {predictions.index.max().date()}")

    print("\n=== 60D Empirical Layer Backtest ===")
    print(format_percent_table(summary).to_string(index=False))

    print("\n=== Latest 60D Read ===")
    print(f"As of: {latest['as_of'].date()}")
    print(f"Signal: {latest['signal_60d']}")
    print(f"Score bucket: {latest['score_bucket']}")
    print(f"Rotation score: {latest['rotation_score']:.0f} / 9")
    print(f"Value probability: {latest['value_probability_60d']:.2%}")
    print(f"AI/growth probability: {latest['ai_probability_60d']:.2%}")
    print(f"Expected relative return: {latest['expected_relative_60d']:.2%}")
    print(f"Matched observations: {latest['matched_observations']:,}")
    print(f"Training rows: {latest['train_rows']:,}")

    if args.out_dir:
        save_60d_outputs(Path(args.out_dir), predictions, summary)
        print(f"\nSaved CSV outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()
