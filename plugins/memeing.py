##builtin
import pickle
import re
import time

##3rd party
import praw
import discord
import asyncio

##local
import markovChaining
import BSJ
import classes

markovChaining.init()
BsjFacts = BSJ.BSJText()

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("MemeingPlugin: " +  str(text), flush = True)
    except:
        print("MemeingPlugin: Logging error. Probably some retard name", flush = True)

async def send_meme(*args, **kwargs):
    """
    builds, validates, and sends a meme message
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        cfg = kwargs['cfg']
        client = kwargs['client']
        if(cfg.checkMessage("meme", msg)):##any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
            table = markovChaining.nd if kwargs['command'] == classes.discordCommands.SEND_MEME else markovChaining.d
            i = 0
            meme_base = msg.content.split()
            st = time.time()
            meme = markovChaining.generateText3(table, builder = meme_base[1:])
            while((meme.strip().startswith("!") or len(meme.strip()) == 0) and i < 10):
                i += 1
                meme = markovChaining.generateText3(table, builder = [])
                botLog("Invalid meme, rebuilding")
            if(meme.strip().startswith("!") or len(meme.strip()) == 0):
                return
            et1 = time.time()
            meme = re.sub(r"@everyone", r"everyone", meme)
            for s in re.finditer(r"<@(\d+)>", meme):
                meme = meme.replace(s.group(0), (await client.get_user_info(s.group(1))).name)
            et2 = time.time()
            botLog("build meme: " + str(et1 - st) + "\treplace: " + str(et2 - et1))
            await client.send_message(msg.channel, meme)


async def add_meme(*args, **kwargs):
    """
    adds a new meme
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        cfg = kwargs['cfg']
        client = kwargs['client']
        if(cfg.checkMessage("meme", msg)):
            markovChaining.addSingle3(msg.content[len("!newmeme"):], markovChaining.nd)
            await client.send_message(msg.channel, "new meme added, thanks!")

async def purge_memes(*args, **kwargs):
    """
    purges the meme database. Command is currently disabled
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        cfg = kwargs['cfg']
        client = kwargs['client']
        if(cfg.checkMessage("meme", msg)):
                msg = kwargs['msg']
                await client.send_message(msg.channel, "That command is currently disabled.")


async def bsj_meme(*args, **kwargs):
    """
    builds and sends a BSJ meme
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        cfg = kwargs['cfg']
        client = kwargs['client']
        if(cfg.checkMessage("meme", msg)):
            await client.send_message(msg.channel, BsjFacts.getFact())

async def bsj_name(*args, **kwargs):
    """
    Answers the biggest question in life... what does BSJ actually stand for?
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        cfg = kwargs['cfg']
        client = kwargs['client']
        if(cfg.checkMessage("meme", msg)):
            await client.send_message(msg.channel, BsjFacts.bsjName())

def save():
    markovChaining.dumpAllTables()
    botLog("saving")

def update_dict(newmeme):
    markovChaining.addSingle3(newmeme, markovChaining.nd)

function_dict = { classes.discordCommands.SEND_MEME : send_meme, classes.discordCommands.NEW_MEME : add_meme,
    classes.discordCommands.PURGE_MEMES : purge_memes,
    classes.discordCommands.BSJ_MEME : bsj_meme, classes.discordCommands.BSJ_NAME : bsj_name,
    classes.discordCommands.SEND_OLD_MEME : send_meme }

chat_dict = {"meme" : classes.discordCommands.SEND_MEME, "newmeme" : classes.discordCommands.NEW_MEME,
    "purgememes" : classes.discordCommands.PURGE_MEMES,
    "bsjme" : classes.discordCommands.BSJ_MEME, "bsjname" : classes.discordCommands.BSJ_NAME,
     "oldmeme" : classes.discordCommands.SEND_OLD_MEME }

def init(chat_command_translation, function_translation):
        function_translation.update(function_dict)
        chat_command_translation.update(chat_dict)
        return(chat_command_translation, function_translation)
