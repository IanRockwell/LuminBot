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
            await self.handle_basic_watchstreak(ctx, channel_id)
            return

        arg = arg.replace(" 󠀀", "")  # Remove invisible characters from the argument
        args = arg.split(" ")

        if args[0] == "top":
            await self.handle_top_watchstreaks(ctx, channel_id)
            return

        if args[0] == "recordtop":
            await self.handle_recordtop_watchstreaks(ctx, channel_id)
            return

        if args[0] == "set":

            # Check if the command issuer is a moderator or broadcaster
            if not ctx.author.is_mod and not ctx.author.is_broadcaster:
                return

            if len(args) < 3:
                await ctx.reply("Invalid usage. Correct usage: !watchstreak set <user> <streak> [-resetrecord]")
                return

            username = args[1]
            streak_value = args[2]

            # Convert username to user ID
            user_id = ids.get_id_from_name(username)
            if user_id == -1:
                await ctx.reply("The user you specified is not a valid Twitch user.")
                return

            try:
                streak = int(streak_value)
            except ValueError:
                await ctx.reply("The watchstreak value you specified is not a valid integer.")
                return

            # Update the watchstreak data for the specified user
            user_data = data.get_data(user_id)

            try:
                user_watchstreak_data = user_data[f"streamer_{channel_id}_watchstreaks"]
            except (KeyError, ValueError):
                user_watchstreak_data = {
                    "latest_stream": None,
                    "watchstreak": 0,
                    "watchstreak_record": 0,
                }

            previous_record = user_watchstreak_data.get("watchstreak_record", 0)

            user_watchstreak_data["watchstreak"] = streak

            # Update the record watchstreak if the new streak is higher
            if streak > previous_record:
                user_watchstreak_data["watchstreak_record"] = streak
            elif len(args) > 3 and args[3] == "-resetrecord":
                user_watchstreak_data["watchstreak_record"] = streak

            user_data[f"streamer_{channel_id}_watchstreaks"] = user_watchstreak_data

            # Update the data
            data.update_data(user_id, user_data)

            await ctx.reply(f"Watchstreak for {username} set to {streak}.")


    async def handle_basic_watchstreak(self, ctx: commands.Context, channel_id: str):
        """
        Helper method to handle basic 'watchstreak' command.

        Parameters:
            ctx (commands.Context): The command context.
            channel_id (str): The channel ID.
        """
        user_id = ctx.author.id
        user_data = data.get_data(user_id)

        try:
            watchstreak_data = user_data[f"streamer_{channel_id}_watchstreaks"]
            watchstreak = watchstreak_data.get("watchstreak", "None")
            watchstreak_record = watchstreak_data.get("watchstreak_record", "None")
        except (KeyError, ValueError):
            watchstreak = watchstreak_record = "None"

        await ctx.reply(f"PartyHat Your current watchstreak is: {watchstreak} (Your record is: {watchstreak_record})")

    async def handle_top_watchstreaks(self, ctx: commands.Context, channel_id: str):
        """
        Helper method to handle 'top watchstreaks' command.

        Parameters:
            ctx (commands.Context): The command context.
            channel_id (str): The channel ID.
        """
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

    async def handle_recordtop_watchstreaks(self, ctx: commands.Context, channel_id: str):
        """
        Helper method to handle 'recordtop watchstreaks' command.

        Parameters:
            ctx (commands.Context): The command context.
            channel_id (str): The channel ID.
        """
        leaderboard = "PogChamp Top Watchstreak Records: "
        sorted_documents = data.get_sorted_document_ids(f"streamer_{channel_id}_watchstreaks.watchstreak_record")

        for index, document_id in enumerate(sorted_documents):
            if index >= 10:
                break

            document = data.get_data(document_id)
            document_watchstreak = document[f"streamer_{channel_id}_watchstreaks"]["watchstreak_record"]
            document_user = ids.get_name_from_id(document_id)

            leaderboard = leaderboard + f"{index + 1}. {document_user} ({document_watchstreak}), "

        await ctx.reply(leaderboard + "PogChamp")


async def handle_watchstreaks_message_event(bot, message):
    """
    Event handler for processing messages and updating watchstreaks.

    This event is called inside the global_event_handler
    in order to prevent very annoying race conditions.

    Parameters:
        bot: The Twitch bot instance.
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
    stream = await bot.fetch_streams(user_logins=[message.channel.name], type="live")

    if not stream:
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

            latest_stream = document[f"streamer_{channel_id}_watchstreaks"]["latest_stream"]

            if latest_stream not in [last_stream, current_stream]:
                del document[f"streamer_{channel_id}_watchstreaks"]["watchstreak"]
                data.update_data(document_id, document)

    if message.author.name in known_bots.KNOWN_BOTS:
        return

    user_data = data.get_data(user_id)

    try:
        user_watchstreak_data = user_data[f"streamer_{channel_id}_watchstreaks"]
    except (KeyError, ValueError):
        user_watchstreak_data = {
            "latest_stream": current_stream,
            "watchstreak": 1,
            "watchstreak_record": 1,
        }
        user_data[f"streamer_{channel_id}_watchstreaks"] = user_watchstreak_data
        data.update_data(user_id, user_data)
        return

    user_latest_stream = user_watchstreak_data["latest_stream"]
    user_watchstreak = user_watchstreak_data["watchstreak"]
    user_watchstreak_record = user_watchstreak_data["watchstreak_record"]

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
            channel = bot.get_channel(message.channel.name)
            await channel.send(
                f"PartyHat {message.author.name} has reached a watchstreak of {user_watchstreak}! PartyHat")
            print(
                f"[watchstreak] {message.author.name} has reached a {user_watchstreak} watchstreak in {message.channel.name}'s channel")

    user_watchstreak_data["latest_stream"] = user_latest_stream
    user_watchstreak_data["watchstreak"] = user_watchstreak

    if user_watchstreak_record < user_watchstreak:
        user_watchstreak_data["watchstreak_record"] = user_watchstreak

    data.update_data(user_id, user_data)


def prepare(bot: commands.Bot):
    bot.add_cog(Watchstreak(bot))
