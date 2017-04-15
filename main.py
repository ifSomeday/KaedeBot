import discord
import praw
##keys.py needs to contain a discord TOKEN, PRAW_ID and PRAW_SECRET
import markovChaining, saveThread, keys, BSJ, os
import asyncio
import random, time
import bernoulli_detection

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
                            "Use !meme to get a spicy meme\nUse !newmeme to add your own dank memes")

    if message.content.startswith("!BsjMe"):
        await client.send_message(message.channel, BsjFacts.getFact())

    if message.content.startswith("!BsjName"):
        await client.send_message(message.channel, BsjFacts.bsjName())

    if message.content.startswith("!twitter"):
        await client.send_message(message.channel, "Follow my twitter counterpart!!\nhttps://twitter.com/NameIsBot")

    if message.content.startswith('Can I get a "what what" from my homies?!'):
        if(not str(message.author.id) == str(85148771226234880)):
            await client.send_message(message.channel, "what what")
        else:
            await client.send_message(message.channel, "nope")

    if message.content.startswith("!test"):
        url = message.content[len("!test"):]
        await bernoulli_detection.checkUrlImage("https://cdn.discordapp.com/attachments/213086692683415552/302667850697408523/berger.jpg")

    if(not message.content.startswith('!')):
        ##if(random.randint(0,1000) == 666):
        # if(message.author.name.lower() == "lay your heaven on me"):
        #     newNick = message.author.name + " senpai san"
        #     print(newNick)
        #     client.change_nickname(message.author, newNick)
        #     await client.send_message(message.channel, "(✿◠‿◠)")
        pass

    if len(message.attachments) != 0:
        res = await bernoulli_detection.checkImage(message.attachments)
        print(res)
        if(res == True):
            await client.send_message(message.channel, "Illicit Bernoulli detected!\nPlease be more careful in the future.")



@client.event
async def on_ready():
    print("Bot Online")

@client.event
async def on_message(message):
    await processMessage(client, message)

client.run(keys.TOKEN)
