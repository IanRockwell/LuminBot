import time
from twitchio.ext import commands
from bot.utilities import ids
from data import data


class LuminBot(commands.Bot):
    """
    Twitch bot class for LuminBot with pre-loaded cogs.
    """

    cogs = [
        "global_event_handler",

        "feature_toggle",
        "watchstreak",
        "firsts",
        "global_rank",
        "valorant",
        "osu",
        "register",
        "wiki"
    ]

    def __init__(self, nick, token, client_id, client_secret):
        """
        Initializes the LuminBot.

        Parameters:
            nick (str): The bot's Twitch username.
            token (str): The bot's Twitch token.
            client_id (str): The bot's Twitch client ID.
            client_secret (str): The bot's Twitch client secret.
        """

        # Retrieve linked channels data
        linked_channels = data.get_data("linked_accounts")

        # Ensure 'accounts' key exists in linked_channels
        if "accounts" not in linked_channels:
            linked_channels["accounts"] = []

        # Retrieve channel names from linked channels
        channels = tuple(ids.get_name_from_id(key) for key in linked_channels["accounts"])

        # Initialize the Twitch bot
        super().__init__(
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            prefix='!',
            initial_channels=channels + (nick,)
        )

        print("")
        print("Loading modules:")

        # Load each cog module and print loading information
        for cog in self.cogs:
            start_time = time.time()
            self.load_module(f"bot.cogs.{cog}")
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f" - Loaded module: {cog} (in {elapsed_time * 1000:.2f} ms)")
        print("")

    async def event_ready(self):
        """
        Event handler for when the bot is ready.

        Displays information about the connected channels.
        """

        # Retrieve connected channels
        channel_list = self.connected_channels
        channel_names = [channel.name for channel in channel_list]

        print(
            f"[Twitch] Successfully logged in as {self.nick} (ID: {self.user_id}). Overviewing {len(channel_names)} channels.")

        # Display connected channel names (up to 30 for brevity)
        if len(channel_names) <= 30:
            formatted_channel_names = ", ".join(channel_names)
        else:
            formatted_channel_names = ", ".join(channel_names[:30]) + " ..."

        print(f" + Channels: {formatted_channel_names}")

    async def event_command_error(self, ctx, error):
        """
        Event handler for command errors.

        Ignores specific errors and prints others.

        Parameters:
            ctx (commands.Context): The command context.
            error (Exception): The raised exception.
        """

        if isinstance(error, commands.CommandNotFound) or isinstance(error, commands.CommandOnCooldown):
            pass  # Ignore CommandNotFound and CommandOnCooldown errors
        else:
            # Print other errors
            print(f"Ignoring exception in command: {error}")