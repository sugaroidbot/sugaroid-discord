# bot.py
import importlib
import sys
import os
import random
import shlex
import shutil
import subprocess
import traceback
import psutil
import discord
import sugaroid_commands as scom
from datetime import datetime
from nltk import word_tokenize
import sugaroid as sug
from sugaroid import sugaroid
from sugaroid import version
from dotenv import load_dotenv
import time
from datetime import timedelta

process = psutil.Process()
init_cpu_time = process.cpu_percent()


load_dotenv()
token = os.getenv("DISCORD_TOKEN")
sg = sugaroid.Sugaroid()
sg.toggle_discord()
client = discord.Client()
interrupt_local = False
start_time = datetime.now()
message_length_limit = 1990


formatters = {
    "<b>": "**",
    "</b>": "**",
    "<i>": "_",
    "</i>": "_",
    "<pre><code>": "```",
    "</code></pre>": "```",
}


def split_into_packets(response: str) -> list:
    messages = []
    for i in range(0, len(response), message_length_limit):
        messages.append(response[i : i + message_length_limit])

    broken_messages = []
    for message in messages:
        broken_messages.extend(message.split("<br>"))

    return broken_messages


def format_messages(message: str) -> str:
    new_message = message
    for i in formatters:
        new_message = new_message.replace(i, formatters[i])
    return new_message


async def update_sugaroid(message, branch="master"):
    # initiate and announce to the user of the upgrade
    await message.channel.send("Updating my brain with new features :smile:")

    # execute pip3 install
    pip = shutil.which("pip")
    pip_popen_subprocess = subprocess.Popen(
        shlex.split(
            f"{pip} install --upgrade --force-reinstall --no-deps "
            f"https://github.com/srevinsaju/sugaroid/archive/{branch}.zip"
        ),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    # reload modules
    os.chdir("/")
    importlib.reload(sug)
    importlib.reload(sugaroid)
    importlib.reload(version)

    # updating the bot
    os.chdir(os.path.dirname(sug.__file__))
    git = shutil.which("git")
    # reset --hard
    git_reset_popen_subprocess = subprocess.Popen(
        shlex.split(f"{git} reset --hard origin/master"),
        stdout=sys.stdout,
        stderr=sys.stderr,
    ).wait(500)
    # git pull
    git_pull_popen_subprocess = subprocess.Popen(
        shlex.split(f"{git} pull"), stdout=sys.stdout, stderr=sys.stderr
    )

    importlib.reload(scom)

    await client.change_presence(
        activity=discord.Game(
            name="v{} since {:02d}:{:02d} UTC".format(
                version.VERSION, datetime.utcnow().hour, datetime.utcnow().minute
            )
        )
    )
    await message.channel.send("Update completed. :smile:")
    await message.channel.send("Restarting myself :zzz:")
    sys.exit(1)


@client.event
async def on_ready():
    print(f"{client.user.name} has connected to Discord!")
    os.chdir(os.path.dirname(sug.__file__))
    await client.change_presence(
        activity=discord.Game(
            name="v{} since {:02d}:{:02d} UTC".format(
                version.VERSION, datetime.utcnow().hour, datetime.utcnow().minute
            )
        )
    )


@client.event
async def on_message(message):
    if message.author == client.user:
        # print("Ignoring message sent by another Sugaroid Instance")
        return
    if isinstance(message.channel, discord.channel.DMChannel):
        # ban private messages to sugaroid
        return
    global interrupt_local

    if any(
        (
            message.content.startswith(f"<@{client.user.id}>"),
            message.content.startswith(f"<@!{client.user.id}>"),
            message.content.startswith("!S"),
        )
    ):
        # make the user aware that Sugaroid received the message
        async with message.channel.typing():
            # clean the message
            msg = (
                message.content.replace(f"<@{client.user.id}>", "")
                .replace(f"<@!{client.user.id}>", "")
                .replace("!S", "")
                .strip()
            )

            command_processor = scom.SugaroidDiscordCommands(client)

            is_valid_command = await command_processor.call_command(msg, message)
            # print("Recv", is_valid_command)
            if is_valid_command:
                return

            elif "update" in msg and len(msg) <= 7:
                if str(message.author) == "srevinsaju#8324":
                    parts = msg.split()[-1]
                    if parts.lower() == "update":
                        parts = "master"
                    await update_sugaroid(message, parts)
                else:
                    # no permissions
                    await message.channel.send(
                        f"I am sorry @{message.author}. I would not be able to update myself.\n"
                        f"Seems like you do not have sufficient permissions"
                    )
                return

            elif "stop" in message.content and "learn" in message.content:
                if str(message.author) == "srevinsaju#8324":
                    global interrupt_local
                    interrupt_local = False
                    await message.channel.send("InterruptAdapter terminated")
                else:
                    await message.channel.send(
                        f"I am sorry @{message.author}. I would not be able to update myself.\n"
                        f"Seems like you do not have sufficient permissions"
                    )
                return
            try:
                response = sg.parse(msg)
            except Exception:
                # some random error occured. Log it
                error_message = traceback.format_exc(chain=True)
                response = (
                    "```py\nAn unhandled exception occurred: " + error_message + "```"
                )
            print(f"sugaroid: {response}")
            for packet in split_into_packets(str(response)):
                if packet:
                    # only try to send if the message is not empty
                    await message.channel.send(format_messages(packet))
            return
        return

    elif interrupt_local:
        token = word_tokenize(message.content)
        for i in range(len(token)):
            if str(token[i]).startswith("@"):
                token.pop(i)
        if len(token) <= 5:
            messages = " ".join(token)
            author = message.author.mention
            sg.append_author(author)
            sg.interrupt_ds()
            response = sg.parse(messages)
            # print(response, "s" * 5)
            await message.channel.send(format_messages(response))
        return


@client.event
async def on_member_join(member):
    for channel in member.server.channels:
        if channel.name == "general":
            await channel.send(channel, "Welcome {}".format(str(member)))


client.run(token)
