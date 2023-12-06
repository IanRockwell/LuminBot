from twitchio.ext import commands
from typing import Optional

from bot.utilities import ids, known_bots
from data import data

from datetime import datetime

import time


class Firsts(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["firsts"])
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel)
    async def first(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing all firsts related data

        Parameters:
            ctx (commands.Context): The command context.

        Usage:
            !first
            !first top
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "firsts" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if arg is None:

            user_id = ctx.author.id
            user_data = data.get_data(user_id)

            try:
                firsts = user_data[f"streamer_{channel_id}_firsts"]["firsts"]
            except (KeyError, ValueError):
                firsts = 0

            try:
                first_person = channel_data["firsts"]["first_person"]
            except (KeyError, ValueError):
                first_person = "None"

            await ctx.reply(f"PartyHat {first_person} was here first! PartyHat You have been first {firsts} times PartyHat")
            return

        arg = arg.replace(" 󠀀", "")  # why oh why are there invisible characters in my twitch messages

        if arg == "top":

            leaderboard = "PogChamp Top Firsts: "

            sorted_documents = data.get_sorted_document_ids(f"streamer_{channel_id}_firsts.firsts")

            for index, document_id in enumerate(sorted_documents):

                if index >= 10:
                    break

                document = data.get_data(document_id)
                document_firsts = document[f"streamer_{channel_id}_firsts"]["firsts"]
                document_user = ids.get_name_from_id(document_id)

                leaderboard = leaderboard + f"{index + 1}. {document_user} ({document_firsts}), "

            await ctx.reply(leaderboard + "PogChamp")
            return

    @commands.Cog.event()
    async def event_message(self, message):

        if message.content.startswith("!"):
            return

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

        stream = await self.bot.fetch_streams(user_logins=[message.channel.name], type="live")

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

        try:
            user_firsts = user_data[f"streamer_{channel_id}_firsts"]["firsts"]
            user_firsts += 1
        except (KeyError, ValueError):
            user_firsts = 1

        try:
            user_data[f"streamer_{channel_id}_firsts"]["firsts"] = user_firsts
        except (KeyError, ValueError):
            user_data[f"streamer_{channel_id}_firsts"] = {}
            user_data[f"streamer_{channel_id}_firsts"]["firsts"] = user_firsts

        data.update_data(message.author.id, user_data)

        await self.bot.get_channel(message.channel.name).send(
            f"PartyHat {message.author.name} was first and now has {user_firsts} firsts! PartyHat")
        print(
            f"[firsts] {message.author.name} was first and now has {user_firsts} firsts in {message.channel.name}'s channel")


def prepare(bot: commands.Bot):
    bot.add_cog(Firsts(bot))
