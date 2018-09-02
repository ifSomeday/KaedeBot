import gevent.monkey
import sys
if(sys.platform.startswith('linux')):
    gevent.monkey.patch_all()

import discord
import asyncio
import sys

import classes
import header

from plugins import shadowCouncilSecret

##check if a user is authorized for develop commands
def check_auth(s):
    if(s == header.GWENHWYFAR):
        return(True)
    return(False)

##dumps a list of roles and ids for a server
async def dump_roles(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        client = kwargs['client']

        ##fail if no auth
        if(not check_auth(msg.author.id)):
            return
        resp = [""]
        idx = 0 

        ##iterate through roles
        for role in msg.server.roles:
            s = role.name + " : " + role.id + "\n"

            ##split if message would be over 2k in length, the max discord message size (plus a couple for formatting)
            if(len(resp[idx]) + len(s) >= 1990):
                resp.append("")
                idx += 1

            ##add role to resp
            resp[idx] = resp[idx] + s

        ##send as many responses as needed
        for m in resp:
            await client.send_message(msg.author, "```\n" + m + "\n```")
        
        ##delete request
        await client.delete_message(msg)

async def test_verifier(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        client = kwargs['client']

        ##fail if no auth
        if(not check_auth(msg.author.id)):
            return

        ##fail if on linux (dont want to check current verifier)
        if(sys.platform.startswith("linux")):
            return

        total = 0
        passing = 0
        async for message in client.logs_from(client.get_channel(header.SHADOW_COUNCIL_CHANNEL), limit=sys.maxsize):
            total += 1
            if(await shadowCouncilSecret.shadowCouncilVerifier(message, client)):
                passing += 1
        await client.send_message(msg.channel, "With current verifier, " + str(passing) + "/" + str(total) + " (" + str(round(passing/total, 2)) + "%) of messages in the current shadow council would pass.")

        

##init commands into main class
def init(chat_command_translation, function_translation):

    ##role dump command
    function_translation[classes.discordCommands.DUMP_ROLES] = dump_roles
    chat_command_translation["dumproles"] = classes.discordCommands.DUMP_ROLES

    #check verifier
    function_translation[classes.discordCommands.CHECK_VERIFIER] = test_verifier
    chat_command_translation["testverifier"] = classes.discordCommands.CHECK_VERIFIER

    return(chat_command_translation, function_translation)