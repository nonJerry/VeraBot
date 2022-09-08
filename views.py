import asyncio
import logging
from typing import Optional

import discord
from discord import ui

from utility import Utility


class DateModal(ui.Modal, title='Date Selection'):
    date = ui.TextInput(label='What is the correct date?', style=discord.TextStyle.short, required=True, min_length=8,
                        max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class DenialModal(ui.Modal, title='Denial Message'):
    message = ui.TextInput(label='What do you want to tell the person?', style=discord.TextStyle.paragraph,
                           required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class PersistentView(discord.ui.View):
    def __init__(self, member_handler):
        super().__init__(timeout=None)
        self.member_handler = member_handler
        self.database = member_handler.db

    @discord.ui.button(style=discord.ButtonStyle.success, label="Everything fine!", emoji="✅", custom_id="Correct")
    async def handle_correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = interaction.message.embeds[0]
        server_db = self.database.get_server_db(interaction.guild.id)

        # always only the id
        target_member_id = int(embed.title)

        logging.info("Recognized date correct in %s for user %s.", interaction.guild.id, target_member_id)

        if server_db.get_automatic():
            await interaction.message.add_reaction('👌')
            self.stop()
        else:
            membership_date = embed.fields[0].value

            # set membership
            if Utility.is_multi_server(interaction.guild.id):
                vtuber = embed.fields[1].value
            else:
                vtuber = None
            if await self.member_handler.set_membership(interaction, target_member_id, membership_date,
                                                        False, interaction.user, vtuber):
                await interaction.message.add_reaction('👌')
                await self.remove_buttons(interaction)
                await interaction.followup.send("Finished Verification Process", ephemeral=True)
                self.stop()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Wrong Date!", emoji=u"\U0001F4C5",
                       custom_id="Change")
    async def handle_change(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DateModal()
        await interaction.response.send_modal(modal)

        if await modal.wait():
            await interaction.response.send_message(f'You took too long, please press the button again!',
                                                    ephemeral=True)
        else:
            msg = interaction.message
            embed = msg.embeds[0]

            # always only the id
            target_member_id = int(embed.title)

            logging.info("Wrong date recognized in %s for user %s.", interaction.guild.id, target_member_id)
            await interaction.followup.send(f'The used date was {modal.date.value}!')
            if Utility.is_multi_server(interaction.guild.id):
                vtuber = embed.fields[1].value
            else:
                vtuber = None
            if await self.member_handler.set_membership(interaction, target_member_id, modal.date.value, False,
                                                        interaction.user, vtuber):
                await msg.add_reaction('👍')
                await self.remove_buttons(interaction)
                await interaction.followup.send("Finished Verification Process", ephemeral=True)
                self.stop()
            else:
                return False

    @discord.ui.button(style=discord.ButtonStyle.danger, label="Not acceptable!", emoji=u"\U0001F6AB",
                       custom_id="Wrong")
    async def handle_denied(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DenialModal()
        await interaction.response.send_modal(modal)

        if await modal.wait():
            await interaction.followup.send(f'You took too long, please press the button again!',
                                                    ephemeral=True)
        else:
            msg = interaction.message
            embed = msg.embeds[0]

            # always only the id
            target_member_id = int(embed.title)

            target_member = self.member_handler.bot.get_user(target_member_id)
            if Utility.is_multi_server(msg.guild.id):
                server = msg.guild.name
            else:
                server = Utility.get_vtuber(msg.guild.id) + " server"
            await target_member.send("{}:\n{}".format(server, modal.message))
            await interaction.followup.send("Message was sent by `{}` to {}:\n{}".format(interaction.user.mention, target_member.mention, modal.message))

            if Utility.is_multi_server(interaction.guild.id):
                vtuber = embed.fields[1].value
            else:
                vtuber = None

            if self.database.get_server_db(msg.guild.id).get_automatic():
                await self.member_handler.del_membership(msg, target_member_id, None, False, False, vtuber)
                # set embed
            embed.description = "**DENIED**\nUser: {}\nBy: {}".format(target_member.mention, interaction.user)
            await msg.edit(content=msg.content, embed=embed)
            await msg.add_reaction('👎')
            await self.remove_buttons(interaction)
            await interaction.followup.send("Finished Verification Process", ephemeral=True)
            return True

    async def remove_buttons(self, interaction: discord.Interaction):
        try:
            await interaction.edit_original_response(view=None)
        except discord.errors.NotFound:
            logging.info('Webhook in %s could not be found', interaction.guild.id)
