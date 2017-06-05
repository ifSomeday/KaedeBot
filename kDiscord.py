import asyncio
import random, time
import edit_distance as ed
import discord
import praw
import threading
import classes
import markovChaining, saveThread, keys, BSJ, os, header
from steam import SteamID
from concurrent.futures import ProcessPoolExecutor

def discBot(kstQ, dscQ, draftEvent):

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = discord.Client()
    markovChaining.init()
    ##Save Thread
    sThread = saveThread.saveThread(1800, saveThread.saveTable, "Save-Thread")
    sThread.start()

    BsjFacts = BSJ.BSJText()

    draft_messages = []
    media_messages = {}

    async def sendMessage(channel, string):
        await client.send_message(channel, string)

    async def cmdSendMsg(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            await sendMessage(cmd.args[0], cmd.args[1])

    ##Call and Response
    async def processMessage(client, message):
        if(len(message.attachments) > 0):
            await check_media_message(message)
        if message.content.startswith('!'):
            await client.send_typing(message.channel)
            cMsg = message.content.lower()[1:].split()
            command = header.chat_command_translation[cMsg[0]] if cMsg[0] in header.chat_command_translation else classes.discordCommands.INVALID_COMMAND
            ##TODO: prettier implementation of this:
            if((not command == classes.discordCommands.TOGGLE_DRAFT_MODE) and (message.server.id == '315211723231461386')):
                return
            await function_translation[command](cMsg, msg = message, command = command)
        if(ed.distance(message.content.lower(), 'can I get a "what what" from my homies?!') < 6):
            if(not str(message.author.id) == str(85148771226234880)):
                await client.send_message(message.channel, "what what")
            else:
                await client.send_message(message.channel, "quack quack")


    async def send_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
                table = markovChaining.nd if kwargs['command'] == classes.discordCommands.SEND_MEME else markovChaining.d
                await client.send_message(msg.channel, markovChaining.generateText(table, builder = args[0][1:]))
            else:
                await client.send_message(msg.channel, "Please use that command in an appropriate channel.")

    async def check_media_message(message):
        if(not any(name in message.channel.name for name in ['meme', 'meming', 'afk'])):
            if(message.author.id in media_messages and not message.author.id == '213099188584579072'):
                if(time.time() - media_messages[message.author.id] < 60):
                    await client.delete_message(message)
                    await client.send_message(message.channel, message.author.mention + " please refrain from spamming !!")
                else:
                    media_messages[message.author.id] = time.time()
            else:
                media_messages[message.author.id] = time.time()


    async def add_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            markovChaining.addSingle(msg.content[len("!newmeme"):], markovChaining.nd)
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
            if(any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
                await client.send_message(msg.channel, BsjFacts.getFact())
            else:
                await client.send_message(msg.channel, "Please use that command in an appropriate channel.")

    async def bsj_name(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
                await client.send_message(msg.channel, BsjFacts.bsjName())
            else:
                await client.send_message(msg.channel, "Please use that command in an appropriate channel.")

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
            if(msg.author.id in header.anime_enough):
                await client.delete_message(msg)
                if('command' in kwargs):
                    command = kwargs['command']
                    await client.send_file(msg.channel, os.getcwd() + "/dataStores/" + header.chat_macro_translation[command])
            else:
                await client.send_message(msg.channel, "Sorry, you aren't anime enough. Please contact a weeb if you believe this is in error.")

    async def broadcast_draft_pick(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            #bChannel = client.get_channel('320033818083983361')
            resr = await build_draft_message(row = cmd.args[0])
            bChannel = client.get_channel('315212408740380672')
            draft_messages.append(await client.send_message(bChannel, resr))

    async def build_draft_message(*args, **kwargs):
        row = kwargs['row']
        start = "----------\n" if(not int(row[0]) == 1) else ""
        return(start + (header.base_draft_message % (str(row[1]), str(row[2]), str(row[0]), str(row[4]), str(row[5]), str(row[6]), str(row[7]))))

    async def update_draft_message(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            playerIndex = int(cmd.args[0][0]) - 1
            message = draft_messages[playerIndex]
            resr = await build_draft_message(row = cmd.args[0])
            draft_messages[playerIndex] = await client.edit_message(message, resr)

    async def broadcast_lobby(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            total_members = 0
            for member in cmd.args[0].members:
                if(member.team == 0 or member.team == 1):
                    total_members += 1
            sid = SteamID(cmd.args[1].account_id)
            await client.send_message(client.get_channel('133812880654073857'), "Inhouse looking for members.\nLooking for " + str(10 - total_members) + " more players\nContact " + cmd.args[1].persona_name + " on steam.\n(<" + sid.community_url +">)")

    async def toggle_draft(*args, **kwargs):
        return
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(msg.author.id == '127651622628229120' or msg.author.id == '133811493778096128' or msg.author.id == '85148771226234880'):
                if(draftEvent.is_set()):
                    draftEvent.clear()
                else:
                    draftEvent.set()
                await client.send_message(msg.channel, "draft mode is now " + ("enabled" if draftEvent.is_set() else "disabled"))
            else:
                await client.send_message(msg.channel, "you don't have permission to do that :(")

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
        classes.discordCommands.INVALID_COMMAND : invalid_command, classes.discordCommands.BROADCAST : cmdSendMsg, classes.discordCommands.CHOCOLATE : image_macro,
        classes.discordCommands.TOMATO : image_macro, classes.discordCommands.TRANSFORM : image_macro,
        classes.discordCommands.BROADCAST_LOBBY : broadcast_lobby, classes.discordCommands.SEND_OLD_MEME : send_meme,
        classes.discordCommands.BROADCAST_DRAFT_PICK : broadcast_draft_pick, classes.discordCommands.TOGGLE_DRAFT_MODE : toggle_draft,
        classes.discordCommands.UPDATE_DRAFT_PICK : update_draft_message}

    async def messageHandler(kstQ, dscQ):
        await client.wait_until_ready()
        while(not client.is_closed):
            while(dscQ.qsize() > 0):
                cmd = dscQ.get()
                await function_translation[cmd.command](cmd = cmd)

            await asyncio.sleep(1)


    @client.event
    async def on_ready():
        print("discord bot Online", flush=True)
        await client.change_presence(game=discord.Game(name='Yuru Yuri San Hai !!'))


    @client.event
    async def on_message(message):
        await processMessage(client, message)

    client.loop.create_task(messageHandler(kstQ, dscQ))
    client.run(keys.TOKEN)
