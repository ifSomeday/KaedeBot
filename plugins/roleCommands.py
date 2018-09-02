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

        update, addRole, removeRole = await add_find_role(roleRequest, msg, client)

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
            
async def remove_role(*args, **kwargs):
    if('msg' in kwargs):

        ##unpack from args
        msg = kwargs['msg']
        client = kwargs['client']
        cMsg = args[0]
        roleRequest = ' '.join(cMsg[1:])

        update, addRole, removeRole = await remove_find_role(roleRequest, msg, client)

        ##update roles
        if(update):
            await client.remove_roles(msg.author, addRole)
            await pm_wrapper(client, msg.author, "Removed role '" + addRole.name + "'")
        await client.delete_message(msg)
        return

async def add_find_role(roleRequest, msg, client):
    return await __find_role(roleRequest, msg, client, False)

async def remove_find_role(roleRequest, msg, client):
    return await __find_role(roleRequest, msg, client, True)

async def __find_role(roleRequest, msg, client, remove):
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
                    elif(role.id in removeIds and not remove):
                        if(role in msg.author.roles):
                            removeRole.append(role)

                if(addRole == None):
                    update = False
                    await pm_wrapper(client, msg.author, "Unable to add role '" + addRole.name + "', as the role does not exist.")

                elif(not roleLimit == -1 and not remove):
                    roleCount = 0
                    for member in msg.server.members:
                        for role in member.roles:
                            if(role.id == addRole.id):
                                roleCount += 1
                    if(roleCount >= roleLimit):
                        update = False
                        await pm_wrapper(client, msg.author, "Unable to add role '" + addRole.name + "', as the user limit for that role has been reached.")

                return(update, addRole, removeRole)

        await pm_wrapper(client, msg.author, "Unable to match requested role '" + roleRequest + "'")
        return(False, None, None)


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

    ##remove role command
    function_translation[classes.discordCommands.REMOVE_ROLE] = remove_role
    chat_command_translation["removerole"] = classes.discordCommands.REMOVE_ROLE
    chat_command_translation["rmrole"] = classes.discordCommands.REMOVE_ROLE

    ##role help command
    function_translation[classes.discordCommands.ROLE_HELP] = role_help
    chat_command_translation["rolehelp"] = classes.discordCommands.ROLE_HELP

    return(chat_command_translation, function_translation)