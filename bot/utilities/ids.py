import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

TWITCH_CLIENTID = os.getenv("TWITCH_CLIENTID")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")

def get_name_from_id(user_id):
    """
    Get the Twitch broadcaster name associated with the provided user ID.

    Parameters:
    - user_id (str): The user ID of the Twitch broadcaster.

    Returns:
    - str: The broadcaster name.
    """
    headers = {
        'Client-Id': str(TWITCH_CLIENTID),
        'Authorization': str(f'Bearer {TWITCH_TOKEN}')
    }

    url = f'https://api.twitch.tv/helix/channels?broadcaster_id={user_id}'

    response = requests.get(url, headers=headers)

    json_response = json.loads(response.text)
    broadcaster_name = json_response['data'][0]['broadcaster_name']

    return broadcaster_name


def get_id_from_name(name):
    """
    Get the Twitch user ID associated with the provided broadcaster name.

    Parameters:
    - name (str): The broadcaster name on Twitch.

    Returns:
    - str: The user ID.
    """
    headers = {
        'Client-Id': str(TWITCH_CLIENTID),
        'Authorization': str(f'Bearer {TWITCH_TOKEN}')
    }

    url = f'https://api.twitch.tv/helix/users?login={name}'

    response = requests.get(url, headers=headers)

    json_response = json.loads(response.text)
    broadcaster_id = json_response['data'][0]['id']

    return broadcaster_id