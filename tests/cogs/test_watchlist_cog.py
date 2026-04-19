from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cogs.watchlist import WatchlistCog


def make_cog():
    """Build a WatchlistCog with mocked services."""
    bot = MagicMock()
    watchlist = MagicMock()
    coingecko = MagicMock()
    return WatchlistCog(bot, watchlist, coingecko)


def make_interaction():
    interaction = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user.id = 12345
    return interaction


@pytest.mark.asyncio
async def test_watch_add_error():
    """ValueError from WatchlistService.add results in an ❌ response message."""
    cog = make_cog()
    cog.watchlist.add.side_effect = ValueError("BTC is already on your watchlist.")
    interaction = make_interaction()

    await cog.watch_add.callback(cog, interaction, coin="BTC")

    interaction.response.send_message.assert_awaited_once()
    call_args = interaction.response.send_message.call_args
    msg = call_args.args[0] if call_args.args else call_args.kwargs.get("content", "")
    assert "❌" in msg


@pytest.mark.asyncio
async def test_watch_remove_error():
    """ValueError from WatchlistService.remove results in an ❌ response message."""
    cog = make_cog()
    cog.watchlist.remove.side_effect = ValueError("BTC is not on your watchlist.")
    interaction = make_interaction()

    await cog.watch_remove.callback(cog, interaction, coin="BTC")

    interaction.response.send_message.assert_awaited_once()
    call_args = interaction.response.send_message.call_args
    msg = call_args.args[0] if call_args.args else call_args.kwargs.get("content", "")
    assert "❌" in msg


@pytest.mark.asyncio
async def test_watch_show_empty_watchlist():
    """Empty watchlist returns a plain followup message containing 'empty'."""
    cog = make_cog()
    cog.watchlist.get.return_value = []
    interaction = make_interaction()

    await cog.watch_show.callback(cog, interaction)

    interaction.followup.send.assert_awaited_once()
    call_args = interaction.followup.send.call_args
    msg = call_args.args[0] if call_args.args else call_args.kwargs.get("content", "")
    assert "empty" in msg.lower()


@pytest.mark.asyncio
async def test_watch_show_coin_fetch_error():
    """When CoinGecko raises for a coin, a single embed is sent containing ❌ unavailable."""
    cog = make_cog()
    cog.watchlist.get.return_value = ["BTC"]
    cog.watchlist.get_last_prices.return_value = {}
    cog.coingecko.get_price_data.side_effect = Exception("API down")
    interaction = make_interaction()

    await cog.watch_show.callback(cog, interaction)

    interaction.followup.send.assert_awaited_once()
    call_args = interaction.followup.send.call_args
    embeds = call_args.kwargs.get("embeds")
    assert embeds is not None and len(embeds) == 1
    field_value = embeds[0].fields[0].value
    assert "❌" in field_value
    assert "BTC" in field_value


@pytest.mark.asyncio
async def test_watch_show_success():
    """Successful fetch sends a single embed with a table containing the coin ticker."""
    cog = make_cog()
    cog.watchlist.get.return_value = ["BTC"]
    cog.watchlist.get_last_prices.return_value = {"BTC": 83000.00}
    cog.coingecko.get_price_data.return_value = {
        "current_price": 84123.00,
        "price_change_pct": 2.14,
    }
    cog.coingecko.get_market_chart.return_value = {
        "close_prices": [80000.0] * 30,
        "volumes": [1e9] * 30,
    }
    interaction = make_interaction()

    with patch("cogs.watchlist.calculate_indicators") as mock_calc:
        mock_calc.return_value = {
            "rsi": 65.0,
            "sma20": 81234.00,
            "volume_trend": "Rising",
        }
        await cog.watch_show.callback(cog, interaction)

    interaction.followup.send.assert_awaited_once()
    call_args = interaction.followup.send.call_args
    embeds = call_args.kwargs.get("embeds")
    assert embeds is not None and len(embeds) == 1
    field_value = embeds[0].fields[0].value
    assert "BTC" in field_value


@pytest.mark.asyncio
async def test_watch_clear_error():
    """Generic Exception from WatchlistService.clear results in an ❌ response message."""
    cog = make_cog()
    cog.watchlist.clear.side_effect = Exception("disk full")
    interaction = make_interaction()

    await cog.watch_clear.callback(cog, interaction)

    interaction.response.send_message.assert_awaited_once()
    call_args = interaction.response.send_message.call_args
    msg = call_args.args[0] if call_args.args else call_args.kwargs.get("content", "")
    assert "❌" in msg
