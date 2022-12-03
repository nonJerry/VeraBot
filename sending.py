#External
import discord
# Python
import logging
#Internal
from utility import Utility
from translate import Translate

# Setup i18n
_ = Translate.get_translation_function('sending')

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
            return
        target_user = cls.bot.get_user(int(member_id))
        try:
            if embed:
                # split message into title and description
                embed = discord.Embed(title = title, description = message, colour = cls.embed_color)

                if attachment_url:
                    embed.set_image(url = attachment_url)
                await target_user.send(content = None, embed = embed)
            else:
                await target_user.send(message)
            logging.debug(_("Sent DM to %s"), member_id)
        except AttributeError:
            logging.info(_("User {} does not exist.").format(member_id))
        except Exception:
            logging.info(_("Something went wrong with user {} a DM").format(member_id))