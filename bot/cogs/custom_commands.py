from twitchio.ext import commands
from typing import Optional
import shlex
import re
import aiohttp
import asyncio
import json
import random
from collections import defaultdict

import time

from bot.utilities import ids
from data import data

USER_LEVELS = ["Everyone",
               "Subscriber",
               "VIP",
               "Moderator",
               "Streamer"]

# Constants for token buckets
URLFETCH_RATE_LIMIT = 3  # Number of urlfetches allowed per minute
URLFETCH_TOKEN_REFILL_RATE = 60  # Refill rate in seconds (tokens per second)

# Constants for custom command cooldowns
DEFAULT_COMMAND_COOLDOWN = 5  # Default cooldown in seconds

# Mutex for thread safety
token_bucket_lock = asyncio.Lock()

# Dictionary to store token buckets for each channel
channel_buckets = defaultdict(lambda: {"tokens": 3, "last_refill": None})

# Token bucket dictionary to store token information for each channel
urlfetch_token_buckets = defaultdict(lambda: {"tokens": URLFETCH_RATE_LIMIT, "last_refill": None})


class CustomCommands(commands.Cog):
    """
    A Twitch bot cog for handling custom commands.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the CustomCommands cog.

        Parameters:
            bot (commands.Bot): The Twitch bot instance.
        """
        self.bot = bot

    async def add_command(self, ctx: commands.Context, args: list, channel_id, channel_data):
        """
        Add a new custom command.

        Parameters:
            ctx (commands.Context): The context of the command.
            args (list): The arguments passed with the command.
            channel_id: The ID of the Twitch channel.
            channel_data: The data associated with the Twitch channel.

        Returns:
            None
        """

        # Check if the user is a mod or broadcaster
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        # Assuming channel_data is a dictionary
        channel_data["commands"] = channel_data.get("commands", {})

        if len(args) < 2 or not args[1]:
            await ctx.reply("You must specify a name for the command you want to add.")
            return

        if len(args) < 3 or not args[2]:
            await ctx.reply("You must specify a message for the command to send.")
            return

        command_name = args[1].lower()
        command_message = args[2]

        if command_name in channel_data["commands"]:
            await ctx.reply(
                f"You cannot add a command that already exists, you can edit the command with !cmd edit {command_name}")
            return

        # Add the new command to channel_data["commands"]
        channel_data["commands"][command_name] = {
            'message': command_message,
            'usage_count': 0,
            'user_level': USER_LEVELS[0],
            'cooldown': DEFAULT_COMMAND_COOLDOWN,
            'last_used': 0,
            'aliases': []
        }

        data.update_data(channel_id, channel_data)

        await ctx.reply(f"Command '{command_name}' added with the message: '{command_message}'")

    async def edit_command(self, ctx: commands.Context, args: list, channel_id, channel_data):
        """
        Edit an existing custom command.

        Parameters:
            ctx (commands.Context): The context of the command.
            args (list): The arguments passed with the command.
            channel_id: The ID of the Twitch channel.
            channel_data: The data associated with the Twitch channel.

        Returns:
            None
        """

        # Check if the user is a mod or broadcaster
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        if len(args) < 2 or not args[1]:
            await ctx.reply("You must specify the name of the command you want to edit.")
            return

        command_name = args[1].lower()

        if command_name not in channel_data["commands"]:
            await ctx.reply(f"The command '{command_name}' does not exist.")
            return

        command_data = channel_data["commands"][command_name]

        if len(args) < 3:
            # If no additional arguments provided, show the current command information
            await ctx.reply(
                f"Current information for '{command_name}' | "
                f"Message: {command_data['message']} | "
                f"User Level: {command_data['user_level']} | "
                f"Cooldown: {command_data['cooldown']} seconds | "
                f"Aliases: {', '.join(command_data['aliases'])}"
            )
            return

        # Split the sub-command and its arguments using shlex
        sub_command_args = shlex.split(args[2])

        if not sub_command_args:
            await ctx.reply("Invalid sub-command. Supported sub-commands: message, userlevel, cooldown, aliases.")
            return

        sub_command = sub_command_args[0].lower()

        if sub_command == "message":
            if len(sub_command_args) < 2:
                await ctx.reply(
                    f"You did not specify a new message value. (Current message for '{command_name}': {command_data['message']})")
                return
            new_message = " ".join(map(str, sub_command_args[1:]))
            command_data['message'] = new_message
            await ctx.reply(f"Message for '{command_name}' updated.")

        elif sub_command == "userlevel":
            if len(sub_command_args) < 2:
                await ctx.reply(
                    f"You did not specify a new user level value. (Current user level for '{command_name}': {command_data['user_level']})")
                return
            if not sub_command_args[1] or sub_command_args[1].capitalize() not in USER_LEVELS:
                await ctx.reply(f"Invalid user level. Supported levels: {', '.join(USER_LEVELS)}")
                return
            command_data['user_level'] = sub_command_args[1].capitalize()
            await ctx.reply(f"User level for '{command_name}' updated.")

        elif sub_command == "cooldown":
            if len(sub_command_args) < 2:
                await ctx.reply(
                    f"You did not specify a new cooldown value. (Current cooldown for '{command_name}': {command_data['cooldown']} seconds)")
                return
            if not sub_command_args[1].isdigit():
                await ctx.reply("You must provide a valid cooldown duration in seconds.")
                return
            command_data['cooldown'] = int(sub_command_args[1])
            await ctx.reply(f"Cooldown for '{command_name}' updated.")

        elif sub_command == "aliases":
            if len(sub_command_args) < 2:
                await ctx.reply(
                    f"You did not specify a new aliases value. (Current aliases for '{command_name}': {', '.join(command_data['aliases'])})")
                return
            command_data['aliases'] = [alias.strip() for alias in sub_command_args[1].split(',')]
            await ctx.reply(f"Aliases for '{command_name}' updated.")

        else:
            await ctx.reply("Invalid sub-command. Supported sub-commands: message, userlevel, cooldown, aliases.")

        # Update the channel data
        data.update_data(channel_id, channel_data)

    async def remove_command(self, ctx: commands.Context, args: list, channel_id, channel_data):
        """
        Remove a custom command.

        Parameters:
            ctx (commands.Context): The context of the command.
            args (list): The arguments passed with the command.
            channel_id: The ID of the Twitch channel.
            channel_data: The data associated with the Twitch channel.

        Returns:
            None
        """

        # Check if the user is a mod or broadcaster
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        if len(args) < 2 or not args[1]:
            await ctx.reply("You must specify the name of the command you want to remove.")
            return

        command_name = args[1].lower()

        if command_name not in channel_data["commands"]:
            await ctx.reply(f"The command '{command_name}' does not exist.")
            return

        # Remove the command from channel_data["commands"]
        del channel_data["commands"][command_name]

        # Update the channel data
        data.update_data(channel_id, channel_data)

        await ctx.reply(f"Command '{command_name}' has been removed.")

    async def list_commands(self, ctx: commands.Context, args: list, channel_id, channel_data):
        """
        List all custom commands.

        Parameters:
            ctx (commands.Context): The context of the command.
            args (list): The arguments passed with the command.
            channel_id: The ID of the Twitch channel.
            channel_data: The data associated with the Twitch channel.

        Returns:
            None
        """

        # Check if the user is a mod or broadcaster
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return

        commands_list = channel_data.get("commands", {})

        if not commands_list:
            await ctx.reply("There are no custom commands for this channel.")
            return

        commands_info = ", ".join([f"{cmd}" for cmd, data in commands_list.items()])

        await ctx.reply(f"Custom Commands: {commands_info}")

    @commands.command(aliases=["cmd"])
    async def command(self, ctx: commands.Context, *, arg: Optional[str] = None):
        """
        Handle custom command management.

        Parameters:
            ctx (commands.Context): The context of the command.
            arg (Optional[str]): The arguments passed with the command.

        Returns:
            None
        """

        channel_id = ids.get_id_from_name(ctx.channel.name)
        channel_data = data.get_data(channel_id)

        try:
            if "customcommands" in channel_data["disabled_features"]:
                return
        except (KeyError, ValueError):
            pass

        if arg is None:
            await ctx.reply(
                "You must specify a valid command argument: add, edit, remove, list. Or if you wish to disable this feature use !pref commands.")
            return

        arg = arg.replace(" 󠀀", "")
        args = arg.split(" ", 2)

        command_mapping = {
            "add": self.add_command,
            "edit": self.edit_command,
            "remove": self.remove_command,
            "list": self.list_commands,
        }

        command_name = args[0].lower()
        if command_name in command_mapping:
            await command_mapping[command_name](ctx, args, channel_id, channel_data)
        else:
            await ctx.reply("Invalid command. Supported commands: add, edit, remove, list.")


async def handle_command_message_event(bot, message):
    """
    Event handler for processing command messages.

    Parameters:
        bot: The Twitch bot instance.
        message: The Twitch message.
    """

    # Check if customcommands feature is disabled for the channel
    channel_id = ids.get_id_from_name(message.channel.name)
    channel_data = data.get_data(channel_id)

    try:
        if "customcommands" in channel_data["disabled_features"]:
            return
    except (KeyError, ValueError):
        pass

    channel_data = data.get_data(channel_id)
    channel_data["commands"] = channel_data.get("commands", {})

    # Split the message content into words
    words = message.content.split()

    # Get the base command (the first word in the message)
    base_command = words[0].lower()

    # Check if the base command or any of its aliases are in the available commands
    for command, command_data in channel_data["commands"].items():
        if base_command == command or base_command in command_data.get("aliases", []):
            await process_command(message, channel_id, channel_data, command)
            break


async def process_command(message, channel_id, channel_data, command):
    """
    Process and execute a custom command.

    Parameters:
        bot: The Twitch bot instance.
        message: The Twitch message.
        channel_id: The ID of the Twitch channel.
        channel_data: The data associated with the Twitch channel.
        command (str): The name of the command to execute.

    Returns:
        None
    """
    command_data = channel_data["commands"][command]

    current_time = int(time.time())
    last_used = command_data["last_used"]
    cooldown = command_data["cooldown"]

    if current_time - last_used < cooldown:
        return

    # Check if the user level is sufficient
    user_level_required = USER_LEVELS.index(command_data["user_level"])
    user_level_actual = 0  # Default to "Everyone" user level

    if message.author.is_subscriber:
        user_level_actual = USER_LEVELS.index("Subscriber")
    if message.author.is_vip:
        user_level_actual = USER_LEVELS.index("VIP")
    if message.author.is_mod:
        user_level_actual = USER_LEVELS.index("Moderator")
    if message.author.is_broadcaster:
        user_level_actual = USER_LEVELS.index("Streamer")

    if user_level_actual < user_level_required:
        await message.channel.send(f"You do not have the required user level to use this command.")
        return

    # Incremement usage count
    command_data["usage_count"] = command_data["usage_count"] + 1

    command_message_content = await replace_placeholders(channel_id, message, command_data["message"], command_data)

    await message.channel.send(command_message_content)

    # Update the last used timestamp
    command_data["last_used"] = current_time
    data.update_data(channel_id, channel_data)


async def replace_placeholders(channel_id, message, command_message, command_data):
    """
    Replace placeholders in the message with corresponding data.

    Parameters:
        channel_id (int): The channel's ID.
        message (discord.Message): The Discord message.
        command_message (str): The command message.
        command_data (dict): The data associated with the command.

    Returns:
        str: The message with placeholders replaced.
    """
    # Remove invisible characters from the argument
    message_content = message.content.replace(" 󠀀", "")

    replacements = {
        "{count}": str(command_data["usage_count"]),
        "{touser}": message_content.split(' ', 1)[1].strip() if ' ' in message_content else f"@{message.author.name}",
        "{user}": f"@{message.author.name}",
    }

    # Replace placeholders in the message
    for placeholder, value in replacements.items():
        command_message = command_message.replace(placeholder, value)

    # Handle {urlfetch} placeholder with rate limiting
    urlfetch_pattern = re.compile(r"{urlfetch\s+(.*?)\s*}")
    matches = urlfetch_pattern.finditer(command_message)

    for match in matches:
        url_placeholder = match.group(0)
        url_params = match.group(1).split()  # Split parameters by spaces
        url = url_params[0]

        # Check if the token bucket allows the urlfetch
        async with token_bucket_lock:
            tokens, last_refill = urlfetch_token_buckets[channel_id]["tokens"], urlfetch_token_buckets[channel_id][
                "last_refill"]
            current_time = time.time()

            if last_refill is None or current_time - last_refill > URLFETCH_TOKEN_REFILL_RATE:
                # Refill the tokens if it's a new minute
                urlfetch_token_buckets[channel_id] = {"tokens": URLFETCH_RATE_LIMIT, "last_refill": current_time}
                tokens = URLFETCH_RATE_LIMIT

            if tokens <= 0:
                # Rate limit reached, replace with an error message
                error_message = "Rate limit reached for {urlfetch} placeholders. Please try again later."
                command_message = command_message.replace(url_placeholder, error_message)
                continue

            # Consume a token and proceed with the urlfetch
            urlfetch_token_buckets[channel_id]["tokens"] -= 1

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    fetched_content = await handle_urlfetch_response(response, url_params)
        except Exception as e:
            fetched_content = f"Error fetching content: {str(e)}"

        # Replace the {urlfetch} placeholder with the fetched content
        command_message = command_message.replace(url_placeholder, fetched_content)

    return command_message


async def handle_urlfetch_response(response, url_params):
    """
    Handle the response from a URL fetch.

    Parameters:
        response (aiohttp.ClientResponse): The response from the URL fetch.
        url_params (list): Parameters associated with the URL fetch.

    Returns:
        str: The fetched content.
    """
    # Check if the response is JSON
    if 'json' in url_params:
        try:
            json_data = await response.json()
            fetched_content = await process_json_response(json_data, url_params)
        except json.JSONDecodeError:
            fetched_content = "Error decoding JSON response."
    else:
        fetched_content = await response.text()

    # Handle line parameter
    if 'line' in url_params and len(url_params) > url_params.index('line') + 1:
        line_param = url_params[url_params.index('line') + 1].lower()

        if line_param.isdigit():
            # Get the specified line number
            line_number = int(line_param)
            fetched_content = get_line_from_content(fetched_content, line_number)
        elif line_param == 'random':
            # Get a random line
            fetched_content = get_random_line_from_content(fetched_content)

    return fetched_content


def get_line_from_content(content, line_number):
    """
    Get the specified line number from the content.

    Parameters:
        content (str): The content to extract the line from.
        line_number (int): The line number to retrieve.

    Returns:
        str: The specified line or an error message if the line is not found.
    """
    lines = content.split('\n')
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]
    else:
        return f"Error: Line {line_number} not found in the response."


def get_random_line_from_content(content):
    """
    Get a random line from the content.

    Parameters:
        content (str): The content to extract a random line from.

    Returns:
        str: A random line or an error message if the content is empty.
    """
    lines = content.split('\n')
    if lines:
        return random.choice(lines)
    else:
        return "Error: No lines found in the response."


async def process_json_response(json_data, url_params):
    """
    Process JSON response from a URL fetch.

    Parameters:
        json_data (dict or list): JSON data from the response.
        url_params (list): Parameters associated with the URL fetch.

    Returns:
        str: The processed JSON content.
    """
    # If the parameter "json" is present, use it to extract the specified JSON value
    json_key = url_params[url_params.index('json') + 1] if 'json' in url_params and len(url_params) > url_params.index(
        'json') + 1 else None

    if json_key:
        # Split the nested keys and traverse the JSON structure
        keys = json_key.split('.')
        nested_value = json_data

        try:
            for key in keys:
                if isinstance(nested_value, list):
                    # Handle the case where nested_value is a list
                    index = int(key)
                    nested_value = nested_value[index]
                else:
                    nested_value = nested_value[key]
        except (KeyError, IndexError, TypeError):
            # Handle cases where the key is not found or the structure is not as expected
            fetched_content = f"Key '{json_key}' not found in JSON response."
        else:
            # If the value is a string, remove the quotes
            fetched_content = nested_value if isinstance(nested_value, str) else json.dumps(nested_value, indent=2)
    else:
        fetched_content = json.dumps(json_data, indent=2)

    return fetched_content


def prepare(bot: commands.Bot):
    bot.add_cog(CustomCommands(bot))
