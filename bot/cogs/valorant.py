from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

import requests
import os
from twitchio.ext import commands

from bot.utilities import ids, add_mention
from data import data

load_dotenv()

HENRIK_DEV_APIKEY = os.getenv("HENRIK_DEV_APIKEY")

# Some basic handling for if no API key is given.
if HENRIK_DEV_APIKEY != "":
    HEADERS = {"Authorization": HENRIK_DEV_APIKEY}
else:
    HEADERS = {}


class Valorant(commands.Cog):
    """
    A Twitch bot cog for handling Valorant-related commands and notifications.
    """

    # This is the amount of seconds a game will last
    # until it is no longer included in the !record command
    TIME_THRESHOLD = 12 * 60 * 60

    def __init__(self, bot: commands.Bot):
        """
        Initializes the Valorant cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    @commands.command(aliases=["valset"])
    async def valorantset(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for configuring the linked Valorant account.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument containing the region and user.

        Usage:
            !valorantset <region> <user>
        """

        # Check if the user is a mod or broadcaster
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        # Check if the argument is provided
        if arg is None:
            await ctx.reply(
                "You must specify a valid region and user for this command. (Usage: !valorantset <region> <user>)")
            return

        # Parse the region and user from the argument
        space_index = arg.find(" ")
        if space_index == -1:
            await ctx.reply(
                "You must specify a valid region and user for this command. (Usage: !valorantset <region> <user>)")
            return

        region = arg[:space_index]
        user = arg[space_index + 1:]

        regions = ["eu", "ap", "na", "kr", "latam", "br"]

        # Validate the region
        if region.lower() not in regions:
            await ctx.reply(
                "You did not specify a valid region (EU, AP, NA, KR, Latam, BR): !valorantset <region> <name>")
            return

        # Validate the user format
        if "#" not in user:
            await ctx.reply("You must specify a valid user type (Example: User#3183): !valorantset <region> <name>")
            return

        if len(user) > 25:
            await ctx.reply("The user you have provided appears to be too long, are you sure it's correct?")
            return

        # Update channel data with Valorant account information
        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        if "valorant" not in channel_data:
            channel_data["valorant"] = {}

        channel_data["valorant"]["account_user"] = user
        channel_data["valorant"]["account_region"] = region

        data.update_data(document_id=channel_id, new_data=channel_data)

        await ctx.reply(f"Successfully linked {ctx.channel.name} with: {user}: {region}")
        print(f"[valorant] {ctx.author.name} has linked {ctx.channel.name} with: {user}: {region}")

    @commands.command(aliases=["valunset"])
    async def valorantunset(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for unconfiguring the linked valorant account.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument (unused).

        Usage:
            !valorantunset
        """

        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        channel_data["valorant"] = {}

        data.update_data(document_id=channel_id, new_data=channel_data)

        await ctx.reply("Successfully unlinked VALORANT.")

    @commands.command()
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def record(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing the streamer's win/loss this stream.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The mentioned user.

        Usage:
            !record
        """

        mention = add_mention.process_mention(arg)

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "valorant.record" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if not channel_data:
            return

        try:
            name, discriminator = channel_data["valorant"]["account_user"].split("#")
            region = channel_data["valorant"]["account_region"]
        except (KeyError, ValueError):
            return

        career_request = await get_career(region=region, name=name, discriminator=discriminator)

        if career_request.status_code != 200:
            await ctx.reply(f"Error: Status code: {career_request.status_code}, Response: {career_request.text}")
            return

        career = career_request.json()

        difference = 0
        win = 0
        loss = 0

        current_time = datetime.now().timestamp()

        for game in career["data"]:
            time_difference = current_time - game["date_raw"]

            if time_difference <= 12 * 60 * 60:
                if game["mmr_change_to_last_game"] >= 1:
                    win += 1
                elif game["mmr_change_to_last_game"] <= 0:
                    loss += 1

                difference += game["mmr_change_to_last_game"]

        if difference <= 0:
            difference_tag = "down"
        else:
            difference_tag = "up"

        await ctx.reply(
            f"{mention}{name} is currently {difference_tag} {difference}RR with {win} wins and {loss} losses in the last 12 hours")

    @commands.command()
    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.channel)
    async def radiant(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing the current radiant threshold.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument (unused).

        Usage:
            !radiant
        """

        mention = add_mention.process_mention(arg)

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "valorant.radiant" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if not channel_data:
            return

        try:
            region = channel_data["valorant"]["account_region"]
        except (KeyError, ValueError):
            return

        await ctx.reply(
            f"{mention}{await get_radiant_rr(region)}RR is the current radiant threshold in {region.upper()}.")

    @commands.command()
    @commands.cooldown(rate=1, per=60, bucket=commands.Bucket.channel)
    async def lastgame(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing the streamer's last game played.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The mentioned user.

        Usage:
            !lastgame
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "valorant.record" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if not channel_data:
            return

        try:
            if "valorant.lastgame" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        try:
            name, discriminator = channel_data["valorant"]["account_user"].split("#")
            region = channel_data["valorant"]["account_region"]
        except (KeyError, ValueError):
            return

        streams = await self.bot.fetch_streams(user_logins=[f"{ctx.channel.name}"], type="live")
        await win_loss_notifications(self.bot, streams, True)


async def win_loss_notifications(bot, streams, command):
    """
    Function for checking win/loss notifications in connected channels.
    """

    for stream in streams:
        # Check if the stream is playing Valorant
        if stream.game_name != "VALORANT":
            continue

        # Get channel data
        channel_id = ids.get_id_from_name(stream.user.name)
        channel_data = data.get_data(channel_id)

        if command is False:
            # Check if win/loss notifications are disabled for the channel
            if channel_data and "valorant.winlossnoti" in channel_data.get("disabled_features", []):
                continue

        try:
            # Get Valorant account information for the channel
            name, discriminator = channel_data["valorant"]["account_user"].split("#")
            region = channel_data["valorant"]["account_region"]
        except (KeyError, ValueError):
            continue

        # Retrieve career information for the Valorant account
        career = await get_career(region=region, name=name, discriminator=discriminator)

        if career.status_code != 200:
            continue

        career_json = career.json()

        # Check if the latest match ID has been remembered
        latest_match_id = career_json["data"][0]["match_id"]
        latest_remembered_match_id = channel_data.get("valorant", {}).get("latest_match_id")

        print(
            f"[valorant] {stream.user.name} -> comparing match ids {latest_match_id} - {latest_remembered_match_id}")

        # If the function is called in a command, ignore if the latest match ID is set or not.
        if command is False:
            if latest_match_id == latest_remembered_match_id:
                continue

        # Update the latest remembered match ID
        channel_data.setdefault("valorant", {})["latest_match_id"] = latest_match_id
        data.update_data(document_id=channel_id, new_data=channel_data)

        # Retrieve detailed information about the latest match
        match = await get_match(latest_match_id)
        match_json = match.json()

        # Extract relevant match details
        all_players = match_json["data"]["players"]["all_players"]
        user_data = next((player for player in all_players if player["name"].lower() == name.lower() and
                          player["tag"].lower() == discriminator.lower()), None)

        if not user_data:
            continue

        # Extract match outcome and player statistics
        red_team_rounds_won, blue_team_rounds_won = (match_json['data']['teams'][team]['rounds_won'] for team in
                                                     ['red', 'blue'])
        score = f"{max(red_team_rounds_won, blue_team_rounds_won)}-{min(red_team_rounds_won, blue_team_rounds_won)}"

        map = match_json["data"]["metadata"]["map"]

        rr_difference = career_json['data'][0]['mmr_change_to_last_game']

        agent = user_data['character']

        ability_casts = user_data['ability_casts']
        c_cast, q_cast, e_cast, x_cast = [ability_casts.get(ability, 0) for ability in
                                          ['c_cast', 'q_cast', 'e_cast', 'x_cast']]
        c_cast_name, q_cast_name, e_cast_name, x_cast_name = [get_ability(agent, ability) for ability in
                                                              ['c', 'q', 'e', 'x']]

        stats = user_data['stats']
        kills, deaths, assists = stats['kills'], stats['deaths'], stats['assists']
        headshots, bodyshots, legshots = stats['headshots'], stats['bodyshots'], stats['legshots']
        headshot_percentage = round((headshots / (headshots + bodyshots + legshots) * 100))

        # Prepare and send the win/loss notification message
        message_header = f"😭{stream.user.name} lost {abs(rr_difference)}RR on {map} | " if rr_difference <= 0 else \
            f"PartyHat {stream.user.name} gained {rr_difference}RR on {map} | "
        message_footer = "😭" if rr_difference <= 0 else "PartyHat"

        message_body = (
            f"Score: {score} | KDA: {kills}/{deaths}/{assists} | Agent: {agent} | "
            f"Abilities: {e_cast_name} {e_cast} times, {q_cast_name} {q_cast} times, "
            f"{c_cast_name} {c_cast} times, {x_cast_name} {x_cast} times | "
            f"Headshot: {headshot_percentage}% | "
            f"Tracker: https://tracker.gg/valorant/match/{latest_match_id} "
        )

        print(
            f"[valorant] {stream.user.name} -> {abs(rr_difference)}RR on {map} https://tracker.gg/valorant/match/{latest_match_id}")

        message_header = f"Last Game Played: {message_header}"

        await bot.get_channel(stream.user.name).send(message_header + message_body + message_footer)


async def get_rank(channel_name):
    """
    Retrieves and formats the Valorant rank information for a Twitch streamer.

    Args:
        channel_name (str): Twitch channel name of the streamer.

    Returns:
        str or None: Formatted Valorant rank details or None if data is unavailable.

    This function is used in the global_rank cog's !rank command to fetch and present
    the Valorant rank of a streamer. It extracts account details (name, discriminator,
    region) from stored data, queries the HenrikDev API for rank information,
    and formats the result. Special handling for Immortal and Radiant ranks includes
    additional details like RR from Radiant for Immortal ranks. If there's an API error,
    it returns an error message with the HTTP status code and response text.
    """

    channel_id = ids.get_id_from_name(channel_name)
    channel_data = data.get_data(channel_id)

    if not channel_data:
        return None

    try:
        name, discriminator = channel_data["valorant"]["account_user"].split("#")
        region = channel_data["valorant"]["account_region"]
    except (KeyError, ValueError):
        return None

    rank_data_request = await get_rr(region=region, name=name, discriminator=discriminator)

    if rank_data_request.status_code != 200:
        return f"Error: Status code: {rank_data_request.status_code}, Response: {rank_data_request.text}"

    rank_json = rank_data_request.json()

    current_tier_patched = rank_json["data"]["currenttierpatched"]
    rank = current_tier_patched.split()[0]

    if rank == "Immortal":
        tier = int(current_tier_patched.split()[1])
        rr = rank_json["data"]["ranking_in_tier"]
        radiant_rr = await get_radiant_rr(region=region)

        rr_from_radiant = radiant_rr - rr

        result = f"{rank} {tier} - {rr}RR ({rr_from_radiant}RR from Radiant)"

    elif rank == "Radiant":
        rr = rank_json["data"]["ranking_in_tier"]
        result = f"{rank} - {rr}RR"

    else:
        tier = int(current_tier_patched.split()[1])
        rr = rank_json["data"]["ranking_in_tier"]
        result = f"{rank} {tier} - {rr}RR"

    return result


async def get_rr(region: str, name: str, discriminator: str):
    """
    Get Valorant rank information.

    Parameters:
        region (str): The Valorant region.
        name (str): The Valorant account name.
        discriminator (str): The Valorant account discriminator.

    Returns:
        Response: The HTTP response containing rank information.
    """

    url = f"https://api.henrikdev.xyz/valorant/v1/mmr/{region}/{name}/{discriminator}?show=combo&display=0"

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving Valorant rank information: {req_err}")
        return None


async def get_match(match_id):
    """
    Get Valorant match information.

    Parameters:
        match_id (str): The ID of the Valorant match.

    Returns:
        Response: The HTTP response containing match information.
    """

    url = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving Valorant match information: {req_err}")
        return None


async def get_career(region: str, name: str, discriminator: str):
    """
    Get Valorant career information.

    Parameters:
        region (str): The Valorant region.
        name (str): The Valorant account name.
        discriminator (str): The Valorant account discriminator.

    Returns:
        Response: The HTTP response containing career information.
    """

    url = f"https://api.henrikdev.xyz/valorant/v1/mmr-history/{region}/{name}/{discriminator}"

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving Valorant career information: {req_err}")
        return None


async def get_leaderboard(region: str):
    """
    Get Valorant leaderboard information.

    Parameters:
        region (str): The Valorant region.

    Returns:
        Response: The HTTP response containing leaderboard information.
    """

    url = f"https://api.henrikdev.xyz/valorant/v1/leaderboard/{region}"

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        print(f"Error retrieving Valorant leaderboard information: {req_err}")
        return None


async def get_radiant_rr(region: str):
    """
    Get the amount of RR currently needed for radiant in any given region.

    Parameters:
        region (str): The Valorant region.

    Returns:
        int: The radiant RR threshold.
    """

    leaderboard_request = await get_leaderboard(region=region)
    json = leaderboard_request.json()
    ranked_rating_500 = next(item["rankedRating"] for item in json if item["leaderboardRank"] == 500)
    return max(ranked_rating_500, 450)


def get_ability(agent, keybind):
    """
    Get the ability corresponding to the valorant agent and keybind.

    Parameters:
        agent (str): The name of the agent.
        keybind (str): The keybind for the ability.

    Returns:
        str: The ability corresponding to the agent and keybind.
             If the keybind is "x", it returns the ultimate ability.
             If the agent or keybind is invalid, it returns an error message.
    """
    agents = {
        "Brimstone": {"e": "Smoke", "q": "Incendiary", "c": "Stim Beacon"},
        "Gecko": {"e": "Dizzy", "q": "Wingman", "c": "Mosh Pit"},
        "Harbor": {"e": "High Tide", "q": "Cove", "c": "Cascade"},
        "Fade": {"e": "Haunt", "q": "Seize", "c": "Prowler"},
        "Neon": {"e": "High Gear", "q": "Relay Bolt", "c": "Fast Lane"},
        "Chamber": {"e": "Rendezvous", "q": "Headhunter", "c": "Trademark"},
        "KAY/O": {"e": "Zero/Point", "q": "Flash/Drive", "c": "Frag/Ment"},
        "Astra": {"e": "Nebula", "q": "Nova Pulse", "c": "Gravity Well"},
        "Yoru": {"e": "Gatecrash", "q": "Blindside", "c": "Fakeout"},
        "Skye": {"e": "Guiding Light", "q": "Trailblazer", "c": "Regrowth"},
        "Raze": {"e": "Paint Shells", "q": "Blast Pack", "c": "Boom Bot"},
        "Jett": {"e": "Tailwind", "q": "Updraft", "c": "Cloudburst"},
        "Omen": {"e": "Dark Cover", "q": "Paranoia", "c": "Shrouded Step"},
        "Breach": {"e": "Fault Line", "q": "Flashpoint", "c": "Aftershock"},
        "Killjoy": {"e": "Alarmbot", "q": "Nanoswarm", "c": "Nanoswarm"},
        "Reyna": {"e": "Dismiss", "q": "Devour", "c": "Leer"},
        "Cypher": {"e": "Spycam", "q": "Cyber Cage", "c": "Trapwire"},
        "Viper": {"e": "Toxic Screen", "q": "Poison Cloud", "c": "Snake Bite"},
        "Sova": {"e": "Recon Bolt", "q": "Shock Bolt", "c": "Owl Drone"},
        "Sage": {"e": "Healing Orb", "q": "Slow Orb", "c": "Barrier Orb"},
        "Phoenix": {"e": "Hot Hands", "q": "Curveball", "c": "Blaze"},
        "Iso": {"e": "Double Tap", "q": "Undercut", "c": "Contingency"}
    }

    if agent in agents and keybind in agents[agent]:
        return agents[agent][keybind]
    elif keybind == "x":
        return "Ultimate"
    else:
        return "Invalid keybind or agent"


def prepare(bot: commands.Bot):
    bot.add_cog(Valorant(bot))
