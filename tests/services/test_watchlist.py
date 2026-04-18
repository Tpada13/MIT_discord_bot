import pytest

from config import SUPPORTED_COINS
from services.watchlist import WatchlistService


@pytest.fixture
def svc(tmp_path):
    return WatchlistService(path=tmp_path / "watchlists.json")


def test_add_happy_path(svc):
    svc.add(1, "BTC")
    assert svc.get(1) == ["BTC"]


def test_add_duplicate(svc):
    svc.add(1, "BTC")
    with pytest.raises(ValueError, match="already on your watchlist"):
        svc.add(1, "BTC")


def test_add_cap(svc):
    all_coins = list(SUPPORTED_COINS.keys())
    for coin in all_coins[:10]:
        svc.add(1, coin)
    with pytest.raises(ValueError, match="full"):
        svc.add(1, all_coins[10])


def test_add_unsupported_coin(svc):
    with pytest.raises(ValueError, match="not a supported coin"):
        svc.add(1, "INVALID")


def test_remove_happy_path(svc):
    svc.add(1, "BTC")
    svc.remove(1, "BTC")
    assert svc.get(1) == []


def test_remove_not_on_list(svc):
    with pytest.raises(ValueError, match="not on your watchlist"):
        svc.remove(1, "BTC")


def test_get_unknown_user(svc):
    assert svc.get(999) == []


def test_clear(svc):
    svc.add(1, "BTC")
    svc.add(1, "ETH")
    svc.clear(1)
    assert svc.get(1) == []
