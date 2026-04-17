from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.crypto import CryptoCog


def make_cog():
    """Build a CryptoCog with mocked services — matches the updated constructor."""
    bot = MagicMock()
    coingecko = MagicMock()
    analyst = MagicMock()
    fear_greed = MagicMock()
    return CryptoCog(bot, coingecko, analyst, fear_greed)


def make_interaction():
    interaction = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def fear_greed_data(classification: str, value: int = 50) -> dict:
    return {
        "value": value,
        "classification": classification,
        "timestamp": "2024-04-15",
        "previous_value": 45,
        "previous_classification": "Fear",
    }


@pytest.mark.asyncio
async def test_feargreed_color_extreme_fear():
    cog = make_cog()
    cog.fear_greed.get_current.return_value = fear_greed_data("Extreme Fear", value=10)
    interaction = make_interaction()

    await cog.feargreed.callback(cog, interaction)

    sent = interaction.followup.send.call_args
    embed = sent.kwargs.get("embed") or sent.args[0]
    assert embed.color == discord.Color.red()


@pytest.mark.asyncio
async def test_feargreed_color_neutral():
    cog = make_cog()
    cog.fear_greed.get_current.return_value = fear_greed_data("Neutral", value=50)
    interaction = make_interaction()

    await cog.feargreed.callback(cog, interaction)

    sent = interaction.followup.send.call_args
    embed = sent.kwargs.get("embed") or sent.args[0]
    assert embed.color == discord.Color.light_grey()


@pytest.mark.asyncio
async def test_feargreed_color_extreme_greed():
    cog = make_cog()
    cog.fear_greed.get_current.return_value = fear_greed_data("Extreme Greed", value=90)
    interaction = make_interaction()

    await cog.feargreed.callback(cog, interaction)

    sent = interaction.followup.send.call_args
    embed = sent.kwargs.get("embed") or sent.args[0]
    assert embed.color == discord.Color.green()


@pytest.mark.asyncio
async def test_feargreed_color_fear():
    cog = make_cog()
    cog.fear_greed.get_current.return_value = fear_greed_data("Fear", value=25)
    interaction = make_interaction()
    await cog.feargreed.callback(cog, interaction)
    sent = interaction.followup.send.call_args
    embed = sent.kwargs.get("embed") or sent.args[0]
    assert embed.color == discord.Color.red()


@pytest.mark.asyncio
async def test_feargreed_color_greed():
    cog = make_cog()
    cog.fear_greed.get_current.return_value = fear_greed_data("Greed", value=75)
    interaction = make_interaction()
    await cog.feargreed.callback(cog, interaction)
    sent = interaction.followup.send.call_args
    embed = sent.kwargs.get("embed") or sent.args[0]
    assert embed.color == discord.Color.green()


@pytest.mark.asyncio
async def test_feargreed_api_error():
    cog = make_cog()
    cog.fear_greed.get_current.side_effect = RuntimeError("API down")
    interaction = make_interaction()

    await cog.feargreed.callback(cog, interaction)

    interaction.followup.send.assert_awaited_once()
    call_args = interaction.followup.send.call_args
    msg = call_args.args[0] if call_args.args else call_args.kwargs.get("content", "")
    assert "❌" in msg
