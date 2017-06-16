from gevent import monkey
monkey.patch_ssl()

from steam import SteamClient
from steam import WebAPI
from steam import SteamID
from dota2 import Dota2Client
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

import keys

def steamSlave(sBot, kstQ, dscQ):
    time.sleep(1)
    client = SteamClient()
    dota = Dota2Client(client)

    stop_event = threading.Event()

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
        lobby_stat = dota.lobby
        if(not lobby_stat == None):
            if(len(lobby_stat.members) <= 1 and not lobby_stat.leader_id == bot_SteamID.as_64):
                botLog("Lobby is dead, leaving")
                leave_lobby()

    #TODO: this shit is a fucking mess
    @dota.on('lobby_removed')
    def lobby_removed(msg):
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

            botCleanup()

    @client.on(EMsg.ClientFriendMsgIncoming)
    def steam_message_handler(msg):
        ##TODO: check you have permission to release
        msgT = msg.body.message.decode("utf-8").rstrip('\x00')
        if(len(msgT) > 0):
            if(msgT == "release"):
                botCleanup()

    @client.friends.on('friend_invite')
    def friend_invite(msg):
        client.friends.add(msg)

    @dota.on('lobby_invite')
    def lobby_invite(msg):
        if(dota.lobby == None):
            botLog("joining lobby")
            dota.respond_lobby_invite(msg.group_id, accept=True)

    def botCleanup():
        kstQ.put(classes.command(classes.steamCommands.FREE_BOT, [sBot]))
        stop_event.set()
        botLog("shutting down")

    def timeoutHandler(*args, **kwargs):
        evnt = args[0]
        if(dota.lobby == None):
            botLog("lobby not found")
            botCleanup()
        else:
            botLog("im in a lobby!")


    ##fifteen minutes to get in a lobby
    toH = threading.Timer(900.0, timeoutHandler, [stop_event,])
    toH.start()

    client.cli_login(username=sBot.username, password=sBot.password)
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
