from discord.ext import commands
from distest import TestCollector
from distest import run_dtest_bot
from discord import Embed, Member, Status
from distest import TestInterface
import discord
import os
import sys

# The tests themselves

log_channel_id = int(os.getenv("TEST_SERVER1_VERI_CHANNEL_ID"))
test_collector = TestCollector()

@test_collector()
async def setup(interface):

    await interface.assert_reply_embed_equals("$setVTuber Lamy", "Set VTuber name to Lamy")

    await interface.assert_reply_embed_equals("$setVTuber Lamy", "This Vtuber is already mapped to a server!")

    await interface.assert_reply_embed_equals("$memberRole 815151130991656970", "Member role id set to 815151130991656970")

    await interface.assert_reply_embed_equals("$logChannel {}".format(log_channel_id), "Log Channel id set to {}".format(log_channel_id))

    await interface.assert_reply_embed_equals("$auto False", "Flag for automatic role handling set to False")

    await interface.assert_reply_embed_equals("$picture https://pbs.twimg.com/profile_images/1198438854841094144/y35Fe_Jj.jpg", "Image for expiration message set.")

    await interface.assert_reply_embed_equals("$setRequireProof False", "Flag for additional Proof set to False")

    await interface.assert_reply_embed_equals("$setTolerance 1", "Time that users will still have access to the channel after their membership expired set to 1 days.")

    await interface.assert_reply_embed_equals("$setPriorNotice 1", "Users will be notified 1 days before their membership ends.")

    await interface.assert_reply_embed_equals("$enableLogging True", "Flag for logging set to True")

    embed = (
        Embed(
            title="Current Settings",
            description="None",
            color=0x1440de,
        )
        .set_image(
            url="https://pbs.twimg.com/profile_images/1198438854841094144/y35Fe_Jj.jpg"
        )
        .add_field(name='Prefixes', value="$", inline=True)
        .add_field(name='Member Role ID', value="815151130991656970", inline=True)
        .add_field(name='Log Channel ID', value=str(log_channel_id), inline=True)
        .add_field(name='Auto Role Flag', value="False", inline=True)
        .add_field(name='Require Additional Proof', value="False", inline=True)
        .add_field(name='Tolerance Duration', value="1", inline=True)
        .add_field(name='Prior Notice Duration', value="1", inline=True)
    )

    await interface.assert_reply_embed_equals("$settings", embed)

async def send_and_get_verify(interface, vtuber, filepath):
    client = interface.client

    # _channel is the command channel
    await interface.channel.send(content="$verify {}".format(vtuber), file=discord.File(filepath))

    def check(m):
        return m.author == interface.target and m.channel == interface.channel

    return await client.wait_for('message', check=check)

@test_collector()
async def test_verify(interface):
    # NOTE: IMPORTANT WAY TO SEND DMS
    # client = interface.client
    # await client.get_user(517732773943836682).send("aaa")
    # target -> user !!!
    # interface.client._channel -> channel for commands
    
    msg = await send_and_get_verify(interface, "lamy", 'tests/pictures/test1.png')
    

    patterns = {
        "title": str(interface.client.user.id),
        "description": "Main Proof",
    }
    await interface.assert_embed_regex(msg, patterns)

@test_collector()
async def revert_vtuber(interface):
    await interface.assert_reply_embed_equals("$setVTuber aaaaaaaaaaaaaaaaa", "Set VTuber name to aaaaaaaaaaaaaaaaa")


# run test bot
if __name__ == "__main__":
    run_dtest_bot(sys.argv, test_collector)