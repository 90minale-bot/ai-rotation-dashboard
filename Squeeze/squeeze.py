import argparse
from datetime import datetime

import pandas as pd
import yfinance as yf
from yahooquery import Ticker


DEFAULT_WATCHLIST = [
    "GME", "AMC", "BYND", "CVNA", "PLTR",
    "CAR", "HTZ", "SOUN", "NVAX", "NTLA",
    "W", "CHTR", "MRNA", "WOLF", "PLUG",
    "APLD", "RIVN", "LCID", "MARA", "RIOT",
    "AI", "UPST", "BBAI", "IONQ"
]

OUTPUT_FILE = "squeeze_results.csv"


def get_all_us_tickers():
    urls = [
        "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    ]

    tickers = []

    for url in urls:
        df = pd.read_csv(url, sep="|")
        symbol_col = "Symbol" if "Symbol" in df.columns else "ACT Symbol"

        df = df[df[symbol_col].notna()]
        df = df[~df[symbol_col].astype(str).str.contains("File Creation Time", na=False)]

        if "Test Issue" in df.columns:
            df = df[df["Test Issue"] == "N"]

        if "ETF" in df.columns:
            df = df[df["ETF"] != "Y"]

        tickers.extend(df[symbol_col].astype(str).tolist())

    clean = []

    for t in tickers:
        t = t.strip().upper()

        if not t:
            continue

        if any(x in t for x in ["$", "^", "/", ".", "-"]):
            continue

        if len(t) > 5:
            continue

        clean.append(t)

    return sorted(list(set(clean)))


def safe_get(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def safe_number(value):
    try:
        if value is None:
            return None
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except Exception:
        return None


def get_short_data(symbol):
    try:
        t = Ticker(symbol)
        stats = t.key_stats.get(symbol, {})

        short_percent_float = safe_number(safe_get(stats, "shortPercentOfFloat"))
        short_ratio = safe_number(safe_get(stats, "shortRatio"))
        shares_short = safe_number(safe_get(stats, "sharesShort"))
        float_shares = safe_number(safe_get(stats, "floatShares"))
        market_cap = safe_number(safe_get(stats, "marketCap"))

        return {
            "symbol": symbol,
            "short_float_pct": round(short_percent_float * 100, 2) if short_percent_float is not None else None,
            "days_to_cover": round(short_ratio, 2) if short_ratio is not None else None,
            "shares_short": int(shares_short) if shares_short is not None else None,
            "float_shares": int(float_shares) if float_shares is not None else None,
            "market_cap": int(market_cap) if market_cap is not None else None,
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "short_float_pct": None,
            "days_to_cover": None,
            "shares_short": None,
            "float_shares": None,
            "market_cap": None,
            "short_data_error": str(e),
        }


def get_price_volume_data(symbol):
    try:
        data = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
            group_by="column",
            threads=False
        )

        if data.empty:
            return None, "No price/volume data returned from yfinance"

        if len(data) < 25:
            return None, f"Insufficient trading history: only {len(data)} rows"

        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"][symbol]
            volume = data["Volume"][symbol]
        else:
            close = data["Close"]
            volume = data["Volume"]

        close = close.dropna()
        volume = volume.dropna()

        if len(close) < 25 or len(volume) < 25:
            return None, "Not enough clean close/volume rows after dropna"

        last_price = safe_number(close.iloc[-1])
        last_vol = safe_number(volume.iloc[-1])

        avg_vol_5 = safe_number(volume.tail(5).mean())
        avg_vol_20 = safe_number(volume.tail(20).mean())
        vol_std_20 = safe_number(volume.tail(20).std())

        volume_ratio_5 = round(last_vol / avg_vol_5, 2) if last_vol and avg_vol_5 else None
        volume_ratio_20 = round(last_vol / avg_vol_20, 2) if last_vol and avg_vol_20 else None

        if volume_ratio_5 is not None and volume_ratio_20 is not None:
            volume_ratio = max(volume_ratio_5, volume_ratio_20)
        elif volume_ratio_5 is not None:
            volume_ratio = volume_ratio_5
        else:
            volume_ratio = volume_ratio_20

        volume_zscore_20 = None
        if last_vol is not None and avg_vol_20 and vol_std_20 and vol_std_20 > 0:
            volume_zscore_20 = round((last_vol - avg_vol_20) / vol_std_20, 2)

        ret_5d = safe_number(((close.iloc[-1] / close.iloc[-6]) - 1) * 100) if len(close) > 6 else None
        ret_20d = safe_number(((close.iloc[-1] / close.iloc[-21]) - 1) * 100) if len(close) > 21 else None

        high_20 = safe_number(close.tail(20).max())
        low_20 = safe_number(close.tail(20).min())

        pct_from_20d_high = round(((last_price / high_20) - 1) * 100, 2) if last_price and high_20 else None
        pct_from_20d_low = round(((last_price / low_20) - 1) * 100, 2) if last_price and low_20 else None

        return {
            "last_price": round(last_price, 2) if last_price is not None else None,
            "last_volume": int(last_vol) if last_vol is not None else None,
            "avg_volume_5": int(avg_vol_5) if avg_vol_5 is not None else None,
            "avg_volume_20": int(avg_vol_20) if avg_vol_20 is not None else None,
            "volume_ratio": volume_ratio,
            "volume_ratio_5": volume_ratio_5,
            "volume_ratio_20": volume_ratio_20,
            "volume_zscore_20": volume_zscore_20,
            "ret_5d_pct": round(ret_5d, 2) if ret_5d is not None else None,
            "ret_20d_pct": round(ret_20d, 2) if ret_20d is not None else None,
            "pct_from_20d_high": pct_from_20d_high,
            "pct_from_20d_low": pct_from_20d_low,
        }, None

    except Exception as e:
        return None, f"Price/volume error: {e}"


def add_float_turnover(row):
    last_volume = row.get("last_volume")
    float_shares = row.get("float_shares")

    if last_volume and float_shares and float_shares > 0:
        return round((last_volume / float_shares) * 100, 2)

    return None


def score_stock(row):
    score = 0

    short_float = row.get("short_float_pct")
    days_to_cover = row.get("days_to_cover")
    volume_ratio = row.get("volume_ratio")
    volume_zscore = row.get("volume_zscore_20")
    float_turnover = row.get("float_turnover_pct")
    ret_5d = row.get("ret_5d_pct")
    ret_20d = row.get("ret_20d_pct")
    pct_from_20d_high = row.get("pct_from_20d_high")

    if short_float is not None:
        score += min(short_float, 60) * 1.5

    if days_to_cover is not None:
        score += min(days_to_cover, 10) * 6

    if volume_ratio is not None:
        score += min(volume_ratio, 5) * 8

    if volume_zscore is not None and volume_zscore > 0:
        score += min(volume_zscore, 5) * 5

    if float_turnover is not None:
        score += min(float_turnover, 20) * 1.2

    if ret_5d is not None and ret_5d > 0:
        score += min(ret_5d, 40)

    if ret_20d is not None and ret_20d > 0:
        score += min(ret_20d, 60) * 0.5

    if pct_from_20d_high is not None and pct_from_20d_high > -5:
        score += 10

    return round(score, 1)


def pro_score_stock(row):
    score = 0

    short_float = row.get("short_float_pct")
    days_to_cover = row.get("days_to_cover")
    volume_ratio = row.get("volume_ratio")
    volume_zscore = row.get("volume_zscore_20")
    float_turnover = row.get("float_turnover_pct")
    ret_5d = row.get("ret_5d_pct")
    ret_20d = row.get("ret_20d_pct")
    pct_from_20d_high = row.get("pct_from_20d_high")

    if short_float is not None:
        if short_float >= 40:
            score += 40
        elif short_float >= 30:
            score += 30
        elif short_float >= 20:
            score += 18
        elif short_float >= 15:
            score += 10

    if days_to_cover is not None:
        if days_to_cover >= 10:
            score += 35
        elif days_to_cover >= 7:
            score += 28
        elif days_to_cover >= 5:
            score += 20
        elif days_to_cover >= 3:
            score += 10

    if volume_ratio is not None:
        if volume_ratio >= 5:
            score += 35
        elif volume_ratio >= 3:
            score += 25
        elif volume_ratio >= 2:
            score += 15
        elif volume_ratio >= 1.5:
            score += 8

    if volume_zscore is not None:
        if volume_zscore >= 3:
            score += 25
        elif volume_zscore >= 2:
            score += 15
        elif volume_zscore >= 1.5:
            score += 8

    if float_turnover is not None:
        if float_turnover >= 20:
            score += 25
        elif float_turnover >= 10:
            score += 18
        elif float_turnover >= 5:
            score += 10

    if ret_5d is not None:
        if ret_5d >= 20:
            score += 30
        elif ret_5d >= 10:
            score += 22
        elif ret_5d >= 5:
            score += 15
        elif ret_5d > 0:
            score += 6
        elif ret_5d < -5:
            score -= 10

    if ret_20d is not None:
        if ret_20d >= 30:
            score += 20
        elif ret_20d >= 15:
            score += 14
        elif ret_20d >= 5:
            score += 8
        elif ret_20d < -10:
            score -= 8

    if pct_from_20d_high is not None:
        if pct_from_20d_high >= -2:
            score += 15
        elif pct_from_20d_high >= -5:
            score += 8
        elif pct_from_20d_high < -15:
            score -= 8

    return round(score, 1)


def squeeze_rating(row):
    score = row.get("squeeze_score") or 0

    if score >= 150:
        return "🔥 EXTREME"
    elif score >= 115:
        return "HIGH"
    elif score >= 80:
        return "MEDIUM"
    elif score >= 50:
        return "LOW"
    else:
        return "WEAK"


def pro_squeeze_rating(row):
    score = row.get("pro_squeeze_score") or 0

    if score >= 150:
        return "🔥 PRO EXTREME"
    elif score >= 115:
        return "PRO HIGH"
    elif score >= 80:
        return "PRO WATCH"
    elif score >= 50:
        return "EARLY WATCH"
    else:
        return "LOW PRO SETUP"


def classify(row):
    short_float = row.get("short_float_pct") or 0
    days_to_cover = row.get("days_to_cover") or 0
    volume_ratio = row.get("volume_ratio") or 0
    volume_z = row.get("volume_zscore_20") or 0
    ret_5d = row.get("ret_5d_pct") or 0
    float_turnover = row.get("float_turnover_pct") or 0

    if short_float >= 30 and days_to_cover >= 5 and volume_ratio >= 2 and ret_5d > 5:
        return "HIGH SQUEEZE SETUP"

    if short_float >= 25 and volume_ratio >= 2.5 and ret_5d > 3:
        return "VOLUME-TRIGGERED SQUEEZE WATCH"

    if short_float >= 20 and days_to_cover >= 4:
        return "WATCHLIST"

    if short_float >= 20 and volume_z >= 2:
        return "UNUSUAL VOLUME + HIGH SHORT INTEREST"

    if volume_ratio >= 3 and float_turnover >= 5 and ret_5d > 0:
        return "MOMENTUM / RETAIL ATTENTION WATCH"

    if short_float >= 20:
        return "HIGH SHORT INTEREST"

    return "LOW / NORMAL"


def build_reason_text(row):
    reasons = []

    short_float = row.get("short_float_pct") or 0
    days_to_cover = row.get("days_to_cover") or 0
    volume_ratio = row.get("volume_ratio") or 0
    volume_z = row.get("volume_zscore_20") or 0
    ret_5d = row.get("ret_5d_pct") or 0
    float_turnover = row.get("float_turnover_pct") or 0

    if short_float >= 30:
        reasons.append("Very high short float")
    elif short_float >= 20:
        reasons.append("High short float")
    elif short_float > 0:
        reasons.append("Moderate/low short float")
    else:
        reasons.append("Short float unavailable")

    if days_to_cover >= 5:
        reasons.append("High days to cover")
    elif days_to_cover >= 3:
        reasons.append("Moderate days to cover")
    elif days_to_cover > 0:
        reasons.append("Low days to cover")
    else:
        reasons.append("Days to cover unavailable")

    if volume_ratio >= 3:
        reasons.append("Major volume spike")
    elif volume_ratio >= 2:
        reasons.append("Strong volume increase")
    elif volume_ratio >= 1.2:
        reasons.append("Slightly elevated volume")
    else:
        reasons.append("No meaningful volume spike")

    if volume_z >= 2:
        reasons.append("Statistically unusual volume")

    if float_turnover >= 10:
        reasons.append("Heavy float turnover")
    elif float_turnover >= 5:
        reasons.append("Moderate float turnover")

    if ret_5d > 5:
        reasons.append("Strong 5-day momentum")
    elif ret_5d > 0:
        reasons.append("Positive 5-day momentum")
    else:
        reasons.append("Weak/negative 5-day momentum")

    return "; ".join(reasons)


def run_screen(symbols, max_symbols=None):
    rows = []
    skipped_rows = []

    if max_symbols:
        symbols = symbols[:max_symbols]

    for symbol in symbols:
        symbol = symbol.upper().strip()
        print(f"Processing {symbol}...")

        market_data, skip_reason = get_price_volume_data(symbol)

        if market_data is None:
            print(f"SKIPPED {symbol} - {skip_reason}")
            skipped_rows.append({
                "symbol": symbol,
                "status": "SKIPPED",
                "skip_reason": skip_reason
            })
            continue

        short_data = get_short_data(symbol)
        row = {**short_data, **market_data}

        row["float_turnover_pct"] = add_float_turnover(row)

        row["squeeze_score"] = score_stock(row)
        row["squeeze_rating"] = squeeze_rating(row)

        row["pro_squeeze_score"] = pro_score_stock(row)
        row["pro_squeeze_rating"] = pro_squeeze_rating(row)

        row["signal"] = classify(row)
        row["reason"] = build_reason_text(row)
        row["status"] = "INCLUDED"
        row["scan_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        print("No candidates found.")
        pd.DataFrame(skipped_rows).to_csv("squeeze_skipped.csv", index=False)
        return df

    df = df.sort_values(by="squeeze_score", ascending=False)

    today = datetime.now().strftime("%Y-%m-%d")
    dated_file = f"short_squeeze_candidates_{today}.csv"

    df.to_csv(OUTPUT_FILE, index=False)
    df.to_csv(dated_file, index=False)

    pd.DataFrame(skipped_rows).to_csv("squeeze_skipped.csv", index=False)

    print()
    print("Top 50 Results:")
    print(df.head(50).to_string(index=False))

    print()
    print(f"Saved dashboard file to: {OUTPUT_FILE}")
    print(f"Saved dated file to: {dated_file}")
    print("Saved skipped file to: squeeze_skipped.csv")

    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Scan all listed US stocks")
    parser.add_argument("--max", type=int, help="Limit number of symbols scanned")

    args = parser.parse_args()

    symbols = get_all_us_tickers() if args.all else DEFAULT_WATCHLIST

    run_screen(symbols, max_symbols=args.max)


if __name__ == "__main__":
    main()