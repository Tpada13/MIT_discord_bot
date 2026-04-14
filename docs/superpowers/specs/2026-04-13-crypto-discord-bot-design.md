# Crypto Analysis Discord Bot — Design Spec
**Date:** 2026-04-13
**Status:** Approved

---

## Overview

A new Discord bot (replacing `mybot.py`) that provides cryptocurrency market data, technical analysis, and AI-powered forecasting via Discord slash commands. Built with discord.py, CoinGecko's free API, pandas-ta for indicators, and Claude (Anthropic) as the analyst LLM.

Runs locally for now. Architecture is designed to expand to additional data sources (Binance, sentiment feeds, news) without modifying existing code.

---

## Project Structure

```
MIT_discord_bot/
├── bot.py                    # Entry point — loads cogs, starts bot
├── config.py                 # Supported coins list, default timeframes
├── .env                      # DISCORD_TOKEN, ANTHROPIC_API_KEY
├── requirements.txt          # Updated dependencies
├── CLAUDE.md                 # Project-level git workflow rules
├── cogs/
│   └── crypto.py             # All slash commands (/price, /analyze, /forecast, /help)
└── services/
    ├── coingecko.py          # CoinGecko API client (price, OHLCV history)
    ├── indicators.py         # RSI, SMA, EMA calculations via pandas-ta
    └── claude_analyst.py     # Formats data + calls Claude API for forecast
```

---

## Slash Commands

All commands use Discord's native slash command system.

### `/price <coin> [timeframe]`
- Returns current price, % change over timeframe, market cap, 24h volume
- `timeframe` options: `1h`, `24h`, `3d`, `7d`
- Default timeframe: `24h`
- Example: `/price BTC 3d`

### `/analyze <coin> [timeframe]`
- Returns price summary + technical indicators: RSI-14, SMA-20, SMA-50, EMA-12, EMA-26, volume trend
- `timeframe` options: `7d`, `30d`, `90d`, `180d`
- Default timeframe: `30d`
- Example: `/analyze ETH 90d`

### `/forecast <coin> [timeframe]`
- Returns a Claude-generated structured analyst report (see Forecast Format below)
- `timeframe` options: `7d`, `30d`, `90d`, `180d`
- Default timeframe: `30d`
- Example: `/forecast SOL 60d`

### `/help`
- Returns list of all commands with descriptions and the full supported coin list

---

## Supported Coins

Default list (all can be passed as tickers to any command):

`BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, XDC, LINK, SUI, ZRO, ONDO, CRV, SEI`

Any ticker not on this list will be attempted via CoinGecko. If the lookup fails, the bot returns a friendly error and shows the supported list.

---

## Data Flow

### `/price` and `/analyze`
```
User command → cogs/crypto.py (validate + defer)
             → services/coingecko.py (fetch price + OHLCV)
             → services/indicators.py (calculate RSI, SMA, EMA)  [/analyze only]
             → Discord embed response
```

### `/forecast`
```
User command → cogs/crypto.py (validate + defer)
             → services/coingecko.py (fetch OHLCV)
             → services/indicators.py (calculate indicators)
             → services/claude_analyst.py (build prompt + call Claude API)
             → Discord embed response
```

**Latency handling:** All commands defer immediately (Discord shows a loading state) to stay within Discord's 3-second response window. The follow-up is sent once data and/or Claude response is ready.

**Rate limits:** CoinGecko free tier supports ~30 calls/min — sufficient for local personal use.

---

## Technical Indicators

Calculated via `pandas-ta` from CoinGecko OHLCV data:

| Indicator | Parameters | Purpose |
|-----------|-----------|---------|
| RSI | 14-period | Momentum / overbought-oversold |
| SMA | 20 and 50-period | Trend direction |
| EMA | 12 and 26-period | Short-term momentum |
| Volume | Trend vs average | Confirms price moves |

---

## Forecast Report Format

Claude is prompted to respond as a senior financial analyst. Output structure:

```
**<COIN> — Senior Analyst Forecast** (based on <timeframe> data)

**Summary**
2–3 sentence market overview.

**Key Signals**
- Bullet list of notable indicator readings

**Risk Factors**
- Bullet list of key downside risks

**Price Target**
Short-term (7–14d): $X,XXX – $X,XXX

**Recommendation**
HOLD / BUY / SELL — one-line rationale

**Analyst Commentary**
2–3 sentence narrative conclusion in plain English.

---
⚠️ This is not financial advice. Crypto markets are highly volatile.
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `discord.py` | Discord bot framework, slash command support |
| `anthropic` | Claude API client |
| `python-dotenv` | Load `.env` variables |
| `requests` | CoinGecko HTTP calls |
| `pandas` | OHLCV data manipulation |
| `pandas-ta` | Technical indicator calculations |

---

## Future Expansion Points

The service layer is designed so these can be added without touching existing code:

- `services/sentiment.py` — Alternative.me Fear & Greed Index (free), CryptoPanic news (free tier)
- `services/binance.py` — OHLCV data from Binance for higher-fidelity technical analysis
- `cogs/portfolio.py` — New command group for portfolio tracking
- Cloud deployment — `bot.py` has no local-only dependencies; can be containerized and deployed to Railway/Render

---

## Git Workflow (MANDATORY)

- Every implementation chunk gets its own feature branch: `feature/<task-id>-<short-description>`
- Well-documented commits with subject line + body explaining why
- After each branch: push and prompt user to create a PR targeting `main`
- Never batch unrelated work onto one branch
