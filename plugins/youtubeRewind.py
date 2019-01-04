import gevent.monkey
import sys
if(sys.platform.startswith('linux')):
    gevent.monkey.patch_all()

import asyncio
import os
import sys
import re
import random
import pickle

import header
import classes

fileLock = asyncio.Lock()

FILE_PATH = os.getcwd() + "/dataStores/rewind.pickle"

URLFINDER = r"((?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/(?:watch\?v=)?\/?[^ \n]*)"

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("ytRewind: " +  str(text), flush = True)
    except:
        print("DiscordBot: Logging error. Probably some retard name", flush = True)

async def loadRewind():
    async with fileLock:
        videos = []
        if(os.path.isfile(FILE_PATH)):
            with open(FILE_PATH, 'rb') as f:
                videos = pickle.load(f)
        return(videos)

async def saveRewind(videos):
    async with fileLock:
        with open(FILE_PATH, 'wb') as f:
            pickle.dump(videos, f)

async def rewind(*args, **kwargs):
    if('msg' in kwargs):

        client = kwargs['client']
        msg = kwargs['msg']
        cmd = kwargs['command']

        if(not msg.channel.id == header.SHRIMP_HOLE):
            return

        videos = await loadRewind()

        if(videos == []):
            await client.send_message(msg.channel, "Building library.. please wait")

            async for message in client.logs_from(msg.channel, limit=sys.maxsize):
                if(not message.author.id == header.MY_DISC_ID):
                    m = re.findall(URLFINDER, message.content)
                    if(not m == []):
                        videos += m

            await saveRewind(videos)
            
        await client.send_message(msg.channel, "Your YouTube rewind is\n %s" % random.choice(videos))

async def onMessageProcessor(message):
    if(message.channel.id == header.SHRIMP_HOLE and not message.author.id == header.MY_DISC_ID):
        m = re.findall(URLFINDER, message.content)
        if(not m == []):
            videos = await loadRewind()
            videos += m
            botLog("added %s to rewind" % str(m))
            await saveRewind(videos)

def init(chat_command_translation, function_translation):
    
    ##add rewind command
    function_translation[classes.discordCommands.REWIND] = rewind
    chat_command_translation["rewind"] = classes.discordCommands.REWIND

    return(chat_command_translation, function_translation)
    