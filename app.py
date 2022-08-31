# External
from database import Database
import discord
from discord import app_commands, Forbidden
from discord.ext import commands
from discord.ext.commands.errors import CommandNotFound
from pymongo import MongoClient
# Python
import asyncio
from datetime import datetime as dtime
from datetime import timezone, timedelta
import os
import logging
# Internal
from membership_handling import MembershipHandler
from settings import Settings
from membership import Membership
from utility import Utility
from ocr import OCR
from sending import Sending
from views import PersistentView
from logging.handlers import SysLogHandler

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
log_dest = os.getenv("LOG_LINK")
log_port = os.getenv("LOG_PORT")
syslog = SysLogHandler(address=(log_dest, log_port))
logging.getLogger().addHandler(syslog)
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
intents.message_content = True


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
bot = commands.Bot(command_prefix=determine_prefix,
                   description='Bot to verify and manage Memberships.\nlogChannel, Vtuber name and memberRole need to be set!',
                   intents=intents, case_insensitive=True, owner_id=owner_id)

# 2 tries per 50s as default
verify_tries = 2

# listen to other bots while testing
if stage == "TEST":
    # to not run into cooldown limit
    verify_tries = 1000

# database settings
db_cluster = MongoClient(db_url.format(db_user, db_pass))

# set up classes
database = Database(db_cluster)
member_handler = MembershipHandler(bot, embed_color)
Utility.setup(bot, embed_color)
OCR.setup(bot, local)
Sending.setup(bot, embed_color)


# add cogs
async def add_cogs():
    await bot.add_cog(Settings(bot))
    await bot.add_cog(Membership(bot, member_handler))
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
        # skip already locally handled errors
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You are missing a required argument!")
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
    logging.info("Joined new Guild: %s (%s)", guild.name, guild.id)

    database.create_new_server(guild.id)

    logging.info("Created database for %s", guild.id)


@bot.event
async def on_guild_remove(guild):
    """
    Removes the guild from the supported idols so that memberships are not checked.
    """
    logging.info("Left Guild: %s (%s)", guild.name, guild.id)
    database.remove_server(guild.id)
    logging.info(f"Deleted Collection for {guild.id}")


def dm_or_test_only():
    def predicate(ctx):
        return isinstance(ctx.channel, discord.DMChannel) or stage == "TEST"

    return commands.check(predicate)


@bot.command(
    help="Obsolete verify command, notifies user to use slash command version instead.",
    brief="Obsolete verify command."
)
@dm_or_test_only()
@commands.cooldown(verify_tries, 50, commands.BucketType.user)
async def verify(ctx, *args):
    await ctx.send(
        "This command no longer works through DMs, please use the slash command '/verify' in the server instead.")


@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        logging.info("%s tried to use verify too often.", ctx.author.id)
        await ctx.send(f"Try again in {error.retry_after:.0f}s.")


@bot.command(hidden=True, name="checkIdols")
@commands.is_owner()
async def check(ctx):
    logging.info("Checked supported VTuber!")
    Utility.create_supported_vtuber_embed()
    await ctx.send(database.get_vtuber_list())


def owner_or_test(ctx):
    return ctx.author.id == 846648298093936641 or ctx.author.id == owner_id


@bot.command(hidden=True, name="forceCheck")
@commands.check(owner_or_test)
async def force_member_check(ctx):
    logging.info("Running forced check!")
    await member_handler.delete_expired_memberships(True)


@bot.command(hidden=True, name="broadcast")
@commands.is_owner()
async def broadcast(ctx, title, text):
    serverlist = database.get_vtuber_list()

    # create Embed
    embed = discord.Embed(title=title, description=text, colour=embed_color)

    # send to every server
    for server in serverlist:
        server_db = database.get_server_db(server['guild_id'])
        lg_ch = bot.get_channel(server_db.get_log_channel())

        await lg_ch.send(content=None, embed=embed)
    logging.info("Sent broadcast to all servers.")


@bot.command(name="dmMe",
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
             help="Allows to send additional proof. Requires the name of the vtuber. Only available in DMs",
             brief="Send additional proof")
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
    embed = discord.Embed(title=title, description=None, colour=embed_color)
    embed.set_image(url=ctx.message.attachments[0].url)
    await member_veri_ch.send(content="```\n{}\n```".format(desc), embed=embed)

    # send confirmation
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


# slash commands must be synced manually, guild for the current guild (good for testing), and global for all servers

@bot.command(name="syncGuild")
@commands.is_owner()
@commands.guild_only()
async def syncGuild(ctx):
    ctx.bot.tree.copy_global_to(guild=ctx.guild)
    await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send("commands synced to guild")


@bot.command(name="syncGuildClear")
@commands.is_owner()
@commands.guild_only()
async def syncGuildClear(ctx):
    # since all commands are global, doing a sync call without the copy_global_to function will clear all guild synced commands
    await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send("guild commands cleared from sync")


@bot.command(name="syncGlobal")
@commands.is_owner()
@commands.guild_only()
async def syncGlobal(ctx):
    await ctx.bot.tree.sync()
    await ctx.send("commands synced globally")


@bot.tree.error
async def tree_error(interaction, error):
    try:
        if isinstance(error, Forbidden):
            logging.info("Could not message the user in command by %s", interaction.user.id)
            await interaction.response.send_message("Could not message the user.")
        elif isinstance(error, discord.errors.NotFound):
            logging.info("Did not find interaction in %s by %s", interaction.guild_id, interaction.user.id)
            await interaction.response.send_message("Had a problem finding the interaction, please try again", ephemeral=True)
    except discord.errors.NotFound:
        logging.info("Could not send the info of error")



# List Coroutines to be executed
coroutines = (
    member_handler.check_membership_routine(),
    member_handler.handle_verifies()
)


# Main Coroutine
async def background_main():
    await add_cogs()
    # Add Log Channel processing view
    bot.add_view(PersistentView(member_handler))
    await bot.wait_until_ready()
    await asyncio.gather(*coroutines)


async def main():
    async with bot:
        bot.loop.create_task(background_main())
        await bot.start(token)


asyncio.run(main())
