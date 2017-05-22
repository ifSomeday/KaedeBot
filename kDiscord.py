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

    async def sendMessage(channel, string):
        await client.send_message(channel, string)

    async def cmdSendMsg(*args, **kwargs):
        await sendMessage(args[0], args[1])

    ##Call and Response
    async def processMessage(client, message):
        if message.content.startswith("!meme"):
            await client.send_message(message.channel, markovChaining.generateText())

        if message.content.startswith("!newmeme"):
            new_meme = message.content[len("!newmeme"):]
            print(new_meme)
            markovChaining.addSingle(new_meme)
            await client.send_message(message.channel, "new meme added, thanks!")

        if message.content.startswith("!purgememes"):
            if(message.author.name.lower() == "lay your heaven on me"):
                markovChaining.clearTable()
                markovChaining.addTable(markovChaining.download(markovChaining.SUBREDDIT, 250))
                markovChaining.dumpTable(markovChaining.TABLE_NAME)
                await client.send_message(message.channel, "memes purged.")
            else:
                await client.send_message(message.channel, "permission denied.")

        if message.content.startswith("!help"):
            await client.send_message(message.channel,
                                "Use !meme to get a spicy meme\nUse !newmeme to add your own dank memes\nUse !MsjMe to get BSJ memes\nUse !BsjName to get your BSJ Name\nUse !twitter to see my twitter counterpart")

        if message.content.startswith("!BsjMe"):
            await client.send_message(message.channel, BsjFacts.getFact())

        if message.content.startswith("!BsjName"):
            await client.send_message(message.channel, BsjFacts.bsjName())

        if message.content.startswith("!twitter"):
            await client.send_message(message.channel, "Follow my twitter counterpart!!\nhttps://twitter.com/NameIsBot")

        if(ed.distance(message.content.lower(), 'can I get a "what what" from my homies?!') < 6):
            if(not str(message.author.id) == str(85148771226234880)):
                await client.send_message(message.channel, "what what")
            else:
                await client.send_message(message.channel, "quack quack")


        if message.content.startswith("!status"):
            await client.send_typing(message.channel)
            kstQ.put(classes.command(classes.steamCommands.STATUS, [message.channel]))

    print("get ere")

    # async def messageHandler(*args, **kwargs):
    #     while(True):
    #         dscQ = args[0]
    #         kstQ = args[1]
    #         print("calling message handler")
    #         cmd = dscQ.get()
    #         if(cmd):
    #             print("found command")
    #             if(cmd.command == classes.discordCommands.BROADCAST):
    #                 print("sending status")
    #                 await client.send_message(cmd.args[0], cmd.args[1])
    #
    #         await asyncio.sleep(10.0)

    async def messageHandler(kstQ, dscQ):
        await client.wait_until_ready()
        while(not client.is_closed):
            if(dscQ.qsize() > 0):
                cmd = dscQ.get()
                print("found command")
                if(cmd.command == classes.discordCommands.BROADCAST):
                    print("found command")
                    print("sending status")
                    #loop.run_until_complete(sendMessage(args[0],args[1]))
                    await client.send_message(cmd.args[0], cmd.args[1])
            await asyncio.sleep(1)



    async def my_background_task(test1, test2):
        await client.wait_until_ready()
        counter = 0
        channel = discord.Object(id='213086692683415552')
        while not client.is_closed:
            print(test1, test2)
            counter += 1
            await client.send_message(channel, counter)
            await asyncio.sleep(1) # task runs every 1 seconds

    #tsk = asyncio.ensure_future(loop.run_in_executor(executor, messageHandler, args=[kstQ, dscQ]))


    @client.event
    async def on_ready():
        print("Bot Online")



    @client.event
    async def on_message(message):
        await processMessage(client, message)

    print("so we get here")
    client.loop.create_task(messageHandler(kstQ, dscQ))
    #client.loop.create_task(my_background_task(3, 4))
    print("and here?")
    client.run(keys.TOKEN)
