import gevent.monkey
import sys
if(sys.platform.startswith('linux')):
    gevent.monkey.patch_all()

import discord
import asyncio

import classes
import header

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
        print("here")

        ##fail if no auth
        if(not check_auth(msg.author.id)):
            return
        resp = [""]
        idx = 0 

        ##iterate through roles
        for role in msg.server.roles:
            s = role.name + " : " + role.id + "\n"

            ##split if message would be over 2k in length, the max discord message size
            if(len(resp[idx]) + len(s) >= 2000):
                resp.append("")
                idx += 1

            ##add role to resp
            resp[idx] = resp[idx] + s

        ##send as many responses as needed
        for m in resp:
            await client.send_message(msg.author, m)
        
        ##delete request
        await client.delete_message(msg)


##init commands into main class
def init(chat_command_translation, function_translation):

    ##role dump command
    function_translation[classes.discordCommands.DUMP_ROLES] = dump_roles
    chat_command_translation["dumproles"] = classes.discordCommands.DUMP_ROLES

    return(chat_command_translation, function_translation)