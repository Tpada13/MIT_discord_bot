# Watchlist Table Redesign — Design Spec

**Date:** 2026-04-18
**Status:** Approved for implementation
**Branch:** `feature/task-12-watchlist-table`

---

## Overview

Redesign `/watch show` to display a compact monospace table (one embed, one code block) instead of one embed per coin. Add a "change since last show" column (Δ$ and Δ%) by persisting the current prices at the end of every `/watch show` call. Migrate `watchlists.json` to a richer nested format that holds both coins and price snapshots in one file.

Existing `data/watchlists.json` is deleted on deploy — existing data is disposable.

---

## Data Format

**File:** `data/watchlists.json`

New format (replaces the old flat list):

```json
{
  "123456789": {
    "coins": ["BTC", "ETH", "SOL"],
    "last_prices": {
      "BTC": 84123.00,
      "ETH": 3210.00
    }
  }
}
```

- `coins` — ordered list of tickers on the user's watchlist
- `last_prices` — map of ticker → price at the time of the last `/watch show`. Only coins that successfully fetched are stored. Coins never shown before are absent (rendered as `—`).

---

## WatchlistService Changes

All existing methods (`add`, `remove`, `get`, `clear`) are updated to read/write the new nested format. Externally their signatures and behaviour are unchanged — `get(user_id)` still returns `list[str]`.

Two new methods:

```python
def get_last_prices(self, user_id: int) -> dict[str, float]:
    """Returns the saved price snapshot. Returns {} if no snapshot exists. Never raises."""

def save_last_prices(self, user_id: int, prices: dict[str, float]) -> None:
    """Merges prices into the user's last_prices entry and writes to disk."""
```

`save_last_prices` merges (not replaces) — so if only 3 of 5 coins fetched successfully, the other 2 retain their previous snapshot values.

---

## `/watch show` — New Behaviour

1. `await interaction.response.defer(ephemeral=True)`
2. Get coin list via `watchlist.get(user_id)` — if empty, send empty-state message and return
3. Get last prices via `watchlist.get_last_prices(user_id)`
4. For each coin (sequential): call `get_price_data(coin, "24h")` + `get_market_chart(coin, 30)` → `calculate_indicators()`
5. Build the table string (see layout below)
6. Call `watchlist.save_last_prices(user_id, fetched_prices)` — only successful fetches
7. Send one ephemeral embed containing the table in a code block

### Table Layout

```
Coin  Price         24h%    RSI   SMA20         Trend    Δ$          Δ%
BTC   $84,123.00   ▲2.14%   65   $81,234.00   Rising   +$420.00   +0.50%
ETH    $3,210.00   ▼0.50%   42    $3,150.00   Flat     -$210.00   -6.14%
SOL      $142.00   ▲1.30%   58     $138.00    Rising       —          —
DOGE       $0.12   ▼1.20%   35       $0.11    Falling      —          —
BNB            ❌ unavailable
```

- Columns: `Coin`, `Price`, `24h%`, `RSI`, `SMA20`, `Trend`, `Δ$`, `Δ%`
- `—` for Δ$ and Δ% when no previous price is stored for that coin
- Failed fetches render as `{COIN}   ❌ unavailable` — one line, no other columns
- Failed coins are **not** added to `fetched_prices` — their previous snapshot is preserved
- Embed color: green if strictly more than half of successfully-fetched coins have positive 24h change, red if strictly more than half are negative, grey if equal or all failed

---

## Files Changed

| Action | File |
|--------|------|
| Modify | `services/watchlist.py` |
| Modify | `cogs/watchlist.py` |
| Modify | `tests/services/test_watchlist.py` |
| Modify | `tests/cogs/test_watchlist_cog.py` |
| Delete | `data/watchlists.json` (existing data disposable) |

No changes to `bot.py`, `cogs/crypto.py`, or any other file.

---

## Tests

### `tests/services/test_watchlist.py`

All existing tests updated for new nested format. New tests:

| Test | What it verifies |
|------|-----------------|
| `test_get_last_prices_empty` | Returns `{}` for user with no snapshot |
| `test_save_and_get_last_prices` | Saved prices are retrievable |
| `test_save_last_prices_merges` | Saving partial prices doesn't overwrite unaffected coins |

### `tests/cogs/test_watchlist_cog.py`

| Test | What it verifies |
|------|-----------------|
| `test_watch_show_empty_watchlist` | Unchanged behaviour — empty-state message |
| `test_watch_show_coin_fetch_error` | Single embed sent; failed coin row present in code block |
| `test_watch_show_success` | Single embed sent; table contains coin tickers |

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Coin fetch fails | Row renders as `{COIN}   ❌ unavailable`; coin excluded from price snapshot save |
| No previous price for coin | Δ$ and Δ% columns render as `—` |
| All coins fail | Single embed with all rows showing `❌ unavailable`; no price snapshot saved |
| Empty watchlist | Ephemeral message: "Your watchlist is empty. Use `/watch add` to get started." |
