from bot import bot

import os
from dotenv import load_dotenv

load_dotenv()

TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_CLIENTID = os.getenv("TWITCH_CLIENTID")
TWITCH_CLIENTSECRET = os.getenv("TWITCH_CLIENTSECRET")
TWITCH_NICK = os.getenv("TWITCH_NICK")

if __name__ == "__main__":
    print("Initialising Twitch Bot...")

    bot = bot.LuminBot(
        nick=TWITCH_NICK,
        token=TWITCH_TOKEN,
        client_id=TWITCH_CLIENTID,
        client_secret=TWITCH_CLIENTSECRET
    )

    bot.run()
