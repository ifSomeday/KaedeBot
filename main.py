from gevent import monkey
monkey.patch_ssl()
monkey.patch_socket()

import ksteam as sb
import kDiscord as db
import ksteamSlave
##import draftThread as dt
import threading
import random, string
import keys, classes
from threading import Event
import queue
import time


##locks
count_lock = threading.Lock()

testingEnabled = False
##replace with Event
running = True
sBotArray = []

for i in range(0, len(keys.SLAVEBOTNAMES)):
    sBotArray.append(classes.steamBotInfo(keys.SLAVEBOTNAMES[i], keys.SLAVEUSERNAMES[i], keys.SLAVEPASSWORDS[i], keys.SLAVEBOTSTEAMLINKS[i]))

kstQ = queue.Queue()
dscQ = queue.Queue()
factoryQ = queue.Queue()
draftEvent = Event()

kst = None
kdc = None
drft = None

def startMainSteam(kst):
    kst = threading.Thread(target = sb.dotaThread, args=(kstQ, dscQ, factoryQ,))
    kst.start()
    return(kst)

def startDiscord(kdc):
    kdc = threading.Thread(target = db.discBot, args=(kstQ, dscQ, factoryQ, draftEvent,))
    kdc.start()
    return(kdc)

def startDraft(drft):
    drft = threading.Thread(target = dt.main, args=(kstQ, dscQ, draftEvent,))
    drft.start()
    return(drft)

def startSteamSlave(*args, **kwargs):
    ##Check trust level here, or when requested in discord
    cmd = kwargs['cmd']
    cargs = cmd.args
    sBot = None
    count_lock.acquire()
    for bot in sBotArray:
        if(not bot.in_use):
            bot.in_use = True
            sBot = bot
            break
    count_lock.release()
    if(sBot):
        lobby_name = cargs[0]
        pswrd = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
        slaveBot = threading.Thread(target = ksteamSlave.steamSlave, args=(sBot, kstQ, dscQ, factoryQ, lobby_name, pswrd)).start()
        return(sBot)
    print("Issue getting lobby bot")
    return(None)

def freeBot(*args, **kwargs):
    cmd = kwargs['cmd']
    sBot = cmd.args[0]
    count_lock.acquire()
    for bot in sBotArray:
        if(bot.name == sBot.name):
            bot.in_use = False
            break
    count_lock.release()

def getFreeBots(*args, **kwargs):
    cmd = kwargs['cmd']
    msg  = cmd.args[0]
    l = []
    count_lock.acquire()
    for bot in sBotArray:
        if(bot.in_use == False):
            l.append(bot.name)
    count_lock.release()
    dscQ.put(classes.command(classes.discordCommands.BOT_LIST_RET, [msg, l]))

while(running):
    if(kst == None or not kst.isAlive()):
        pass
        #print("thread kst is stopped... starting...")
        ##kst = startMainSteam(kst)
    if(kdc == None or not kdc.isAlive()):
        print("thread kdc is stopped... starting...")
        kdc = startDiscord(kdc)
    if(drft == None or not drft.isAlive()):
        pass
        #print("thread drft is stopped... starting...")
        #drft = startDraft(drft)
    time.sleep(1)
    while(factoryQ.qsize() > 0):
        cmd = factoryQ.get()
        if(cmd.command == classes.botFactoryCommands.SPAWN_SLAVE):
            startSteamSlave(cmd = cmd)
        elif(cmd.command == classes.botFactoryCommands.FREE_SLAVE):
            freeBot(cmd = cmd)
            running = False
        elif(cmd.command == classes.botFactoryCommands.LIST_BOTS_D):
            getFreeBots(cmd = cmd)

##kst.join()
kdc.join()
##drft.join()
