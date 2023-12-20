from twitchio.ext import commands
from typing import Optional

from data import data
from bot.utilities import ids


class FeatureToggle(commands.Cog):
    """
    A Twitch bot cog for enabling and disabling various features.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the FeatureToggle cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command(aliases=["featuretoggle", "ft"])
    async def feature_toggle(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for enabling or disabling specific features.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): An optional argument for the command.

        Usage:
            !ft <enable/disable> <feature>
        """

        # Check if the command issuer is a moderator or broadcaster
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        # List of available features
        features = [
            "customcommands",  # Entire custom commands feature
            "watchstreaks",  # Entire watchstreaks feature
            "firsts",  # Entire firsts feature
            "rank",  # Global rank command

            "osu.map",  # osu related
            "osu.profile",  # osu related
            "osu.recent",  # osu related

            "valorant.radiant",  # valorant related
            "valorant.record",  # valorant related
            "valorant.winlossnoti"  # valorant related
        ]

        # Split the argument into components
        args = arg.split(" ")

        # Validate the command syntax
        if args[0].lower() not in ["enable", "disable"]:
            await ctx.reply("You must specify what action you want to do. (Usage: !ft <enable/disable> <feature>)")
            return

        # Validate the specified feature
        if args[1].lower() not in features:
            await ctx.reply("The feature you specified is not valid, view the wiki for more help.")
            return

        # Extract channel information
        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        # Ensure that the 'disabled_features' key exists in the channel_data dictionary
        if "disabled_features" not in channel_data:
            channel_data["disabled_features"] = []

        # Enable or disable the specified feature based on the command
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

        # Update the channel_data with the modified feature settings
        data.update_data(channel_id, channel_data)


def prepare(bot: commands.Bot):
    bot.add_cog(FeatureToggle(bot))
