from twitchio.ext import commands
from typing import Optional
from dotenv import load_dotenv
import os

from data import data

load_dotenv()


class Register(commands.Cog):
    """
    A Twitch bot cog for user registration.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Register cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command()
    async def register(self, ctx: commands.Context, arg: Optional[int]):
        """
        Command for registering to the bot.

        This command allows Twitch users to register their accounts with the bot.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[int]): An optional argument (unused).

        Usage:
            !register [arg]
        """

        # Check if the bot is in public mode
        if os.getenv('BOT_PUBLIC') != "true":
            return

        # Get Twitch bot's nickname from environment variable
        twitch_nick = os.getenv('TWITCH_NICK')

        # Check if the command is executed in the correct channel
        if ctx.channel.name.lower() != twitch_nick.lower():
            return

        # Check if the user is trying to register the bot itself
        if ctx.author.name.lower() == twitch_nick.lower():
            await ctx.reply("You cannot register to your own bot, as it is automatically in your own channel.")
            return

        # Retrieve linked accounts data
        linked_channels = data.get_data("linked_accounts")

        if "accounts" not in linked_channels:
            linked_channels["accounts"] = []

        # Check if the user is already registered
        if str(ctx.author.id) in linked_channels["accounts"]:
            await ctx.reply(f"Your account is already registered to {twitch_nick}.")
            return

        # Add user to the list of registered accounts
        linked_channels["accounts"].append(str(ctx.author.id))
        data.update_data("linked_accounts", linked_channels)

        # Respond with a success message
        await ctx.reply(f"You have successfully added {twitch_nick} to your stream!")

        # Join the user's channel
        await self.bot.join_channels([ctx.author.name])


def prepare(bot: commands.Bot):
    bot.add_cog(Register(bot))