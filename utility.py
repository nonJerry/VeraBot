#External
from dateutil.relativedelta import relativedelta
import discord
from dateparser.search import search_dates
#Python
import re
import asyncio
from datetime import datetime as dtime, tzinfo
from datetime import timezone, timedelta
#Internal
from core import Core

data = Core()
bot, db_cluster, embed_color = data.bot, data.db_cluster, data.embed_color


def is_integer(s):
    # check if a string is an integer (includes negative integers)
    try: 
        int(s)
        return True
    except ValueError:
        return False


def date_from_txt(s):
    # needed because replace cannot be called on None
    if search_dates(s):
        return search_dates(s)[0][1].replace(tzinfo = timezone.utc)
        
async def confirm_action(res, actor):

    tick_emote = u"\u2705"
    cross_emote = u"\U0001F6AB"
    await res.add_reaction(tick_emote)
    await res.add_reaction(cross_emote)

    def check(reaction, user):
            reacted_emote = str(reaction.emoji)
            return reaction.message.id == res.id and user == actor and (reacted_emote == tick_emote or reacted_emote == cross_emote)
    m = "The pending action has been cancelled."
    cancel_embed = discord.Embed(title = "Action cancelled", description = m, colour = 0xFF0000)
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout = 60.0, check=check)
    except asyncio.TimeoutError:
        # if overtime, send timeout message and return
        await res.channel.send(content = None, embed = cancel_embed)
        return False

    # if cancelled, send cancellation message and return
    if str(reaction.emoji) == cross_emote:
        await res.channel.send(content = None, embed = cancel_embed)
        return False

    return True

def check_date(date):
    date = date.replace(tzinfo = timezone.utc)
    now = dtime.now().replace(tzinfo = timezone.utc)
    if date < now:
        return False
    if date > now + relativedelta(months=1):
        return False
    return True

def get_vtuber(guild_id):
    settings_db = db_cluster["settings"]["general"]
    result = settings_db.find_one({}, {'supported_idols' : { '$elemMatch': {'guild_id' : guild_id}}})
    if 'supported_idols' in result:
        return result['supported_idols'][0]['name']
    else:
        return "not supported server"

def create_supported_vtuber_embed():
    settings = db_cluster['settings']['general']
    array = settings.find_one({}, {'supported_idols'})['supported_idols']

    # list every vtuber like "- <vtuber>"
    vtuber_list = "- " + '\n- '.join(element['name'] for element in array)
    title = "Supported VTuber"

    return discord.Embed(title = title, description = vtuber_list, colour = embed_color)
