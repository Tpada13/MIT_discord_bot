# Feature 5: Watchlist (`/watch`) — Design Spec

**Date:** 2026-04-18
**Status:** Approved for implementation
**Branch:** `feature/task-9-watchlist`

---

## Overview

Per-user coin watchlist with four subcommands. Users build a personal list of up to 10 coins; `/watch show` runs a richer-than-market snapshot across their coins (price, 24h change, RSI, SMA20, volume trend). All replies are ephemeral (visible only to the user who ran the command).

---

## Architecture

Three new files, one wiring change:

| File | Purpose |
|------|---------|
| `services/watchlist.py` | `WatchlistService` — reads/writes `data/watchlists.json`, enforces cap and coin validation |
| `cogs/watchlist.py` | `WatchlistCog` — `app_commands.Group` with four subcommands; takes `WatchlistService` + `CoinGeckoClient` |
| `data/.gitkeep` | Creates `data/` directory in repo; `data/` is gitignored |
| `bot.py` | Instantiate `WatchlistService`, load `cogs.watchlist` |

---

## Data & Persistence

**File:** `data/watchlists.json`

```json
{
  "123456789": ["BTC", "ETH", "SOL"],
  "987654321": ["DOGE"]
}
```

- Keyed by user ID (string)
- Read and write the full file on every call — no in-memory cache
- File and `data/` directory are created automatically on first write if absent

### `WatchlistService` interface

```python
WATCHLIST_PATH = Path("data/watchlists.json")

class WatchlistService:
    def add(self, user_id: int, coin: str) -> None: ...
    def remove(self, user_id: int, coin: str) -> None: ...
    def get(self, user_id: int) -> list[str]: ...
    def clear(self, user_id: int) -> None: ...
```

**Validation rules (enforced in the service, not the cog):**

| Method | Error conditions |
|--------|-----------------|
| `add` | Coin not in `SUPPORTED_COINS`; coin already on list; list at 10-coin cap |
| `remove` | Coin not on user's list |
| `get` | Returns `[]` for unknown user — never raises |
| `clear` | Removes user's entry entirely — never raises |

All `ValueError` messages are user-facing strings passed directly to Discord.

---

## Commands

**Cog structure:** `WatchlistCog` declares a `watch = app_commands.Group(name="watch", description="Manage your coin watchlist")`. Each subcommand is decorated with `@watch.command(name=...)`.

All subcommands send ephemeral replies.

### `/watch add <coin>`
- `coin` is a free-text parameter with `app_commands.choices` autocomplete from `SUPPORTED_COINS`
- No defer needed (no API calls)
- Calls `WatchlistService.add()`; on `ValueError` sends `❌ <message>`
- Success reply: `✅ BTC added to your watchlist. (3/10 coins)`

### `/watch remove <coin>`
- `coin` is a free-text parameter with `app_commands.choices` autocomplete from `SUPPORTED_COINS`
- No defer needed
- Calls `WatchlistService.remove()`; on `ValueError` sends `❌ <message>`
- Success reply: `✅ BTC removed from your watchlist.`

### `/watch clear`
- No defer needed
- Calls `WatchlistService.clear()`
- Success reply: `✅ Your watchlist has been cleared.`

### `/watch show`
- Defers immediately (`await interaction.response.defer(ephemeral=True)`)
- Calls `WatchlistService.get()`; if empty replies: `Your watchlist is empty. Use /watch add <coin> to get started.`
- For each coin (sequential, free-tier safe):
  - `get_price_data(coin, "24h")`
  - `get_market_chart(coin, 30)` → `calculate_indicators()`
- Sends all coin embeds in one `followup.send(embeds=[...], ephemeral=True)`

---

## `/watch show` Embed Format

One embed per coin, all sent together in a single `followup.send(embeds=[...])`:

- **Title:** `BTC — Watchlist`
- **Color:** green if 24h change ≥ 0, red otherwise
- **Inline fields:** Current Price | Change (24h) | *(blank spacer)* | RSI (14) | SMA 20 | Volume Trend
- **Footer:** `Data: CoinGecko` — on the last embed only

Discord allows up to 10 embeds per message, matching the 10-coin cap exactly.

Each coin requires 2 CoinGecko calls → a 10-coin watchlist makes 20 calls. Slow but consistent with the established free-tier pattern.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| `add`/`remove` validation failure | Ephemeral `❌ <user-facing message>` |
| CoinGecko fetch fails for one coin in `/watch show` | Include a `❌ BTC — unavailable` embed for that coin; continue with the rest |
| `data/` directory missing on write | `WatchlistService` creates it automatically via `Path.mkdir(parents=True, exist_ok=True)` |

---

## Wiring (`bot.py`)

```python
from services.watchlist import WatchlistService

class CryptoBot(commands.Bot):
    async def setup_hook(self):
        ...
        self.watchlist = WatchlistService()
        await self.load_extension("cogs.crypto")
        await self.load_extension("cogs.watchlist")
        ...
```

`cogs/watchlist.py` `setup()` function:

```python
async def setup(bot: commands.Bot):
    await bot.add_cog(WatchlistCog(bot, bot.watchlist, bot.coingecko))
```

---

## Tests (`tests/services/test_watchlist.py`)

All tests use pytest's `tmp_path` fixture — no real files touched.

| Test | What it verifies |
|------|-----------------|
| `test_add_happy_path` | Coin appears in `get()` after `add()` |
| `test_add_duplicate` | `ValueError` on adding same coin twice |
| `test_add_cap` | `ValueError` when adding an 11th coin |
| `test_add_unsupported_coin` | `ValueError` for ticker not in `SUPPORTED_COINS` |
| `test_remove_happy_path` | Coin absent from `get()` after `remove()` |
| `test_remove_not_on_list` | `ValueError` when removing a coin not present |
| `test_get_unknown_user` | Returns `[]` for a user with no watchlist |
| `test_clear` | `get()` returns `[]` after `clear()` |
