"""
Sentiment scoring using LM Studio (local, free).
Scores news headlines via Qwen2.5 14B running in LM Studio.
Primary source: NewsAPI headlines (100% weighting).
Social sources (StockTwits, Reddit) dropped — blocked by Cloudflare/network.
"""

import logging
import json
from openai import OpenAI
from pipeline.config import LM_STUDIO

log = logging.getLogger(__name__)

client = OpenAI(
    base_url=LM_STUDIO["base_url"],
    api_key=LM_STUDIO["api_key"],
)

SYSTEM_PROMPT = """You are a financial sentiment analyser.
Given a list of news headlines about a financial asset, score the overall sentiment.
Respond ONLY with valid JSON — no preamble, no markdown fences.
Format: {"score": <int 0-100>, "label": "<Bearish|Neutral|Bullish>", "key_themes": ["theme1","theme2"]}
Where 0=extremely bearish, 50=neutral, 100=extremely bullish."""


def score_sentiment(news_items: list, social_posts: list, ticker: str) -> dict:
    """
    Score sentiment from news headlines via LM Studio.
    social_posts accepted for interface compatibility but not used.
    """
    news_score = _score_batch(news_items, "headline", ticker, "news")
    composite  = news_score["score"]
    label      = "Bullish" if composite >= 60 else "Bearish" if composite <= 40 else "Neutral"

    return {
        "composite_score": composite,
        "label":           label,
        "sources":         {"news": news_score},
        "key_themes":      news_score.get("key_themes", []),
    }


def _score_batch(items: list, text_field: str, ticker: str, source_name: str) -> dict:
    if not items:
        log.warning(f"  No {source_name} items to score for {ticker}")
        return {"score": 50, "label": "Neutral", "key_themes": []}

    texts = [item.get(text_field, "") for item in items[:20] if item.get(text_field)]
    if not texts:
        return {"score": 50, "label": "Neutral", "key_themes": []}

    texts_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    user_msg    = f"Asset: {ticker}\nSource: {source_name}\n\nHeadlines:\n{texts_block}"

    log.debug(f"  Scoring {len(texts)} {source_name} items for {ticker}")

    try:
        resp = client.chat.completions.create(
            model=LM_STUDIO["analysis_model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw    = resp.choices[0].message.content.strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        return {
            "score":      int(parsed.get("score", 50)),
            "label":      parsed.get("label", "Neutral"),
            "key_themes": parsed.get("key_themes", []),
        }

    except json.JSONDecodeError as e:
        log.warning(f"  LM Studio returned non-JSON for {source_name}/{ticker}: {e}")
        return {"score": 50, "label": "Neutral", "key_themes": []}
    except Exception as e:
        log.error(f"  LM Studio call failed for {source_name}/{ticker}: {e}")
        return {"score": 50, "label": "Neutral", "key_themes": []}
