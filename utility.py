#External
import discord
from dateparser.search import search_dates
#Python
from datetime import datetime as dtime
from datetime import timezone
from dateutil.relativedelta import relativedelta
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
        usual_date = dtime.now() + relativedelta(months=1)
        date_index = s.find("billing date")
        if date_index != -1:
            s = s[date_index:] # starting at date text
        billed_index = s.find("Billed with")
        if billed_index != -1:
            s = s[:billed_index] # ending at billing with text

        dates = search_dates(s, settings={'RELATIVE_BASE': usual_date})
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
