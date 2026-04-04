# SignalDesk — Architecture

## Overview
## What Was Built

| What | How |
|------|-----|
| Daily scheduler | launchd fires at 7:30 AM |
| Price + OHLCV | yfinance (free) |
| Macro indicators | FRED API (free) |
| News headlines | NewsAPI (free) |
| Technical analysis | pandas-ta — RSI, MACD, EMA, BB, ATR, Stochastic |
| Sentiment scoring | Qwen2.5 14B via LM Studio (local, free) |
| AI narrative + forecast | Qwen2.5 14B via LM Studio (local, free) |
| Storage | SQLite with duplicate-safe daily upsert |
| Backend | FastAPI on localhost:8000 |
| Dashboard | Dark terminal UI — overview, detail, macro, watchlist |
| Tests | 98/98 unit + integration tests passing |
| Git | Committed to GitHub, API keys excluded |

## Daily Routine

- Mac wakes at 7:30 AM → launchd fires the pipeline automatically
- LM Studio must be running with server started (add to Login Items)
- Open `http://localhost:8000` anytime to see the latest analysis
- Run `python -m pytest tests/ -v` after any code changes to verify nothing broke

```
                        ┌─────────────────────────────────┐
                        │   macOS launchd  (7:30 AM)      │
                        │   com.signaldesk.pipeline.plist  │
                        └────────────┬────────────────────┘
                                     │ triggers
                                     ▼
                        ┌─────────────────────────────────┐
                        │   run_pipeline.py               │
                        │   Main orchestrator             │
                        └──┬──────┬───────┬──────┬───────┘
                           │      │       │      │
              ┌────────────┘  ┌───┘   ┌───┘  ┌──┘
              ▼               ▼       ▼       ▼
    ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │data_fetcher  │  │technical │  │news_     │  │data_fetcher  │
    │.py           │  │.py       │  │fetcher.py│  │.py           │
    │              │  │          │  │          │  │(macro)       │
    │yfinance      │  │pandas-ta │  │NewsAPI   │  │FRED API      │
    │Price/OHLCV   │  │RSI,MACD  │  │headlines │  │yfinance      │
    │30d history   │  │EMA,BB    │  │20/ticker │  │VIX,DXY,10Y   │
    └──────┬───────┘  │ATR,Vol   │  └────┬─────┘  └──────┬───────┘
           │          └────┬─────┘       │                │
           │               │             ▼                │
           │               │    ┌──────────────┐          │
           │               │    │sentiment.py  │          │
           │               │    │              │          │
           │               │    │LM Studio     │          │
           │               │    │Qwen2.5 14B   │          │
           │               │    │localhost:1234│          │
           │               │    │              │          │
           │               │    │News → score  │          │
           │               │    │0–100 + themes│          │
           │               │    └──────┬───────┘          │
           │               │           │                  │
           └───────────────┴─────┬─────┴──────────────────┘
                                 │ all signals
                                 ▼
                    ┌────────────────────────┐
                    │    ai_analyst.py       │
                    │                        │
                    │    LM Studio           │
                    │    Qwen2.5 14B         │
                    │    localhost:1234      │
                    │                        │
                    │  Input: tech scores +  │
                    │  sentiment + macro     │
                    │                        │
                    │  Output: narrative +   │
                    │  5-day forecast +      │
                    │  key levels + risks    │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    storage.py          │
                    │    SQLite              │
                    │    data/db/            │
                    │    signaldesk.db       │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    api/server.py       │
                    │    FastAPI             │
                    │    localhost:8000      │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    dashboard/          │
                    │    index.html          │
                    │    Browser UI          │
                    └────────────────────────┘
```

---

## Data flow per ticker

```
yfinance (price)  ──►  technical.py  ──►  composite tech score (0–100)
                                                          │
NewsAPI (news)    ──►  sentiment.py  ──►  sentiment score (0–100)
                       (LM Studio)                        │
                                                          │
FRED + yfinance   ──►  macro score   ──►  macro score (0–100)
(macro)                                                   │
                                                          ▼
                                           Weighted aggregate score
                                           40% tech + 35% sent + 25% macro
                                                          │
                                                          ▼
                                              ai_analyst.py
                                              (LM Studio Qwen2.5 14B)
                                                          │
                                                          ▼
                                           ┌──────────────────────────┐
                                           │ bias + conviction        │
                                           │ narrative (2–3 sentences)│
                                           │ 5-day forecast           │
                                           │ key support/resistance   │
                                           │ risks + catalysts        │
                                           └──────────────────────────┘
```

---

## File responsibilities

| File | Responsibility |
|------|---------------|
| `pipeline/run_pipeline.py` | Orchestrates the full pipeline for each ticker |
| `pipeline/config.py` | All settings, API keys, model config (gitignored) |
| `pipeline/config.example.py` | Safe template for version control |
| `pipeline/data_fetcher.py` | yfinance price/OHLCV + FRED/yfinance macro data |
| `pipeline/technical.py` | RSI, MACD, EMA cross, Bollinger Bands, ATR, volume |
| `pipeline/news_fetcher.py` | NewsAPI headlines with yfinance fallback |
| `pipeline/social_fetcher.py` | Stub — extensible for future social sources |
| `pipeline/sentiment.py` | LM Studio sentiment scoring from news headlines |
| `pipeline/ai_analyst.py` | LM Studio narrative generation + 5-day forecast |
| `pipeline/storage.py` | SQLite schema, read/write, history queries |
| `api/server.py` | FastAPI REST endpoints for dashboard |
| `dashboard/index.html` | Browser frontend |
| `scheduler/com.signaldesk.pipeline.plist` | macOS launchd config (7:30 AM) |

---

## External services

| Service | URL | Auth | Purpose |
|---------|-----|------|---------|
| yfinance | Yahoo Finance | None | Price, OHLCV, basic news |
| FRED | api.stlouisfed.org | API key (free) | Fed rate, CPI, GDP |
| NewsAPI | newsapi.org | API key (free) | News headlines |
| LM Studio | localhost:1234 | None (local) | AI analysis + sentiment |

Twitter/X, Reddit, StockTwits — evaluated and dropped (paid or network-blocked).

---

## Machine specs (Emily's setup)

| Component | Spec |
|-----------|------|
| Mac | MacBook Pro M5 |
| RAM | 32 GB unified memory |
| Python | 3.12.12 (via miniconda `dev` env) |
| venv | `.venv` at project root |
| Model | Qwen2.5-14B-Instruct Q6_K (~12.1GB) |
| Model host | LM Studio (localhost:1234) |
| DB | SQLite at `data/db/signaldesk.db` |
| Project root | `~/LocalDocuments/Projects/signaldesk/` |

---

## Aggregate score formula

```
aggregate_score = round(
    technical_score  × 0.40 +
    sentiment_score  × 0.35 +
    macro_score      × 0.25
)
```

Score interpretation:
- 0–40: Bearish
- 41–59: Neutral
- 60–100: Bullish
