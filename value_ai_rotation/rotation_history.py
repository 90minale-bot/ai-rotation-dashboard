"""
Persistent history for rotation dashboard reads.

The backdated trend is useful for context, but the live dashboard should also
keep a dated record of what it actually showed over time. This module writes
one row per market as-of date and updates that row if the same date is rerun.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "data" / "rotation_clock_history.csv"

HISTORY_COLUMNS = [
    "Date",
    "Saved At",
    "Score",
    "20D Signal",
    "20D Favors Value",
    "20D Favors AI",
    "20D Expected Rel",
    "20D Matched Obs",
    "60D Signal",
    "60D Favors Value",
    "60D Favors AI",
    "60D Expected Rel",
    "60D Matched Obs",
    "20D Agreement",
    "60D Agreement",
    "QQQ 5D Direction",
    "QQQ 20D Direction",
]


def get_history_path() -> Path:
    configured = os.getenv("ROTATION_HISTORY_PATH")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_HISTORY_PATH


def _as_date(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None:
        return pd.NaT
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return pd.NaT
    return pd.Timestamp(timestamp).normalize()


def _safe_float(value: Any) -> float:
    if value is None:
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def build_clock_snapshot(
    prediction_20d: dict | None,
    prediction_60d: dict | None,
    agreement: dict | None = None,
    direction: dict | None = None,
) -> dict:
    prediction_20d = prediction_20d or {}
    prediction_60d = prediction_60d or {}
    agreement = agreement or {}
    direction = direction or {}

    as_of = _as_date(prediction_20d.get("as_of"))
    if pd.isna(as_of):
        as_of = _as_date(prediction_60d.get("as_of"))

    return {
        "Date": as_of,
        "Saved At": pd.Timestamp.now().isoformat(timespec="seconds"),
        "Score": _safe_float(prediction_20d.get("rotation_score", prediction_60d.get("rotation_score"))),
        "20D Signal": prediction_20d.get("signal_20d"),
        "20D Favors Value": _safe_float(prediction_20d.get("value_probability_20d")),
        "20D Favors AI": _safe_float(prediction_20d.get("ai_probability_20d")),
        "20D Expected Rel": _safe_float(prediction_20d.get("expected_relative_20d")),
        "20D Matched Obs": _safe_float(prediction_20d.get("matched_observations")),
        "60D Signal": prediction_60d.get("signal_60d"),
        "60D Favors Value": _safe_float(prediction_60d.get("value_probability_60d")),
        "60D Favors AI": _safe_float(prediction_60d.get("ai_probability_60d")),
        "60D Expected Rel": _safe_float(prediction_60d.get("expected_relative_60d")),
        "60D Matched Obs": _safe_float(prediction_60d.get("matched_observations")),
        "20D Agreement": agreement.get("agreement_20d"),
        "60D Agreement": agreement.get("agreement_60d"),
        "QQQ 5D Direction": direction.get("agreement_5d"),
        "QQQ 20D Direction": direction.get("agreement_20d"),
    }


def read_clock_history(path: Path | None = None) -> pd.DataFrame:
    history_path = path or get_history_path()
    if not history_path.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    history = pd.read_csv(history_path)
    for col in HISTORY_COLUMNS:
        if col not in history.columns:
            history[col] = np.nan

    history = history[HISTORY_COLUMNS].copy()
    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
    history = history.dropna(subset=["Date"])
    return history.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")


def upsert_clock_snapshot(snapshot: dict, path: Path | None = None) -> pd.DataFrame:
    history_path = path or get_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot_df = pd.DataFrame([snapshot], columns=HISTORY_COLUMNS)
    snapshot_df["Date"] = pd.to_datetime(snapshot_df["Date"], errors="coerce")
    snapshot_df = snapshot_df.dropna(subset=["Date"])
    if snapshot_df.empty:
        return read_clock_history(history_path)

    history = read_clock_history(history_path)
    combined = pd.concat([history, snapshot_df], ignore_index=True)
    combined = combined.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    combined.to_csv(history_path, index=False)
    return combined

