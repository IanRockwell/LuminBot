from twitchio.ext import commands
from typing import Optional
from dotenv import load_dotenv
import os

from data import data

load_dotenv()


class Register(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def register(self, ctx: commands.Context, arg: Optional[int]):
        """
        The command for registering to the bot

        This command allows Twitch users to register their accounts with the bot.
        """

        if os.getenv('BOT_PUBLIC') != "true":
            return

        twitch_nick = os.getenv('TWITCH_NICK')

        if ctx.channel.name.lower() != twitch_nick.lower():
            return

        if ctx.author.name.lower() == twitch_nick.lower():
            await ctx.reply(f"You cannot register to your own bot, as it is automatically in your own channel.")
            return

        linked_channels = data.get_data("linked_accounts")

        if "accounts" not in linked_channels:
            linked_channels["accounts"] = []

        if str(ctx.author.id) in linked_channels["accounts"]:
            await ctx.reply(f"Your account is already registered to {twitch_nick}.")
            return

        linked_channels["accounts"].append(str(ctx.author.id))
        data.update_data("linked_accounts", linked_channels)

        await ctx.reply(f"You have successfully added {twitch_nick} to your stream!")

        await self.bot.join_channels([ctx.author.name])

def prepare(bot: commands.Bot):
    bot.add_cog(Register(bot))