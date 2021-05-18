# Singleton

import os
from decouple import config
import discord

class Core(object):
    class __Core:
        def __init__(self):
            self.bot = None
            self.owner = None
            self.dev = None
            self.embed_color = None
            self.tess = None
            self.dm_log = None
            self.db_cluster = None
            self.local = None
    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not Core.instance:
            Core.instance = Core.__Core()
        return Core.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, value):
        return setattr(self.instance, name, value)


def create_core(local):

    #External
    import discord
    from discord.ext import commands
    import pytesseract as Tess
    from pymongo import MongoClient

# Customizable Settings
# For local testing
    if(local):
        token = config("TOKEN")
        owner = config("OWNER")
        owner_id = int(config("OWNER_ID"))
        dev = config("DEV")
        embed_color = int(config("EMBED_COLOR"), 16)
        # Setting up the ocr
        Tess.pytesseract.tesseract_cmd = config('TESS_PATH')
        db_user = config("DB_USER")
        db_pass = config("DB_PASS")
        db_url = config("DB_LINK")
        dm_log = int(config("DM_LOG"))
    # For server
    else:
        token = os.getenv("TOKEN")
        owner = os.getenv("OWNER")
        owner_id = int(os.getenv("OWNER_ID"))
        dev = os.getenv("DEV")
        embed_color = int(os.getenv("EMBED_COLOR"), 16)
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_url = os.getenv("DB_LINK")
        dm_log = int(os.getenv("DM_LOG"))

    # Intents
    intents = discord.Intents.all()
    intents.invites = False
    intents.emojis = False
    intents.typing = False
    intents.presences = False
    intents.integrations = False
    intents.webhooks = False
    intents.voice_states = False
    intents.guild_typing = False

    # Set up bot
    bot = commands.Bot(command_prefix=determine_prefix, description='Bot to verify and manage Memberships.\nlogChannel, Vtuber name and memberRole need to be set!', intents=intents, case_insensitive=True, owner_id=owner_id)


    # database settings
    cluster = MongoClient(db_url.format(db_user, db_pass))

    # Initializing Core data so that every module can access it
    data = Core()
    data.bot = bot
    data.local = local
    data.owner = owner
    data.dev = dev
    data.embed_color = embed_color
    data.tess = Tess
    data.dm_log = dm_log
    data.db_cluster = cluster
    return token, data

async def determine_prefix(bot, message):
    db_cluster = Core().db_cluster
    if isinstance(message.channel, discord.channel.DMChannel):
        return "$" #no prefix needed
    guild = message.guild
    if guild:
        prefixes = db_cluster[str(guild.id)]["settings"].find_one({"kind": "prefixes"})["values"]
        if prefixes:
            return prefixes
    return "$"


