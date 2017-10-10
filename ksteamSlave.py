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
import header

import keys, edit_distance

def steamSlave(sBot, kstQ, dscQ, factoryQ, args):
    client = SteamClient()
    dota = Dota2Client(client)
    bot_SteamID = None

    lobby_name = args[0]
    lobby_pass = args[1]
    lobby_msg = args[2]

    hosted = False

    kyouko_toshino = SteamID(75419738)

    d = {}

    sides_ready = [False, False]

    stop_event = threading.Event()

    lobby_command_translation = {"switchside" : classes.leagueLobbyCommands.SWITCH_SIDE, "fp" : classes.leagueLobbyCommands.FIRST_PICK,
                                "firstpick" :  classes.leagueLobbyCommands.FIRST_PICK, "server": classes.leagueLobbyCommands.SERVER,
                                "start" : classes.leagueLobbyCommands.START, "name" : classes.leagueLobbyCommands.GAME_NAME,
                                "pass" : classes.leagueLobbyCommands.GAME_PASS, "password" : classes.leagueLobbyCommands.GAME_PASS}

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
        hostLobby(tournament=True)

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
        else:
            botlog("hosted lobby disappeared")
            botCleanup()

    @client.on(EMsg.ClientFriendMsgIncoming)
    def steam_message_handler(msg):
        ##TODO: check you have permission to release
        msgT = msg.body.message.decode("utf-8").rstrip('\x00')
        if(len(msgT) > 0):
            if(msgT == "release" and msg.body.steamid_from == kyouko_toshino.as_64):
                botLog("releasing")
                botCleanup()
            if(msgT == "lobby" and SteamID(msg.body.steamid_from).as_32 in list(header.captain_steam_ids.keys())):
                hosted = False
                hostLobby(tournament=True)

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
        botLog("name: " + lobby_name)
        botLog("pass: " + lobby_pass)
        d['game_name'] = lobby_name
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
            #d['leagueid'] = 5432
            pass
        dota.create_practice_lobby(password=lobby_pass, options=d)
        time.sleep(1)
        dota.join_practice_lobby_team(team=4)
        botLog("Lobby hosted")
        hosted = True
        dscQ.put(classes.command(classes.discordCommands.LOBBY_CREATE_MESSAGE, args))

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
            if(len(cMSG) < 2):
                sendLobbyMessage("Please specify a lobby name", msg.channel_id)
                return
            lobby_name = str(cMsg[1]).strip()
            d['game_name'] = lobby_name
            dota.config_practice_lobby(d)
            sendLobbyMessage("Set lobby name to '" + lobby_name + "'")
            reset_ready(msg=msg)

    def set_pass(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMSG) < 2):
                sendLobbyMessage("Please specify a lobby password", msg.channel_id)
                return
            lobby_pass = str(cMsg[1]).strip()
            d['pass_key'] = lobby_pass
            dota.config_practice_lobby(d)
            sendLobbyMessage("Set lobby password to '" + lobby_pass + "'")
            reset_ready(msg=msg)

    def first_pick(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            if(len(cMsg) < 2):
                sendLobbyMessage("Please specify a side (Radiant, Dire)", msg.channel_id)
                return
            side = str(cMsg[1]).lower().strip()
            if(edit_distance.distance(side, 'radiant') < 4):
                d['cm_pick'] = dota2.enums.DOTA_CM_PICK.DOTA_CM_GOOD_GUYS
                side = "Radiant"
            elif(edit_distance.distance(side, 'dire') < 4):
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

    def reset_ready(*args, **kwargs):
        sides_ready[0] = False
        sides_ready[1] = False
        if ('msg' in kwargs):
            msg = kwargs['msg']
            sendLobbyMessage("Reset ready status.", msg.channel_id)


    def botCleanup():
        botLog("shutting down")
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
                            classes.leagueLobbyCommands.START : start_lobby, classes.leagueLobbyCommands.GAME_NAME : set_name,
                            classes.leagueLobbyCommands.GAME_PASS : set_pass}

    ##five minutes to get in a lobby
    toH = threading.Timer(300.0, timeoutHandler, [stop_event,])
    toH.start()

    client.cli_login(username=sBot.username, password=sBot.password)
    bot_SteamID = client.steam_id
    while(not stop_event.isSet()):
        client.sleep(5)
    client.disconnect()
    client.logout()
    factoryQ.put(classes.command(classes.botFactoryCommands.FREE_SLAVE, [sBot]))
    return

if(__name__ == "__main__"):
    sBot = classes.steamBotInfo(keys.SLAVEBOTNAMES[0], keys.SLAVEUSERNAMES[0], keys.SLAVEPASSWORDS[0], keys.SLAVEBOTSTEAMLINKS[0])
    kstQ = queue.Queue()
    dstQ = queue.Queue()
    factoryQ = queue.Queue()
    client = steamSlave(sBot, kstQ, dstQ, factoryQ, ["test", "test", None])
