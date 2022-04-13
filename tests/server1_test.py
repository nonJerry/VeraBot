import asyncio
from distest import TestCollector
from distest.exceptions import NoResponseError
from distest import run_dtest_bot
from discord import Embed
import discord
import os
import sys

# The tests themselves

log_channel_id = int(os.getenv("TEST_SERVER1_VERI_CHANNEL_ID"))
test_collector = TestCollector()

@test_collector()
async def setup(interface):

    # making sure it does not run into problems
    await interface.channel.send(content="$setVTuber Aaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    # wait that it does not conflict with first test
    await asyncio.sleep(5)

    # initial settings tests
    await interface.assert_reply_contains("$setVTuber Lamy", "Set VTuber name to Lamy")

    await interface.assert_reply_contains("$setVTuber Lamy", "This Vtuber is already mapped to a server!")

    await interface.assert_reply_contains("$memberRole 815151130991656970", "Member role id set to 815151130991656970")

    await interface.assert_reply_contains("$logChannel {}".format(log_channel_id), "Log Channel id set to {}".format(log_channel_id))

    await interface.assert_reply_contains("$auto False", "Flag for automatic role handling set to False")

    await interface.assert_reply_contains("$picture https://pbs.twimg.com/profile_images/1198438854841094144/y35Fe_Jj.jpg", "Image for expiration message set.")

    await interface.assert_reply_contains("$setRequireProof False", "Flag for additional Proof set to False")

    await interface.assert_reply_contains("$setTolerance 1", "Time that users will still have access to the channel after their membership expired set to 1 days.")

    await interface.assert_reply_contains("$setPriorNotice 1", "Users will be notified 1 days before their membership ends.")

    await interface.assert_reply_contains("$enableLogging True", "Flag for logging set to True")

    embed = (
        Embed(
            title="Current Settings",
            description="None"
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
        .add_field(name='Logging enabled', value="True", inline=True)
        .add_field(name='Threads enabled', value="False", inline=True)
        .add_field(name='Proof Channel ID', value=875848307119902780, inline=True)
    )

    await interface.send_message("$settings")
    await interface.get_delayed_reply(5, interface.assert_embed_equals, embed, None)

async def send_and_get_verify(interface, vtuber, filepath):
    client = interface.client

    # _channel is the command channel
    await interface.channel.send(content="$verify {}".format(vtuber), file=discord.File(filepath))

    def check(m):
        return m.author == interface.target and m.channel == client.get_channel(log_channel_id) # verify channel

    try:
        msg = await client.wait_for('message', check=check, timeout=90.0)
    except asyncio.TimeoutError:
        raise NoResponseError
    return msg


async def assert_proof(interface, vtuber: str, picture: str, expected_date: str):

    msg = await send_and_get_verify(interface, vtuber, picture)

    patterns = {
        "title": str(interface.client.user.id),
        "description": "Main Proof"
    }
    await interface.assert_embed_regex(msg, patterns)

    #  make sure the date is correct
    await interface.assert_message_contains(msg, expected_date)


@test_collector()
async def test_verify(interface):
    # NOTE: interface.client._channel -> channel for commands

    LAMY = "lamy"
    await assert_proof(interface, LAMY, 'tests/pictures/test1.png', "06/06/2021")
    await assert_proof(interface, LAMY, 'tests/pictures/test2.jpg', "11/06/2021")
    await assert_proof(interface, LAMY, 'tests/pictures/test3.png', "26/05/2021")
    await assert_proof(interface, LAMY, 'tests/pictures/test4.png', "29/05/2021")
    await assert_proof(interface, LAMY, 'tests/pictures/test5.png', "26/05/2021")
    await assert_proof(interface, LAMY, 'tests/pictures/test6.png', "15/06/2021")
    await assert_proof(interface, LAMY, 'tests/pictures/test7.png', "14/06/2069")
    await assert_proof(interface, LAMY, 'tests/pictures/test10.png', "Date not detected")



@test_collector()
async def revert_vtuber(interface):
    await interface.assert_reply_contains("$setVTuber aaaaaaaaaaaaaaaaa", "Set VTuber name to aaaaaaaaaaaaaaaaa")


# run test bot
if __name__ == "__main__":
    run_dtest_bot(sys.argv, test_collector)