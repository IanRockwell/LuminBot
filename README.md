<div align="center">

# Lumin - Chat interaction enhancer

Lumin is a Twitch bot that allows for chat integration for a variety of games.

[Join the discord](https://discord.gg/UzUaUkpC6g)

</div>

# Register👋

### [To register simply type !register in the bot's chat!](https://www.twitch.tv/LuminBotTV)

# Supported Games 🎮

Lumin currently supports chat integration for the following games:

- Valorant - *Special thanks to [Henrik](https://github.com/Henrik-3) for the [ValorantAPI](https://github.com/Henrik-3/unofficial-valorant-api)*
- osu! - *Special thanks to [Tillerino](https://github.com/Tillerino) for the [ppAddictAPI](https://tillerino.github.io/Tillerinobot/swagger/)* & thanks to [osu!snipe](https://discord.gg/U3fZVX2B) for the [huismetbenenAPI](https://pp.huismetbenen.nl/)

with many more being planned.

# Additional Features 📙

In addition to game integration, Lumin offers a range of non-game related features to enhance your Twitch channel:

- Watchstreaks
- Firsts

Feel free to explore these features and customize Lumin to create an engaging and interactive experience for your Twitch community!

## Setup 📦

### Requirements

- Python 3.10+

Library requirements can be installed with:

```
pip install -r requirements.txt
```

### Environment Variables

Make sure you have added and configured your `.env` file

```
# Twitch Authorization
TWITCH_NICK=LuminBotTV

TWITCH_TOKEN=
TWITCH_CLIENTID=
TWITCH_CLIENTSECRET=

# Osu Authorization
# Can be left blank if not needed, but osu.py will stop functioning
PP_ADDICT_APIKEY=
OSU_V1_APIKEY=

# Do you want people to be able to add your bot to their channel with !register
BOT_PUBLIC=true
```

### Run!

The bot can then be run with the command:
```
python main.py
```

## Contributing 🚀

We welcome contributions to enhance Lumin and make it even more powerful! To contribute, follow these steps:

1. Clone the repository:

```
git clone https://github.com/IanRockwell/LuminBot.git
```

2. Make your changes in the local repository.

3. Add, commit, and push your changes:

```
git add .
git commit -m "Description of your changes"
git push
```

4. Create a pull request on the [Lumin GitHub repository](https://github.com/IanRockwell/LuminBot/pulls) to submit your changes.

Thank you for your contribution! 🎉
