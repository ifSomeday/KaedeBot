from gevent import monkey
monkey.patch_ssl()
monkey.patch_socket()

from threading import Thread
import threading
import queue
import classes
import os
import pickle
import header
import time

from steam import SteamClient
from steam import SteamID
from dota2 import Dota2Client
import dota2
import discord
import logging

##ENUM IMPORTS
from steam.enums.emsg import EMsg
from dota2.enums import EDOTAGCMsg as dGCMsg
from dota2.enums import ESOMsg as dEMsg
from dota2.enums import ESOType as dEType
from dota2.enums import DOTA_GameState as dGState
from dota2.enums import EMatchOutcome as dOutcome
from dota2.enums import GCConnectionStatus as dConStat
from dota2.enums import EGCBaseClientMsg as dGCbase


import keys, edit_distance

def steamSlave(sBot, kstQ, dscQ, factoryQ, gameInfo):

    client = SteamClient()
    dota = Dota2Client(client)
    bot_SteamID = None

    ##args 0, 1 are always name and password
    lobby_name = gameInfo.lobbyName
    lobby_pass = gameInfo.lobbyPassword

    ##args 2 is a msg for discord requests, None for web requests
    lobby_msg = gameInfo.discordMessage

    ##args 3 is then the queue to put hosted result in
    job_queue = gameInfo.jobQueue

    hosted = threading.Event()
    joined = threading.Event()
    reconnecting = threading.Lock()

    kyouko_toshino = SteamID(75419738)

    d = {}

    sides_ready = [False, False]

    stop_event = threading.Event()

    lobby_command_translation = {"switchside" : classes.leagueLobbyCommands.SWITCH_SIDE, "fp" : classes.leagueLobbyCommands.FIRST_PICK,
                                "firstpick" :  classes.leagueLobbyCommands.FIRST_PICK, "server": classes.leagueLobbyCommands.SERVER,
                                "start" : classes.leagueLobbyCommands.START, "name" : classes.leagueLobbyCommands.GAME_NAME,
                                "pass" : classes.leagueLobbyCommands.GAME_PASS, "password" : classes.leagueLobbyCommands.GAME_PASS,
                                "cancel" : classes.leagueLobbyCommands.CANCEL_START, "shuffle" : classes.leagueLobbyCommands.SHUFFLE}

    chat_command_translation = {"linvite" : classes.steamCommands.LOBBY_INVITE, "lleave" : classes.steamCommands.LEAVE_LOBBY,
        "leave" : classes.steamCommands.LEAVE_PARTY, "tleave" : classes.steamCommands.LEAVE_TEAM,
        "status" : classes.steamCommands.STATUS}

    debug = True
    if(debug):
        logging.basicConfig(filename=sBot.name + ".log", format='[%(asctime)s] %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
        logging.debug("====================NEW SESSION====================DEADBEEF====================")

    def botLog(text):
        try:
            if(debug):
                logging.debug(sBot.name + ": " +  str(text))
            print(sBot.name + ": " +  str(text), flush=True)
        except:
            print(sBot.name + ": Logging error. Probably some retard name", flush = True)


    ##after logon, launch dota
    @client.on('logged_on')
    def start_dota():
        botLog("Logged into steam")
        if(dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            botLog("Already in logon queue...")
            return
        if(not dota.connection_status is dConStat.HAVE_SESSION):
            botLog("launching dota")
            dota.launch()

    ##At this point dota is ready
    @dota.on('ready')
    def ready0():
        botLog("Connection status:")
        botLog(dota.connection_status)
        botLog("Dota is ready")
        if(not hosted.isSet()):
            hostLobby()

    @dota.on('notready')
    def reload():
        #botLog("out of dota, restarting...")
        botLog("Connection status:")
        botLog(dota.connection_status)
        if(dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            botLog("Already in logon queue...")
            return
        ##NOTE: disabling this is a test to fix zombie threads
        ##if(not dota.connection_status is dConStat.HAVE_SESSION):
        ##    dota.exit()
        ##    dota.launch()

    ##NOTE: this needs work. May be impossible to enter actual game
    ##@dota.on(dGCbase.EMsgGCPingRequest)
    ##def reply():
    ##    dota.send(dGCbase.EMsgGCPingResponseResponse, {})

    @client.on('disconnected')
    def restart():
        if(not stop_event.isSet()):
            botLog("disconnected from steam")
            if(reconnecting.locked()):
                botLog("We are already attempting a reconnection")
                return
            with reconnecting:
                botLog("Attempting to relog...")
                client.reconnect()

    ##determines if the actual teams have changed, and if so, emits the "team_changed" event
    def emit_team_change_event(msg):
        changed = False
        tmpPlayers = []
        for member in dota.lobby.members:
            if(member.team in [0, 1]):
                tmpPlayers.append(member.id)
                if(not member.id in gameInfo.currPlayers):
                    changed = True
        gameInfo.currPlayers = tmpPlayers
        if(changed):
            dota.emit("team_changed", msg)

    def set_curr_players(arr):
        curr_players = arr

    ##dota lobby on lobby change event handler
    @dota.on('lobby_changed')
    def lobby_change_handler(msg):
        if(hosted.isSet()):
            botLog("The hosted lobby has changed")
            gameInfo.lobby = msg
            emit_team_change_event(msg)
        else:
            botLog("We have not hosted a lobby yet, ignoring change")
        return

    @dota.on("team_changed")
    def team_change_handler(msg):
        botLog("team changed")
        if(len(set(gameInfo.players)) > 0):
            for member in dota.lobby.members:
                if(member.team in [0, 1]):
                    if(not member.id in gameInfo.players):
                        botLog("kicking " + str(member.name) + "from team slots")
                        dota.practice_lobby_kick_from_team(SteamID(member.id).as_32)
                        ##dota.practice_lobby_kick(SteamID(member.id).as_32)

    #TODO: this shit is a fucking mess
    #Triggers on launch if previous lobby existed.
    @dota.on('lobby_removed')
    def lobby_removed(msg):

        ## lobby remove is flooding logs
        ##botLog(msg)


        if(not hosted.isSet()):
            return
        factoryQ.put(classes.command(classes.botFactoryCommands.PROCESS_BASIC ,[gameInfo, msg]))

        matchId = msg.match_id
        with open(os.getcwd() + "/matchResults/" + str(matchId) + "_basic.txt", "w") as f:
            f.write(str(msg))

        retries = 0
        match_job = dota.request_match_details(int(matchId))
        matchRes = dota.wait_msg(match_job, timeout=10)
        while(not matchRes.result == 1 and retries < 5):
            dota.sleep(5)
            botLog("Unable to get match result... retrying " + str(retries))
            retries += 1
            match_job = dota.request_match_details(int(matchId))
            matchRes = dota.wait_msg(match_job, timeout=10)

        if(matchRes.result == 1):
            with open(os.getcwd() + "/matchResults/" + str(matchId) + "_detailed.txt", "w") as f:
                f.write(str(matchRes.match))
        else:
            botLog("ERROR: UNABLE TO GET DATA FOR " + str(matchId))
        
        botCleanup()

    @client.on(EMsg.ClientFriendMsgIncoming)
    def steam_message_handler(msg):
        ##TODO: check you have permission to release
        msgT = msg.body.message.decode("utf-8").rstrip('\x00')
        if(not msg.body.steamid_from in header.LD2L_ADMIN_STEAM_IDS):
            return
        if(len(msgT) > 0):
            cMsg = msgT.lower().split()
            if((msgT == "release" or msgT == "!release")and msg.body.steamid_from == kyouko_toshino.as_64):
                botLog("releasing")
                botCleanup()
            elif(msgT == "lobby"):
                hosted.clear()
                hostLobby()
            else:
                if(cMsg[0].startswith("!")):
                  cMsg[0] = cMsg[0][1:]
                command = chat_command_translation[cMsg[0]] if cMsg[0] in chat_command_translation else classes.steamCommands.INVALID_COMMAND
                function_translation[command](cMsg, msg = msg)
        else:
            ##just someone typing
            pass


    @dota.on(dGCMsg.EMsgGCChatMessage)
    def lobby_message_handler(msg):
        if(len(msg.text) > 0):
            cMsg = msg.text.split()
            if(cMsg[0].startswith("!")):
                cMsg[0] = cMsg[0][1:]
            command = lobby_command_translation[cMsg[0].lower()] if cMsg[0].lower() in lobby_command_translation else classes.lobbyCommands.INVALID_COMMAND
            function_translation[command](cMsg, msg = msg)

    @client.friends.on('friend_invite')
    def friend_invite(msg):
        client.friends.add(msg)

    @dota.on('lobby_invite')
    def lobby_invite(msg):
        if(msg.sender_id in header.LD2L_ADMIN_STEAM_IDS):
            if(dota.lobby == None):
                botLog("joining lobby")
                dota.respond_lobby_invite(msg.group_id, accept=True)

    @dota.on('lobby_new')
    def on_lobby_joined(msg):
        if(hosted.isSet()):

            dota.channels.join_channel("Lobby_%s" % msg.lobby_id,channel_type=3)
            ##botLog(msg)
            ##msg is set to none for web requests
            if(lobby_msg != None):
                args = [lobby_name, lobby_pass, lobby_msg, sBot]
                dscQ.put(classes.command(classes.discordCommands.LOBBY_CREATE_MESSAGE, args))
            else:
                job_queue.put((True, gameInfo))
            
            ##TODO: listen for proper team join and remove sleep
            dota.sleep(1)
            dota.join_practice_lobby_team(4)
            for player in gameInfo.players:
                dota.invite_to_lobby(SteamID(player).as_64)

    ##party invite event handler
    @dota.on('party_invite')
    def party_invite(msg):
        if(msg.sender_id in header.LD2L_ADMIN_STEAM_IDS):
            botLog("accepting party invite")
            leave_lobby()
            dota.leave_party()
            if(dota.party == None):
                botLog(msg)
                dota.respond_to_party_invite(msg.group_id, accept=True)

    def hostLobby():
        if(dota.lobby):
            test = dota.leave_practice_lobby()
            while(dota.lobby):
                dota.sleep(0.1) ##SPIN
        d['game_name'] = lobby_name
        d['game_mode'] = dota2.enums.DOTA_GameMode.DOTA_GAMEMODE_CM
        d['server_region'] = dota2.enums.EServerRegion.USEast ##USWest, USEast, Europe
        d['allow_cheats'] = False
        d['visibility'] = dota2.enums.DOTALobbyVisibility.Public ##Public, Friends, Unlisted
        d['dota_tv_delay'] = dota2.enums.LobbyDotaTVDelay.LobbyDotaTV_120
        d['pause_setting'] = dota2.enums.LobbyDotaPauseSetting.Unlimited ##Unlimited, Limited, Disabled
        d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
        d['allow_spectating'] = True
        d['fill_with_bots'] = False
        if(not gameInfo.tournament == None and not gameInfo.tournament == 0):
            d['tournament_id'] = int(gameInfo.tournament)

        ##set additional options from request
        for key, val in gameInfo.config.items():
            d[key] = val

        dota.create_practice_lobby(password=lobby_pass, options=d)
        while(dota.lobby):
            dota.sleep(0.1) ##SPIN
        botLog("Lobby hosted")
        hosted.set()

    def naw(*args, **kwargs):
        pass

    def sendLobbyMessage(message, channel_id):
        dota.send(dGCMsg.EMsgGCChatMessage, {"channel_id": channel_id, "text": message})

    def set_penalty(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 3):
                sendLobbyMessage("Please specify a side and a penalty level (0 - 3)", msg.channel_id)
                return
            side = str(cMsg[1]).lower().strip()
            if(edit_distance.distance(side, 'radiant') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "radiant"
            elif(edit_distance.distance(side, 'dire') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "dire"
            else:
                sendLobbyMessage("Invalid side (Radiant, Dire)", msg.channel_id)
                return
            level = cMsg[2].strip()
            try:
                level = int(level)
            except:
                level = 4
            if(not level in range(0,4)):
                sendLobbyMessage("Invalid penalty level (0 - 3)", msg.channel_id)
                return
            d['penalty_level_' + side] = level
            ##TODO: second translation here
            sendLobbyMessage("Set penalty level of " + side + " to " + str(level), msg.channel_id)


    def swap_teams(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            dota.flip_lobby_teams()
            ##sides_ready[0], sides_ready[1] = sides_ready[1], sides_ready[0]
            sendLobbyMessage("Sides switched", msg.channel_id)
            reset_ready(msg=msg)

    def set_server(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a server region (USW USE EU)", msg.channel_id)
                return
            server = str(cMsg[1]).lower().strip()
            if(server == 'usw'):
                d['server_region'] = dota2.enums.EServerRegion.USWest
            elif(server == 'use'):
                d['server_region'] = dota2.enums.EServerRegion.USEast
            elif(server == 'eu'):
                d['server_region'] = dota2.enums.EServerRegion.Europe
            else:
                sendLobbyMessage("Invalid region (USW USE EU)", msg.channel_id)
                return
            dota.config_practice_lobby(d)
            reset_ready(msg=msg)
            sendLobbyMessage(("Set region to " + server.upper()), msg.channel_id)

    def set_name(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a lobby name", msg.channel_id)
                return
            lobby_name = str(cMsg[1]).strip()
            d['game_name'] = lobby_name
            dota.config_practice_lobby(d)
            sendLobbyMessage("Set lobby name to '" + lobby_name + "'", msg.channel_id)
            reset_ready(msg=msg)

    def set_pass(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a lobby password", msg.channel_id)
                return
            lobby_pass = str(cMsg[1]).strip()
            d['pass_key'] = lobby_pass
            dota.config_practice_lobby(d)
            sendLobbyMessage("Set lobby password to '" + lobby_pass + "'", msg.channel_id)
            reset_ready(msg=msg)

    def lobby_shuffle(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            dota.balanced_shuffle_lobby()
            sendLobbyMessage("Lobby shuffled", msg.channel_id)

    def first_pick(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a side (Radiant, Dire)", msg.channel_id)
                return
            side = str(cMsg[1]).lower().strip()
            if(edit_distance.distance(side, 'radiant') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "Radiant"
            elif(edit_distance.distance(side, 'dire') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "Dire"
            else:
                sendLobbyMessage("Invalid side (Radiant, Dire)", msg.channel_id)
                return
            sendLobbyMessage(("Gave first pick to " + side), msg.channel_id)
            dota.config_practice_lobby(d)
            reset_ready(msg=msg)

    def start_lobby(*args, **kwargs):
        if ('msg' in kwargs):
            msg = kwargs['msg']
            tot_mem = 0
            sender_team = -1
            for member in dota.lobby.members:
                if member.team == 0 or member.team == 1:
                    tot_mem += 1
                    botLog("found member " + str(member.name))
                    if(SteamID(member.id).as_64 == SteamID(msg.account_id).as_64):
                        sender_team = member.team
            if(tot_mem == len(set(gameInfo.players)) or len(set(gameInfo.players)) == 0 and tot_mem == 10):
                if(sender_team == 1 or sender_team == 0):
                    sides_ready[sender_team] = True
                else:
                    sendLobbyMessage("Please only ready up if you are on a team.", msg.channel_id)
                    return
            launch = True
            for side in sides_ready:
                launch = side and launch
            if(launch):
                sendLobbyMessage("Starting lobby. Use !cancel to stop countdown", msg.channel_id)
                for i in range(5, 0, -1):
                    for side in sides_ready:
                        launch = side and launch
                    if(launch):
                        sendLobbyMessage(str(i), msg.channel_id)
                        dota.sleep(1)
                    else:
                        sendLobbyMessage("Countdown canceled", msg.channel_id)
                        return
                dota.launch_practice_lobby()
            else:
                sendLobbyMessage("One side readied up. Waiting for other team..", msg.channel_id)


    def leave_lobby(*args, **kwargs):
        ##check if in lobby
        dota.leave_practice_lobby()
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving lobby")

    def leave_party(*args, **kwargs):
        ##check if in party
        dota.leave_party()
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving party")

    def send_status(*args, **kwargs):
        msg = kwargs['msg']
        id = msg.body.steamid_from
        requester = client.get_user(SteamID(id))
        requester.send_message("Party: " + str("None" if dota.party == None else "Active"))
            ##TODO parse and send party info
        requester.send_message("Lobby: " + str("None" if dota.lobby == None else "Active"))
            ##TODO parse and send lobby info

    def cancel(*args, **kwargs):
        if('msg' in kwargs):
            reset_ready()

    def reset_ready(*args, **kwargs):
        sides_ready[0] = False
        sides_ready[1] = False
        if ('msg' in kwargs):
            msg = kwargs['msg']
            sendLobbyMessage("Reset ready status.", msg.channel_id)


    def botCleanup():
        botLog("shutting down")
        if(not job_queue == None):
            job_queue.put((False, None))
            dota.leave_practice_lobby()
        stop_event.set()

    def timeoutHandler(*args, **kwargs):
        evnt = args[0]
        if(stop_event.isSet()):
            botLog("timeout occoured, but bot is already shutting down!")
            return
        if(dota.lobby == None):
            botLog("lobby not found")
            botCleanup()
        else:
            botLog("im in a lobby!")
            if(len(dota.lobby.members) < 2):
                botLog("but im alone")
                botCleanup()

    def checkQueue():
        if(gameInfo.commandQueue.qsize() > 0 and not dota.lobby == None):
            cmd = gameInfo.commandQueue.get()
            if(cmd.command == classes.slaveBotCommands.INVITE_PLAYER):
                dota.invite_to_lobby(int(cmd.args[0]))
            elif(cmd.command == classes.slaveBotCommands.RELEASE_BOT):
                botCleanup()


    function_translation = {classes.leagueLobbyCommands.SWITCH_SIDE : swap_teams, classes.leagueLobbyCommands.FIRST_PICK : first_pick,
                            classes.leagueLobbyCommands.SERVER : set_server, classes.lobbyCommands.INVALID_COMMAND : naw,
                            classes.leagueLobbyCommands.START : start_lobby, classes.leagueLobbyCommands.GAME_NAME : set_name,
                            classes.leagueLobbyCommands.GAME_PASS : set_pass, classes.leagueLobbyCommands.CANCEL_START : cancel,
                            classes.leagueLobbyCommands.SHUFFLE : lobby_shuffle,
                            classes.steamCommands.LEAVE_LOBBY : leave_lobby, classes.steamCommands.LEAVE_PARTY : leave_party, 
                            classes.steamCommands.STATUS : send_status}

    ##five minutes to get in a lobby
    toH = threading.Timer(600.0, timeoutHandler, [stop_event,])
    gameInfo.timeout = int(time.time()) + 600
    toH.start()

    botLog("logging in")
    client.cli_login(username=sBot.username, password=sBot.password)
    botLog("logged in")

    bot_SteamID = client.steam_id

    while(not stop_event.isSet()):
        checkQueue()
        client.sleep(1)
    toH.cancel()
    botLog("Exited loop")

    client.disconnect()
    botLog("Called disconnect")

    client.logout()
    botLog("Called logout")

    factoryQ.put(classes.command(classes.botFactoryCommands.FREE_SLAVE, [sBot, gameInfo]))
    botLog("Put shutdown command")

    return

if(__name__ == "__main__"):
    sBot = classes.steamBotInfo(keys.SLAVEBOTNAMES[0], keys.SLAVEUSERNAMES[0], keys.SLAVEPASSWORDS[0], keys.SLAVEBOTSTEAMLINKS[0])
    kstQ = queue.Queue()
    dstQ = queue.Queue()
    factoryQ = queue.Queue()
    gameInfo = classes.gameInfo()
    gameInfo.lobbyName = "test"
    gameInfo.lobbyPassword = "test"
    gameInfo.jobQueue = queue.Queue()
    gameInfo.commandQueue = queue.Queue()
    gameInfo.players = [76561198035685466]
    steamSlave(sBot, kstQ, dstQ, factoryQ, gameInfo)
