# External
import asyncio
from database import Database
from dateutil.relativedelta import relativedelta
import discord
from discord.ext import commands
import gspread
# Python
import logging
from os import getenv
# Internal
from membership_handling import MembershipHandler

class Membership(commands.Cog):

    def __init__(self, bot, member_handler: MembershipHandler):
        self.bot = bot
        self.member_handler = member_handler
        
    @commands.command(name="viewMembers", aliases=["members","member", "viewMember"],
        help = "Shows all user with the membership role. Or if a id is given this users data.",
        brief = "Show membership(s)")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def view_members(self, ctx, vtuber=None, *member_id: int):
        if member_id and not vtuber:
            logging.info("%s used viewMember with ID in %s", ctx.author.id, ctx.guild.id)
            await self.member_handler.view_membership(ctx.message, member_id, None)
        elif vtuber:
            logging.info("%s viewed all members in %s for %s", ctx.author.id, ctx.guild.id, vtuber)
            await self.member_handler.view_membership(ctx.message, None, vtuber)
        else:
            logging.info("%s viewed all members in %s", ctx.author.id, ctx.guild.id)
            await self.member_handler.view_membership(ctx.message, None, None)


    @commands.command(name="addMember", aliases=["set_membership", "setMember"],
        help="Gives the membership role to the user whose ID was given.\n" + 
        "<date> has to be in the format dd/mm/yyyy.\n" +
        "It equals the date shown on the sent screenshot",
        brief="Gives the membership role to a user")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def set_membership(self, ctx, member_id: int, date, vtuber=None):
        logging.info("%s used addMember in %s", ctx.author.id, ctx.guild.id)
        await self.member_handler.set_membership(ctx.message, member_id, date, True, True, vtuber)

    @set_membership.error
    async def set_membership_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            logging.debug("%s forgot argument for addMember", ctx.author.id)
            await ctx.send("Please include at least two arguments!")
        elif isinstance(error, commands.BadArgument):
            logging.debug("%s used an invalid argument for addMember.", ctx.author.id)
            await ctx.send("One of the arguments has the wrong data type!")


    @commands.command(name="delMember",
        help="Removes the membership role from the user whose ID was given.\n" +
        "A text which is sent to the user as DM can be given but is optional.",
        brief="Removes the membership role from the user")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def del_membership(self, ctx, member_id: int, vtuber=None, *text):
        logging.info("%s used delMember in %s", ctx.author.id, ctx.guild.id)
        await self.member_handler.del_membership(ctx.message, member_id, text, True, True, vtuber)


    @commands.command(name="purgeMember", aliases=["purge"],
    brief="Initiates a Membership Check",
    help="This will initiate a membership check which also removes members that MIGHT already have lost their membership.\n" +
    "CAUTION: This will also hit many members that are still valid (Timezones and exact time of membering ...)")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge_members(self, ctx):
        await self.member_handler.purge_memberships(ctx.guild.id)
        await ctx.send("This was a hard check, it might have hit many members that still have a valid membership.")

    @del_membership.error
    @view_members.error
    async def id_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            logging.debug("%s used invalid ID for delMember or viewMember.", ctx.author.id)
            await ctx.send("Please provide a valid id!")
        elif isinstance(error, commands.MissingRequiredArgument):
            logging.debug("%s forgot argument for delMember or viewMember.", ctx.author.id)
            await ctx.send("Please include the argument!")

    @commands.command(hidden = True, name = "queue")
    @commands.is_owner()
    async def queue(self, ctx):
        count = len(self.member_handler.verify_deque)
        await ctx.send("Queue count: {}".format(count))

    @commands.command(hidden= True, name = "relayVerify")
    @commands.is_owner()
    async def relay_verify(self, ctx, user_id: int, server_id: int):
        embed = discord.Embed(title = str(user_id))

        # Send attachment and message to membership verification channel
        member_veri_ch = self.bot.get_channel(Database().get_server_db(server_id).get_log_channel())

        author = self.bot.get_user(user_id)
        desc = "{}\n{}".format(str(author), "Date not detected")

        embed.description = "Main Proof\nUser: {}".format(author.mention)
        embed.add_field(name="Recognized Date", value = "None")
        embed.set_image(url = ctx.message.attachments[0].url)
        message = await member_veri_ch.send(content = "```\n{}\n```".format(desc), embed = embed)
        await message.add_reaction(u"\U0001F4C5")  # calendar
        await message.add_reaction(u"\U0001F6AB")  # no entry
        logging.info("Relayed the verify to %s", server_id)

    
    @commands.command(hidden = True, name ="dumpSheet")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def dump_sheet(self, ctx, link: str):
        logging.info("%s used dump sheet for link %s.", ctx.author.id, link)
        credential_file = getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        await ctx.send("Starting to dump data now!")
        try:
            gc = gspread.service_account(filename=credential_file)
            sh = gc.open_by_url(link)
            worksheet = sh.worksheet("Member Dump")
            if not worksheet:
                worksheet = sh.add_worksheet(title="Member Dump", rows="300", cols="20")

            server_db = Database().get_server_db(ctx.guild.id)
            count = 0
            entries = []
            for member in server_db.get_members():
                    count += 1

                    target_member = ctx.guild.get_member(member.id)
                    date = member.last_membership + relativedelta(months = 1)

                    member_id = str(member.id)
                    name = str(target_member)
                    date = date.strftime(r"%d/%m/%Y")

                    entries.append([member_id, name, date])
            try:
                worksheet.clear()
                worksheet.update('A1:C' + str(count), entries, raw = False)
            except gspread.exceptions.APIError as e:
                code = e.args[0]['code']
                if code == 429:
                    logging.warning("Hit API rate limit of google sheets")
                    await asyncio.sleep(100)
            logging.info("%s: Dumped data successfully.", ctx.guild.id)
            await ctx.send("Finished dumping the data. It is in a sheet called `Member Dump`.")

        except gspread.exceptions.APIError as e:
            code = e.args[0]['code']
            if code == 403:
                logging.info("%s didn't give bot access to sheet.", ctx.guild.id)
                await ctx.send("Please give the bot access to the sheet. You can either use a link that can be used by everyone or add `verabot@verabot-318714.iam.gserviceaccount.com`.")
            elif code == 404:
                logging.info("%s requested sheet dump with invalid link.", ctx.guild.id)
                await ctx.send("Your link was not valid. Please use the command with a valid google sheets link.")

    @dump_sheet.error
    async def verify_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            logging.info("%s tried to use dump sheet too often.", ctx.author.id)
            await ctx.send(f"Try again in {error.retry_after:.0f}s.")
        elif isinstance(error, commands.BadArgument):
            logging.debug("%s used invalid Link (not string) for %s", ctx.author.id, ctx.command)
            await ctx.send("Please provide a valid link!")
        elif isinstance(error, commands.MissingRequiredArgument):
            logging.debug("%s forgot link for %s", ctx.author.id, ctx.command)
            await ctx.send("Please include the link to the spreadsheet!")