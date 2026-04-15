import os

import anthropic

from config import (
    COIN_DESCRIPTIONS,
    COMPARE_TEMPLATE,
    DERIVED_SIGNALS_TEMPLATE,
    DISCLAIMER,
    FORECAST_TEMPLATE,
    SYSTEM_PROMPT,
)

_MODEL = "claude-opus-4-6"


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
            if macd > 0:
                macd_signal = "Bullish momentum"
            elif macd < 0:
                macd_signal = "Bearish momentum"
            else:
                macd_signal = "Neutral (no divergence)"
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
        elif sma20 is not None:
            trend_structure = f"Partial — price {'above' if price > sma20 else 'below'} SMA20, SMA50 unavailable"
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
        print(f"Model:      {_MODEL}")
        print(f"Max tokens: 1024")
        print("\n--- SYSTEM PROMPT ---")
        print(SYSTEM_PROMPT)
        print("\n--- USER MESSAGE ---")
        print(prompt)
        print("=====================================")

        message = self.client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text + DISCLAIMER

    def compare_coins(
        self,
        ticker_a: str,
        price_data_a: dict,
        indicators_a: dict,
        ticker_b: str,
        price_data_b: dict,
        indicators_b: dict,
    ) -> str:
        """
        Call Claude to produce a 1-2 sentence verdict on which coin looks technically stronger.

        Args:
            ticker_a / ticker_b: coin ticker symbols (e.g. "BTC")
            price_data_a / price_data_b: output of CoinGeckoClient.get_price_data()
            indicators_a / indicators_b: output of calculate_indicators()

        Returns:
            Verdict string. Falls back to a neutral message if the API call fails.
        """
        def _macd_signal(ind: dict) -> str:
            ema12 = ind.get("ema12")
            ema26 = ind.get("ema26")
            if ema12 is None or ema26 is None:
                return "N/A"
            diff = ema12 - ema26
            if diff > 0:
                return f"Bullish (+${diff:,.2f})"
            if diff < 0:
                return f"Bearish (-${abs(diff):,.2f})"
            return "Neutral"

        def _fmt_indicator(value) -> str:
            if value is None:
                return "N/A"
            return f"${value:,.2f}"

        timeframe = price_data_a.get("timeframe", "30d")

        description_a = COIN_DESCRIPTIONS.get(ticker_a, f"{ticker_a} - cryptocurrency")
        description_b = COIN_DESCRIPTIONS.get(ticker_b, f"{ticker_b} - cryptocurrency")

        prompt = COMPARE_TEMPLATE.format(
            ticker_a=ticker_a,
            description_a=description_a,
            ticker_b=ticker_b,
            description_b=description_b,
            timeframe=timeframe,
            price_a=price_data_a["current_price"],
            change_a=price_data_a["price_change_pct"],
            rsi_a=indicators_a["rsi"] if indicators_a["rsi"] is not None else "N/A",
            sma20_a=_fmt_indicator(indicators_a["sma20"]),
            macd_signal_a=_macd_signal(indicators_a),
            vol_trend_a=indicators_a["volume_trend"],
            price_b=price_data_b["current_price"],
            change_b=price_data_b["price_change_pct"],
            rsi_b=indicators_b["rsi"] if indicators_b["rsi"] is not None else "N/A",
            sma20_b=_fmt_indicator(indicators_b["sma20"]),
            macd_signal_b=_macd_signal(indicators_b),
            vol_trend_b=indicators_b["volume_trend"],
        )

        try:
            message = self.client.messages.create(
                model=_MODEL,
                max_tokens=256,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception:
            return f"Comparison unavailable — could not reach analyst. Check individual /forecast for each coin."
