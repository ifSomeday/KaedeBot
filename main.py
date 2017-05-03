import discord
import praw
##keys.py needs to contain a discord TOKEN, PRAW_ID and PRAW_SECRET
import markovChaining, saveThread, keys, BSJ, os
import asyncio
import random, time
import bernoulli_detection
import edit_distance as ed

testingEnabled= False





##fixes race conditions lol
time.sleep(15)

##Praw
client = discord.Client()
markovChaining.init()

##Save Thread
sThread = saveThread.saveThread(1800, saveThread.saveTable, "Save-Thread")
sThread.start()

##Bsj Facts
BsjFacts = BSJ.BSJText()

async def sendMessage(channel, string):
    await client.send_message(channel, string)

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


@client.event
async def on_ready():
    print("Bot Online")

@client.event
async def on_message(message):
    await processMessage(client, message)

client.run(keys.TOKEN)
