#External
import discord
#Python
import asyncio
from datetime import datetime as dtime, tzinfo
from datetime import timezone, timedelta
from dateutil.relativedelta import relativedelta
#Internal
import utility
from ocr import detect_image_date, detect_image_text
from core import Core
from sending import dm_member

data = Core()
bot, db_cluster, embed_color = data.bot, data.db_cluster, data.embed_color

ID_NOT_FOUND_TEXT = "Can't find membership id in the database!"
DATE_FORMAT = r"%d/%m/%Y"

async def _check_membership_dates(server, res = None, msg = None):
    # Performs a mass check on membership dates and delete expired membership with a default message
    # Returns an expired_membership list {id, last_membership}

    server_db = db_cluster[str(server['guild_id'])]
    idol = server['name']

    
    expired_memberships = []
    expired_start_date = dtime.now(tz = timezone.utc) - relativedelta(months=1)

    message_title = idol + " Membership Expired"
    message_desc = "Your access to " + idol + "'s members-only channel has just expired!"
    message_desc += "\nYou may renew your membership by sending another updated verification photo using the ``verify`` command."
    message_desc += " Thank you so much for your cotinued support!"
    message_image = server_db['settings'].find_one({'kind': "picture_link"})['value']

    for member in server_db['members'].find():
        # For each bodan, if membership date ended (31 days) 30 days with one day buffer
        if (not member["last_membership"]) or member["last_membership"].replace(tzinfo = timezone.utc) < expired_start_date:
            # Add to delete list
            expired_memberships.append(member)

            # Delete from database
            server_db['members'].delete_one(member)

            # Remove member role from user
            guild = bot.get_guild(server['guild_id'])
            target_member = guild.get_member(member["id"])

            role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
            member_role = guild.get_role(role_id)

            await target_member.remove_roles(member_role)

            # dm expired membership
            await dm_member(member["id"], "{}\n{}".format(message_title, message_desc), embed = True, attachment_url = message_image)

    # Returns expired_memberships list
    return expired_memberships


async def view_membership(res, member_id=None):
    # if msg is empty, show all members
    db = db_cluster[str(res.guild.id)]

    if not member_id:
        m = ""
        for member in db["members"].find():
            member_id = member["id"]
            membership_date = member["last_membership"].replace(tzinfo = timezone.utc) + relativedelta(months=1)
            membership_date = membership_date.strftime("%d/%m/%Y")
            new_line = "{}: {}\n".format(member_id, membership_date)
            if len(m) + len(new_line) > 2000:
                await res.channel.send(m)
                m = ""
            m += new_line
        await res.channel.send(m)
        return

    # Check if zoopass in database and delete
    target_membership = db["members"].find_one({"id": member_id})
    if not target_membership:
        await res.channel.send(ID_NOT_FOUND_TEXT)
        return
    
    # Send information about membership
    guild = bot.get_guild(res.guild.id)
    target_member = guild.get_member(member_id)

    membership_date = target_membership["last_membership"].replace(tzinfo = timezone.utc)
    expiration_date = membership_date + relativedelta(months=1)

    ## change dates to strings
    membership_date = membership_date.strftime(DATE_FORMAT)
    expiration_date = expiration_date.strftime(DATE_FORMAT)

    m = "Name: {}\nID: {}\nLast Renewal Date: {}\nMembership End Date: {}"
    m = m.format(str(target_member), member_id, membership_date, expiration_date)
    embed = discord.Embed(title = "Membership", description = m)

    await res.channel.send(content=None, embed = embed)
    
"""
{
    "id": int
    "last_membership": datetime
}
"""

NO_PICTURE_TEXT = "I'm sorry {}, you need to provide a valid photo along with the ``verify`` command to complete the verification process.\n The image should be a **direct upload** and not a shareable link (Ex. Imgure, lighshot etc)"

async def verify_membership_with_server_detection(res):
    
    # Check if there is a valid attachment
    if not res.attachments:
        await res.channel.send(NO_PICTURE_TEXT.format(res.author))
        return

    if res.content:

        await res.channel.send("Start verifying the image...")

        server = None
        try:
            idol, server = await detect_idol_server(res.attachments[0].url)
        except Exception:
            pass

        if not server:
            m = "I am sorry I could not detect a VTuber name on the image.\n"
            m += "Please send a screenshot with the name of the VTuber on it.\n"
            m+= "If this was the case, please use `$verify <VTuber name>` instead of the normal $verify"
            embed = utility.create_supported_vtuber_embed()
            await res.channel.send(content = m, embed = embed)
            return

        confirm_msg = await res.channel.send("Do you want to verify Membership for " + idol + "?")
        if await utility.confirm_action(confirm_msg, res.author):
            await verify_membership(res, server)
        else:
            m = "Please make sure that only one VTuber name is shown.\n"
            m +="If this was the case, please use `$verify <VTuber name>` instead of the normal $verify"
            embed = utility.create_supported_vtuber_embed()
            await res.channel.send(content = m, embed = embed)



async def detect_idol_server(url):
    idols = db_cluster["settings"]['general'].find_one({'name': "supported_idols"})['supported_idols']
    
    text, inverted_text = await asyncio.wait_for(detect_image_text(url), timeout = 60)
    
    for idol in idols:
        if idol['name'] in text or idol['name'] in inverted_text:
            return (idol['name'], idol['guild_id'])


async def detect_membership_date(res):
    img_date = None
    # check date
    try:
        img_date = await detect_image_date(res.attachments[0].url)

    except asyncio.TimeoutError:
        print("timeout error detecting image")
    except Exception:
        print("date detection fail!!")

    if img_date:
        return (img_date)


async def verify_membership(res, server_id):

    if not res.attachments:
        await res.channel.send(NO_PICTURE_TEXT.format(res.author))
        return

    guild = bot.get_guild(server_id)
    server_db = db_cluster[str(server_id)]
    member_collection = server_db["members"]

    # if member exists, update date
    member = member_collection.find_one({"id": res.author.id})

    new_membership_date = await detect_membership_date(res)


    if not new_membership_date:
        m = "I am sorry, I could not detect a date on the image you sent. Please wait for manual confirmation from the staff.\n"
        m+= "If you do not get your role within the next day, please contact the staff."
        await res.channel.send(m)
        desc = "{}\n{}".format(str(res.author), "Date not detected")
        membership_date_text = "None"
    else:
        if not utility.check_date(new_membership_date):
            await res.channel.send("The date must not be in the past or too far in the future")
            return

        membership_date_text = new_membership_date.strftime(DATE_FORMAT)
        desc = "{}\n{}".format(str(res.author), membership_date_text)

        #substract month for db
        new_membership_date = new_membership_date  - relativedelta(months=1)

    

    #verification channel of the server
    member_veri_ch =bot.get_channel(server_db["settings"].find_one({"kind": "log_channel"})["value"])
    
    FORGOTTEN_SETTINGS_TEXT = "Please contact the staff of your server, the forgot to set some settings"
    
    if not member_veri_ch:
        res.channel.send(FORGOTTEN_SETTINGS_TEXT)
        return

    # Send attachment and message to membership verification channel
    title = res.author.id
    embed = discord.Embed(title = title, colour = embed_color)
    embed.add_field(name="Recognized Date", value = membership_date_text)
    embed.set_image(url = res.attachments[0].url)
    message = await member_veri_ch.send(content = "```\n{}\n```".format(desc), embed = embed)


    # should not get the role yet
    if not new_membership_date:
        return


    automatic_role = server_db["settings"].find_one({"kind": "automatic_role"})["value"]

    # automatic role not allowed
    if not automatic_role:
        m = "The staff is checking your proof now. You will gain access if they deem the proof as appropriate"
        await res.channel.send(m)
        return

    if member:
        last_membership = member["last_membership"].replace(tzinfo = timezone.utc)
        member_collection.update_one({"id": res.author.id}, {"$set": {"last_membership": max(new_membership_date, last_membership)}})

    # if not, create data
    else:
        member_collection.insert_one({
            "id": res.author.id,
            "last_membership": new_membership_date
        })
    # add role
    author = guild.get_member(res.author.id)

    role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
    role = guild.get_role(role_id)

    if not role:
        res.channel.send(FORGOTTEN_SETTINGS_TEXT)
        return
        
    await author.add_roles(role)

    # DM user that the verification process is complete
    m = "Membership applied! You now have access to members-excusive content in the server."
    m += "\nPlease note that our staff will double-confirm the verification photo and may revoke it on a case-by-case basis."
    m += "\nIf you have encountered any issue with accessing the channels or have a separate enquiry, please contact a mod."
    await res.channel.send(m)


async def set_membership(res, member_id, date):
    
    member_collection = db_cluster[str(res.guild.id)]['members']
    # Check if id exists
    target_membership = member_collection.find_one({"id": member_id})
    dates = date.split("/")

    if len(dates)!=3 or any(not utility.is_integer(date) for date in dates):
            await res.channel.send("Please provide a valid date (dd/mm/yyyy) or integer days (+/- integer).")
            return
    new_date = dtime(year = int(dates[2]), month = int(dates[1]), day = int(dates[0]), tzinfo = timezone.utc)

    if not utility.check_date(new_date):
        await res.channel.send("The date must not be in the past or too far in the future")
        return

    db_date = new_date - relativedelta(months=1)
    if not target_membership:
            #needs to be date for new entry
            await res.channel.send("Creating new entry!")
            member_collection.insert_one({
                "id": member_id,
                "last_membership": db_date
            })
    else:
        db_cluster[str(res.guild.id)]['members'].update_one({"id": member_id}, {"$set": {"last_membership": db_date}})

    server_db = db_cluster[str(res.guild.id)]


    target_member = res.guild.get_member(member_id)
    role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
    role = res.guild.get_role(role_id)
    await target_member.add_roles(role)

    await res.channel.send("New membership date for {} set at {}!".format(member_id, new_date.strftime(DATE_FORMAT)))
    

async def del_membership(res, member_id: int, text):
    
    member_id = int(member_id)

    server_db = db_cluster[str(res.guild.id)]

    # Check if zoopass in database and delete
    target_membership = server_db['members'].find_one({"id": member_id})
    if not target_membership:
        await res.channel.send(ID_NOT_FOUND_TEXT)
        return
    await res.channel.send("Found membership in database, deleting now!")
    server_db['members'].delete_one(target_membership)

    # Remove zoopass role from user
    guild = res.guild
    target_member = guild.get_member(member_id)

    role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
    role = guild.get_role(role_id)

    await target_member.remove_roles(role)


    
    await res.channel.send("Membership successfully deleted.")

    # If msg has extra lines, send dm to target user to notify the zoopass deletion
    if text:
        await target_member.send(" ".join(text))
    else:
        await target_member.send("Your membership for " + utility.get_vtuber(res.guild.id) + " was deleted!")

async def delete_expired_memberships(forced=False):
    
    overall_settings = db_cluster["settings"]['general']

    # get data of last checked timestamp
    now = dtime.now(tz = timezone.utc)
    last_checked = overall_settings.find_one({"name": "member_check"}).get("last_checked", None)

    #get all active servers
    serverlist = overall_settings.find_one({'name': "supported_idols"})['supported_idols']

    #execute for every server
    for server in serverlist:
        server_db = db_cluster[str(server['guild_id'])]
        lg_ch = bot.get_channel(server_db['settings'].find_one({'kind': "log_channel"})['value'])

        if not forced:
            await lg_ch.send("Performing membership check, last check was {}".format(last_checked))
        else:
            await lg_ch.send("Forced Membership check")

        # perform check
        expired_memberships = await _check_membership_dates(server)
        content = ["{}: {}".format(d["id"], d["last_membership"]) for d in expired_memberships]
        m = "Expired Memberships:\n"
        m += "\n".join(content)
        if m:
            await lg_ch.send(m)

        # add wait time
        overall_settings.update_one({"name": "member_check"}, {"$set": {"last_checked": now}})
    
async def check_membership_routine():
    while not bot.is_closed():
        now = dtime.now(tz = timezone.utc)
        last_checked = db_cluster["settings"]['general'].find_one({"name": "member_check"}).get("last_checked", None)

        # if there is no last checked, or last checked is more than 12 hours ago, do new check
        if last_checked:
            # add utc to last checked (mongodb always naive)
            last_checked = last_checked.replace(tzinfo = timezone.utc)

        if not last_checked or (now - last_checked >= timedelta(hours = 12)):
            await delete_expired_memberships()
            wait_time = 12 * 3600
        else:
            # else wait for the remaining time left
            wait_time = 12 * 3600 - (now - last_checked).total_seconds()
        await asyncio.sleep(wait_time)