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
