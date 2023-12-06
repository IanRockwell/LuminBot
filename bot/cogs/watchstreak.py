from twitchio.ext import commands
from typing import Optional

from bot.utilities import ids, known_bots
from data import data

class Watchstreak(commands.Cog):
    """
    A Twitch bot cog for handling watchstreaks.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Watchstreak cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command(aliases=["watchstreaks", "ws"])
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def watchstreak(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing all watchstreak related data

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): An optional argument for the command.

        Usage:
            !watchstreak
            !watchstreak top
        """

        # Extract channel information
        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        # Check if watchstreaks feature is disabled for the channel
        try:
            if "watchstreaks" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if arg is None:
            # Display user's watchstreak information
            user_id = ctx.author.id
            user_data = data.get_data(user_id)

            try:
                watchstreak = user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak"]
            except (KeyError, ValueError):
                watchstreak = "None"

            try:
                watchstreak_record = user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak_record"]
            except (KeyError, ValueError):
                watchstreak_record = "None"

            await ctx.reply(f"PartyHat Your current watchstreak is: {watchstreak} (Your record is: {watchstreak_record})")
            return

        arg = arg.replace(" 󠀀", "")  # Remove invisible characters from the argument

        if arg == "top":
            # Display the top 10 watchstreaks in the channel
            leaderboard = "PogChamp Top Active Watchstreaks: "
            sorted_documents = data.get_sorted_document_ids(f"streamer_{channel_id}_watchstreaks.watchstreak")

            for index, document_id in enumerate(sorted_documents):
                if index >= 10:
                    break

                document = data.get_data(document_id)
                document_watchstreak = document[f"streamer_{channel_id}_watchstreaks"]["watchstreak"]
                document_user = ids.get_name_from_id(document_id)

                leaderboard = leaderboard + f"{index + 1}. {document_user} ({document_watchstreak}), "

            await ctx.reply(leaderboard + "PogChamp")
            return

    @commands.Cog.event()
    async def event_message(self, message):
        """
        Event handler for processing messages and updating watchstreaks.

        Parameters:
            message: The Twitch message.
        """

        # Check if watchstreaks feature is disabled for the channel
        channel_id = ids.get_id_from_name(message.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "watchstreaks" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        try:
            user_id = message.author.id
        except AttributeError:
            return

        # Fetch the current stream information
        stream = await self.bot.fetch_streams(user_logins=[message.channel.name], type="live")

        if not stream:
            return

        # Update data for the stream
        channel_data.setdefault("firsts", {})
        current_stream = channel_data["firsts"].get("current_stream")

        # If the firsts event is currently running, stop processing watchstreaks
        if current_stream != stream[0].id:
            return

        channel_data.setdefault("watchstreaks", {})
        current_stream = channel_data["watchstreaks"].get("current_stream")
        last_stream = channel_data["watchstreaks"].get("last_stream")

        if current_stream != stream[0].id:
            last_stream = current_stream
            current_stream = stream[0].id

            channel_data["watchstreaks"]["last_stream"] = last_stream
            channel_data["watchstreaks"]["current_stream"] = current_stream

            data.update_data(document_id=channel_id, new_data=channel_data)

            all_watchstreak_documents = data.get_documents_with_key(f"streamer_{channel_id}_watchstreaks.watchstreak")

            for document_id in all_watchstreak_documents:
                document = data.get_data(document_id)

                if document[f"streamer_{channel_id}_watchstreaks"]["latest_stream"] not in [last_stream, current_stream]:
                    del document[f"streamer_{channel_id}_watchstreaks"]["watchstreak"]
                    data.update_data(document_id, document)

        if message.author.name in known_bots.KNOWN_BOTS:
            return

        user_data = data.get_data(user_id)

        try:
            user_latest_stream = user_data[f"streamer_{channel_id}_watchstreaks"]["latest_stream"]
            user_watchstreak = user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak"]
            user_watchstreak_record = user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak_record"]
        except (KeyError, ValueError):
            user_latest_stream = current_stream
            user_watchstreak = 1

            user_data[f"streamer_{channel_id}_watchstreaks"] = {}

            user_data[f"streamer_{channel_id}_watchstreaks"]["latest_stream"] = user_latest_stream
            user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak"] = user_watchstreak

            user_watchstreak_record = user_data.get(f"streamer_{channel_id}_watchstreaks", {}).get("watchstreak_record")

            if user_watchstreak_record is None:
                user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak_record"] = user_watchstreak

            data.update_data(message.author.id, user_data)
            return

        # Do nothing if the user's last stream is already this stream
        if user_latest_stream == current_stream:
            return

        # If the user's last stream is not the last stream, reset watchstreak back to 1
        if user_latest_stream != last_stream:
            user_latest_stream = current_stream
            user_watchstreak = 1
        else:
            # If the user's last stream is the last stream, add 1 to the watchstreak
            user_latest_stream = current_stream
            user_watchstreak += 1

            if user_watchstreak % 5 == 0:
                await self.bot.get_channel(message.channel.name).send(
                    f"PartyHat {message.author.name} has reached a watchstreak of {user_watchstreak}! PartyHat")
                print(
                    f"[watchstreak] {message.author.name} has reached a {user_watchstreak} watchstreak in {message.channel.name}'s channel")

        user_data[f"streamer_{channel_id}_watchstreaks"]["latest_stream"] = user_latest_stream
        user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak"] = user_watchstreak

        if user_watchstreak_record < user_watchstreak:
            user_data[f"streamer_{channel_id}_watchstreaks"]["watchstreak_record"] = user_watchstreak

        data.update_data(message.author.id, user_data)


def prepare(bot: commands.Bot):
    bot.add_cog(Watchstreak(bot))
