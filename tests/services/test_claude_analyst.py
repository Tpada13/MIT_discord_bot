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
