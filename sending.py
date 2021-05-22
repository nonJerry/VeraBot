#External
import discord
#Internal
import utility
from core import Core
from utility import is_integer

data = Core()
bot, embed_color, dev = data.bot, data.embed_color, data.dev


async def dm_member(member_id, title, message, embed = False, attachment_url = None):
    # dm a member, and returns a message if error occurs

    # if member_id is not integer or a string that represents integer, return error message
    if not utility.is_integer(member_id):
        return "Please provide a valid user id!"
    target_user = bot.get_user(int(member_id))

    if embed:
        # split message into title and description
        embed = discord.Embed(title = title, description = message, colour = embed_color)

        if attachment_url:
            embed.set_image(url = attachment_url)
        await target_user.send(content = None, embed = embed)
    else:
        await target_user.send(message)