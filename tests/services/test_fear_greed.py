from unittest.mock import MagicMock, patch

import pytest

from services.fear_greed import FearGreedClient


@pytest.fixture
def client():
    return FearGreedClient()


def make_mock_response(json_data, raise_http_error=False):
    mock = MagicMock()
    mock.json.return_value = json_data
    if raise_http_error:
        mock.raise_for_status.side_effect = Exception("HTTP 500")
    else:
        mock.raise_for_status = MagicMock()
    return mock


SAMPLE_RESPONSE = {
    "data": [
        {
            "value": "23",
            "value_classification": "Extreme Fear",
            "timestamp": "1713225600",
        },
        {
            "value": "18",
            "value_classification": "Extreme Fear",
            "timestamp": "1713139200",
        },
    ]
}


def test_get_current_success(client):
    with patch("services.fear_greed.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(SAMPLE_RESPONSE)
        result = client.get_current()

    assert result["value"] == 23
    assert result["classification"] == "Extreme Fear"
    assert result["timestamp"] == "2024-04-15"
    assert result["previous_value"] == 18
    assert result["previous_classification"] == "Extreme Fear"


def test_get_current_http_error(client):
    with patch("services.fear_greed.requests.get") as mock_get:
        mock_get.return_value = make_mock_response({}, raise_http_error=True)
        with pytest.raises(RuntimeError):
            client.get_current()


def test_get_current_missing_data(client):
    with patch("services.fear_greed.requests.get") as mock_get:
        mock_get.return_value = make_mock_response({"data": []})
        with pytest.raises(RuntimeError):
            client.get_current()
