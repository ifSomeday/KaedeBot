from gevent import monkey
monkey.patch_ssl()
monkey.patch_socket()

##handles thread creation and management
import ksteam as sb
import kDiscord as db
import draftThread as dt
import asyncio
from threading import Thread
from threading import Event
import queue
import time

testingEnabled= False

##TODO: create master queue so bots can talk to me(I.E. coordinated graceful shutdown)
kstQ = queue.Queue()
dscQ = queue.Queue()
draftEvent = Event()

kst = Thread(target = sb.dotaThread, args=(kstQ, dscQ,))
kst.start()

kdc = Thread(target = db.discBot, args=(kstQ, dscQ, draftEvent,))
kdc.start()

drft = Thread(target = dt.main, args=(kstQ, dscQ, draftEvent,))
drft.start()

kst.join()
kdc.join()
drft.join()
#loop = asyncio.get_event_loop()
#loop.run_until_complete(db.discBot(kstQ, dscQ))


##Keep threads alive
