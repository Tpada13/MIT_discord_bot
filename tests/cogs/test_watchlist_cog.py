from unittest.mock import AsyncMock, MagicMock

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
    """When CoinGecko raises for a coin, a dark_grey error embed is included."""
    cog = make_cog()
    cog.watchlist.get.return_value = ["BTC"]
    cog.coingecko.get_price_data.side_effect = Exception("API down")
    interaction = make_interaction()

    await cog.watch_show.callback(cog, interaction)

    interaction.followup.send.assert_awaited_once()
    call_args = interaction.followup.send.call_args
    embeds = call_args.kwargs.get("embeds") or (call_args.args[0] if call_args.args else None)
    assert embeds is not None and len(embeds) == 1
    assert embeds[0].color == discord.Color.dark_grey()


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
