# External
from discord.ext import commands
# Python
import logging
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
    async def view_members(self, ctx, *member_id: int):
        # always only one id at max
        if member_id:
            logging.info("%s used viewMember with ID in %s", ctx.author.id, ctx.guild.id)
            await self.member_handler.view_membership(ctx.message, member_id[0])
        else:
            logging.info("%s viewed all members in %s", ctx.author.id, ctx.guild.id)
            await self.member_handler.view_membership(ctx.message, None)


    @commands.command(name="addMember", aliases=["set_membership", "setMember"],
        help="Gives the membership role to the user whose ID was given.\n" + 
        "<date> has to be in the format dd/mm/yyyy.\n" +
        "It equals the date shown on the sent screenshot",
        brief="Gives the membership role to a user")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def set_membership(self, ctx, member_id: int, date):
        logging.info("%s used addMember in %s", ctx.author.id, ctx.guild.id)
        await self.member_handler.set_membership(ctx.message, member_id, date)

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
    async def del_membership(self, ctx, member_id: int, *text):
        logging.info("%s used delMember in %s", ctx.author.id, ctx.guild.id)
        await self.member_handler.del_membership(ctx.message, member_id, text)

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
                     