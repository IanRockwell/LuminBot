from twitchio.ext import commands

from bot.cogs import watchstreak, firsts


class GlobalEventHandler(commands.Cog):
    """
    The class that handles any events that multiple cogs call
    from at the same time to prevent any issues with race-conditions
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Wiki cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.Cog.event()
    async def event_message(self, message):
        """
        Global event handler for processing messages and doing the required functions

        Parameters:
            message: The Twitch message.
        """

        await firsts.handle_firsts_message_event(self.bot, message)
        await watchstreak.handle_watchstreaks_message_event(self.bot, message)


def prepare(bot: commands.Bot):
    bot.add_cog(GlobalEventHandler(bot))
