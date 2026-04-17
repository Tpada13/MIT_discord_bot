# Feature 4: `/chart` — Price & Volume Chart

**Date:** 2026-04-17
**Branch:** `feature/task-8-price-charts`
**Status:** Approved for implementation

---

## Overview

Adds a `/chart <coin> [timeframe]` slash command that generates a dark-themed two-panel PNG chart (price line + SMA20 overlay, volume bars) and sends it as a Discord file attachment alongside a minimal price embed.

---

## New Dependency

Add to `requirements.txt`:
```
matplotlib
```

---

## New File: `services/chart.py`

Pure function — no class, no state, no side effects:

```python
def generate_price_chart(
    ticker: str,
    close_prices: list[float],
    volumes: list[float],
    timeframe: str,
) -> bytes:
    """
    Renders a two-panel dark-themed chart and returns PNG bytes.

    Top panel: price line + SMA20 overlay (omitted if < 20 data points).
    Bottom panel: volume bars (green if price up vs prior, red if down).

    Returns PNG bytes from BytesIO. Does not write to disk.
    """
```

### Chart layout

- `plt.style.use('dark_background')`
- `fig, (ax_price, ax_vol) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]}, figsize=(10, 6))`
- **Top panel (ax_price):**
  - Price line chart
  - SMA20 overlay: rolling mean over 20 points. Skipped silently if `len(close_prices) < 20`
  - Title: `f"{ticker} — {timeframe}"`
- **Bottom panel (ax_vol):**
  - Volume bars, one per data point
  - Bar color: green if `close_prices[i] >= close_prices[i-1]`, red otherwise. First bar defaults to green.
- `fig.tight_layout()`
- Save to `io.BytesIO`, return `.getvalue()`
- Call `plt.close(fig)` after saving to free memory

---

## Command: `/chart`

Added to `cogs/crypto.py`.

### Signature

```
/chart <coin> [timeframe]
```

- `coin`: ticker from `SUPPORTED_COINS`
- `timeframe`: `7d`, `30d`, `90d`, `180d` (default: `30d`) — same choices as `/analyze`

### Behavior

1. `await interaction.response.defer()`
2. Fetch `get_price_data(coin, tf)` and `get_market_chart(coin, days)` sequentially
3. On `ValueError`: send `❌ {e}` and return
4. On other exception: send `❌ CoinGecko error: {e}` and return
5. Call `generate_price_chart(coin, chart_data["close_prices"], chart_data["volumes"], tf)`
6. Build minimal embed: title `"{COIN} — {tf} Chart"`, color green/red based on % change, fields: Current Price + Change ({tf})
7. Send `discord.File(fp=io.BytesIO(chart_bytes), filename=f"{coin}_{tf}_chart.png")` + embed in one `followup.send()`

### Imports needed in `cogs/crypto.py`

```python
import io
from services.chart import generate_price_chart
```

### `/help` update

Add after `/feargreed` and before `Supported Coins`:
```
/chart <coin> [timeframe] — Price + volume chart image. Timeframes: 7d, 30d, 90d, 180d (default: 30d)
```

---

## Wiring

No changes to `bot.py` — `generate_price_chart` is a pure function, not a service instance.

---

## Tests

New file: `tests/services/test_chart.py`

| # | Test | What it checks |
|---|------|----------------|
| 1 | `test_generate_price_chart_returns_bytes` | 30 days of synthetic data → non-empty `bytes` returned |
| 2 | `test_generate_price_chart_minimal_data` | 7 data points (< SMA20 window) → no exception, non-empty bytes |
| 3 | `test_generate_price_chart_different_timeframes` | `"7d"` and `"180d"` labels → both return bytes without error |

No visual regression tests. Byte output verification is sufficient.

**Target: 45 existing + 3 new = 48 passing tests.**

---

## Files Changed

| File | Action |
|------|--------|
| `requirements.txt` | Add `matplotlib` |
| `services/chart.py` | **New** — `generate_price_chart()` |
| `cogs/crypto.py` | Add `import io`, import `generate_price_chart`, add `/chart` command, update `/help` |
| `tests/services/test_chart.py` | **New** — 3 smoke tests |

---

## Out of Scope

- Candlestick / OHLCV charts (CoinGecko free tier only provides close prices)
- Interactive charts (Discord only supports static images)
- Timestamp labels on x-axis (adds complexity, minimal value for trend reading)
- Additional indicators in the chart (EMA, RSI overlays)
