from twitchio.ext import commands
from typing import Optional


class Wiki(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["commands"])
    async def wiki(self, ctx: commands.Context, *, arg: Optional[str] = None):

        await ctx.reply("You can view all the commands here: https://github.com/IanRockwell/LuminBot/wiki")


def prepare(bot: commands.Bot):
    bot.add_cog(Wiki(bot))