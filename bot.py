import os

import discord
from discord.ext import commands
from dotenv import load_dotenv


class CryptoBot(commands.Bot):
    async def setup_hook(self):
        # Load the cog before syncing so commands are registered
        await self.load_extension("cogs.crypto")

        # Guild-specific sync — instant availability in the dev server
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Slash commands synced to guild {guild_id}.")

        # Global sync — takes up to 1 hour to propagate
        await self.tree.sync()
        print("Slash commands synced globally.")

    async def on_ready(self):
        print(f"Logged in as {self.user}")


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN environment variable is not set.")
    intents = discord.Intents.default()
    bot = CryptoBot(command_prefix="!", intents=intents)
    bot.run(token)
