from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    ANALYSIS_TIMEFRAMES,
    DEFAULT_ANALYSIS_TIMEFRAME,
    DEFAULT_PRICE_TIMEFRAME,
    PRICE_TIMEFRAMES,
    SUPPORTED_COINS,
    TIMEFRAME_TO_DAYS,
)
from services.claude_analyst import ClaudeAnalyst
from services.coingecko import CoinGeckoClient
from services.indicators import calculate_indicators


def _format_large_number(n: float) -> str:
    """Format large numbers as $1.23T, $456.78B, $12.34M."""
    if n >= 1_000_000_000_000:
        return f"${n / 1_000_000_000_000:.2f}T"
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    return f"${n:,.2f}"


def _fmt_indicator(value: float | None, prefix: str = "$") -> str:
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.2f}"


def _rsi_label(rsi) -> str:
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi:.1f} ⚠️ Overbought"
    if rsi <= 30:
        return f"{rsi:.1f} ⚠️ Oversold"
    return f"{rsi:.1f} Neutral"


class CryptoCog(commands.Cog):
    def __init__(self, bot: commands.Bot, coingecko: CoinGeckoClient, analyst: ClaudeAnalyst):
        self.bot = bot
        self.coingecko = coingecko
        self.analyst = analyst

    # -------------------------------------------------------------------------
    # /help
    # -------------------------------------------------------------------------

    @app_commands.command(name="help", description="Show available commands and supported coins")
    async def help_command(self, interaction: discord.Interaction):
        coin_list = ", ".join(SUPPORTED_COINS.keys())
        embed = discord.Embed(
            title="Crypto Bot — Commands",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="/price <coin> [timeframe]",
            value=f"Current price + change. Timeframes: {', '.join(PRICE_TIMEFRAMES)} (default: {DEFAULT_PRICE_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(
            name="/analyze <coin> [timeframe]",
            value=f"Price + RSI, SMA, EMA, volume trend. Timeframes: {', '.join(ANALYSIS_TIMEFRAMES)} (default: {DEFAULT_ANALYSIS_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(
            name="/forecast <coin> [timeframe]",
            value=f"AI analyst report (Claude). Timeframes: {', '.join(ANALYSIS_TIMEFRAMES)} (default: {DEFAULT_ANALYSIS_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(name="Supported Coins", value=coin_list, inline=False)
        embed.set_footer(text="Data: CoinGecko (free) | Analysis: Anthropic Claude")
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # /price
    # -------------------------------------------------------------------------

    @app_commands.command(name="price", description="Get current price and change over a timeframe")
    @app_commands.describe(
        coin="Coin ticker, e.g. BTC, ETH, SOL",
        timeframe="Time period for price change (default: 24h)",
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="1 hour", value="1h"),
            app_commands.Choice(name="24 hours", value="24h"),
            app_commands.Choice(name="3 days", value="3d"),
            app_commands.Choice(name="7 days", value="7d"),
        ]
    )
    async def price(
        self,
        interaction: discord.Interaction,
        coin: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_PRICE_TIMEFRAME

        try:
            data = self.coingecko.get_price_data(coin.upper(), tf)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error: {e}")
            return

        change = data["price_change_pct"]
        color = discord.Color.green() if change >= 0 else discord.Color.red()
        arrow = "▲" if change >= 0 else "▼"

        embed = discord.Embed(
            title=f"{data['ticker']} — Price",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Current Price", value=f"${data['current_price']:,.4f}", inline=True)
        embed.add_field(name=f"Change ({tf})", value=f"{arrow} {abs(change):.2f}%", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # spacer
        embed.add_field(name="Market Cap", value=_format_large_number(data["market_cap"]), inline=True)
        embed.add_field(name="24h Volume", value=_format_large_number(data["volume_24h"]), inline=True)
        embed.set_footer(text="Data: CoinGecko")
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # /analyze
    # -------------------------------------------------------------------------

    @app_commands.command(name="analyze", description="Technical analysis: RSI, SMA, EMA, volume trend")
    @app_commands.describe(
        coin="Coin ticker, e.g. BTC, ETH, SOL",
        timeframe="Analysis period (default: 30d)",
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="7 days", value="7d"),
            app_commands.Choice(name="30 days", value="30d"),
            app_commands.Choice(name="90 days", value="90d"),
            app_commands.Choice(name="180 days", value="180d"),
        ]
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        coin: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_ANALYSIS_TIMEFRAME
        days = TIMEFRAME_TO_DAYS[tf]

        try:
            price_data = self.coingecko.get_price_data(coin.upper(), tf)
            chart = self.coingecko.get_market_chart(coin.upper(), days)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error: {e}")
            return

        indicators = calculate_indicators(chart["close_prices"], chart["volumes"])

        change = price_data["price_change_pct"]
        color = discord.Color.green() if change >= 0 else discord.Color.red()
        arrow = "▲" if change >= 0 else "▼"

        embed = discord.Embed(
            title=f"{coin.upper()} — Technical Analysis ({tf})",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Current Price", value=f"${price_data['current_price']:,.4f}", inline=True)
        embed.add_field(name=f"Change ({tf})", value=f"{arrow} {abs(change):.2f}%", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="RSI (14)", value=_rsi_label(indicators["rsi"]), inline=True)
        embed.add_field(name="SMA 20", value=_fmt_indicator(indicators["sma20"]), inline=True)
        embed.add_field(name="SMA 50", value=_fmt_indicator(indicators["sma50"]), inline=True)
        embed.add_field(name="EMA 12", value=_fmt_indicator(indicators["ema12"]), inline=True)
        embed.add_field(name="EMA 26", value=_fmt_indicator(indicators["ema26"]), inline=True)
        embed.add_field(name="Volume Trend", value=indicators["volume_trend"], inline=True)
        embed.set_footer(text="Data: CoinGecko | Indicators: pandas-ta")
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # /forecast
    # -------------------------------------------------------------------------

    @app_commands.command(name="forecast", description="AI-powered senior analyst forecast (Claude)")
    @app_commands.describe(
        coin="Coin ticker, e.g. BTC, ETH, SOL",
        timeframe="Analysis period for forecast (default: 30d)",
    )
    @app_commands.choices(
        timeframe=[
            app_commands.Choice(name="7 days", value="7d"),
            app_commands.Choice(name="30 days", value="30d"),
            app_commands.Choice(name="90 days", value="90d"),
            app_commands.Choice(name="180 days", value="180d"),
        ]
    )
    async def forecast(
        self,
        interaction: discord.Interaction,
        coin: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_ANALYSIS_TIMEFRAME
        days = TIMEFRAME_TO_DAYS[tf]

        try:
            price_data = self.coingecko.get_price_data(coin.upper(), tf)
            chart = self.coingecko.get_market_chart(coin.upper(), days)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error: {e}")
            return

        indicators = calculate_indicators(chart["close_prices"], chart["volumes"])

        try:
            report = self.analyst.generate_forecast(price_data, indicators)
        except Exception as e:
            await interaction.followup.send(f"❌ Analyst error: {e}")
            return

        # Prepend coin/timeframe header for context
        header = f"**{coin.upper()} — AI Forecast ({tf})**\n\n"
        report_with_header = header + report

        # Discord message limit is 2000 chars — split if needed
        if len(report_with_header) <= 2000:
            await interaction.followup.send(report_with_header)
        else:
            chunks = [report_with_header[i:i + 1990] for i in range(0, len(report_with_header), 1990)]
            for chunk in chunks:
                await interaction.followup.send(chunk)


async def setup(bot: commands.Bot):
    """Called by bot.load_extension('cogs.crypto')."""
    await bot.add_cog(CryptoCog(bot, CoinGeckoClient(), ClaudeAnalyst()))
