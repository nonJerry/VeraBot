import asyncio
import logging
from typing import Optional

import discord
from utility import Utility
class PersistentView(discord.ui.View):
    def __init__(self, member_handler):
        super().__init__(timeout=None)
        self.member_handler = member_handler
        self.database = member_handler.db

    @discord.ui.button(style=discord.ButtonStyle.success, label="Everything fine!", emoji="✅", custom_id="Correct")
    async def handle_correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        server_db = self.database.get_server_db(interaction.guild.id)

        # always only the id
        target_member_id = int(embed.title)

        logging.info("Recognized date correct in %s for user %s.", interaction.guild.id, target_member_id)

        await interaction.response.defer()
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
            if await self.member_handler.set_membership(interaction.message, target_member_id, membership_date,
                                                        False, interaction.user, vtuber):
                await interaction.message.add_reaction('👌')
                await self.remove_buttons(interaction)
                self.stop()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Wrong Date!", emoji=u"\U0001F4C5",
                       custom_id="Change")
    async def handle_change(self, interaction: discord.Interaction, button: discord.ui.Button):
    @discord.ui.button(style=discord.ButtonStyle.danger, label="Not acceptable!", emoji=u"\U0001F6AB",
                       custom_id="Wrong")
    async def handle_denied(self, interaction: discord.Interaction, button: discord.ui.Button):

    async def remove_buttons(self, interaction: discord.Interaction):
        try:
            await interaction.edit_original_response(view=None)
        except discord.errors.NotFound:
            logging.info('Webhook in %s could not be found', interaction.guild.id)
