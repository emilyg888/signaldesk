"""
SignalDesk — Daily Morning Pipeline
Runs at 7:30 AM via launchd
Collects data → scores sentiment → generates AI analysis → stores to SQLite

Data sources:
  - yfinance        : price / OHLCV (free, no key)
  - FRED            : macro indicators (free API key)
  - NewsAPI         : news headlines for sentiment (free API key)
  - LM Studio       : local AI for sentiment scoring + analysis (free, local)
  - SQLite          : local storage (free, no setup)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.config import load_watchlist, SETTINGS
from pipeline.data_fetcher import fetch_price_data, fetch_macro_data
from pipeline.technical import compute_technicals
from pipeline.sentiment import score_sentiment
from pipeline.news_fetcher import fetch_news
from pipeline.social_fetcher import fetch_social
from pipeline.ai_analyst import generate_analysis
from pipeline.storage import save_run, init_db
from pipeline.notifier import send_whatsapp_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "logs" / "pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def run():
    log.info("=" * 60)
    log.info(f"SignalDesk pipeline starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)

    init_db()
    watchlist = load_watchlist()
    log.info(f"Watchlist: {watchlist}")

    results = []
    for ticker in watchlist:
        log.info(f"\n--- Processing {ticker} ---")
        try:
            result = process_ticker(ticker)
            results.append(result)
            save_run(result)
            log.info(f"✓ {ticker} complete — aggregate score: {result['aggregate_score']}")
        except Exception as e:
            log.error(f"✗ {ticker} failed: {e}", exc_info=True)

    log.info(f"\nPipeline complete. {len(results)}/{len(watchlist)} tickers processed.")
    send_whatsapp_summary(results)
    return results


def process_ticker(ticker: str) -> dict:
    # 1. Price + OHLCV
    log.info(f"  Fetching price data...")
    price_data = fetch_price_data(ticker)

    # 2. Technical indicators
    log.info(f"  Computing technical indicators...")
    technicals = compute_technicals(price_data)

    # 3. News headlines
    log.info(f"  Fetching news...")
    news_items = fetch_news(ticker)

    # 4. Social sentiment (StockTwits stub — returns empty, NewsAPI is primary)
    log.info(f"  Fetching social sentiment...")
    social_posts = fetch_social(ticker)

    # 5. Macro snapshot (fetched once per day via FRED + yfinance)
    log.info(f"  Loading macro data...")
    macro = fetch_macro_data()

    # 6. Sentiment scoring via LM Studio (news-driven)
    log.info(f"  Scoring sentiment (LM Studio)...")
    sentiment = score_sentiment(news_items, social_posts, ticker)

    # 7. AI analysis + forecast via LM Studio (Qwen2.5 14B)
    log.info(f"  Generating AI analysis (LM Studio)...")
    analysis = generate_analysis(ticker, price_data, technicals, sentiment, macro)

    # 8. Aggregate score — weighted: 40% technical, 35% sentiment, 25% macro
    aggregate_score = round(
        technicals["composite_score"] * SETTINGS["weights"]["technical"]
        + sentiment["composite_score"] * SETTINGS["weights"]["sentiment"]
        + macro["composite_score"] * SETTINGS["weights"]["macro"]
    )

    return {
        "ticker":          ticker,
        "run_date":        datetime.now().isoformat(),
        "price_data":      price_data,
        "technicals":      technicals,
        "sentiment":       sentiment,
        "macro":           macro,
        "news":            news_items,
        "social":          social_posts,
        "analysis":        analysis,
        "aggregate_score": aggregate_score,
    }


if __name__ == "__main__":
    run()
