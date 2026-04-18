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

    def add(self, user_id: int, coin: str) -> int:
        if coin not in SUPPORTED_COINS:
            raise ValueError(f"{coin} is not a supported coin.")
        data = self._read()
        key = str(user_id)
        watchlist = data.get(key, [])
        if coin in watchlist:
            raise ValueError(f"{coin} is already on your watchlist.")
        if len(watchlist) >= 10:
            raise ValueError("Your watchlist is full (10/10 coins). Remove a coin first.")
        watchlist.append(coin)
        data[key] = watchlist
        self._write(data)
        return len(watchlist)

    def remove(self, user_id: int, coin: str) -> None:
        data = self._read()
        key = str(user_id)
        watchlist = data.get(key, [])
        if coin not in watchlist:
            raise ValueError(f"{coin} is not on your watchlist.")
        watchlist.remove(coin)
        data[key] = watchlist
        self._write(data)

    def get(self, user_id: int) -> list[str]:
        data = self._read()
        return data.get(str(user_id), [])

    def clear(self, user_id: int) -> None:
        data = self._read()
        data.pop(str(user_id), None)
        self._write(data)
