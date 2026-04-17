import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from services.claude_analyst import ClaudeAnalyst
from services.coingecko import CoinGeckoClient
from services.fear_greed import FearGreedClient


class CryptoBot(commands.Bot):
    async def setup_hook(self):
        self.coingecko = CoinGeckoClient()
        self.analyst = ClaudeAnalyst()
        self.fear_greed = FearGreedClient()
        # Load the cog before syncing so commands are registered
        await self.load_extension("cogs.crypto")
        # Sync slash commands globally — takes up to 1 hour to propagate on first run
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message):
        pass  # slash commands only — skip prefix processing to suppress missing-intent warning


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN environment variable is not set.")
    intents = discord.Intents.default()
    bot = CryptoBot(command_prefix="!", intents=intents)
    bot.run(token)
