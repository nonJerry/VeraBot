# External
from database import Database
import discord
from discord.ext import commands
# Python
import logging
# Internal
from utility import Utility

class Settings(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @commands.command(name="viewSettings", aliases=["settings", "allSettings", "showSettings"],
        help="Shows all settings of this server.",
        brief="Shows all settings")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def show_settings(self, ctx):
        logging.debug("%s called viewSettings.", ctx.author.id)

        title = "Current Settings"
        embed = discord.Embed(title = title, description = None)
        server_db = self.db.get_server_db(ctx.guild.id)

        # VTuber
        vtuber = server_db.get_vtuber()
        embed.add_field(name="VTuber", value=vtuber)
        
        #get prefixes
        prefixes = server_db.get_prefixes()
        prefixes = ', '.join(element for element in prefixes)
        embed.add_field(name='Prefixes', value=prefixes, inline=True)

        # Member Role
        member_role = server_db.get_member_role()
        embed.add_field(name='Member Role ID', value=str(member_role), inline=True)

        # Log Channel
        log_channel = server_db.get_log_channel()
        embed.add_field(name='Log Channel ID', value=str(log_channel), inline=True)

        # current picture (als image anhängen)
        picture_url = server_db.get_picture()
        embed.set_image(url=picture_url)

        # automatic role
        automatic_role = server_db.get_automatic()
        embed.add_field(name='Auto Role Flag', value=str(automatic_role), inline=True)

        # require additional proof
        additional_proof = server_db.get_additional_proof()
        embed.add_field(name='Require Additional Proof', value=str(additional_proof), inline=True)

        # tolerance duration
        tolerance_duration = server_db.get_tolerance_duration()
        embed.add_field(name='Tolerance Duration', value=str(tolerance_duration), inline=True)

        # inform duration
        inform_duration = server_db.get_inform_duration()
        embed.add_field(name='Prior Notice Duration', value=str(inform_duration), inline=True)

        # logging
        enable_logging = server_db.get_logging()
        embed.add_field(name='Logging enabled', value=str(enable_logging), inline=True)

        # threads
        enable_threads = server_db.get_threads_enabled()
        embed.add_field(name='Threads enabled', value=str(enable_threads), inline=True)

        # proof channel
        proof_channel = server_db.get_proof_channel()
        embed.add_field(name='Proof Channel ID', value=str(proof_channel), inline=True)

        m = "These are your current settings.\nYour set expiration image is the picture.\n"
        m += "For a full explanation of the settings please refer to:\n"
        m += "<https://github.com/nonJerry/VeraBot/blob/master/settings.md>"
        await ctx.send(content=m, embed = embed)

    @commands.command(name="prefix",
        help="Adds the <prefix> that can be used for the bot on this server.",
        brief="Adds an additional prefix")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_prefix(self, ctx, prefix: str):
        self.db.get_server_db(ctx.guild.id).set_prefix(prefix)

        await ctx.send("Prefix " + prefix + " added")
        logging.debug("%s added %s as prefix.", ctx.guild.id, prefix)

    @set_prefix.error
    async def prefix_error(self, ctx, error):
        if isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('The argument is invalid')


    @commands.command(name="removePrefix",
        help="Removes the <prefix> so that it is not available as a prefix anymore for this server.",
        brief="Removes an prefix")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def remove_prefix(self, ctx, prefix: str):

        if self.db.get_server_db(ctx.guild.id).remove_prefix(prefix) == 0:
            await ctx.send("Prefix not found")
        else:
            await ctx.send(prefix +" removed")
        logging.debug("%s removed %s as prefix.", ctx.guild.id, prefix)


    @commands.command(name="showPrefix", aliases=["viewPrefix", "showPrefixes", "viewPrefixes"],
        help="Shows all prefixes that are available to use commands of this bot on this server.",
        brief="Shows all prefixes")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def show_prefix(self, ctx):

        await ctx.send("Those prefixes are set: " + str(self.db.get_server_db(ctx.guild.id).get_prefixes()))
        logging.debug("%s viewed their prefixes.", ctx.guild.id)


    @commands.command(name="setVTuber",
        help="Sets the name of the VTuber of this server.\nThe screenshot sent for the verification is scanned for this name. Therefore this name should be identical with the name in the membership tab.",
        brief="Sets the name of the VTuber of this server")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_idol(self, ctx, vtuber_name: str):

        # always only one entry
        for element in self.db.get_vtuber_list():
            if vtuber_name.lower() in element['name']:
                await ctx.send("This Vtuber is already mapped to a server!")
                return
        self.db.set_vtuber(vtuber_name, ctx.guild.id)

        await ctx.send("Set VTuber name to " + vtuber_name)
        logging.info("%s (%s) -> New Vtuber added: %s", ctx.guild.name, ctx.guild.id, vtuber_name)


    @commands.command(name="memberRole", aliases=["setMemberRole"],
        help="Sets the role that should be given to a member who has proven that he has valid access to membership content.\nRequires the ID not the role name or anything else!",
        brief="Sets the role for membership content")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_member_role(self, ctx, role_id: int):
        if self.check_role_integrity(ctx, role_id):
            self.db.get_server_db(ctx.guild.id).set_member_role(role_id)

            await ctx.send("Member role id set to " + str(role_id))
        else:
            await ctx.send("ID does not refer to a legit role")
        logging.info("%s set %s as member role.", ctx.guild.id, role_id)


    @commands.command(name="logChannel", aliases=["setLogChannel"],
        help="Sets the channel which is used to control the sent memberships.\nRequires the ID not the role name or anything else!",
        brief="Sets the channel for logging")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_log_channel(self, ctx, channel_id: int):
        if self.check_channel_integrity(channel_id):
            self.db.get_server_db(ctx.guild.id).set_log_channel(channel_id)
            logging.info("%s set %s as log channel.", ctx.guild.id, channel_id)
            await ctx.send("Log Channel id set to " + str(channel_id))
        else:
            await ctx.send("ID does not refer to a legit channel")
            logging.info("%s used a wrong ID as log channel.", ctx.guild.id)



    @commands.command(name="picture", aliases=["setPicture"],
        help="Sets the image that is sent when a membership is about to expire.\n" +
        "It supports link that end with png, jpg or jpeg.",
        brief="Set image for expiration message.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_picture(self, ctx, link: str):
        logging.info("{} set their picture: {}".format(str(ctx.guild.id), link))
        from re import fullmatch
        match = fullmatch(r"http[s]?://[a-zA-Z0-9\_\-\.]+/[a-zA-Z0-9\_\-/]+\.(png|jpeg|jpg)", link)
        if match:
            self.db.get_server_db(ctx.guild.id).set_picture(link)
            await ctx.send("Image for expiration message set.")
        else:
            await ctx.send("Please send a legit link. Only jpg, jpeg and png are accepted.")


    @commands.command(name="setAuto", aliases=["auto", "setAutoRole", "setAutomaticRole"],
        help = "Sets whether the bot is allowed to automatically add the membership role.\n"
        + "Only allows True or False as input.",
        brief = "Set flag for automatic role handling")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_automatic_role(self, ctx, flag: str):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await ctx.send(self.BOOLEAN_ONLY_TEXT)
            return

        self.db.get_server_db(ctx.guild.id).set_automatic(flag)
        logging.info("%s set auto to %s", ctx.guild.id, str(flag))

        await ctx.send("Flag for automatic role handling set to " + str(flag))


    @commands.command(name="setAdditionalProof", aliases=["setProof", "setRequireProof", "additionalProof", "requireAdditionalProof"],
        help = "Sets whether the bot will require additional proof from the user.\n"
        + "Only allows True or False as input.",
        brief = "Set flag for the inquiry of additional Proof")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_require_additional_proof(self, ctx, flag: str):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await ctx.send(self.BOOLEAN_ONLY_TEXT)
            return

        self.db.get_server_db(ctx.guild.id).set_additional_proof(flag)
        logging.info("%s set additional Proof to %s", ctx.guild.id, str(flag))

        await ctx.send("Flag for additional Proof set to " + str(flag))


    @commands.command(name="setTolerance", aliases=["tolerance", "toleranceDuration"],
        help = "Sets the time that users will have access to the membership channel after their membership expired.",
        brief = "Set tolerance time after membership expiry")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_tolerance_duration(self, ctx, time: int):
        if(time < 0):
            await ctx.send("This value needs to be at least 0 days.")
            return

        self.db.get_server_db(ctx.guild.id).set_tolerance_duration(time)
        logging.info("%s set Tolerance to %s", ctx.guild.id, time)

        await ctx.send("Time that users will still have access to the channel after their membership expired set to {} days.".format(str(time)))


    @commands.command(name="setPriorNoticeDuration", aliases=["informDuration", "PriorNoticeDuration", "PriorNotice", "setPriorNotice"],
        help = "Sets how many days before the expiry of their membership a user will be notified to renew their proof.",
        brief = "Set time for notice before membership expiry")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_inform_duration(self, ctx, time: int):
        if(time < 0):
            await ctx.send("This value needs to be at least 0 days.")
            return

        self.db.get_server_db(ctx.guild.id).set_inform_duration(time)
        logging.info("%s set prior Notice to %s", ctx.guild.id, time)

        await ctx.send("Users will be notified " + str(time) + " days before their membership ends.")

    @commands.command(name="enableLogging",
        help="Flag which decides whether you will see the logs when the bot checks for expired memberships.",
        brief="Toggles logging regarding expired memberships")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_logging(self, ctx, flag):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await ctx.send(self.BOOLEAN_ONLY_TEXT)
            return
        
        self.db.get_server_db(ctx.guild.id).set_logging(flag)
        logging.info("%s set logging to %s", ctx.guild.id, str(flag))

        await ctx.send("Flag for logging set to " + str(flag))


    @commands.command(name="proofChannel", aliases=["setProofChannel", "threadChannel", "setThreadChannel"],
    help="Sets the Channel to which the threads will be attached.",
    brief="Sets the Channel to which the threads will be attached.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_proof_channel(self, ctx, channel_id: int):
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("Please use a valid channel!")
            return

        #check whether use_public_thread is allowed
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.create_public_threads:
            await ctx.send("You need to enable use_public_threads for VeraBot on your proof channel first!")
            return

        self.db.get_server_db(ctx.guild.id).set_proof_channel(channel_id)
        logging.info("%s set %s as proof channel.", ctx.guild.id, channel_id)

        await ctx.send("Proof Channel id set to " + str(channel_id))


    @commands.command(name="enableThreads", aliases=["threads", "enabledThread", "thread"],
    help="Will activate the use of threads. The bot will create a Thread for each submitted proof. The log channel will be used to protocol the verified/denied proofs, not as place to verify them anymore.\n" +
    "Requires a proof channel to be set and use_public_threads to be enabled for this channel.",
    brief="Toggles function that the bot creates a thread for each proof.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def toggle_threads(self, ctx, flag):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await ctx.send(self.BOOLEAN_ONLY_TEXT)
            return

        if flag:
            channel = self.bot.get_channel(self.db.get_server_db(ctx.guild.id).get_proof_channel())
            if not channel:
                await ctx.send("Please set a proof channel first!")
                return

            #check whether use_public_thread is allowed
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.create_public_threads:
                await ctx.send("You need to enable use_public_threads for VeraBot on your proof channel first!")
                return
        # set value
        self.db.get_server_db(ctx.guild.id).set_threads_enabled(flag)
        logging.info("%s set threads to %s", ctx.guild.id, str(flag))

        await ctx.send("Flag for using threads set to " + str(flag))

    async def check_thread_permissions(self, guild_id: int) -> bool:
        member_veri_ch = self.bot.get_channel(self.db.get_server_db(guild_id).get_proof_channel())
        permissions = member_veri_ch.permissions_for(member_veri_ch.guild.me)
        if not permissions.create_public_threads:
            logging.info("%s: Did not have Threads permission enabled.", guild_id)
            return False
        return True


    @set_idol.error
    @set_log_channel.error
    @set_member_role.error
    @set_prefix.error
    @remove_prefix.error
    @set_automatic_role.error
    @set_require_additional_proof.error
    @set_tolerance_duration.error
    @set_inform_duration.error
    @set_picture.error
    @set_logging.error
    @toggle_threads.error
    @set_proof_channel.error
    #@toggle_threads.error
    async def general_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            logging.debug("%s used invalid ID for %s", ctx.author.id, ctx.command)
            await ctx.send("Please provide a valid id!")
        elif isinstance(error, commands.MissingRequiredArgument):
            logging.debug("%s forgot argument for %s", ctx.author.id, ctx.command)
            await ctx.send("Please include the argument!")

    def check_role_integrity(self, ctx, role_id: int):
        if ctx.guild.get_role(role_id):
            return True
        return False

    def check_channel_integrity(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False
        return True

    @commands.command(hidden = True, name = "createNewSetting")
    @commands.is_owner()
    async def create_new_setting(self, ctx, kind: str, value):
        if Utility.is_integer(value):
            value = int(value)
        else:
            tmp = Utility.text_to_boolean(value)
            if isinstance(tmp, bool):
                value = tmp

        self.db.create_new_setting(kind, value)

        logging.info("Added %s with default value %s", kind, str(value))
        await ctx.send("Added " + kind + " with default value " + str(value))

    

    @commands.command(hidden = True, name = "newMemberSetting")
    @commands.is_owner()
    async def create_new_member_setting(self, ctx, kind: str, value):
        if Utility.is_integer(value):
            value = int(value)
        else:
            tmp = Utility.text_to_boolean(value)
            if isinstance(tmp, bool):
                value = tmp

        self.db.create_new_member_setting(kind, value)

        logging.info("Member: Added %s with default value %s", kind, str(value))            
        await ctx.send("Member: Added " + kind + " with default value " + str(value))

    

    @commands.command(hidden = True, name = "servers")
    @commands.is_owner()
    async def servers(self, ctx):
        activeservers = self.bot.guilds
        m = ""
        for guild in activeservers:
            if not guild.id in [843294906440220693 ,623148148344225792, 815517423179530252]:
                m += "{}: {} ({} user)\n".format(str(guild.id), guild.name, guild.member_count)
        embed = discord.Embed(title="Current Servers", description=m)

        await ctx.send(content=None, embed=embed)

    @commands.command(hidden=True, name="leaveGuild")
    @commands.is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send("Guild does not exist.")
            return
        await guild.leave()

        await ctx.send("Left guild {}.".format(str(guild_id)))
