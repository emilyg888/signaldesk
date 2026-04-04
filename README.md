# SignalDesk

Daily morning pipeline for short-term (1–5 day) market analysis.
Runs at 7:30 AM via macOS launchd. Results served via a local FastAPI dashboard.

---

## What it does

Each morning the pipeline:
1. Fetches price + OHLCV data for every ticker in your watchlist (yfinance)
2. Computes technical indicators — RSI, MACD, EMA, Bollinger Bands, ATR, volume ratio
3. Fetches recent news headlines (NewsAPI)
4. Fetches macro indicators — Fed rate, CPI, GDP, VIX, DXY, 10Y yield (FRED + yfinance)
5. Scores sentiment from headlines using Qwen2.5 14B via LM Studio (local, free)
6. Generates a narrative analysis + 5-day forecast using the same local model
7. Stores everything to SQLite
8. Results available instantly in the dashboard at http://localhost:8000

---

## Stack

| Component | Tool | Cost |
|-----------|------|------|
| Scheduler | macOS launchd | Free |
| Price data | yfinance | Free, no key |
| Macro data | FRED API | Free |
| News | NewsAPI | Free (100 req/day) |
| AI model | LM Studio + Qwen2.5-14B-Instruct Q6_K | Free, local |
| Database | SQLite | Free |
| Backend | FastAPI + uvicorn | Free |

Monthly cost: ~$0

---

## Requirements

- macOS (Apple Silicon M-series recommended)
- Python 3.12 (via conda `dev` environment)
- LM Studio with Qwen2.5-14B-Instruct Q6_K loaded
- FRED API key (free)
- NewsAPI key (free)

---

## Installation

**1. Clone / unzip into your projects folder**
```bash
cd ~/LocalDocuments/Projects
# unzip signaldesk.zip here
cd signaldesk
```

**2. Create venv using Python 3.12**
```bash
~/miniconda3/envs/dev/bin/python -m venv .venv
source .venv/bin/activate
python --version  # must show 3.12.x
```

**3. Install dependencies**
```bash
pip install --upgrade pip
pip install yfinance pandas pandas-ta requests openai fastapi praw fredapi newsapi-python python-dotenv
pip install "uvicorn[standard]"
```

**4. Configure API keys**
```bash
cp pipeline/config.example.py pipeline/config.py
code pipeline/config.py   # paste your FRED and NewsAPI keys
```

**5. Set LM Studio model name**

In `pipeline/config.py`, set `analysis_model` to match the model name
shown in LM Studio's Local Server tab exactly (without the .gguf extension):
```python
"analysis_model": "qwen2.5-14b-instruct",
```

**6. Verify everything works**
```bash
python test_keys.py
```
Expected output:
```
✓ yfinance — AAPL: $xxx.xx
✓ FRED — Fed rate: x.xx%
✓ NewsAPI — found xxx articles
✓ LM Studio — working
```

**7. Run the pipeline manually**
```bash
python pipeline/run_pipeline.py
```

**8. Start the dashboard**
```bash
uvicorn api.server:app --reload --port 8000
```
Open http://localhost:8000

---

## Schedule with launchd (7:30 AM daily)

```bash
# Edit paths in the plist first
nano scheduler/com.signaldesk.pipeline.plist

# Install
cp scheduler/com.signaldesk.pipeline.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.signaldesk.pipeline.plist

# Verify
launchctl list | grep signaldesk

# Test fire immediately
launchctl start com.signaldesk.pipeline

# Watch the log
tail -f logs/pipeline.log
```

> LM Studio must be running at 7:30 AM. Add it to Login Items and enable
> auto-start server so it's ready when launchd fires.

---

## Project structure

```
signaldesk/
├── .venv/                          # Python 3.12 venv (not committed)
├── .gitignore
├── .vscode/settings.json           # VS Code interpreter → .venv
├── pipeline/
│   ├── config.py                   # API keys + settings (not committed)
│   ├── config.example.py           # Safe template to commit
│   ├── run_pipeline.py             # Main orchestrator
│   ├── data_fetcher.py             # yfinance prices + FRED macro
│   ├── technical.py                # RSI, MACD, EMA, BB, ATR, volume
│   ├── sentiment.py                # LM Studio sentiment scoring
│   ├── news_fetcher.py             # NewsAPI + yfinance fallback
│   ├── social_fetcher.py           # Stub (extensible for future sources)
│   ├── ai_analyst.py               # LM Studio narrative + forecast
│   └── storage.py                  # SQLite read/write
├── api/
│   └── server.py                   # FastAPI backend
├── dashboard/
│   └── index.html                  # Frontend (served by FastAPI)
├── scheduler/
│   └── com.signaldesk.pipeline.plist  # launchd config
├── data/
│   ├── db/                         # SQLite database (not committed)
│   ├── cache/                      # Cached responses (not committed)
│   └── watchlist.json              # Your ticker list
├── logs/                           # Pipeline logs (not committed)
├── test_keys.py                    # Verify all integrations
└── requirements.txt
```

---

## Watchlist format

Edit `data/watchlist.json` or use the dashboard:
```json
["AAPL", "NVDA", "TSLA", "BTC-USD", "EURUSD=X"]
```

Supported formats:
- US stocks: `AAPL`, `NVDA`, `MSFT`, `TSLA`
- Crypto: `BTC-USD`, `ETH-USD`, `SOL-USD`
- FX pairs: `EURUSD=X`, `GBPUSD=X`, `JPY=X`

---

## LM Studio settings (recommended)

Model: Qwen2.5-14B-Instruct Q6_K (official Qwen release)

| Setting | Value |
|---------|-------|
| Context Length | 16384 |
| GPU Offload | 48 (all layers) |
| CPU Thread Pool | 10 |
| Eval Batch Size | 256 |
| Max Concurrent Predictions | 1 |
| Unified KV Cache | ON |
| Offload KV Cache to GPU | ON |
| Keep Model in Memory | ON |

---

## Troubleshooting

**LM Studio not responding**
```bash
curl http://localhost:1234/v1/models
```
If no response, open LM Studio → Local Server tab → Start Server.

**yfinance errors**
```bash
pip install --upgrade yfinance
```

**launchd not firing**
```bash
cat logs/launchd_stderr.log
launchctl list | grep signaldesk
```
Check Python path with `which python` after activating venv.

**FRED / NewsAPI errors**
Re-check keys in `pipeline/config.py` — FRED key must be exactly 32 lowercase alphanumeric characters.
