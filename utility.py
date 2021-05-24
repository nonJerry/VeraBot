#External
import discord
from dateparser.search import search_dates
#Python
import asyncio
from datetime import datetime as dtime
from datetime import timezone


class Utility:

    bot = None
    db_cluster = None
    embed_color = None

    @classmethod
    def setup(cls, bot, db_cluster, embed_color):
        cls.bot = bot
        cls.db_cluster = db_cluster
        cls.embed_color = embed_color

    @staticmethod
    def is_integer(s):
        # check if a string is an integer (includes negative integers)
        try: 
            int(s)
            return True
        except ValueError:
            return False

    @staticmethod
    def date_from_txt(s):
        # needed because replace cannot be called on None
        if search_dates(s):
            return search_dates(s)[0][1].replace(tzinfo = timezone.utc)

    @staticmethod
    def text_to_boolean(flag):
        if flag in ['True', 'true']:
            return True
        elif flag in [ 'False', 'false']:
            return False
            
    @classmethod
    async def confirm_action(cls, res, actor):

        tick_emote = u"\u2705"
        cross_emote = u"\U0001F6AB"
        await res.add_reaction(tick_emote)
        await res.add_reaction(cross_emote)

        def check(reaction, user):
                reacted_emote = str(reaction.emoji)
                return reaction.message.id == res.id and user == actor and (reacted_emote == tick_emote or reacted_emote == cross_emote)
        try:
            reaction, user = await cls.bot.wait_for('reaction_add', timeout = 60.0, check=check)
        except asyncio.TimeoutError:
            # if overtime, send timeout message and return
            return False

        # if cancelled, send cancellation message and return
        if str(reaction.emoji) == cross_emote:
            return False

        return True

    @classmethod
    def get_vtuber(cls, guild_id):
        settings_db = cls.db_cluster["settings"]["general"]
        result = settings_db.find_one({}, {'supported_idols' : { '$elemMatch': {'guild_id' : guild_id}}})
        if 'supported_idols' in result:
            return result['supported_idols'][0]['name']
        else:
            return "not supported server"

    @classmethod
    def create_supported_vtuber_embed(cls):
        settings = cls.db_cluster['settings']['general']
        array = settings.find_one({}, {'supported_idols'})['supported_idols']

        # list every vtuber like "- <vtuber>"
        vtuber_list = "- " + '\n- '.join(element['name'] for element in array)
        title = "Supported VTuber"

        return discord.Embed(title = title, description = vtuber_list, colour = cls.embed_color)
