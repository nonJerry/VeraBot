#External
import discord
#Internal
from utility import Utility

class Sending:

    bot = None
    embed_color = None

    @classmethod
    def setup(cls, bot, embed_color):
        cls.bot = bot
        cls.embed_color = embed_color

    @classmethod
    async def dm_member(cls, member_id, title, message, embed = False, attachment_url = None):
        # dm a member, and returns a message if error occurs

        # if member_id is not integer or a string that represents integer, return error message
        if not Utility.is_integer(member_id):
            return "Please provide a valid user id!"
        target_user = cls.bot.get_user(int(member_id))

        if embed:
            # split message into title and description
            embed = discord.Embed(title = title, description = message, colour = cls.embed_color)

            if attachment_url:
                embed.set_image(url = attachment_url)
            await target_user.send(content = None, embed = embed)
        else:
            await target_user.send(message)