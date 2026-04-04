"""
SignalDesk Configuration — EXAMPLE / TEMPLATE
==============================================
Copy this to config.py and fill in your real keys.
This file is safe to commit to git (no real secrets).
"""

import json
from pathlib import Path

ROOT           = Path(__file__).parent.parent
WATCHLIST_FILE = ROOT / "data" / "watchlist.json"

DEFAULT_WATCHLIST = ["AAPL", "NVDA", "TSLA", "BTC-USD", "EURUSD=X"]

LM_STUDIO = {
    "base_url":       "http://localhost:1234/v1",
    "api_key":        "lm-studio",
    "analysis_model": "qwen2.5-14b-instruct",
    "temperature":    0.2,
    "max_tokens":     1200,
}

SETTINGS = {
    "weights": {
        "technical": 0.40,
        "sentiment": 0.35,
        "macro":     0.25,
    },
    "lookback_days":  30,
    "forecast_days":  5,
    "news_max_items": 20,
}

API_KEYS = {
    # https://fredaccount.stlouisfed.org/apikeys
    "fred": "TODO_FRED_API_KEY",

    # https://newsapi.org/register
    "newsapi": "TODO_NEWSAPI_KEY",

    # X (Twitter) API — pay-per-use
    # Get from: developer.x.com → your app → Keys and Tokens → Bearer Token
    "x_bearer_token": "TODO_X_BEARER_TOKEN",
}

PATHS = {
    "db":    ROOT / "data" / "db" / "signaldesk.db",
    "cache": ROOT / "data" / "cache",
    "logs":  ROOT / "logs",
}


def load_watchlist() -> list[str]:
    if WATCHLIST_FILE.exists():
        return json.loads(WATCHLIST_FILE.read_text())
    save_watchlist(DEFAULT_WATCHLIST)
    return DEFAULT_WATCHLIST


def save_watchlist(tickers: list[str]):
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_FILE.write_text(json.dumps(tickers, indent=2))
