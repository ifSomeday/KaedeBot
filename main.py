from gevent import monkey
monkey.patch_ssl()
monkey.patch_socket()

import ksteam as sb
import kDiscord as db
import botFactory
##import draftThread as dt
import threading
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
fct = None

def startMainSteam(kst):
    kst = threading.Thread(target = sb.dotaThread, args=(kstQ, dscQ, factoryQ,))
    kst.start()
    return(kst)

def startDiscord(kdc):
    kdc = threading.Thread(target = db.discBot, args=(kstQ, dscQ, factoryQ, draftEvent,))
    kdc.start()
    return(kdc)

def startDraft(drft):
    ##drft = threading.Thread(target = dt.main, args=(kstQ, dscQ, draftEvent,))
    ##drft.start()
    return(drft)

def startFactory(fct):
##    fct = threading.Thread(target = botFactory.factory, args=(kstQ, dscQ, ))
##    fct.start()
    return(fct)

while(running):
    if(False):##kst == None or not kst.isAlive()):
        pass
        print("thread kst is stopped... starting...")
        kst = startMainSteam(kst)
    if(kdc == None or not kdc.isAlive()):
        print("thread kdc is stopped... starting...")
        kdc = startDiscord(kdc)
    ##if(fct == None or not fct.isAlive()):
    ##    print("thread fct is stopped... starting...")
    ##    fct = startFactory(fct)
    ##if(drft == None or not drft.isAlive()):
    ##    pass
    ##    print("thread drft is stopped... starting...")
    ##    drft = startDraft(drft)
    time.sleep(1)
    

time.sleep(30)
#kst.join()
#kdc.join()
##drft.join()
