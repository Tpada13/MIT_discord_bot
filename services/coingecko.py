import os

import requests

from config import SUPPORTED_COINS, TIMEFRAME_TO_DAYS


class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self._api_key = os.getenv("COINGECKO")

    def _auth_params(self) -> dict:
        """Return API key param if configured, else empty dict."""
        return {"x_cg_demo_api_key": self._api_key} if self._api_key else {}

    def _ticker_to_id(self, ticker: str) -> str:
        """Map ticker symbol to CoinGecko coin ID. Falls back to lowercase ticker."""
        return SUPPORTED_COINS.get(ticker.upper(), ticker.lower())

    def get_price_data(self, ticker: str, timeframe: str = "24h") -> dict:
        """
        Fetch current price and % change over the requested timeframe.

        For 1h/24h/7d: single call to /coins/markets (CoinGecko provides these natively).
        For 3d/30d/90d/180d: two calls — /coins/markets for current data +
                /coins/{id}/market_chart for historical prices to calculate the change.

        Returns:
            {ticker, current_price, price_change_pct, market_cap, volume_24h, timeframe}

        Raises:
            ValueError: if the timeframe is unsupported or the coin is not found on CoinGecko.
        """
        if timeframe not in TIMEFRAME_TO_DAYS:
            raise ValueError(f"Invalid timeframe '{timeframe}'. Valid options: {list(TIMEFRAME_TO_DAYS.keys())}")

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
        response = requests.get(url, params={**params, **self._auth_params()}, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ValueError(f"Coin '{ticker.upper()}' not found on CoinGecko.")

        coin = data[0]

        if timeframe == "1h":
            pct_change = coin.get("price_change_percentage_1h_in_currency") or 0.0
        elif timeframe == "7d":
            pct_change = coin.get("price_change_percentage_7d_in_currency") or 0.0
        elif timeframe in ("3d", "30d", "90d", "180d"):
            chart = self.get_market_chart(ticker, days=TIMEFRAME_TO_DAYS[timeframe])
            prices = chart["close_prices"]
            pct_change = ((prices[-1] - prices[0]) / prices[0]) * 100 if len(prices) >= 2 else 0.0
        else:  # 24h
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

        response = requests.get(url, params={**params, **self._auth_params()}, timeout=10)
        response.raise_for_status()
        data = response.json()

        return {
            "ticker": ticker.upper(),
            "days": days,
            "close_prices": [point[1] for point in data["prices"]],
            "volumes": [point[1] for point in data["total_volumes"]],
            "timestamps": [point[0] for point in data["prices"]],
        }
