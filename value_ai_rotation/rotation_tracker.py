from yahooquery import Ticker
import pandas as pd

AI_TICKERS = ["NVDA", "MSFT", "META", "AMD", "AVGO", "SMH", "QQQ", "XLK"]
VALUE_TICKERS = ["VTV", "SCHV", "IWD", "VLUE", "XLF", "XLE", "XLU", "XLP"]


def get_returns(tickers, period="6mo"):
    data = {}

    for ticker in tickers:
        print(f"Downloading {ticker}...")
        hist = Ticker(ticker).history(period=period)

        if hist.empty:
            continue

        if isinstance(hist.index, pd.MultiIndex):
            hist = hist.reset_index()

        hist["date"] = pd.to_datetime(hist["date"])
        hist = hist.sort_values("date")

        close = hist["close"]
        ret_5 = close.pct_change(5).iloc[-1]
        ret_20 = close.pct_change(20).iloc[-1]
        ret_60 = close.pct_change(60).iloc[-1]

        data[ticker] = {
            "ret_5": ret_5,
            "ret_20": ret_20,
            "ret_60": ret_60,
        }

    return pd.DataFrame(data).T


def score_group(df):
    return (
        df["ret_5"].mean() * 0.25 +
        df["ret_20"].mean() * 0.35 +
        df["ret_60"].mean() * 0.40
    )


def main():
    ai = get_returns(AI_TICKERS)
    value = get_returns(VALUE_TICKERS)

    ai_score = score_group(ai)
    value_score = score_group(value)
    spread = value_score - ai_score

    print("\n=== AI / Growth Basket ===")
    print(ai)

    print("\n=== Value / Defensive Basket ===")
    print(value)

    print("\n=== Rotation Summary ===")
    print(f"AI Score:    {ai_score:.2%}")
    print(f"Value Score: {value_score:.2%}")
    print(f"Spread:      {spread:.2%}")

    if spread > 0.02:
        signal = "VALUE ROTATION"
    elif spread < -0.02:
        signal = "AI LEADERSHIP"
    else:
        signal = "NEUTRAL / MIXED"

    print(f"Signal:      {signal}")


if __name__ == "__main__":
    main()