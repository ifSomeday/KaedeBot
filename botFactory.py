import tornado.ioloop
import tornado.web
from tornado import gen
from tornado import httpclient
import tornado

import keys
import classes
import ksteamSlave

import threading
import queue
import json
import os

import asyncio

import requests

from google.protobuf.json_format import MessageToJson, MessageToDict

def factory(kstQ, dscQ, factoryQ):

    ##this starts in a thread, so we need to create an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ##locks
    count_lock = threading.Lock()

    ##array of bots we init later
    sBotArray = []

    ##dict mapping idents to active lobbies
    active_lobbies = {}

    for i in range(0, len(keys.SLAVEBOTNAMES)):
        sBotArray.append(classes.steamBotInfo(keys.SLAVEBOTNAMES[i], keys.SLAVEUSERNAMES[i], keys.SLAVEPASSWORDS[i], keys.SLAVEBOTSTEAMLINKS[i]))

    def botLog(text):
        try:
            print("BotFactory: " +  str(text), flush = True)
        except:
            print("BotFactory: Logging error. Probably some retard name", flush = True)


    class LobbyInfoRequestHandler(tornado.web.RequestHandler):
        
        @gen.coroutine
        def get(self):

            key = self.get_query_argument("key", default=None)

            ##verify key
            if(not key == keys.LD2L_API_KEY):
                botLog("Info Request error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"result" : False, "reason" : "invalid key"}))
                self.finish()
                return

            resp = {}
            resp["lobbies"] = []

            for ident, info in active_lobbies.items():
                lobby = {}

                ##request info
                lobby["ident"] = ident
                lobby["lobbyName"] = info.lobbyName
                lobby["lobbyPassword"] = info.lobbyPassword
                lobby["tournament"] = info.tournament
                lobby["hook"] = info.hook
                lobby["timeout"] = info.timeout

                if(not info.lobby == None):
                    lobby["lobby"] = MessageToDict(info.lobby)

                resp["lobbies"].append(lobby)

            botLog("Responding to info request")

            self.write(json.dumps(resp))
            self.finish()
            

    class SingleLobbyInfoHandler(tornado.web.RequestHandler):

        @gen.coroutine
        def get(self, slug):

            key = self.get_query_argument("key", default=None)

            ##verify key
            if(not key == keys.LD2L_API_KEY):
                botLog("Single Lobby Info error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"result" : False, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not slug in list(active_lobbies.keys())):
                botLog("Single Lobby Info error, invalid ident")
                self.set_status(400)
                self.write(json.dumps({"result" : False, "reason" : "ident not found"}))
                self.finish()
                return

            resp = {"result" : True}

            lobbyInfo = active_lobbies[slug]

            lobby = {}

            ##request info
            lobby["ident"] = slug
            lobby["lobbyName"] = lobbyInfo.lobbyName
            lobby["lobbyPassword"] = lobbyInfo.lobbyPassword
            lobby["tournament"] = lobbyInfo.tournament
            lobby["hook"] = lobbyInfo.hook
            lobby["timeout"] = lobbyInfo.timeout

            if(not lobbyInfo.lobby == None):
                lobby["lobby"] = MessageToDict(lobbyInfo.lobby)

            resp["lobby"] = lobby

            botLog("Responding to single info request")

            self.write(json.dumps(resp))
            self.finish()


    class LobbyCreateHandler(tornado.web.RequestHandler):

        data = {}

        info = classes.gameInfo()

        res = {}

        @gen.coroutine
        def post(self):
            
            self.data = {}
            self.info = classes.gameInfo()
            self.res = {}

            self.data = tornado.escape.json_decode(self.request.body)

            self.set_header("Content-type", 'application/json')

            botLog("GREGGREG")
            botLog(self.data)

            ##verify key
            if(not "key" in self.data or not self.data["key"] == keys.LD2L_API_KEY):
                botLog("Lobby Create error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"result" : False, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not "ident" in self.data or self.data["ident"] in list(active_lobbies.keys())):
                botLog("Lobby Create error, invalid ident")
                self.set_status(403)
                self.write(json.dumps({"result" : False, "reason" : "duplicate ident"}))
                self.finish()
                return

            ##get lobby ident
            self.info.ident = self.data["ident"]
            
            ##get hook, default value of none
            self.info.hook = self.data["hook"]

            ##get lobby name, default value of none results in autogenerated name
            self.info.lobbyName = self.data["name"]

            ##get lobby password, default value of none results in autogenerated password
            self.info.lobbyPassword = self.data["password"]

            ##get tournament id, default of 0 means no tournament lobby
            self.info.tournament = self.data["tournament"]

            ##get Players to invite
            teams = self.data["teams"]
            if(not teams is None):
                self.info.teams = [x["players"] for x in teams]
                for team in teams:
                    for player in team["players"]:
                        self.info.players.append(player)
                    self.info.captains.append(team["captain"])

            ##queues 
            self.info.jobQueue = queue.Queue()
            self.info.commandQueue = queue.Queue()

            ##aquire a bot
            sBot = acquireBot()

            ##if we get a bot, start it and wait for lobby create
            if(sBot):

                ##bot has been primed, meaning it is already online
                if(sBot.primed):
                    if(sBot.commandQueue is None):
                        botLog("Bot doesnt have a queue, we are stuck")
                        self.write(json.dumps({"result" : False, "reason" : "NO COMMAND QUEUE"}))
                        self.finish()
                        return
                    else:
                        botLog("Hosting lobby with primed bot: " + sBot.username)
                        sBot.commandQueue.put(classes.command(classes.slaveBotCommands.HOST_LOBBY, [self.info]))

                ##bot has not been primed, meaning its not online
                else:

                    ##specify lobby create
                    self.info.startupCommand = classes.slaveBotCommands.HOST_LOBBY
                    botLog("Hosting lobby with unprimed bot: " + sBot.username)
                    slaveBot = threading.Thread(target = ksteamSlave.steamSlave, args=(sBot, kstQ, dscQ, factoryQ, self.info)).start()

                ##prime bot
                attemptPrime(sBot.username)
               
                active_lobbies[self.info.ident] = self.info

                self.res['result'] = True
                self.write(json.dumps(self.res))

            ##no bot, so return false
            else:
                botLog("Lobby Create error, no free bots")
                self.write(json.dumps({"result" : False, "reason" : "NO FREE BOTS"}))
            self.finish()

    class LobbyInviteHandler(tornado.web.RequestHandler):

        @gen.coroutine
        def post(self):

            self.data = tornado.escape.json_decode(self.request.body)

            ##verify key
            if(not "key" in self.data or not self.data["key"] == keys.LD2L_API_KEY):
                botLog("Lobby Invite error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"result" : False, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not "ident" in self.data or not self.data["ident"] in list(active_lobbies.keys())):
                botLog("Lobby Invite error, invalid ident")
                self.set_status(400)
                self.write(json.dumps({"result" : False, "reason" : "ident not found"}))
                self.finish()
                return

            if("player" in self.data):
                commandQueue = active_lobbies[self.data["ident"]].commandQueue
                commandQueue.put(classes.command(classes.slaveBotCommands.INVITE_PLAYER, [self.data["player"]]))

                botLog("Inviting user to lobby")
                self.write(json.dumps({"result" : True}))
                self.finish()
    
    class LobbyRemoveHandler(tornado.web.RequestHandler):

        @gen.coroutine
        def post(self):

            self.data = tornado.escape.json_decode(self.request.body)

            ##verify key
            if(not "key" in self.data or not self.data["key"] == keys.LD2L_API_KEY):
                botLog("Lobby Remove error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"result" : False, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not "ident" in self.data or not self.data["ident"] in list(active_lobbies.keys())):
                botLog("Lobby Remove error, invalid ident")
                self.set_status(400)
                self.write(json.dumps({"result" : False, "reason" : "ident not found"}))
                self.finish()
                return

            commandQueue = active_lobbies[self.data["ident"]].commandQueue
            commandQueue.put(classes.command(classes.slaveBotCommands.RELEASE_BOT, [None]))

            botLog("Removing lobby")

            self.write(json.dumps({"result" : True}))
            self.finish()

                 

    async def processMatch(cmd):

        botLog("Got match process")
        ##gameInfo the gameInfo specified when this lobby was created
        gameInfo = cmd.args[0]

        ##msg the CSODOTALobby result from the lobby_removed message
        msg = cmd.args[1]
        match = MessageToDict(msg)
        ident = gameInfo.ident

        match["ident"] = ident
        match["key"] = keys.LD2L_API_KEY

        ##remove lobby with ident from
        active_lobbies.pop(ident, None)

        if(not gameInfo.hook == ''):
            botLog("Posting to hook")
            asc = httpclient.AsyncHTTPClient()
            r = httpclient.HTTPRequest(gameInfo.hook, method="POST", body=json.dumps(match))
            botLog("posting:")
            botLog(json.dumps(match))
            await asc.fetch(r)

    ##just sets up routing
    def make_app():
        return tornado.web.Application([
        (r"/lobbies/create", LobbyCreateHandler),
        (r"/lobbies", LobbyInfoRequestHandler),
        (r"/lobbies/invite", LobbyInviteHandler),
        (r"/lobbies/remove", LobbyRemoveHandler),
        (r"/lobbies/([^/]+)", SingleLobbyInfoHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path":  os.getcwd() + "/staticHtml", "default_filename": "apiIndex.html"}),
        (r"/shadow_council.html", tornado.web.StaticFileHandler, {"path":  os.getcwd() + "/staticHtml", "default_filename": "shadow_council.html"})
        ])

    ##starts a lobby from a discord command
    def startSteamSlave(*args, **kwargs):
        ##TODO: Check trust level here, or when requested in discord
        cmd = kwargs['cmd']
        info = cmd.args[0]
        sBot = acquireBot()

        ##if we get a bot, set it up
        if(sBot):
            slaveBot = threading.Thread(target = ksteamSlave.steamSlave, args=(sBot, kstQ, dscQ, factoryQ, info)).start()
            return(sBot)
        botLog("Issue getting lobby bot")
        dscQ.put(classes.command(classes.discordCommands.NO_BOTS_AVAILABLE, [info.discordMessage]))
        return(None)

    ##acquires a lobby bot under lock
    def acquireBot():
        with count_lock:
            ##prefer primed bots
            for bot in sBotArray:
                if(not bot.in_use and bot.primed):
                    bot.in_use = True
                    return(bot)
            ##fallback on offline bots
            for bot in sBotArray:
                if(not bot.in_use):
                    bot.in_use = True
                    return(bot)
        return(None)

    ##attempts to prime the next bot in line
    def attemptPrime(botName):
        with count_lock:
            ##try to get the next bot
            for i in range(0, len(sBotArray)):
                if(sBotArray[i].username == botName):
                    ##bot is ready to be primed
                    nextIdx = (i + 1) % len(sBotArray)
                    if(not sBotArray[nextIdx].in_use and not sBotArray[nextIdx].primed):
                        botLog("entering priority prime")

                        info = classes.gameInfo()
                        info.commandQueue = queue.Queue()
                        info.startupCommand = classes.slaveBotCommands.LAUNCH_IDLE
                        sBotArray[nextIdx].commandQueue = info.commandQueue

                        slaveBot = threading.Thread(target = ksteamSlave.steamSlave, args=(sBotArray[nextIdx], kstQ, dscQ, factoryQ, info)).start()
                        sBotArray[nextIdx].primed = True

                        botLog("Primed: " + sBotArray[nextIdx].name)
                        return
            ##try to get any bot
            for sBot in sBotArray:
                if(not sBot.in_use and not sBot.primed):
                    botLog("entering secondary prime")

                    info = classes.gameInfo()
                    info.commandQueue = queue.Queue()
                    sBot.commandQueue = info.commandQueue
                    info.startupCommand = classes.slaveBotCommands.LAUNCH_IDLE
                    slaveBot = threading.Thread(target = ksteamSlave.steamSlave, args=(sBot, kstQ, dscQ, factoryQ, info)).start()
                    sBot.primed = True

                    botLog("Primed: " + sBot.name)
                    return

    ##frees a previously in use bot
    def freeBot(*args, **kwargs):
        cmd = kwargs['cmd']
        sBot = cmd.args[0]
        with count_lock:
            for bot in sBotArray:
                if(bot.name == sBot.name):
                    bot.in_use = False
                    bot.primed = False
                    bot.commandQueue = None
                    break
        gameInfo = cmd.args[1]
        active_lobbies.pop(gameInfo.ident, None)

    ##gets a list of the free bots
    def getFreeBots(*args, **kwargs):
        cmd = kwargs['cmd']
        msg  = cmd.args[0]
        l = []
        with count_lock:
            for bot in sBotArray:
                if(bot.in_use == False):
                    l.append(bot.name)
        dscQ.put(classes.command(classes.discordCommands.BOT_LIST_RET, [msg, l]))

    ##suposedly shuts down discord and main steam bot (does not work)
    def shutdownBots(*args, **kwargs):
        cmd = kwargs['cmd']
        dscQ.put(classes.command(classes.discordCommands.SHUTDOWN_BOT, []))
        kstQ.put(classes.command(classes.steamCommands.SHUTDOWN_BOT, []))

    ##checks the queue for new commands
    async def checkQueue():
        while(factoryQ.qsize() > 0):
            cmd = factoryQ.get()
            if(cmd.command == classes.botFactoryCommands.SPAWN_SLAVE):
                botLog("Got spawn request")
                startSteamSlave(cmd = cmd)
            elif(cmd.command == classes.botFactoryCommands.FREE_SLAVE):
                botLog("Got free request")
                freeBot(cmd = cmd)
            elif(cmd.command == classes.botFactoryCommands.LIST_BOTS_D):
                botLog("Got list request")
                getFreeBots(cmd = cmd)
            elif(cmd.command == classes.botFactoryCommands.SHUTDOWN_BOT):
                botLog("Got shutdown request")
                shutdownBots(cmd = cmd)
                running = False
            elif(cmd.command == classes.botFactoryCommands.PROCESS_BASIC):
                botLog("Got process request")
                await processMatch(cmd)

    ##set up app
    app = make_app()
    app.listen(80, xheaders=True)

    attemptPrime(None)

    ##set up loops
    main_loop = tornado.ioloop.IOLoop.current()
    sched = tornado.ioloop.PeriodicCallback(checkQueue, 1000)

    ##start loops
    sched.start()
    main_loop.start()

##for debug
if __name__ == "__main__":

    factoryQ = queue.Queue()
    kstQ = queue.Queue()
    dscQ = queue.Queue()

    factory(kstQ, dscQ, factoryQ)
