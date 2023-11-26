from twitchio.ext import commands
from typing import Optional

import json

import requests

from bot.utilities import ids
from data import data

import os

from dotenv import load_dotenv

load_dotenv()

PP_ADDICT_APIKEY = os.getenv("PP_ADDICT_APIKEY")
OSU_V1_APIKEY = os.getenv("OSU_V1_APIKEY")

class Osu(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel)
    async def osuset(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """Command for configuring the linked osu account."""

        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            return

        if arg is None:
            await ctx.reply("You must specify a user for this command. (Usage: !osuset <username>)")
            return

        arg = arg.replace(" 󠀀", "")  # Remove invisible characters in Twitch messages

        user_request = await get_user(arg)

        try:
            user_id = user_request.json()[0]["user_id"]
        except IndexError:
            await ctx.reply("The osu! account you specified appears to be invalid.")
            return

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        # Ensure "osu" key exists in channel_data
        channel_data.setdefault("osu", {})

        channel_data["osu"]["user_id"] = user_id

        data.update_data(channel_id, channel_data)

        osu_profile_url = f"https://osu.ppy.sh/users/{user_id}"
        await ctx.reply(f"Successfully linked {ctx.channel.name} with: {osu_profile_url}")
        print(f"[osu] {ctx.author.name} has linked {ctx.channel.name} with: {osu_profile_url}")

    @commands.command()
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel)
    async def map(self, ctx: commands.Context, *, arg: Optional[str] = None):

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

        # Format and send the reply
        pp_values_string = ""
        for key, value in accuracy_values.items():
            pp_values_string += f"{round(float(key) * 100)}%: {value}PP, "

        reply_message = f"{beatmap_title} [{beatmap_diff_name}] ({beatmap_stars}) +{mods_string} https://osu.ppy.sh/b/{beatmap_id} | {pp_values_string}"
        await ctx.reply(reply_message)

async def get_rank(channel_name):

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


def osu_mods_to_string(mods_integer):
    mods = {
        0: "NoMod",# No Mod
        1: "NF",   # No Fail
        2: "EZ",   # Easy
        4: "TD",   # Touch Device
        8: "HD",   # Hidden
        16: "HR",  # Hard Rock
        32: "SD",  # Sudden Death
        64: "DT",  # Double Time
        128: "RX", # Relax
        256: "HT", # Half Time
        512: "NC", # Nightcore
        1024: "FL",# Flashlight
        2048: "AU",# Autoplay
        4096: "SO",# Spun Out
        8192: "AP",# Autopilot
        16384: "PF",# Perfect
        32768: "4K",# Key 4
        65536: "5K",# Key 5
        131072: "6K",# Key 6
        262144: "7K",# Key 7
        524288: "8K",# Key 8
        1048576: "FI",# Fade In
        2097152: "RD",# Random
        4194304: "CN",# Cinema
        8388608: "TP",# Target Practice
        16777216: "9K",# Key 9
        33554432: "CO",# Key Co-op
        67108864: "1K",# Key 1
        134217728: "3K",# Key 3
        268435456: "2K",# Key 2
        536870912: "V2",# ScoreV2
    }

    if mods_integer == 0:
        return "NoMod"

    mod_string = ""
    for mod_value in sorted(mods.keys(), reverse=True):
        if mods_integer & mod_value:
            mod_string += mods[mod_value]

    return mod_string

def prepare(bot: commands.Bot):
    bot.add_cog(Osu(bot))