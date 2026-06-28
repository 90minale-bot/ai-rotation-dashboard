"""
rotation_v2.py

Value vs AI Rotation Tracker v2

Purpose:
- Detect whether market leadership is favoring AI/growth or rotating toward
  value, cyclicals, quality, bonds, and broader market participation.
"""

import pandas as pd
import numpy as np
from yahooquery import Ticker


ROTATION_TICKERS = {
    "QQQ": "AI / Growth",
    "SMH": "Semiconductors / AI Infrastructure",
    "VTV": "Large Cap Value",
    "XLI": "Industrials",
    "XLE": "Energy",
    "EFV": "International Value",
    "VEA": "Developed Markets",
    "TLT": "Long Treasury Bonds",
    "LQD": "Investment Grade Credit",
    "JNK": "High Yield Credit",
    "IEF": "Intermediate Treasury Bonds",
    "QUAL": "Quality Factor",
    "ARKK": "Speculative Innovation",
    "SPY": "S&P 500",
    "RSP": "Equal Weight S&P 500",
    "^VIX": "Volatility Index",
}


RATIO_SIGNALS = {
    "value_vs_ai": ("VTV", "QQQ"),
    "industrials_vs_ai": ("XLI", "QQQ"),
    "energy_vs_ai": ("XLE", "QQQ"),
    "international_value_vs_ai": ("EFV", "QQQ"),
    "developed_markets_vs_ai": ("VEA", "QQQ"),
    "quality_vs_speculation": ("QUAL", "ARKK"),
    "credit_risk_appetite": ("JNK", "IEF"),
    "market_breadth": ("RSP", "SPY"),
    "semis_vs_growth": ("SMH", "QQQ"),
}

SCORE_INPUT_COLUMNS = [
    "value_vs_ai_ret_20",
    "value_vs_ai_trend_up",
    "industrials_vs_ai_ret_20",
    "industrials_vs_ai_trend_up",
    "energy_vs_ai_ret_20",
    "energy_vs_ai_trend_up",
    "international_value_vs_ai_ret_20",
    "international_value_vs_ai_trend_up",
    "quality_vs_speculation_ret_20",
    "quality_vs_speculation_trend_up",
    "market_breadth_ret_20",
    "market_breadth_trend_up",
    "TLT_ret_20",
    "TLT_trend_up",
    "credit_risk_appetite_ret_20",
    "VIX_ret_20",
]


def _normalize_history(raw_history: pd.DataFrame) -> pd.DataFrame:
    if raw_history is None or raw_history.empty:
        return pd.DataFrame()

    df = raw_history.copy()

    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()

    if "date" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_convert(None)

    if "symbol" not in df.columns:
        return pd.DataFrame()

    price_col = "adjclose" if "adjclose" in df.columns else "close"

    if price_col not in df.columns:
        return pd.DataFrame()

    df = df[["date", "symbol", price_col]].rename(columns={price_col: "close"})
    df = df.dropna(subset=["date", "symbol", "close"])

    wide = df.pivot_table(index="date", columns="symbol", values="close", aggfunc="last")
    wide = wide.sort_index()
    wide = wide.ffill().dropna(how="all")

    return wide


def download_rotation_prices(period: str = "2y") -> pd.DataFrame:
    tickers = list(ROTATION_TICKERS.keys())
    tq = Ticker(tickers)
    hist = tq.history(period=period)
    return _normalize_history(hist)


def _safe_ratio(df: pd.DataFrame, numerator: str, denominator: str) -> pd.Series:
    if numerator not in df.columns or denominator not in df.columns:
        return pd.Series(index=df.index, dtype=float)

    ratio = df[numerator] / df[denominator].replace(0, np.nan)
    return ratio.replace([np.inf, -np.inf], np.nan)


def build_rotation_features(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.copy()
    feature_cols = {}

    for signal_name, (num, den) in RATIO_SIGNALS.items():
        ratio_col = f"{signal_name}_ratio"

        ratio = _safe_ratio(df, num, den)
        ma_20 = ratio.rolling(20).mean()
        ma_60 = ratio.rolling(60).mean()

        feature_cols.update(
            {
                ratio_col: ratio,
                f"{signal_name}_ret_5": ratio.pct_change(5, fill_method=None),
                f"{signal_name}_ret_20": ratio.pct_change(20, fill_method=None),
                f"{signal_name}_ret_60": ratio.pct_change(60, fill_method=None),
                f"{signal_name}_ma_20": ma_20,
                f"{signal_name}_ma_60": ma_60,
                f"{signal_name}_trend_up": ma_20 > ma_60,
            }
        )

    standalone_tickers = [
        "QQQ",
        "SMH",
        "VTV",
        "XLI",
        "XLE",
        "EFV",
        "VEA",
        "TLT",
        "LQD",
        "JNK",
        "IEF",
        "QUAL",
        "ARKK",
        "SPY",
        "RSP",
        "^VIX",
    ]

    for ticker in standalone_tickers:
        if ticker in df.columns:
            clean_name = ticker.replace("^", "")
            ma_20 = df[ticker].rolling(20).mean()
            ma_60 = df[ticker].rolling(60).mean()

            feature_cols.update(
                {
                    f"{clean_name}_ret_5": df[ticker].pct_change(5, fill_method=None),
                    f"{clean_name}_ret_20": df[ticker].pct_change(20, fill_method=None),
                    f"{clean_name}_ret_60": df[ticker].pct_change(60, fill_method=None),
                    f"{clean_name}_ma_20": ma_20,
                    f"{clean_name}_ma_60": ma_60,
                    f"{clean_name}_trend_up": ma_20 > ma_60,
                }
            )

    if not feature_cols:
        return df

    return pd.concat([df, pd.DataFrame(feature_cols, index=df.index)], axis=1)


def _latest_scored_row(features: pd.DataFrame) -> pd.Series | None:
    available_cols = [c for c in SCORE_INPUT_COLUMNS if c in features.columns]
    if not available_cols:
        return None

    scored_rows = features.dropna(subset=available_cols, how="all")
    if scored_rows.empty:
        return None

    return scored_rows.iloc[-1]


def score_latest_rotation(features: pd.DataFrame) -> dict:
    if features is None or features.empty:
        return {
            "rotation_score": np.nan,
            "max_score": 9,
            "signal": "NO DATA",
            "details": {},
        }

    latest = _latest_scored_row(features)
    if latest is None:
        return {
            "rotation_score": np.nan,
            "max_score": 9,
            "signal": "NO DATA",
            "details": {},
        }

    score = 0
    details = {}

    def check(condition, label):
        nonlocal score
        passed = bool(condition) if pd.notna(condition) else False
        details[label] = passed
        if passed:
            score += 1

    check(
        latest.get("value_vs_ai_ret_20", np.nan) > 0
        and latest.get("value_vs_ai_trend_up", False),
        "Value outperforming AI",
    )

    check(
        latest.get("industrials_vs_ai_ret_20", np.nan) > 0
        and latest.get("industrials_vs_ai_trend_up", False),
        "Industrials outperforming AI",
    )

    check(
        latest.get("energy_vs_ai_ret_20", np.nan) > 0
        and latest.get("energy_vs_ai_trend_up", False),
        "Energy outperforming AI",
    )

    check(
        latest.get("international_value_vs_ai_ret_20", np.nan) > 0
        and latest.get("international_value_vs_ai_trend_up", False),
        "International value outperforming AI",
    )

    check(
        latest.get("quality_vs_speculation_ret_20", np.nan) > 0
        and latest.get("quality_vs_speculation_trend_up", False),
        "Quality outperforming speculation",
    )

    check(
        latest.get("market_breadth_ret_20", np.nan) > 0
        and latest.get("market_breadth_trend_up", False),
        "Market breadth improving",
    )

    check(
        latest.get("TLT_ret_20", np.nan) > 0
        and latest.get("TLT_trend_up", False),
        "Long bonds rising",
    )

    check(
        latest.get("credit_risk_appetite_ret_20", np.nan) < 0,
        "Credit risk appetite weakening",
    )

    check(
        latest.get("VIX_ret_20", np.nan) > 0,
        "Volatility rising",
    )

    if score >= 7:
        signal = "STRONG VALUE / DEFENSIVE ROTATION"
    elif score >= 5:
        signal = "CONFIRMED ROTATION"
    elif score >= 3:
        signal = "EARLY ROTATION"
    else:
        signal = "AI / GROWTH DOMINANCE"

    return {
        "rotation_score": score,
        "max_score": 9,
        "signal": signal,
        "details": details,
        "as_of": latest.name,
    }


def get_rotation_trend(features: pd.DataFrame, lookback_days: int = 20) -> dict:
    """
    Compare today's rotation score against the score from lookback_days ago.
    """
    if features is None or features.empty or len(features) <= lookback_days:
        return {
            "trend": "NO DATA",
            "score_change": np.nan,
            "prior_score": np.nan,
            "current_score": np.nan,
        }

    current_score = score_latest_rotation(features)
    prior_score = score_latest_rotation(features.iloc[:-lookback_days])

    current = current_score.get("rotation_score", np.nan)
    prior = prior_score.get("rotation_score", np.nan)

    if pd.isna(current) or pd.isna(prior):
        trend = "NO DATA"
        change = np.nan
    else:
        change = current - prior

        if change >= 2:
            trend = "ROTATION STRENGTHENING"
        elif change <= -2:
            trend = "AI DOMINANCE STRENGTHENING"
        elif change > 0:
            trend = "ROTATION IMPROVING"
        elif change < 0:
            trend = "ROTATION WEAKENING"
        else:
            trend = "UNCHANGED"

    return {
        "trend": trend,
        "score_change": change,
        "prior_score": prior,
        "current_score": current,
    }


def get_rotation_dashboard_data(period: str = "2y") -> tuple[pd.DataFrame, dict]:
    prices = download_rotation_prices(period=period)
    features = build_rotation_features(prices)
    score = score_latest_rotation(features)

    return features, score


if __name__ == "__main__":
    features, score = get_rotation_dashboard_data(period="2y")
    trend = get_rotation_trend(features, lookback_days=20)

    print("\n=== Value vs AI Rotation Tracker v2 ===")
    print(f"As of: {score.get('as_of')}")
    print(f"Signal: {score.get('signal')}")
    print(f"Score: {score.get('rotation_score')} / {score.get('max_score')}")

    print("\n20-Day Trend:")
    print(f"Trend: {trend.get('trend')}")
    print(f"Score Change: {trend.get('score_change')}")
    print(f"Prior Score: {trend.get('prior_score')}")
    print(f"Current Score: {trend.get('current_score')}")

    print("\nSignal details:")
    for key, value in score.get("details", {}).items():
        print(f"- {key}: {value}")
