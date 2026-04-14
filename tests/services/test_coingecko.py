from unittest.mock import MagicMock, patch

import pytest

from services.coingecko import CoinGeckoClient


@pytest.fixture
def client():
    return CoinGeckoClient()


def make_mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


# --- get_price_data ---

def test_get_price_data_24h(client):
    mock_data = [
        {
            "id": "bitcoin",
            "current_price": 50000.0,
            "price_change_percentage_24h_in_currency": 2.5,
            "price_change_percentage_1h_in_currency": 0.3,
            "price_change_percentage_7d_in_currency": 5.1,
            "market_cap": 1_000_000_000_000,
            "total_volume": 50_000_000_000,
        }
    ]
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(mock_data)
        result = client.get_price_data("BTC", "24h")

    assert result["ticker"] == "BTC"
    assert result["current_price"] == 50000.0
    assert result["price_change_pct"] == 2.5
    assert result["market_cap"] == 1_000_000_000_000
    assert result["volume_24h"] == 50_000_000_000
    assert result["timeframe"] == "24h"


def test_get_price_data_1h(client):
    mock_data = [
        {
            "id": "bitcoin",
            "current_price": 50000.0,
            "price_change_percentage_24h_in_currency": 2.5,
            "price_change_percentage_1h_in_currency": 0.3,
            "price_change_percentage_7d_in_currency": 5.1,
            "market_cap": 1_000_000_000_000,
            "total_volume": 50_000_000_000,
        }
    ]
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(mock_data)
        result = client.get_price_data("BTC", "1h")

    assert result["price_change_pct"] == 0.3
    assert result["timeframe"] == "1h"


def test_get_price_data_coin_not_found(client):
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response([])
        with pytest.raises(ValueError, match="not found"):
            client.get_price_data("FAKE", "24h")


def test_get_price_data_3d_uses_market_chart(client):
    """3d timeframe requires a market_chart call to calculate % change."""
    markets_data = [
        {
            "id": "bitcoin",
            "current_price": 50000.0,
            "price_change_percentage_24h_in_currency": 2.5,
            "price_change_percentage_1h_in_currency": 0.3,
            "price_change_percentage_7d_in_currency": 5.1,
            "market_cap": 1_000_000_000_000,
            "total_volume": 50_000_000_000,
        }
    ]
    chart_data = {
        "prices": [[1000, 45000.0], [2000, 47000.0], [3000, 50000.0]],
        "total_volumes": [[1000, 1e9], [2000, 1.1e9], [3000, 1.2e9]],
    }

    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_response(markets_data),
            make_mock_response(chart_data),
        ]
        result = client.get_price_data("BTC", "3d")

    # (50000 - 45000) / 45000 * 100 = 11.11...
    assert result["timeframe"] == "3d"
    assert abs(result["price_change_pct"] - 11.11) < 0.1


# --- get_market_chart ---

def test_get_market_chart_returns_prices_and_volumes(client):
    chart_data = {
        "prices": [[1000, 45000.0], [2000, 46000.0], [3000, 47000.0]],
        "total_volumes": [[1000, 1e9], [2000, 1.1e9], [3000, 1.2e9]],
    }
    with patch("services.coingecko.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(chart_data)
        result = client.get_market_chart("BTC", days=7)

    assert result["ticker"] == "BTC"
    assert result["days"] == 7
    assert result["close_prices"] == [45000.0, 46000.0, 47000.0]
    assert result["volumes"] == [1e9, 1.1e9, 1.2e9]
    assert len(result["timestamps"]) == 3


def test_ticker_to_id_known_coin(client):
    assert client._ticker_to_id("BTC") == "bitcoin"
    assert client._ticker_to_id("eth") == "ethereum"


def test_ticker_to_id_unknown_coin_falls_back_to_lowercase(client):
    assert client._ticker_to_id("NEWCOIN") == "newcoin"


def test_get_price_data_invalid_timeframe(client):
    with pytest.raises(ValueError, match="Invalid timeframe"):
        client.get_price_data("BTC", "banana")
