from gevent import monkey
monkey.patch_all()

import zmq

from threading import Thread
import multiprocessing
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
from plugins import zmqutils

class SteamSlave(Thread):

    def __init__(self, sBot, kstQ, dscQ, gameInfo, context=None):

        #GUIDO
        threading.Thread.__init__(self)

        ##bot info
        self.sBot = sBot

        ##lobby info
        self.gameInfo = gameInfo

        ##queues for communication
        self.kstQ = kstQ
        self.dscQ = dscQ

        ##zmq context
        self.context = context or zmq.Context()

        ##create socket
        self.sock = self.context.socket(zmq.DEALER)
        self.sock.setsockopt(zmq.IDENTITY, bytes(self.sBot.username, 'utf-8'))
        self.sock.connect("tcp://127.0.0.1:9001")

        ##client info
        self.client = SteamClient()
        self.dota = Dota2Client(self.client)
        self.bot_SteamID = None

        ##args 2 is a msg for discord requests, None for web requests
        self.lobby_msg = gameInfo.discordMessage

        ##Events and locks
        self.hosted = threading.Event()
        self.joined = threading.Event()
        self.launching = threading.Event()
        self.reconnecting = threading.Lock()
        self.stop_event = threading.Event()

        ##for administration purposes
        self.kyouko_toshino = SteamID(75419738)

        ##information about the lobby
        self.d = {}
        self.kickList = {}
        self.sides_ready = [False, False]

        ##lobby chat command processor
        self.lobby_command_translation = {"switchside" : classes.leagueLobbyCommands.SWITCH_SIDE, "fp" : classes.leagueLobbyCommands.FIRST_PICK,
                                    "firstpick" :  classes.leagueLobbyCommands.FIRST_PICK, "server": classes.leagueLobbyCommands.SERVER,
                                    "start" : classes.leagueLobbyCommands.START, "name" : classes.leagueLobbyCommands.GAME_NAME,
                                    "pass" : classes.leagueLobbyCommands.GAME_PASS, "password" : classes.leagueLobbyCommands.GAME_PASS,
                                    "cancel" : classes.leagueLobbyCommands.CANCEL_START, "shuffle" : classes.leagueLobbyCommands.SHUFFLE}

        ##steam chat command processor
        self.chat_command_translation = {"linvite" : classes.steamCommands.LOBBY_INVITE, "lleave" : classes.steamCommands.LEAVE_LOBBY,
            "leave" : classes.steamCommands.LEAVE_PARTY, "tleave" : classes.steamCommands.LEAVE_TEAM,
            "status" : classes.steamCommands.STATUS}

        ##command to function translation
        self.function_translation = {   classes.leagueLobbyCommands.SWITCH_SIDE : self.swap_teams, classes.leagueLobbyCommands.FIRST_PICK : self.first_pick,
                                classes.leagueLobbyCommands.SERVER : self.set_server, classes.lobbyCommands.INVALID_COMMAND : self.naw,
                                classes.leagueLobbyCommands.START : self.start_lobby, classes.leagueLobbyCommands.GAME_NAME : self.set_name,
                                classes.leagueLobbyCommands.GAME_PASS : self.set_pass, classes.leagueLobbyCommands.CANCEL_START : self.cancel,
                                classes.leagueLobbyCommands.SHUFFLE : self.lobby_shuffle,
                                classes.steamCommands.LEAVE_LOBBY : self.leave_lobby, classes.steamCommands.LEAVE_PARTY : self.leave_party, 
                                classes.steamCommands.STATUS : self.send_status
                            }

        ##debug enable flag
        self.debug = True

        ##enable library debugging
        if(self.debug):
            logging.basicConfig(filename=sBot.name + ".log", format='[%(asctime)s] %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
            logging.debug("====================NEW SESSION====================DEADBEEF====================")

        self.__register_steam_callbacks()
        self.__register_dota_callbacks()


    def run(self):

        ##initiate log on
        self.botLog("logging in")

        while(not self.client.logged_on):
            try:
                self.client.cli_login(username=self.sBot.username, password=self.sBot.password)
            except Exception as e:
                self.botLog(e)
                self.botLog("logon failed, sleeping 60 and retrying")
                self.client.sleep(60)

        ##update my steam id
        self.bot_SteamID = self.client.steam_id

        ##main loop
        while(not self.stop_event.isSet()):

            ##check zmq
            self.recvMsg()

            ##checks if the lobby has timed out
            self.timeoutHandler()

            ##sleeps for a second
            self.client.sleep(0.5)



        self.freeBot()

        self.botLog("Exited loop")

        self.client.disconnect()
        self.botLog("Called disconnect")

        self.client.logout()
        self.botLog("Called logout")


    def __register_steam_callbacks(self):
        self.client.on('logged_on', self.steam_logon_handler)
        self.client.on('disconnected', self.restart)
        self.client.friends.on('friend_invite', self.friend_invite)
        self.client.on(EMsg.ClientFriendMsgIncoming, self.steam_message_handler)

    def __register_dota_callbacks(self):
        self.dota.on('ready', self.dota_ready_handler)
        self.dota.on('lobby_changed', self.lobby_change_handler)
        self.dota.on('team_changed', self.team_change_handler)
        self.dota.on('lobby_removed', self.lobby_removed)
        self.dota.on('lobby_invite', self.lobby_invite)
        self.dota.on('lobby_new', self.on_lobby_joined)
        self.dota.on('party_invite', self.party_invite)
        self.dota.on(dGCMsg.EMsgGCChatMessage, self.lobby_message_handler)


    def botLog(self, text):
        try:
            ##log to logging, and in return the file
            if(self.debug):
                logging.debug(self.sBot.name + ": " +  str(text))
            
            ##print to stdout
            print(self.sBot.name + ": " +  str(text), flush=True)

        ##we hit this if people have names with dumb characters the terminal cannot print
        except:
            print(self.sBot.name + ": Logging error. Probably some retard name", flush = True)


    ##after logon, launch dota
    def steam_logon_handler(self):
        self.botLog("Logged into steam")

        ##if the startupcommand is launch Dota, rejoin Lobby, or host Lobby we want to continue with the startup procedure
        if(self.gameInfo.startupCommand in [classes.slaveBotCommands.LAUNCH_DOTA, classes.slaveBotCommands.HOST_LOBBY, classes.slaveBotCommands.REJOIN_LOBBY]):

            ##we do not need to do anything else special here, launch dota handles that
            self.launch_dota()


    ##Launch Dota
    def launch_dota(self):
        if(self.dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            self.botLog("Already in logon queue")
            return
        elif(not self.dota.connection_status is dConStat.HAVE_SESSION):
            self.botLog("launching dota")
            self.dota.launch()
        else:
            self.botLog("Dota is already online. called ready handler")
            self.dota_ready_handler()


    ##At this point dota is ready
    def dota_ready_handler(self):

        ##log connection status here, debug purposes
        self.botLog("Dota is ready")

        ##host lobby specific code
        if(self.gameInfo.startupCommand == classes.slaveBotCommands.HOST_LOBBY):
            if(not self.hosted.isSet()):
                self.hostLobby()

        ##rejoin lobby specific code
        elif(self.gameInfo.startupCommand == classes.slaveBotCommands.REJOIN_LOBBY):

            ##set hosted 
            self.hosted.set()

            ##check if we have a lobby to rejoin
            if(self.dota.lobby == None):
                self.botLog("Attempted to rejoin a lobby, but it did not exist! The lobby probably ended...")
                self.botCleanup()
            else:
                self.botLog("Lobby rejoined")

    
    ##attempts to restart steam
    def restart(self):
        if(not self.stop_event.isSet()):
            #self.botLog("disconnected from steam")
            if(self.reconnecting.locked()):
                return
            with self.reconnecting:
                #self.botLog("Attempting to relog...")
                self.client.reconnect()
        else:
            self.botLog("No need to reconnect, we are stopping")

    ##determines if the actual teams have changed, and if so, emits the "team_changed" event
    def emit_team_change_event(self, msg):
        
        ##temp variables 
        changed = False
        tmpPlayers = [[], []]

        ##iterate over lobby members
        for member in self.dota.lobby.members:

            ##track players that join the lobby
            if(not member.id in self.gameInfo.members):
                self.lobby_broadcast_slot(member)
            self.gameInfo.members.append(member.id)

            ##if the person joined a team, add to our temporary player array
            if(member.team in [0, 1]):
                tmpPlayers[member.team].append(member.id)

                ##if they were not in a team before, we have a real team_change
                if(not member.id in self.gameInfo.currPlayers[member.team]):
                    changed = True

        ##update our gameInfo's current player array
        self.gameInfo.currPlayers = tmpPlayers

        ##send team change event if the teams did indeed change
        if(changed):
            self.dota.emit("team_changed", msg)

    ##broadcast slot to join to new member
    def lobby_broadcast_slot(self, member):

        ##iterate over the teams
        for i in range(0, len(self.gameInfo.teams)):

            ##if our member is supposed to be on a team
            if(str(member.id) in self.gameInfo.teams[i]):

                loop = 0

                ##wait for member to be in the chat channel (10 seconds max)
                while(True and loop < 5):

                    ##wait 2 seconds for a member update event
                    res = self.dota.channels.wait_event("members_update", 2.0)

                    ##if we got the update
                    if(not res == None):

                        ##split response
                        channel, joined, left = res

                        ##dont send message while we are launching (we shouldn't be able to launch while missing a member)
                        if(member.id in joined and not self.launching.isSet()):
                            self.sendLobbyMessage(member.name + ", please join the " + ("radiant" if i == 0 else "dire") + " team.")
                            return
                    
                    ##increment loop counter
                    loop += 1
                

    ##dota lobby on lobby change event handler
    def lobby_change_handler(self, msg):

        ##only update if we are hosting a lobby
        if(self.hosted.isSet()):
            self.botLog("The hosted lobby has changed")

            ##update lobby object
            self.gameInfo.lobby = msg

            ##emit teams changed
            self.emit_team_change_event(msg)

    ##called on "team_changed" event
    def team_change_handler(self, msg):
        self.botLog("team changed")
        if(len(set(self.gameInfo.players)) > 0):
            for member in self.dota.lobby.members:
                if(member.team in [0, 1]):

                    ##if player is not supposed to be in a team
                    if(not str(member.id) in self.gameInfo.players):

                        ##add to kicklist if not already
                        if(not str(member.id) in self.kickList):
                            self.kickList[str(member.id)] = 0

                        ##increment kick counter
                        self.kickList[str(member.id)] += 1
                        self.botLog(member.name + " kick #" + str(self.kickList[str(member.id)]))

                        ###if kicked 3 times already, kick from lobby
                        if(self.kickList[str(member.id)] > 3):
                            self.botLog("kicking " + str(member.name) + "from lobby")
                            self.dota.practice_lobby_kick(SteamID(member.id).as_32)

                        ##kick from slot
                        else:
                            self.botLog("kicking " + str(member.name) + "from team slots")
                            self.dota.practice_lobby_kick_from_team(SteamID(member.id).as_32)
                
                    ##if player IS supposed to be in a team
                    else:
                        for i in range(0, len(self.gameInfo.teams)):
                            ##if player is in the wrong team, kick from team and send mesasge
                            if(str(member.id) in self.gameInfo.teams[i] and not member.team == i):
                                self.dota.practice_lobby_kick_from_team(SteamID(member.id).as_32)
                                self.sendLobbyMessage(member.name + ", please join the " + ("radiant" if i == 0 else "dire") + " team.")
        
        ##update lobby
        self.gameInfo.lobby = self.dota.lobby
        
        cmd = classes.command(classes.botFactoryCommands.UPDATE_LOBBY, [self.gameInfo])
        zmqutils.sendObjDealer(self.sock, cmd)

                        

    #TODO: this shit is a fucking mess
    #Triggers on launch if previous lobby existed.
    def lobby_removed(self, msg):

        ##if we weren't hosting, it does not matter that the lobby is gone
        if(not self.hosted.isSet()):
            return

        ##save matchid, dump match response to that file
        matchId = msg.match_id
        with open(os.getcwd() + "/matchResults/" + str(matchId) + "_basic.txt", "w") as f:
            f.write(str(msg))

        ##attempt to get match details
        retries = 0
        match_job = self.dota.request_match_details(int(matchId))
        matchRes = self.dota.wait_msg(match_job, timeout=10)

        ##we only want to try 5 times, or until we get it
        while(not matchRes.result == 1 and retries < 5):

            ##wait 5 seconds, then try again
            self.dota.sleep(5)
            self.botLog("Unable to get match result... retrying " + str(retries))
            retries += 1
            match_job = self.dota.request_match_details(int(matchId))
            matchRes = self.dota.wait_msg(match_job, timeout=10)

        ##we got a result here, so save details, and request a process
        if(matchRes.result == 1):
            with open(os.getcwd() + "/matchResults/" + str(matchId) + "_detailed.txt", "w") as f:
                f.write(str(matchRes.match))
            cmd = classes.command(classes.botFactoryCommands.PROCESS_BASIC, [self.gameInfo, matchRes])
            zmqutils.sendObjDealer(self.sock, cmd)

        ##we did not get a result, request process on the original message
        else:
            self.botLog("ERROR: UNABLE TO GET DATA FOR " + str(matchId))
            cmd = classes.command(classes.botFactoryCommands.PROCESS_BASIC ,[self.gameInfo, msg])
            zmqutils.sendObjDealer(self.sock, cmd)
        
        self.botCleanup()


    def steam_message_handler(self, msg):
        
        ##decode the weirdness that is steam messages
        msgT = msg.body.message.decode("utf-8").rstrip('\x00')
        if(not msg.body.steamid_from in header.LD2L_ADMIN_STEAM_IDS):
            return

        ##if the length is 0, then the message was just someone typing
        if(len(msgT) > 0):

            cmd = None

            ##parse message
            cMsg = msgT.lower().split()

            ##release the bot from the current lobby
            if(msgT == "release" or msgT == "!release"):
                self.botLog("releasing")
                self.botCleanup()

            ##start the lobby immediately
            elif(msgT == "start" or msgT == "!start"):
                self.botLog("starting")
                self.dota.launch_practice_lobby()

            ##start dota
            elif(msgT == "launchdota" or msgT == "!launchdota"):
                self.botLog("got launchdota")
                cmd = classes.command(classes.slaveBotCommands.LAUNCH_DOTA, [])

            ##rejoin last lobby
            elif(msgT == "rejoinlobby" or msgT == "!rejoinlobby"):
                self.botLog("got rejoinlobby")
                cmd = classes.command(classes.slaveBotCommands.REJOIN_LOBBY, [])
            
            ##host a new lobby
            elif(msgT == "hostlobby" or msgT == "!hostlobby"):
                self.botLog("got hostlobby")
                cmd = classes.command(classes.slaveBotCommands.HOST_LOBBY, [])

            ##do work here if we have to
            if(not cmd is None):
                self.parseCommand(cmd)

    def lobby_message_handler(self, msg):

        ##I don't know why we get these empty messages sometimes (/roll maybe?)
        if(len(msg.text) > 0):

            ##"anyways" isn't a word.
            if("anyways" in msg.text.lower()):
                self.sendLobbyMessage("\"anyways\" isn't a word")

            ##parse message
            cMsg = msg.text.split()

            ##its a command, strip the '!'
            if(cMsg[0].startswith("!")):
                cMsg[0] = cMsg[0][1:]
            
            ##process command
            command = self.lobby_command_translation[cMsg[0].lower()] if cMsg[0].lower() in self.lobby_command_translation else classes.lobbyCommands.INVALID_COMMAND
            self.function_translation[command](cMsg, msg = msg)

    ##automatically accept friend invites
    def friend_invite(self, msg):
        self.client.friends.add(msg)

    ##accept lobby invites from trusted sources
    def lobby_invite(self, msg):
        if(msg.sender_id in header.LD2L_ADMIN_STEAM_IDS):
            if(self.dota.lobby == None):
                self.botLog("joining lobby")
                self.dota.respond_lobby_invite(msg.group_id, accept=True)


    def on_lobby_joined(self, msg):
        if(self.hosted.isSet()):

            ##send created state
            cmd = classes.command(classes.botFactoryCommands.UPDATE_STATE, [classes.stateData(self.gameInfo.hook, classes.lobbyState.CREATED, "Lobby created", keys.LD2L_API_KEY, self.gameInfo.ident)])
            zmqutils.sendObjDealer(self.sock, cmd)

            ##msg is set to none for web requests
            if(self.lobby_msg != None):
                args = [self.gameInfo.lobbyName, self.gameInfo.lobbyPassword, self.lobby_msg, self.sBot]
                self.dscQ.put(classes.command(classes.discordCommands.LOBBY_CREATE_MESSAGE, args))
            else:
                self.gameInfo.jobQueue.put((True, self.gameInfo))
            
            ##join chat channel
            self.dota.channels.join_channel("Lobby_%s" % msg.lobby_id, channel_type=3)

            ##switch to unassigned team so we don't prevent the lobby from loading
            self.dota.join_practice_lobby_team(4)

            ##invite all players
            for player in self.gameInfo.players:
                self.dota.invite_to_lobby(SteamID(player).as_64)

                ##attempt to fix the missing invites
                self.client.sleep(0.3)


    ##party invite event handler
    def party_invite(self, msg):
        if(msg.sender_id in header.LD2L_ADMIN_STEAM_IDS):
            self.botLog("accepting party invite")
            self.leave_lobby()
            self.dota.leave_party()
            if(self.dota.party == None):
                self.botLog(msg)
                self.dota.respond_to_party_invite(msg.group_id, accept=True)


    def hostLobby(self):

        ##leave existing lobby
        if(self.dota.lobby):
            test = self.dota.leave_practice_lobby()
            self.dota.wait_event("lobby_removed", 5.0)

        ##set lobby settings field
        self.d['game_name'] = self.gameInfo.lobbyName
        self.d['game_mode'] = dota2.enums.DOTA_GameMode.DOTA_GAMEMODE_CM
        self.d['server_region'] = dota2.enums.EServerRegion.USEast ##USWest, USEast, Europe
        self.d['allow_cheats'] = False
        self.d['visibility'] = dota2.enums.DOTALobbyVisibility.Public ##Public, Friends, Unlisted
        self.d['dota_tv_delay'] = dota2.enums.LobbyDotaTVDelay.LobbyDotaTV_120
        self.d['pause_setting'] = dota2.enums.LobbyDotaPauseSetting.Unlimited ##Unlimited, Limited, Disabled
        self.d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
        self.d['allow_spectating'] = True
        self.d['fill_with_bots'] = False
        self.d['selection_priority_rules'] = dota2.enums.DOTASelectionPriorityRules.Automatic

        ##set tournament (ticket), if a league id was provided
        if(not self.gameInfo.tournament == None and not self.gameInfo.tournament == 0):
            self.d["leagueid"] = int(self.gameInfo.tournament)

        ##set additional options from request
        for key, val in self.gameInfo.config.items():
            self.d[key] = val

        ##create lobby
        self.dota.create_practice_lobby(password=self.gameInfo.lobbyPassword, options=self.d)

        ##five minutes to get in a lobby
        self.gameInfo.timeout = int(time.time()) + 600

        ##set hosted event
        self.hosted.set()


    #nop
    def naw(self, *args, **kwargs):
        pass

    ##wrapper for lobby chat
    def sendLobbyMessage(self, message):
        self.dota.channels.lobby.send(message)

    ##sets a draft penalty
    def set_penalty(self, *args, **kwargs):

        ##disabled for now
        return

        ##prevents null pointers
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]

            ##message must be 3 words in length
            if(len(cMsg) < 3):
                self.sendLobbyMessage("Please specify a side and a penalty level (0 - 3)")
                return

            ##parse side parameter
            side = str(cMsg[1]).lower().strip()

            ##validate side parameter
            if(edit_distance.distance(side, 'radiant') < 3):
                self.d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "radiant"
            elif(edit_distance.distance(side, 'dire') < 3):
                self.d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "dire"
            else:
                self.sendLobbyMessage("Invalid side (Radiant, Dire)")
                return
            
            ##parse level parameter
            level = cMsg[2].strip()

            ##validate level parameter
            try:
                level = int(level)
            except:
                level = 4
            if(not level in range(0,4)):
                self.sendLobbyMessage("Invalid penalty level (0 - 3)")
                return

            ##set penalty level
            self.d['penalty_level_' + side] = level
            self.dota.config_practice_lobby(self.d)
            ##TODO: second translation here
            self.sendLobbyMessage("Set penalty level of " + side + " to " + str(level))


    ##swaps the two teams
    def swap_teams(self, *args, **kwargs):

        ##disabled for now
        return

        ##prevents null pointers
        if('msg' in kwargs):
            msg = kwargs['msg']

            ##swap teams in gameInfo
            self.gameInfo.teams[0], self.gameInfo.teams[1] = self.gameInfo.teams[1], self.gameInfo.teams[0]

            ##swap teams in lobby
            self.dota.flip_lobby_teams()
            
            ##swap ready sides
            self.sides_ready[0], self.sides_ready[1] = self.sides_ready[1], self.sides_ready[0]
            self.sendLobbyMessage("Sides switched")
            self.reset_ready(msg=msg)

    ##updates the game server
    def set_server(self, *args, **kwargs):

        ##prevents null pointers
        if('msg' in kwargs):
            msg = kwargs['msg']

            ##check if initiator was a captain
            if(not str(SteamID(msg.account_id).as_64) in self.gameInfo.captains):
                self.sendLobbyMessage("You must be a captain to use this command.")
                return
            
            ##parse command
            cMsg = args[0]

            ##validate command parameter length
            if(len(cMsg) < 2):
                self.sendLobbyMessage("Please specify a server region (USW USE EU)")
                return

            ##parse server parameter
            server = str(cMsg[1]).lower().strip()
            if(server == 'usw'):
                self.d['server_region'] = dota2.enums.EServerRegion.USWest
            elif(server == 'use'):
                self.d['server_region'] = dota2.enums.EServerRegion.USEast
            elif(server == 'eu'):
                self.d['server_region'] = dota2.enums.EServerRegion.Europe
            else:
                self.sendLobbyMessage("Invalid region (USW USE EU)")
                return

            ##update lobby
            self.dota.config_practice_lobby(self.d)
            self.reset_ready(msg=msg)
            self.sendLobbyMessage(("Set region to " + server.upper()))


    ##set lobby name
    def set_name(self, *args, **kwargs):

        ##disabled for now
        return

        ##prevents null pointer
        if('msg' in kwargs):
            msg = kwargs['msg']

            ##parse command
            cMsg = args[0]

            ##validate command parameter length
            if(len(cMsg) < 2):
                self.sendLobbyMessage("Please specify a lobby name")
                return

            ##update lobby name
            self.gameInfo.lobbyName = str(cMsg[1]).strip()
            self.d['game_name'] = self.gameInfo.lobbyName
            self.dota.config_practice_lobby(self.d)
            self.sendLobbyMessage("Set lobby name to '" + self.gameInfo.lobbyName + "'")
            self.reset_ready(msg=msg)


    ##set password 
    def set_pass(self, *args, **kwargs):

        ##disabled for now
        return

        ##prevents null pointer
        if('msg' in kwargs):
            msg = kwargs['msg']

            ##parse command
            cMsg = args[0]

            ##validate comamnd parameter length
            if(len(cMsg) < 2):
                self.sendLobbyMessage("Please specify a lobby password")
                return

            ##update lobby password
            self.gameInfo.lobbyPassword = str(cMsg[1]).strip()
            self.d['pass_key'] = self.gameInfo.lobbyPassword
            self.dota.config_practice_lobby(self.d)
            self.sendLobbyMessage("Set lobby password to '" + self.gameInfo.lobbyPassword + "'")
            self.reset_ready(msg=msg)


    ##shuffle the lobby
    def lobby_shuffle(self, *args, **kwargs):

        ##disabled for now
        return

        ##prevents null pointer
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]

            ##shuffle the lobby
            self.dota.balanced_shuffle_lobby()
            self.sendLobbyMessage("Lobby shuffled")


    ##set first pick
    def first_pick(self, *args, **kwargs):

        ##disabled for now
        return

        ##prevents null pointer
        if('msg' in kwargs):
            msg = kwargs['msg']

            ##parse command
            cMsg = args[0]

            ##validate command parameter length
            if(len(cMsg) < 2):
                self.sendLobbyMessage("Please specify a side (Radiant, Dire)")
                return

            ##validate side parameter
            side = str(cMsg[1]).lower().strip()
            if(edit_distance.distance(side, 'radiant') < 3):
                self.d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "Radiant"
            elif(edit_distance.distance(side, 'dire') < 3):
                self.d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "Dire"
            else:
                self.sendLobbyMessage("Invalid side (Radiant, Dire)")
                return

            ##update lobby config
            self.sendLobbyMessage("Gave first pick to " + side)
            self.dota.config_practice_lobby(self.d)
            self.reset_ready(msg=msg)


    ##start the lobby
    def start_lobby(self, *args, **kwargs):

        ##prevents null pointer
        if ('msg' in kwargs):

            ##make sure both teams have set a team name
            if(not len(self.dota.lobby.team_details) == 2 or any(x.team_id == 0 for x in self.dota.lobby.team_details)):
                self.sendLobbyMessage("Both teams must have a name set before starting.")
                return

            ##parse command
            msg = kwargs['msg']

            ##initialize temporary variables
            tot_mem = 0
            sender_team = -1

            ##iterate through lobby members
            for member in self.dota.lobby.members:

                ##if member is on a team, increase total member count
                if member.team == 0 or member.team == 1:
                    tot_mem += 1
                    self.botLog("found member " + str(member.name))

                    ##if member was the one who initiated the request, record which team they are on
                    if(SteamID(member.id).as_64 == SteamID(msg.account_id).as_64):
                        sender_team = member.team

            ##if we have 10 players on teams in the lobby
            if(tot_mem >= 10 or tot_mem == len(set(self.gameInfo.players)) or SteamID(msg.account_id).as_64 in header.LD2L_ADMIN_STEAM_IDS):

                ##record which team readied up
                if(sender_team == 1 or sender_team == 0):
                    self.sides_ready[sender_team] = True
                else:
                    self.sendLobbyMessage("Please only ready up if you are on a team.")
                    return
            else:
                self.sendLobbyMessage("Please wait for the teams to be filled")
                return
            
            ##check if both teams are ready
            launch = True
            for side in self.sides_ready:
                launch = side and launch

            ##if we are ready to launch, and not launching already
            if(launch and not self.launching.is_set()):

                ##set launching flag, alert lobby
                self.launching.set()
                self.sendLobbyMessage("Starting lobby. Use !cancel to stop countdown")

                ##launch countdown
                for i in range(5, 0, -1):
                    for side in self.sides_ready:
                        launch = side and launch
                    if(launch):
                        self.sendLobbyMessage(str(i))
                        self.dota.sleep(1)
                    else:
                        self.sendLobbyMessage("Countdown canceled")
                        self.launching.clear()
                        return

                ##after countdown, sanity check everyone is ready, and launch if so
                if(not len(self.dota.lobby.team_details) == 2 or any(x is None for x in self.dota.lobby.team_details)):
                    self.reset_ready()
                    self.sendLobbyMessage("Cannot start lobby without both teams being set!")
                else:
                    self.dota.launch_practice_lobby()

                ##clean up launching flag
                self.launching.clear()

            ##only one side is ready
            elif(not self.launching.is_set()):
                self.sendLobbyMessage("One side readied up. Waiting for other team..")


    ##leaves current lobby
    def leave_lobby(self, *args, **kwargs):

        ##check if in lobby
        self.dota.leave_practice_lobby()

        ##if this was a message, send a response
        if('msg' in kwargs):
            msg = kwargs['msg']
            self.client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving lobby")

    ##leaves current party
    def leave_party(self, *args, **kwargs):

        ##check if in party
        self.dota.leave_party()

        ##if this was a message, send a response
        if('msg' in kwargs):
            msg = kwargs['msg']
            self.client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving party")


    ##sends current status
    def send_status(self, *args, **kwargs):

        ##parse message
        msg = kwargs['msg']
        mid = msg.body.steamid_from
        requester = self.client.get_user(SteamID(mid))

        ##send response 
        requester.send_message("Party: " + str("None" if self.dota.party == None else "Active"))
            ##TODO parse and send party info
        requester.send_message("Lobby: " + str("None" if self.dota.lobby == None else "Active"))
            ##TODO parse and send lobby info


    ##cancels a readyup
    def cancel(self, *args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(not str(SteamID(msg.account_id).as_64) in self.gameInfo.captains):
                self.sendLobbyMessage("You must be a captain to use this command.")
                return
            self.reset_ready()


    ##resets the ready status
    def reset_ready(self, *args, **kwargs):

        ##set the sides to not ready
        self.sides_ready[0] = False
        self.sides_ready[1] = False

        ##notify the lobby
        if ('msg' in kwargs):
            msg = kwargs['msg']
            self.sendLobbyMessage("Reset ready status.")


    ##cleans up the bot
    def botCleanup(self, shutdown = False):
        self.botLog("shutting down")

        ##if there was a lobby, leave it
        if(not self.gameInfo.jobQueue == None):
            self.gameInfo.jobQueue.put((False, None))
            self.dota.leave_practice_lobby()

        ##if we want to shutdown, do it
        if(shutdown):
            self.stop_event.set()

        ##otherwise just leave dota
        else:    
            self.dota.exit()
            self.hosted.clear()
            self.freeBot()


    ##handles lobby timeout
    def timeoutHandler(self, *args, **kwargs):

        ##if we have a lobby hsoted and we timeout
        if(self.hosted.isSet() and time.time() > self.gameInfo.timeout):
            
            ##if we are already shutting down, do nothing
            if(self.stop_event.isSet()):
                self.botLog("timeout occoured, but bot is already shutting down!")
                return

            ##if we aren't in a lobby, there is nothing to really do, but clean up anyway
            if(self.dota.lobby == None):
                self.botLog("lobby not found")
                self.botCleanup()

            ##if we aren't alone dont clean up
            elif(len(self.dota.lobby.members) < 2):
                    self.botLog("cleaning up empty lobby")
                    self.botCleanup()

                    
    def parseCommand(self, cmd):
        ##invite a player
        if(cmd.command == classes.slaveBotCommands.INVITE_PLAYER):
            self.botLog("got command to invite player")
            self.dota.invite_to_lobby(SteamID(cmd.args[0]).as_64)

        ##release this bot
        elif(cmd.command == classes.slaveBotCommands.RELEASE_BOT):
            self.botLog("got command to release bot")
            self.gameInfo.startupCommand = classes.slaveBotCommands.RELEASE_BOT
            self.botCleanup()

        ##launch dota
        elif(cmd.command == classes.slaveBotCommands.LAUNCH_DOTA):
            self.botLog("got command to launch dota")
            self.gameInfo.startupCommand = classes.slaveBotCommands.LAUNCH_DOTA
            self.launch_dota()

        ##rejoin existing lobby
        elif(cmd.command == classes.slaveBotCommands.REJOIN_LOBBY):
            self.botLog("got command to rejoin lobby")
            self.gameInfo.startupCommand = classes.slaveBotCommands.REJOIN_LOBBY
            self.launch_dota()

        ##host a new lobby
        elif(cmd.command == classes.slaveBotCommands.HOST_LOBBY):
            self.botLog("got command to host lobby")

            ##update existing info
            if(len(cmd.args) > 0):
                self.gameInfo.update(cmd.args[0])
                self.d = {}

            ##set startup command, then launch dota to trigger it
            self.gameInfo.startupCommand = classes.slaveBotCommands.HOST_LOBBY
            self.launch_dota()

    def recvMsg(self):
        try:
            cmd = zmqutils.recvObjDealer(self.sock, zmq.DONTWAIT)

            self.parseCommand(cmd)
        except zmq.error.Again as e:
            ##self.botLog("Nothing to recv currently.")
            pass
        except Exception as e:
            print("socket error:\n %s" % str(e))




    ##notifies factory that the bot is done and ready for more jobs
    def freeBot(self):
        ##update (remove) lobby
        cmd = classes.command(classes.botFactoryCommands.UPDATE_STATE, [classes.stateData(self.gameInfo.hook, classes.lobbyState.REMOVED, "Bot shutting down", keys.LD2L_API_KEY, self.gameInfo.ident)])
        zmqutils.sendObjDealer(self.sock, cmd)
        self.botLog("Called state update (shutdown)")

        ##free bot for future use
        cmd = classes.command(classes.botFactoryCommands.FREE_SLAVE, [self.sBot, self.gameInfo])
        zmqutils.sendObjDealer(self.sock, cmd)
        self.botLog("Put shutdown command")

    ##Rejoin Lobby
    def rejoin_lobby(self):
        if(not self.dota.connection_status is dConStat.HAVE_SESSION):
            self.launch_dota()



if(__name__ == "__main__"):
    botnum = 0
    sBot = classes.steamBotInfo(keys.SLAVEBOTNAMES[botnum], keys.SLAVEUSERNAMES[botnum], keys.SLAVEPASSWORDS[botnum], keys.SLAVEBOTSTEAMLINKS[botnum])
    kstQ = queue.Queue()
    dstQ = queue.Queue()
    gameInfo = classes.gameInfo()
    gameInfo.lobbyName = "test"
    gameInfo.lobbyPassword = "test"
    gameInfo.jobQueue = queue.Queue()
    gameInfo.commandQueue = queue.Queue()
    gameInfo.players = []
    gameInfo.teams = [[], []]
    gameInfo.startupCommand = classes.slaveBotCommands.HOST_LOBBY
    slave = SteamSlave(sBot, kstQ, dstQ, gameInfo)
    slave.start()
    
