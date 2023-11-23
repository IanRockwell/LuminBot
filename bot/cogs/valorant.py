from datetime import datetime
from typing import Optional

import requests
from twitchio.ext import commands
from twitchio.ext import routines

from bot.utilities import ids
from data import data


class Valorant(commands.Cog):

    # This is the amount of seconds a game will last
    # until it is no longer included in the !record command
    TIME_THRESHOLD = 12 * 60 * 60

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.win_loss_notifications.start()

    @commands.command()
    async def valorantset(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for configuring the linked valorant account.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument containing the region and user.

        Usage:
            !valorantset <region> <user>
        """

        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        if arg == None:
            await ctx.reply(
                "You must specify a valid region and user for this command. (Usage: !valorantset <region> <user>)")
            return

        space_index = arg.find(" ")

        if space_index == -1:
            await ctx.reply(
                f"You must specify a valid region and user for this command. (Usage: !valorantset <region> <user>)")
            return

        region = arg[:space_index]
        user = arg[space_index + 1:]

        regions = ["eu", "ap", "na", "kr", "latam", "br"]

        if region.lower() not in regions:
            await ctx.reply(
                "You did not specify a valid region (EU, AP, NA, KR, Latam, BR): !valorantset <region> <name>")
            return

        if "#" not in user:
            await ctx.reply(
                f"You must specify a valid user type (Example: User#3183): !valorantset <region> <name>")
            return

        if len(user) > 25:
            await ctx.reply("The user you have provided appears to be too long, are you sure it's correct?")
            return

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        if "valorant" not in channel_data:
            channel_data["valorant"] = {}

        channel_data["valorant"]["account_user"] = user
        channel_data["valorant"]["account_region"] = region

        data.update_data(document_id=channel_id, new_data=channel_data)

        await ctx.reply(f"Successfully linked {ctx.channel.name} with: {user}: {region}")
        print(f"[valorant] {ctx.author.name} has linked {ctx.channel.name} with: {user}: {region}")

    @commands.command()
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
    async def record(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing the streamer"s win/loss this stream.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument (unused).

        Usage:
            !record
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

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

        await ctx.reply(f"{name} is currently {difference_tag} {difference}RR with {win} wins and {loss} losses in the last 12 hours")

    @commands.command()
    async def radiant(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Command for viewing the current radiant threshold.

        Parameters:
            ctx (commands.Context): The command context.
            arg (Optional[str]): The argument (unused).

        Usage:
            !radiant
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        if not channel_data:
            return

        try:
            region = channel_data["valorant"]["account_region"]
        except (KeyError, ValueError):
            return

        await ctx.reply(f"{await get_radiant_rr(region)}RR is the current radiant threshold.")

    @routines.routine(seconds=5)
    async def win_loss_notifications(self):
        """
        Routine for checking win/loss notifications in connected channels.
        """
        connected_channels = self.bot.connected_channels

        if not connected_channels:
            return

        user_logins = [channel.name for channel in connected_channels]

        streams = await self.bot.fetch_streams(user_logins=user_logins, type="live")

        for stream in streams:

            if stream.game_name != "VALORANT":
                continue

            channel_id = ids.get_id_from_name(stream.user.name)
            channel_data = data.get_data(channel_id)

            if not channel_data:
                continue

            try:
                name, discriminator = channel_data["valorant"]["account_user"].split("#")
                region = channel_data["valorant"]["account_region"]
            except (KeyError, ValueError):
                continue

            career = await get_career(region=region, name=name, discriminator=discriminator)

            if career.status_code != 200:
                continue

            career_json = career.json()

            latest_match_id = career_json["data"][0]["match_id"]
            try:
                latest_remembered_match_id = channel_data["valorant"]["latest_match_id"]
            except (KeyError, ValueError):
                latest_remembered_match_id = None

            print(f"[valorant] comparing match ids {latest_match_id} - {latest_remembered_match_id}")
            if latest_match_id == latest_remembered_match_id:
                continue

            channel_data["valorant"]["latest_match_id"] = latest_match_id
            data.update_data(document_id=channel_id, new_data=channel_data)

            match = await get_match(latest_match_id)
            match_json = match.json()

            all_players = match_json["data"]["players"]["all_players"]
            user_data = [player for player in all_players if
                         player["name"].lower() == name.lower() and player["tag"].lower() == discriminator.lower()]

            red_team_rounds_won, blue_team_rounds_won = (match_json['data']['teams'][team]['rounds_won'] for team in
                                                         ['red', 'blue'])
            score = f"{max(red_team_rounds_won, blue_team_rounds_won)}-{min(red_team_rounds_won, blue_team_rounds_won)}"

            map = match_json["data"]["metadata"]["map"]

            rr_difference = career_json['data'][0]['mmr_change_to_last_game']

            agent = user_data[0]['character']

            ability_casts = user_data[0]['ability_casts']
            c_casts, q_casts, e_casts, x_casts = [ability_casts[ability] for ability in
                                                  ['c_cast', 'q_cast', 'e_cast', 'x_cast']]
            c_cast_name, q_cast_name, e_cast_name, x_cast_name = [get_ability(agent, ability) for ability in
                                                                  ['c', 'q', 'e', 'x']]

            stats = user_data[0]['stats']
            kills, deaths, assists = stats['kills'], stats['deaths'], stats['assists']
            headshots, bodyshots, legshots = stats['headshots'], stats['bodyshots'], stats['legshots']
            headshot_percentage = round((headshots / (headshots + bodyshots + legshots) * 100))

            if rr_difference <= 0:
                message_header = f"😭{stream.user.name} lost {rr_difference}RR on {map} | "
                message_footer = "😭"
            else:
                message_header = f"PartyHat {stream.user.name} gained {rr_difference}RR on {map} | "
                message_footer = "PartyHat"

            message_body = f"Score: {score} | KDA: {kills}/{deaths}/{assists} | Agent: {agent} | Abilties: {e_cast_name} {e_casts} times, {q_cast_name} {q_casts} times, {c_cast_name} {c_casts} times, {x_cast_name} {x_casts} times | Headshot: {headshot_percentage}% | Tracker: https://tracker.gg/valorant/match/%{latest_match_id} "

            await self.bot.get_channel(stream.user.name).send(message_header + message_body + message_footer)

async def get_rank(channel_name):
    """
    Retrieves and formats the Valorant rank information for a Twitch streamer.

    Args:
        channel_name (str): Twitch channel name of the streamer.

    Returns:
        str or None: Formatted Valorant rank details or None if data is unavailable.

    This function is used in the global_rank cog's !rank command to fetch and present
    the Valorant rank of a streamer. It extracts account details (name, discriminator,
    region) from stored data, queries the Kyroskoh API for rank information,
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

    rank_split = rank_data_request.text.split()

    rank = rank_split[0]

    if rank == "Immortal":
        tier = int(rank_split[1])
        rr = int(rank_split[3][:-3])
        radiant_rr = await get_radiant_rr(region=region)

        rr_from_radiant = radiant_rr - rr

        result = f"{rank} {tier} - {rr}RR ({rr_from_radiant}RR from Radiant)"

    elif rank == "Radiant":
        rr = int(rank_split[2][:-3])
        result = f"{rank} - {rr}RR"

    else:
        tier = int(rank_split[1])
        rr = int(rank_split[3][:-3])
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

    url = f"https://api.kyroskoh.xyz/valorant/v1/mmr/{region}/{name}/{discriminator}?show=combo&display=0"

    try:
        response = requests.get(url)
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
        response = requests.get(url)
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
        response = requests.get(url)
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
        response = requests.get(url)
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