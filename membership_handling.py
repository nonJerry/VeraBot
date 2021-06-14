#External
import discord
#Python
import asyncio
from datetime import datetime as dtime, date, time, tzinfo
from datetime import timezone, timedelta
from dateutil.relativedelta import relativedelta
from collections import deque
import logging
import gc
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

    async def add_to_queue(self, res, server_id=None, lang="eng"):
        
        # Check if there is a valid attachment
        if not res.attachments:
            await res.channel.send(self.NO_PICTURE_TEXT.format(res.author))
            logging.info("Verify without screenshot from %s.", res.author.id)
            return
        self.verify_deque.append([res, server_id, lang])
        logging.info("Proof from %s added to queue for server: %s", res.author.id, server_id)

        m = "Your proof is added to the queue now and will be processed later.\n"
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
        expiry_date = dtime.now(tz = timezone.utc) - relativedelta(months=1) - timedelta(days=1)
        notify_date = expiry_date + timedelta(days=inform_duration)
        tolerance_date = expiry_date - timedelta(days=tolerance_duration)

        message_title = idol + " Membership {}!"
        end_text = "You may renew your membership by sending another updated verification photo using the ``$verify`` command."
        end_text += "Thank you so much for your continued support!"
        message_image = server_db['settings'].find_one({'kind': "picture_link"})['value']

        #TODO: Restructure DB after dates?
        for member in server_db['members'].find():
            try:
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

                        if target_member:
                            role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
                            member_role = guild.get_role(role_id)

                            await target_member.remove_roles(member_role)
                            #send dm
                            await Sending.dm_member(member["id"], title, message_desc.format(idol.title(), str(inform_duration)), embed = True, attachment_url = message_image)
                    # notify
                    elif inform_duration != 0 and last_membership <= notify_date and not member['informed']:
                        title = message_title.format("expires soon!")
                        message_desc = "Your membership to {} will expire within the next {} hours.\n"
                        message_desc += "If you do not want to lose this membership please don't forget to anew it!"
                        await Sending.dm_member(member["id"], title, message_desc.format(idol.title(), str(inform_duration * 24)), embed = True, attachment_url = message_image)

                        server_db['members'].update_one({"id": member['id']}, {"$set": {"informed": True}})

                if not last_membership or (last_membership <= expiry_date and not member['expiry_sent'] and tolerance_date < last_membership):
                    title = message_title.format("expired")
                    message_desc = "Your membership to {} should have expired today!\n"
                    message_desc += "If your billing date has not changed yet, please wait until it does to send your new proof.\n"
                    message_desc += "You will lose your access to the channel after {} day(s) if you do not renew your membership.\n"
                    message_desc += end_text
                
                    # Add to delete list
                    expired_memberships.append(member)

                    # dm expired membership
                    await Sending.dm_member(member["id"], title, message_desc.format(idol.title(), str(tolerance_duration)), embed = True, attachment_url = message_image)

                    server_db['members'].update_one({"id": member['id']}, {"$set": {"expiry_sent": True}})
            except discord.errors.Forbidden:
                logging.warn("Could not send DM to %s", member["id"])

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
                membership_date = membership_date.strftime(self.DATE_FORMAT)
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

    async def verify_membership_with_server_detection(self, res, lang):

        server = None
        try:
            idol, server = await self.detect_idol_server(res.attachments[0].url)
        except Exception:
            logging.info("Could not detect server for %s.", res.author.id)

        if not server:
            m = "I am sorry I could not detect a VTuber name on the image you sent earlier.\n"
            m += "Please send a screenshot with the name of the VTuber on it.\n"
            m+= "If this was the case, please use `$verify <VTuber name>` instead of the normal $verify.\n"
            m += "You might need to wait as there is a cooldown on this command to avoid spam."
            embed = Utility.create_supported_vtuber_embed()
            await res.channel.send(content = m, embed = embed)
            return

        logging.info("Detected server for %s: %s (%s)", res.author.id, idol, server)
        await self.verify_membership(res, server, lang)



    async def detect_idol_server(self, url):
        # get list from db
        idols = self.db_cluster["settings"]['general'].find_one({'name': "supported_idols"})['supported_idols']
        
        text, inverted_text = await asyncio.wait_for(OCR.detect_image_text(url), timeout = 60)
        
        for idol in idols:
            if idol['name'].title() in text or idol['name'].title() in inverted_text:
                return (idol['name'], idol['guild_id'])


    async def detect_membership_date(self, res, lang):
        img_date = None
        # check date
        try:
            img_date = await OCR.detect_image_date(res.attachments[0].url, lang)

        except asyncio.TimeoutError:
            logging.info("Timout while detecting image for %s.", res.author.id)
        except Exception:
            logging.exception("Date detection failed for %s.", res.author.id)

        if img_date:
            return (img_date)


    async def verify_membership(self, res, server_id, lang):

        guild = self.bot.get_guild(server_id)
        server_db = self.db_cluster[str(server_id)]
        member_collection = server_db["members"]

        # if member exists, update date
        member = member_collection.find_one({"id": res.author.id})

        new_membership_date = await self.detect_membership_date(res, lang)


        if not new_membership_date:
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
            logging.info("Requiring additional proof from %s for server %s.", res.author.id, server_id)

            def check(m):
                return len(m.attachments) > 0 and m.author == res.author and isinstance(m.channel, discord.DMChannel)
            try:
                proof_msg = await self.bot.wait_for('message', timeout=60, check=check)
            except asyncio.TimeoutError:
                logging.info("%s took to long with the proof.", res.author.id)
                await res.channel.send("I am sorry, you timed out. Please start the verify process again.")
                return

            # if overtime, send timeout message and return
            embed.description = "Additional proof"
            embed.set_image(url = proof_msg.attachments[0].url)
            await member_veri_ch.send(content=None, embed = embed)

        # Send attachment and message to membership verification channel
        
        embed.description = "Main Proof\nUser: {}".format(res.author.mention)
        embed.add_field(name="Recognized Date", value = membership_date_text)
        embed.set_image(url = res.attachments[0].url)
        message = await member_veri_ch.send(content = "```\n{}\n```".format(desc), embed = embed)
        await message.add_reaction(emoji='✅')
        await message.add_reaction(emoji=u"\U0001F4C5") # calendar
        await message.add_reaction(emoji=u"\U0001F6AB") # no entry
        logging.info("Sent embed with reactions to %s", server_id)


        # should not get the role yet
        if not new_membership_date:
            logging.info("Date for %s on server %s was missing.", res.author.id, server_id)
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
        if author:
            logging.info("Adding role automatically for %s on server %s", res.author.id, server_id)

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
        else:
            logging.info("%s is not part of server %s", res.author.id, server_id)
            await res.channel.send("You are not part of this server!")


    async def set_membership(self, res, member_id, date, manual=True, actor=None) -> bool:
        
        member_collection = self.db_cluster[str(res.guild.id)]['members']
        dates = date.split("/")

        if len(dates)!=3 or any(not Utility.is_integer(date) for date in dates):
            logging.info("%s used a wrong date format to set the membership.", res.author.id)

            await res.channel.send("Please provide a valid date (dd/mm/yyyy) or integer days (+/- integer).")
            return False
        new_date = dtime(year = int(dates[2]), month = int(dates[1]), day = int(dates[0]), tzinfo = timezone.utc)
        db_date = new_date - relativedelta(months=1)

        # Check if id exists
        target_membership = member_collection.find_one({"id": member_id})
        if not target_membership:
            logging.info("Creating new membership for %s on server %s with last membership: %s.", member_id, res.guild.id, db_date)
            member_collection.insert_one({
                "id": member_id,
                "last_membership": db_date,
                "informed": False,
                "expiry_sent": False
            })
        else:
            logging.info("Updating membership for %s on server %s with last membership: %s.", member_id, res.guild.id, db_date)
            self.db_cluster[str(res.guild.id)]['members'].update_one({"id": member_id}, {"$set": {"last_membership": db_date, "informed": False, "expiry_sent": False}})

        server_db = self.db_cluster[str(res.guild.id)]

        await asyncio.sleep(0.21)
        target_member = res.guild.get_member(member_id)
        role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
        role = res.guild.get_role(role_id)
        await target_member.add_roles(role)
        logging.info("Added member role to user %s on server %s.", member_id, res.guild.id)

        await asyncio.sleep(0.21)
        await target_member.send("You have been granted access to the membership channel of {}.".format(Utility.get_vtuber(res.guild.id)))

        await asyncio.sleep(0.21)
        if manual:
            await res.channel.send("New membership date for {} set at {}!".format(target_member.mention, new_date.strftime(self.DATE_FORMAT)), reference=res, mention_author=False)
        else:
            embed = res.embeds[0]
            embed.description = "**VERIFIED:** {}\nUser: {}\nBy: {}".format(new_date.strftime(self.DATE_FORMAT), target_member.mention, actor.mention)
            await res.edit(content = res.content, embed = embed)
        return True
        

    async def del_membership(self, res, member_id: int, text, dm_flag=True, manual=True):
        
        member_id = int(member_id)

        server_db = self.db_cluster[str(res.guild.id)]

        # Check if zoopass in database and delete
        target_membership = server_db['members'].find_one({"id": member_id})
        if not target_membership:
            logging.info("Requested user does not have membership; by %s.", res.author.id)
            await res.channel.send(self.ID_NOT_FOUND_TEXT)
            return
        await res.channel.send("Found membership in database, deleting now!")
        server_db['members'].delete_one(target_membership)

        logging.info("Deleted membership on %s: %s", res.guild.id, target_membership)

        # Remove zoopass role from user
        guild = res.guild
        target_member = guild.get_member(member_id)

        role_id = server_db["settings"].find_one({"kind": "member_role"})["value"]
        role = guild.get_role(role_id)

        if target_member:
            await target_member.remove_roles(role)
            logging.info("Removing role from %s on server %s.", target_membership, res.guild.id)

            if manual:
                await res.channel.send("Membership successfully deleted.")

            if dm_flag:
                # If msg has extra lines, send dm to target user to notify the zoopass deletion
                if text:
                    await target_member.send(" ".join(text))
                else:
                    await target_member.send("Your membership for " + Utility.get_vtuber(res.guild.id) + " was deleted!")
        else:
            res.channel.send("User is not on this server!")
            logging.info("%s not on server %s.", target_membership, res.guild.id)

    async def delete_expired_memberships(self, forced=False):
        
        overall_settings = self.db_cluster["settings"]['general']

        # get data of last checked timestamp
        last_checked = overall_settings.find_one({"name": "member_check"}).get("last_checked", None)

        #get all active servers
        serverlist = overall_settings.find_one({'name': "supported_idols"})['supported_idols']

        #execute for every server
        for server in serverlist:
            logging.info("Checking Memberships for %s.", server['guild_id'])

            server_db = self.db_cluster[str(server['guild_id'])]
            lg_ch = self.bot.get_channel(server_db['settings'].find_one({'kind': "log_channel"})['value'])
            logging_enabled = server_db['settings'].find_one({'kind': "logging"})['value']

            expired_memberships = await self._check_membership_dates(server)

            if logging_enabled:
                if not forced:
                    await lg_ch.send("Performing membership check, last check was {}".format(last_checked))
                else:
                    await lg_ch.send("Forced Membership check")

                content = ["{}".format(d["id"]) for d in expired_memberships]
                count = 0
                m = "Expired Memberships:"
                for member in content:
                    count += 1
                    new_line = '\n' + member
                    if len(m) + len(new_line) > 2000:
                        await lg_ch.send(m)
                        m = ""
                    m += new_line

                if count != 0:
                    # send ids if there are some
                    if m != "":
                        await lg_ch.send(m)
                    # send count
                    await lg_ch.send("Expired membership count: " + str(count))
                else:
                    await lg_ch.send("No expired memberships!")


        # add wait time
        dt = date.today()
        today = dtime.combine(dt, time(12, 0, 0, tzinfo = timezone.utc))
        overall_settings.update_one({"name": "member_check"}, {"$set": {"last_checked": today}})
        logging.info("Set last membership check to %s.", today)
        
    async def check_membership_routine(self):
        while not self.bot.is_closed():
            now = dtime.now(tz = timezone.utc)
            last_checked = self.db_cluster["settings"]['general'].find_one({"name": "member_check"}).get("last_checked", None)

            # if there is no last checked, or last checked is more than 12 hours ago, do new check
            if last_checked:
                # add utc to last checked (mongodb always naive)
                last_checked = last_checked.replace(tzinfo = timezone.utc)

            if not last_checked or (now - last_checked >= timedelta(hours = 24)):
                logging.info("Checking memberships!")
                await self.delete_expired_memberships()

            wait_time = 24 * 3600 - (now - last_checked).total_seconds()
            logging.info("Waiting for %s seconds to next membership check.", wait_time)
            await asyncio.sleep(wait_time)

    async def handle_verifies(self):
        # check if new tweet found
        while not self.bot.is_closed():
            try:
                while self.verify_deque:
                    verify = self.verify_deque.popleft()
                    if verify[1]:
                        await self.verify_membership(verify[0], verify[1], verify[2])
                    else:
                        await self.verify_membership_with_server_detection(verify[0], verify[2])
                    del verify
                gc.collect()
                await asyncio.sleep(10) # check all 10 seconds
            except Exception:
                logging.exception("Catched error in deque")

    async def process_reaction(self, channel, msg, user, reaction):
        emoji = reaction.emoji
        embed = msg.embeds[0]
        automatic_role = self.db_cluster[str(msg.guild.id)]["settings"].find_one({"kind": "automatic_role"})["value"]
        bot = self.bot

        
        # always only the id
        target_member_id = int(embed.title)

        # correct date
        if emoji == '✅':
            logging.info("Recognized date correct in %s for user %s.", channel.guild.id, target_member_id)
            
            if not automatic_role:
                membership_date = embed.fields[0].value

                # set membership
            if await self.set_membership(msg, target_member_id, membership_date, False, user):
            #always clear
                await asyncio.sleep(0.21)
                await msg.clear_reactions()
                await asyncio.sleep(0.21)
                await msg.add_reaction(emoji='👌')
        # wrong date
        elif emoji == u"\U0001F4C5":
            logging.info("Wrong date recognized in %s for user %s.", channel.guild.id, target_member_id)

            m = "Please write the correct date from the screenshot in the format dd/mm/yyyy.\n"
            m += "Type CANCEL to stop the process."
            await channel.send(m, reference=msg, mention_author=False)
            def check(m):
                return m.author == user and m.channel == channel

            date_msg = await bot.wait_for('message', check=check)

            if date_msg.content.lower() != "cancel" and await self.set_membership(msg, target_member_id, date_msg.content, False, user):
                await msg.clear_reactions()
                await asyncio.sleep(0.21)
                await msg.add_reaction(emoji='👍')
            else:
                logging.info("Canceled reaction by user %s in %s.", user.id, channel.guild.id)
                await reaction.remove(user)
                await asyncio.sleep(0.21)
                await channel.send("Stopped the process and removed reaction.")

        # deny option - fake / missing date
        elif emoji == u"\U0001F6AB":
            logging.info("Fake or without date in %s for user %s.", channel.guild.id, target_member_id)

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

                if automatic_role:
                    await self.del_membership(msg, target_member_id, None, False, False)
                # set embed
                embed.description = "**DENIED**\nUser: {}\nBy: {}".format(target_member.mention, user)
                await msg.edit(content = msg.content, embed = embed)
                await asyncio.sleep(0.21)
                await msg.clear_reactions()
                await msg.add_reaction(emoji='👎')
            else:
                logging.info("Canceled reaction by user %s in %s.", user.id, channel.guild.id)
                await reaction.remove(user)
                await channel.send("Stopped the process and removed reaction.")