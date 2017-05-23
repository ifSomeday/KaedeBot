import asyncio
import random, time
import edit_distance as ed
import discord
import praw
import threading
import classes
import markovChaining, saveThread, keys, BSJ, os
from concurrent.futures import ProcessPoolExecutor

def discBot(kstQ, dscQ):

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = discord.Client()
    markovChaining.init()
    ##Save Thread
    sThread = saveThread.saveThread(1800, saveThread.saveTable, "Save-Thread")
    sThread.start()

    BsjFacts = BSJ.BSJText()

    chat_command_translation = {"meme" : classes.discordCommands.SEND_MEME, "newmeme" : classes.discordCommands.NEW_MEME,
        "purgememes" : classes.discordCommands.PURGE_MEMES, "help" : classes.discordCommands.HELP,
        "BsjMe" : classes.discordCommands.BSJ_MEME, "BsjName" : classes.discordCommands.BSJ_NAME,
        "twitter" : classes.discordCommands.TWITTER, "status" : classes.discordCommands.GET_STEAM_STATUS,
        "leaderboard" : classes.discordCommands.GET_STEAM_LEADERBOARD, "thumbsup" :  classes.discordCommands.THUMBSUP,
        "airguitar" :  classes.discordCommands.AIRGUITAR, "cheerleader" :  classes.discordCommands.CHEERLEADER}

    chat_macro_translation = { classes.discordCommands.THUMBSUP : "Kyouko_Thumbs_up.gif", classes.discordCommands.AIRGUITAR : "Kyouko_air_guitar.gif",
        classes.discordCommands.CHEERLEADER : "Kyouko_Cheerleader.gif"}

    anime_enough = ['133811493778096128', '146490789520867328', '127651622628229120', '225768977115250688', '162830306137735169', '85148771226234880']

    async def sendMessage(channel, string):
        await client.send_message(channel, string)

    async def cmdSendMsg(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            await sendMessage(cmd.args[0], cmd.args[1])

    ##Call and Response
    async def processMessage(client, message):
        if message.content.startswith('!'):
            await client.send_typing(message.channel)
            cMsg = message.content.lower()[1:].split()
            command = chat_command_translation[cMsg[0]] if cMsg[0] in chat_command_translation else classes.discordCommands.INVALID_COMMAND
            await function_translation[command](cMsg, msg = message, command = command)
        if(ed.distance(message.content.lower(), 'can I get a "what what" from my homies?!') < 6):
            if(not str(message.author.id) == str(85148771226234880)):
                await client.send_message(message.channel, "what what")
            else:
                await client.send_message(message.channel, "quack quack")


    async def send_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, markovChaining.generateText())

    async def add_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            markovChaining.addSingle(msg.content[len("!newmeme"):])
            await client.send_message(msg.channel, "new meme added, thanks!")

    async def purge_memes(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "That command is currently disabled.")

    async def help_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "Use !meme to get a spicy meme\nUse !newmeme to add your own dank memes\nUse !MsjMe to get BSJ memes\nUse !BsjName to get your BSJ Name\nUse !twitter to see my twitter counterpart")

    async def bsj_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, BsjFacts.getFact())

    async def bsj_name(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, BsjFacts.bsjName())

    async def twitter(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "Follow my twitter counterpart !!\nhttps://twitter.com/NameIsBot")

    async def steam_status(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            kstQ.put(classes.command(classes.steamCommands.STATUS_4D, [msg.channel]))

    async def steam_leaderboard(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            sMsg = msg.content.split()
            if(len(sMsg) > 1):
                spots =  sMsg[1]
            else :
                spots = 3
            kstQ.put(classes.command(classes.steamCommands.LEADERBOARD_4D, [msg.channel, str(spots)]))

    async def image_macro(*args, **kwargs):
        if('msg' in kwargs):

            msg = kwargs['msg']
            if(msg.author.id in anime_enough):
                await client.delete_message(msg)
                if('command' in kwargs):
                    command = kwargs['command']
                    await client.send_file(msg.channel, os.getcwd() + "/dataStores/" + chat_macro_translation[command])
            else:
                await client.send_message(msg.channel, "Sorry, you aren't anime enough. Please contact someone who is if you believe this is in error.")

    async def invalid_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "invalid command")

    function_translation = {classes.discordCommands.SEND_MEME : send_meme, classes.discordCommands.NEW_MEME : add_meme,
        classes.discordCommands.PURGE_MEMES : purge_memes, classes.discordCommands.HELP : help_command,
        classes.discordCommands.BSJ_MEME : bsj_meme, classes.discordCommands.BSJ_NAME : bsj_name ,
        classes.discordCommands.TWITTER : twitter, classes.discordCommands.GET_STEAM_STATUS : steam_status,
        classes.discordCommands.GET_STEAM_LEADERBOARD : steam_leaderboard, classes.discordCommands.THUMBSUP : image_macro,
        classes.discordCommands.AIRGUITAR : image_macro, classes.discordCommands.CHEERLEADER : image_macro,
        classes.discordCommands.INVALID_COMMAND : invalid_command, classes.discordCommands.BROADCAST : cmdSendMsg}

    async def messageHandler(kstQ, dscQ):
        await client.wait_until_ready()
        while(not client.is_closed):
            if(dscQ.qsize() > 0):
                cmd = dscQ.get()
                print("found discord command")
                await function_translation[cmd.command](cmd = cmd)

            await asyncio.sleep(1)


    @client.event
    async def on_ready():
        print("discord bot Online")



    @client.event
    async def on_message(message):
        await processMessage(client, message)

    client.loop.create_task(messageHandler(kstQ, dscQ))
    client.run(keys.TOKEN)
