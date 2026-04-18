# Feature 5: Watchlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-user coin watchlist with `/watch add/remove/show/clear` subcommands, persisted to `data/watchlists.json`.

**Architecture:** `WatchlistService` handles all JSON reads/writes and validation; `WatchlistCog` uses an `app_commands.Group` for Discord subcommands. The service is instantiated in `bot.py` and passed into the cog constructor. `/watch show` fetches price + 30d indicators per coin and sends up to 10 embeds in one ephemeral reply.

**Tech Stack:** discord.py v2 `app_commands.Group`, Python `json` + `pathlib`, pytest `tmp_path` fixture

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `data/.gitkeep` | Ensures `data/` directory exists in repo |
| Modify | `.gitignore` | Add `data/` entry |
| Create | `services/watchlist.py` | `WatchlistService` — JSON persistence + validation |
| Create | `tests/services/test_watchlist.py` | Unit tests for `WatchlistService` |
| Create | `cogs/watchlist.py` | `WatchlistCog` — Discord subcommands |
| Modify | `bot.py` | Instantiate `WatchlistService`, load `cogs.watchlist` |
| Modify | `cogs/crypto.py` | Add `/watch` entry to `/help` embed |

---

### Task 1: Feature branch + persistence infrastructure

**Files:**
- Create: `data/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-9-watchlist
```

Expected: switched to new branch `feature/task-9-watchlist`.

- [ ] **Step 2: Create data directory**

Create `data/.gitkeep` as an empty file (no content). This ensures the `data/` directory is tracked in git.

- [ ] **Step 3: Add data/ to .gitignore**

Add this line anywhere in `.gitignore` (e.g. after the `# Claude Code` section):

```
data/
```

- [ ] **Step 4: Commit**

```bash
git add data/.gitkeep .gitignore
git commit -m "chore: add data/ directory for persistent storage"
```

Expected: 2 files changed.

---

### Task 2: WatchlistService — tests first, then implementation

**Files:**
- Create: `tests/services/test_watchlist.py`
- Create: `services/watchlist.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_watchlist.py`:

```python
import pytest

from config import SUPPORTED_COINS
from services.watchlist import WatchlistService


@pytest.fixture
def svc(tmp_path):
    return WatchlistService(path=tmp_path / "watchlists.json")


def test_add_happy_path(svc):
    svc.add(1, "BTC")
    assert svc.get(1) == ["BTC"]


def test_add_duplicate(svc):
    svc.add(1, "BTC")
    with pytest.raises(ValueError, match="already on your watchlist"):
        svc.add(1, "BTC")


def test_add_cap(svc):
    all_coins = list(SUPPORTED_COINS.keys())
    for coin in all_coins[:10]:
        svc.add(1, coin)
    with pytest.raises(ValueError, match="full"):
        svc.add(1, all_coins[10])


def test_add_unsupported_coin(svc):
    with pytest.raises(ValueError, match="not a supported coin"):
        svc.add(1, "INVALID")


def test_remove_happy_path(svc):
    svc.add(1, "BTC")
    svc.remove(1, "BTC")
    assert svc.get(1) == []


def test_remove_not_on_list(svc):
    with pytest.raises(ValueError, match="not on your watchlist"):
        svc.remove(1, "BTC")


def test_get_unknown_user(svc):
    assert svc.get(999) == []


def test_clear(svc):
    svc.add(1, "BTC")
    svc.add(1, "ETH")
    svc.clear(1)
    assert svc.get(1) == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/services/test_watchlist.py -v
```

Expected: `ImportError` — `services/watchlist.py` does not exist yet.

- [ ] **Step 3: Implement WatchlistService**

Create `services/watchlist.py`:

```python
import json
from pathlib import Path

from config import SUPPORTED_COINS

WATCHLIST_PATH = Path("data/watchlists.json")


class WatchlistService:
    def __init__(self, path: Path = WATCHLIST_PATH):
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f)

    def add(self, user_id: int, coin: str) -> None:
        if coin not in SUPPORTED_COINS:
            raise ValueError(f"{coin} is not a supported coin.")
        data = self._read()
        key = str(user_id)
        watchlist = data.get(key, [])
        if coin in watchlist:
            raise ValueError(f"{coin} is already on your watchlist.")
        if len(watchlist) >= 10:
            raise ValueError("Your watchlist is full (10/10 coins). Remove a coin first.")
        watchlist.append(coin)
        data[key] = watchlist
        self._write(data)

    def remove(self, user_id: int, coin: str) -> None:
        data = self._read()
        key = str(user_id)
        watchlist = data.get(key, [])
        if coin not in watchlist:
            raise ValueError(f"{coin} is not on your watchlist.")
        watchlist.remove(coin)
        data[key] = watchlist
        self._write(data)

    def get(self, user_id: int) -> list[str]:
        data = self._read()
        return data.get(str(user_id), [])

    def clear(self, user_id: int) -> None:
        data = self._read()
        data.pop(str(user_id), None)
        self._write(data)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/services/test_watchlist.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add services/watchlist.py tests/services/test_watchlist.py
git commit -m "feat: add WatchlistService with JSON persistence and unit tests"
```

---

### Task 3: WatchlistCog

**Files:**
- Create: `cogs/watchlist.py`

- [ ] **Step 1: Create cogs/watchlist.py**

```python
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import SUPPORTED_COINS
from services.coingecko import CoinGeckoClient
from services.indicators import calculate_indicators
from services.watchlist import WatchlistService

_log = logging.getLogger(__name__)


def _rsi_label(rsi) -> str:
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi:.1f} ⚠️ Overbought"
    if rsi <= 30:
        return f"{rsi:.1f} ⚠️ Oversold"
    return f"{rsi:.1f} Neutral"


def _fmt_indicator(value: float | None, prefix: str = "$") -> str:
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.2f}"


class WatchlistCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        watchlist: WatchlistService,
        coingecko: CoinGeckoClient,
    ):
        self.bot = bot
        self.watchlist = watchlist
        self.coingecko = coingecko

    watch = app_commands.Group(name="watch", description="Manage your coin watchlist")

    @watch.command(name="add", description="Add a coin to your watchlist")
    @app_commands.describe(coin="Coin ticker to add")
    @app_commands.choices(coin=[app_commands.Choice(name=k, value=k) for k in SUPPORTED_COINS])
    async def watch_add(self, interaction: discord.Interaction, coin: str):
        try:
            self.watchlist.add(interaction.user.id, coin)
            count = len(self.watchlist.get(interaction.user.id))
            await interaction.response.send_message(
                f"✅ {coin} added to your watchlist. ({count}/10 coins)", ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @watch.command(name="remove", description="Remove a coin from your watchlist")
    @app_commands.describe(coin="Coin ticker to remove")
    @app_commands.choices(coin=[app_commands.Choice(name=k, value=k) for k in SUPPORTED_COINS])
    async def watch_remove(self, interaction: discord.Interaction, coin: str):
        try:
            self.watchlist.remove(interaction.user.id, coin)
            await interaction.response.send_message(
                f"✅ {coin} removed from your watchlist.", ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @watch.command(name="clear", description="Clear your entire watchlist")
    async def watch_clear(self, interaction: discord.Interaction):
        self.watchlist.clear(interaction.user.id)
        await interaction.response.send_message(
            "✅ Your watchlist has been cleared.", ephemeral=True
        )

    @watch.command(name="show", description="Show prices + indicators for your watchlist coins")
    async def watch_show(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        coins = self.watchlist.get(interaction.user.id)
        if not coins:
            await interaction.followup.send(
                "Your watchlist is empty. Use `/watch add` to get started.",
                ephemeral=True,
            )
            return

        embeds = []
        for i, coin in enumerate(coins):
            is_last = i == len(coins) - 1
            try:
                price_data = self.coingecko.get_price_data(coin, "24h")
                chart_data = self.coingecko.get_market_chart(coin, 30)
                indicators = calculate_indicators(chart_data["close_prices"], chart_data["volumes"])

                change = price_data["price_change_pct"]
                color = discord.Color.green() if change >= 0 else discord.Color.red()
                arrow = "▲" if change >= 0 else "▼"

                embed = discord.Embed(
                    title=f"{coin} — Watchlist",
                    color=color,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="Current Price", value=f"${price_data['current_price']:,.4f}", inline=True)
                embed.add_field(name="Change (24h)", value=f"{arrow} {abs(change):.2f}%", inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=True)
                embed.add_field(name="RSI (14)", value=_rsi_label(indicators["rsi"]), inline=True)
                embed.add_field(name="SMA 20", value=_fmt_indicator(indicators["sma20"]), inline=True)
                embed.add_field(name="Volume Trend", value=indicators["volume_trend"], inline=True)
                if is_last:
                    embed.set_footer(text="Data: CoinGecko")
                embeds.append(embed)
            except Exception as exc:
                _log.warning("watch_show: failed to fetch %s: %r", coin, exc)
                embeds.append(discord.Embed(
                    title=f"{coin} — Watchlist",
                    color=discord.Color.dark_grey(),
                    description="❌ Data unavailable",
                ))

        await interaction.followup.send(embeds=embeds, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WatchlistCog(bot, bot.watchlist, bot.coingecko))
```

- [ ] **Step 2: Run full test suite**

```bash
pytest --tb=short -q
```

Expected: 56 passed (48 existing + 8 watchlist).

- [ ] **Step 3: Commit**

```bash
git add cogs/watchlist.py
git commit -m "feat: add WatchlistCog with /watch subcommand group"
```

---

### Task 4: Wire bot.py + update /help

**Files:**
- Modify: `bot.py`
- Modify: `cogs/crypto.py`

- [ ] **Step 1: Update imports in bot.py**

Add to the existing imports block (after `from services.fear_greed import FearGreedClient`):

```python
from services.watchlist import WatchlistService
```

- [ ] **Step 2: Update setup_hook in bot.py**

Replace the existing `setup_hook` method with:

```python
    async def setup_hook(self):
        self.coingecko = CoinGeckoClient()
        self.analyst = ClaudeAnalyst()
        self.fear_greed = FearGreedClient()
        self.watchlist = WatchlistService()
        await self.load_extension("cogs.crypto")
        await self.load_extension("cogs.watchlist")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global commands: {[c.name for c in synced]}")
        except Exception as e:
            print(f"ERROR: Failed to sync commands: {e}")
```

- [ ] **Step 3: Add /watch to /help embed in cogs/crypto.py**

In `help_command`, add after the `/feargreed` field (before the `Supported Coins` field):

```python
        embed.add_field(
            name="/watch add|remove|show|clear",
            value="Personal coin watchlist. `/watch show` displays price, RSI, SMA20, and volume trend for each coin.",
            inline=False,
        )
```

- [ ] **Step 4: Run full test suite**

```bash
pytest --tb=short -q
```

Expected: 56 passed.

- [ ] **Step 5: Commit**

```bash
git add bot.py cogs/crypto.py
git commit -m "feat: wire WatchlistService into bot and add /watch to /help"
```

---

### Task 5: Push and open PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feature/task-9-watchlist
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "feat: add /watch watchlist command (Feature 5)" --base main --body "$(cat <<'EOF'
## Summary

- Adds `services/watchlist.py` with `WatchlistService` — reads/writes `data/watchlists.json`, enforces 10-coin cap and SUPPORTED_COINS validation
- Adds `cogs/watchlist.py` with `WatchlistCog` using `app_commands.Group` for `/watch add`, `/watch remove`, `/watch show`, `/watch clear`
- `/watch show` returns one ephemeral embed per coin with price, 24h % change, RSI, SMA20, and volume trend
- All replies are ephemeral (visible only to the user who ran the command)
- 8 unit tests covering all service methods, cap enforcement, and unsupported coin rejection
- Updates `/help` to list the new command group

## Tech Notes

- `WatchlistService` accepts a `path` constructor parameter (default: `data/watchlists.json`) so tests inject a `tmp_path` without touching real files
- `app_commands.Group` declared as a class variable on `WatchlistCog` — discord.py v2 registers it with the tree automatically on `add_cog()`
- `/watch show` makes 2 CoinGecko calls per coin (price + chart) sequentially — consistent with the established free-tier pattern
- `data/` is gitignored; `data/.gitkeep` is force-tracked to ensure the directory exists

## Test Plan

- [ ] Run `pytest` — 56 tests pass, 0 failures
- [ ] `/watch add BTC` — ephemeral confirmation with count (1/10 coins)
- [ ] `/watch add BTC` again — ephemeral error: "already on your watchlist"
- [ ] `/watch add INVALID` — ephemeral error: "not a supported coin"
- [ ] `/watch show` — ephemeral embeds for each watchlist coin with price + indicators
- [ ] `/watch show` on empty watchlist — ephemeral empty-state message
- [ ] `/watch remove BTC` — ephemeral confirmation
- [ ] `/watch clear` — ephemeral confirmation, subsequent `/watch show` shows empty state
- [ ] `/help` lists `/watch add|remove|show|clear`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

