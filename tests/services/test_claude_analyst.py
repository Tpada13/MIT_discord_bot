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
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    indicators_with_nones = {
        "rsi": None,
        "sma20": None,
        "sma50": None,
        "ema12": 49800.0,
        "ema26": 47500.0,
        "volume_trend": "Insufficient data",
    }

    with patch.object(analyst.client.messages, "create", side_effect=capture):
        result = analyst.generate_forecast(make_price_data(), indicators_with_nones)

    assert isinstance(result, str)
    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "N/A" in prompt_text


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


def test_generate_forecast_derived_signals_values(analyst):
    """Derived signal values (ABOVE/BELOW, MACD, trend) must be computed correctly."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="forecast")]
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    # price=50000 > sma20=48500 and sma50=45000 → ABOVE both → Bullish trend
    # ema12=49800 > ema26=47500 → macd=+2300 → Bullish momentum
    with patch.object(analyst.client.messages, "create", side_effect=capture):
        analyst.generate_forecast(make_price_data(), make_indicators())

    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "Price vs SMA20: ABOVE" in prompt_text
    assert "Price vs SMA50: ABOVE" in prompt_text
    assert "+$2,300.00" in prompt_text
    assert "Bullish momentum" in prompt_text
    assert "Trend Structure: Bullish" in prompt_text


# ---------------------------------------------------------------------------
# compare_coins() tests
# ---------------------------------------------------------------------------

def make_price_data_for(ticker, price=50000.0, change=2.5, timeframe="30d"):
    return {
        "ticker": ticker,
        "current_price": price,
        "price_change_pct": change,
        "market_cap": 1_000_000_000_000,
        "volume_24h": 50_000_000_000,
        "timeframe": timeframe,
    }


def test_compare_coins_returns_string(analyst):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="BTC looks stronger due to bullish RSI.")]

    with patch.object(analyst.client.messages, "create", return_value=mock_message):
        result = analyst.compare_coins(
            "BTC", make_price_data_for("BTC"), make_indicators(),
            "ETH", make_price_data_for("ETH", price=3000.0, change=-1.2), make_indicators(),
        )

    assert isinstance(result, str)
    assert len(result) > 0


def test_compare_coins_includes_both_tickers_in_prompt(analyst):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="verdict")]
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    with patch.object(analyst.client.messages, "create", side_effect=capture):
        analyst.compare_coins(
            "BTC", make_price_data_for("BTC"), make_indicators(),
            "SOL", make_price_data_for("SOL", price=150.0), make_indicators(),
        )

    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "BTC" in prompt_text
    assert "SOL" in prompt_text


def test_compare_coins_fallback_on_api_error(analyst):
    """If the Claude API raises, compare_coins returns a fallback string mentioning /forecast."""
    with patch.object(analyst.client.messages, "create", side_effect=Exception("API error")):
        result = analyst.compare_coins(
            "BTC", make_price_data_for("BTC"), make_indicators(),
            "ETH", make_price_data_for("ETH", price=3000.0, change=-1.2), make_indicators(),
        )

    assert isinstance(result, str)
    assert "/forecast" in result


def test_compare_coins_macd_signal_in_prompt(analyst):
    """MACD signal string must be computed correctly and appear in the prompt."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="verdict")]
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    # ema12=49800 > ema26=47500 → diff=+2300 → Bullish
    with patch.object(analyst.client.messages, "create", side_effect=capture):
        analyst.compare_coins(
            "BTC", make_price_data_for("BTC"), make_indicators(),
            "ETH", make_price_data_for("ETH", price=3000.0, change=-1.2), make_indicators(),
        )

    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "Bullish" in prompt_text
    assert "2,300.00" in prompt_text


def test_compare_coins_handles_none_indicators(analyst):
    """None indicator values must not crash — should appear as N/A in prompt."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="verdict")]
    captured_kwargs = {}

    def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    none_indicators = {
        "rsi": None,
        "sma20": None,
        "sma50": None,
        "ema12": None,
        "ema26": None,
        "volume_trend": "Insufficient data",
    }

    with patch.object(analyst.client.messages, "create", side_effect=capture):
        result = analyst.compare_coins(
            "BTC", make_price_data_for("BTC"), make_indicators(),
            "ETH", make_price_data_for("ETH", price=3000.0, change=-1.2), none_indicators,
        )

    assert isinstance(result, str)
    prompt_text = captured_kwargs["messages"][0]["content"]
    assert "N/A" in prompt_text
