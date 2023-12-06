from twitchio.ext import commands
from typing import Optional

from bot.cogs import valorant, osu
from bot.utilities import ids, add_mention
from data import data

class GlobalRank(commands.Cog):
    """
    A Twitch bot cog for handling global rank commands.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the GlobalRank cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command(aliases=["rr", "elo"])
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel)
    async def rank(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing all game ranks.

        Parameters:
            ctx (commands.Context): The context of the command.
            arg (Optional[str]): Additional arguments for the command.

        Usage:
            !rank
        """

        # Process mention argument
        mention = add_mention.process_mention(arg)

        # Get channel data
        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "rank" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        # Get ranks for different games
        ranks = {
            "VALORANT": await valorant.get_rank(ctx.channel.name),
            "osu!": await osu.get_rank(ctx.channel.name)
        }

        result = ""

        # Format the result with game ranks
        for game, rank in ranks.items():
            if rank is not None:
                result += f" {game}: {rank},"

        # Check if there are linked accounts
        if result == "":
            await ctx.reply("No linked accounts. To link accounts see !commands.")
            return

        await ctx.reply(mention + result)


def prepare(bot: commands.Bot):
    bot.add_cog(GlobalRank(bot))
