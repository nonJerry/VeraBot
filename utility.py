#External
from random import paretovariate
import discord
from dateparser.search import search_dates
#Python
from datetime import datetime as dtime
from datetime import timezone
from dateutil.relativedelta import relativedelta
import logging
from typing import Optional, Tuple, Union
from database import Database



class Utility:

    bot = None
    db = None
    embed_color = None

    @classmethod
    def setup(cls, bot, embed_color) -> None:
        cls.bot = bot
        cls.db = Database()
        cls.embed_color = embed_color

    @staticmethod
    def is_integer(s) -> bool:
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

    @classmethod
    def map_vtuber_to_server(cls, name) -> Optional[int]:
        return cls.db.get_vtuber_guild(name)

    @staticmethod
    def map_language(lang: str) -> str:
        supported = {
            "eng": ["en", "eng", "english"],
            "jpn": ["jp", "jap", "jpn", "japanese"],
            "chi_sim": ["zh", "chi", "chinese"],
            "rus": ["ru", "rus", "russian"]
        }
        for aliases in supported.items():
            if lang.lower() in aliases[1]:
                return aliases[0]
        return "eng"
    

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
            "l9": {BILLING_DATE: 'REBRA', BILLED_WITH: 'BTS', ACCESS_ENDS: 'AZDKRT A', GREETING: '#&'} # japanese if used with eng ocr
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
            start_index = date_index + len(hooks["billing date"]) - 1
            s = s[start_index:] # starting after date text
            billed_index = s.find(hooks["billed with"])
            if billed_index != -1:
                s = s[:billed_index] # ending at billing with text
            return s, True
        else:
            date_index = s.find(hooks["expired"])
            if date_index != -1:
                start_index = date_index + len(hooks["expired"]) - 1
                s = s[start_index:] # starting after date text
                billed_index = s.find(hooks["greeting"])
                if billed_index != -1:
                    s = s[:billed_index]
                return s, True
        return s, False


    @staticmethod
    def text_to_boolean(flag) -> Union[bool, str]:
        if flag in ['True', 'true']:
            return True
        elif flag in [ 'False', 'false']:
            return False
        return " "

    @classmethod
    def get_vtuber(cls, guild_id) -> str:
        return cls.db.get_vtuber(guild_id)

    @classmethod
    def create_supported_vtuber_embed(cls) -> discord.Embed:
        array = cls.db.get_vtuber_list()

        # list every vtuber like "- <vtuber>"
        vtuber_list = "- " + '\n- '.join(element['name'].title() for element in array)
        title = "Supported VTuber"

        return discord.Embed(title = title, description = vtuber_list, colour = cls.embed_color)

    @classmethod
    def is_user_on_server(cls, user: int, server: int) -> bool:
        guild = cls.bot.get_guild(server)
        member = guild.get_member(user)
        if member:
            return True
        return False

    @classmethod
    def is_multi_server(cls, guild_id: int) -> bool:
        if not guild_id in cls.db.get_multi_server():
            return False
        return True

    @classmethod
    def is_interaction_not_dm(cls, interaction: discord.Interaction) -> bool:
        if isinstance(interaction.channel, discord.PartialMessageable):
            # reaching here means it's a DM
            return False
        return True
