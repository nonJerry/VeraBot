#External
from database import Database
import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandNotFound
from pymongo import MongoClient
#Python
import asyncio
from datetime import datetime as dtime
from datetime import timezone, timedelta
import os
import logging
#Internal
from membership_handling import MembershipHandler
from settings import Settings
from membership import Membership
from utility import Utility
from ocr import OCR
from sending import Sending



logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logging.info("Started")

### Setup data
# Set variable to true for local testing
local = False


# Customizable Settings
# For local testing

token = os.getenv("TOKEN")
owner_id = int(os.getenv("OWNER_ID"))
embed_color = int(os.getenv("EMBED_COLOR"), 16)
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_url = os.getenv("DB_LINK")
dm_log = int(os.getenv("DM_LOG"))
stage = os.getenv("STAGE")

# Intents
intents = discord.Intents.default()
intents.members = True
intents.invites = False
intents.emojis = False
intents.typing = False
intents.integrations = False
intents.webhooks = False
intents.voice_states = False
intents.guild_typing = False

async def determine_prefix(bot, message):
    if isinstance(message.channel, discord.channel.DMChannel):
        return "$"
    guild = message.guild
    if guild:
        try:
            prefixes = database.get_server_db(guild.id).get_prefixes()
        except TypeError:
            return "$"
        if prefixes:
            return prefixes
    return "$"

# Set up bot
bot = commands.Bot(command_prefix=determine_prefix, description='Bot to verify and manage Memberships.\nlogChannel, Vtuber name and memberRole need to be set!', intents=intents, case_insensitive=True, owner_id=owner_id)

# 2 tries per 50s as default
verify_tries = 2

# listen to other bots while testing
if stage == "TEST":
    """
    Patches the target bot. It changes the ``process_commands`` function to remove the check if the received message
    author is a bot or not.
    :param discord.ext.commands.Bot bot:
    :return: The patched bot.
    """
    from discord.ext.commands.bot import Bot
    async def process_commands(self, message):
        ctx = await self.get_context(message)
        await self.invoke(ctx)
    if type(bot) == Bot:
        bot.process_commands = process_commands.__get__(bot, Bot)

    # to not run into cooldown limit
    verify_tries = 1000
    logging.info("Listining to bots too. Only for testing purposes!!!")


# database settings
db_cluster = MongoClient(db_url.format(db_user, db_pass))


# set up classes
database = Database(db_cluster)
member_handler = MembershipHandler(bot, embed_color)
Utility.setup(bot, embed_color)
OCR.setup(bot, local)
Sending.setup(bot, embed_color)

#add cogs
bot.add_cog(Settings(bot))
bot.add_cog(Membership(bot, member_handler))
logging.info("Cogs added")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        # Ignore this error
        pass
    elif isinstance(error, commands.MissingPermissions):
        logging.info("%s tried to invoke %s without the needed permissions!", ctx.author.id, ctx.command)
        await ctx.send("You are not allowed to use this command!")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command should not be used in the DMs")
    elif hasattr(ctx.command, 'on_error'):
        #skip already locally handled errors
        pass
    else:
        raise error
    
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.event
async def on_guild_join(guild):
    """
    Creates the database and settings collection when the bot joins a server.
    """
    logging.info("Joined new Guild: %s (%s)", guild.name , guild.id)

    database.create_new_server(guild.id)

    logging.info("Created database for %s", guild.id)


@bot.event
async def on_guild_remove(guild):
    """
    Removes the guild from the supported idols so that memberships are not checked.
    """
    logging.info("Left Guild: %s (%s)", guild.name , guild.id)
    database.remove_vtuber(guild.id)

@bot.event
async def on_raw_reaction_add(payload):
    
    if not payload.guild_id:
        return

    # ignore if not one of the wanted emotes
    if str(payload.emoji) not in ('✅', u"\U0001F4C5", u"\U0001F6AB"):
        return

    channel = bot.get_channel(payload.channel_id)
    permissions = channel.permissions_for(channel.guild.me)
    
    # abort if not able to read messages in the channel of reaction
    if not permissions.read_message_history:
        return

    # get reaction from payload
    try:
        msg = await channel.fetch_message(payload.message_id)
        reaction = discord.utils.get(msg.reactions, emoji=payload.emoji.name)

        # only the first react by somebody else than the bot should be processed
        if reaction:
            if reaction.count != 2:
                return
            msg = reaction.message

            # Only process reactions that also were also made by the bot
            if not reaction.me:
                return
            if msg.embeds:
                user = bot.get_user(payload.user_id)
                await process_reaction(channel, msg, reaction, user)
                    
    except discord.errors.Forbidden:
        logging.info("%s: forbidden on reaction in %s", payload.guild_id, channel.id)
        return
    except discord.errors.NotFound:
        logging.info("%s: message not found on reaction in %s", payload.guild_id, channel.id)
        return
    except discord.errors.DiscordServerError:
        logging.info("%s: Discord Server has some problems", payload.guild_id)


async def process_reaction(channel, msg, reaction, user):
    emoji = reaction.emoji
    embed = msg.embeds[0]
    server_db = database.get_server_db(msg.guild.id)
    threads_enabled = server_db.get_threads_enabled()
    success = False

    # always only the id
    target_member_id = int(embed.title)

    # correct date
    if emoji == '✅':
        logging.info("Recognized date correct in %s for user %s.", channel.guild.id, target_member_id)
        
        if server_db.get_automatic():
            await msg.clear_reactions()
            await asyncio.sleep(0.21)
            await msg.add_reaction(emoji='👌')
        else:
            membership_date = embed.fields[0].value

            # set membership
            if await member_handler.set_membership(msg, target_member_id, membership_date, False, user):
                await asyncio.sleep(0.21)
                await msg.clear_reactions()
                await asyncio.sleep(0.21)
                await msg.add_reaction(emoji='👌')
        success = True

    # wrong date
    elif emoji == u"\U0001F4C5":
        logging.info("Wrong date recognized in %s for user %s.", channel.guild.id, target_member_id)

        success = await handle_wrong_date(channel, msg, reaction, target_member_id, user)

    # deny option - fake / missing date
    elif emoji == u"\U0001F6AB":
        logging.info("Fake or without date in %s for user %s.", channel.guild.id, target_member_id)
        success = await handle_denied(channel, msg, reaction, embed, target_member_id, user)

    if success and threads_enabled:
        log_channel = bot.get_channel(server_db.get_log_channel())
        embed.clear_fields()
        embed.set_image(url = discord.Embed.Empty)
        await log_channel.send(content=None, embed = embed)
        await channel.edit(archived=True)

async def handle_wrong_date(channel, msg, reaction, target_member_id: int, user) -> bool:
    """Process if the date was recognized wrongly
    
    Parameters
    ----------
    channel:
        The channel of the proof message
    msg:
        The proof message
    reaction:
        The reaction that was added
    target_member_id: int
        The id of the member whose proof is being processed

    Returns
    -------
    bool
        Whether the process was ended successfully (no abort)
    """

    m = "Please write the correct date from the screenshot in the format dd/mm/yyyy.\n"
    m += "Type CANCEL to stop the process."
    await channel.send(m, reference=msg, mention_author=False)

    def check(m):
        return m.author == user and m.channel == channel

    date_msg = await bot.wait_for('message', check=check)

    if date_msg.content.lower() != "cancel" and await member_handler.set_membership(msg, target_member_id, date_msg.content, False, user):
        await msg.clear_reactions()
        await asyncio.sleep(0.21)
        await msg.add_reaction(emoji='👍')
        return True
    else:
        logging.info("Canceled reaction by user %s in %s.", user.id, channel.guild.id)
        await reaction.remove(user)
        await asyncio.sleep(0.21)
        await channel.send("Stopped the process and removed reaction.")
        return False



async def handle_denied(channel, msg, reaction, embed, target_member_id: int, user) -> bool:
    """Process if the proof is denied
    
    Parameters
    ----------
    channel:
        The channel of the proof message
    msg:
        The proof message
    reaction:
        The reaction that was added
    embed:
        The edited embed
    target_member_id: int
        The id of the member whose proof is being processed

    Returns
    -------
    bool
        Whether the process was ended successfully (no abort)
    """

    m = "Please write a message that will be sent to the User."
    m += "Type CANCEL to stop the process."
    await channel.send(m, reference=msg, mention_author=False)

    def check(m):
        return m.author == user and m.channel == channel

    text_msg = await bot.wait_for('message', check=check)
    if text_msg.content.lower() != "cancel":
        target_member = bot.get_user(target_member_id)
        await target_member.send("{} server:\n{}".format(Utility.get_vtuber(msg.guild.id), text_msg.content))
        await channel.send("Message was sent to {}.".format(target_member.mention), reference=text_msg, mention_author=False)

        if database.get_server_db(msg.guild.id).get_automatic():
            await member_handler.del_membership(msg, target_member_id, None, False, False)
            # set embed
        embed.description = "**DENIED**\nUser: {}\nBy: {}".format(target_member.mention, user)
        await msg.edit(content = msg.content, embed = embed)
        await asyncio.sleep(0.21)
        await msg.clear_reactions()
        await msg.add_reaction(emoji='👎')
        return True
    else:
        logging.info("Canceled reaction by user %s in %s.", user.id, channel.guild.id)
        await reaction.remove(user)
        await channel.send("Stopped the process and removed reaction.")
        return False


def dm_or_test_only():
    def predicate(ctx):
        return isinstance(ctx.channel, discord.DMChannel) or stage == "TEST"
    return commands.check(predicate)

@bot.command(
    help="Can be called with just $verify but also with $verify <VTuber name>\n" +
    "Both versions require a screenshot sent with it.",
	brief=" Tries to verify a screenshot for membership in the DMs"
)
@dm_or_test_only()
@commands.cooldown(verify_tries, 50, commands.BucketType.user)
async def verify(ctx, *args):
    """
    Command in the DMs that tries to verify a screenshot for membership.
    """
    # log content to dm log channel for record
    dm_lg_ch = bot.get_channel(dm_log)
    await dm_lg_ch.send("{} ({})\n{}".format(str(ctx.author), str(ctx.author.id), ctx.message.content))
    # check for needed picture
    if not ctx.message.attachments:
        NO_PICTURE_TEXT = "I'm sorry {}, you need to provide a valid photo along with the ``verify`` command to complete the verification process.\n The image should be a **direct upload** and not a shareable link (Ex. Imgure, lighshot etc)"
        await ctx.message.channel.send(NO_PICTURE_TEXT.format(ctx.author))
        logging.info("Verify without screenshot from %s.", ctx.author.id)
        return
    for attachment in ctx.message.attachments:
        await dm_lg_ch.send(attachment.url)

    if args:
        server = Utility.map_vtuber_to_server(args[0])

        if len(args) > 1:
            language = Utility.map_language(args[1])
        else:
            language = "eng"

        if server:
            if Utility.is_user_on_server(ctx.author.id, server):
                await member_handler.add_to_queue(ctx.message, server, language)
            else:
                logging.info("%s tried to verify for a server they are not on.", ctx.author.id)
                await ctx.send("You are not on {} server!".format(args[0].title()))
        else:
            embed = Utility.create_supported_vtuber_embed()
            await ctx.send(content ="Please use a valid supported VTuber!", embed = embed)
    else:
        await member_handler.add_to_queue(ctx.message)

@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        logging.info("%s tried to use verify too often.", ctx.author.id)
        await ctx.send(f"Try again in {error.retry_after:.0f}s.")


@bot.command(hidden = True, name = "checkIdols")
@commands.is_owner()
async def check(ctx):
    logging.info("Checked supported VTuber!")
    Utility.create_supported_vtuber_embed()
    await ctx.send(database.get_vtuber_list())

def owner_or_test(ctx):
    return ctx.author.id == 846648298093936641 or ctx.author.id == owner_id

@bot.command(hidden = True, name = "forceCheck")
@commands.check(owner_or_test)
async def force_member_check(ctx):
    logging.info("Running forced check!")
    await member_handler.delete_expired_memberships(True)


@bot.command(hidden = True, name = "broadcast")
@commands.is_owner()
async def broadcast(ctx, title, text):
    serverlist = database.get_vtuber_list()

    #create Embed
    embed = discord.Embed(title = title, description = text, colour = embed_color)

    #send to every server
    for server in serverlist:
        server_db = database.get_server_db(server['guild_id'])
        lg_ch = bot.get_channel(server_db.get_log_channel())

        await lg_ch.send(content = None, embed = embed)
    logging.info("Sent broadcast to all servers.")

    
@bot.command(name = "dmMe",
    help="Sends a DM containg \"hi\" to the user using the command.",
	brief="Sends a DM to the user")
async def send_dm(ctx):
    logging.info("%s wanted a DM!", ctx.author.id)
    await ctx.author.send("Hi")

@send_dm.error
async def dm_error(ctx, error):
    if isinstance(error, discord.errors.Forbidden):
        logging.info("%s has DMs not allowed.", ctx.author.id)
        await ctx.send("You need to allow DMs!")

@bot.command(name="proof",
    help = "Allows to send additional proof. Requires the name of the vtuber. Only available in DMs",
    brief = "Send additional proof")
@commands.dm_only()
async def send_proof(ctx, vtuber: str):
    if not ctx.message.attachments:
        await ctx.send("Please include a screenshot of the proof!")
        return
    server_id = Utility.map_vtuber_to_server(vtuber)
    member_veri_ch = bot.get_channel(database.get_server_db(server_id).get_log_channel())

    # Send attachment and message to membership verification channel
    desc = "{}\n{}".format(str(ctx.author), "Additional proof")
    title = ctx.author.id
    embed = discord.Embed(title = title, description = None, colour = embed_color)
    embed.set_image(url = ctx.message.attachments[0].url)
    await member_veri_ch.send(content = "```\n{}\n```".format(desc), embed = embed)

    #send confirmation
    await ctx.send("Your additional proof was delivered safely!")

    logging.info("%s used the proof method for %s", ctx.author.id, vtuber)

@send_proof.error
async def proof_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Please do only send a valid name")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please include the server name!")
    embed = Utility.create_supported_vtuber_embed()
    await ctx.send(content=None, embed=embed)


#Time in status
async def jst_clock():
    while not bot.is_closed():
        try:
            now = dtime.now(tz = timezone.utc) + timedelta(hours = 9)
            timestr = now.strftime("%H:%M JST, %d/%m/%Y")
            await bot.change_presence(activity=discord.Game(name=timestr))
            await asyncio.sleep(60)
        except ConnectionResetError:
            logging.warn("Could not update JST Clock!")


# List Coroutines to be executed
coroutines = (
    jst_clock(),
    member_handler.check_membership_routine(),
    member_handler.handle_verifies()
)

# Main Coroutine
async def background_main():
    await bot.wait_until_ready()
    await asyncio.gather(*coroutines)

async def main():
    async with bot:
        bot.loop.create_task(background_main())
        await bot.start(token)

asyncio.run(main())
