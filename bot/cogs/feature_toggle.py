from twitchio.ext import commands
from typing import Optional

from data import data
from bot.utilities import ids


class FeatureToggle(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["featuretoggle",
                               "ft"])
    async def feature_toggle(self, ctx: commands.Context, *, arg: Optional[str] = None):

        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        features = [

                    "watchstreaks", # Entire watchstreaks feature
                    "firsts", # Entire firsts feature

                    "rank",  # Global rank command

                    "osu.map", # osu related

                    "valorant.radiant",  # valorant related
                    "valorant.record",  # valorant related
                    "valorant.winlossnoti"  # valorant related

                    ]

        args = arg.split(" ")
        if args[0].lower() not in ["enable", "disable"]:
            await ctx.reply("You must specify what action you want to do. (Usage: !ft <enable/disable> <feature>)")
            return

        if args[1].lower() not in features:
            await ctx.reply("The feature you specified is not valid, view the wiki for more help.")
            return

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        if "disabled_features" not in channel_data:
            channel_data["disabled_features"] = []

        if args[0].lower() == "enable":
            if args[1].lower() not in channel_data["disabled_features"]:
                await ctx.reply("You cannot enable a feature that is already enabled.")
                return
            channel_data["disabled_features"].remove(args[1].lower())
            await ctx.reply(f"You have successfully enabled {args[1].lower()}.")

        if args[0].lower() == "disable":
            if args[1].lower() in channel_data["disabled_features"]:
                await ctx.reply("You cannot disable a feature that is already disabled.")
                return
            channel_data["disabled_features"].append(args[1].lower())
            await ctx.reply(f"You have successfully disabled {args[1].lower()}.")

        data.update_data(channel_id, channel_data)


def prepare(bot: commands.Bot):
    bot.add_cog(FeatureToggle(bot))
