# Feature Roadmap — MIT Crypto Discord Bot

> **For a fresh session:** Read this section first, then pick up from the Implementation Order table to find the next unbuilt feature.
>
> **Repo:** https://github.com/Tpada13/MIT_discord_bot  
> **Clone:** `git clone https://github.com/Tpada13/MIT_discord_bot.git && cd MIT_discord_bot`  
> **Install:** `pip install -r requirements.txt`  
> **Run tests:** `pytest` (all tests must pass before and after each feature)  
> **Run bot:** `python bot.py` (requires `.env` — see README.md for env var details)
>
> **Workflow:**
> 1. Check the Implementation Order table below for the next feature (lowest task number not yet on `main`).
> 2. Create a feature branch: `git checkout -b feature/task-<N>-<short-description>` from `main`.
> 3. Implement the feature as specified in its section below.
> 4. Run `pytest` — all tests must pass.
> 5. Push the branch and create a PR targeting `main`. Tag the user for review before merging.
>
> **Key files to understand first:**
> - `bot.py` — entry point; loads cogs and instantiates services
> - `cogs/crypto.py` — all current slash commands
> - `services/coingecko.py` — CoinGecko API client
> - `services/indicators.py` — RSI, SMA, EMA calculations
> - `services/claude_analyst.py` — Anthropic Claude forecast generation
> - `config.py` — supported coins, timeframes, Claude prompt constants
> - `README.md` — setup and project structure overview

**Date:** 2026-04-15  
**Status:** Approved for implementation  
**Branch convention:** `feature/task-<N>-<short-description>`

---

## Overview

This document specifies 7 planned features for the MIT Crypto Discord Bot, ordered from simplest to most complex. Each feature is a self-contained unit with its own branch, spec, and implementation plan. Build them in order — later features depend on patterns established by earlier ones.

**Current bot state (as of this doc):**
- Commands: `/price`, `/analyze`, `/forecast`, `/help`
- Services: `CoinGeckoClient`, `calculate_indicators`, `ClaudeAnalyst`
- No persistence layer yet (all stateless)
- Entry point: `bot.py` → loads `cogs/crypto.py`

---

## Feature 1: `/compare <coin1> <coin2>`

### What it does
Side-by-side technical comparison of two supported coins. Shows price, % change, RSI, SMA20, EMA12, volume trend, and a Claude "which looks stronger" verdict.

### Command signature
```
/compare <coin1> <coin2> [timeframe]
```
- `coin1`, `coin2`: coin tickers from `SUPPORTED_COINS`
- `timeframe`: `7d`, `30d`, `90d`, `180d` (default: `30d`) — same choices as `/analyze`

### Implementation
- **No new files.** Add command to `cogs/crypto.py`.
- Fetch `get_price_data()` and `get_market_chart()` for both coins in parallel (two separate calls — CoinGecko free tier has no batch endpoint).
- Run `calculate_indicators()` for both.
- Call `ClaudeAnalyst.generate_forecast()` for both coins, then ask Claude to compare them in a second call — OR add a new `compare_coins()` method to `ClaudeAnalyst` that takes both coins' data and returns a single verdict sentence.
- Respond with a Discord embed: two columns (one per coin) using inline fields, verdict at the bottom.

### New method on ClaudeAnalyst
```python
def compare_coins(
    self,
    coin_a: str, data_a: dict, indicators_a: dict,
    coin_b: str, data_b: dict, indicators_b: dict,
) -> str:
    """Returns a 1-2 sentence verdict on which coin looks stronger."""
```
Prompt: feed both coins' metrics and ask for a concise comparative verdict.

### Error handling
- If either coin lookup fails, return an error embed identifying which coin failed.
- If Claude comparison fails, fall back to showing the raw side-by-side data without the verdict.

### Tests
- Unit test `compare_coins()` with mocked Anthropic client.
- Test embed formatting logic with fixture data.

---

## Feature 2: `/market`

### What it does
Snapshot of all supported coins sorted by 24h % change — biggest gainers at top, biggest losers at bottom.

### Command signature
```
/market
```
No parameters.

### Implementation
- **No new files.** Add command to `cogs/crypto.py`.
- Loop over all keys in `SUPPORTED_COINS`, call `get_price_data(coin, "24h")` for each.
- Sort results by `price_change_pct` descending.
- Respond with a single embed. Each coin is one line: `BTC  $84,231.00  ▲ 2.14%`. Use a code block for alignment.
- Cap the embed field at Discord's 1024-char field limit — with 15 coins this will fit comfortably.

### Performance note
15 sequential CoinGecko calls will be slow (~3-5s on free tier). Defer the interaction immediately (`await interaction.response.defer()`). Consider adding a brief "Fetching market data..." message. Do not parallelize — CoinGecko free tier rate-limits aggressively.

### Error handling
- If a coin fails, include it in the output as `BTC  —  (unavailable)` rather than aborting the whole command.

### Tests
- Test sorting logic.
- Test truncation/formatting with 15 coins of fixture data.

---

## Feature 3: Fear & Greed Index (`/feargreed`)

### What it does
Shows the current Crypto Fear & Greed Index from Alternative.me — a 0-100 score with a classification (Extreme Fear / Fear / Neutral / Greed / Extreme Greed) and the previous day's value for context.

### Command signature
```
/feargreed
```
No parameters.

### New file: `services/fear_greed.py`
```python
class FearGreedClient:
    BASE_URL = "https://api.alternative.me/fng/"

    def get_current(self) -> dict:
        """
        Returns:
            {
                "value": int,           # 0-100
                "classification": str,  # "Extreme Fear" | "Fear" | "Neutral" | "Greed" | "Extreme Greed"
                "timestamp": str,       # ISO date string
                "previous_value": int,
                "previous_classification": str,
            }
        """
```
- Call `GET https://api.alternative.me/fng/?limit=2` — returns today and yesterday.
- No API key required.
- Raises `RuntimeError` on HTTP error or malformed response.

### Embed design
- Color: red for Fear/Extreme Fear, gray for Neutral, green for Greed/Extreme Greed.
- Fields: Score, Classification, Previous Day (score + classification), timestamp.

### Wiring
- Instantiate `FearGreedClient` in `bot.py` alongside `CoinGeckoClient` and `ClaudeAnalyst`.
- Pass into `CryptoCog.__init__()` — update the constructor signature.
- Register the new command in `cogs/crypto.py`.

### Tests
- Unit test `FearGreedClient.get_current()` with a mocked HTTP response.
- Test color selection logic for each classification bucket.

---

## Feature 4: Price Charts (`/chart`)

### What it does
Generates and attaches a price + volume chart image for a coin over a chosen timeframe. Returns a PNG file attached to the Discord message.

### Command signature
```
/chart <coin> [timeframe]
```
- `timeframe`: `7d`, `30d`, `90d`, `180d` (default: `30d`)

### Dependencies
Add to `requirements.txt`:
```
matplotlib
```

### New file: `services/chart.py`
```python
def generate_price_chart(
    ticker: str,
    close_prices: list[float],
    volumes: list[float],
    timeframe: str,
) -> bytes:
    """
    Renders a two-panel matplotlib figure (price line + volume bar)
    and returns PNG bytes (suitable for discord.File).
    """
```
- Top panel: price line chart with SMA20 overlay (calculate inline, no pandas-ta needed for a simple rolling mean).
- Bottom panel: volume bar chart.
- Dark background (`plt.style.use('dark_background')`) to suit Discord's dark theme.
- Return `bytes` from `BytesIO` — do not write to disk.

### In the command handler
```python
chart_bytes = generate_price_chart(coin, chart["close_prices"], chart["volumes"], tf)
file = discord.File(fp=io.BytesIO(chart_bytes), filename=f"{coin}_{tf}_chart.png")
await interaction.followup.send(file=file, embed=embed)
```
The embed (price + indicators) and the chart image are sent together in one message.

### Tests
- Test that `generate_price_chart()` returns non-empty bytes.
- Test that the function doesn't raise with minimal (7-day) data.
- No visual regression tests — keep it simple.

---

## Feature 5: Watchlist (`/watch`)

### What it does
Per-user watchlist. Users add coins they care about; `/watch show` runs a mini market snapshot across their watchlist coins.

### Commands
```
/watch add <coin>     — add a coin to the user's watchlist
/watch remove <coin>  — remove a coin
/watch show           — show current prices for all watchlist coins
/watch clear          — remove all coins from the watchlist
```

### Persistence layer
**New directory:** `data/` (add `data/` to `.gitignore`, create `data/.gitkeep`)

**New file: `services/watchlist.py`**
```python
WATCHLIST_PATH = Path("data/watchlists.json")

class WatchlistService:
    def add(self, user_id: int, coin: str) -> None: ...
    def remove(self, user_id: int, coin: str) -> None: ...
    def get(self, user_id: int) -> list[str]: ...
    def clear(self, user_id: int) -> None: ...
```
Storage format:
```json
{
  "123456789": ["BTC", "ETH", "SOL"],
  "987654321": ["DOGE"]
}
```
- Read/write JSON on every call (file is tiny; no in-memory cache needed).
- Cap watchlist at 10 coins per user — return a user-facing error if exceeded.
- Only allow coins present in `SUPPORTED_COINS`.

### New cog: `cogs/watchlist.py`
- Separate cog to keep `cogs/crypto.py` focused.
- Load in `bot.py` alongside `cogs.crypto`.
- Constructor takes `WatchlistService` and `CoinGeckoClient`.

### Tests
- Unit test all four `WatchlistService` methods with a temp file.
- Test the 10-coin cap enforcement.
- Test rejection of unsupported coin tickers.

---

## Feature 6: Price Alerts (`/alert`)

### What it does
Users set a price threshold for a coin. The bot polls every 5 minutes and DMs the user when the condition is met. Alert is deleted after firing (one-shot).

### Commands
```
/alert set <coin> <above|below> <price>  — create an alert
/alert list                               — show the user's active alerts
/alert clear                              — remove all the user's alerts
```

### Persistence layer
**New file: `services/alerts.py`**
```python
ALERTS_PATH = Path("data/alerts.json")

class AlertsService:
    def add(self, user_id: int, coin: str, direction: str, price: float) -> str:
        """Returns alert ID."""

    def get_all(self) -> list[dict]: ...
    def get_for_user(self, user_id: int) -> list[dict]: ...
    def delete(self, alert_id: str) -> None: ...
    def clear_user(self, user_id: int) -> None: ...
```
Storage format:
```json
{
  "alert_id_1": {
    "user_id": 123456789,
    "coin": "BTC",
    "direction": "above",
    "price": 90000.0
  }
}
```
- Cap at 5 alerts per user.
- `alert_id` is a short UUID (`uuid.uuid4().hex[:8]`).

### Background polling
**New cog: `cogs/alerts.py`**
- Uses `@tasks.loop(minutes=5)` from `discord.ext.tasks`.
- On each tick: fetch current price for every unique coin referenced in active alerts, check conditions, fire DMs for triggered alerts, delete fired alerts.
- DM format: `🔔 Alert fired: BTC is now $91,200 (your threshold: above $90,000)`
- Start the loop in `cog_load` / `setup`.

### Error handling
- If a DM fails (user has DMs disabled), log the error and delete the alert anyway.
- If CoinGecko fails during a poll tick, skip that tick silently (don't crash the loop).

### Tests
- Unit test all `AlertsService` methods with a temp file.
- Test the 5-alert cap.
- Test condition evaluation logic (above/below checks) separately from the polling loop.

---

## Feature 7: Scheduled Digest

### What it does
At a configured time each day, the bot posts a market digest to a designated channel: top 3 gainers, top 3 losers, Fear & Greed index, and a one-paragraph Claude market commentary.

### Commands
```
/digest setchannel <#channel>   — set the channel for daily digests (admin only)
/digest settime <HH:MM UTC>     — set the daily post time (admin only)
/digest now                     — post the digest immediately (admin only)
```

### Persistence
**New file: `data/digest_config.json`**
```json
{
  "guild_id": {
    "channel_id": 123456789,
    "time_utc": "08:00"
  }
}
```

**New file: `services/digest.py`**
```python
class DigestService:
    def get_config(self, guild_id: int) -> dict | None: ...
    def set_config(self, guild_id: int, channel_id: int, time_utc: str) -> None: ...
```

### New cog: `cogs/digest.py`
- Uses `@tasks.loop(minutes=1)` to check if any guild's configured time matches `datetime.utcnow()` (hour + minute).
- Tracks which guilds have already been posted today (in-memory dict reset at midnight UTC) to avoid duplicate posts.
- Builds the digest: calls `get_price_data()` for all coins, sorts, takes top/bottom 3, calls `FearGreedClient.get_current()`, calls a new `ClaudeAnalyst.generate_market_commentary()` method.
- Posts as a rich embed to the configured channel.

### New method on ClaudeAnalyst
```python
def generate_market_commentary(
    self,
    top_gainers: list[dict],
    top_losers: list[dict],
    fear_greed: dict,
) -> str:
    """Returns a 2-3 sentence market commentary paragraph."""
```

### Admin guard
All three `/digest` commands check `interaction.user.guild_permissions.manage_guild` before executing. Return a permission error embed if not met.

### Tests
- Unit test `DigestService` with a temp file.
- Unit test the time-match logic.
- Unit test `generate_market_commentary()` with mocked Anthropic client.

---

## Implementation Order & Branch Names

| # | Feature | Branch |
|---|---------|--------|
| 1 | `/compare` | `feature/task-5-compare-command` |
| 2 | `/market` | `feature/task-6-market-command` |
| 3 | Fear & Greed | `feature/task-7-fear-greed` |
| 4 | Price Charts | `feature/task-8-price-charts` |
| 5 | Watchlist | `feature/task-9-watchlist` |
| 6 | Price Alerts | `feature/task-10-price-alerts` |
| 7 | Scheduled Digest | `feature/task-11-scheduled-digest` |

---

## Shared Conventions

- All new slash commands go in `cogs/crypto.py` unless they form a coherent independent group (watchlist, alerts, digest get their own cog files).
- All new cogs are loaded in `bot.py` via `await self.load_extension("cogs.<name>")`.
- All new services are instantiated in `bot.py` and passed into cog constructors — no singletons, no globals.
- Persistent data lives in `data/` (gitignored). Create `data/.gitkeep` so the directory exists in the repo.
- Every new service gets a corresponding test file in `tests/services/`.
- Run `pytest` before every PR. All 28+ existing tests must continue to pass.
