import requests
import pandas as pd
import yaml
import os

with open("config.yaml") as f:
    config = yaml.safe_load(f)

ALPHA_KEY = config['alpha_vantage_key']
DATA_PATH = config['data_path']

def fetch_stock(symbol: str):
    url = f'https://www.alphavantage.co/query'
    params = {
        'function': 'TIME_SERIES_DAILY_ADJUSTED',
        'symbol': symbol,
        'apikey': ALPHA_KEY,
        'outputsize': 'full',
        'datatype': 'csv'
    }
    response = requests.get(url, params=params)
    df = pd.read_csv(pd.compat.StringIO(response.text))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    os.makedirs(DATA_PATH, exist_ok=True)
    df.to_csv(f"{DATA_PATH}{symbol}.csv")
    print(f"{symbol} data saved.")

if __name__ == "__main__":
    fetch_stock("AAPL")