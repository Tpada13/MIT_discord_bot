import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import SUPPORTED_COINS
from services.coingecko import CoinGeckoClient
from services.indicators import calculate_indicators
from services.watchlist import WatchlistService

_log = logging.getLogger(__name__)


def _rsi_label(rsi) -> str:
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi:.1f} ⚠️ Overbought"
    if rsi <= 30:
        return f"{rsi:.1f} ⚠️ Oversold"
    return f"{rsi:.1f} Neutral"


def _fmt_indicator(value: float | None, prefix: str = "$") -> str:
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.2f}"


class WatchlistCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        watchlist: WatchlistService,
        coingecko: CoinGeckoClient,
    ):
        self.bot = bot
        self.watchlist = watchlist
        self.coingecko = coingecko

    watch = app_commands.Group(name="watch", description="Manage your coin watchlist")

    @watch.command(name="add", description="Add a coin to your watchlist")
    @app_commands.describe(coin="Coin ticker to add")
    @app_commands.choices(coin=[app_commands.Choice(name=k, value=k) for k in SUPPORTED_COINS])
    async def watch_add(self, interaction: discord.Interaction, coin: str):
        try:
            self.watchlist.add(interaction.user.id, coin)
            count = len(self.watchlist.get(interaction.user.id))
            await interaction.response.send_message(
                f"✅ {coin} added to your watchlist. ({count}/10 coins)", ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @watch.command(name="remove", description="Remove a coin from your watchlist")
    @app_commands.describe(coin="Coin ticker to remove")
    @app_commands.choices(coin=[app_commands.Choice(name=k, value=k) for k in SUPPORTED_COINS])
    async def watch_remove(self, interaction: discord.Interaction, coin: str):
        try:
            self.watchlist.remove(interaction.user.id, coin)
            await interaction.response.send_message(
                f"✅ {coin} removed from your watchlist.", ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @watch.command(name="clear", description="Clear your entire watchlist")
    async def watch_clear(self, interaction: discord.Interaction):
        try:
            self.watchlist.clear(interaction.user.id)
            await interaction.response.send_message(
                "✅ Your watchlist has been cleared.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to clear watchlist: {e}", ephemeral=True)

    @watch.command(name="show", description="Show prices + indicators for your watchlist coins")
    async def watch_show(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        coins = self.watchlist.get(interaction.user.id)
        if not coins:
            await interaction.followup.send(
                "Your watchlist is empty. Use `/watch add` to get started.",
                ephemeral=True,
            )
            return

        embeds = []
        for i, coin in enumerate(coins):
            is_last = i == len(coins) - 1
            try:
                price_data = self.coingecko.get_price_data(coin, "24h")
                chart_data = self.coingecko.get_market_chart(coin, 30)
                indicators = calculate_indicators(chart_data["close_prices"], chart_data["volumes"])

                change = price_data["price_change_pct"]
                color = discord.Color.green() if change >= 0 else discord.Color.red()
                arrow = "▲" if change >= 0 else "▼"

                embed = discord.Embed(
                    title=f"{coin} — Watchlist",
                    color=color,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="Current Price", value=f"${price_data['current_price']:,.4f}", inline=True)
                embed.add_field(name="Change (24h)", value=f"{arrow} {abs(change):.2f}%", inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=True)
                embed.add_field(name="RSI (14)", value=_rsi_label(indicators["rsi"]), inline=True)
                embed.add_field(name="SMA 20", value=_fmt_indicator(indicators["sma20"]), inline=True)
                embed.add_field(name="Volume Trend", value=indicators["volume_trend"], inline=True)
                if is_last:
                    embed.set_footer(text="Data: CoinGecko")
                embeds.append(embed)
            except Exception as exc:
                _log.warning("watch_show: failed to fetch %s: %r", coin, exc)
                embeds.append(discord.Embed(
                    title=f"{coin} — Watchlist",
                    color=discord.Color.dark_grey(),
                    description="❌ Data unavailable",
                ))

        await interaction.followup.send(embeds=embeds, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WatchlistCog(bot, bot.watchlist, bot.coingecko))
