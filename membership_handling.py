#External
import discord
#Python
import asyncio
from datetime import datetime as dtime, tzinfo
from datetime import timezone, timedelta
from dateutil.relativedelta import relativedelta
from collections import deque
#Internal
from utility import Utility
from ocr import OCR
from sending import Sending

class MembershipHandler:
    def __init__(self, bot, db_cluster, embed_color):
        self.NO_PICTURE_TEXT = "I'm sorry {}, you need to provide a valid photo along with the ``verify`` command to complete the verification process.\n The image should be a **direct upload** and not a shareable link (Ex. Imgure, lighshot etc)"
        self.ID_NOT_FOUND_TEXT = "Can't find membership id in the database!"
        self.DATE_FORMAT = r"%d/%m/%Y"

        self.bot = bot
        self.db_cluster = db_cluster
        self.embed_color = embed_color
        # deque for data
        self.verify_deque = deque()

    async def add_to_queue(self, res, server_id=None):
        
        # Check if there is a valid attachment
        if not res.attachments:
            await res.channel.send(self.NO_PICTURE_TEXT.format(res.author))
            return
        self.verify_deque.append([res, server_id])
        m = "You're proof is added to the queue now and will be processed later.\n"
        m += "You will get a message when your role is applied."
        await res.channel.send(m)

    async def _check_membership_dates(self, server, res = None, msg = None):
        # Performs a mass check on membership dates and delete expired membership with a default message
        # Returns an expired_membership list {id, last_membership}

        server_db = self.db_cluster[str(server['guild_id'])]
        idol = server['name']

        inform_duration = server_db['settings'].find_one({"kind": "inform_duration"})['value']
        tolerance_duration = server_db['settings'].find_one({"kind": "tolerance_duration"})['value']

        expired_memberships = []
        expiry_date = dtime.now(tz = timezone.utc) - relativedelta(months=1)
        notify_date = expiry_date + timedelta(days=inform_duration)
        tolerance_date = expiry_date - timedelta(days=tolerance_duration)

        message_title = idol + " Membership {}!"
        end_text = "You may renew your membership by sending another updated verification photo using the ``$verify`` command."
        end_text += "Thank you so much for your continued support!"
        message_image = server_db['settings'].find_one({'kind': "picture_link"})['value']

        #TODO: Restructure DB after dates?
        for member in server_db['members'].find():
            # For each member
            if member["last_membership"]:
                last_membership = member["last_membership"].replace(tzinfo = timezone.utc)
                # delete role
                if last_membership <= tolerance_date:
                    title = message_title.format("channel access ended")
                    message_desc = "You lost your access to {}'s members-only channel!\n"
                    message_desc += end_text

                    # Delete from database
                    server_db['members'].delete_one(member)

                    # Remove member role from user
                    guild = self.bot.get_guild(server['guild_id'])
                    target_member = guild.get_member(member["id"])

                    role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
                    member_role = guild.get_role(role_id)

                    await target_member.remove_roles(member_role)
                    #send dm
                    await Sending.dm_member(member["id"], title, message_desc.format(idol, str(inform_duration)), embed = True, attachment_url = message_image)
                # notify
                elif inform_duration != 0 and last_membership <= notify_date and not member['informed']:
                    title = message_title.format("expires soon!")
                    message_desc = "Your membership to {} will expire in {} day(s).\n"
                    message_desc += "If you do not want to lose this membership please don't forget to anew it!"
                    await Sending.dm_member(member["id"], title, message_desc.format(idol, str(inform_duration)), embed = True, attachment_url = message_image)
                    server_db['members'].update_one({"id": member['id']}, {"$set": {"informed": True}})

            if not last_membership or (last_membership <= expiry_date and not member['expiry_sent'] and tolerance_date < last_membership):
                title = message_title.format("expired")
                message_desc = "Your membership to {} has just expired!\n"
                message_desc += "You will lose your access to the channel after {} day(s) if you do not renew your membership.\n"
                message_desc += end_text
            
                # Add to delete list
                expired_memberships.append(member)

                # dm expired membership
                await Sending.dm_member(member["id"], title, message_desc.format(idol, str(tolerance_duration)), embed = True, attachment_url = message_image)

                server_db['members'].update_one({"id": member['id']}, {"$set": {"expiry_sent": True}})

        # Returns expired_memberships list
        return expired_memberships


    async def view_membership(self, res, member_id=None):
        # if msg is empty, show all members
        db = self.db_cluster[str(res.guild.id)]

        if not member_id:
            count = 0
            m = ""
            for member in db["members"].find():
                count += 1
                member_id = member["id"]
                membership_date = member["last_membership"].replace(tzinfo = timezone.utc) + relativedelta(months=1)
                membership_date = membership_date.strftime("%d/%m/%Y")
                new_line = "{}: {}\n".format(member_id, membership_date)
                if len(m) + len(new_line) > 2000:
                    await res.channel.send(m)
                    m = ""
                m += new_line
            if m != "":
                await res.channel.send(m)
                await res.channel.send("Member count: " + str(count))
            else:
                await res.channel.send("No active memberships!")
            return

        # Check if zoopass in database and delete
        target_membership = db["members"].find_one({"id": member_id})
        if not target_membership:
            await res.channel.send(self.ID_NOT_FOUND_TEXT)
            return
        
        # Send information about membership
        guild = self.bot.get_guild(res.guild.id)
        target_member = guild.get_member(member_id)

        membership_date = target_membership["last_membership"].replace(tzinfo = timezone.utc)
        expiration_date = membership_date + relativedelta(months=1)

        ## change dates to strings
        membership_date = membership_date.strftime(self.DATE_FORMAT)
        expiration_date = expiration_date.strftime(self.DATE_FORMAT)

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

    async def verify_membership_with_server_detection(self, res):

            server = None
            try:
                idol, server = await self.detect_idol_server(res.attachments[0].url)
            except Exception:
                pass

            if not server:
                m = "I am sorry I could not detect a VTuber name on the image you sent earlier.\n"
                m += "Please send a screenshot with the name of the VTuber on it.\n"
                m+= "If this was the case, please use `$verify <VTuber name>` instead of the normal $verify.\n"
                m += "You might need to wait as there is a cooldown on this command to avoid spam."
                embed = Utility.create_supported_vtuber_embed()
                await res.channel.send(content = m, embed = embed)
                return
            await self.verify_membership(res, server)



    async def detect_idol_server(self, url):
        # get list from db
        idols = self.db_cluster["settings"]['general'].find_one({'name': "supported_idols"})['supported_idols']
        
        text, inverted_text = await asyncio.wait_for(OCR.detect_image_text(url), timeout = 60)
        
        for idol in idols:
            if idol['name'] in text.lower() or idol['name'] in inverted_text.lower():
                return (idol['name'], idol['guild_id'])


    async def detect_membership_date(self, res):
        img_date = None
        # check date
        try:
            img_date = await OCR.detect_image_date(res.attachments[0].url)

        except asyncio.TimeoutError:
            print("timeout error detecting image")
        except Exception:
            print("date detection fail!!")

        if img_date:
            return (img_date)


    async def verify_membership(self, res, server_id):

        guild = self.bot.get_guild(server_id)
        server_db = self.db_cluster[str(server_id)]
        member_collection = server_db["members"]

        # if member exists, update date
        member = member_collection.find_one({"id": res.author.id})

        new_membership_date = await self.detect_membership_date(res)


        if not new_membership_date:
            print(str(server_id) + ": date detection failed")
            desc = "{}\n{}".format(str(res.author), "Date not detected")
            membership_date_text = "None"
        else:

            membership_date_text = new_membership_date.strftime(self.DATE_FORMAT)
            desc = "{}\n{}".format(str(res.author), membership_date_text)

            #substract month for db
            new_membership_date = new_membership_date  - relativedelta(months=1)

        

        #verification channel of the server
        member_veri_ch = self.bot.get_channel(server_db["settings"].find_one({"kind": "log_channel"})["value"])
        
        FORGOTTEN_SETTINGS_TEXT = "Please contact the staff of your server, they forgot to set some settings"
        
        if not member_veri_ch:
            res.channel.send(FORGOTTEN_SETTINGS_TEXT)
            return

        automatic_role = server_db["settings"].find_one({"kind": "automatic_role"})["value"]

        require_additional_proof = server_db["settings"].find_one({"kind": "require_additional_proof"})["value"]

        title = res.author.id
        embed = discord.Embed(title = title, colour = self.embed_color)

        if require_additional_proof:
            m = "This server requires you to send additional proof.\n"
            m += "Please send a screenshot as specified by them."
            await res.channel.send(m)

            def check(m):
                return len(m.attachments) > 0
            try:
                proof_msg = await self.bot.wait_for('message', timeout=60, check=check)
            except asyncio.TimeoutError:
                await res.channel.send("I am sorry, you timed out. Please start the verify process again.")
                return

            # if overtime, send timeout message and return
            embed.description = "Additional proof"
            embed.set_image(url = proof_msg.attachments[0].url)
            await member_veri_ch.send(content=None, embed = embed)

        # Send attachment and message to membership verification channel
        
        embed.description = "Main Proof"
        embed.add_field(name="Recognized Date", value = membership_date_text)
        embed.set_image(url = res.attachments[0].url)
        message = await member_veri_ch.send(content = "```\n{}\n```".format(desc), embed = embed)
        await message.add_reaction(emoji='✅')
        await message.add_reaction(emoji=u"\U0001F6AB")


        # should not get the role yet
        if not new_membership_date:
            return

        # automatic role not allowed
        if not automatic_role:
            return

        if member:
            last_membership = member["last_membership"].replace(tzinfo = timezone.utc)
            member_collection.update_one({"id": res.author.id}, {"$set": {"last_membership": max(new_membership_date, last_membership), "informed": False, "expiry_sent": False}})

        # if not, create data
        else:
            member_collection.insert_one({
                "id": res.author.id,
                "last_membership": new_membership_date,
                "informed": False,
                "expiry_sent": False
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


    async def set_membership(self, res, member_id, date):
        
        member_collection = self.db_cluster[str(res.guild.id)]['members']
        # Check if id exists
        target_membership = member_collection.find_one({"id": member_id})
        dates = date.split("/")

        if len(dates)!=3 or any(not Utility.is_integer(date) for date in dates):
                await res.channel.send("Please provide a valid date (dd/mm/yyyy) or integer days (+/- integer).")
                return
        new_date = dtime(year = int(dates[2]), month = int(dates[1]), day = int(dates[0]), tzinfo = timezone.utc)

        db_date = new_date - relativedelta(months=1)
        if not target_membership:
                #needs to be date for new entry
                await res.channel.send("Creating new entry!")
                member_collection.insert_one({
                    "id": member_id,
                    "last_membership": db_date,
                    "informed": False,
                    "expiry_sent": False
                })
        else:
            self.db_cluster[str(res.guild.id)]['members'].update_one({"id": member_id}, {"$set": {"last_membership": db_date, "informed": False, "expiry_sent": False}})

        server_db = self.db_cluster[str(res.guild.id)]


        target_member = res.guild.get_member(member_id)
        role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
        role = res.guild.get_role(role_id)
        await target_member.add_roles(role)

        await target_member.send("Your have been granted access to the membership channel of {}.".format(Utility.get_vtuber(res.guild.id)))

        await res.channel.send("New membership date for {} set at {}!".format(member_id, new_date.strftime(self.DATE_FORMAT)), reference=res, mention_author=False)
        

    async def del_membership(self, res, member_id: int, text, dm_flag=True):
        
        member_id = int(member_id)

        server_db = self.db_cluster[str(res.guild.id)]

        # Check if zoopass in database and delete
        target_membership = server_db['members'].find_one({"id": member_id})
        if not target_membership:
            await res.channel.send(self.ID_NOT_FOUND_TEXT)
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

        if dm_flag:
            # If msg has extra lines, send dm to target user to notify the zoopass deletion
            if text:
                await target_member.send(" ".join(text))
            else:
                await target_member.send("Your membership for " + Utility.get_vtuber(res.guild.id) + " was deleted!")

    async def delete_expired_memberships(self, forced=False):
        
        overall_settings = self.db_cluster["settings"]['general']

        # get data of last checked timestamp
        now = dtime.now(tz = timezone.utc)
        last_checked = overall_settings.find_one({"name": "member_check"}).get("last_checked", None)

        #get all active servers
        serverlist = overall_settings.find_one({'name': "supported_idols"})['supported_idols']

        #execute for every server
        for server in serverlist:
            server_db = self.db_cluster[str(server['guild_id'])]
            lg_ch = self.bot.get_channel(server_db['settings'].find_one({'kind': "log_channel"})['value'])
            logging = server_db['settings'].find_one({'kind': "logging"})['value']

            if logging:
                if not forced:
                    await lg_ch.send("Performing membership check, last check was {}".format(last_checked))
                else:
                    await lg_ch.send("Forced Membership check")

            # perform check
            expired_memberships = await self._check_membership_dates(server)
            content = ["{}: {}".format(d["id"], d["last_membership"]) for d in expired_memberships]
            m = "Expired Memberships:\n"
            m += "\n".join(content)
            if m:
                await lg_ch.send(m)

            # add wait time
            overall_settings.update_one({"name": "member_check"}, {"$set": {"last_checked": now}})
        
    async def check_membership_routine(self):
        while not self.bot.is_closed():
            now = dtime.now(tz = timezone.utc)
            last_checked = self.db_cluster["settings"]['general'].find_one({"name": "member_check"}).get("last_checked", None)

            # if there is no last checked, or last checked is more than 12 hours ago, do new check
            if last_checked:
                # add utc to last checked (mongodb always naive)
                last_checked = last_checked.replace(tzinfo = timezone.utc)

            if not last_checked or (now - last_checked >= timedelta(hours = 12)):
                await self.delete_expired_memberships()
                wait_time = 12 * 3600
            else:
                # else wait for the remaining time left
                wait_time = 12 * 3600 - (now - last_checked).total_seconds()
            await asyncio.sleep(wait_time)

    async def handle_verifies(self):
        await self.bot.wait_until_ready()
        # check if new tweet found
        while not self.bot.is_closed():
            while self.verify_deque:
                verify = self.verify_deque.popleft()
                if verify[1]:
                    await self.verify_membership(verify[0], verify[1])
                else:
                    await self.verify_membership_with_server_detection(verify[0])

            await asyncio.sleep(10) # check all 10 seconds