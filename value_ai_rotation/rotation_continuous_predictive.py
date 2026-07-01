"""
Continuous predictive layer for AI vs value rotation.

This module complements the bucket-based empirical reads. It uses continuous
market features to estimate whether value is likely to outperform AI/growth
over 20D and 60D horizons, then exposes model-agreement summaries for the
dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from value_ai_rotation.rotation_20_predictive import build_20d_model_dataset
    from value_ai_rotation.rotation_60_predictive import build_60d_model_dataset
    from value_ai_rotation.rotation_v2 import download_rotation_prices
except ImportError:
    from rotation_20_predictive import build_20d_model_dataset
    from rotation_60_predictive import build_60d_model_dataset
    from rotation_v2 import download_rotation_prices


MIN_FULL_ROWS = 250
MIN_AI_ERA_ROWS = 150
MIN_RECENT_ROWS = 250
AI_ERA_START = "2023-01-01"

CONTINUOUS_FEATURES = [
    "rotation_score",
    "score_change_5",
    "score_change_10",
    "score_change_20",
    "score_ge5_count_10",
    "score_ge5_count_20",
    "score_ge7_count_10",
    "score_ge7_count_20",
    "value_vs_ai_ret_5",
    "value_vs_ai_ret_20",
    "value_vs_ai_ret_60",
    "industrials_vs_ai_ret_20",
    "energy_vs_ai_ret_20",
    "international_value_vs_ai_ret_20",
    "quality_vs_speculation_ret_20",
    "market_breadth_ret_5",
    "market_breadth_ret_20",
    "credit_risk_appetite_ret_20",
    "semis_vs_growth_ret_5",
    "semis_vs_growth_ret_20",
    "QQQ_ret_5",
    "QQQ_ret_20",
    "SMH_ret_5",
    "SMH_ret_20",
    "ARKK_ret_20",
    "TLT_ret_20",
    "VIX_ret_5",
    "VIX_ret_20",
    "ai_internals_weak",
    "breadth_confirmed",
    "credit_weak",
    "volatility_up",
    "rotation_exhaustion",
    "ai_reacceleration",
    "risk_recovery",
]


@dataclass(frozen=True)
class ModelSpec:
    label: str
    start_date: str | None
    min_rows: int


MODEL_SPECS = [
    ModelSpec("Full History", None, MIN_FULL_ROWS),
    ModelSpec("AI Era", AI_ERA_START, MIN_AI_ERA_ROWS),
    ModelSpec("Recent 18M", "recent_18m", MIN_RECENT_ROWS),
]


def _available_features(dataset: pd.DataFrame) -> list[str]:
    return [col for col in CONTINUOUS_FEATURES if col in dataset.columns]


def _clean_feature_frame(df: pd.DataFrame, feature_cols: Iterable[str]) -> pd.DataFrame:
    out = df.loc[:, list(feature_cols)].copy()
    out = out.replace([np.inf, -np.inf], np.nan)
    for col in out.columns:
        if out[col].dtype == bool:
            out[col] = out[col].astype(float)
    return out


def _training_start(latest_date: pd.Timestamp, spec: ModelSpec) -> pd.Timestamp | None:
    if spec.start_date is None:
        return None
    if spec.start_date == "recent_18m":
        return latest_date - pd.DateOffset(months=18)
    return pd.Timestamp(spec.start_date)


def _fit_probability(
    dataset: pd.DataFrame,
    horizon: int,
    spec: ModelSpec,
) -> dict:
    relative_col = f"relative_forward_{horizon}d"
    target_col = f"value_outperformed_{horizon}d"
    feature_cols = _available_features(dataset)

    if not feature_cols or relative_col not in dataset.columns or target_col not in dataset.columns:
        return {
            "model": spec.label,
            "available": False,
            "reason": "missing features or target",
        }

    scored = dataset.dropna(subset=["rotation_score"]).copy()
    if scored.empty:
        return {
            "model": spec.label,
            "available": False,
            "reason": "no scored rows",
        }

    latest = scored.iloc[-1]
    latest_date = pd.Timestamp(latest.name)
    latest_position = dataset.index.get_loc(latest.name)
    if isinstance(latest_position, slice):
        latest_position = latest_position.stop - 1

    train_end = max(0, int(latest_position) - horizon)
    train = dataset.iloc[:train_end].dropna(subset=["rotation_score", relative_col, target_col]).copy()

    start = _training_start(latest_date, spec)
    if start is not None:
        train = train[train.index >= start]

    train = train.dropna(subset=[target_col])
    if len(train) < spec.min_rows:
        return {
            "model": spec.label,
            "available": False,
            "reason": f"only {len(train)} rows",
            "training_rows": int(len(train)),
        }

    y = train[target_col].astype(int)
    if y.nunique() < 2:
        return {
            "model": spec.label,
            "available": False,
            "reason": "single target class",
            "training_rows": int(len(train)),
        }

    X_train = _clean_feature_frame(train, feature_cols)
    X_latest = _clean_feature_frame(latest.to_frame().T, feature_cols)

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "logit",
                LogisticRegression(
                    class_weight="balanced",
                    C=0.05,
                    max_iter=2000,
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(X_train, y)
    value_probability = float(model.predict_proba(X_latest)[0, 1])
    ai_probability = 1.0 - value_probability
    favored_side = "Value" if value_probability >= ai_probability else "AI"

    return {
        "model": spec.label,
        "available": True,
        "horizon": horizon,
        "as_of": latest.name,
        "value_probability": value_probability,
        "ai_probability": ai_probability,
        "favored_side": favored_side,
        "favored_probability": max(value_probability, ai_probability),
        "edge": abs(value_probability - 0.5),
        "training_rows": int(len(train)),
        "feature_count": int(len(feature_cols)),
    }


def predict_continuous_models(dataset: pd.DataFrame, horizon: int) -> pd.DataFrame:
    rows = [_fit_probability(dataset, horizon, spec) for spec in MODEL_SPECS]
    return pd.DataFrame(rows)


def _agreement_label(rows: pd.DataFrame) -> str:
    available = rows[rows["available"] == True].copy()
    if available.empty:
        return "NO MODEL"

    sides = available["favored_side"].dropna()
    if sides.empty:
        return "NO MODEL"

    value_votes = int((sides == "Value").sum())
    ai_votes = int((sides == "AI").sum())

    if value_votes == len(sides):
        return "VALUE AGREEMENT"
    if ai_votes == len(sides):
        return "AI AGREEMENT"
    return "MIXED"


def build_model_agreement(prices: pd.DataFrame) -> dict:
    dataset_20d = build_20d_model_dataset(prices)
    dataset_60d = build_60d_model_dataset(prices)

    models_20d = predict_continuous_models(dataset_20d, horizon=20)
    models_60d = predict_continuous_models(dataset_60d, horizon=60)

    return {
        "models_20d": models_20d,
        "models_60d": models_60d,
        "agreement_20d": _agreement_label(models_20d),
        "agreement_60d": _agreement_label(models_60d),
    }


def _direction_dataset(prices: pd.DataFrame, horizon: int) -> pd.DataFrame:
    dataset = build_20d_model_dataset(prices).copy()
    if "QQQ" not in prices.columns:
        return dataset.iloc[0:0]

    qqq_forward = prices["QQQ"].shift(-horizon) / prices["QQQ"] - 1
    dataset[f"qqq_forward_{horizon}d"] = qqq_forward
    dataset[f"qqq_positive_{horizon}d"] = np.where(qqq_forward.isna(), np.nan, (qqq_forward > 0).astype(float))
    return dataset


def _fit_direction_probability(
    dataset: pd.DataFrame,
    horizon: int,
    spec: ModelSpec,
) -> dict:
    forward_col = f"qqq_forward_{horizon}d"
    target_col = f"qqq_positive_{horizon}d"
    feature_cols = _available_features(dataset)

    if not feature_cols or forward_col not in dataset.columns or target_col not in dataset.columns:
        return {
            "model": spec.label,
            "available": False,
            "reason": "missing features or target",
        }

    scored = dataset.dropna(subset=["rotation_score"]).copy()
    if scored.empty:
        return {
            "model": spec.label,
            "available": False,
            "reason": "no scored rows",
        }

    latest = scored.iloc[-1]
    latest_date = pd.Timestamp(latest.name)
    latest_position = dataset.index.get_loc(latest.name)
    if isinstance(latest_position, slice):
        latest_position = latest_position.stop - 1

    train_end = max(0, int(latest_position) - horizon)
    train = dataset.iloc[:train_end].dropna(subset=["rotation_score", forward_col, target_col]).copy()

    start = _training_start(latest_date, spec)
    if start is not None:
        train = train[train.index >= start]

    if len(train) < spec.min_rows:
        return {
            "model": spec.label,
            "available": False,
            "reason": f"only {len(train)} rows",
            "training_rows": int(len(train)),
        }

    y = train[target_col].astype(int)
    if y.nunique() < 2:
        return {
            "model": spec.label,
            "available": False,
            "reason": "single target class",
            "training_rows": int(len(train)),
        }

    X_train = _clean_feature_frame(train, feature_cols)
    X_latest = _clean_feature_frame(latest.to_frame().T, feature_cols)

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "logit",
                LogisticRegression(
                    class_weight="balanced",
                    C=0.05,
                    max_iter=2000,
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(X_train, y)
    up_probability = float(model.predict_proba(X_latest)[0, 1])
    down_probability = 1.0 - up_probability
    expected_return = float(train[forward_col].mean())
    similar_direction = train[train[target_col] == int(up_probability >= down_probability)]
    if not similar_direction.empty:
        expected_return = float(similar_direction[forward_col].mean())

    favored_side = "Up" if up_probability >= down_probability else "Down"

    return {
        "model": spec.label,
        "available": True,
        "horizon": horizon,
        "as_of": latest.name,
        "up_probability": up_probability,
        "down_probability": down_probability,
        "favored_side": favored_side,
        "favored_probability": max(up_probability, down_probability),
        "edge": abs(up_probability - 0.5),
        "expected_return": expected_return,
        "training_rows": int(len(train)),
        "feature_count": int(len(feature_cols)),
    }


def predict_direction_models(dataset: pd.DataFrame, horizon: int) -> pd.DataFrame:
    rows = [_fit_direction_probability(dataset, horizon, spec) for spec in MODEL_SPECS]
    return pd.DataFrame(rows)


def _direction_agreement_label(rows: pd.DataFrame) -> str:
    available = rows[rows["available"] == True].copy()
    if available.empty:
        return "NO MODEL"

    sides = available["favored_side"].dropna()
    if sides.empty:
        return "NO MODEL"

    up_votes = int((sides == "Up").sum())
    down_votes = int((sides == "Down").sum())

    if up_votes == len(sides):
        return "QQQ UP AGREEMENT"
    if down_votes == len(sides):
        return "QQQ DOWN AGREEMENT"
    return "MIXED"


def build_qqq_direction_agreement(prices: pd.DataFrame) -> dict:
    dataset_5d = _direction_dataset(prices, horizon=5)
    dataset_20d = _direction_dataset(prices, horizon=20)

    models_5d = predict_direction_models(dataset_5d, horizon=5)
    models_20d = predict_direction_models(dataset_20d, horizon=20)

    return {
        "models_5d": models_5d,
        "models_20d": models_20d,
        "agreement_5d": _direction_agreement_label(models_5d),
        "agreement_20d": _direction_agreement_label(models_20d),
    }


def run_model_agreement(period: str = "5y") -> dict:
    prices = download_rotation_prices(period=period)
    if prices.empty:
        raise RuntimeError("No price data returned for continuous model.")
    return build_model_agreement(prices)
