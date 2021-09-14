#External
from typing import List, Optional, Tuple

from database import Database, Member
import discord
#Python
import asyncio
from datetime import datetime as dtime, date, time
from datetime import timezone, timedelta
from dateutil.relativedelta import relativedelta
from collections import deque
import logging
import gc

from discord.enums import ChannelType
#Internal
from utility import Utility
from ocr import OCR
from sending import Sending

class MembershipHandler:
    def __init__(self, bot, embed_color):
        self.ID_NOT_FOUND_TEXT = "Can't find membership id in the database!"
        self.DATE_FORMAT = r"%d/%m/%Y"

        self.bot = bot
        self.db = Database()
        self.embed_color = embed_color
        # deque for data
        self.verify_deque = deque()

    async def add_to_queue(self, res, server_id=None, lang="eng"):
        
        # Check if there is a valid attachment
        self.verify_deque.append([res, server_id, lang])
        logging.info("Proof from %s added to queue for server: %s", res.author.id, server_id)

        m = "Your proof has been added to the queue and will be processed later.\n"
        m += "You will get a message when your role is applied."
        await res.channel.send(m)

    async def _check_membership_dates(self, server: dict, purge = False) -> List[Member]:
        # Performs a mass check on membership dates and delete expired membership with a default message
        # Returns an expired_membership list {id, last_membership}

        server_db= self.db.get_server_db(server['guild_id'])
        idol = server['name']


        inform_duration = server_db.get_inform_duration()
        tolerance_duration = server_db.get_tolerance_duration()

        expired_memberships = []
        expiry_date = dtime.now(tz = timezone.utc) - relativedelta(months=1)

        if purge:
            tolerance_date = expiry_date
        else:
            expiry_date = expiry_date - timedelta(days=1)
            tolerance_date = expiry_date - timedelta(days=tolerance_duration)
        notify_date = expiry_date + timedelta(days=inform_duration)

        message_title = idol.title() + " Membership {}!"
        end_text = "You may renew your membership by sending another updated verification photo using the ``$verify`` command.\n"
        end_text += "Thank you so much for your continued support!"
        if purge:
            end_text = "This expiration may be too soon. It was initiated by the server to avoid illegit access during e.g. a membership stream.\n"

        message_image = server_db.get_picture()

        # only needs to check those that are already expired to save ressources
        for member in server_db.get_members(only_expired=True):
            try:
                # For each member
                last_membership = member.last_membership
                # need to remove role?
                if last_membership <= tolerance_date:
                    title = message_title.format("channel access ended")
                    message_desc = "You lost your access to {}'s members-only channel!\n"
                    message_desc += end_text

                    # Delete from database
                    server_db.remove_member(member)

                    # Remove member role from user
                    guild = self.bot.get_guild(server['guild_id'])
                    target_member = guild.get_member(member.id)

                    if target_member:
                        role_id = server_db.get_member_role()
                        member_role = guild.get_role(role_id)

                        await target_member.remove_roles(member_role)
                        #send dm
                        await Sending.dm_member(member.id, title, message_desc.format(idol.title(), str(inform_duration)), embed = True, attachment_url = message_image)

                        if purge:
                            expired_memberships.append(member)
                
                # else notify
                elif inform_duration != 0 and last_membership <= notify_date and not member.informed:
                    title = message_title.format("expires soon!")
                    message_desc = "Your membership to {} will expire within the next {} hours.\n"
                    message_desc += "If you do not want to lose this membership please don't forget to renew it!"
                    await Sending.dm_member(member.id, title, message_desc.format(idol.title(), str(inform_duration * 24)), embed = True, attachment_url = message_image)

                    server_db.informed(member)

                elif last_membership <= expiry_date and not member.expiry_sent:
                    title = message_title.format("expired")
                    message_desc = "Your membership to {} should have expired today!\n"
                    message_desc += "If your billing date has not changed yet, please wait until it does to send your new proof.\n"
                    message_desc += "You will lose your access to the channel after {} day(s) if you do not renew your membership.\n"
                    message_desc += end_text
                
                    # Add to delete list
                    expired_memberships.append(member)

                    # dm expired membership
                    await Sending.dm_member(member.id, title, message_desc.format(idol.title(), str(tolerance_duration)), embed = True, attachment_url = message_image)

                    server_db.expiry_sent(member)

            except discord.errors.Forbidden:
                logging.warn("Could not send DM to %s", member.id)
                member_veri_ch = self.bot.get_channel(server_db.get_log_channel())
                user = self.bot.get_user(member.id)
                await member_veri_ch.send("Could not send reminder to {}.".format(user.mention))


        # Returns expired_memberships list
        return expired_memberships


    async def view_membership(self, res, member_id=None):
        # if msg is empty, show all members
        server_db = self.db.get_server_db(res.guild.id)

        if not member_id:
            count = 0
            m = ""
            for member in server_db.get_members():
                count += 1
                member_id = member.id
                membership_date = member.last_membership + relativedelta(months=1)
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
        target_membership = server_db.get_member(member_id)
        if not target_membership:
            await res.channel.send(self.ID_NOT_FOUND_TEXT)
            return
        
        # Send information about membership
        guild = self.bot.get_guild(res.guild.id)
        target_member = guild.get_member(member_id)

        membership_date = target_membership.last_membership
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
        "informed": bool
        "expiry_sent": bool
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
        if Utility.is_user_on_server(res.author.id, server):
            await self.verify_membership(res, server, lang)
        else:
            logging.info("%s tried to verify for a server they are not on.", res.author.id)
            await res.channel.send("You are not on {} server!".format(idol.title()))



    async def detect_idol_server(self, url) -> Optional[Tuple[str, int]]:
        # get list from db
        idols = self.db.get_vtuber_list()
        
        text, inverted_text = await asyncio.wait_for(OCR.detect_image_text(url, "eng"), timeout = 60)
        
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
        server_db = self.db.get_server_db(server_id)

        # if member exists, update date
        member = server_db.get_member(res.author.id)

        new_membership_date = await self.detect_membership_date(res, lang)

        new_membership_date, membership_date_text, desc = self.process_date(res, new_membership_date)
        

        threads_enabled = server_db.get_threads_enabled()
        # check if permissions are okay
        if threads_enabled:
            if self.bot.get_cog('Settings').check_thread_permissions(server_id):
                member_veri_ch = self.bot.get_channel(server_db.get_proof_channel())
            else:
                logging.info("%s: Has Threads enabled but perms are missing.", server_id)
        else:
            #verification channel of the server
            member_veri_ch = self.bot.get_channel(server_db.get_log_channel())
            
        
        if not member_veri_ch:
            res.channel.send("Please contact the staff of your server, they forgot to set some settings")
            return

        automatic_role = server_db.get_automatic()

        title = res.author.id
        embed = discord.Embed(title = title, colour = self.embed_color)

        #create thread if setting enabled
        if threads_enabled:
            member_veri_ch = await member_veri_ch.create_thread(name="Proof: {}".format(res.author.name), type=ChannelType.public_thread)

        try:
            if server_db.get_additional_proof():
                proof_url = await self.handle_additional_proof(res, server_id)
                embed.description = "Additional proof"
                embed.set_image(url = proof_url)
                await member_veri_ch.send(content=None, embed = embed)
                await res.channel.send("Your additional proof was delivered to the server, please wait for the staff to check your proof.")
        # if overtime, send timeout message and return
        except asyncio.TimeoutError:
            logging.info("%s took to long with the proof.", res.author.id)
            await res.channel.send("I am sorry, you timed out. Please start the verify process again.")
            return

        # Send attachment and message to membership verification channel
        
        embed.description = "Main Proof\nUser: {}".format(res.author.mention)
        embed.add_field(name="Recognized Date", value = membership_date_text)
        embed.set_image(url = res.attachments[0].url)
        message = await member_veri_ch.send(content = "```\n{}\n```".format(desc), embed = embed)
        await message.add_reaction(emoji='✅')
        await message.add_reaction(emoji=u"\U0001F4C5") # calendar
        await message.add_reaction(emoji=u"\U0001F6AB") # no entry
        logging.info("Sent embed with reactions to %s", server_id)



        # starting here only if automatic role is enabled
        if not automatic_role:
            return

        # no date = no automatic role/manual judgement needed
        if not new_membership_date:
            logging.info("Date for %s on server %s was missing.", res.author.id, server_id)
            return

        # no need to update if new date is not newer
        if member and new_membership_date < member.last_membership:
            return

        await self.handle_role(res, server_id, new_membership_date)

    async def handle_role(self, res, server_id, new_membership_date):
        guild = self.bot.get_guild(server_id)
        author = guild.get_member(res.author.id)

        # if author not part of guild do nothing
        if author:
            server_db = self.db.get_server_db(server_id)
            logging.info("Adding role automatically for %s on server %s", res.author.id, server_id)

            role_id = server_db.get_member_role()
            role = guild.get_role(role_id)

            if not role:
                res.channel.send("Please contact the staff of your server, they forgot to set a membership role")
                return
            
            # add role and update db entry
            server_db.update_member(res.author.id, new_membership_date)
            await author.add_roles(role)

            # DM user that the verification process is complete
            m = "Membership applied! You now have access to members-excusive content in the server."
            m += "\nPlease note that our staff will double-confirm the verification photo and may revoke it on a case-by-case basis."
            m += "\nIf you have encountered any issue with accessing the channels or have a separate enquiry, please contact a mod."
            await res.channel.send(m)
        else:
            logging.info("%s is not part of server %s", res.author.id, server_id)
            await res.channel.send("You are not part of this server!")


    async def handle_additional_proof(self, res, server_id):
            m = "This server requires you to send additional proof.\n"
            m += "Please send a screenshot as specified by them."
            await res.channel.send(m)
            logging.info("Requiring additional proof from %s for server %s.", res.author.id, server_id)

            # check if message by user
            def check(m):
                return len(m.attachments) > 0 and m.author == res.author and isinstance(m.channel, discord.DMChannel)
            
            # wait for message by user
            proof_msg = await self.bot.wait_for('message', timeout=60, check=check)
            
            return proof_msg.attachments[0].url

    def process_date(self, res, new_membership_date) -> Tuple[dtime, str, str]:
        if not new_membership_date:
            desc = "{}\n{}".format(str(res.author), "Date not detected")
            membership_date_text = "None"
        else:
            membership_date_text = new_membership_date.strftime(self.DATE_FORMAT)
            desc = "{}\n{}".format(str(res.author), membership_date_text)

            #substract month for db
            new_membership_date = new_membership_date  - relativedelta(months=1)

        return (new_membership_date, membership_date_text, desc)


    async def set_membership(self, res, member_id, date, manual=True, actor=None) -> bool:
        dates = date.split("/")

        if len(dates)!=3 or any(not Utility.is_integer(date) for date in dates):
            logging.info("%s used a wrong date format to set the membership.", res.author.id)

            await res.channel.send("Please provide a valid date (dd/mm/yyyy).")
            return False
        try:
            new_date = dtime(year = int(dates[2]), month = int(dates[1]), day = int(dates[0]), tzinfo = timezone.utc)
        except ValueError:
            logging.info("%s used a invalid number for the date to set the membership.", res.author.id)
            await res.channel.send("Your date was not valid. Please use the format dd/mm/yyyy")
            return False

        target_member = res.guild.get_member(member_id)

        # stop if user not on server
        if not target_member:
            await res.channel.send("{} is not on this server!".format(target_member.mention), reference=res, mention_author=False)
            return True

        db_date = new_date - relativedelta(months=1)
        server_db = self.db.get_server_db(res.guild.id)

        # update/create member in db
        server_db.update_member(member_id, db_date)
        
        role_id = server_db.get_member_role()
        role = res.guild.get_role(role_id)
        await target_member.add_roles(role)
        logging.info("Added member role to user %s on server %s.", member_id, res.guild.id)

        await asyncio.sleep(0.21)
        await target_member.send("You have been granted access to the membership channel of {}.".format(server_db.get_vtuber()))

        await asyncio.sleep(0.21)
        if manual:
            await res.channel.send("New membership date for {} set at {}!".format(target_member.mention, new_date.strftime(self.DATE_FORMAT)), reference=res, mention_author=False)
        else:
            embed = res.embeds[0]
            embed.description = "**VERIFIED:** {}\nUser: {}\nBy: {}".format(new_date.strftime(self.DATE_FORMAT), target_member.mention, actor.mention)
            await res.edit(content = res.content, embed = embed)
        return True
        

    async def del_membership(self, res, member_id: int, text, dm_flag=True, manual=True):
        server_db = self.db.get_server_db(res.guild.id)

        # Delete from db
        if server_db.remove_member(member_id) == 0:
            logging.info("Requested user does not have membership; by %s.", res.author.id)
            await res.channel.send(self.ID_NOT_FOUND_TEXT)
            return
        logging.info("Deleted membership on %s: %s", res.guild.id, member_id)

        # Remove member role from user
        guild = res.guild
        target_member = guild.get_member(member_id)

        role_id = server_db.get_member_role()
        role = guild.get_role(role_id)

        if target_member:
            try: 
                await target_member.remove_roles(role)
                logging.info("Removing role from %s on server %s.", member_id, res.guild.id)

                if manual:
                    await res.channel.send("Membership successfully deleted.")

                if dm_flag:
                    # If msg has extra lines, send dm to target user to notify the zoopass deletion
                    if text:
                        await target_member.send(" ".join(text))
                    else:
                        await target_member.send("Your membership for " + server_db.get_vtuber() + " was deleted!")
            except (discord.errors.Forbidden, discord.HTTPException):
                res.channel.send("Removing the role failed, please remove the role manually and check my permissions.")
        else:
            res.channel.send("User is not on this server!")
            logging.info("%s not on server %s.", member_id, res.guild.id)

    async def purge_memberships(self, server_id: int):
        server = {'guild_id': server_id, 'name': self.db.get_vtuber(server_id)}
        lg_ch = self.bot.get_channel(self.db.get_server_db(server_id).get_log_channel())

        expired_memberships = await self._check_membership_dates(server, purge=True)

        content = ["{}".format(d.id) for d in expired_memberships]
        await self.send_expired_info(lg_ch, content)


    async def delete_expired_memberships(self, forced=False):
        # get data of last checked timestamp
        last_checked = self.db.get_last_checked()

        #get all active servers
        serverlist = self.db.get_vtuber_list()

        #execute for every server
        for server in serverlist:
            server_id = server['guild_id']
            logging.info("Checking Memberships for %s.", server_id)

            server_db = self.db.get_server_db(server_id)
            logging_enabled = server_db.get_logging()
            expired_memberships = await self._check_membership_dates(server)

            if logging_enabled:
                lg_ch = self.bot.get_channel(server_db.get_log_channel())
                try:
                    if not forced:
                        await lg_ch.send("Performing membership check, last check was {}".format(last_checked))
                    else:
                        await lg_ch.send("Forced Membership check")

                    content = ["{}".format(d.id) for d in expired_memberships]
                    await self.send_expired_info(lg_ch, content)
                    
                except discord.errors.Forbidden:
                    logging.info("{}: ERROR - Cannot post in Log Channel!!!".format(server_id))
                except Exception:
                    logging.info("{}: Other ERROR occured during membership check!".format)

        # add wait time
        dt = date.today()
        today = dtime.combine(dt, time(12, 0, 0, tzinfo = timezone.utc))
        self.db.set_last_checked(today)
        logging.info("Set last membership check to %s.", today)

    async def send_expired_info(self, lg_ch, content):
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


        
    async def check_membership_routine(self):
        while not self.bot.is_closed():
            now = dtime.now(tz = timezone.utc)
            last_checked = self.db.get_last_checked()
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
