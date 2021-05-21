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
from core import create_core

### Setup data
# Set variable to true for local testing
local = False

token, data = create_core(local)

bot = data.bot
owner = data.owner
dev = data.dev
embed_color = data.embed_color
dm_log = data.dm_log
db_cluster = data.db_cluster


#Late import to guarantee data is initialized
#Internal
import membership
from utility import create_supported_vtuber_embed

error_text = None
@bot.event
async def on_command_error(ctx, error):
    """
    Rewrites on_command_error a not found command gets a respnse.
    """
    global error_text

    if isinstance(error, CommandNotFound):
        await ctx.send("This command does not exist!")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You are not allowed to use this command!")
    elif error_text:
        await ctx.send(error_text)
        error_text = None
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


@bot.event
async def on_guild_remove(guild):
    """
    Removes the guild from the supported idols so that memberships are not checked.
    """
    print("Left Guild: " + str(guild.id))
    settings = db_cluster["settings"]["general"]
    settings.update_one({'name': 'supported_idols'}, {'$pull': { 'supported_idols': {'guild_id': guild.id}}})


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
            await membership.verify_membership(ctx.message, server)
        else:
            embed = create_supported_vtuber_embed()
            await ctx.send(content ="Please use a valid supported VTuber!", embed = embed)
    else:
        await membership.verify_membership_with_server_detection(ctx.message)

@verify.error
async def verify_error(ctx, error):
    global error_text
    if isinstance(error, commands.PrivateMessageOnly):
        error_text = "This command only works in DMs!"


@bot.command(name="prefix",
    help="Adds the <prefix> that can be used for the bot on this server.",
	brief="Adds an additional prefix")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_prefix(ctx, prefix: str):
    settings = db_cluster[str(ctx.guild.id)]["settings"]
    settings.update_one({"kind": "prefixes"}, {'$push': {'values': prefix}})
    await ctx.send("Prefix " + prefix + " added")

@set_prefix.error
async def prefix_error(ctx, error):
    await dm_error(ctx, error)
    await invalid_argument_error(ctx, error)

async def dm_error(ctx, error):
    if isinstance(ctx.channel, discord.channel.DMChannel) and isinstance(error, commands.MissingPermissions):
        await ctx.send("This command should not be used in the DMs")

async def invalid_argument_error(ctx, error):
    if isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('The argument is invalid')


@bot.command(name="removePrefix",
    help="Removes the <prefix> so that it is not available as a prefix anymore for this server.",
	brief="Removes an prefix")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def remove_prefix(ctx, prefix: str):
    settings = db_cluster[str(ctx.guild.id)]["settings"]

    if settings.update_one({"kind": "prefixes"}, {'$pull': {'values': prefix}}).matched_count == 0:
        await ctx.send("Prefix not found")
    else:
        await ctx.send(prefix +" removed")


@bot.command(name="showPrefix",
    help="Shows all prefixes that are available to use commands of this bot on this server.",
	brief="Shows all prefixes")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def remove_prefix(ctx):
    settings = db_cluster[str(ctx.guild.id)]["settings"]

    await ctx.send("Those prefixes are set: " + str(settings.find_one({"kind": "prefixes"})['values']))


@bot.command(name="setVTuber",
    help="Sets the name of the VTuber of this server.\nThe screenshot sent for the verification is scanned for this name. Therefore this name should be identical with the name in the membership tab.",
	brief="Sets the name of the VTuber of this server")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_idol(ctx, vtuber_name: str):
    settings = db_cluster["settings"]["general"]
    # always only one entry
    for element in settings.find_one({}, {'supported_idols'})['supported_idols']:
        if vtuber_name in element['name']:
            await ctx.send("This Vtuber is already mapped to a server!")
            return
    if settings.find_one( { 'supported_idols.guild_id': ctx.guild.id}):
        settings.update_one({'supported_idols.guild_id': ctx.guild.id}, {'$set': {'supported_idols.$': {"name": vtuber_name, "guild_id": ctx.guild.id}}})
    else:
        settings.update_one({"name": "supported_idols"}, {'$push': {'supported_idols': {"name": vtuber_name, "guild_id": ctx.guild.id}}})
    await ctx.send("Set VTuber name to " + vtuber_name)
    print("New Vtuber added: " + vtuber_name)


@bot.command(name="memberRole", aliases=["setMemberRole"],
    help="Sets the role that should be given to a member who has proven that he has valid access to membership content.\nRequires the ID not the role name or anything else!",
	brief="Sets the role for membership content")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_member_role(ctx, id: int):
    if check_role_integrity(ctx, id):
        set_value_in_server_settings(ctx, "member_role", id)

        await ctx.send("Member role id set to " + str(id))
    else:
        await ctx.send("ID does not refer to a legit role")


@bot.command(name="logChannel", aliases=["setLogChannel"],
    help="Sets the channel which is used to control the sent memberships.\nRequires the ID not the role name or anything else!",
	brief="Sets the channel in which the logs should be sent")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_log_channel(ctx, id: int):
    set_value_in_server_settings(ctx, "log_channel", id)

    await ctx.send("Log Channel id set to " + str(id))


@bot.command(hidden = True, name="modRole")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_mod_role(ctx, id: int):
    if check_role_integrity(ctx, id):
        set_value_in_server_settings(ctx, "mod_role", id)

        await ctx.send("Mod role id set to " + str(id))
    else:
        await ctx.send("ID does not refer to a legit role")


@bot.command(name="picture", aliases=["setPicture"],
    help="Sets the image that is sent when a membership is about to expire.\n" +
    "It supports link that end with png, jpg or jpeg.",
	brief="Set image for expiration message.")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_mod_role(ctx, link: str):
    print(link)
    match = re.search(r"http[s]?://[a-zA-Z0-9_\.]+/[a-zA-Z0-9_/]+\.(png|jpeg|jpg)", link)
    if match:
        set_value_in_server_settings(ctx, "picture_link", link)
        await ctx.send("Image for expiration message set.")
    else:
        await ctx.send("Please send a legit link. Only jpg, jpeg and png are accepted.")

@bot.command(name="setAuto", aliases=["auto", "setAutoRole", "setAutomaticRole"],
    help = "Sets whether the bot is allowed to automatically add the membership role.",
    brief = "Set flag for automatic role handling")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_automatic_role(ctx, flag: str):
    if flag in ['True', 'true']:
        flag = True
    elif flag in [ 'False', 'false']:
        flag = False
    else:
        ctx.send("Please do only use True or False")
        return
    set_value_in_server_settings(ctx, "automatic_role", flag)
    await ctx.send("Flag for automatic role handling set to " + str(flag))


@bot.command(name="viewMembers", aliases=["members","member", "viewMember"],
    help = "Shows all user with the membership role. Or if a id is given this users data.",
    brief = "Show membership(s)")
@commands.has_permissions(manage_messages=True)
@commands.guild_only()
async def view_members(ctx, *id: int):
    # always only one id at max
    if id:
        await membership.view_membership(ctx.message, id[0])
    else:
        await membership.view_membership(ctx.message, None)

@bot.command(name="addMember", aliases=["set_membership", "setMember"],
    help="Gives the membership role to the user whose ID was given.\n" + 
    "<date> has to be in the format dd/mm/yyyy.\n" +
    "It equals the date shown on the sent screenshot",
	brief="Gives the membership role to a user")
@commands.has_permissions(manage_messages=True)
@commands.guild_only()
async def set_membership(ctx, member_id: int, date):
    await membership.set_membership(ctx.message, member_id, date)

@set_membership.error
async def set_membership_error(ctx, error):
    global error_text
    if isinstance(error, commands.MissingRequiredArgument):
        error_text = "Please include at least two arguments!"
    elif isinstance(error, commands.BadArgument):
        error_text = "One of the arguments has the wrong data type!"


@bot.command(name="delMember",
    help="Removes the membership role from the user whose ID was given.\n" +
    "A text which is sent to the user as DM can be given but is optional.",
	brief="Removes the membership role from the user")
@commands.has_permissions(manage_messages=True)
@commands.guild_only()
async def del_membership(ctx, member_id: int, *text):
    await membership.del_membership(ctx.message, member_id, text)

@set_idol.error
@set_log_channel.error
@set_member_role.error
@del_membership.error
@set_prefix.error
@remove_prefix.error
@set_automatic_role.error
@view_members.error
async def id_error(ctx, error):
    global error_text
    if isinstance(error, commands.BadArgument):
        error_text = "Please provide a valid id!"
    elif isinstance(error, commands.MissingRequiredArgument):
        error_text = "Please include the argument!"


@bot.command(hidden = True, name = "checkIdols")
@commands.is_owner()
async def check(ctx):
    create_supported_vtuber_embed()
    await ctx.send(db_cluster['settings']['general'].find_one()['supported_idols'])


@bot.command(hidden = True, name = "forceCheck")
@commands.is_owner()
async def force_member_check(ctx):
    await membership.delete_expired_memberships(True)


@bot.command(name = "dmMe",
    help="Sends a DM containg \"hi\" to the user using the command.",
	brief="Sends a DM to the user")
async def send_dm(ctx):
    await ctx.author.send("Hi")

@send_dm.error
async def dm_error(ctx, error):
    global error_text
    if isinstance(error, discord.errors.Forbidden):
        error_text = "You need to allow DMs!"

@bot.command(name="proof",
    help = "Allows to send additional proof. Requires the name of the vtuber. Only available in DMs",
    brief = "Send additional proof")
@commands.dm_only()
async def send_proof(ctx, vtuber: str):
    if not ctx.message.attachments:
        ctx.send("Please include a screenshot of the proof!")
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
    global error_text
    if isinstance(error, commands.BadArgument):
        error_text = "Please do only send a valid name"
    elif isinstance(error, commands.MissingRequiredArgument):
        error_text = "Please include the server name!"
    embed = create_supported_vtuber_embed()
    ctx.send(content=None, embed=embed)
    


def check_role_integrity(ctx, id: int):
    if ctx.guild.get_role(id):
        return True
    return False

def set_value_in_server_settings(ctx, setting: str, value):
    settings_db = db_cluster[str(ctx.guild.id)]["settings"]

    settings_db.update_one({'kind': setting}, {'$set': {'value': value}})


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
    membership.check_membership_routine(),
)

# Main Coroutine
async def background_main():
    await bot.wait_until_ready()
    await asyncio.gather(*coroutines)

bot.loop.create_task(background_main())
bot.run(token)