import discord
import praw
##keys.py needs to contain a discord TOKEN, PRAW_ID and PRAW_SECRET
import markovChaining, saveThread, keys, BSJ, os
import asyncio

os.chdir("/home/pi/KaedeBot/")

##Praw
client = discord.Client()
markovChaining.init()

##Save Thread
sThread = saveThread.saveThread(1800, saveThread.saveTable, "Save-Thread")
sThread.start()

##Bsj Facts
BsjFacts = BSJ.BSJText()

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



@client.event
async def on_ready():
    print("Bot Online")

@client.event
async def on_message(message):
    await processMessage(client, message)

client.run(keys.TOKEN)
