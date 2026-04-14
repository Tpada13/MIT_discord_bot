import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class CryptoBot(commands.Bot):
    async def setup_hook(self):
        # Load the cog before syncing so commands are registered
        await self.load_extension("cogs.crypto")
        # Sync slash commands globally — takes up to 1 hour to propagate on first run
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
bot = CryptoBot(command_prefix="!", intents=intents)

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
