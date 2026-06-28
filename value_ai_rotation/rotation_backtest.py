"""
Backtest the AI vs value rotation score against future relative returns.

The core question is:
When the rotation score is high today, does a value basket outperform an
AI/growth basket over the next N trading days?
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from value_ai_rotation.rotation_v2 import (
        build_rotation_features,
        download_rotation_prices,
        score_rotation_row,
    )
except ImportError:
    from rotation_v2 import build_rotation_features, download_rotation_prices, score_rotation_row


DEFAULT_VALUE_BASKET = ("VTV", "XLI", "XLE", "EFV", "VEA", "RSP", "QUAL")
DEFAULT_AI_BASKET = ("QQQ", "SMH", "ARKK")
DEFAULT_HORIZONS = (20, 60)

SCORE_BUCKETS = [
    (0, 2, "0-2 AI / Growth"),
    (3, 4, "3-4 Early Rotation"),
    (5, 6, "5-6 Confirmed Rotation"),
    (7, 9, "7-9 Strong Rotation"),
]

REQUIRED_SCORE_INPUTS = [
    "value_vs_ai_ret_20",
    "industrials_vs_ai_ret_20",
    "energy_vs_ai_ret_20",
    "international_value_vs_ai_ret_20",
    "quality_vs_speculation_ret_20",
    "market_breadth_ret_20",
    "TLT_ret_20",
    "credit_risk_appetite_ret_20",
    "VIX_ret_20",
]


def _available_tickers(prices: pd.DataFrame, tickers: Iterable[str]) -> list[str]:
    return [ticker for ticker in tickers if ticker in prices.columns]


def _basket_forward_return(
    prices: pd.DataFrame,
    tickers: Iterable[str],
    horizon: int,
) -> pd.Series:
    available = _available_tickers(prices, tickers)
    if not available:
        return pd.Series(index=prices.index, dtype=float)

    forward_returns = prices[available].shift(-horizon) / prices[available] - 1
    return forward_returns.mean(axis=1, skipna=True)


def _score_bucket(score: float) -> str:
    if pd.isna(score):
        return "NO DATA"

    score_int = int(score)
    for low, high, label in SCORE_BUCKETS:
        if low <= score_int <= high:
            return label

    return "OUT OF RANGE"


def _score_history(features: pd.DataFrame) -> pd.DataFrame:
    required = [col for col in REQUIRED_SCORE_INPUTS if col in features.columns]
    if required:
        has_enough_data = features[required].notna().any(axis=1)
    else:
        has_enough_data = pd.Series(False, index=features.index)

    rows = []
    for as_of, row in features.iterrows():
        if not bool(has_enough_data.loc[as_of]):
            rows.append(
                {
                    "as_of": as_of,
                    "rotation_score": np.nan,
                    "signal": "NO DATA",
                    "score_bucket": "NO DATA",
                }
            )
            continue

        score_data = score_rotation_row(row)
        score = score_data.get("rotation_score", np.nan)
        rows.append(
            {
                "as_of": as_of,
                "rotation_score": score,
                "signal": score_data.get("signal", "NO DATA"),
                "score_bucket": _score_bucket(score),
            }
        )

    return pd.DataFrame(rows).set_index("as_of")


def build_rotation_backtest(
    prices: pd.DataFrame,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    value_basket: Iterable[str] = DEFAULT_VALUE_BASKET,
    ai_basket: Iterable[str] = DEFAULT_AI_BASKET,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = build_rotation_features(prices)
    results = _score_history(features)

    for horizon in horizons:
        value_return = _basket_forward_return(prices, value_basket, horizon)
        ai_return = _basket_forward_return(prices, ai_basket, horizon)

        results[f"value_forward_{horizon}d"] = value_return
        results[f"ai_forward_{horizon}d"] = ai_return
        results[f"relative_forward_{horizon}d"] = value_return - ai_return
        results[f"value_outperformed_{horizon}d"] = (
            results[f"relative_forward_{horizon}d"] > 0
        )

    return results, features


def summarize_by_score_bucket(results: pd.DataFrame, horizon: int) -> pd.DataFrame:
    relative_col = f"relative_forward_{horizon}d"
    value_col = f"value_forward_{horizon}d"
    ai_col = f"ai_forward_{horizon}d"
    hit_col = f"value_outperformed_{horizon}d"

    data = results.dropna(subset=["rotation_score", relative_col]).copy()
    if data.empty:
        return pd.DataFrame()

    summary = (
        data.groupby("score_bucket", sort=False)
        .agg(
            observations=(relative_col, "size"),
            hit_rate=(hit_col, "mean"),
            avg_relative_return=(relative_col, "mean"),
            median_relative_return=(relative_col, "median"),
            avg_value_return=(value_col, "mean"),
            avg_ai_return=(ai_col, "mean"),
        )
        .reset_index()
    )

    return summary


def summarize_by_exact_score(results: pd.DataFrame, horizon: int) -> pd.DataFrame:
    relative_col = f"relative_forward_{horizon}d"
    hit_col = f"value_outperformed_{horizon}d"

    data = results.dropna(subset=["rotation_score", relative_col]).copy()
    if data.empty:
        return pd.DataFrame()

    data["rotation_score"] = data["rotation_score"].astype(int)
    return (
        data.groupby("rotation_score")
        .agg(
            observations=(relative_col, "size"),
            hit_rate=(hit_col, "mean"),
            avg_relative_return=(relative_col, "mean"),
            median_relative_return=(relative_col, "median"),
        )
        .reset_index()
        .sort_values("rotation_score")
    )


def summarize_thresholds(
    results: pd.DataFrame,
    horizon: int,
    thresholds: Iterable[int] = (3, 5, 7),
) -> pd.DataFrame:
    relative_col = f"relative_forward_{horizon}d"
    hit_col = f"value_outperformed_{horizon}d"

    data = results.dropna(subset=["rotation_score", relative_col]).copy()
    rows = []

    for threshold in thresholds:
        subset = data[data["rotation_score"] >= threshold]
        if subset.empty:
            rows.append(
                {
                    "signal_rule": f"score >= {threshold}",
                    "observations": 0,
                    "hit_rate": np.nan,
                    "avg_relative_return": np.nan,
                    "median_relative_return": np.nan,
                }
            )
            continue

        rows.append(
            {
                "signal_rule": f"score >= {threshold}",
                "observations": int(len(subset)),
                "hit_rate": float(subset[hit_col].mean()),
                "avg_relative_return": float(subset[relative_col].mean()),
                "median_relative_return": float(subset[relative_col].median()),
            }
        )

    return pd.DataFrame(rows)


def _format_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary

    out = summary.copy()
    pct_cols = [
        "hit_rate",
        "avg_relative_return",
        "median_relative_return",
        "avg_value_return",
        "avg_ai_return",
    ]
    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].map(lambda value: f"{value:.2%}" if pd.notna(value) else "N/A")
    return out


def save_backtest_outputs(
    out_dir: Path,
    results: pd.DataFrame,
    horizons: Iterable[int],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_dir / "rotation_backtest_daily.csv")

    for horizon in horizons:
        summarize_by_score_bucket(results, horizon).to_csv(
            out_dir / f"rotation_backtest_summary_{horizon}d.csv",
            index=False,
        )
        summarize_by_exact_score(results, horizon).to_csv(
            out_dir / f"rotation_backtest_exact_score_{horizon}d.csv",
            index=False,
        )
        summarize_thresholds(results, horizon).to_csv(
            out_dir / f"rotation_backtest_thresholds_{horizon}d.csv",
            index=False,
        )


def run_backtest(
    period: str = "5y",
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    value_basket: Iterable[str] = DEFAULT_VALUE_BASKET,
    ai_basket: Iterable[str] = DEFAULT_AI_BASKET,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = download_rotation_prices(period=period)
    if prices.empty:
        raise RuntimeError("No price data returned for rotation backtest.")

    return build_rotation_backtest(
        prices=prices,
        horizons=horizons,
        value_basket=value_basket,
        ai_basket=ai_basket,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest the AI vs value rotation score against future relative returns."
    )
    parser.add_argument("--period", default="5y", help="Yahoo history period. Default: 5y.")
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=list(DEFAULT_HORIZONS),
        help="Forward trading-day horizons to test. Default: 20 60.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional directory for CSV outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    horizons = tuple(args.horizons)

    print(f"Downloading rotation history for period={args.period}...")
    results, _ = run_backtest(period=args.period, horizons=horizons)

    valid_scores = results.dropna(subset=["rotation_score"])
    print(f"Backtest rows with usable scores: {len(valid_scores):,}")
    if not valid_scores.empty:
        print(f"Date range: {valid_scores.index.min().date()} to {valid_scores.index.max().date()}")

    for horizon in horizons:
        print(f"\n=== Forward {horizon} trading days ===")
        print("\nBy score bucket:")
        print(_format_summary(summarize_by_score_bucket(results, horizon)).to_string(index=False))

        print("\nBy signal threshold:")
        print(_format_summary(summarize_thresholds(results, horizon)).to_string(index=False))

    if args.out_dir:
        save_backtest_outputs(Path(args.out_dir), results, horizons)
        print(f"\nSaved CSV outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()
