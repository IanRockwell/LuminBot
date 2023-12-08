from twitchio.ext import commands
from typing import Optional
from dotenv import load_dotenv

import aiohttp
import os
import requests

from bot.utilities import ids
from data import data

load_dotenv()

PP_ADDICT_APIKEY = os.getenv("PP_ADDICT_APIKEY")
OSU_V1_APIKEY = os.getenv("OSU_V1_APIKEY")


class Osu(commands.Cog):
    """
    A Twitch bot cog for handling osu! related commands.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Osu cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command()
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def osuset(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for configuring the linked osu account.

        Parameters:
            ctx (commands.Context): The context of the command.
            arg (Optional[str]): The osu username to link.

        Usage:
            !osuset <username>
        """

        # Check if the user is a mod or broadcaster
        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            return

        # Check if the username argument is provided
        if arg is None:
            await ctx.reply("You must specify a user for this command. (Usage: !osuset <username>)")
            return

        # Remove invisible characters in Twitch messages
        arg = arg.replace(" 󠀀", "")

        # Retrieve user data from osu!
        user_request = await get_user(arg)

        try:
            user_id = user_request.json()[0]["user_id"]
        except IndexError:
            await ctx.reply("The osu! account you specified appears to be invalid.")
            return

        # Retrieve channel data
        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        # Ensure "osu" key exists in channel_data
        channel_data.setdefault("osu", {})

        # Update channel data with osu! user_id
        channel_data["osu"]["user_id"] = user_id
        data.update_data(channel_id, channel_data)

        osu_profile_url = f"https://osu.ppy.sh/users/{user_id}"
        await ctx.reply(f"Successfully linked {ctx.channel.name} with: {osu_profile_url}")
        print(f"[osu] {ctx.author.name} has linked {ctx.channel.name} with: {osu_profile_url}")

    @commands.command()
    async def osuunset(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for unconfiguring the linked osu account.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument (unused).

        Usage:
            !osuunset
        """

        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        channel_data["osu"] = {}

        data.update_data(document_id=channel_id, new_data=channel_data)

        await ctx.reply("Successfully unlinked osu.")

    @commands.command(aliases=["rs"])
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def recent(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing the player's recent play

        Parameters:
            ctx (commands.Context): The context of the command.
            arg (Optional[str]): Additional arguments for the command.

        Usage:
            !recent
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "osu.recent" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        try:
            user_id = channel_data["osu"]["user_id"]
        except (KeyError, ValueError):
            return

        recent_request = await get_recent(user_id)
        recent_info = recent_request.json()
        if not recent_info:
            await ctx.reply(f"{ctx.channel.name} has not played a map recently.")
            return

        pp_info = await get_pp_value(beatmap_id=recent_info[0]["beatmap_id"],
                                     combo=recent_info[0]["maxcombo"],
                                     good=recent_info[0]["count300"],
                                     ok=recent_info[0]["count100"],
                                     meh=recent_info[0]["count50"],
                                     miss=recent_info[0]["countmiss"],
                                     mods=osu_mods_to_list(int(recent_info[0]["enabled_mods"])))

        beatmap_id = recent_info[0]["beatmap_id"]

        beatmap_request = await get_beatmap(beatmap_id)
        beatmap_info = beatmap_request.json()[0]

        beatmap_title = beatmap_info["title"]
        beatmap_diff_name = beatmap_info["version"]
        beatmap_max_combo = beatmap_info["max_combo"]

        accuracy = pp_info['accuracy']
        max_combo = pp_info['max_combo']
        miss = pp_info['miss']
        local_pp = pp_info['local_pp']
        new_sr = pp_info['newSR']

        """
        perfect = pp_info['perfect']
        great = pp_info['great']
        good = pp_info['good']
        aim_pp = pp_info['aim_pp']
        tap_pp = pp_info['tap_pp']
        acc_pp = pp_info['acc_pp']
        """

        rank = recent_info[0]["rank"]
        mods = recent_info[0]["enabled_mods"]
        mods_string = osu_mods_to_string(int(mods))

        await ctx.reply(f"Just played: {beatmap_title} [{beatmap_diff_name}] ({new_sr}⭐️) +{mods_string} https://osu.ppy.sh/b/{beatmap_id} | PP: {round(local_pp)} | Accuracy: {accuracy:.2f}% | Combo: {max_combo}/{beatmap_max_combo} | {miss} misses | Rank: {rank}")


    @commands.command(aliases=["osu"])
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def profile(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for retrieving information about the linked osu account.

        Parameters:
            ctx (commands.Context): The context of the command.
            arg (Optional[str]): Additional arguments for the command.

        Usage:
            !profile
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "osu.profile" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        try:
            user_id = channel_data["osu"]["user_id"]
        except (KeyError, ValueError):
            return

        user_request = await get_user(user_id)
        user_data = user_request.json()[0]

        profile_url = f"https://osu.ppy.sh/u/{user_data['user_id']}"
        rank = user_data["pp_rank"]
        username = user_data["username"]
        pp = round(float(user_data["pp_raw"]))
        country = user_data["country"]
        country_rank = user_data["pp_country_rank"]
        acc = round(float(user_data["accuracy"]), 2)

        await ctx.reply(f"{profile_url} {username}: #{rank} (#{country_rank} {country}) {pp}PP (Profile Acc: {acc}%)")

    @commands.command()
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def map(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for retrieving information about the most recent osu map played.

        Parameters:
            ctx (commands.Context): The context of the command.
            arg (Optional[str]): Additional arguments for the command.

        Usage:
            !map
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "osu.map" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        try:
            user_id = channel_data["osu"]["user_id"]
        except (KeyError, ValueError):
            return

        recent_request = await get_recent(user_id)

        if not recent_request.json():
            await ctx.reply(f"{ctx.channel.name} has not played a map recently.")
            return

        beatmap_id = recent_request.json()[0]["beatmap_id"]
        beatmap_request = await get_beatmap(beatmap_id)

        beatmap_info = beatmap_request.json()[0]
        beatmap_title = beatmap_info["title"]
        beatmap_diff_name = beatmap_info["version"]
        beatmap_stars = round(float(beatmap_info["difficultyrating"]), 2)

        mods = recent_request.json()[0]["enabled_mods"]
        mods_string = osu_mods_to_string(int(mods))

        pp_values_request = await get_pp_values(beatmap_id, mods)

        accuracy_values = {key: None for key in ['1.0', '0.99', '0.97', '0.95']}

        for key, value in pp_values_request.json()["ppForAcc"].items():
            if key in accuracy_values:
                accuracy_values[key] = round(value)

        pp_values_string = ""
        for key, value in accuracy_values.items():
            pp_values_string += f"{round(float(key) * 100)}%: {value}PP, "

        reply_message = f"{beatmap_title} [{beatmap_diff_name}] ({beatmap_stars}⭐️) +{mods_string} https://osu.ppy.sh/b/{beatmap_id} | {pp_values_string}"
        await ctx.reply(reply_message)


async def get_rank(channel_name):
    """
    Get the osu rank information for a specific Twitch channel.

    Parameters:
    - channel_name (str): The name of the Twitch channel.

    Returns:
    str: A formatted string containing osu rank information.
    """

    channel_id = ids.get_id_from_name(channel_name)
    channel_data = data.get_data(channel_id)

    if not channel_data:
        return None

    try:
        user_id = channel_data["osu"]["user_id"]
    except (KeyError, ValueError):
        return None

    user_request = await get_user(user_id)

    rank = user_request.json()[0]["pp_rank"]
    pp = round(float(user_request.json()[0]["pp_raw"]))

    country = user_request.json()[0]["country"]
    country_rank = user_request.json()[0]["pp_country_rank"]

    return f"Rank #{rank} (#{country_rank} {country}) {pp}PP"


async def get_user(username):
    """
    Get osu user information by username.

    Parameters:
    - username (str): The osu username.

    Returns:
    requests.Response: The HTTP response containing user information.
    """
    url = f"https://osu.ppy.sh/api/get_user"

    params = {
        'k': OSU_V1_APIKEY,
        'u': username
    }

    try:
        response = requests.get(url=url, params=params)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving osu! user information: {req_err}")
        return None


async def get_recent(user_id):
    """
    Get the most recent osu play information for a user.

    Parameters:
    - user_id (str): The osu user ID.

    Returns:
    requests.Response: The HTTP response containing recent play information.
    """
    url = f"https://osu.ppy.sh/api/get_user_recent"

    params = {
        'k': OSU_V1_APIKEY,
        'u': user_id
    }

    try:
        response = requests.get(url=url, params=params)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving osu! recent information: {req_err}")
        return None


async def get_beatmap(beatmap_id):
    """
    Get osu beatmap information by beatmap ID.

    Parameters:
    - beatmap_id (str): The osu beatmap ID.

    Returns:
    requests.Response: The HTTP response containing beatmap information.
    """
    url = f"https://osu.ppy.sh/api/get_beatmaps"

    params = {
        'k': OSU_V1_APIKEY,
        'b': beatmap_id
    }

    try:
        response = requests.get(url=url, params=params)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving osu! recent information: {req_err}")
        return None


async def get_pp_values(beatmap_id, mods):
    """
    Get osu PP values for a specific beatmap and mods.

    Parameters:
    - beatmap_id (str): The osu beatmap ID.
    - mods (str): The osu mods.

    Returns:
    requests.Response: The HTTP response containing PP values.
    """
    url = "https://api.tillerino.org/beatmapinfo"

    params = {
        'k': PP_ADDICT_APIKEY,
        'beatmapid': beatmap_id,
        'mods': mods,
    }

    try:
        response = requests.get(url=url, params=params)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving osu! recent information: {req_err}")
        return None


async def get_pp_value(beatmap_id, mods, good, ok, meh, miss, combo):
    url = "https://pp-api.huismetbenen.nl/calculate-score"

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'YOUR_AUTH_TOKEN_HERE',  # Replace with your actual authorization token
    }

    data = {
        'map_id': beatmap_id,
        'mods': mods,
        'good': good,
        'ok': ok,
        'meh': meh,
        'miss': miss,
        'combo': combo,
        'rework': 'live',
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.patch(url=url, json=data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()  # Use await to get the JSON response
        except aiohttp.ClientError as client_err:
            print(f"Error retrieving osu! PP values: {client_err}")
            return None


def osu_mods_to_string(mods_integer):
    """
    Convert osu mods from integer to string representation.

    Parameters:
    - mods_integer (int): The integer representation of osu mods.

    Returns:
    str: The string representation of osu mods.
    """
    mods = {
        0: "NoMod",  # No Mod
        1: "NF",  # No Fail
        2: "EZ",  # Easy
        4: "TD",  # Touch Device
        8: "HD",  # Hidden
        16: "HR",  # Hard Rock
        32: "SD",  # Sudden Death
        64: "DT",  # Double Time
        128: "RX",  # Relax
        256: "HT",  # Half Time
        512: "NC",  # Nightcore
        1024: "FL",  # Flashlight
        2048: "AU",  # Autoplay
        4096: "SO",  # Spun Out
        8192: "AP",  # Autopilot
        16384: "PF",  # Perfect
        32768: "4K",  # Key 4
        65536: "5K",  # Key 5
        131072: "6K",  # Key 6
        262144: "7K",  # Key 7
        524288: "8K",  # Key 8
        1048576: "FI",  # Fade In
        2097152: "RD",  # Random
        4194304: "CN",  # Cinema
        8388608: "TP",  # Target Practice
        16777216: "9K",  # Key 9
        33554432: "CO",  # Key Co-op
        67108864: "1K",  # Key 1
        134217728: "3K",  # Key 3
        268435456: "2K",  # Key 2
        536870912: "V2",  # ScoreV2
    }

    if mods_integer == 0:
        return "NoMod"

    mod_string = ""
    for mod_value in sorted(mods.keys(), key=lambda x: mods[x], reverse=True):
        if mods_integer & mod_value:
            if mods[mod_value] == "DT" and "NC" in mod_string:
                continue  # Skip adding DT if NC is already in mod_string
            mod_string += mods[mod_value]

    return mod_string


def osu_mods_to_list(mods_integer):
    """
    Convert osu mods from integer to a list of string representations.

    Parameters:
    - mods_integer (int): The integer representation of osu mods.

    Returns:
    list: A list containing string representations of osu mods.
    """
    mods = {
        0: "NoMod",  # No Mod
        1: "NF",  # No Fail
        2: "EZ",  # Easy
        4: "TD",  # Touch Device
        8: "HD",  # Hidden
        16: "HR",  # Hard Rock
        32: "SD",  # Sudden Death
        64: "DT",  # Double Time
        128: "RX",  # Relax
        256: "HT",  # Half Time
        512: "NC",  # Nightcore
        1024: "FL",  # Flashlight
        2048: "AU",  # Autoplay
        4096: "SO",  # Spun Out
        8192: "AP",  # Autopilot
        16384: "PF",  # Perfect
        32768: "4K",  # Key 4
        65536: "5K",  # Key 5
        131072: "6K",  # Key 6
        262144: "7K",  # Key 7
        524288: "8K",  # Key 8
        1048576: "FI",  # Fade In
        2097152: "RD",  # Random
        4194304: "CN",  # Cinema
        8388608: "TP",  # Target Practice
        16777216: "9K",  # Key 9
        33554432: "CO",  # Key Co-op
        67108864: "1K",  # Key 1
        134217728: "3K",  # Key 3
        268435456: "2K",  # Key 2
        536870912: "V2",  # ScoreV2
    }

    if mods_integer == 0:
        return []

    mod_list = []
    for mod_value in sorted(mods.keys(), key=lambda x: mods[x], reverse=True):
        if mods_integer & mod_value:
            if mods[mod_value] == "NC":
                mod_list.append("DT")
            else:
                mod_list.append(mods[mod_value])

    return mod_list


def prepare(bot: commands.Bot):
    bot.add_cog(Osu(bot))
