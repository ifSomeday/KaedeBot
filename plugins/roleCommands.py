import gevent.monkey
import sys
if(sys.platform.startswith('linux')):
    gevent.monkey.patch_all()

import discord
import asyncio

import classes
import edit_distance
from dataStores import roles

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("RoleCommands: " +  str(text), flush = True)
    except:
        print("RoleCommands: Logging error. Probably some retard name", flush = True)

async def pm_wrapper(client, user, message):
    try:
        await client.send_message(user, message)
    except:
        botLog("unable to send message, user probably does not allow PMs: " + user.name)

async def add_role(*args, **kwargs):
    if('msg' in kwargs):

        ##unpack from args
        msg = kwargs['msg']
        client = kwargs['client']
        cMsg = args[0]
        roleRequest = ' '.join(cMsg[1:])

        ##if this server has role support
        if(msg.server.id in roles.roles):
            svr = roles.roles[msg.server.id]

            ##look through groups
            for group in svr['groups']:
                roleId = 0
                removeIds = []
                roleLimit = -1

                ##look through roles
                for role in group['roles']:
                    if(edit_distance.distance(role['name'].lower(), roleRequest.lower()) < 3):
                        if('limit' in role):
                            roleLimit = role['limit']
                        roleId = role["id"]
                    elif('limited' in group and group['limited']):
                        removeIds.append(role['id'])
                
                ##if we found a role
                if(not roleId == 0):
                    addRole = None
                    removeRole = []
                    update = True

                    ##get actual role objects
                    for role in msg.server.roles:
                        if(role.id == roleId):
                            addRole = role
                        elif(role.id in removeIds):
                            if(role in msg.author.roles):
                                removeRole.append(role)

                    if(not roleLimit == -1):
                        roleCount = 0
                        for member in msg.server.members:
                            for role in member.roles:
                                if(role.id == addRole.id):
                                    roleCount += 1
                        if(roleCount >= roleLimit):
                            update = False
                            await pm_wrapper(client, msg.author, "Unable to add role '" + addRole.name + "', as the user limit for that role has been reached.")

                    ##update roles
                    if(update):
                        out = ""
                        for role in removeRole:
                            out += " " + role.name
                        botLog(out)
                        await client.add_roles(msg.author, addRole)
                        await pm_wrapper(client, msg.author, "Added role '" + addRole.name + "'")
                        await client.remove_roles(msg.author, *removeRole)
                    await client.delete_message(msg)
                    return
            
            await pm_wrapper(client, msg.author, "Unable to match requested role '" + roleRequest + "'")
            await client.delete_message(msg)
            

async def role_help(*args, **kwargs):
    if('msg' in kwargs):

        ##unpack from args
        msg = kwargs['msg']
        client = kwargs['client']

        ##if this server has role support
        if(msg.server.id in roles.roles):
            svr = roles.roles[msg.server.id]
            output = "You can request roles with `!role` or `!addrole`\nCurrently available roles in " + msg.server.name + " are:\n\n"

            ##look through groups
            for group in svr['groups']:
                if(len(group['roles']) > 0):
                    output += "**" + group['category'] + "**: " + group['description'] + "\n"

                    ##add limited text
                    if('limited' in group and group['limited']):
                        output += "*You can only have 1 role from this category at a time.*\n"
                    
                    ##look through roles
                    for role in group['roles']:
                        output += "\t" + role['name'] + "\n"

                        ##add limited roles
                        if('limit' in role):
                            output += "\t\t*Limit*: " + str(role['limit']) + " Users\n"
                    output += '\n'

        ##send message
        await client.send_message(msg.channel, output)

async def monster_hunter_workaround(*args, **kwargs):
    client = kwargs['client']
    msg = kwargs['msg']
    cMsg = ["role", "Monster", "Hunter"]
    await add_role(cMsg, msg=msg, client=client)

def init(chat_command_translation, function_translation):

    ##add role command
    function_translation[classes.discordCommands.ADD_ROLE] = add_role
    chat_command_translation["addrole"] = classes.discordCommands.ADD_ROLE
    chat_command_translation["role"] = classes.discordCommands.ADD_ROLE

    ##workaround
    function_translation[666] = monster_hunter_workaround
    chat_command_translation["mh"] = 666
    chat_command_translation["mhme"] = 666

    ##role help command
    function_translation[classes.discordCommands.ROLE_HELP] = role_help
    chat_command_translation["rolehelp"] = classes.discordCommands.ROLE_HELP

    return(chat_command_translation, function_translation)