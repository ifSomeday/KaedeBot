import asyncio
import random, time
import edit_distance as ed
import discord
import praw
import threading
import classes
import markovChaining, saveThread, keys, BSJ, os
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

    chat_command_translation = {"meme" : classes.discordCommands.SEND_MEME, "newmeme" : classes.discordCommands.NEW_MEME,
        "purgememes" : classes.discordCommands.PURGE_MEMES, "help" : classes.discordCommands.HELP,
        "bsjme" : classes.discordCommands.BSJ_MEME, "bsjname" : classes.discordCommands.BSJ_NAME,
        "twitter" : classes.discordCommands.TWITTER, "status" : classes.discordCommands.GET_STEAM_STATUS,
        "leaderboard" : classes.discordCommands.GET_STEAM_LEADERBOARD, "thumbsup" :  classes.discordCommands.THUMBSUP,
        "airguitar" :  classes.discordCommands.AIRGUITAR, "cheerleader" :  classes.discordCommands.CHEERLEADER,
        "chocolate" : classes.discordCommands.CHOCOLATE, "tomato" : classes.discordCommands.TOMATO,
        "transform" : classes.discordCommands.TRANSFORM, "oldmeme" : classes.discordCommands.SEND_OLD_MEME,
        "toggledraft" : classes.discordCommands.TOGGLE_DRAFT_MODE}

    chat_macro_translation = { classes.discordCommands.THUMBSUP : "Kyouko_Thumbs_up.gif", classes.discordCommands.AIRGUITAR : "Kyouko_air_guitar.gif",
        classes.discordCommands.CHEERLEADER : "Kyouko_Cheerleader.gif", classes.discordCommands.CHOCOLATE : "Kyouko_chocolate.gif",
        classes.discordCommands.TOMATO : "Kyouko_tomato.gif", classes.discordCommands.TRANSFORM : "Kyouko_transform.gif"}

    anime_enough = ['133811493778096128', '146490789520867328', '127651622628229120', '225768977115250688', '162830306137735169', '85148771226234880']

    base_draft_message = ("**Round:**__ %s __ **Pick:**__ %s __ (*Overall:* __ %s __)\n"
        "**Captain**__ %s __ picks **Player**__ %s __\n**Player MMR:**__ %s __ **Team Avg:**__ %s __")

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
            if(msg.author.id in anime_enough):
                await client.delete_message(msg)
                if('command' in kwargs):
                    command = kwargs['command']
                    await client.send_file(msg.channel, os.getcwd() + "/dataStores/" + chat_macro_translation[command])
            else:
                await client.send_message(msg.channel, "Sorry, you aren't anime enough. Please contact a weeb if you believe this is in error.")

    async def broadcast_draft_pick(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            #bChannel = client.get_channel('320033818083983361')
            bChannel = client.get_channel('315212408740380672')
            resr = await build_draft_message(row = cmd.args[0])
            draft_messages.append(await client.send_message(bChannel, resr))

    async def build_draft_message(*args, **kwargs):
        row = kwargs['row']
        return(base_draft_message % (str(row[1]), str(row[2]), str(row[0]), str(row[4]), str(row[5]), str(row[6]), str(row[7])))

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
            print(cmd.args[1])
            sid = SteamID(cmd.args[1].account_id)
            await client.send_message(client.get_channel('133812880654073857'), "Inhouse looking for members.\nLooking for " + str(10 - total_members) + " more players\nContact " + cmd.args[1].persona_name + " on steam.\n(<" + sid.community_url +">)")

    async def toggle_draft(*args, **kwargs):
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
