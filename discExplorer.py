import keys
import discord

import asyncio
from aioconsole import ainput

import pickle
import os
import sys


client = discord.Client()

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

async def waitEnter():
    await ainput("")

def isNum(string):
    try:
        string = int(string)
    except:
        return(False)
    return(True)


async def genericSubMenu(d):
        for i, item in enumerate(d.keys()):
            print("\t%s. %s" % (i + 1, item))
        print("\n\t0. Back")

        val = await ainput(">> ")
        val = val.lower().strip()
        ##val = await client.loop.run_in_executor(None, input())

        print(val)

        if(val == '0'):
            return(0)
        elif(isNum(val)):
            valIdx = int(val) - 1
            keys = list(d.keys())
            if(valIdx in range(0, len(keys))):
                return(keys[valIdx])
        return(1)

async def readChannelMessages(cid):
    num = "a"
    while not(isNum(num)):
        num = await ainput("How many messages to read?[20]:\n>> ")
        if(num == ""):
            num = 20
    num = int(num)
    msgs = []
    async for msg in client.logs_from(client.get_channel(cid), limit=num):
        msgs.append(msg)
    msgs.reverse()
    for msg in msgs:
        print("%s : %s" % (msg.author.display_name, msg.clean_content))
    await waitEnter()
    


async def sendChannelMessage(cid):
    msg = await ainput("What would you like to send?\n>> ")
    
    await client.send_message(client.get_channel(cid), msg)

    print("Sent message!")
    await waitEnter()

async def dumpChannelLog(cid):
    msgs = []
    print("Gathering messages...")
    async for msg in client.logs_from(client.get_channel(cid), limit=sys.maxsize):
        msgs.append(msg)
    print("Messages gathered. Reversing...")
    msgs.reverse()
    print("Messages reversed. Saving to pickle...")
    with open("%s.log" % cid, "wb") as f:
        pickle.dump(msgs, f)
    print("Messages saved to file %s.log" % cid)
    await waitEnter()

async def showMemberMenu(sid):
    print("member menu")

async def showRoleMenu(sid):
    print("role menu")

async def serverStats(sid):
    server = client.get_server(sid)
    print("Server Stats for %s:" % server.name)
    print("\tOwner: %s" % server.owner.name)
    print("\tCreated on: %s" % str(server.created_at))
    print("\t# Channels: %s" % len(list(server.channels)))
    print("\t# Members: %s" % len(list(server.members)))
    await waitEnter()

async def serverInvite(sid):
    inv = await client.create_invite(client.get_server(sid), max_uses=1)
    print("Invite: %s" % inv.code)
    await waitEnter()

async def channelInvite(cid):
    inv = await client.create_invite(client.get_channel(cid), max_uses=1)
    print("Invite: %s" % inv.code)
    await waitEnter()


################################
################################
### OBJECT INTERACTION MENUS ###
################################
################################


async def showServerMenu(sid):
    run = True
    while(run):

        cls()

        server = client.get_server(sid)

        print("%s:" % server.name)

        ret = await genericSubMenu(serverMenu)

        if(ret == 0):
            run = False
        elif(not ret == 1):
            await serverMenu[ret](sid)
        
async def showChannelMenu(cid):
    run = True
    while(run):

        cls()

        channel = client.get_channel(cid)

        print("%s" % channel.name)

        ret = await genericSubMenu(channelMenu)

        if(ret == 0):
            run = False
        elif(not ret == 1):
            await channelMenu[ret](cid)
        

##############################
##############################
### OBJECT SELECTION MENUS ###
##############################
##############################


async def showServersMenu():
    run = True
    while(run):

        cls()

        print("Server Menu:")
        serverList = { server.name : server for server in client.servers }

        ret = await genericSubMenu(serverList)

        if(ret == 0):
            run = False
        elif(not ret == 1):
            await showServerMenu(serverList[ret].id)


async def showChannelsMenu(sid):
    run = True
    while(run):

        cls()

        server = client.get_server(sid)

        channels = {channel.name : channel for channel in server.channels if channel.type == discord.ChannelType.text}

        ret = await genericSubMenu(channels)

        if(ret == 0):
            run = False
        elif(not ret == 1):
            await showChannelMenu(channels[ret].id)
            

mainMenu = { "Servers" : showServersMenu }
serverMenu = { "Channels" : showChannelsMenu, "Members" : showMemberMenu, "Roles" : showRoleMenu, "Stats" : serverStats, "Invite" : serverInvite }
channelMenu = { "Read Messages" : readChannelMessages, "Send Message" : sendChannelMessage, "Dump Log" : dumpChannelLog, "Invite" : channelInvite }

async def explore():
    await client.wait_until_ready()

    run = True

    while(run):
        cls()

        print("Main Menu")
        for i, item in enumerate(mainMenu.keys()):
            print("\t%s. %s" % (i + 1, item))
        print("\n\t0. Exit")
        
        val = await ainput(">> ")
        val = val.lower().strip()

        if(val in ['q', 'quit', 'exit', 'bye', '0']):
            run = False
        elif(isNum(val)):
            valIdx = int(val) - 1
            keys = list(mainMenu.keys())
            if(valIdx in range(0, len(keys))):
                await mainMenu[keys[valIdx]]()

    await client.logout()
    await client.close()

client.loop.create_task(explore())
print("loading explore....")
client.run(keys.TOKEN)


