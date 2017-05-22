##handles thread creation and management
import ksteam as sb
import kDiscord as db
import asyncio
from threading import Thread
import queue
import time

testingEnabled= False

##TODO: create master queue so bots can talk to me(I.E. coordinated graceful shutdown)
kstQ = queue.Queue()
dscQ = queue.Queue()

kst = Thread(target = sb.dotaThread, args=(kstQ, dscQ,))
kst.start()

kdc = Thread(target = db.discBot, args=(kstQ, dscQ,))
kdc.start()

kst.join()
kdc.join()

#loop = asyncio.get_event_loop()
#loop.run_until_complete(db.discBot(kstQ, dscQ))


##Keep threads alive
