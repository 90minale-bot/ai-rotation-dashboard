"""
Update the persisted AI/value rotation clock history.

This script is designed for a scheduled GitHub Actions run. It computes the
latest dashboard reads, upserts one row for the latest market as-of date, and
leaves git to commit the history file only when it changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from value_ai_rotation.rotation_20_predictive import build_20d_model_dataset, predict_latest_20d
from value_ai_rotation.rotation_60_predictive import build_60d_model_dataset, predict_latest_60d
from value_ai_rotation.rotation_continuous_predictive import (
    build_model_agreement,
    build_qqq_direction_agreement,
)
from value_ai_rotation.rotation_history import (
    HISTORY_COLUMNS,
    build_clock_snapshot,
    get_history_path,
    read_clock_history,
    upsert_clock_snapshot,
)
from value_ai_rotation.rotation_v2 import download_rotation_prices


def _same_saved_values(existing: pd.Series, snapshot: dict) -> bool:
    for col in HISTORY_COLUMNS:
        if col == "Saved At":
            continue

        left = existing.get(col)
        right = snapshot.get(col)

        if col == "Date":
            if pd.Timestamp(left).normalize() != pd.Timestamp(right).normalize():
                return False
            continue

        if pd.isna(left) and pd.isna(right):
            continue

        if isinstance(left, (int, float, np.number)) or isinstance(right, (int, float, np.number)):
            if not np.isclose(float(left), float(right), equal_nan=True):
                return False
            continue

        if str(left) != str(right):
            return False

    return True


def main() -> None:
    prices = download_rotation_prices(period="5y")
    if prices.empty:
        raise RuntimeError("No price data returned; rotation history was not updated.")

    prediction_20d = predict_latest_20d(build_20d_model_dataset(prices))
    prediction_60d = predict_latest_60d(build_60d_model_dataset(prices))
    agreement = build_model_agreement(prices)
    direction = build_qqq_direction_agreement(prices)

    snapshot = build_clock_snapshot(
        prediction_20d=prediction_20d,
        prediction_60d=prediction_60d,
        agreement=agreement,
        direction=direction,
    )

    history_before = read_clock_history()
    if not history_before.empty:
        snapshot_date = pd.Timestamp(snapshot["Date"]).normalize()
        existing_rows = history_before[history_before["Date"] == snapshot_date]
        if not existing_rows.empty and _same_saved_values(existing_rows.iloc[-1], snapshot):
            print(f"No signal changes for {snapshot_date:%Y-%m-%d}; history file was not updated.")
            return

    history = upsert_clock_snapshot(snapshot)

    print(f"Updated {get_history_path()}")
    print(f"Rows: {len(history):,}")
    print(
        "Latest: "
        f"{snapshot['Date']:%Y-%m-%d} | "
        f"20D={snapshot['20D Signal']} | "
        f"60D={snapshot['60D Signal']} | "
        f"QQQ 5D={snapshot['QQQ 5D Direction']} | "
        f"QQQ 20D={snapshot['QQQ 20D Direction']}"
    )


if __name__ == "__main__":
    main()
