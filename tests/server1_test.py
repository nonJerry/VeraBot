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
    print(interface.target.send)
    c = interface.channel

    await c.send("$setVTuber Lamy")
    await c.send("$memberRole 815151130991656970")
    await c.send("$logChannel {}".format(log_channel_id))

    await c.send("$auto False")
    await c.send("$picture https://pbs.twimg.com/profile_images/1198438854841094144/y35Fe_Jj.jpg")
    await c.send("setRequireProof False")
    await c.send("$setTolerance 1")
    await c.send("$setPriorNotice 1")
    await c.send("$enableLogging True")

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

    # This image is in WikiMedia Public Domain
    await interface.assert_reply_embed_equals("$settings", embed)
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

async def send_and_get_verify(interface, vtuber, filepath):
    client = interface.client

    # _channel is the command channel
    await client._channel.send(content="$verify {}".format(vtuber), file=discord.File(filepath))

    def check(m):
        return m.author == interface.target and m.channel == client.get_channel(log_channel_id)

    return await client.wait_for('message', check=check)


# run test bot
if __name__ == "__main__":
    run_dtest_bot(sys.argv, test_collector)