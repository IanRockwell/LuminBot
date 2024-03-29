from twitchio.ext import commands
from typing import Optional

from bot.utilities import ids, known_bots
from data import data


class Firsts(commands.Cog):
    """
    A Twitch bot cog for handling 'firsts' related commands and events.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Firsts cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command(aliases=["firsts"])
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def first(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing all 'firsts' related data.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): Additional arguments for the command.

        Usage:
            !first
            !first top
        """

        # Get channel data
        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "firsts" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if arg is None:
            await self.handle_basic_firsts(ctx, channel_id, channel_data)
            return

        arg = arg.replace(" 󠀀", "")  # Remove invisible characters from the argument
        args = arg.split(" ")

        if args[0] == "top":
            await self.handle_top_firsts(ctx, channel_id)
            return

        if args[0] == "set":

            # Check if the command issuer is a moderator or broadcaster
            if not ctx.author.is_mod and not ctx.author.is_broadcaster:
                return

            if len(args) < 3:
                await ctx.reply("Invalid usage. Correct usage: !first set <user> <count>")
                return

            username = args[1]
            firsts_value = args[2]

            # Convert username to user ID
            user_id = ids.get_id_from_name(username)
            if user_id == -1:
                await ctx.reply("The user you specified is not a valid Twitch user.")
                return

            try:
                firsts_count = int(firsts_value)
            except ValueError:
                await ctx.reply("The firsts count you specified is not a valid integer.")
                return

            # Update the firsts count for the specified user
            user_data = data.get_data(user_id)
            channel_id = ids.get_id_from_name(ctx.channel.name)

            user_data.setdefault(f"streamer_{channel_id}_firsts", {})
            user_data[f"streamer_{channel_id}_firsts"]["firsts"] = firsts_count

            # Update the data
            data.update_data(user_id, user_data)

            await ctx.reply(f"Firsts count for {username} set to {firsts_count}.")

    async def handle_basic_firsts(self, ctx: commands.Context, channel_id: str, channel_data: dict):
        """
        Helper method to handle basic 'firsts' command.

        Parameters:
            ctx (commands.Context): The command context.
            channel_id (str): The channel ID.
            channel_data (dict): The channel data.
        """
        user_id = ctx.author.id
        user_data = data.get_data(user_id)

        try:
            firsts_data = user_data[f"streamer_{channel_id}_firsts"]
            firsts = firsts_data.get("firsts", 0)
        except (KeyError, ValueError):
            firsts = 0

        try:
            first_person_data = channel_data["firsts"]
            first_person = first_person_data.get("first_person", "None")
        except (KeyError, ValueError):
            first_person = "None"

        await ctx.reply(f"PartyHat {first_person} was here first! PartyHat You have been first {firsts} times PartyHat")

    async def handle_top_firsts(self, ctx: commands.Context, channel_id: str):
        """
        Helper method to handle 'top firsts' command.

        Parameters:
            ctx (commands.Context): The command context.
            channel_id (str): The channel ID.
        """
        leaderboard = "PogChamp Top Firsts: "

        sorted_documents = data.get_sorted_document_ids(f"streamer_{channel_id}_firsts.firsts")

        for index, document_id in enumerate(sorted_documents):
            if index >= 10:
                break

            document = data.get_data(document_id)
            document_firsts = document[f"streamer_{channel_id}_firsts"]["firsts"]
            document_user = ids.get_name_from_id(document_id)

            leaderboard += f"{index + 1}. {document_user} ({document_firsts}), "

        await ctx.reply(leaderboard + "PogChamp")


async def handle_firsts_message_event(bot, message):
    """
    Event handler for processing firsts and updating data.

    This event is called inside the global_event_handler
    in order to prevent very annoying race conditions.

    Parameters:
        bot: The Twitch bot instance.
        message: The incoming message.
    """

    if message.content.startswith("!"):
        return

    # Get channel data
    channel_id = ids.get_id_from_name(message.channel.name)
    channel_data = data.get_data(channel_id)

    try:
        if "firsts" in channel_data["disabled_features"]:
            return
    except (KeyError, ValueError):
        pass

    try:
        user_id = message.author.id
    except AttributeError:
        return

    # If the user is in the known bots list, return
    if message.author.name in known_bots.KNOWN_BOTS:
        return

    stream = await bot.fetch_streams(user_logins=[message.channel.name], type="live")

    if not stream:
        return

    # Update data for the stream
    channel_data.setdefault("firsts", {})
    current_stream = channel_data["firsts"].get("current_stream")

    if current_stream == stream[0].id:
        return

    current_stream = stream[0].id
    channel_data["firsts"]["current_stream"] = current_stream
    channel_data["firsts"]["first_person"] = message.author.name
    data.update_data(channel_id, channel_data)

    user_data = data.get_data(user_id)

    user_firsts = user_data.get(f"streamer_{channel_id}_firsts", {}).get("firsts", 0) + 1

    user_data.setdefault(f"streamer_{channel_id}_firsts", {})
    user_data[f"streamer_{channel_id}_firsts"]["firsts"] = user_firsts

    data.update_data(message.author.id, user_data)

    channel = bot.get_channel(message.channel.name)
    await channel.send(f"PartyHat {message.author.name} was first and now has {user_firsts} firsts! PartyHat")
    print(
        f"[firsts] {message.author.name} was first and now has {user_firsts} firsts in {message.channel.name}'s channel")


def prepare(bot: commands.Bot):
    bot.add_cog(Firsts(bot))
