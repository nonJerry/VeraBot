
import discord
from discord.ext import commands
#Internal
from utility import Utility

class Settings(commands.Cog):

    def __init__(self, bot, db_cluster):
        self.bot = bot
        self.db_cluster = db_cluster
        BOOLEAN_ONLY_TEXT = "Please do only use True or False."

    @commands.command(name="viewSettings", aliases=["settings", "allSettings", "showSettings"],
        help="Shows all settings of this server.",
        brief="Shows all settings")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def show_settings(self, ctx):
        title = "Current Settings"
        embed = discord.Embed(title = title, description = None)
        settings = self.db_cluster[str(ctx.guild.id)]["settings"]
        
        #get prefixes
        prefixes = settings.find_one({'kind' : 'prefixes'})['values']
        prefixes = ', '.join(element for element in prefixes)
        embed.add_field(name='Prefixes', value=prefixes, inline=True)

        # Member Role
        member_role = settings.find_one({'kind' : 'member_role'})['value']
        embed.add_field(name='Member Role ID', value=str(member_role), inline=True)

        # Log Channel
        log_channel = settings.find_one({'kind' : 'log_channel'})['value']
        embed.add_field(name='Log Channel ID', value=str(log_channel), inline=True)

        # current picture (als image anhängen)
        picture_url = settings.find_one({'kind' : 'picture_link'})['value']
        embed.set_image(url=picture_url)

        # automatic role
        automatic_role = settings.find_one({'kind' : 'automatic_role'})['value']
        embed.add_field(name='Auto Role Flag', value=str(automatic_role), inline=True)

        # require additional proof
        additional_proof = settings.find_one({'kind' : 'require_additional_proof'})['value']
        embed.add_field(name='Require Additional Proof', value=str(additional_proof), inline=True)

        # tolerance duration
        tolerance_duration = settings.find_one({'kind' : 'tolerance_duration'})['value']
        embed.add_field(name='Tolerance Duration', value=str(tolerance_duration), inline=True)

        # inform duration
        inform_duration = settings.find_one({'kind' : 'inform_duration'})['value']
        embed.add_field(name='Prior Notice Duration', value=str(inform_duration), inline=True)

        m = "These are your current settings.\nYour set expiration image is the picture.\n"
        m += "For a full explanation of the settings please refer to:\n:"
        m += "<https://github.com/nonJerry/VeraBot/blob/master/settings.md>"
        await ctx.send(content=m, embed = embed)

    @commands.command(name="prefix",
        help="Adds the <prefix> that can be used for the bot on this server.",
        brief="Adds an additional prefix")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_prefix(self, ctx, prefix: str):
        settings = self.db_cluster[str(ctx.guild.id)]["settings"]
        settings.update_one({"kind": "prefixes"}, {'$push': {'values': prefix}})
        await ctx.send("Prefix " + prefix + " added")

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
        settings = self.db_cluster[str(ctx.guild.id)]["settings"]

        if settings.update_one({"kind": "prefixes"}, {'$pull': {'values': prefix}}).matched_count == 0:
            await ctx.send("Prefix not found")
        else:
            await ctx.send(prefix +" removed")


    @commands.command(name="showPrefix", aliases=["viewPrefix", "showPrefixes", "viewPrefixes"],
        help="Shows all prefixes that are available to use commands of this bot on this server.",
        brief="Shows all prefixes")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def show_prefix(self, ctx):
        settings = self.db_cluster[str(ctx.guild.id)]["settings"]

        await ctx.send("Those prefixes are set: " + str(settings.find_one({"kind": "prefixes"})['values']))


    @commands.command(name="setVTuber",
        help="Sets the name of the VTuber of this server.\nThe screenshot sent for the verification is scanned for this name. Therefore this name should be identical with the name in the membership tab.",
        brief="Sets the name of the VTuber of this server")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_idol(self, ctx, vtuber_name: str):
        settings = self.db_cluster["settings"]["general"]
        # always only one entry
        for element in settings.find_one({}, {'supported_idols'})['supported_idols']:
            if vtuber_name.lower() in element['name']:
                await ctx.send("This Vtuber is already mapped to a server!")
                return
        if settings.find_one( { 'supported_idols.guild_id': ctx.guild.id}):
            settings.update_one({'supported_idols.guild_id': ctx.guild.id}, {'$set': {'supported_idols.$': {"name": vtuber_name.lower(), "guild_id": ctx.guild.id}}})
        else:
            settings.update_one({"name": "supported_idols"}, {'$push': {'supported_idols': {"name": vtuber_name.lower(), "guild_id": ctx.guild.id}}})
        await ctx.send("Set VTuber name to " + vtuber_name)
        print(str(ctx.guild.id) + "-> New Vtuber added: " + vtuber_name)


    @commands.command(name="memberRole", aliases=["setMemberRole"],
        help="Sets the role that should be given to a member who has proven that he has valid access to membership content.\nRequires the ID not the role name or anything else!",
        brief="Sets the role for membership content")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_member_role(self, ctx, id: int):
        if self.check_role_integrity(ctx, id):
            self.set_value_in_server_settings(ctx, "member_role", id)

            await ctx.send("Member role id set to " + str(id))
        else:
            await ctx.send("ID does not refer to a legit role")


    @commands.command(name="logChannel", aliases=["setLogChannel"],
        help="Sets the channel which is used to control the sent memberships.\nRequires the ID not the role name or anything else!",
        brief="Sets the channel for logging")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_log_channel(self, ctx, id: int):
        self.set_value_in_server_settings(ctx, "log_channel", id)

        await ctx.send("Log Channel id set to " + str(id))


    @commands.command(hidden = True, name="modRole")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_mod_role(self, ctx, id: int):
        if self.check_role_integrity(ctx, id):
            self.set_value_in_server_settings(ctx, "mod_role", id)

            await ctx.send("Mod role id set to " + str(id))
        else:
            await ctx.send("ID does not refer to a legit role")


    @commands.command(name="picture", aliases=["setPicture"],
        help="Sets the image that is sent when a membership is about to expire.\n" +
        "It supports link that end with png, jpg or jpeg.",
        brief="Set image for expiration message.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_picture(self, ctx, link: str):
        print("{}: {}".format(str(ctx.guild.id), link))
        from re import search
        match = search(r"http[s]?://[a-zA-Z0-9_\.]+/[a-zA-Z0-9_/]+\.(png|jpeg|jpg)", link)
        if match:
            self.set_value_in_server_settings(ctx, "picture_link", link)
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
        self.set_value_in_server_settings(ctx, "automatic_role", flag)
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
        self.set_value_in_server_settings(ctx, "require_additional_proof", flag)
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
        self.set_value_in_server_settings(ctx, "tolerance_duration", time)
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
        self.set_value_in_server_settings(ctx, "inform_duration", time)
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
        self.set_value_in_server_settings(ctx, "logging", flag)
        await ctx.send("Flag for logging set to " + str(flag))


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
    async def general_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("Please provide a valid id!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please include the argument!")

    def check_role_integrity(self, ctx, id: int):
        if ctx.guild.get_role(id):
            return True
        return False

    def set_value_in_server_settings(self, ctx, setting: str, value):
        settings_db = self.db_cluster[str(ctx.guild.id)]["settings"]

        settings_db.update_one({'kind': setting}, {'$set': {'value': value}})

    @commands.command(hidden = True, name = "createNewSetting")
    @commands.is_owner()
    async def create_new_setting(self, ctx, kind: str, value):
        if Utility.is_integer(value):
            value = int(value)
        else:
            tmp = Utility.text_to_boolean(value)
            if type(tmp) == bool:
                value = tmp

        dbnames = self.db_cluster.list_database_names()

        for server in dbnames:
            if Utility.is_integer(server):
                server_db = self.db_cluster[str(server)]
                settings = server_db["settings"]

                # Create base configuration
                json = { "kind": kind, "value" : value}
                settings.insert_one(json)
        await ctx.send("Added " + kind + " with default value " + str(value))

    @commands.command(hidden = True, name = "newMemberSetting")
    @commands.is_owner()
    async def create_new_member_setting(self, ctx, kind: str, value):
        if Utility.is_integer(value):
            value = int(value)
        else:
            tmp = Utility.text_to_boolean(value)
            if type(tmp) == bool:
                value = tmp

        dbnames = self.db_cluster.list_database_names()

        for server in dbnames:
            if Utility.is_integer(server):
                server_db = self.db_cluster[str(server)]
                for member in server_db['members'].find():
                    # Create base configuration
                    server_db['members'].update_one({"id": member['id']}, {"$set": {kind: value}})
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