"""
AI Analyst — generates narrative insight + 5-day forecast via LM Studio.
Uses Qwen2.5-14B-Instruct running locally.
Sentiment source: NewsAPI only (Reddit/StockTwits dropped).
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

SYSTEM_PROMPT = """You are an expert quantitative analyst and market strategist.
You receive structured data on a financial asset including technical indicators,
sentiment scores, macro environment, and recent news.

Your job: produce a SHORT-TERM (1–5 day) trading analysis.

Respond ONLY with valid JSON — no preamble, no markdown fences. Format:
{
  "bias": "Bullish" | "Bearish" | "Neutral",
  "conviction": "High" | "Medium" | "Low",
  "narrative": "<2–3 sentence synthesis of technical + sentiment + macro>",
  "key_risks": ["risk1", "risk2"],
  "key_catalysts": ["catalyst1", "catalyst2"],
  "forecast": [
    {"day": "D+1", "direction": "Up" | "Down" | "Flat", "magnitude": "<e.g. +0.8%>", "confidence": <int 50-85>},
    {"day": "D+2", "direction": "...", "magnitude": "...", "confidence": <int>},
    {"day": "D+3", "direction": "...", "magnitude": "...", "confidence": <int>},
    {"day": "D+4", "direction": "...", "magnitude": "...", "confidence": <int>},
    {"day": "D+5", "direction": "...", "magnitude": "...", "confidence": <int>}
  ],
  "key_levels": {
    "support": ["level1", "level2"],
    "resistance": ["level1", "level2"]
  },
  "suggested_action": "<e.g. Watch for breakout above resistance at X>"
}"""


def generate_analysis(
    ticker: str,
    price_data: dict,
    technicals: dict,
    sentiment: dict,
    macro: dict,
) -> dict:
    prompt = _build_prompt(ticker, price_data, technicals, sentiment, macro)

    log.debug(f"  Calling LM Studio analysis model for {ticker}")
    try:
        resp = client.chat.completions.create(
            model=LM_STUDIO["analysis_model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=LM_STUDIO["temperature"],
            max_tokens=LM_STUDIO["max_tokens"],
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        log.warning(f"  Analysis model returned non-JSON for {ticker}: {e}")
        return _fallback_analysis(ticker, technicals, sentiment)
    except Exception as e:
        log.error(f"  LM Studio analysis call failed for {ticker}: {e}")
        return _fallback_analysis(ticker, technicals, sentiment)


def _build_prompt(ticker, price_data, tech, sent, macro) -> str:
    price = price_data.get("current_price", "N/A")
    chg   = price_data.get("change_pct", 0)

    # Safely get news sentiment score
    news_score = sent.get("sources", {}).get("news", {})
    news_sentiment_line = (
        f"News: {news_score.get('score', 50)}/100 — {news_score.get('label', 'Neutral')}"
    )

    lines = [
        f"Asset: {ticker}",
        f"Current price: {price} (today's change: {chg:+.2f}%)",
        "",
        "=== TECHNICAL INDICATORS ===",
        f"RSI(14): {tech.get('rsi')}",
        f"MACD: {tech.get('macd')} | Signal: {tech.get('macd_signal')} | Hist: {tech.get('macd_hist')}",
        f"EMA20: {tech.get('ema20')} | EMA50: {tech.get('ema50')} | Cross: {tech.get('ema_cross')}",
        f"Bollinger position: {tech.get('bb_position')} | Width: {tech.get('bb_width')}",
        f"ATR%: {tech.get('atr_pct')} | Volume ratio vs 20d avg: {tech.get('volume_ratio')}x",
        f"Stoch K/D: {tech.get('stoch_k')}/{tech.get('stoch_d')}",
        f"Technical composite score: {tech.get('composite_score')}/100",
        "",
        "=== SENTIMENT (NewsAPI — LM Studio scored) ===",
        f"Composite sentiment score: {sent.get('composite_score')}/100 ({sent.get('label')})",
        news_sentiment_line,
        f"Key themes: {', '.join(sent.get('key_themes', []))}",
        "",
        "=== MACRO ENVIRONMENT ===",
        f"VIX: {macro.get('vix')} | DXY: {macro.get('dxy')} | US10Y: {macro.get('us10y')}%",
        f"Fed rate: {macro.get('fed_rate')}% | CPI YoY: {macro.get('cpi_yoy')}% | GDP QoQ: {macro.get('gdp_qoq')}%",
        f"S&P 500: {macro.get('sp500')} | Gold: {macro.get('gold')}",
        f"Macro composite score: {macro.get('composite_score')}/100",
    ]

    return "\n".join(lines)


def _fallback_analysis(ticker, tech, sent) -> dict:
    """Minimal fallback if LM Studio call fails."""
    score = (tech.get("composite_score", 50) + sent.get("composite_score", 50)) / 2
    bias  = "Bullish" if score >= 60 else "Bearish" if score <= 40 else "Neutral"
    return {
        "bias":       bias,
        "conviction": "Low",
        "narrative":  f"Fallback analysis — AI call failed. Tech: {tech.get('composite_score')}/100, Sentiment: {sent.get('composite_score')}/100.",
        "key_risks":        ["LM Studio unavailable"],
        "key_catalysts":    [],
        "forecast": [
            {"day": f"D+{i}", "direction": "Flat", "magnitude": "0%", "confidence": 50}
            for i in range(1, 6)
        ],
        "key_levels":       {"support": [], "resistance": []},
        "suggested_action": "Check LM Studio connection and retry.",
    }
