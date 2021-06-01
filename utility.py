#External
import discord
from dateparser.search import search_dates
#Python
from datetime import datetime as dtime
from datetime import timezone
import logging


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
    def date_from_txt(s) -> dtime:
        # needed because replace cannot be called on None
        dates = search_dates(s)
        # NOTE: Temporary as info to search for reason why variable didn't want to work
        logging.info("Input string for date search: %s", s)
        if dates:
            return dates[0][1].replace(tzinfo = timezone.utc)

    @staticmethod
    def text_to_boolean(flag):
        if flag in ['True', 'true']:
            return True
        elif flag in [ 'False', 'false']:
            return False
        return " "

    @classmethod
    def get_vtuber(cls, guild_id) -> str:
        settings_db = cls.db_cluster["settings"]["general"]
        result = settings_db.find_one({}, {'supported_idols' : { '$elemMatch': {'guild_id' : guild_id}}})
        if 'supported_idols' in result:
            return result['supported_idols'][0]['name'].title()
        else:
            logging.warn("Not supported server on getVtuber!")
            return "not supported server"

    @classmethod
    def create_supported_vtuber_embed(cls):
        settings = cls.db_cluster['settings']['general']
        array = settings.find_one({}, {'supported_idols'})['supported_idols']

        # list every vtuber like "- <vtuber>"
        vtuber_list = "- " + '\n- '.join(element['name'].title() for element in array)
        title = "Supported VTuber"

        return discord.Embed(title = title, description = vtuber_list, colour = cls.embed_color)
