# Crypto Analysis Discord Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Discord bot with slash commands for crypto price data, technical analysis, and AI-powered forecasting using Claude as a senior financial analyst.

**Architecture:** Class-based discord.py bot with `setup_hook` for slash command registration. A service layer (`services/`) decouples all data concerns from Discord concerns — CoinGecko client, pandas-ta indicators, and Claude analyst are each independent modules. All slash commands live in a single Cog (`cogs/crypto.py`).

**Tech Stack:** Python 3.10+, discord.py, anthropic SDK, requests, pandas, pandas-ta, pytest, python-dotenv

---

## File Map

| File | Responsibility |
|------|---------------|
| `bot.py` | Entry point — instantiates bot class, registers cog, calls `bot.run()` |
| `config.py` | Supported coins dict (ticker → CoinGecko ID), timeframe constants |
| `cogs/__init__.py` | Empty — marks directory as package |
| `cogs/crypto.py` | All slash commands: `/price`, `/analyze`, `/forecast`, `/help` |
| `services/__init__.py` | Empty — marks directory as package |
| `services/coingecko.py` | CoinGecko REST client: `get_price_data()`, `get_market_chart()` |
| `services/indicators.py` | `calculate_indicators()` — RSI, SMA, EMA, volume trend via pandas-ta |
| `services/claude_analyst.py` | `ClaudeAnalyst.generate_forecast()` — builds prompt, calls Claude API |
| `tests/__init__.py` | Empty |
| `tests/services/__init__.py` | Empty |
| `tests/services/test_coingecko.py` | Unit tests for CoinGeckoClient (mocked HTTP) |
| `tests/services/test_indicators.py` | Unit tests for calculate_indicators |
| `tests/services/test_claude_analyst.py` | Unit tests for ClaudeAnalyst (mocked Anthropic) |

---

## Task 1: Project Scaffold

**Branch:** `feature/task-1-project-scaffold`

**Files:**
- Modify: `requirements.txt`
- Create: `config.py`
- Create: `bot.py`
- Create: `cogs/__init__.py`
- Create: `services/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/services/__init__.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout -b feature/task-1-project-scaffold
```

- [ ] **Step 2: Update requirements.txt**

```
discord.py
python-dotenv
anthropic
requests
pandas
pandas-ta
pytest
pytest-asyncio
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors. If `pandas-ta` fails, try `pip install pandas-ta --no-deps` then `pip install pandas numpy`.

- [ ] **Step 4: Create config.py**

```python
# Mapping from ticker symbol to CoinGecko coin ID
SUPPORTED_COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "XDC": "xdce-crowd-sale",
    "LINK": "chainlink",
    "SUI": "sui",
    "ZRO": "layerzero",
    "ONDO": "ondo-finance",
    "CRV": "curve-dao-token",
    "SEI": "sei-network",
}

# Valid timeframes for /price command
PRICE_TIMEFRAMES = ["1h", "24h", "3d", "7d"]
DEFAULT_PRICE_TIMEFRAME = "24h"

# Valid timeframes for /analyze and /forecast commands
ANALYSIS_TIMEFRAMES = ["7d", "30d", "90d", "180d"]
DEFAULT_ANALYSIS_TIMEFRAME = "30d"

# Maps timeframe string to number of days for CoinGecko API
TIMEFRAME_TO_DAYS = {
    "1h": 1,
    "24h": 1,
    "3d": 3,
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
}
```

- [ ] **Step 5: Create bot.py**

```python
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class CryptoBot(commands.Bot):
    async def setup_hook(self):
        # Load the cog before syncing so commands are registered
        await self.load_extension("cogs.crypto")
        # Sync slash commands globally — takes up to 1 hour to propagate on first run
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
bot = CryptoBot(command_prefix="!", intents=intents)

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
```

- [ ] **Step 6: Create directory structure and empty init files**

```bash
mkdir -p cogs services tests/services
touch cogs/__init__.py services/__init__.py tests/__init__.py tests/services/__init__.py
```

- [ ] **Step 7: Verify structure looks correct**

```bash
find . -not -path './.git/*' -not -path './docs/*' -type f
```

Expected output includes:
```
./bot.py
./config.py
./requirements.txt
./cogs/__init__.py
./services/__init__.py
./tests/__init__.py
./tests/services/__init__.py
```

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.py bot.py cogs/__init__.py services/__init__.py tests/__init__.py tests/services/__init__.py
git commit -m "feat: scaffold crypto bot project structure

Sets up the cog/service architecture for the crypto analysis Discord
bot. Includes config with supported coins and timeframes, bot entry
point with slash command sync via setup_hook, and empty module
directories for cogs, services, and tests."
```

- [ ] **Step 9: Push and open PR**

```bash
git push -u origin feature/task-1-project-scaffold
gh pr create --title "feat: scaffold crypto bot project structure" --body "$(cat <<'EOF'
## Summary
- Adds `config.py` with supported coins (15 tickers → CoinGecko IDs) and timeframe constants
- Adds `bot.py` entry point using class-based `CryptoBot` with `setup_hook` for slash command sync
- Creates empty `cogs/`, `services/`, `tests/` directory packages
- Updates `requirements.txt` with all required dependencies

## Tech Notes
- Slash commands are synced globally in `setup_hook` (runs once on startup before connection)
- Global command propagation takes up to 1 hour on first deployment

## Test Plan
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] Directory structure is correct
EOF
)"
```

---

## Task 2: CoinGecko Service

**Branch:** `feature/task-2-coingecko-service`

**Files:**
- Create: `services/coingecko.py`
- Create: `tests/services/test_coingecko.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-2-coingecko-service
```

- [ ] **Step 2: Write failing tests**

Create `tests/services/test_coingecko.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from services.coingecko import CoinGeckoClient


@pytest.fixture
def client():
    return CoinGeckoClient()


def make_mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


# --- get_price_data ---

def test_get_price_data_24h(client):
    mock_data = [
        {
            "id": "bitcoin",
            "current_price": 50000.0,
            "price_change_percentage_24h_in_currency": 2.5,
            "price_change_percentage_1h_in_currency": 0.3,
            "price_change_percentage_7d_in_currency": 5.1,
            "market_cap": 1_000_000_000_000,
            "total_volume": 50_000_000_000,
        }
    ]
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(mock_data)
        result = client.get_price_data("BTC", "24h")

    assert result["ticker"] == "BTC"
    assert result["current_price"] == 50000.0
    assert result["price_change_pct"] == 2.5
    assert result["market_cap"] == 1_000_000_000_000
    assert result["volume_24h"] == 50_000_000_000
    assert result["timeframe"] == "24h"


def test_get_price_data_1h(client):
    mock_data = [
        {
            "id": "bitcoin",
            "current_price": 50000.0,
            "price_change_percentage_24h_in_currency": 2.5,
            "price_change_percentage_1h_in_currency": 0.3,
            "price_change_percentage_7d_in_currency": 5.1,
            "market_cap": 1_000_000_000_000,
            "total_volume": 50_000_000_000,
        }
    ]
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(mock_data)
        result = client.get_price_data("BTC", "1h")

    assert result["price_change_pct"] == 0.3
    assert result["timeframe"] == "1h"


def test_get_price_data_coin_not_found(client):
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response([])
        with pytest.raises(ValueError, match="not found"):
            client.get_price_data("FAKE", "24h")


def test_get_price_data_3d_uses_market_chart(client):
    """3d timeframe requires a market_chart call to calculate % change."""
    markets_data = [
        {
            "id": "bitcoin",
            "current_price": 50000.0,
            "price_change_percentage_24h_in_currency": 2.5,
            "price_change_percentage_1h_in_currency": 0.3,
            "price_change_percentage_7d_in_currency": 5.1,
            "market_cap": 1_000_000_000_000,
            "total_volume": 50_000_000_000,
        }
    ]
    chart_data = {
        "prices": [[1000, 45000.0], [2000, 47000.0], [3000, 50000.0]],
        "total_volumes": [[1000, 1e9], [2000, 1.1e9], [3000, 1.2e9]],
    }

    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_response(markets_data),
            make_mock_response(chart_data),
        ]
        result = client.get_price_data("BTC", "3d")

    # (50000 - 45000) / 45000 * 100 = 11.11...
    assert result["timeframe"] == "3d"
    assert abs(result["price_change_pct"] - 11.11) < 0.1


# --- get_market_chart ---

def test_get_market_chart_returns_prices_and_volumes(client):
    chart_data = {
        "prices": [[1000, 45000.0], [2000, 46000.0], [3000, 47000.0]],
        "total_volumes": [[1000, 1e9], [2000, 1.1e9], [3000, 1.2e9]],
    }
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(chart_data)
        result = client.get_market_chart("BTC", days=7)

    assert result["ticker"] == "BTC"
    assert result["days"] == 7
    assert result["close_prices"] == [45000.0, 46000.0, 47000.0]
    assert result["volumes"] == [1e9, 1.1e9, 1.2e9]
    assert len(result["timestamps"]) == 3


def test_ticker_to_id_known_coin(client):
    assert client._ticker_to_id("BTC") == "bitcoin"
    assert client._ticker_to_id("eth") == "ethereum"


def test_ticker_to_id_unknown_coin_falls_back_to_lowercase(client):
    assert client._ticker_to_id("NEWCOIN") == "newcoin"
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/services/test_coingecko.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.coingecko'`

- [ ] **Step 4: Create services/coingecko.py**

```python
import requests

from config import SUPPORTED_COINS


class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def _ticker_to_id(self, ticker: str) -> str:
        """Map ticker symbol to CoinGecko coin ID. Falls back to lowercase ticker."""
        return SUPPORTED_COINS.get(ticker.upper(), ticker.lower())

    def get_price_data(self, ticker: str, timeframe: str = "24h") -> dict:
        """
        Fetch current price and % change over the requested timeframe.

        For 1h/24h/7d: single call to /coins/markets (CoinGecko provides these natively).
        For 3d: two calls — /coins/markets for current data + /coins/{id}/market_chart
                for historical prices to calculate the 3-day change.

        Returns:
            {ticker, current_price, price_change_pct, market_cap, volume_24h, timeframe}

        Raises:
            ValueError: if the coin is not found on CoinGecko.
        """
        coin_id = self._ticker_to_id(ticker)

        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
            "price_change_percentage": "1h,24h,7d",
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ValueError(f"Coin '{ticker.upper()}' not found on CoinGecko.")

        coin = data[0]

        if timeframe == "1h":
            pct_change = coin.get("price_change_percentage_1h_in_currency") or 0.0
        elif timeframe == "7d":
            pct_change = coin.get("price_change_percentage_7d_in_currency") or 0.0
        elif timeframe == "3d":
            chart = self.get_market_chart(ticker, days=3)
            prices = chart["close_prices"]
            pct_change = ((prices[-1] - prices[0]) / prices[0]) * 100 if len(prices) >= 2 else 0.0
        else:  # default: 24h
            pct_change = coin.get("price_change_percentage_24h_in_currency") or 0.0

        return {
            "ticker": ticker.upper(),
            "current_price": coin["current_price"],
            "price_change_pct": round(pct_change, 2),
            "market_cap": coin["market_cap"],
            "volume_24h": coin["total_volume"],
            "timeframe": timeframe,
        }

    def get_market_chart(self, ticker: str, days: int) -> dict:
        """
        Fetch price and volume history for technical analysis.

        CoinGecko free tier granularity (automatic):
          - days=1: minutely
          - days=2-90: hourly
          - days>90: daily

        Returns:
            {ticker, days, close_prices: list[float], volumes: list[float], timestamps: list[int]}
        """
        coin_id = self._ticker_to_id(ticker)
        url = f"{self.BASE_URL}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        return {
            "ticker": ticker.upper(),
            "days": days,
            "close_prices": [point[1] for point in data["prices"]],
            "volumes": [point[1] for point in data["total_volumes"]],
            "timestamps": [point[0] for point in data["prices"]],
        }
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/services/test_coingecko.py -v
```

Expected: All 8 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add services/coingecko.py tests/services/test_coingecko.py
git commit -m "feat: add CoinGecko service with price and market chart methods

Implements CoinGeckoClient with get_price_data() (1h/24h/3d/7d) and
get_market_chart() for OHLCV history. Uses the free /coins/markets
endpoint for standard timeframes; falls back to market_chart for
3d change calculation. Unknown tickers are attempted as-is."
```

- [ ] **Step 7: Push and open PR**

```bash
git push -u origin feature/task-2-coingecko-service
gh pr create --title "feat: add CoinGecko service" --body "$(cat <<'EOF'
## Summary
- Implements `CoinGeckoClient` in `services/coingecko.py`
- `get_price_data(ticker, timeframe)` — fetches current price, % change, market cap, volume
- `get_market_chart(ticker, days)` — fetches close prices + volumes for technical analysis
- 8 unit tests, all mocked (no live API calls in test suite)

## Tech Notes
- 1h/24h/7d use a single `/coins/markets` call (native CoinGecko fields)
- 3d requires an additional `/market_chart` call to calculate change manually
- Unknown tickers fall back to lowercase as CoinGecko ID (enables ad-hoc coins)

## Test Plan
- [ ] `pytest tests/services/test_coingecko.py -v` — all 8 tests pass
EOF
)"
```

---

## Task 3: Technical Indicators Service

**Branch:** `feature/task-3-indicators-service`

**Files:**
- Create: `services/indicators.py`
- Create: `tests/services/test_indicators.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-3-indicators-service
```

- [ ] **Step 2: Write failing tests**

Create `tests/services/test_indicators.py`:

```python
import pytest

from services.indicators import calculate_indicators


def make_prices(n: int, start: float = 100.0, step: float = 1.0) -> list:
    """Generate a simple linear price series."""
    return [start + i * step for i in range(n)]


def make_volumes(n: int, base: float = 1_000_000.0) -> list:
    return [base] * n


# --- Sufficient data (60 points covers all indicators) ---

def test_all_indicators_present_with_sufficient_data():
    prices = make_prices(60)
    volumes = make_volumes(60)
    result = calculate_indicators(prices, volumes)

    assert set(result.keys()) == {"rsi", "sma20", "sma50", "ema12", "ema26", "volume_trend"}


def test_rsi_is_float_with_sufficient_data():
    prices = make_prices(60)
    volumes = make_volumes(60)
    result = calculate_indicators(prices, volumes)

    assert isinstance(result["rsi"], float)
    assert 0 <= result["rsi"] <= 100


def test_sma20_is_float_with_sufficient_data():
    prices = make_prices(60)
    volumes = make_volumes(60)
    result = calculate_indicators(prices, volumes)

    assert isinstance(result["sma20"], float)


def test_sma50_is_float_with_60_points():
    prices = make_prices(60)
    volumes = make_volumes(60)
    result = calculate_indicators(prices, volumes)

    assert isinstance(result["sma50"], float)


def test_ema12_and_ema26_are_floats():
    prices = make_prices(60)
    volumes = make_volumes(60)
    result = calculate_indicators(prices, volumes)

    assert isinstance(result["ema12"], float)
    assert isinstance(result["ema26"], float)


def test_volume_trend_is_string():
    prices = make_prices(60)
    volumes = make_volumes(60)
    result = calculate_indicators(prices, volumes)

    assert isinstance(result["volume_trend"], str)
    assert len(result["volume_trend"]) > 0


# --- Insufficient data ---

def test_rsi_is_none_with_fewer_than_15_points():
    prices = make_prices(10)
    volumes = make_volumes(10)
    result = calculate_indicators(prices, volumes)

    assert result["rsi"] is None


def test_sma50_is_none_with_fewer_than_50_points():
    prices = make_prices(30)
    volumes = make_volumes(30)
    result = calculate_indicators(prices, volumes)

    assert result["sma50"] is None
    assert result["sma20"] is not None  # 30 >= 20, so sma20 should be present


def test_very_short_series_returns_all_none():
    result = calculate_indicators([100.0, 101.0], [1000.0, 1000.0])

    assert result["rsi"] is None
    assert result["sma20"] is None
    assert result["sma50"] is None


# --- Volume trend ---

def test_volume_trend_rising_when_recent_volumes_higher():
    base_volumes = [1_000_000.0] * 40
    # Recent 10 are 3x higher
    high_volumes = [3_000_000.0] * 10
    result = calculate_indicators(make_prices(50), base_volumes + high_volumes)

    assert "Rising" in result["volume_trend"]


def test_volume_trend_declining_when_recent_volumes_lower():
    high_volumes = [3_000_000.0] * 40
    low_volumes = [500_000.0] * 10
    result = calculate_indicators(make_prices(50), high_volumes + low_volumes)

    assert "Declining" in result["volume_trend"]
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/services/test_indicators.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.indicators'`

- [ ] **Step 4: Create services/indicators.py**

```python
import pandas as pd
import pandas_ta as ta


def calculate_indicators(close_prices: list, volumes: list) -> dict:
    """
    Calculate technical indicators from close price and volume history.

    Indicators requiring more data points than available are returned as None
    rather than raising — callers should handle None gracefully in display logic.

    Args:
        close_prices: Ordered list of closing prices (oldest first).
        volumes: Ordered list of volume values matching close_prices length.

    Returns:
        {rsi, sma20, sma50, ema12, ema26, volume_trend}
    """
    n = len(close_prices)

    if n < 2:
        return {
            "rsi": None,
            "sma20": None,
            "sma50": None,
            "ema12": None,
            "ema26": None,
            "volume_trend": "Insufficient data",
        }

    close = pd.Series(close_prices, dtype=float)

    def last_valid(series) -> float | None:
        """Return last non-NaN value from a pandas Series, or None."""
        if series is None:
            return None
        valid = series.dropna()
        return round(float(valid.iloc[-1]), 2) if len(valid) > 0 else None

    rsi = last_valid(ta.rsi(close, length=14) if n >= 15 else None)
    sma20 = last_valid(ta.sma(close, length=20) if n >= 20 else None)
    sma50 = last_valid(ta.sma(close, length=50) if n >= 50 else None)
    ema12 = last_valid(ta.ema(close, length=12) if n >= 13 else None)
    ema26 = last_valid(ta.ema(close, length=26) if n >= 27 else None)

    return {
        "rsi": rsi,
        "sma20": sma20,
        "sma50": sma50,
        "ema12": ema12,
        "ema26": ema26,
        "volume_trend": _calculate_volume_trend(volumes),
    }


def _calculate_volume_trend(volumes: list) -> str:
    """
    Compare recent volume (last 25% of data) to the overall average.
    Returns a human-readable string like 'Rising (+23%)' or 'Stable (+2%)'.
    """
    if len(volumes) < 4:
        return "Insufficient data"

    avg_volume = sum(volumes) / len(volumes)
    recent_count = max(1, len(volumes) // 4)
    recent_avg = sum(volumes[-recent_count:]) / recent_count

    pct_diff = ((recent_avg - avg_volume) / avg_volume) * 100

    if pct_diff > 10:
        return f"Rising (+{pct_diff:.0f}%)"
    elif pct_diff < -10:
        return f"Declining ({pct_diff:.0f}%)"
    else:
        return f"Stable ({pct_diff:+.0f}%)"
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/services/test_indicators.py -v
```

Expected: All 12 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add services/indicators.py tests/services/test_indicators.py
git commit -m "feat: add technical indicators service using pandas-ta

Implements calculate_indicators() returning RSI-14, SMA-20/50,
EMA-12/26, and volume trend from close price + volume history.
Indicators requiring more data than available return None so callers
can display 'N/A' rather than crashing. Volume trend compares the
most recent 25% of data to the overall average."
```

- [ ] **Step 7: Push and open PR**

```bash
git push -u origin feature/task-3-indicators-service
gh pr create --title "feat: add technical indicators service" --body "$(cat <<'EOF'
## Summary
- Implements `calculate_indicators(close_prices, volumes)` in `services/indicators.py`
- Returns RSI-14, SMA-20, SMA-50, EMA-12, EMA-26, and volume trend
- Returns `None` for indicators with insufficient data (not an error)
- 12 unit tests covering sufficient data, insufficient data, and volume trend direction

## Tech Notes
- pandas-ta operates on pandas Series; no DataFrame required for single-series indicators
- Volume trend uses last 25% of data vs overall average, threshold ±10%

## Test Plan
- [ ] `pytest tests/services/test_indicators.py -v` — all 12 tests pass
EOF
)"
```

---

## Task 4: Claude Analyst Service

**Branch:** `feature/task-4-claude-analyst-service`

**Files:**
- Create: `services/claude_analyst.py`
- Create: `tests/services/test_claude_analyst.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-4-claude-analyst-service
```

- [ ] **Step 2: Write failing tests**

Create `tests/services/test_claude_analyst.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from services.claude_analyst import ClaudeAnalyst


@pytest.fixture
def analyst():
    return ClaudeAnalyst()


def make_price_data(ticker="BTC", timeframe="30d"):
    return {
        "ticker": ticker,
        "current_price": 50000.0,
        "price_change_pct": 5.2,
        "market_cap": 1_000_000_000_000,
        "volume_24h": 50_000_000_000,
        "timeframe": timeframe,
    }


def make_indicators():
    return {
        "rsi": 62.5,
        "sma20": 48500.0,
        "sma50": 45000.0,
        "ema12": 49800.0,
        "ema26": 47500.0,
        "volume_trend": "Rising (+15%)",
    }


def test_generate_forecast_returns_string(analyst):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="**BTC — Senior Analyst Forecast**\n\nSummary...")]

    with patch.object(analyst.client.messages, "create", return_value=mock_message):
        result = analyst.generate_forecast(
            make_price_data(), make_indicators()
        )

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_forecast_includes_disclaimer(analyst):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Some forecast text")]

    with patch.object(analyst.client.messages, "create", return_value=mock_message):
        result = analyst.generate_forecast(
            make_price_data(), make_indicators()
        )

    assert "not financial advice" in result.lower()


def test_generate_forecast_passes_ticker_in_prompt(analyst):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="forecast")]
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    with patch.object(analyst.client.messages, "create", side_effect=capture):
        analyst.generate_forecast(make_price_data("ETH"), make_indicators())

    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "ETH" in prompt_text


def test_generate_forecast_handles_none_indicators(analyst):
    """None indicators (insufficient data) should not crash — show N/A in prompt."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="forecast with limited data")]

    indicators_with_nones = {
        "rsi": None,
        "sma20": None,
        "sma50": None,
        "ema12": 49800.0,
        "ema26": 47500.0,
        "volume_trend": "Insufficient data",
    }

    with patch.object(analyst.client.messages, "create", return_value=mock_message):
        result = analyst.generate_forecast(make_price_data(), indicators_with_nones)

    assert isinstance(result, str)
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/services/test_claude_analyst.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.claude_analyst'`

- [ ] **Step 4: Create services/claude_analyst.py**

```python
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a senior cryptocurrency financial analyst with 15 years of experience \
in digital asset markets. You provide rigorous, data-driven analysis based strictly on the \
technical indicators and market data provided. Your reports are structured, professional, and \
include specific price targets and clear recommendations. Never speculate beyond what the data shows."""

FORECAST_TEMPLATE = """Analyze {ticker} based on the following {timeframe} market data and provide a comprehensive forecast.

MARKET DATA:
- Current Price: ${current_price:,.4f}
- Price Change ({timeframe}): {price_change_pct:+.2f}%
- Market Cap: ${market_cap:,.0f}
- 24h Volume: ${volume_24h:,.0f}

TECHNICAL INDICATORS ({timeframe} data):
- RSI (14): {rsi}
- SMA 20: {sma20}
- SMA 50: {sma50}
- EMA 12: {ema12}
- EMA 26: {ema26}
- Volume Trend: {volume_trend}

Respond using EXACTLY this format:

**{ticker} — Senior Analyst Forecast** *(based on {timeframe} data)*

**Summary**
[2-3 sentence market overview]

**Key Signals**
- [Signal 1]
- [Signal 2]
- [Signal 3]

**Risk Factors**
- [Risk 1]
- [Risk 2]

**Price Target**
Short-term (7–14d): $X,XXX – $X,XXX

**Recommendation**
[HOLD/BUY/SELL] — [one-line rationale]

**Analyst Commentary**
[2-3 sentence narrative conclusion in plain English]"""

DISCLAIMER = "\n\n---\n⚠️ *This is not financial advice. Crypto markets are highly volatile.*"


def _fmt(value, prefix="$", decimals=2) -> str:
    """Format a numeric indicator value, returning 'N/A' if None."""
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.{decimals}f}"


class ClaudeAnalyst:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def generate_forecast(self, price_data: dict, indicators: dict) -> str:
        """
        Build a structured analyst report using Claude.

        Args:
            price_data: Output of CoinGeckoClient.get_price_data()
            indicators: Output of calculate_indicators()

        Returns:
            Formatted analyst report string with disclaimer appended.
        """
        prompt = FORECAST_TEMPLATE.format(
            ticker=price_data["ticker"],
            timeframe=price_data["timeframe"],
            current_price=price_data["current_price"],
            price_change_pct=price_data["price_change_pct"],
            market_cap=price_data["market_cap"],
            volume_24h=price_data["volume_24h"],
            rsi=indicators["rsi"] if indicators["rsi"] is not None else "N/A",
            sma20=_fmt(indicators["sma20"]),
            sma50=_fmt(indicators["sma50"]),
            ema12=_fmt(indicators["ema12"]),
            ema26=_fmt(indicators["ema26"]),
            volume_trend=indicators["volume_trend"],
        )

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text + DISCLAIMER
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/services/test_claude_analyst.py -v
```

Expected: All 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add services/claude_analyst.py tests/services/test_claude_analyst.py
git commit -m "feat: add Claude analyst service for forecast generation

Implements ClaudeAnalyst.generate_forecast() which formats market data
and technical indicators into a structured prompt for Claude. Returns a
formatted senior analyst report with sections for Summary, Key Signals,
Risk Factors, Price Target, Recommendation, and Analyst Commentary.
Appends a financial disclaimer to every response."
```

- [ ] **Step 7: Push and open PR**

```bash
git push -u origin feature/task-4-claude-analyst-service
gh pr create --title "feat: add Claude analyst service" --body "$(cat <<'EOF'
## Summary
- Implements `ClaudeAnalyst` in `services/claude_analyst.py`
- `generate_forecast(price_data, indicators)` builds a structured prompt and calls Claude API
- Uses claude-opus-4-6 with a senior analyst system prompt
- Appends financial disclaimer to every forecast response
- None indicator values are displayed as 'N/A' in the prompt

## Tech Notes
- System prompt instructs Claude to respond only based on provided data
- Template uses Python `.format()` for clean prompt construction
- Max tokens set to 1024 — sufficient for the structured report format

## Test Plan
- [ ] `pytest tests/services/test_claude_analyst.py -v` — all 4 tests pass
EOF
)"
```

---

## Task 5: Discord Slash Commands

**Branch:** `feature/task-5-slash-commands`

**Files:**
- Create: `cogs/crypto.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-5-slash-commands
```

- [ ] **Step 2: Create cogs/crypto.py**

```python
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    ANALYSIS_TIMEFRAMES,
    DEFAULT_ANALYSIS_TIMEFRAME,
    DEFAULT_PRICE_TIMEFRAME,
    PRICE_TIMEFRAMES,
    SUPPORTED_COINS,
)
from services.claude_analyst import ClaudeAnalyst
from services.coingecko import CoinGeckoClient
from services.indicators import calculate_indicators


def _format_large_number(n: float) -> str:
    """Format large numbers as $1.23T, $456.78B, $12.34M."""
    if n >= 1_000_000_000_000:
        return f"${n / 1_000_000_000_000:.2f}T"
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    return f"${n:,.2f}"


def _fmt_indicator(value, prefix="$") -> str:
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.2f}"


def _rsi_label(rsi) -> str:
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi} ⚠️ Overbought"
    if rsi <= 30:
        return f"{rsi} ⚠️ Oversold"
    return f"{rsi} Neutral"


class CryptoCog(commands.Cog):
    def __init__(self, bot: commands.Bot, coingecko: CoinGeckoClient, analyst: ClaudeAnalyst):
        self.bot = bot
        self.coingecko = coingecko
        self.analyst = analyst

    # -------------------------------------------------------------------------
    # /help
    # -------------------------------------------------------------------------

    @app_commands.command(name="help", description="Show available commands and supported coins")
    async def help_command(self, interaction: discord.Interaction):
        coin_list = ", ".join(SUPPORTED_COINS.keys())
        embed = discord.Embed(
            title="Crypto Bot — Commands",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="/price <coin> [timeframe]",
            value=f"Current price + change. Timeframes: {', '.join(PRICE_TIMEFRAMES)} (default: {DEFAULT_PRICE_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(
            name="/analyze <coin> [timeframe]",
            value=f"Price + RSI, SMA, EMA, volume trend. Timeframes: {', '.join(ANALYSIS_TIMEFRAMES)} (default: {DEFAULT_ANALYSIS_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(
            name="/forecast <coin> [timeframe]",
            value=f"AI analyst report (Claude). Timeframes: {', '.join(ANALYSIS_TIMEFRAMES)} (default: {DEFAULT_ANALYSIS_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(name="Supported Coins", value=coin_list, inline=False)
        embed.set_footer(text="Data: CoinGecko (free) | Analysis: Anthropic Claude")
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # /price
    # -------------------------------------------------------------------------

    @app_commands.command(name="price", description="Get current price and change over a timeframe")
    @app_commands.describe(
        coin="Coin ticker, e.g. BTC, ETH, SOL",
        timeframe="Time period for price change (default: 24h)",
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="1 hour", value="1h"),
            app_commands.Choice(name="24 hours", value="24h"),
            app_commands.Choice(name="3 days", value="3d"),
            app_commands.Choice(name="7 days", value="7d"),
        ]
    )
    async def price(
        self,
        interaction: discord.Interaction,
        coin: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_PRICE_TIMEFRAME

        try:
            data = self.coingecko.get_price_data(coin.upper(), tf)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error: {e}")
            return

        change = data["price_change_pct"]
        color = discord.Color.green() if change >= 0 else discord.Color.red()
        arrow = "▲" if change >= 0 else "▼"

        embed = discord.Embed(
            title=f"{data['ticker']} — Price",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Current Price", value=f"${data['current_price']:,.4f}", inline=True)
        embed.add_field(name=f"Change ({tf})", value=f"{arrow} {abs(change):.2f}%", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # spacer
        embed.add_field(name="Market Cap", value=_format_large_number(data["market_cap"]), inline=True)
        embed.add_field(name="24h Volume", value=_format_large_number(data["volume_24h"]), inline=True)
        embed.set_footer(text="Data: CoinGecko")
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # /analyze
    # -------------------------------------------------------------------------

    @app_commands.command(name="analyze", description="Technical analysis: RSI, SMA, EMA, volume trend")
    @app_commands.describe(
        coin="Coin ticker, e.g. BTC, ETH, SOL",
        timeframe="Analysis period (default: 30d)",
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="7 days", value="7d"),
            app_commands.Choice(name="30 days", value="30d"),
            app_commands.Choice(name="90 days", value="90d"),
            app_commands.Choice(name="180 days", value="180d"),
        ]
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        coin: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_ANALYSIS_TIMEFRAME

        from config import TIMEFRAME_TO_DAYS
        days = TIMEFRAME_TO_DAYS[tf]

        try:
            price_data = self.coingecko.get_price_data(coin.upper(), tf)
            chart = self.coingecko.get_market_chart(coin.upper(), days)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error: {e}")
            return

        indicators = calculate_indicators(chart["close_prices"], chart["volumes"])

        change = price_data["price_change_pct"]
        color = discord.Color.green() if change >= 0 else discord.Color.red()
        arrow = "▲" if change >= 0 else "▼"

        embed = discord.Embed(
            title=f"{coin.upper()} — Technical Analysis ({tf})",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Current Price", value=f"${price_data['current_price']:,.4f}", inline=True)
        embed.add_field(name=f"Change ({tf})", value=f"{arrow} {abs(change):.2f}%", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="RSI (14)", value=_rsi_label(indicators["rsi"]), inline=True)
        embed.add_field(name="SMA 20", value=_fmt_indicator(indicators["sma20"]), inline=True)
        embed.add_field(name="SMA 50", value=_fmt_indicator(indicators["sma50"]), inline=True)
        embed.add_field(name="EMA 12", value=_fmt_indicator(indicators["ema12"]), inline=True)
        embed.add_field(name="EMA 26", value=_fmt_indicator(indicators["ema26"]), inline=True)
        embed.add_field(name="Volume Trend", value=indicators["volume_trend"], inline=True)
        embed.set_footer(text="Data: CoinGecko | Indicators: pandas-ta")
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # /forecast
    # -------------------------------------------------------------------------

    @app_commands.command(name="forecast", description="AI-powered senior analyst forecast (Claude)")
    @app_commands.describe(
        coin="Coin ticker, e.g. BTC, ETH, SOL",
        timeframe="Analysis period for forecast (default: 30d)",
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="7 days", value="7d"),
            app_commands.Choice(name="30 days", value="30d"),
            app_commands.Choice(name="90 days", value="90d"),
            app_commands.Choice(name="180 days", value="180d"),
        ]
    )
    async def forecast(
        self,
        interaction: discord.Interaction,
        coin: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_ANALYSIS_TIMEFRAME

        from config import TIMEFRAME_TO_DAYS
        days = TIMEFRAME_TO_DAYS[tf]

        try:
            price_data = self.coingecko.get_price_data(coin.upper(), tf)
            chart = self.coingecko.get_market_chart(coin.upper(), days)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error: {e}")
            return

        indicators = calculate_indicators(chart["close_prices"], chart["volumes"])

        try:
            report = self.analyst.generate_forecast(price_data, indicators)
        except Exception as e:
            await interaction.followup.send(f"❌ Claude API error: {e}")
            return

        # Discord message limit is 2000 chars — split if needed
        if len(report) <= 2000:
            await interaction.followup.send(report)
        else:
            chunks = [report[i:i + 1990] for i in range(0, len(report), 1990)]
            for chunk in chunks:
                await interaction.followup.send(chunk)


async def setup(bot: commands.Bot):
    """Called by bot.load_extension('cogs.crypto')."""
    await bot.add_cog(CryptoCog(bot, CoinGeckoClient(), ClaudeAnalyst()))
```

- [ ] **Step 3: Run the full test suite to make sure nothing is broken**

```bash
pytest tests/ -v
```

Expected: All previously passing tests still PASS (cog itself has no unit tests — it is smoke-tested in Task 6).

- [ ] **Step 4: Commit**

```bash
git add cogs/crypto.py
git commit -m "feat: add Discord slash commands cog with /price /analyze /forecast /help

Implements all four slash commands using discord.py app_commands.
Commands defer immediately to handle CoinGecko + Claude latency within
Discord's 3-second response window. Responses use Discord embeds with
green/red coloring based on price change direction. Forecast responses
are split into 1990-char chunks to stay within Discord's 2000-char limit."
```

- [ ] **Step 5: Push and open PR**

```bash
git push -u origin feature/task-5-slash-commands
gh pr create --title "feat: add Discord slash commands cog" --body "$(cat <<'EOF'
## Summary
- Implements `cogs/crypto.py` with four slash commands: `/price`, `/analyze`, `/forecast`, `/help`
- All commands defer immediately (shows loading state) to handle async latency
- Price/analyze responses use Discord embeds with color-coded change direction
- Forecast responses are plain text (supports markdown) with auto-splitting for long outputs
- Unknown coin tickers return a friendly error message

## Tech Notes
- `setup(bot)` function follows discord.py extension pattern — called by `load_extension`
- Services injected at setup time: `CoinGeckoClient()` and `ClaudeAnalyst()`
- `/forecast` uses `interaction.followup.send()` in chunks if response > 2000 chars

## Test Plan
- [ ] `pytest tests/ -v` — all existing tests pass
- [ ] Smoke test in Task 6 covers live command testing
EOF
)"
```

---

## Task 6: Integration & Smoke Test

**Branch:** `feature/task-6-integration`

**Files:**
- No new files — this task verifies the full system works end-to-end

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-6-integration
```

- [ ] **Step 2: Confirm .env has both required keys**

Open `.env` and verify it contains:
```
TOKEN=your_discord_bot_token
ANTHROPIC_API_KEY=your_anthropic_api_key
```

Both values must be present. `TOKEN` is the Discord bot token from the Discord Developer Portal. `ANTHROPIC_API_KEY` is from console.anthropic.com.

- [ ] **Step 3: Run the full test suite one final time**

```bash
pytest tests/ -v
```

Expected: All tests PASS. Fix any failures before proceeding.

- [ ] **Step 4: Start the bot**

```bash
python bot.py
```

Expected output:
```
Slash commands synced.
Logged in as YourBot#1234
```

If you see `Slash commands synced.` the bot is live. Slash commands may take up to 1 hour to appear in Discord on the first run (global propagation). For instant testing during development, you can guild-sync by modifying `setup_hook` to pass a guild ID:

```python
# Temporary during development — guild sync is instant
TEST_GUILD = discord.Object(id=YOUR_GUILD_ID)  # replace with your server's ID
await self.tree.sync(guild=TEST_GUILD)
```

Remove the guild ID and use global sync before production.

- [ ] **Step 5: Smoke test each command in Discord**

In your Discord server, test each command and verify the expected output:

| Command | Expected |
|---------|---------|
| `/help` | Embed listing all 4 commands and 15 supported coins |
| `/price BTC` | Embed with current price, 24h % change, market cap, volume |
| `/price ETH 1h` | Embed with 1h % change |
| `/price SOL 3d` | Embed with 3d % change |
| `/analyze BTC 30d` | Embed with RSI, SMA-20/50, EMA-12/26, volume trend |
| `/analyze ETH 7d` | Embed — SMA-50 may show N/A (insufficient 7d data points) |
| `/forecast BTC 30d` | Multi-section analyst report from Claude |
| `/price FAKECOIN` | ❌ error message: coin not found |

- [ ] **Step 6: Commit smoke test confirmation**

```bash
git commit --allow-empty -m "chore: confirm smoke test passed for all slash commands

All four commands (/help, /price, /analyze, /forecast) verified working
end-to-end with live CoinGecko data and Claude API. Bot runs locally
via python bot.py."
```

- [ ] **Step 7: Push and open final PR**

```bash
git push -u origin feature/task-6-integration
gh pr create --title "chore: integration verification — all commands working" --body "$(cat <<'EOF'
## Summary
- Full end-to-end smoke test completed for all slash commands
- All unit tests passing
- Bot runs locally with live CoinGecko + Claude API

## Test Plan
- [ ] `pytest tests/ -v` — all tests pass
- [ ] `/help` — shows all commands and supported coins
- [ ] `/price BTC` — shows current price with 24h change
- [ ] `/price ETH 1h` — shows 1h change
- [ ] `/price SOL 3d` — shows 3d change
- [ ] `/analyze BTC 30d` — shows all technical indicators
- [ ] `/forecast BTC 30d` — Claude analyst report renders correctly
- [ ] `/price FAKECOIN` — returns friendly error
EOF
)"
```

---

## Self-Review Checklist

| Spec Requirement | Covered By |
|-----------------|-----------|
| Discord slash commands | Task 5: cogs/crypto.py |
| `/price` with timeframe | Task 5: price command, 1h/24h/3d/7d |
| `/analyze` with timeframe | Task 5: analyze command, 7d/30d/90d/180d |
| `/forecast` as senior analyst | Task 4: ClaudeAnalyst, Task 5: forecast command |
| `/help` | Task 5: help_command |
| CoinGecko free API | Task 2: coingecko.py |
| RSI, SMA, EMA indicators | Task 3: indicators.py |
| Supported coins (15 tickers) | Task 1: config.py |
| Feature branch per task | All tasks: Step 1 + Step 7 |
| Well-documented commits | All tasks: commit steps |
| PR after each branch | All tasks: gh pr create step |
| Forecast disclaimer | Task 4: DISCLAIMER constant |
| Structured forecast format | Task 4: FORECAST_TEMPLATE |
| Architecture to expand for sentiment | services/ layer — add services/sentiment.py |
