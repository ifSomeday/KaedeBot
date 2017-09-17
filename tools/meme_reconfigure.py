##run this file from the main directory to create a meme database from DMDT
##RECONF_TYPE must be set to the number of context words you want to Save
##file will be output as 'test.pickle', and is immediately ready to be loaded by markovChaining.py
##will NOT load react based memes.

import discord
import sys
import asyncio
import pickle
import markovChaining

client = discord.Client()
RECONF_TYPE = 3

key = input("Discord Token: ")
meme_table = {}

async def get_history():
    ##DMDT
    memes = []
    for channel in client.get_server('133812880654073857').channels:
        try:
            print(channel)
            l = client.logs_from(channel, limit = sys.maxsize)
            async for m in l:
                if(m.content.lower().startswith('!newmeme')):
                    memes.append(m.content[len("!newmeme"):])
        except:
            pass

        with open("log.pickle", 'wb') as f:
            pickle.dump(memes, f)

        for meme in memes:
            markovChaining.addSingle3(meme, meme_table)
        with open("test.pickle", 'wb') as f:
            pickle.dump(meme_table, f)

@client.event
async def on_ready():
    print("discord bot Online")
    await get_history()
    await client.logout()

client.run(key)
