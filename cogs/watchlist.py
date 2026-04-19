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


def _build_watch_table(rows: list[dict]) -> str:
    header = (
        f"{'Coin':<4}  {'Price':>12}  {'24h%':>8}  "
        f"{'RSI':>5}  {'SMA20':>12}  {'Trend':<7}  "
        f"{'Δ$':>12}  {'Δ%':>8}"
    )
    sep = "─" * len(header)
    lines = [header, sep]
    for row in rows:
        if not row["ok"]:
            lines.append(f"{row['coin']:<4}  ❌ unavailable")
            continue
        price_str = f"${row['price']:,.2f}"
        arrow = "▲" if row["change_24h"] >= 0 else "▼"
        change_str = f"{arrow}{abs(row['change_24h']):.2f}%"
        rsi_str = f"{row['rsi']:.1f}" if row["rsi"] is not None else "N/A"
        sma_str = f"${row['sma20']:,.2f}" if row["sma20"] is not None else "N/A"
        delta_d = row["delta_dollar"]
        delta_p = row["delta_pct"]
        if delta_d is None:
            dd_str = "—"
            dp_str = "—"
        else:
            sign = "+" if delta_d >= 0 else "-"
            dd_str = f"{sign}${abs(delta_d):,.2f}"
            dp_str = f"{'+' if delta_p >= 0 else ''}{delta_p:.2f}%"
        lines.append(
            f"{row['coin']:<4}  {price_str:>12}  {change_str:>8}  "
            f"{rsi_str:>5}  {sma_str:>12}  {row['volume_trend']:<7}  "
            f"{dd_str:>12}  {dp_str:>8}"
        )
    return "\n".join(lines)


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
            count = self.watchlist.add(interaction.user.id, coin)
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

        last_prices = self.watchlist.get_last_prices(interaction.user.id)
        rows = []
        fetched_prices: dict[str, float] = {}
        positive_count = 0
        negative_count = 0

        for coin in coins:
            try:
                price_data = self.coingecko.get_price_data(coin, "24h")
                chart_data = self.coingecko.get_market_chart(coin, 30)
                indicators = calculate_indicators(chart_data["close_prices"], chart_data["volumes"])

                price = price_data["current_price"]
                change_24h = price_data["price_change_pct"]
                fetched_prices[coin] = price

                prev = last_prices.get(coin)
                if prev is not None:
                    delta_dollar = price - prev
                    delta_pct = ((price - prev) / prev) * 100
                else:
                    delta_dollar = None
                    delta_pct = None

                if change_24h > 0:
                    positive_count += 1
                elif change_24h < 0:
                    negative_count += 1

                rows.append({
                    "ok": True,
                    "coin": coin,
                    "price": price,
                    "change_24h": change_24h,
                    "rsi": indicators["rsi"],
                    "sma20": indicators["sma20"],
                    "volume_trend": indicators["volume_trend"],
                    "delta_dollar": delta_dollar,
                    "delta_pct": delta_pct,
                })
            except Exception as exc:
                _log.warning("watch_show: failed to fetch %s: %r", coin, exc)
                rows.append({"ok": False, "coin": coin})

        if fetched_prices:
            self.watchlist.save_last_prices(interaction.user.id, fetched_prices)

        if positive_count > negative_count:
            color = discord.Color.green()
        elif negative_count > positive_count:
            color = discord.Color.red()
        else:
            color = discord.Color.dark_grey()

        table = _build_watch_table(rows)
        embed = discord.Embed(
            title="Your Watchlist",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="\u200b", value=f"```\n{table}\n```", inline=False)
        embed.set_footer(text="Data: CoinGecko")

        await interaction.followup.send(embeds=[embed], ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WatchlistCog(bot, bot.watchlist, bot.coingecko))
