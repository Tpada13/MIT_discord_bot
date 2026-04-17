import pytest

from services.chart import generate_price_chart


def make_prices(n: int) -> list[float]:
    return [100.0 + i * 0.5 for i in range(n)]


def make_volumes(n: int) -> list[float]:
    return [1_000_000.0 + i * 10_000 for i in range(n)]


def test_generate_price_chart_returns_bytes():
    """Standard 30d dataset (~720 hourly points) returns non-empty bytes."""
    result = generate_price_chart("BTC", make_prices(720), make_volumes(720), "30d")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_price_chart_minimal_data():
    """7 data points is below the SMA20 window — must not raise, must return bytes."""
    result = generate_price_chart("ETH", make_prices(7), make_volumes(7), "7d")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_price_chart_different_timeframes():
    """Timeframe string only affects the chart title — both labels must work."""
    prices = make_prices(168)  # ~7 days hourly
    volumes = make_volumes(168)
    result_7d = generate_price_chart("SOL", prices, volumes, "7d")
    result_180d = generate_price_chart("SOL", prices, volumes, "180d")
    assert isinstance(result_7d, bytes) and len(result_7d) > 0
    assert isinstance(result_180d, bytes) and len(result_180d) > 0
