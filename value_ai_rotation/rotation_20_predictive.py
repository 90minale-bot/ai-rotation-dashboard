"""
Predictive 20-day rotation quality layer.

The base rotation score is the tactical signal. This layer improves the 20-day
read by checking signal quality, especially whether AI internals are breaking
down. Backtests showed high rotation scores worked better when semiconductors
were not simultaneously weakening versus broader growth.
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


HORIZON_DAYS = 20
MIN_TRAIN_ROWS = 500


def add_20d_quality_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    score = out["rotation_score"]

    out["score_change_5"] = score - score.shift(5)
    out["score_change_10"] = score - score.shift(10)
    out["score_ge5_count_10"] = (score >= 5).rolling(10).sum()
    out["score_ge7_count_10"] = (score >= 7).rolling(10).sum()

    out["ai_internals_weak"] = (
        (out["semis_vs_growth_ret_5"] < 0)
        & (out["semis_vs_growth_ret_20"] < 0)
    ).astype(float)

    out["breadth_confirmed"] = (
        (out["market_breadth_ret_5"] > 0)
        & (out["market_breadth_ret_20"] > 0)
    ).astype(float)

    out["credit_weak"] = (out["credit_risk_appetite_ret_20"] < 0).astype(float)
    out["volatility_up"] = (out["VIX_ret_20"] > 0).astype(float)

    value_vs_ai_q75 = out["value_vs_ai_ret_20"].rolling(252).quantile(0.75)
    out["value_extension_high"] = (out["value_vs_ai_ret_20"] > value_vs_ai_q75).astype(float)

    return out


def build_20d_model_dataset(
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
    dataset = add_20d_quality_features(dataset)

    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    target_col = f"value_outperformed_{HORIZON_DAYS}d"
    dataset["target_20d"] = dataset[target_col].astype(float)
    dataset.loc[dataset[relative_col].isna(), "target_20d"] = np.nan

    return dataset


def signal_group(row: pd.Series) -> str:
    score = row.get("rotation_score", np.nan)
    ai_weak = bool(row.get("ai_internals_weak", False))

    if pd.isna(score):
        return "NO DATA"

    if score >= 7 and not ai_weak:
        return "HIGH-CONVICTION VALUE ROTATION"
    if score >= 7 and ai_weak:
        return "HIGH SCORE / WEAK AI INTERNALS"
    if score >= 5 and not ai_weak:
        return "VALUE ROTATION WATCH"
    if score >= 5:
        return "VALUE ROTATION MIXED"
    if score >= 3:
        return "EARLY ROTATION"
    return "AI / GROWTH DOMINANCE"


def classify_20d_signal(row: pd.Series) -> str:
    group = signal_group(row)

    if group == "HIGH-CONVICTION VALUE ROTATION":
        return "20D HIGH-CONVICTION VALUE ROTATION"
    if group == "HIGH SCORE / WEAK AI INTERNALS":
        return "20D ROTATION SIGNAL QUALITY WARNING"
    if group == "VALUE ROTATION WATCH":
        return "20D VALUE ROTATION WATCH"
    if group == "VALUE ROTATION MIXED":
        return "20D VALUE ROTATION MIXED"
    if group == "EARLY ROTATION":
        return "20D EARLY ROTATION"
    if group == "AI / GROWTH DOMINANCE":
        return "20D AI / GROWTH DOMINANCE"
    return "NO 20D DATA"


def matching_signal_history(train: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    group = signal_group(row)
    return train[train["signal_group_20d"] == group]


def empirical_20d_prediction(train: pd.DataFrame, row: pd.Series) -> dict:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    hit_col = f"value_outperformed_{HORIZON_DAYS}d"

    train = train.dropna(subset=["rotation_score", relative_col]).copy()
    subset = matching_signal_history(train, row)

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

    return {
        "signal_group_20d": signal_group(row),
        "signal_20d": classify_20d_signal(row),
        "value_probability_20d": value_probability,
        "ai_probability_20d": 1 - value_probability if pd.notna(value_probability) else np.nan,
        "expected_relative_20d": expected_relative_return,
        "matched_observations": observations,
        "ai_internals_weak": bool(row.get("ai_internals_weak", False)),
        "breadth_confirmed": bool(row.get("breadth_confirmed", False)),
        "credit_weak": bool(row.get("credit_weak", False)),
        "volatility_up": bool(row.get("volatility_up", False)),
    }


def walk_forward_20d_model(
    dataset: pd.DataFrame,
    min_train_rows: int = MIN_TRAIN_ROWS,
) -> pd.DataFrame:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"
    hit_col = f"value_outperformed_{HORIZON_DAYS}d"

    model_df = dataset.dropna(subset=["rotation_score", relative_col, "target_20d"]).copy()
    model_df["signal_group_20d"] = model_df.apply(signal_group, axis=1)

    rows = []
    for i in range(min_train_rows + HORIZON_DAYS, len(model_df)):
        train_end = i - HORIZON_DAYS
        train = model_df.iloc[:train_end]
        test = model_df.iloc[i]

        prediction = empirical_20d_prediction(train, test)
        rows.append(
            {
                "date": model_df.index[i],
                "rotation_score": test["rotation_score"],
                relative_col: test[relative_col],
                hit_col: test[hit_col],
                **prediction,
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
            "avg_relative_return": np.nan,
            "median_relative_return": np.nan,
        }

    return {
        "rule": name,
        "observations": int(len(subset)),
        "value_hit_rate": float(subset[hit_col].mean()),
        "avg_relative_return": float(subset[relative_col].mean()),
        "median_relative_return": float(subset[relative_col].median()),
    }


def summarize_20d_model(predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame()

    rows = [
        _summarize_subset(
            "raw score >= 7",
            predictions[predictions["rotation_score"] >= 7],
        ),
        _summarize_subset(
            "score >= 7 and AI internals not weak",
            predictions[
                (predictions["rotation_score"] >= 7)
                & (~predictions["ai_internals_weak"])
            ],
        ),
        _summarize_subset(
            "20D high-conviction value rotation",
            predictions[
                predictions["signal_20d"] == "20D HIGH-CONVICTION VALUE ROTATION"
            ],
        ),
        _summarize_subset(
            "20D value rotation watch",
            predictions[predictions["signal_20d"] == "20D VALUE ROTATION WATCH"],
        ),
    ]

    return pd.DataFrame(rows)


def predict_latest_20d(dataset: pd.DataFrame) -> dict:
    relative_col = f"relative_forward_{HORIZON_DAYS}d"

    train = dataset.dropna(subset=["rotation_score", relative_col]).copy()
    train["signal_group_20d"] = train.apply(signal_group, axis=1)
    latest = dataset.dropna(subset=["rotation_score"]).iloc[-1]
    prediction = empirical_20d_prediction(train, latest)

    return {
        "as_of": latest.name,
        "rotation_score": float(latest["rotation_score"]),
        "train_rows": int(len(train)),
        **prediction,
    }


def format_percent_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary

    out = summary.copy()
    for col in ["value_hit_rate", "avg_relative_return", "median_relative_return"]:
        if col in out.columns:
            out[col] = out[col].map(lambda value: f"{value:.2%}" if pd.notna(value) else "N/A")
    return out


def save_20d_outputs(out_dir: Path, predictions: pd.DataFrame, summary: pd.DataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(out_dir / "rotation_20d_model_predictions.csv")
    summary.to_csv(out_dir / "rotation_20d_model_summary.csv", index=False)


def run_20d_model(period: str = "5y") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    prices = download_rotation_prices(period=period)
    if prices.empty:
        raise RuntimeError("No price data returned for 20-day model.")

    dataset = build_20d_model_dataset(prices)
    predictions = walk_forward_20d_model(dataset)
    summary = summarize_20d_model(predictions)
    latest = predict_latest_20d(dataset)
    return predictions, summary, latest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest an empirical 20-day rotation quality layer."
    )
    parser.add_argument("--period", default="5y", help="Yahoo history period. Default: 5y.")
    parser.add_argument("--out-dir", default=None, help="Optional CSV output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Downloading rotation history for period={args.period}...")
    predictions, summary, latest = run_20d_model(period=args.period)

    print(f"Walk-forward prediction rows: {len(predictions):,}")
    if not predictions.empty:
        print(f"Prediction range: {predictions.index.min().date()} to {predictions.index.max().date()}")

    print("\n=== 20D Quality Layer Backtest ===")
    print(format_percent_table(summary).to_string(index=False))

    print("\n=== Latest 20D Read ===")
    print(f"As of: {latest['as_of'].date()}")
    print(f"Signal: {latest['signal_20d']}")
    print(f"Rotation score: {latest['rotation_score']:.0f} / 9")
    print(f"Value probability: {latest['value_probability_20d']:.2%}")
    print(f"AI/growth probability: {latest['ai_probability_20d']:.2%}")
    print(f"Expected relative return: {latest['expected_relative_20d']:.2%}")
    print(f"AI internals weak: {latest['ai_internals_weak']}")
    print(f"Matched observations: {latest['matched_observations']:,}")
    print(f"Training rows: {latest['train_rows']:,}")

    if args.out_dir:
        save_20d_outputs(Path(args.out_dir), predictions, summary)
        print(f"\nSaved CSV outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()
