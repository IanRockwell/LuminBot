from twitchio.ext import commands
from typing import Optional

class Wiki(commands.Cog):
    """
    A Twitch bot cog for handling wiki commands.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Wiki cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command(aliases=["commands"])
    async def wiki(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for providing a link to the bot's commands wiki.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): An optional argument for the command.
        """

        # Reply with a link to the bot's commands wiki on GitHub
        await ctx.reply("You can view all the commands here: https://github.com/IanRockwell/LuminBot/wiki")


def prepare(bot: commands.Bot):
    bot.add_cog(Wiki(bot))