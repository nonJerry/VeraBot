# External
import asyncio

from discord.app_commands import CheckFailure

from database import Database
from dateutil.relativedelta import relativedelta
import discord
from discord import app_commands
from discord.ext import commands
import gspread
# Python
import logging
from os import getenv
# Internal
from membership_handling import MembershipHandler
from utility import Utility


class Membership(commands.Cog):

    def __init__(self, bot, member_handler: MembershipHandler):
        self.bot = bot
        self.member_handler = member_handler

    @app_commands.command(name="verify", description="Tries to verify a screenshot for membership in the DMs")
    @app_commands.check(Utility.is_interaction_not_dm)
    async def verify(self, interaction: discord.Interaction, attachment: discord.Attachment, vtuber: str = None,
                     language: str = None):
        if not attachment.content_type.startswith("image"):
            await interaction.response.send_message("The included attachment is not an image, please attach an image.",
                                                    ephemeral=True)
            logging.info("Verify without screenshot from %s.", interaction.user.id)
        await interaction.response.defer(ephemeral=True, thinking=True)
        if vtuber or language:
            if vtuber:
                server = Utility.map_vtuber_to_server(vtuber)
            elif Utility.is_multi_server(interaction.guild.id):
                embed = Utility.create_supported_vtuber_embed()
                await interaction.followup.send(content="Please use a valid supported VTuber!", embed=embed,
                                                ephemeral=True)

            if language:
                language = Utility.map_language(language)
            else:
                language = "eng"

            if server:
                await self.member_handler.add_to_queue(interaction, attachment, server, language, vtuber)
            else:
                embed = Utility.create_supported_vtuber_embed()
                await interaction.followup.send(content="Please use a valid supported VTuber!", embed=embed,
                                                ephemeral=True)
        elif Utility.is_multi_server(interaction.guild.id):
            embed = Utility.create_supported_vtuber_embed()
            await interaction.followup.send(content="Please use a valid supported VTuber!", embed=embed, ephemeral=True)
        else:
            await self.member_handler.add_to_queue(interaction, attachment, interaction.guild.id)

    @verify.error
    async def verify_error(self, interaction, error):
        if isinstance(error, commands.CommandOnCooldown):
            logging.info("%s tried to use verify too often.", interaction.user.id)
            await interaction.response.send_message(f"Try again in {error.retry_after:.0f}s.")
        elif isinstance(error, CheckFailure):
            logging.info("%s tried to use verify in DMs.", interaction.user.id)
            await interaction.response.send_message(f"Please use this command in the server and not in DMs anymore.")

    @verify.autocomplete('vtuber')
    async def verify_autocomplete(self, interaction: discord.Interaction, current: str):
        server_db = Database().get_server_db(interaction.guild.id)
        if Utility.is_multi_server(interaction.guild.id):
            multi_talents = server_db.get_multi_talents()
            vtubers = [m['idol'] for m in multi_talents]
            return [app_commands.Choice(name=vtuber, value=vtuber) for vtuber in vtubers if
                    current.lower() in vtuber.lower()]
        else:
            vtuber = server_db.get_vtuber()
            return [app_commands.Choice(name=vtuber, value=vtuber)]

    @app_commands.command(name="viewmembers",
                          description="Shows all user with the membership role. Or if a id is given this users data.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(Utility.is_interaction_not_dm)
    async def view_members(self, interaction: discord.Interaction, member: discord.User = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if member:
            logging.info(f"{interaction.user.id} used viewMember with ID in {interaction.guild.id}")
            await self.member_handler.view_membership(interaction, member.id, None)
        else:
            logging.info(f"{interaction.user.id} viewed all members in {interaction.guild.id}")
            await self.member_handler.view_membership(interaction, None)

    @app_commands.command(name="viewmembersfor",
                          description="Shows all user with the membership role. Or if a vtuber is given for that VTuber.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(Utility.is_interaction_not_dm)
    async def view_members_multi(self, interaction: discord.Interaction, vtuber: str = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if vtuber:
            logging.info("%s viewed all members in %s for %s", interaction.user.id, interaction.guild.id, vtuber)
            await self.member_handler.view_membership(interaction, None, vtuber)
        else:
            logging.info("%s viewed all members in %s", interaction.user.id, interaction.guild.id)
            await self.member_handler.view_membership(interaction, None, None)

    @view_members_multi.autocomplete('vtuber')
    async def view_members_multi_autocomplete(self, interaction: discord.Interaction, current: str):
        server_db = Database().get_server_db(interaction.guild.id)
        multi_talents = server_db.get_multi_talents()
        vtubers = [m['idol'] for m in multi_talents]
        return [app_commands.Choice(name=vtuber, value=vtuber) for vtuber in vtubers if
                current.lower() in vtuber.lower()]

    @app_commands.command(name="addmember",
                          description="Gives the membership role to the user whose ID was given.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(Utility.is_interaction_not_dm)
    @app_commands.describe(date='Date has to be in the format dd/mm/yyyy.')
    async def set_membership(self, interaction: discord.Interaction, member: discord.User, date: str,
                             vtuber: str = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        logging.info("%s used addMember in %s", interaction.user.id, interaction.guild.id)
        await self.member_handler.set_membership(interaction, member.id, date, manual=True, vtuber=vtuber)

    @set_membership.autocomplete('vtuber')
    async def set_membership_autocomplete(self, interaction: discord.Interaction, current: str):
        server_db = Database().get_server_db(interaction.guild.id)
        multi_talents = server_db.get_multi_talents()
        vtubers = [m['idol'] for m in multi_talents]
        return [app_commands.Choice(name=vtuber, value=vtuber) for vtuber in vtubers if
                current.lower() in vtuber.lower()]

    @app_commands.command(name="delmember",
                          description="Removes the membership role from the user whose ID was given.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(Utility.is_interaction_not_dm)
    async def del_membership(self, interaction: discord.Interaction, member: discord.User, vtuber: str = None,
                             text: str = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        logging.info("%s used delMember in %s", interaction.user.id, interaction.guild.id)
        await self.member_handler.del_membership(interaction, member.id, text, manual=True, vtuber=vtuber)

    @del_membership.autocomplete('vtuber')
    async def del_membership_autocomplete(self, interaction: discord.Interaction, current: str):
        server_db = Database().get_server_db(interaction.guild.id)
        multi_talents = server_db.get_multi_talents()
        vtubers = [m['idol'] for m in multi_talents]
        return [app_commands.Choice(name=vtuber, value=vtuber) for vtuber in vtubers if
                current.lower() in vtuber.lower()]

    @app_commands.command(name="purgemember",
                          description="Initiates a Membership Check")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(Utility.is_interaction_not_dm)
    async def purge_members(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.member_handler.purge_memberships(interaction.guild.id)
        await interaction.followup.send(
            "This was a hard check, it might have hit many members that still have a valid membership.", ephemeral=True)

    @commands.command(hidden=True, name="queue")
    @commands.is_owner()
    async def queue(self, ctx):
        count = len(self.member_handler.verify_deque)
        await ctx.send("Queue count: {}".format(count))

    @commands.command(hidden=True, name="relayVerify")
    @commands.is_owner()
    async def relay_verify(self, ctx, user_id: int, server_id: int):
        embed = discord.Embed(title=str(user_id))

        # Send attachment and message to membership verification channel
        member_veri_ch = self.bot.get_channel(Database().get_server_db(server_id).get_log_channel())

        author = self.bot.get_user(user_id)
        desc = "{}\n{}".format(str(author), "Date not detected")

        embed.description = "Main Proof\nUser: {}".format(author.mention)
        embed.add_field(name="Recognized Date", value="None")
        embed.set_image(url=ctx.message.attachments[0].url)
        message = await member_veri_ch.send(content="```\n{}\n```".format(desc), embed=embed)
        await message.add_reaction(u"\U0001F4C5")  # calendar
        await message.add_reaction(u"\U0001F6AB")  # no entry
        logging.info("Relayed the verify to %s", server_id)

    @commands.command(hidden=True, name="dumpSheet")
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
                date = member.last_membership + relativedelta(months=1)

                member_id = str(member.id)
                name = str(target_member)
                date = date.strftime(r"%d/%m/%Y")

                entries.append([member_id, name, date])
            try:
                worksheet.clear()
                worksheet.update('A1:C' + str(count), entries, raw=False)
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
                await ctx.send(
                    "Please give the bot access to the sheet. You can either use a link that can be used by everyone or add `verabot@verabot-318714.iam.gserviceaccount.com`.")
            elif code == 404:
                logging.info("%s requested sheet dump with invalid link.", ctx.guild.id)
                await ctx.send("Your link was not valid. Please use the command with a valid google sheets link.")

    @dump_sheet.error
    async def verify_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            logging.info("%s tried to use dump sheet too often.", ctx.author.id)
            await ctx.send(f"Try again in {error.retry_after:.0f}s.")
        elif isinstance(error, commands.BadArgument):
            logging.debug("%s used invalid Link (not string) for %s", ctx, ctx.command)
            await ctx.send("Please provide a valid link!")
        elif isinstance(error, commands.MissingRequiredArgument):
            logging.debug("%s forgot link for %s", ctx.author.id, ctx.command)
            await ctx.send("Please include the link to the spreadsheet!")
