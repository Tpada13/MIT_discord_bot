import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    ANALYSIS_TIMEFRAMES,
    COIN_DESCRIPTIONS,
    DEFAULT_ANALYSIS_TIMEFRAME,
    DEFAULT_PRICE_TIMEFRAME,
    PRICE_TIMEFRAMES,
    SUPPORTED_COINS,
    TIMEFRAME_TO_DAYS,
)
from services.claude_analyst import ClaudeAnalyst
from services.coingecko import CoinGeckoClient
from services.fear_greed import FearGreedClient
from services.indicators import calculate_indicators

_log = logging.getLogger(__name__)


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


def _format_market_block(rows: list[dict], failed: list[str]) -> str:
    """
    Sort rows by price_change_pct descending, append failed tickers,
    and return a monospace code-block string for a Discord embed field.

    rows: list of {ticker: str, current_price: float, price_change_pct: float}
    failed: list of ticker strings that could not be fetched
    """
    sorted_rows = sorted(rows, key=lambda r: r["price_change_pct"], reverse=True)

    lines = []
    for row in sorted_rows:
        ticker = row["ticker"].ljust(4)
        price = f"${row['current_price']:>14,.4f}"
        arrow = "▲" if row["price_change_pct"] >= 0 else "▼"
        change_str = f"{arrow}  {abs(row['price_change_pct']):>6.2f}%"
        lines.append(f"{ticker}  {price}   {change_str}")

    for ticker in failed:
        lines.append(f"{ticker.ljust(4)}  {'':>15}   —  (unavailable)")

    return "```\n" + "\n".join(lines) + "\n```"


def _build_market_rows(
    coins: list[str],
    coingecko: "CoinGeckoClient",
) -> tuple[list[dict], list[str]]:
    """
    Fetch 24h price data for each coin sequentially (no parallelism —
    CoinGecko free tier rate-limits aggressively).

    Returns (successful_rows, failed_tickers).
    successful_rows: list of {ticker, current_price, price_change_pct}
    """
    rows = []
    failed = []
    for coin in coins:
        try:
            data = coingecko.get_price_data(coin, "24h")
            rows.append({
                "ticker": data["ticker"],
                "current_price": data["current_price"],
                "price_change_pct": data["price_change_pct"],
            })
        except Exception as exc:
            _log.warning("_build_market_rows: failed to fetch %s: %r", coin, exc)
            failed.append(coin)
    return rows, failed


class CryptoCog(commands.Cog):
    def __init__(self, bot: commands.Bot, coingecko: CoinGeckoClient, analyst: ClaudeAnalyst, fear_greed: FearGreedClient):
        self.bot = bot
        self.coingecko = coingecko
        self.analyst = analyst
        self.fear_greed = fear_greed

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
        embed.add_field(
            name="/compare <coin1> <coin2> [timeframe]",
            value=f"Side-by-side comparison + Claude verdict. Timeframes: {', '.join(ANALYSIS_TIMEFRAMES)} (default: {DEFAULT_ANALYSIS_TIMEFRAME})",
            inline=False,
        )
        embed.add_field(
            name="/market",
            value="All supported coins sorted by 24h % change",
            inline=False,
        )
        embed.add_field(
            name="/feargreed",
            value="Crypto Fear & Greed Index (0–100 sentiment score)",
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

        coin_description = COIN_DESCRIPTIONS.get(coin.upper())
        try:
            report = self.analyst.generate_forecast(price_data, indicators, coin_description)
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

    # -------------------------------------------------------------------------
    # /compare
    # -------------------------------------------------------------------------

    @app_commands.command(name="compare", description="Side-by-side technical comparison of two coins")
    @app_commands.describe(
        coin1="First coin ticker, e.g. BTC",
        coin2="Second coin ticker, e.g. ETH",
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
    async def compare(
        self,
        interaction: discord.Interaction,
        coin1: str,
        coin2: str,
        timeframe: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        tf = timeframe.value if timeframe else DEFAULT_ANALYSIS_TIMEFRAME
        days = TIMEFRAME_TO_DAYS[tf]

        ticker_a = coin1.upper()
        ticker_b = coin2.upper()

        if ticker_a == ticker_b:
            await interaction.followup.send("❌ Please choose two different coins to compare.")
            return

        # Fetch data for both coins (sequential — CoinGecko free tier rate limits)
        try:
            price_a = self.coingecko.get_price_data(ticker_a, tf)
            chart_a = self.coingecko.get_market_chart(ticker_a, days)
        except ValueError as e:
            await interaction.followup.send(f"❌ {ticker_a}: {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error for {ticker_a}: {e}")
            return

        try:
            price_b = self.coingecko.get_price_data(ticker_b, tf)
            chart_b = self.coingecko.get_market_chart(ticker_b, days)
        except ValueError as e:
            await interaction.followup.send(f"❌ {ticker_b}: {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"❌ CoinGecko error for {ticker_b}: {e}")
            return

        ind_a = calculate_indicators(chart_a["close_prices"], chart_a["volumes"])
        ind_b = calculate_indicators(chart_b["close_prices"], chart_b["volumes"])

        try:
            verdict = self.analyst.compare_coins(
                ticker_a, price_a, ind_a,
                ticker_b, price_b, ind_b,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Analyst error: {e}")
            return

        def coin_fields(ticker: str, price_data: dict, ind: dict) -> list[tuple]:
            change = price_data["price_change_pct"]
            arrow = "▲" if change >= 0 else "▼"
            return [
                (f"{ticker} Price", f"${price_data['current_price']:,.4f}", True),
                (f"{ticker} Change ({tf})", f"{arrow} {abs(change):.2f}%", True),
                (f"{ticker} RSI (14)", _rsi_label(ind["rsi"]), True),
                (f"{ticker} SMA 20", _fmt_indicator(ind["sma20"]), True),
                (f"{ticker} EMA 12", _fmt_indicator(ind["ema12"]), True),
                (f"{ticker} Volume", ind["volume_trend"], True),
            ]

        embed = discord.Embed(
            title=f"{ticker_a} vs {ticker_b} — Comparison ({tf})",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        for name, value, inline in coin_fields(ticker_a, price_a, ind_a):
            embed.add_field(name=name, value=value, inline=inline)

        embed.add_field(name="\u200b", value="\u200b", inline=False)  # spacer

        for name, value, inline in coin_fields(ticker_b, price_b, ind_b):
            embed.add_field(name=name, value=value, inline=inline)

        embed.add_field(name="Analyst Verdict", value=verdict, inline=False)
        embed.set_footer(text="Data: CoinGecko | Analysis: Anthropic Claude")

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # /market
    # -------------------------------------------------------------------------

    @app_commands.command(name="market", description="Market snapshot: all coins sorted by 24h % change")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer()

        rows, failed = _build_market_rows(list(SUPPORTED_COINS.keys()), self.coingecko)

        if not rows:
            await interaction.followup.send("❌ Unable to fetch market data. Please try again later.")
            return

        block = _format_market_block(rows, failed)

        gainers = sum(1 for r in rows if r["price_change_pct"] >= 0)
        losers = len(rows) - gainers
        if gainers > losers:
            color = discord.Color.green()
        elif losers > gainers:
            color = discord.Color.red()
        else:
            color = discord.Color.light_grey()

        embed = discord.Embed(
            title="Market Snapshot — 24h Change",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="\u200b", value=block, inline=False)
        embed.set_footer(text="Data: CoinGecko | Sorted by 24h % change")
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # /feargreed
    # -------------------------------------------------------------------------

    @app_commands.command(name="feargreed", description="Crypto Fear & Greed Index (0–100 sentiment score)")
    async def feargreed(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            data = self.fear_greed.get_current()
        except Exception as e:
            await interaction.followup.send(f"❌ Fear & Greed error: {e}")
            return

        value = data["value"]
        classification = data["classification"]

        if classification in ("Extreme Fear", "Fear"):
            color = discord.Color.red()
        elif classification == "Neutral":
            color = discord.Color.light_grey()
        else:  # Greed, Extreme Greed
            color = discord.Color.green()

        embed = discord.Embed(
            title="Crypto Fear & Greed Index",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Score", value=str(value), inline=True)
        embed.add_field(name="Classification", value=classification, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(
            name="Previous Day",
            value=f"{data['previous_value']} — {data['previous_classification']}",
            inline=False,
        )
        embed.set_footer(text=f"Data: Alternative.me | Updated: {data['timestamp']}")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Called by bot.load_extension('cogs.crypto')."""
    await bot.add_cog(CryptoCog(bot, bot.coingecko, bot.analyst, bot.fear_greed))
