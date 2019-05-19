import zmq

import tornado.ioloop
import tornado.web
from tornado import gen
from tornado import httpclient
import tornado

import keys
import classes
import ksteamSlave
from plugins import zmqutils

import threading
import queue
import json
import os

import asyncio

import requests

from google.protobuf.json_format import MessageToJson, MessageToDict

def factory(kstQ, dscQ):

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
                self.write(json.dumps({"status" : 1, "reason" : "invalid key"}))
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
                self.write(json.dumps({"status" : 1, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not slug in list(active_lobbies.keys())):
                botLog("Single Lobby Info error, invalid ident")
                self.set_status(400)
                self.write(json.dumps({"status" : 1, "reason" : "ident not found"}))
                self.finish()
                return

            resp = {"status" : 0}

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
                self.write(json.dumps({"status" : 1, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not "ident" in self.data or self.data["ident"] in list(active_lobbies.keys())):
                botLog("Lobby Create error, invalid ident")
                self.set_status(403)
                self.write(json.dumps({"status" : 1, "reason" : "duplicate ident"}))
                self.finish()
                return

            ##get lobby ident
            self.info.ident = self.data["ident"]
            
            ##hook optional
            if("hook" in self.data):

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
            
            botLog("Factory: teams, players, captains")
            botLog(self.info.teams)
            botLog(self.info.players)
            botLog(self.info.captains)

            ##aquire a bot
            sBot = acquireBot()

            ##if we get a bot, start it and wait for lobby create
            if(sBot):

                print("got bots")

                botIdent = bytes(sBot.username, 'utf-8')

                botLog("Hosting lobby with bot: " + sBot.username)
                command = classes.command(classes.slaveBotCommands.HOST_LOBBY, [self.info])
                try:
                    zmqutils.sendObjRouter(socket, botIdent, command)
                except Exception as e:
                    botLog(e)
                    self.write(json.dumps({"status" : classes.slaveBotCommands.FAILED, "reason" : "SOCKET ERROR DURING BOT COMMUNICATION"}))
                    return
                                
                active_lobbies[self.info.ident] = self.info

                self.res['status'] = 0
                self.res['reason'] = "Creating Lobby"
                self.write(json.dumps(self.res))

            ##no bot, so return false
            else:
                botLog("Lobby Create error, no free bots")
                self.write(json.dumps({"status" : classes.slaveBotCommands.FAILED, "reason" : "NO FREE BOTS"}))
            self.finish()

    class LobbyInviteHandler(tornado.web.RequestHandler):

        @gen.coroutine
        def post(self):

            self.data = tornado.escape.json_decode(self.request.body)

            ##verify key
            if(not "key" in self.data or not self.data["key"] == keys.LD2L_API_KEY):
                botLog("Lobby Invite error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"status" : 1, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not "ident" in self.data or not self.data["ident"] in list(active_lobbies.keys())):
                botLog("Lobby Invite error, invalid ident")
                self.set_status(400)
                self.write(json.dumps({"status" : 1, "reason" : "ident not found"}))
                self.finish()
                return

            if("player" in self.data):
                commandQueue = active_lobbies[self.data["ident"]].commandQueue
                commandQueue.put(classes.command(classes.slaveBotCommands.INVITE_PLAYER, [self.data["player"]]))

                botLog("Inviting user to lobby")
                self.write(json.dumps({"status" : 0}))
                self.finish()
    
    class LobbyRemoveHandler(tornado.web.RequestHandler):

        @gen.coroutine
        def post(self):

            self.data = tornado.escape.json_decode(self.request.body)

            ##verify key
            if(not "key" in self.data or not self.data["key"] == keys.LD2L_API_KEY):
                botLog("Lobby Remove error, invalid key")
                self.set_status(403)
                self.write(json.dumps({"status" : 1, "reason" : "invalid key"}))
                self.finish()
                return

            ##verify ident
            if(not "ident" in self.data or not self.data["ident"] in list(active_lobbies.keys())):
                botLog("Lobby Remove error, invalid ident")
                self.set_status(400)
                self.write(json.dumps({"status" : 1, "reason" : "ident not found"}))
                self.finish()
                return

            commandQueue = active_lobbies[self.data["ident"]].commandQueue
            commandQueue.put(classes.command(classes.slaveBotCommands.RELEASE_BOT, [None]))

            botLog("Removing lobby")

            self.write(json.dumps({"status" : 0}))
            self.finish()

                 

    class scLookupHandler(tornado.web.RequestHandler):

        @gen.coroutine
        def get(self, slug):

            botLog(slug)

            rspQ = queue.Queue()

            cmd = classes.command(classes.discordCommands.SC_LOOKUP, [slug, rspQ])
            dscQ.put(cmd)

            resp = rspQ.get()

            if(resp is None):
                self.write(json.dumps({"status" : 404}))

            else:
                j = {}

                ##success
                j["status"] = 0
            
                j["content"] = resp.clean_content
                j["timestamp"] = resp.timestamp.timestamp()

                self.write(json.dumps(j))

            self.finish()

            


    async def processMatch(cmd):

        botLog("Got match process")
        ##gameInfo the gameInfo specified when this lobby was created
        gameInfo = cmd.args[0]

        ##msg the CSODOTALobby result from the lobby_removed message
        msg = cmd.args[1]
        match = MessageToDict(msg)
        ident = gameInfo.ident

        ##check if hook empty
        if(gameInfo.hook == ""):
            botLog("Hook is empty")
            return

        body = {}

        body["state"] = classes.lobbyState.COMPLETE.value
        body["reason"] = "Sending match results"
        body["key"] = keys.LD2L_API_KEY
        body["ident"] = ident
        
        body["match"] = match

        ##remove lobby with ident from
        active_lobbies.pop(ident, None)

        asc = httpclient.AsyncHTTPClient()
        r = httpclient.HTTPRequest(gameInfo.hook, method="POST", body=json.dumps(body), headers={'content-type' : 'application/json'})
        await asc.fetch(r)

        botLog("Sent update " + str(classes.lobbyState.COMPLETE))


    ##sends a lobby state update to hook2
    async def updateState(cmd):

        ##unpack data
        updateStruct = cmd.args[0]

        ##check if hook empty
        if(updateStruct.hook == ""):
            botLog("Hook is empty")
            return
        
        ##build body
        body = {}
        body["state"] = updateStruct.state.value
        body["reason"] = updateStruct.reason
        body["key"] = updateStruct.apiKey
        body["ident"] = updateStruct.ident

        ##send resp
        asc = httpclient.AsyncHTTPClient()
        r = httpclient.HTTPRequest(updateStruct.hook, method="POST", body=json.dumps(body), headers={'content-type' : 'application/json'})
        await asc.fetch(r)

        botLog("Sent update " + str(updateStruct.state))

    ##just sets up routing
    def make_app():
        return tornado.web.Application([
        (r"/lobbies/create", LobbyCreateHandler),
        (r"/lobbies", LobbyInfoRequestHandler),
        (r"/lobbies/invite", LobbyInviteHandler),
        (r"/lobbies/remove", LobbyRemoveHandler),
        (r"/lobbies/([^/]+)", SingleLobbyInfoHandler),
        (r"/sc/lookup/(\d+)", scLookupHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path":  os.getcwd() + "/staticHtml", "default_filename": "apiIndex.html"}),
        (r"/shadow_council.html", tornado.web.StaticFileHandler, {"path":  os.getcwd() + "/staticHtml", "default_filename": "shadow_council.html"})
        
        ])

    ##updates lobby info for /lobbies endpoint
    def updateLobby(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            gameInfo = cmd.args[0]

            active_lobbies[gameInfo.ident] = gameInfo

    ##starts a lobby from a discord command
    def startSteamSlave(*args, **kwargs):
        ##TODO: Check trust level here, or when requested in discord
        cmd = kwargs['cmd']
        info = cmd.args[0]
        sBot = acquireBot()

        ##if we get a bot, set it up
        if(sBot):
            slaveBot = threading.Thread(target = ksteamSlave.steamSlave, args=(sBot, kstQ, dscQ, info)).start()
            return(sBot)
        botLog("Issue getting lobby bot")
        dscQ.put(classes.command(classes.discordCommands.NO_BOTS_AVAILABLE, [info.discordMessage]))
        return(None)

    ##acquires a lobby bot under lock
    def acquireBot():
        with count_lock:
            ##fallback on offline bots
            for bot in sBotArray:
                if(not bot.in_use):
                    bot.in_use = True
                    return(bot)
        return(None)


    def primeBots():
        with count_lock:
            for sBot in sBotArray:
                info = classes.gameInfo()
                info.commandQueue = queue.Queue()
                info.jobQueue = queue.Queue()
                info.startupCommand = classes.slaveBotCommands.LAUNCH_IDLE

                sBot.commandQueue = info.commandQueue

                bot = ksteamSlave.SteamSlave(sBot, kstQ, dscQ, info)
                bot.start()
                return


    ##frees a previously in use bot
    def freeBot(*args, **kwargs):
        cmd = kwargs['cmd']
        sBot = cmd.args[0]
        with count_lock:
            for bot in sBotArray:
                if(bot.name == sBot.name):
                    bot.in_use = False
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


    async def checkQueueZMQ():
        try:
            botid, cmd = zmqutils.recvObjRouter(socket, zmq.DONTWAIT)
            await processCommand(cmd)
        except zmq.error.Again as e:
            ##botLog("Nothing to recv")
            pass
        except Exception as e:
            botLog("Unexpected recv exception: %s" % str(e))


    async def processCommand(cmd):
        if(cmd.command == classes.botFactoryCommands.SPAWN_SLAVE):
            botLog("Got spawn request")
            startSteamSlave(cmd = cmd)
        elif(cmd.command == classes.botFactoryCommands.FREE_SLAVE):
            botLog("Got free request")
            freeBot(cmd = cmd)
        elif(cmd.command == classes.botFactoryCommands.UPDATE_LOBBY):
            botLog("Update Lobby Request")
            updateLobby(cmd = cmd)
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
        elif(cmd.command == classes.botFactoryCommands.UPDATE_STATE):
            botLog("Got update state request")
            await updateState(cmd)



    context = zmq.Context()
    socket = context.socket(zmq.ROUTER)
    socket.bind("tcp://*:9001")

    ##set up app
    app = make_app()
    app.listen(8080, xheaders=True)

    ##set up loops
    main_loop = tornado.ioloop.IOLoop.current()
    sched = tornado.ioloop.PeriodicCallback(checkQueueZMQ, 500)

    primeBots()

    ##start loops
    sched.start()
    main_loop.start()

##for debug
if __name__ == "__main__":

    kstQ = queue.Queue()
    dscQ = queue.Queue()

    factory(kstQ, dscQ)
