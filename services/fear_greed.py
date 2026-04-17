from datetime import datetime, timezone

import requests


class FearGreedClient:
    BASE_URL = "https://api.alternative.me/fng/"

    def get_current(self) -> dict:
        """
        Fetches the current and previous day's Fear & Greed Index.

        Returns:
            {
                "value": int,
                "classification": str,
                "timestamp": str,               # ISO date YYYY-MM-DD
                "previous_value": int,
                "previous_classification": str,
            }

        Raises:
            RuntimeError: on HTTP error or malformed/empty response.
        """
        try:
            response = requests.get(self.BASE_URL, params={"limit": 2}, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"Fear & Greed API error: {exc}") from exc

        data = payload.get("data", [])
        if len(data) < 2:
            raise RuntimeError("Fear & Greed API returned insufficient data.")

        today = data[0]
        yesterday = data[1]

        try:
            ts = datetime.fromtimestamp(int(today["timestamp"]), tz=timezone.utc)
            timestamp_str = ts.strftime("%Y-%m-%d")
            return {
                "value": int(today["value"]),
                "classification": today["value_classification"],
                "timestamp": timestamp_str,
                "previous_value": int(yesterday["value"]),
                "previous_classification": yesterday["value_classification"],
            }
        except (KeyError, ValueError) as exc:
            raise RuntimeError(f"Fear & Greed API response malformed: {exc}") from exc
