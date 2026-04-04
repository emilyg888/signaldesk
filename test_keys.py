import sys

# Test yfinance
try:
    import yfinance as yf
    price = yf.Ticker("AAPL").fast_info["lastPrice"]
    print(f"✓ yfinance — AAPL: ${price:.2f}")
except Exception as e:
    print(f"✗ yfinance failed: {e}")

# Test FRED
try:
    from fredapi import Fred
    fred = Fred(api_key="ad932311e0553ef2d6f204f3f61aff53")
    rate = fred.get_series("FEDFUNDS").iloc[-1]
    print(f"✓ FRED — Fed rate: {rate}%")
except Exception as e:
    print(f"✗ FRED failed: {e}")

# Test NewsAPI
try:
    from newsapi import NewsApiClient
    api = NewsApiClient(api_key="04acd06fd9374e1e84129f5f7035b538")
    articles = api.get_everything(q="AAPL", page_size=1)
    print(f"✓ NewsAPI — found {articles['totalResults']} articles")
except Exception as e:
    print(f"✗ NewsAPI failed: {e}")

# Test StockTwits
try:
    import requests
    resp = requests.get("https://api.stocktwits.com/api/2/streams/symbol/AAPL.json", timeout=10)
    count = len(resp.json().get("messages", []))
    print(f"✓ StockTwits — {count} messages for AAPL")
except Exception as e:
    print(f"✗ StockTwits failed: {e}")

# Test LM Studio
try:
    from openai import OpenAI
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    resp = client.chat.completions.create(
        model="qwen2.5-14b-instruct",
        messages=[{"role": "user", "content": "Reply with just the word: working"}],
        max_tokens=10
    )
    print(f"✓ LM Studio — {resp.choices[0].message.content.strip()}")
except Exception as e:
    print(f"✗ LM Studio failed: {e}")
