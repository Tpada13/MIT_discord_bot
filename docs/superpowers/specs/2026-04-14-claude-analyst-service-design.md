# Claude Analyst Service — Design Spec

**Date:** 2026-04-14  
**Task:** Task 4 — Claude Analyst Service  
**Branch:** `feature/task-4-claude-analyst-service`

---

## Goal

Replace the stub `ClaudeAnalyst` with a real implementation that calls the Anthropic API and returns a structured senior analyst forecast. Enrich the prompt with a strong system prompt, derived technical signals, and per-coin context so Claude produces analysis that is meaningfully better than a generic crypto bot.

---

## File Changes

| File | Change |
|------|--------|
| `config.py` | Add `SYSTEM_PROMPT`, `FORECAST_TEMPLATE`, `DERIVED_SIGNALS_TEMPLATE`, `DISCLAIMER`, `COIN_DESCRIPTIONS` |
| `services/claude_analyst.py` | Full implementation — imports prompt constants from config, computes derived signals, logs full API call to terminal, calls Anthropic API |
| `cogs/crypto.py` | Pass `coin_description` to `generate_forecast` |
| `tests/services/test_claude_analyst.py` | 5 tests (4 from original spec + 1 for derived signals) |

---

## config.py Additions

All prompt strings live in `config.py` for easy manual tuning without touching service code.

### `SYSTEM_PROMPT`

```python
SYSTEM_PROMPT = """\
You are a senior cryptocurrency financial analyst with 15+ years of experience \
in digital asset markets.

INTERPRETATION GUIDELINES:
- RSI <30: oversold — watch for reversal up
- RSI >70: overbought — watch for reversal down
- RSI 30–70: neutral momentum
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
```

### `DERIVED_SIGNALS_TEMPLATE`

Format string with placeholders filled by `generate_forecast` from existing `price_data` and `indicators`. No new API calls.

```python
DERIVED_SIGNALS_TEMPLATE = """\

DERIVED SIGNALS:
- Price vs SMA20: {price_vs_sma20}
- Price vs SMA50: {price_vs_sma50}
- MACD Proxy (EMA12 − EMA26): {macd_value} — {macd_signal}
- Trend Structure: {trend_structure}\
"""
```

Placeholder logic (computed in `generate_forecast`):

| Placeholder | Logic |
|---|---|
| `price_vs_sma20` | `ABOVE` / `BELOW` / `N/A` (if `sma20` is None) |
| `price_vs_sma50` | `ABOVE` / `BELOW` / `N/A` (if `sma50` is None) |
| `macd_value` | `f"+${ema12-ema26:,.2f}"` / `f"-${abs(ema12-ema26):,.2f}"` / `N/A` |
| `macd_signal` | `Bullish momentum` / `Bearish momentum` / `N/A` |
| `trend_structure` | `Bullish` (price > both MAs) / `Bearish` (price < both MAs) / `Mixed` / `Insufficient data` |

### `FORECAST_TEMPLATE`

The full user message. Includes `{coin_description}` at the top, market data, technical indicators, the `DERIVED_SIGNALS_TEMPLATE` block, and the structured output format.

```python
FORECAST_TEMPLATE = """\
ASSET: {ticker} — {coin_description}

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
[2-3 sentence narrative conclusion in plain English]\
"""
```

### `DISCLAIMER`

```python
DISCLAIMER = "\n\n---\n⚠️ *This is not financial advice. Crypto markets are highly volatile.*"
```

### `COIN_DESCRIPTIONS`

One-liner per coin providing category context for the analyst:

```python
COIN_DESCRIPTIONS = {
    "BTC":  "Bitcoin — decentralized digital currency, largest by market cap, primary store of value",
    "ETH":  "Ethereum — smart contract platform, backbone of DeFi and NFT ecosystems",
    "SOL":  "Solana — high-throughput L1 blockchain, strong NFT and DeFi ecosystem",
    "BNB":  "BNB — Binance exchange token, powers BNB Chain ecosystem",
    "XRP":  "XRP — payments-focused cryptocurrency, used for cross-border settlement",
    "ADA":  "Cardano — proof-of-stake L1 blockchain with academic research focus",
    "DOGE": "Dogecoin — meme-origin cryptocurrency with large retail following",
    "AVAX": "Avalanche — fast L1 blockchain with subnet architecture for custom chains",
    "XDC":  "XDC Network — enterprise-grade blockchain for trade finance",
    "LINK": "Chainlink — decentralized oracle network connecting smart contracts to real-world data",
    "SUI":  "Sui — high-performance L1 blockchain with object-based data model",
    "ZRO":  "LayerZero — cross-chain interoperability protocol",
    "ONDO": "Ondo Finance — real-world asset (RWA) tokenization protocol",
    "CRV":  "Curve Finance — decentralized stablecoin exchange, dominant in DeFi liquidity",
    "SEI":  "Sei — L1 blockchain optimized for trading and order-book DEXs",
}
```

Falls back to `f"{ticker} — cryptocurrency"` for any ticker not in the dict.

---

## services/claude_analyst.py

```python
import os
import anthropic
from config import (
    COIN_DESCRIPTIONS, DERIVED_SIGNALS_TEMPLATE, DISCLAIMER,
    FORECAST_TEMPLATE, SYSTEM_PROMPT,
)

def _fmt(value, prefix="$", decimals=2) -> str:
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
        ticker = price_data["ticker"]
        price = price_data["current_price"]
        sma20 = indicators["sma20"]
        sma50 = indicators["sma50"]
        ema12 = indicators["ema12"]
        ema26 = indicators["ema26"]

        # --- derived signals ---
        price_vs_sma20 = ("ABOVE" if price > sma20 else "BELOW") if sma20 else "N/A"
        price_vs_sma50 = ("ABOVE" if price > sma50 else "BELOW") if sma50 else "N/A"
        if ema12 is not None and ema26 is not None:
            macd = ema12 - ema26
            macd_value = f"+${macd:,.2f}" if macd >= 0 else f"-${abs(macd):,.2f}"
            macd_signal = "Bullish momentum" if macd >= 0 else "Bearish momentum"
        else:
            macd_value = macd_signal = "N/A"

        if sma20 and sma50:
            trend_structure = "Bullish" if price > sma20 and price > sma50 else (
                "Bearish" if price < sma20 and price < sma50 else "Mixed"
            )
        else:
            trend_structure = "Insufficient data"

        derived_signals = DERIVED_SIGNALS_TEMPLATE.format(
            price_vs_sma20=price_vs_sma20,
            price_vs_sma50=price_vs_sma50,
            macd_value=macd_value,
            macd_signal=macd_signal,
            trend_structure=trend_structure,
        )

        description = coin_description or COIN_DESCRIPTIONS.get(ticker, f"{ticker} — cryptocurrency")

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

---

## cogs/crypto.py Change

In the `/forecast` command, look up the coin description and pass it through:

```python
from config import COIN_DESCRIPTIONS

# inside forecast():
coin_description = COIN_DESCRIPTIONS.get(coin.upper())
result = await self.analyst.generate_forecast(price_data, indicators, coin_description)
```

---

## Tests

5 tests in `tests/services/test_claude_analyst.py`, all using `patch.object` on `analyst.client.messages.create` — no live API calls:

| Test | Asserts |
|------|---------|
| `test_generate_forecast_returns_string` | Result is a non-empty string |
| `test_generate_forecast_includes_disclaimer` | "not financial advice" in result (case-insensitive) |
| `test_generate_forecast_passes_ticker_in_prompt` | Ticker appears in the captured prompt |
| `test_generate_forecast_handles_none_indicators` | None indicators don't crash |
| `test_generate_forecast_includes_derived_signals` | "DERIVED SIGNALS" appears in the captured prompt |

---

## API Call

```python
self.client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": prompt}],
)
```

---

## Environment Variable

`ANTHROPIC` — read via `os.getenv("ANTHROPIC")` (set in `.env`, loaded by `bot.py` at startup).
