from twitchio.ext import commands
from twitchio.ext import routines

from bot.cogs import watchstreak, firsts, custom_commands, valorant

from data import data


class GlobalEventHandler(commands.Cog):
    """
    The class that handles any events that multiple cogs call from at the
    same time to prevent any issues with race-condition related issues
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Wiki cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

        # Starting the background routine
        self.background_routine.start()

    @commands.Cog.event()
    async def event_message(self, message):
        """
        Global event handler for processing messages and doing the required functions

        Parameters:
            message: The Twitch message.
        """

        await firsts.handle_firsts_message_event(self.bot, message)
        await watchstreak.handle_watchstreaks_message_event(self.bot, message)
        await custom_commands.handle_command_message_event(self.bot, message)

    @routines.routine(seconds=60)
    async def background_routine(self):
        """
        Executes a routine every 60 seconds, triggering various functions.

        This routine acts as a central point for scheduling and calling
        different functions at regular intervals.

        Functions triggered include:
        - Valorant win/loss notifications
        - Updating logged stream data for external programs
        """
        connected_channels = self.bot.connected_channels

        if not connected_channels:
            return

        # Extract user logins from connected channels
        user_logins = [channel.name for channel in connected_channels]

        # Fetch live streams for connected channels
        streams = await self.bot.fetch_streams(user_logins=user_logins, type="live")

        # Trigger Valorant win/loss notifications
        await valorant.win_loss_notifications(self.bot, streams)

        # Updating the logged stream data, this is used for external programs
        # to get general information about who is streaming on the bot.
        streams_data = data.get_data("streams")
        streams_data["streams"] = streams
        data.update_data("streams", streams_data)


def prepare(bot: commands.Bot):
    bot.add_cog(GlobalEventHandler(bot))
