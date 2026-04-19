import json
from pathlib import Path

from config import SUPPORTED_COINS

WATCHLIST_PATH = Path("data/watchlists.json")


class WatchlistService:
    def __init__(self, path: Path = WATCHLIST_PATH):
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f)

    def _user_entry(self, data: dict, user_id: int) -> dict:
        key = str(user_id)
        if key not in data:
            data[key] = {"coins": [], "last_prices": {}}
        return data[key]

    def add(self, user_id: int, coin: str) -> int:
        if coin not in SUPPORTED_COINS:
            raise ValueError(f"{coin} is not a supported coin.")
        data = self._read()
        entry = self._user_entry(data, user_id)
        if coin in entry["coins"]:
            raise ValueError(f"{coin} is already on your watchlist.")
        if len(entry["coins"]) >= 10:
            raise ValueError("Your watchlist is full (10/10 coins). Remove a coin first.")
        entry["coins"].append(coin)
        self._write(data)
        return len(entry["coins"])

    def remove(self, user_id: int, coin: str) -> None:
        data = self._read()
        entry = self._user_entry(data, user_id)
        if coin not in entry["coins"]:
            raise ValueError(f"{coin} is not on your watchlist.")
        entry["coins"].remove(coin)
        entry["last_prices"].pop(coin, None)
        self._write(data)

    def get(self, user_id: int) -> list[str]:
        data = self._read()
        return data.get(str(user_id), {}).get("coins", [])

    def clear(self, user_id: int) -> None:
        data = self._read()
        data.pop(str(user_id), None)
        self._write(data)

    def get_last_prices(self, user_id: int) -> dict[str, float]:
        data = self._read()
        return data.get(str(user_id), {}).get("last_prices", {})

    def save_last_prices(self, user_id: int, prices: dict[str, float]) -> None:
        data = self._read()
        entry = self._user_entry(data, user_id)
        entry["last_prices"].update(prices)
        self._write(data)
