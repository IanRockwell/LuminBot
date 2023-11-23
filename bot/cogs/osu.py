from twitchio.ext import commands
from typing import Optional

from bot.utilities import ids
from data import data


class Osu(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def osuset(self, ctx: commands.Context, *, arg: Optional[str]):
        """Command for configuring the linked osu account."""

    """
    @commands.Cog.event()
    async def event_message(self, message):
        print(f"{message.content}")
    """


def prepare(bot: commands.Bot):
    bot.add_cog(Osu(bot))
