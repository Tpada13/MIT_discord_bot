# Claude Analyst Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub `ClaudeAnalyst` with a real Anthropic API implementation that builds an enriched prompt from market data, derived technical signals, and per-coin context, then returns a structured senior analyst forecast.

**Architecture:** All prompt strings (`SYSTEM_PROMPT`, `FORECAST_TEMPLATE`, `DERIVED_SIGNALS_TEMPLATE`, `DISCLAIMER`, `COIN_DESCRIPTIONS`) live in `config.py` for easy manual tuning. `ClaudeAnalyst.generate_forecast` computes derived signals from existing data, renders the prompt, logs the full API call to stdout, and calls Claude. The `/forecast` cog command is updated to pass a coin description through.

**Tech Stack:** Python 3.10+, anthropic SDK, python-dotenv, pytest, discord.py

---

## File Map

| File | Change |
|------|--------|
| `config.py` | Add `SYSTEM_PROMPT`, `FORECAST_TEMPLATE`, `DERIVED_SIGNALS_TEMPLATE`, `DISCLAIMER`, `COIN_DESCRIPTIONS` |
| `services/claude_analyst.py` | Full implementation — replaces stub |
| `cogs/crypto.py` | Pass `coin_description` to `generate_forecast` in `/forecast` command |
| `tests/services/test_claude_analyst.py` | 5 unit tests (mocked Anthropic — no live API calls) |

---

## Task 1: Feature Branch + Config Prompt Constants

**Branch:** `feature/task-4-claude-analyst-service`

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull
git checkout -b feature/task-4-claude-analyst-service
```

- [ ] **Step 2: Add prompt constants to config.py**

Open `config.py` and append the following after the existing `TIMEFRAME_TO_DAYS` block:

```python
# ---------------------------------------------------------------------------
# Claude Analyst — prompt constants
# All strings live here so they can be tuned without touching service code.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a senior cryptocurrency financial analyst with 15+ years of experience \
in digital asset markets.

INTERPRETATION GUIDELINES:
- RSI <30: oversold — watch for reversal up
- RSI >70: overbought — watch for reversal down
- RSI 30-70: neutral momentum
- Price above SMA20 and SMA50: bullish trend structure
- Price below SMA20 and SMA50: bearish trend structure
- EMA12 > EMA26 (positive MACD): bullish momentum
- EMA12 < EMA26 (negative MACD): bearish momentum
- Rising volume confirms trend; declining volume = weakening conviction
- When signals conflict: acknowledge it, weigh recency and magnitude, don't force conviction

MARKET CONTEXT:
- Crypto trades 24/7 with higher volatility than equities
- Macro events (Fed rates, regulation) can override technicals instantly
- Adjust confidence when indicators show N/A (insufficient data)

RULES:
- Base analysis strictly on the data provided — never fabricate price history
- Always give specific price target ranges, not vague language
- Flag insufficient data explicitly and lower confidence accordingly\
"""

DERIVED_SIGNALS_TEMPLATE = """\

DERIVED SIGNALS:
- Price vs SMA20: {price_vs_sma20}
- Price vs SMA50: {price_vs_sma50}
- MACD Proxy (EMA12 - EMA26): {macd_value} - {macd_signal}
- Trend Structure: {trend_structure}\
"""

FORECAST_TEMPLATE = """\
ASSET: {ticker} - {coin_description}

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
{derived_signals}

Analyze {ticker} based on the above {timeframe} data and provide a comprehensive forecast.
Respond using EXACTLY this format:

**{ticker} -- Senior Analyst Forecast** *(based on {timeframe} data)*

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
Short-term (7-14d): $X,XXX - $X,XXX

**Recommendation**
[HOLD/BUY/SELL] -- [one-line rationale]

**Analyst Commentary**
[2-3 sentence narrative conclusion in plain English]\
"""

DISCLAIMER = "\n\n---\n\u26a0\ufe0f *This is not financial advice. Crypto markets are highly volatile.*"

COIN_DESCRIPTIONS = {
    "BTC":  "Bitcoin - decentralized digital currency, largest by market cap, primary store of value",
    "ETH":  "Ethereum - smart contract platform, backbone of DeFi and NFT ecosystems",
    "SOL":  "Solana - high-throughput L1 blockchain, strong NFT and DeFi ecosystem",
    "BNB":  "BNB - Binance exchange token, powers BNB Chain ecosystem",
    "XRP":  "XRP - payments-focused cryptocurrency, used for cross-border settlement",
    "ADA":  "Cardano - proof-of-stake L1 blockchain with academic research focus",
    "DOGE": "Dogecoin - meme-origin cryptocurrency with large retail following",
    "AVAX": "Avalanche - fast L1 blockchain with subnet architecture for custom chains",
    "XDC":  "XDC Network - enterprise-grade blockchain for trade finance",
    "LINK": "Chainlink - decentralized oracle network connecting smart contracts to real-world data",
    "SUI":  "Sui - high-performance L1 blockchain with object-based data model",
    "ZRO":  "LayerZero - cross-chain interoperability protocol",
    "ONDO": "Ondo Finance - real-world asset (RWA) tokenization protocol",
    "CRV":  "Curve Finance - decentralized stablecoin exchange, dominant in DeFi liquidity",
    "SEI":  "Sei - L1 blockchain optimized for trading and order-book DEXs",
}
```

- [ ] **Step 3: Verify config imports cleanly**

```bash
python -c "from config import SYSTEM_PROMPT, FORECAST_TEMPLATE, DERIVED_SIGNALS_TEMPLATE, DISCLAIMER, COIN_DESCRIPTIONS; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add config.py
git commit -m "feat: add Claude analyst prompt constants to config

Moves all Claude prompt strings (SYSTEM_PROMPT, FORECAST_TEMPLATE,
DERIVED_SIGNALS_TEMPLATE, DISCLAIMER) and COIN_DESCRIPTIONS into
config.py so they can be tuned without touching service code."
```

---

## Task 2: Tests + ClaudeAnalyst Implementation

**Files:**
- Create: `tests/services/test_claude_analyst.py`
- Modify: `services/claude_analyst.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_claude_analyst.py`:

```python
import os
from unittest.mock import MagicMock, patch

import pytest

from services.claude_analyst import ClaudeAnalyst


@pytest.fixture
def analyst():
    # Provide a dummy key so the Anthropic client constructs without error.
    # All actual API calls are mocked per-test.
    with patch.dict(os.environ, {"ANTHROPIC": "test-key-dummy"}):
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
    mock_message.content = [MagicMock(text="**BTC -- Senior Analyst Forecast**\n\nSummary...")]

    with patch.object(analyst.client.messages, "create", return_value=mock_message):
        result = analyst.generate_forecast(make_price_data(), make_indicators())

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_forecast_includes_disclaimer(analyst):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Some forecast text")]

    with patch.object(analyst.client.messages, "create", return_value=mock_message):
        result = analyst.generate_forecast(make_price_data(), make_indicators())

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
    """None indicators (insufficient data) must not crash — show N/A in prompt."""
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


def test_generate_forecast_includes_derived_signals(analyst):
    """DERIVED SIGNALS block must appear in the prompt sent to the API."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="forecast")]
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    with patch.object(analyst.client.messages, "create", side_effect=capture):
        analyst.generate_forecast(make_price_data(), make_indicators())

    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "DERIVED SIGNALS" in prompt_text
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/services/test_claude_analyst.py -v
```

Expected: 5 failures with `ImportError` or `AttributeError` (stub has no `client` attribute).

- [ ] **Step 3: Implement services/claude_analyst.py**

Replace the entire file:

```python
import os

import anthropic

from config import (
    COIN_DESCRIPTIONS,
    DERIVED_SIGNALS_TEMPLATE,
    DISCLAIMER,
    FORECAST_TEMPLATE,
    SYSTEM_PROMPT,
)


def _fmt(value, prefix="$", decimals=2) -> str:
    """Format a numeric indicator value, returning 'N/A' if None."""
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.{decimals}f}"


class ClaudeAnalyst:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC"))

    def generate_forecast(
        self,
        price_data: dict,
        indicators: dict,
        coin_description: str | None = None,
    ) -> str:
        """
        Build an enriched analyst prompt and call Claude to generate a forecast.

        Args:
            price_data: Output of CoinGeckoClient.get_price_data()
            indicators: Output of calculate_indicators()
            coin_description: Optional one-liner about the coin; falls back to
                              COIN_DESCRIPTIONS[ticker] then a generic string.

        Returns:
            Formatted analyst report string with disclaimer appended.
        """
        ticker = price_data["ticker"]
        price = price_data["current_price"]
        sma20 = indicators["sma20"]
        sma50 = indicators["sma50"]
        ema12 = indicators["ema12"]
        ema26 = indicators["ema26"]

        # --- derived signals ---
        price_vs_sma20 = ("ABOVE" if price > sma20 else "BELOW") if sma20 is not None else "N/A"
        price_vs_sma50 = ("ABOVE" if price > sma50 else "BELOW") if sma50 is not None else "N/A"

        if ema12 is not None and ema26 is not None:
            macd = ema12 - ema26
            macd_value = f"+${macd:,.2f}" if macd >= 0 else f"-${abs(macd):,.2f}"
            macd_signal = "Bullish momentum" if macd >= 0 else "Bearish momentum"
        else:
            macd_value = "N/A"
            macd_signal = "N/A"

        if sma20 is not None and sma50 is not None:
            if price > sma20 and price > sma50:
                trend_structure = "Bullish"
            elif price < sma20 and price < sma50:
                trend_structure = "Bearish"
            else:
                trend_structure = "Mixed"
        else:
            trend_structure = "Insufficient data"

        derived_signals = DERIVED_SIGNALS_TEMPLATE.format(
            price_vs_sma20=price_vs_sma20,
            price_vs_sma50=price_vs_sma50,
            macd_value=macd_value,
            macd_signal=macd_signal,
            trend_structure=trend_structure,
        )

        description = (
            coin_description
            or COIN_DESCRIPTIONS.get(ticker)
            or f"{ticker} - cryptocurrency"
        )

        prompt = FORECAST_TEMPLATE.format(
            ticker=ticker,
            coin_description=description,
            timeframe=price_data["timeframe"],
            current_price=price,
            price_change_pct=price_data["price_change_pct"],
            market_cap=price_data["market_cap"],
            volume_24h=price_data["volume_24h"],
            rsi=indicators["rsi"] if indicators["rsi"] is not None else "N/A",
            sma20=_fmt(sma20),
            sma50=_fmt(sma50),
            ema12=_fmt(ema12),
            ema26=_fmt(ema26),
            volume_trend=indicators["volume_trend"],
            derived_signals=derived_signals,
        )

        # --- terminal debug logging ---
        print("========== CLAUDE API CALL ==========")
        print(f"Model:      claude-opus-4-6")
        print(f"Max tokens: 1024")
        print("\n--- SYSTEM PROMPT ---")
        print(SYSTEM_PROMPT)
        print("\n--- USER MESSAGE ---")
        print(prompt)
        print("=====================================")

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text + DISCLAIMER
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/services/test_claude_analyst.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
python -m pytest tests/ -v
```

Expected: 27 tests PASSED (22 existing + 5 new).

- [ ] **Step 6: Commit**

```bash
git add services/claude_analyst.py tests/services/test_claude_analyst.py
git commit -m "feat: implement ClaudeAnalyst with enriched prompt and debug logging

Replaces stub with real Anthropic API integration. generate_forecast()
computes derived signals (price-vs-MAs, MACD proxy, trend structure)
from existing indicator data, renders the full prompt from config
constants, logs the complete API call to stdout for debugging, then
calls claude-opus-4-6. All prompt strings live in config.py."
```

---

## Task 3: Update /forecast Command to Pass Coin Description

**Files:**
- Modify: `cogs/crypto.py`

- [ ] **Step 1: Add COIN_DESCRIPTIONS to the import from config**

In `cogs/crypto.py`, find the existing import block at the top:

```python
from config import (
    ANALYSIS_TIMEFRAMES,
    DEFAULT_ANALYSIS_TIMEFRAME,
    DEFAULT_PRICE_TIMEFRAME,
    PRICE_TIMEFRAMES,
    SUPPORTED_COINS,
)
```

Replace it with:

```python
from config import (
    ANALYSIS_TIMEFRAMES,
    COIN_DESCRIPTIONS,
    DEFAULT_ANALYSIS_TIMEFRAME,
    DEFAULT_PRICE_TIMEFRAME,
    PRICE_TIMEFRAMES,
    SUPPORTED_COINS,
)
```

- [ ] **Step 2: Pass coin_description to generate_forecast**

In `cogs/crypto.py`, find the `/forecast` command body where `generate_forecast` is called:

```python
        try:
            report = self.analyst.generate_forecast(price_data, indicators)
        except Exception as e:
            await interaction.followup.send(f"❌ Analyst error: {e}")
            return
```

Replace it with:

```python
        coin_description = COIN_DESCRIPTIONS.get(coin.upper())
        try:
            report = self.analyst.generate_forecast(price_data, indicators, coin_description)
        except Exception as e:
            await interaction.followup.send(f"❌ Analyst error: {e}")
            return
```

- [ ] **Step 3: Run full test suite to confirm nothing broke**

```bash
python -m pytest tests/ -v
```

Expected: 27 tests PASSED.

- [ ] **Step 4: Commit**

```bash
git add cogs/crypto.py
git commit -m "feat: pass coin description to ClaudeAnalyst in /forecast command

Looks up the coin's one-liner description from COIN_DESCRIPTIONS and
forwards it to generate_forecast so Claude has category context
(e.g. 'Bitcoin - decentralized digital currency...') in the prompt."
```

---

## Task 4: Push and Open PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feature/task-4-claude-analyst-service
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "feat: add Claude analyst service for AI-powered forecasts" --body "$(cat <<'EOF'
## Summary
- Implements \`ClaudeAnalyst.generate_forecast()\` replacing the stub
- All prompt strings (\`SYSTEM_PROMPT\`, \`FORECAST_TEMPLATE\`, \`DERIVED_SIGNALS_TEMPLATE\`, \`DISCLAIMER\`, \`COIN_DESCRIPTIONS\`) moved to \`config.py\` for easy manual tuning
- Enriched prompt includes derived signals: price vs SMA20/50, MACD proxy (EMA12−EMA26), and trend structure — computed from existing indicator data, no extra API calls
- Per-coin context descriptions added for all 15 supported tickers
- Full API call (system prompt + user message + model/tokens) logged to stdout on every \`/forecast\`

## Tech Notes
- Uses \`claude-opus-4-6\` with \`max_tokens=1024\`
- API key read from \`ANTHROPIC\` env var (set in \`.env\`)
- \`coin_description\` parameter is optional with fallback chain: caller-provided → \`COIN_DESCRIPTIONS\` dict → generic string
- \`DERIVED_SIGNALS_TEMPLATE\` is rendered first, then injected into \`FORECAST_TEMPLATE\` as \`{derived_signals}\` — avoids nested format-string issues

## Test Plan
- [ ] \`python -m pytest tests/ -v\` — 27 tests pass (22 existing + 5 new)
- [ ] \`python bot.py\` starts cleanly
- [ ] \`/forecast BTC 30d\` — terminal shows full API call log, Discord shows structured report
- [ ] \`/forecast ETH 7d\` — N/A indicators handled gracefully (7d may have insufficient data for SMA50)
- [ ] \`/forecast FAKECOIN\` — returns friendly error from CoinGecko layer before Claude is called
EOF
)"
```

---

## Self-Review

### Spec Coverage

| Spec Requirement | Task |
|-----------------|------|
| `SYSTEM_PROMPT` in `config.py` | Task 1 |
| `FORECAST_TEMPLATE` in `config.py` | Task 1 |
| `DERIVED_SIGNALS_TEMPLATE` in `config.py` | Task 1 |
| `DISCLAIMER` in `config.py` | Task 1 |
| `COIN_DESCRIPTIONS` in `config.py` | Task 1 |
| `ClaudeAnalyst.__init__` reads `ANTHROPIC` env var | Task 2 |
| Derived signals: price vs SMA20/50 | Task 2 |
| Derived signals: MACD proxy + signal | Task 2 |
| Derived signals: trend structure | Task 2 |
| Full API call logged to stdout | Task 2 |
| `generate_forecast` accepts optional `coin_description` | Task 2 |
| Fallback chain for coin description | Task 2 |
| 5 unit tests (mocked, no live calls) | Task 2 |
| `/forecast` passes `coin_description` | Task 3 |
| PR with test plan checklist | Task 4 |
