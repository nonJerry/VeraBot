#External
import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandNotFound
#Python
import asyncio
from datetime import datetime as dtime
from datetime import timezone, timedelta
import re
#Internal
from membership_handling import MembershipHandler
from settings import Settings
from membership import Membership
from utility import Utility
from ocr import OCR
from sending import Sending
from pymongo import MongoClient
import os

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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        # Ignore this error
        pass
    elif isinstance(error, commands.MissingPermissions):
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
    print("Joined new Guild: " + str(guild.id))

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

        json = {"kind": "automatic_role", "value" : True}
        settings.insert_one(json)

        json = {"kind": "require_additional_proof", "value" : False}
        settings.insert_one(json)

        json = {"kind": "tolerance_duration", "value" : 1}
        settings.insert_one(json)

        json = {"kind": "inform_duration", "value" : 1}
        settings.insert_one(json)


@bot.event
async def on_guild_remove(guild):
    """
    Removes the guild from the supported idols so that memberships are not checked.
    """
    print("Left Guild: " + str(guild.id))
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
                embed = msg.embeds[0]
                automatic_role = db_cluster[str(msg.guild.id)]["settings"].find_one({"kind": "automatic_role"})["value"]

                # always only the id
                target_member_id = int(embed.title)
                if reaction.emoji == '✅':
                    if not automatic_role:
                        membership_date = embed.fields[0].value

                        # set membership
                        await member_handler.set_membership(msg, target_member_id, membership_date)
                    #always clear
                    await msg.clear_reactions()
                    await msg.add_reaction(emoji='👌')
                # deny option
                elif reaction.emoji == u"\U0001F6AB":
                    user = bot.get_user(payload.user_id)
                    text = "Is there an issue with the proof (Faked or no date on screenshot) -> :white_check_mark:\n"
                    text += "Or is the date recognized incorrectly/was not recognized -> :no_entry_sign:"
                    confirm_msg = await channel.send(text, reference=msg, mention_author=False)
                    if await Utility.confirm_action(confirm_msg, user):
                        confirm_msg = await channel.send("Please write a message that will be sent to the User.", reference=msg, mention_author=False)
                        def check(m):
                            return m.author == user and m.channel == channel

                        text_msg = await bot.wait_for('message', check=check)
                    
                        target_member = bot.get_user(target_member_id)
                        await target_member.send(text_msg.content)
                        await channel.send("Message was sent to user.", reference=text_msg, mention_author=False)

                        if automatic_role:
                            await member_handler.del_membership(msg, target_member_id, None, False)
                        await msg.clear_reactions()
                        await msg.add_reaction(emoji='👎')
                    else:
                        await asyncio.sleep(1)
                        confirm_msg = discord.utils.get(bot.cached_messages, id=confirm_msg.id)
                        if confirm_msg.reactions[0].count == 1 and confirm_msg.reactions[1].count == 1:
                            await channel.send("The reaction took too long! Please remove you reaction from this message and add it again.", reference=msg, mention_author=False)
                        else:
                            m = "Please write the correct date from the screenshot in the format dd/mm/yyyy."
                            await channel.send(m, reference=msg, mention_author=False)
                            def check(m):
                                return m.author == user and m.channel == channel

                            date_msg = await bot.wait_for('message', check=check)

                            await member_handler.set_membership(msg, target_member_id, date_msg.content)
                            await msg.clear_reactions()
                            await msg.add_reaction(emoji='👎')

                    
    except discord.errors.Forbidden:
        print(payload.channel_id)
        print(payload.guild_id)



@bot.command(
    help="Can be called with just $verify but also with $verify <VTuber name>\n" +
    "Both versions require a screenshot sent with it.",
	brief=" Tries to verify a screenshot for membership in the DMs"
)
@commands.dm_only()
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
            await member_handler.verify_membership(ctx.message, server)
        else:
            embed = Utility.create_supported_vtuber_embed()
            await ctx.send(content ="Please use a valid supported VTuber!", embed = embed)
    else:
        await member_handler.verify_membership_with_server_detection(ctx.message)

@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("This command only works in DMs!")


@bot.command(hidden = True, name = "checkIdols")
@commands.is_owner()
async def check(ctx):
    Utility.create_supported_vtuber_embed()
    await ctx.send(db_cluster['settings']['general'].find_one()['supported_idols'])


@bot.command(hidden = True, name = "forceCheck")
@commands.is_owner()
async def force_member_check(ctx):
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

    
@bot.command(name = "dmMe",
    help="Sends a DM containg \"hi\" to the user using the command.",
	brief="Sends a DM to the user")
async def send_dm(ctx):
    await ctx.author.send("Hi")

@send_dm.error
async def dm_error(ctx, error):
    if isinstance(error, discord.errors.Forbidden):
        await ctx.send("You need to allow DMs!")
        error = None

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
    result = settings_db.find_one({}, {'supported_idols' : { '$elemMatch': {'name' : name}}})
    if 'supported_idols' in result:
        return result['supported_idols'][0]['guild_id']

#Time in status
async def jst_clock():
    while not bot.is_closed():
        now = dtime.now(tz = timezone.utc) + timedelta(hours = 9)
        timestr = now.strftime("%H:%M JST, %d/%m/%Y")
        await bot.change_presence(activity=discord.Game(name=timestr))
        await asyncio.sleep(60)


# List Coroutines to be executed
coroutines = (
    jst_clock(),
    member_handler.check_membership_routine(),
)

# Main Coroutine
async def background_main():
    await bot.wait_until_ready()
    await asyncio.gather(*coroutines)

bot.loop.create_task(background_main())
bot.run(token)