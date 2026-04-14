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
        dict with keys: rsi, sma20, sma50, ema12, ema26, volume_trend
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
