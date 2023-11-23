from twitchio.ext import commands
from typing import Optional

from bot.cogs import valorant


class GlobalRank(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["rr", "elo"])
    async def rank(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """Command for viewing all game ranks."""

        ranks = {"VALORANT": await valorant.get_rank(ctx.channel.name)}

        result = ""

        for game, rank in ranks.items():

            if rank is None:
                continue

            result = result + f" {game}: {rank},"

        if result == "":
            await ctx.reply("No linked accounts. To link accounts see !commands.")
            return

        await ctx.reply(result)

    """
    @commands.Cog.event()
    async def event_message(self, message):
        print(f"{message.content}")
    """


def prepare(bot: commands.Bot):
    bot.add_cog(GlobalRank(bot))
