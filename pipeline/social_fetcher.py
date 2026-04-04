"""
Social sentiment fetcher — stub.
StockTwits blocked via Cloudflare; Reddit registration blocked by network.
NewsAPI (275+ articles/query) provides sufficient sentiment signal.
Kept as stub so pipeline architecture remains extensible.
"""

import logging
log = logging.getLogger(__name__)


def fetch_social(ticker: str) -> list[dict]:
    """Returns empty list — NewsAPI is the active sentiment source."""
    log.debug(f"  Social fetch skipped for {ticker} — using NewsAPI sentiment only")
    return []
