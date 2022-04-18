# External
from database import Database
import discord
from discord import app_commands
from discord.ext import commands
# Python
import logging
# Internal
from utility import Utility

class Settings(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(name="viewSettings", description="Shows all settings of this server.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def show_settings(self, interaction: discord.Interaction):
        logging.debug("%s called viewSettings.", interaction.user.id)

        title = "Current Settings"
        embed = discord.Embed(title = title, description = None)
        server_db = self.db.get_server_db(interaction.guild_id)

        # VTuber
        vtuber = server_db.get_vtuber()
        embed.add_field(name="VTuber", value=vtuber)

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
        
        # is multi server
        is_multi = Utility.is_multi_server(interaction.guild_id)
        embed.add_field(name='Multi Server', value=str(is_multi), inline=True)

        m = "These are your current settings.\nYour set expiration image is the picture.\n"
        m += "For a full explanation of the settings please refer to:\n"
        m += "<https://github.com/nonJerry/VeraBot/blob/master/settings.md>"
        await interaction.response.send_message(content=m, embed = embed, ephemeral=True)

    @app_commands.command(name="setVTuber",
        description="Sets the name of the VTuber of this server.\nThe screenshot sent for the verification is scanned for this name. Therefore this name should be identical with the name in the membership tab.")
    @app_commands.check.has_permissions(administrator=True)
    async def set_idol(self, interaction: discord.Interaction, vtuber_name: str):

        # always only one entry
        if self.check_vtuber(vtuber_name):           
            await interaction.response.send_message("This Vtuber is already mapped to a server!")
            return

        self.db.set_vtuber(vtuber_name, interaction.guild_id)

        await interaction.response.send_message("Set VTuber name to " + vtuber_name, ephemeral=True)
        logging.info("%s (%s) -> New Vtuber added: %s", interaction.guild.name, interaction.guild_id, vtuber_name)

    def check_vtuber(self, vtuber_name) -> bool:
        for element in self.db.get_vtuber_list():
            logging.debug(element)
            if vtuber_name.lower() == element['name']:
                return True
        return False


    @app_commands.command(name="memberRole",
        description="Sets the role that should be given to a member who has proven that he has valid access to membership content.\nRequires the ID not the role name or anything else!")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_member_role(self, interaction: discord.Interaction, role_id: int):
        if self.check_role_integrity(interaction, role_id):
            self.db.get_server_db(interaction.guild_id).set_member_role(role_id)

            await interaction.response.send_message("Member role id set to " + str(role_id), ephemeral=True)
        else:
            await interaction.response.send_message("ID does not refer to a legit role", ephemeral=True)
        logging.info("%s set %s as member role.", interaction.guild_id, role_id)


    @app_commands.command(name="logChannel", description="Sets the channel which is used to control the sent memberships.\nRequires the ID not the role name or anything else!")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel_id: int):
        if self.check_channel_integrity(channel_id):
            self.db.get_server_db(interaction.guild_id).set_log_channel(channel_id)
            logging.info("%s set %s as log channel.", interaction.guild_id, channel_id)
            await interaction.response.send_message("Log Channel id set to " + str(channel_id), ephemeral=True)
        else:
            await interaction.response.send_message("ID does not refer to a legit channel", ephemeral=True)
            logging.info("%s used a wrong ID as log channel.", interaction.guild_id)



    @app_commands.command(name="picture",
        description="Sets the image that is sent when a membership is about to expire. It supports link that end with png, jpg or jpeg.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_picture(self, interaction: discord.Interaction, link: str):
        logging.info("{} set their picture: {}".format(str(interaction.guild_id), link))
        from re import fullmatch
        match = fullmatch(r"http[s]?://[a-zA-Z0-9\_\-\.]+/[a-zA-Z0-9\_\-/]+\.(png|jpeg|jpg)", link)
        if match:
            self.db.get_server_db(interaction.guild_id).set_picture(link)
            await interaction.response.send_message("Image for expiration message set.", ephemeral=True)
        else:
            await interaction.response.send_message("Please send a legit link. Only jpg, jpeg and png are accepted.", ephemeral=True)


    @app_commands.command(name="setAuto", description = "Sets whether the bot is allowed to automatically add the membership role. Only allows True or False as input.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_automatic_role(self, interaction: discord.Interaction, flag: str):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await interaction.response.send_message(self.BOOLEAN_ONLY_TEXT, ephemeral=True)
            return

        self.db.get_server_db(interaction.guild_id).set_automatic(flag)
        logging.info("%s set auto to %s", interaction.guild_id, str(flag))

        await interaction.response.send_message("Flag for automatic role handling set to " + str(flag), ephemeral=True)


    @app_commands.command(name="setAdditionalProof", description = "Sets whether the bot will require additional proof from the user. Only allows True or False as input.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_require_additional_proof(self, interaction: discord.Interaction, flag: str):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await interaction.response.send_message(self.BOOLEAN_ONLY_TEXT, ephemeral=True)
            return

        self.db.get_server_db(interaction.guild_id).set_additional_proof(flag)
        logging.info("%s set additional Proof to %s", interaction.guild_id, str(flag))

        await interaction.response.send_message("Flag for additional Proof set to " + str(flag), ephemeral=True)


    @app_commands.command(name="setTolerance", description = "Sets the time that users will have access to the membership channel after their membership expired.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_tolerance_duration(self, interaction: discord.Interaction, time: int):
        if(time < 0):
            await interaction.response.send_message("This value needs to be at least 0 days.", ephemeral=True)
            return

        self.db.get_server_db(interaction.guild_id).set_tolerance_duration(time)
        logging.info("%s set Tolerance to %s", interaction.guild_id, time)

        await interaction.response.send_message("Time that users will still have access to the channel after their membership expired set to {} days.".format(str(time)), ephemeral=True)


    @app_commands.command(name="setPriorNoticeDuration", description = "Sets how many days before the expiry of their membership a user will be notified to renew their proof.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_inform_duration(self, interaction: discord.Interaction, time: int):
        if(time < 0):
            await interaction.response.send_message("This value needs to be at least 0 days.")
            return

        self.db.get_server_db(interaction.guild_id).set_inform_duration(time)
        logging.info("%s set prior Notice to %s", interaction.guild_id, time)

        await interaction.response.send_message("Users will be notified " + str(time) + " days before their membership ends.", ephemeral=True)

    @app_commands.command(name="enableLogging", description="Flag which decides whether you will see the logs when the bot checks for expired memberships.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_logging(self, interaction: discord.Interaction, flag):
        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await interaction.response.send_message(self.BOOLEAN_ONLY_TEXT, ephemeral=True)
            return
        
        self.db.get_server_db(interaction.guild_id).set_logging(flag)
        logging.info("%s set logging to %s", interaction.guild_id, str(flag))

        await interaction.response.send_message("Flag for logging set to " + str(flag), ephemeral=True)


    @app_commands.command(name="proofChannel", description="Sets the Channel to which the threads will be attached.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_proof_channel(self, interaction: discord.Interaction, channel_id: int):
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Please use a valid channel!", ephemeral=True)
            return

        #check whether use_public_thread is allowed
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.create_public_threads:
            await interaction.response.send_message("You need to enable use_public_threads for VeraBot on your proof channel first!", ephemeral=True)
            return

        self.db.get_server_db(interaction.guild_id).set_proof_channel(channel_id)
        logging.info("%s set %s as proof channel.", interaction.guild_id, channel_id)

        await interaction.response.send_message("Proof Channel id set to " + str(channel_id), ephemeral=True)


    @app_commands.command(name="enableThreads", 
    description="Will activate the use of threads. The bot will create a Thread for each submitted proof. The log channel will be used to protocol the verified/denied proofs, not as place to verify them anymore. " +
    "Requires a proof channel to be set and use_public_threads to be enabled for this channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_threads(self, interaction: discord.Interaction, flag):
        # multi-server cannot use threads
        if Utility.is_multi_server(interaction.guild_id):
            await interaction.response.send_message("You cannot enable threads as mutli-server!", ephemeral=True)
            logging.info("%s tried to enable Threads as multi-server.", interaction.guild_id)
            return

        flag = Utility.text_to_boolean(flag)
        if not isinstance(flag, bool):
            await interaction.response.send_message(self.BOOLEAN_ONLY_TEXT, ephemeral=True)
            return

        if flag:
            channel = self.bot.get_channel(self.db.get_server_db(interaction.guild_id).get_proof_channel())
            if not channel:
                await interaction.response.send_message("Please set a proof channel first!", ephemeral=True)
                return

            #check whether use_public_thread is allowed
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.create_public_threads:
                await interaction.response.send_message("You need to enable use_public_threads for VeraBot on your proof channel first!", ephemeral=True)
                return
        # set value
        self.db.get_server_db(interaction.guild_id).set_threads_enabled(flag)
        logging.info("%s set threads to %s", interaction.guild_id, str(flag))

        await interaction.response.send_message("Flag for using threads set to " + str(flag), ephemeral=True)

    async def check_thread_permissions(self, guild_id: int) -> bool:
        if Utility.is_multi_server(guild_id):
            logging.info("%s ended in check thread permission. It is not allowed for multi servers!", guild_id)
            return False

        member_veri_ch = self.bot.get_channel(self.db.get_server_db(guild_id).get_proof_channel())
        permissions = member_veri_ch.permissions_for(member_veri_ch.guild.me)
        if not permissions.create_public_threads:
            logging.info("%s: Did not have Threads permission enabled.", guild_id)
            return False
        return True

    @app_commands.command(name="enableMultiServer", description="Will activate the possibility to support several talents on one server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_multi_server(self, interaction: discord.Interaction):
        if Utility.is_multi_server(interaction.guild_id):
            logging.info("%s: Tried to enable the multi-talent function again.", interaction.guild_id)
            await interaction.response.send_message("Your server already has enabled the usage of multiple talents!", ephemeral=True)
            return
        if self.db.get_server_db(interaction.guild_id).get_threads_enabled():
            await interaction.response.send_message("You cannot enable multi server with threads enabled!", ephemeral=True)
            logging.info("%s: Tried to enable the multi-talent function with threads enabled.", interaction.guild_id)
            return

        self.db.add_multi_server(interaction.guild_id)
        logging.info("%s: Enabled the multi-talent function.", interaction.guild_id)

        await interaction.response.send_message("Management of several talents was activated for this server!", ephemeral=True)

    @app_commands.command(name="disableMultiServer", description="Will disable the possibility to support several talents on one server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_multi_server(self, interaction: discord.Interaction):
        if not Utility.is_multi_server(interaction.guild_id):
            logging.info("%s: Tried to disabled the multi-talent function without having it enabled.", interaction.guild_id)
            await interaction.response.send_message("Your server has not enabled the usage of multiple talents!", ephemeral=True)
            return
        
        self.db.remove_multi_server(interaction.guild_id)
        logging.info("%s: Disabled the multi-talent function.", interaction.guild_id)

        await interaction.response.send_message("Management of several talents was disabled for this server! For this all added VTubers were removed. Please add the one wanted again using $setVtuber", ephemeral=True)

    


    @app_commands.command(name="addTalent", description="Adds new Talent to be supported. Also needs the log channel and role id. Function only for Multi-Talent servers!")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_idol(self, interaction: discord.Interaction, name: str, log_id: int, role_id: int):
        if not Utility.is_multi_server(interaction.guild_id):
            logging.info("%s: Tried to use mutli-talent ADD without having it enabled.", interaction.guild_id)
            await interaction.response.send_message("Your server has not enabled the usage of multiple talents. If you intend to use this feature, please use `$enableMultiServer` first. Otherwise `$setVtuber` is the command you wanted to use.", ephemeral=True)
            return
        logging.info("Multi-Server %s: Trying to add %s as talent.", interaction.guild_id, name)

        # Check for integrity
        if self.check_vtuber(name):       
            logging.info("%s: Talent %s already exists.", interaction.guild_id, name)   
            await interaction.response.send_message("This Vtuber is already mapped to a server!", ephemeral=True)
            return

        if not self.bot.get_channel(log_id):
            await interaction.response.send_message("Please use a proper Channel!", ephemeral=True)
            return

        if not self.check_role_integrity(interaction, role_id):
            return

        # Finally add to db
        self.db.get_server_db(interaction.guild_id).add_multi_talent(name, log_id, role_id)
        self.db.set_vtuber(name, interaction.guild_id)
        logging.info("%s: Added %s with %s as Log Channel and %s as Role.", interaction.guild_id, name, log_id, role_id)

        await interaction.response.send_message("Successfully added the new talent!", ephemeral=True)


    @app_commands.command(name="removeTalent", description="Removes the Talent. Requires the exact name. Function only for Multi-Talent servers!")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_idol(self, interaction: discord.Interaction, name: str):
        if not Utility.is_multi_server(interaction.guild_id):
            logging.info("%s: Tried to remove a mutli-talent without having it enabled.", interaction.guild_id)
            await interaction.response.send_message("Your server has not enabled the usage of multiple talents.", ephemeral=True)
            return
        if self.db.get_server_db(interaction.guild_id).remove_multi_talent(name):
            self.db.remove_multi_talent_vtuber(interaction.guild_id, name)
            logging.info("Removed %s from VTuber list", name)
            await interaction.response.send_message("Successfully removed {}!".format(name), ephemeral=True)
        else:
            await interaction.response.send_message("Could not remove {}!".format(name), ephemeral=True)

# todo: remove these command errors (should no longer be needed with slash commands auto-complete feature)

    @set_idol.error
    @set_log_channel.error
    @set_member_role.error
    @set_automatic_role.error
    @set_require_additional_proof.error
    @set_tolerance_duration.error
    @set_inform_duration.error
    @set_picture.error
    @set_logging.error
    @toggle_threads.error
    @set_proof_channel.error
    @enable_multi_server.error
    @disable_multi_server.error
    @add_idol.error
    #@toggle_threads.error
    async def general_error(self, interaction: discord.Interaction, error):
        if isinstance(error, commands.BadArgument):
            logging.debug("%s used invalid ID for %s", interaction.user.id, interaction.command)
            await interaction.response.send_message("Please provide a valid id!")
        elif isinstance(error, commands.MissingRequiredArgument):
            logging.debug("%s forgot argument for %s", interaction.user.id, interaction.command)
            await interaction.response.send_message("Please include the argument!")

    def check_role_integrity(self, interaction: discord.Interaction, role_id: int):
        if interaction.guild.get_role(role_id):
            return True
        return False

    def check_channel_integrity(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False
        return True

# hidden commands are not possible with slash commands (todo: figure out what to do with these)

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
