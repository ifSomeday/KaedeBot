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

    ##args 2 is a msg for discord requests, None for web requests
    lobby_msg = gameInfo.discordMessage

    hosted = threading.Event()
    joined = threading.Event()
    launching = threading.Event()
    reconnecting = threading.Lock()

    kyouko_toshino = SteamID(75419738)

    d = {}
    kickList = {}

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
    def steam_logon_handler():
        botLog("Logged into steam")

        ##if the startupcommand is launch Dota, rejoin Lobby, or host Lobby we want to continue with the startup procedure
        if(gameInfo.startupCommand in [classes.slaveBotCommands.LAUNCH_DOTA, classes.slaveBotCommands.HOST_LOBBY, classes.slaveBotCommands.REJOIN_LOBBY]):

            ##we do not need to do anything else special here, launch dota handles that
            launch_dota()

    ##At this point dota is ready
    @dota.on('ready')
    def dota_ready_handler():

        ##log connection status here, debug purposes
        botLog("Connection status:")
        botLog(dota.connection_status)
        botLog("Dota is ready")

        ##host lobby specific code
        if(gameInfo.startupCommand == classes.slaveBotCommands.HOST_LOBBY):
            if(not hosted.isSet()):
                hostLobby()

        ##rejoin lobby specific code
        elif(gameInfo.startupCommand == classes.slaveBotCommands.REJOIN_LOBBY):

            ##set hosted 
            hosted.set()

            ##check if we have a lobby to rejoin
            if(dota.lobby == None):
                botLog("Attempted to rejoin a lobby, but it did not exist! The lobby probably ended...")
                botCleanup()
            else:
                botLog("Lobby rejoined")




    @dota.on('notready')
    def reload():
        #botLog("out of dota, restarting...")
        botLog("Connection status:")
        botLog(dota.connection_status)
        if(dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            botLog("Already in logon queue...")
            return

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
        tmpPlayers = [[], []]
        for member in dota.lobby.members:
            if(not member.id in gameInfo.members):
                lobby_broadcast_slot(member)
            gameInfo.members.append(member.id)
            if(member.team in [0, 1]):
                tmpPlayers[member.team].append(member.id)
                if(not member.id in gameInfo.currPlayers[member.team]):
                    changed = True
        gameInfo.currPlayers = tmpPlayers
        if(changed):
            dota.emit("team_changed", msg)

    ##broadcast slot to join to new member
    def lobby_broadcast_slot(member):
        for i in range(0, len(gameInfo.teams)):
            if(str(member.id) in gameInfo.teams[i]):
                loop = 0
                while(True and loop < 5):
                    res = dota.channels.wait_event("members_update", 2.0)
                    if(not res == None):
                        channel, joined, left = res
                        if(member.id in joined and not launching.isSet()):
                            sendLobbyMessage(member.name + ", please join the " + ("radiant" if i == 0 else "dire") + " team.")
                            return
                    loop += 1
                

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

                    ##if player is not supposed to be in a team
                    if(not str(member.id) in gameInfo.players):

                        ##add to kicklist if not already
                        if(not str(member.id) in kickList):
                            kickList[str(member.id)] = 0

                        ##increment kick counter
                        kickList[str(member.id)] += 1
                        botLog(member.name + " kick #" + str(kickList[str(member.id)]))

                        ###if kicked 3 times already, kick from lobby
                        if(kickList[str(member.id)] > 3):
                            botLog("kicking " + str(member.name) + "from lobby")
                            dota.practice_lobby_kick(SteamID(member.id).as_32)

                        ##kick from slot
                        else:
                            botLog("kicking " + str(member.name) + "from team slots")
                            dota.practice_lobby_kick_from_team(SteamID(member.id).as_32)
                
                    ##if player IS supposed to be in a team
                    else:
                        for i in range(0, len(gameInfo.teams)):
                            ##if player is in the wrong team, kick from team and send mesasge
                            if(str(member.id) in gameInfo.teams[i] and not member.team == i):
                                dota.practice_lobby_kick_from_team(SteamID(member.id).as_32)
                                sendLobbyMessage(member.name + ", please join the " + ("radiant" if i == 0 else "dire") + " team.")
        
        ##update lobby
        gameInfo.lobby = dota.lobby
        factoryQ.put(classes.command(classes.botFactoryCommands.UPDATE_LOBBY, [gameInfo]))

                        

    #TODO: this shit is a fucking mess
    #Triggers on launch if previous lobby existed.
    @dota.on('lobby_removed')
    def lobby_removed(msg):

        if(not hosted.isSet()):
            return

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
            factoryQ.put(classes.command(classes.botFactoryCommands.PROCESS_BASIC, [gameInfo, matchRes]))
        else:
            botLog("ERROR: UNABLE TO GET DATA FOR " + str(matchId))
            factoryQ.put(classes.command(classes.botFactoryCommands.PROCESS_BASIC ,[gameInfo, msg]))
        
        botCleanup()

    @client.on(EMsg.ClientFriendMsgIncoming)
    def steam_message_handler(msg):
        ##TODO: check you have permission to release
        msgT = msg.body.message.decode("utf-8").rstrip('\x00')
        if(not msg.body.steamid_from in header.LD2L_ADMIN_STEAM_IDS):
            return
        if(len(msgT) > 0):
            cMsg = msgT.lower().split()
            if(msgT == "release" or msgT == "!release"):
                botLog("releasing")
                botCleanup()
            elif(msgT == "start" or msgT == "!start"):
                botLog("starting")
                dota.launch_practice_lobby()

            ##THESE SHOULD BE USED FOR DEBUG
            elif(msgT == "launchdota" or msgT == "!launchdota"):
                botLog("got launchdota")
                cmd = classes.command(classes.slaveBotCommands.LAUNCH_DOTA, [])
                gameInfo.commandQueue.put(cmd)
            elif(msgT == "rejoinlobby" or msgT == "!rejoinlobby"):
                botLog("got rejoinlobby")
                cmd = classes.command(classes.slaveBotCommands.REJOIN_LOBBY, [])
                gameInfo.commandQueue.put(cmd)
            elif(msgT == "hostlobby" or msgT == "!hostlobby"):
                botLog("got hostlobby")
                cmd = classes.command(classes.slaveBotCommands.HOST_LOBBY, [])
                gameInfo.commandQueue.put(cmd)
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

            ##send created state
            factoryQ.put(classes.command(classes.botFactoryCommands.UPDATE_STATE, [classes.stateData(gameInfo.hook, classes.lobbyState.CREATED, "Lobby created", keys.LD2L_API_KEY, gameInfo.ident)]))
   
            ##msg is set to none for web requests
            if(lobby_msg != None):
                args = [gameInfo.lobbyName, gameInfo.lobbyPassword, lobby_msg, sBot]
                dscQ.put(classes.command(classes.discordCommands.LOBBY_CREATE_MESSAGE, args))
            else:
                gameInfo.jobQueue.put((True, gameInfo))
            
            ##join chat channel
            dota.channels.join_channel("Lobby_%s" % msg.lobby_id, channel_type=3)

            ##switch to unassigned team so we don't prevent the lobby from loading
            dota.join_practice_lobby_team(4)

            ##invite all players
            botLog("steamslave: teams, players, captains")
            botLog(gameInfo.teams)
            botLog(gameInfo.players)
            botLog(gameInfo.captains)
            for player in gameInfo.players:
                dota.invite_to_lobby(SteamID(player).as_64)

                ##attempt to fix the missing invites
                client.sleep(0.3)

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
            dota.wait_event("lobby_removed", 5.0)
        d['game_name'] = gameInfo.lobbyName
        d['game_mode'] = dota2.enums.DOTA_GameMode.DOTA_GAMEMODE_CM
        d['server_region'] = dota2.enums.EServerRegion.USEast ##USWest, USEast, Europe
        d['allow_cheats'] = False
        d['visibility'] = dota2.enums.DOTALobbyVisibility.Public ##Public, Friends, Unlisted
        d['dota_tv_delay'] = dota2.enums.LobbyDotaTVDelay.LobbyDotaTV_120
        d['pause_setting'] = dota2.enums.LobbyDotaPauseSetting.Unlimited ##Unlimited, Limited, Disabled
        d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
        d['allow_spectating'] = True
        d['fill_with_bots'] = False
        d['selection_priority_rules'] = dota2.enums.DOTASelectionPriorityRules.Automatic
        if(not gameInfo.tournament == None and not gameInfo.tournament == 0):
            d["leagueid"] = int(gameInfo.tournament)

        ##set additional options from request
        for key, val in gameInfo.config.items():
            d[key] = val

        dota.create_practice_lobby(password=gameInfo.lobbyPassword, options=d)

        ##five minutes to get in a lobby
        gameInfo.timeout = int(time.time()) + 600

        hosted.set()

    def naw(*args, **kwargs):
        pass

    ##wrapper for lobby chat
    def sendLobbyMessage(message):
        dota.channels.lobby.send(message)

    def set_penalty(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 3):
                sendLobbyMessage("Please specify a side and a penalty level (0 - 3)")
                return
            side = str(cMsg[1]).lower().strip()
            if(edit_distance.distance(side, 'radiant') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "radiant"
            elif(edit_distance.distance(side, 'dire') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "dire"
            else:
                sendLobbyMessage("Invalid side (Radiant, Dire)")
                return
            level = cMsg[2].strip()
            try:
                level = int(level)
            except:
                level = 4
            if(not level in range(0,4)):
                sendLobbyMessage("Invalid penalty level (0 - 3)")
                return
            d['penalty_level_' + side] = level
            ##TODO: second translation here
            sendLobbyMessage("Set penalty level of " + side + " to " + str(level))


    def swap_teams(*args, **kwargs):
        if('msg' in kwargs):
            return
            msg = kwargs['msg']
            gameInfo.teams[0], gameInfo.teams[1] = gameInfo.teams[1], gameInfo.teams[0]
            dota.flip_lobby_teams()
            ##sides_ready[0], sides_ready[1] = sides_ready[1], sides_ready[0]
            sendLobbyMessage("Sides switched")
            reset_ready(msg=msg)

    def set_server(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(not str(SteamID(msg.account_id).as_64) in gameInfo.captains):
                sendLobbyMessage("You must be a captain to use this command.")
                return
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a server region (USW USE EU)")
                return
            server = str(cMsg[1]).lower().strip()
            if(server == 'usw'):
                d['server_region'] = dota2.enums.EServerRegion.USWest
            elif(server == 'use'):
                d['server_region'] = dota2.enums.EServerRegion.USEast
            elif(server == 'eu'):
                d['server_region'] = dota2.enums.EServerRegion.Europe
            else:
                sendLobbyMessage("Invalid region (USW USE EU)")
                return
            dota.config_practice_lobby(d)
            reset_ready(msg=msg)
            sendLobbyMessage(("Set region to " + server.upper()))

    def set_name(*args, **kwargs):
        if('msg' in kwargs):
            return
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a lobby name")
                return
            gameInfo.lobbyName = str(cMsg[1]).strip()
            d['game_name'] = gameInfo.lobbyName
            dota.config_practice_lobby(d)
            sendLobbyMessage("Set lobby name to '" + gameInfo.lobbyName + "'")
            reset_ready(msg=msg)

    def set_pass(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            return
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a lobby password")
                return
            gameInfo.lobbyPassword = str(cMsg[1]).strip()
            d['pass_key'] = gameInfo.lobbyPassword
            dota.config_practice_lobby(d)
            sendLobbyMessage("Set lobby password to '" + gameInfo.lobbyPassword + "'")
            reset_ready(msg=msg)

    def lobby_shuffle(*args, **kwargs):
        if('msg' in kwargs):
            return
            msg = kwargs['msg']
            cMsg = args[0]
            dota.balanced_shuffle_lobby()
            sendLobbyMessage("Lobby shuffled")

    def first_pick(*args, **kwargs):
        if('msg' in kwargs):
            return
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a side (Radiant, Dire)")
                return
            side = str(cMsg[1]).lower().strip()
            if(edit_distance.distance(side, 'radiant') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "Radiant"
            elif(edit_distance.distance(side, 'dire') < 3):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "Dire"
            else:
                sendLobbyMessage("Invalid side (Radiant, Dire)")
                return
            sendLobbyMessage("Gave first pick to " + side)
            dota.config_practice_lobby(d)
            reset_ready(msg=msg)

    def start_lobby(*args, **kwargs):
        if ('msg' in kwargs):
            if(not len(dota.lobby.team_details) == 2 or any(x.team_id == 0 for x in dota.lobby.team_details)):
                sendLobbyMessage("Both teams must have a name set before starting.")
                return
            msg = kwargs['msg']
            tot_mem = 0
            sender_team = -1
            for member in dota.lobby.members:
                if member.team == 0 or member.team == 1:
                    tot_mem += 1
                    botLog("found member " + str(member.name))
                    if(SteamID(member.id).as_64 == SteamID(msg.account_id).as_64):
                        sender_team = member.team
            if(tot_mem >= 10 or tot_mem == len(set(gameInfo.players)) or SteamID(msg.account_id).as_64 in header.LD2L_ADMIN_STEAM_IDS):
                if(sender_team == 1 or sender_team == 0):
                    sides_ready[sender_team] = True
                else:
                    sendLobbyMessage("Please only ready up if you are on a team.")
                    return
            else:
                sendLobbyMessage("Please wait for the teams to be filled")
                return
            launch = True
            for side in sides_ready:
                launch = side and launch
            if(launch and not launching.is_set()):
                launching.set()
                sendLobbyMessage("Starting lobby. Use !cancel to stop countdown")
                for i in range(5, 0, -1):
                    for side in sides_ready:
                        launch = side and launch
                    if(launch):
                        sendLobbyMessage(str(i))
                        dota.sleep(1)
                    else:
                        sendLobbyMessage("Countdown canceled")
                        launching.clear()
                        return
                if(not len(dota.lobby.team_details) == 2 or any(x is None for x in dota.lobby.team_details)):
                    reset_ready()
                    sendLobbyMessage("Cannot start lobby without both teams being set!")
                else:
                    dota.launch_practice_lobby()
                launching.clear()
            elif(not launching.is_set()):
                sendLobbyMessage("One side readied up. Waiting for other team..")


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
            msg = kwargs['msg']
            if(not str(SteamID(msg.account_id).as_64) in gameInfo.captains):
                sendLobbyMessage("You must be a captain to use this command.")
                return
            reset_ready()

    def reset_ready(*args, **kwargs):
        sides_ready[0] = False
        sides_ready[1] = False
        if ('msg' in kwargs):
            msg = kwargs['msg']
            sendLobbyMessage("Reset ready status.")


    def botCleanup(shutdown = False):
        botLog("shutting down")
        if(not gameInfo.jobQueue == None):
            gameInfo.jobQueue.put((False, None))
            dota.leave_practice_lobby()
        if(shutdown):
            stop_event.set()
        else:    
            dota.exit()
            hosted.clear()
            freeBot()

    def timeoutHandler(*args, **kwargs):
        if(hosted.isSet() and time.time() > gameInfo.timeout):
            botLog("timeout triggered")
            if(stop_event.isSet()):
                botLog("timeout occoured, but bot is already shutting down!")
                return
            if(dota.lobby == None):
                botLog("lobby not found")
                botCleanup()
            else:
                if(len(dota.lobby.members) < 2):
                    botLog("cleaning up empty lobby")
                    botCleanup()

    def checkQueue():
        if(gameInfo.commandQueue.qsize() > 0 and client.logged_on):
            botLog("got command")
            cmd = gameInfo.commandQueue.get()
            if(cmd.command == classes.slaveBotCommands.INVITE_PLAYER):
                botLog("got command to invite player")
                dota.invite_to_lobby(SteamID(cmd.args[0]).as_64)
            elif(cmd.command == classes.slaveBotCommands.RELEASE_BOT):
                botLog("got command to release bot")
                gameInfo.startupCommand = classes.slaveBotCommands.RELEASE_BOT
                botCleanup()
            elif(cmd.command == classes.slaveBotCommands.LAUNCH_DOTA):
                botLog("got command to launch dota")
                gameInfo.startupCommand = classes.slaveBotCommands.LAUNCH_DOTA
                launch_dota()
            elif(cmd.command == classes.slaveBotCommands.REJOIN_LOBBY):
                botLog("got command to rejoin lobby")
                gameInfo.startupCommand = classes.slaveBotCommands.REJOIN_LOBBY
                launch_dota()
            elif(cmd.command == classes.slaveBotCommands.HOST_LOBBY):
                botLog("got command to host lobby")
                if(len(cmd.args) > 0):
                    gameInfo.update(cmd.args[0])
                gameInfo.startupCommand = classes.slaveBotCommands.HOST_LOBBY
                launch_dota()

    ##Launch Dota
    def launch_dota():
        if(dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            botLog("Already in logon queue...")
            return
        elif(not dota.connection_status is dConStat.HAVE_SESSION):
            botLog("launching dota")
            dota.launch()
        else:
            botLog("Dota is already online. called ready handler")
            dota_ready_handler()

    def freeBot():
        ##update (remove) lobby
        factoryQ.put(classes.command(classes.botFactoryCommands.UPDATE_STATE, [classes.stateData(gameInfo.hook, classes.lobbyState.REMOVED, "Bot shutting down", keys.LD2L_API_KEY, gameInfo.ident)]))
        botLog("Called state update (shutdown)")

        ##free bot for future use
        factoryQ.put(classes.command(classes.botFactoryCommands.FREE_SLAVE, [sBot, gameInfo]))
        botLog("Put shutdown command")

    ##Rejoin Lobby
    def rejoin_lobby():
        if(not dota.connection_status is dConStat.HAVE_SESSION):
            launch_dota()

    function_translation = {classes.leagueLobbyCommands.SWITCH_SIDE : swap_teams, classes.leagueLobbyCommands.FIRST_PICK : first_pick,
                            classes.leagueLobbyCommands.SERVER : set_server, classes.lobbyCommands.INVALID_COMMAND : naw,
                            classes.leagueLobbyCommands.START : start_lobby, classes.leagueLobbyCommands.GAME_NAME : set_name,
                            classes.leagueLobbyCommands.GAME_PASS : set_pass, classes.leagueLobbyCommands.CANCEL_START : cancel,
                            classes.leagueLobbyCommands.SHUFFLE : lobby_shuffle,
                            classes.steamCommands.LEAVE_LOBBY : leave_lobby, classes.steamCommands.LEAVE_PARTY : leave_party, 
                            classes.steamCommands.STATUS : send_status}

    botLog("logging in")
    client.cli_login(username=sBot.username, password=sBot.password)
    botLog("logged in")

    bot_SteamID = client.steam_id

    while(not stop_event.isSet()):
        checkQueue()
        timeoutHandler()
        client.sleep(1)

    freeBot()

    botLog("Exited loop")

    client.disconnect()
    botLog("Called disconnect")

    client.logout()
    botLog("Called logout")

    return

if(__name__ == "__main__"):
    botnum = 0
    sBot = classes.steamBotInfo(keys.SLAVEBOTNAMES[botnum], keys.SLAVEUSERNAMES[botnum], keys.SLAVEPASSWORDS[botnum], keys.SLAVEBOTSTEAMLINKS[botnum])
    kstQ = queue.Queue()
    dstQ = queue.Queue()
    factoryQ = queue.Queue()
    gameInfo = classes.gameInfo()
    gameInfo.lobbyName = "test"
    gameInfo.lobbyPassword = "test00001111"
    gameInfo.jobQueue = queue.Queue()
    gameInfo.commandQueue = queue.Queue()
    gameInfo.players = []
    gameInfo.teams = [[], []]
    gameInfo.startupCommand = classes.slaveBotCommands.HOST_LOBBY
    steamSlave(sBot, kstQ, dstQ, factoryQ, gameInfo)
