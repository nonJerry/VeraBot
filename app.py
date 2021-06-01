#External
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
local = True


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
        prefixes = db_cluster[str(guild.id)]["settings"].find_one({"kind": "prefixes"})["values"]
        if prefixes:
            return prefixes
    return "$"

# Set up bot
bot = commands.Bot(command_prefix=determine_prefix, description='Bot to verify and manage Memberships.\nlogChannel, Vtuber name and memberRole need to be set!', intents=intents, case_insensitive=True, owner_id=owner_id)

# listen to other bots while testing

if stage == "TEST":
    from distest.patches import patch_target
    bot = patch_target(bot)
    logging.info("Listining to bots too. Only for testing purposes!!!")


# database settings
db_cluster = MongoClient(db_url.format(db_user, db_pass))


# set up classes
member_handler = MembershipHandler(bot, db_cluster, embed_color)
Utility.setup(bot, db_cluster, embed_color)
OCR.setup(bot, local)
Sending.setup(bot, embed_color)

#add cogs
bot.add_cog(Settings(bot, db_cluster))
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

    dbnames = db_cluster.list_database_names()
    
    if not str(guild.id) in dbnames:
        new_guild_db = db_cluster[str(guild.id)]
        settings = new_guild_db["settings"]

        # Create base configuration
        json = { "kind": "prefixes", "values" : ['$']}
        settings.insert_one(json)

        json = {"kind": "member_role", "value" : 0}
        settings.insert_one(json)

        json = {"kind": "log_channel", "value" : 0}
        settings.insert_one(json)

        json = {"kind": "mod_role", "value" : 0}
        settings.insert_one(json)

        json = {"kind": "picture_link", "value" : "https://pbs.twimg.com/profile_images/1198438854841094144/y35Fe_Jj.jpg"} #hololive logo
        settings.insert_one(json)

        json = {"kind": "automatic_role", "value" : False}
        settings.insert_one(json)

        json = {"kind": "require_additional_proof", "value" : False}
        settings.insert_one(json)

        json = {"kind": "tolerance_duration", "value" : 1}
        settings.insert_one(json)

        json = {"kind": "inform_duration", "value" : 1}
        settings.insert_one(json)

        json = {"kind": "logging", "value" : True}
        settings.insert_one(json)

        logging.info("Created database for %s". str(guild.id))


@bot.event
async def on_guild_remove(guild):
    """
    Removes the guild from the supported idols so that memberships are not checked.
    """
    logging.info("Left Guild: %s (%s)", guild.name , guild.id)
    settings = db_cluster["settings"]["general"]
    settings.update_one({'name': 'supported_idols'}, {'$pull': { 'supported_idols': {'guild_id': guild.id}}})

@bot.event
async def on_raw_reaction_add(payload):
    # get reaction from payload
    if not payload.guild_id:
        return
    channel = bot.get_channel(payload.channel_id)
    try:
        msg = await channel.fetch_message(payload.message_id)
        reaction = discord.utils.get(msg.reactions, emoji=payload.emoji.name)

        # only the first react by somebody else than the bot should be processed
        if reaction:
            if reaction.count != 2:
                return
            msg = reaction.message

            # this handling is not for DMs
            # Only process reactions that also were also made by the bot
            if not reaction.me:
                return
            if msg.embeds:
                user = bot.get_user(payload.user_id)
                await member_handler.process_reaction(channel, msg, user, reaction)
                    
    except (discord.errors.Forbidden, discord.errors.NotFound):
        logging.info("%s: problem with reaction in %s", payload.guild_id, channel.id)
        return

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
@commands.cooldown(2, 50, commands.BucketType.user)
async def verify(ctx, *vtuber):
    """
    Command in the DMs that tries to verify a screenshot for membership.
    """
    # log content to dm log channel for record
    dm_lg_ch = bot.get_channel(dm_log)
    await dm_lg_ch.send("{}\n{}".format(str(ctx.author),ctx.message.content))
    for attachment in ctx.message.attachments:
        await dm_lg_ch.send(attachment.url)

    if vtuber:
        server = map_vtuber_to_server(vtuber[0])
        if server:
            await member_handler.add_to_queue(ctx.message, server)
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
    await ctx.send(db_cluster['settings']['general'].find_one()['supported_idols'])

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
    serverlist = db_cluster["settings"]['general'].find_one({'name': "supported_idols"})['supported_idols']

    #create Embed
    embed = discord.Embed(title = title, description = text, colour = embed_color)

    #send to every server
    for server in serverlist:
        server_db = db_cluster[str(server['guild_id'])]
        lg_ch = bot.get_channel(server_db['settings'].find_one({'kind': "log_channel"})['value'])

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
    server_id = map_vtuber_to_server(vtuber)
    member_veri_ch =bot.get_channel(db_cluster[str(server_id)]["settings"].find_one({"kind": "log_channel"})["value"])

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


def map_vtuber_to_server(name):
    settings_db = db_cluster["settings"]["general"]
    result = settings_db.find_one({}, {'supported_idols' : { '$elemMatch': {'name' : name.lower()}}})
    if 'supported_idols' in result:
        return result['supported_idols'][0]['guild_id']

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

bot.loop.create_task(background_main())
bot.run(token)