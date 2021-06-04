#External
import discord
from dateparser.search import search_dates
#Python
from datetime import datetime as dtime
from datetime import timezone
from dateutil.relativedelta import relativedelta
import logging
from typing import Optional, Tuple


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
    def date_from_txt(s: str, lang="eng") -> Optional[dtime]:
        # needed because replace cannot be called on None
        usual_date = dtime.now() + relativedelta(months=1)

        s = Utility.cut_to_date(s, lang)
        logging.info("Input string for date search: %s", s)

        # use date in 1 month from now as reference
        dates = search_dates(s, settings={'RELATIVE_BASE': usual_date})
        if dates:
            return dates[0][1].replace(tzinfo = timezone.utc)

    @staticmethod
    def cut_to_date(s: str, lang: str) -> str:
        # on membership page in several languages
        BILLING_DATE = "billing date"
        BILLED_WITH = "billed with"
        ACCESS_ENDS = "expired"
        GREETING = "greeting"
        searches = {
            "l1": {BILLING_DATE: 'billing date', BILLED_WITH: 'Billed with', ACCESS_ENDS: 'Access to', GREETING: 'Hello'},
            "jpn": {BILLING_DATE: '請求日', BILLED_WITH: 'お支払', ACCESS_ENDS: '終了日', GREETING: '様'},
            "chi_sim": {BILLING_DATE: '算日期', BILLED_WITH: '结算', ACCESS_ENDS: '止日期', GREETING: '尊敬的'},
            "rus": {BILLING_DATE: 'платежа', BILLED_WITH: 'Оплата', ACCESS_ENDS: 'доступны до', GREETING: 'Здравству'},
            "l2": {BILLING_DATE: 'data de', BILLED_WITH: 'Faturado com', ACCESS_ENDS: 'termina a', GREETING: 'Ola'}, #portugese
            "l3": {BILLING_DATE: 'Abrechnungsdatum', BILLED_WITH: 'Abgerechnet tiber', ACCESS_ENDS: 'endet am', GREETING: 'Hallo'}, # german: ocr in en setting cannot parse "ueber"
            "l4": {BILLING_DATE: 'seterusnya', BILLED_WITH: 'Dibilkan dengan', ACCESS_ENDS: 'Akses', GREETING: 'Helo'},
            "l5": {BILLING_DATE: 'berikutnya', BILLED_WITH: 'Ditagih dengan', ACCESS_ENDS: 'Akses', GREETING: 'Halo'},
            "l6": {BILLING_DATE: 'fecha de', BILLED_WITH: 'Facturado con', ACCESS_ENDS: 'acceso', GREETING: 'Hola'},
            "l7": {BILLING_DATE: 'petsa ng pagsingil', BILLED_WITH: 'Sinisingil sa', ACCESS_ENDS: 'mga perk sa', GREETING: 'Kumusta'},
            "l8": {BILLING_DATE: 'nastepnego rozliczenia', BILLED_WITH: 'Ptatnosci kartq', ACCESS_ENDS: 'koniczy sie', GREETING: 'Czesé'},
            "l9": {BILLING_DATE: 'REBRA', BILLED_WITH: 'BTS', ACCESS_ENDS: ' BRAOVIVAZDKRT A', GREETING: '#&'} # japanese if used with eng ocr
            }
            
        # check for direct pattern
        if lang in searches:
            s, success = Utility._cut_to_date(s, searches[lang])
            if success:
                return s

        # if there is no hit, check every pattern
        for hooks in searches.values():
            s, success = Utility._cut_to_date(s, hooks)
            if success:
                return s
        # return full string if not successful
        return s
    
    @staticmethod
    def _cut_to_date(s: str, hooks) -> Tuple[str, bool]:
        date_index = s.find(hooks["billing date"])
        if date_index != -1:
            start_index = date_index + len(hooks["billing date"])
            s = s[start_index:] # starting after date text
            billed_index = s.find(hooks["billed with"])
            if billed_index != -1:
                s = s[:billed_index] # ending at billing with text
            return s, True
        else:
            date_index = s.find(hooks["expired"])
            if date_index != -1:
                start_index = date_index + len(hooks["expired"])
                s = s[start_index:] # starting after date text
                billed_index = s.find(hooks["greeting"])
                if billed_index != -1:
                    s = s[:billed_index]
                return s, True
        return s, False


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
