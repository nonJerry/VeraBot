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
    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Wrong Date!", emoji=u"\U0001F4C5",
                       custom_id="Change")
    async def handle_change(self, interaction: discord.Interaction, button: discord.ui.Button):
    @discord.ui.button(style=discord.ButtonStyle.danger, label="Not acceptable!", emoji=u"\U0001F6AB",
                       custom_id="Wrong")
    async def handle_denied(self, interaction: discord.Interaction, button: discord.ui.Button):
