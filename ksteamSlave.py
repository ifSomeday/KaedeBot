from gevent import monkey
monkey.patch_ssl()
monkey.patch_socket()

from steam import SteamClient
from steam import WebAPI
from steam import SteamID
from dota2 import Dota2Client
import dota2
import discord

##ENUM IMPORTS
from steam.enums.emsg import EMsg
from dota2.enums import EDOTAGCMsg as dGCMsg
from dota2.enums import ESOMsg as dEMsg
from dota2.enums import ESOType as dEType
from dota2.enums import DOTA_GameState as dGState
from dota2.enums import EMatchOutcome as dOutcome

from threading import Thread
import threading
import queue
import classes
import time
import os
import pickle

import keys, edit_distance

def steamSlave(sBot, kstQ, dscQ, steamId, lobby_password):
    client = SteamClient()
    dota = Dota2Client(client)
    bot_SteamID = None

    hosted = False

    sides_ready = [False, False]

    stop_event = threading.Event()

    lobby_command_translation = {"switchside" : classes.leagueLobbyCommands.SWITCH_SIDE, "fp" : classes.leagueLobbyCommands.FIRST_PICK,
                                "server": classes.leagueLobbyCommands.SERVER, "start" : classes.leagueLobbyCommands.START}

    def botLog(text):
        try:
            print(sBot.name + ": " +  str(text), flush=True)
        except:
            print(sBot.name + ": Logging error. Probably some retard name", flush = True)


    ##after logon, launch dota
    @client.on('logged_on')
    def start_dota():
        botLog("Logged into steam, starting dota")
        dota.launch()
        pass

    ##At this point dota is ready
    @dota.on('ready')
    def ready0():
        botLog("Dota is ready")
        hostLobby()

    @dota.on('notready')
    def reload():
        if(not stop_event.isSet()):
            botLog("out of dota, restarting...")
            dota.exit()
            dota.launch()
        pass

    @client.on('disconnected')
    def restart():
        if(not stop_event.isSet()):
            botLog("disconnected from steam. Attempting to relog...")
            client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)

    ##dota lobby on lobby change event handler
    @dota.on('lobby_changed')
    def lobby_change_handler(msg):
        return
        lobby_stat = dota.lobby
        if(not lobby_stat == None):
            if(len(lobby_stat.members) <= 1 and not lobby_stat.leader_id == bot_SteamID.as_64):
                botLog("Lobby is dead, leaving")
                leave_lobby()

    #TODO: this shit is a fucking mess
    @dota.on('lobby_removed')
    def lobby_removed(msg):
        if(not hosted):
            return
        if(msg.game_state == dGState.DOTA_GAMERULES_STATE_POST_GAME):
            teamArray = []
            api = WebAPI(key = keys.STEAM_WEBAPI)
            hero_dict = api.IEconDOTA2_570.GetHeroes(language='en_us')['result']
            winner = msg.match_outcome
            if(winner == dOutcome.RadVictory or winner == dOutcome.DireVictory):
                with open(os.getcwd() + '/dataStores/teamArray.pickle', 'rb') as f:
                    teamArray = pickle.load(f)
                radiant_team_arr = []
                radiant_hero_arr = []
                dire_team_arr = []
                dire_hero_arr = []
                for member in msg.members:
                    if(member.team == 0):
                        radiant_team_arr.append(SteamID(member.id).as_32)
                        radiant_hero_arr.append(classes.get_hero_name(member.hero_id, hero_dict))
                    elif(member.team == 1):
                        dire_team_arr.append(SteamID(member.id).as_32)
                        dire_hero_arr.append(classes.get_hero_name(member.hero_id, hero_dict))
                radiant_team = None
                dire_team = None
                r_team_str = ""
                d_team_str = ""
                for team in teamArray:
                    teamCountRadiant = 0
                    teamCountDire = 0
                    for player in team.players:
                        if str(player.steamID) in str(radiant_team_arr):
                            teamCountRadiant += 1
                            r_team_str += (", " if not teamCountRadiant == 1 else "") + player.playerName
                        elif str(player.steamID) in str(dire_team_arr):
                            teamCountDire += 1
                            d_team_str += (", " if teamCountRadiant == 1 else "") + player.playerName
                    if(teamCountRadiant >= 1):
                        radiant_team = team
                    elif(teamCountDire >= 1):
                        dire_team = team
                r_team_str = (radiant_team.captain.playerName if radiant_team else "Unknown") + "'s team " + ("(" + r_team_str + ")" if r_team_str else "")
                d_team_str = (dire_team.captain.playerName if dire_team else "Unkown") + "'s team " + ("(" + d_team_str + ")" if d_team_str else "")

                out = (r_team_str if winner == dOutcome.RadVictory else d_team_str) + " beat " + (d_team_str if winner == dOutcome.RadVictory else r_team_str)
                dscQ.put(classes.command(classes.discordCommands.BROADCAST_MATCH_RESULT, [out]))
            else:
                botLog("lobby died")
        botLog("removed")
        botCleanup()

    @client.on(EMsg.ClientFriendMsgIncoming)
    def steam_message_handler(msg):
        ##TODO: check you have permission to release
        msgT = msg.body.message.decode("utf-8").rstrip('\x00')
        if(len(msgT) > 0):
            if(msgT == "release"):
                botLog("releasing")
                botCleanup()
            if(msgT == "lobby"):
                hosted = False
                hostLobby()

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
        if(dota.lobby == None):
            botLog("joining lobby")
            dota.respond_lobby_invite(msg.group_id, accept=True)

    @dota.on('lobby_new')
    def on_lobby_joined(msg):
        dota.channels.join_channel("Lobby_%s" % msg.lobby_id,channel_type=3)
        dota.join_practice_lobby_team(team=4)

    def hostLobby(tournament=False):
        if(dota.lobby):
            dota.leave_practice_lobby()
        d = {}
        d['game_name'] = "SEAL: " + str(steamId)
        d['game_mode'] = dota2.enums.DOTA_GameMode.DOTA_GAMEMODE_CM
        d['server_region'] = dota2.enums.EServerRegion.USWest ##USWest, USEast, Europe
        d['allow_cheats'] = False
        d['visibility'] = dota2.enums.DOTALobbyVisibility.Public ##Public, Friends, Unlisted
        d['dota_tv_delay'] = dota2.enums.LobbyDotaTVDelay.LobbyDotaTV_120 ##Unlimited, Limited, Disabled
        d['pause_setting'] = dota2.enums.LobbyDotaPauseSetting.Unlimited
        d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS ##DOTA_CM_GOOD_GUYS, DOTA_CM_BAD_GUYS
        d['allow_spectating'] = True
        d['fill_with_bots'] = False
        d['allow_cheats'] = False

        if(tournament):
            dota.create_tournament_lobby(password=lobby_password, options=d)
        else:
            dota.create_practice_lobby(password=lobby_password, options=d)
        time.sleep(1)
        dota.join_practice_lobby_team(team=4)
        botLog("Lobby hosted")
        hosted = True

    def naw(*args, **kwargs):
        pass

    def sendLobbyMessage(message, channel_id):
        dota.send(dGCMsg.EMsgGCChatMessage, {"channel_id": channel_id, "text": message})

    def swap_teams(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            dota.flip_lobby_teams()
            ##sides_ready[0], sides_ready[1] = sides_ready[1], sides_ready[0]
            sendLobbyMessage("Sides switched", msg.channel_id)

    def set_server(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a server region (USW USE EU)", msg.channel_id)
                return
            server = str(cMsg[1]).lower().strip()
            d = {}
            if(server == 'usw'):
                d['server_region'] = dota2.enums.EServerRegion.USWest
            elif(server == 'use'):
                d['server_region'] = dota2.enums.EServerRegion.USEast
            elif(server == 'eu'):
                d['server_region'] = dota2.enums.EServerRegion.Europe
            else:
                sendLobbyMessage("Invalid region (USW USE EU)", msg.channel_id)
                return
            sendLobbyMessage(("Set region to " + server.upper()), msg.channel_id)
            dota.config_practice_lobby(d)

    def first_pick(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a side (Radiant, Dire)", msg.channel_id)
                return
            side = str(cMsg[1]).lower().strip()
            d = {}
            if(edit_distance.distance(side, 'radiant') < 4):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "Dire"
            elif(edit_distance.distance(side, 'dire') < 4):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_BAD_GUYS
                side = "Radiant"
            else:
                sendLobbyMessage("Invalid side (Radiant, Dire)", msg.channel_id)
                return
            sendLobbyMessage(("Gave first pick to " + side), msg.channel_id)
            dota.config_practice_lobby(d)

    def start_lobby(*args, **kwargs):
        if ('msg' in kwargs):
            msg = kwargs['msg']
            tot_mem = 0
            sender_team = -1
            for member in dota.lobby.members:
                if member.team == 0 or member.team == 1:
                    tot_mem += 1
                    botLog("found member")
                    botLog(member)
                    if(SteamID(member.id).as_64 == SteamID(msg.account_id).as_64):
                        sender_team = member.team
            if(tot_mem == 1):
                if(sender_team == 1 or sender_team == 0):
                    sides_ready[sender_team] = True
                else:
                    sendLobbyMessage("Please only ready up if you are on a team.", msg.channel_id)
                    return
            launch = True
            for side in sides_ready:
                launch = side and launch
            if(launch):
                sendLobbyMessage("Starting", msg.channel_id)
                dota.launch_practice_lobby()
            else:
                sendLobbyMessage("One side readied up. Waiting for other team..", msg.channel_id)


    def botCleanup():
        botLog("shutting down")
        kstQ.put(classes.command(classes.steamCommands.FREE_BOT, [sBot]))
        dota.leave_practice_lobby()
        stop_event.set()

    def timeoutHandler(*args, **kwargs):
        evnt = args[0]
        if(dota.lobby == None):
            botLog("lobby not found")
            botCleanup()
        else:
            botLog("im in a lobby!")
            if(len(dota.lobby.members) < 2):
                botLog("but im alone")
                botCleanup()

    function_translation = {classes.leagueLobbyCommands.SWITCH_SIDE : swap_teams, classes.leagueLobbyCommands.FIRST_PICK : first_pick,
                            classes.leagueLobbyCommands.SERVER : set_server, classes.lobbyCommands.INVALID_COMMAND : naw,
                            classes.leagueLobbyCommands.START : start_lobby}

    ##fifteen minutes to get in a lobby
    toH = threading.Timer(900.0, timeoutHandler, [stop_event,])
    toH.start()

    client.cli_login(username=sBot.username, password=sBot.password)
    bot_SteamID = client.steam_id
    print(bot_SteamID)
    while(not stop_event.isSet()):
        client.sleep(5)
    client.disconnect()
    client.logout()
    return

if(__name__ == "__main__"):
    sBot = classes.steamBotInfo(keys.SLAVEBOTNAMES[0], keys.SLAVEUSERNAMES[0], keys.SLAVEPASSWORDS[0], keys.SLAVEBOTSTEAMLINKS[0])
    kstQ = queue.Queue()
    dstQ = queue.Queue()
    client = steamSlave(sBot, kstQ, dstQ)
