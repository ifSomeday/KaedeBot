##TODO: fix imports

##library imports
import gevent.monkey
##gevent.monkey.patch_all()

from steam import SteamClient
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
from dota2.enums import GCConnectionStatus as dConStat


##general imports
import operator
import queue
import logging
import time
import sys
import re
import os
import pickle
import threading
##need STEAM_USERNAME and STEAM_PASS in keys.py
import keys
import classes
import ksteamSlave
import header

def dotaThread(kstQ, dscQ, factoryQ):
    ##set up client
    client = SteamClient()
    dota = Dota2Client(client)

    stop_event = threading.Event()

    ##flags
    debug = False
    broadcast_game = False

    ##counters
    broadcast_counter = 0

    ##table info
    TABLE_NAME = os.getcwd() + "/dataStores/ratings.pickle"
    table = {}

    ##arg decoding
    r_pattern = re.compile('"(.*?)"')

    ##TODO programatically generate this
    bot_SteamID = SteamID(76561198384957078)
    kyouko_toshino = SteamID(75419738)

    ##enable debug
    if(debug):
        logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

    ##TODO: move elsewhere
    chat_command_translation = {"lobby" : classes.steamCommands.LOBBY_CREATE, "invite" : classes.steamCommands.PARTY_INVITE,
        "linvite" : classes.steamCommands.LOBBY_INVITE, "lleave" : classes.steamCommands.LEAVE_LOBBY,
        "leave" : classes.steamCommands.LEAVE_PARTY, "tleave" : classes.steamCommands.LEAVE_TEAM,
        "die" : classes.steamCommands.STOP_BOT, "leaderboard" : classes.steamCommands.LEADERBOARD,
        "launch" : classes.steamCommands.LAUNCH_LOBBY, "status" : classes.steamCommands.STATUS,
        "inhouse" : classes.steamCommands.INHOUSE, "givebot" : classes.steamCommands.REQUEST_LOBBY_BOT,
        "requestbot" : classes.steamCommands.REQUEST_LOBBY_BOT_FLAME}

    chat_lobby_command_translation = {"broadcast" : classes.lobbyCommands.BROADCAST}

    ##DECORATED FUNCTIONS

    def botLog(text):
        try:
            print("KaedeBot: " +  str(text), flush = True)
        except:
            print("KaedeBot: Logging error. Probably some retard name", flush = True)

    ##after logon, launch dota
    @client.on('logged_on')
    def start_dota():
        botLog("Logged into steam, starting dota")
        time.sleep(1)
        if(dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            botLog("Already in logon queue...")
            return
        if(not dota.connection_status is dConStat.HAVE_SESSION):
            dota.launch()

    ##At this point dota is ready
    @dota.on('ready')
    def ready0():
        botLog("Connection status:")
        botLog(dota.connection_status)
        botLog("Dota is ready")

    @dota.on('notready')
    def reload():
        #botLog("out of dota, restarting...")
        botLog("Connection status:")
        botLog(dota.connection_status)
        time.sleep(15)
        if(dota.connection_status is dConStat.NO_SESSION_IN_LOGON_QUEUE):
            botLog("Already in logon queue...")
            return
        if(not dota.connection_status is dConStat.HAVE_SESSION):
            dota.exit()
            dota.launch()

    @client.on('disconnected')
    def restart():
        botLog("disconnected from steam. Attempting to relog...")
        client.reconnect()

    ##dota lobby on lobby change event handler
    @dota.on('lobby_changed')
    def lobby_change_handler(msg):
        lobby_stat, party_stat = get_status()
        if(not lobby_stat == None):
            if(len(lobby_stat.members) <= 1 and not lobby_stat.leader_id == bot_SteamID.as_64):
                botLog("Lobby is dead, leaving")
                leave_lobby()
        pass

    @dota.on(dGCMsg.EMsgGCChatMessage)
    def lobby_message_handler(msg):
        if(len(msg.text) > 0):
            cMsg = msg.text.split()
            if(cMsg[0].startswith("!")):
                cMsg[0] = cMsg[0][1:]
            command = chat_lobby_command_translation[cMsg[0]] if cMsg[0] in chat_lobby_command_translation else classes.lobbyCommands.INVALID_COMMAND
            lobby_function_translation[command](cMsg, msg = msg)


    @dota.on('party_changed')
    def party_change_handler(msg):
        lobby_stat, party_stat = get_status()
        if(not party_stat == None):
            if(len(party_stat.members) <= 1):
                botLog("lobby is dead, leaving")
                leave_party()
        pass
    #   leave_team_lobby()

    @dota.on('lobby_new')
    def on_lobby_joined(msg):
        leave_team_lobby()
        broadcast_game = False
        dota.channels.join_channel("Lobby_%s" % msg.lobby_id,channel_type=3)

    ##lobby removed event handler
    @dota.on('lobby_removed')
    def lobby_removed(msg):
        broadcast_game = False
        botLog(msg)
        dota.channels.leave_channel("Lobby_%s" % msg.lobby_id)
        ##state 3 is postgame
        ##game_state
        if(msg.game_state == dGState.DOTA_GAMERULES_STATE_POST_GAME):
            with open(os.os.getcwd() + "/" + str(msg.match_id) + ".txt", "w") as f:
                f.write(msg) 
            winner = msg.match_outcome
            if(winner == dOutcome.RadVictory):
                botLog("radiant wins!")
            elif(winner == dOutcome.DireVictory):
                botLog("dire wins!")
            else:
                botLog("lobby died")
                return
            direCount = 0
            radiantCount = 0
            direAverage  = 0
            radiantAverage = 0
            for member in msg.members:
                try:
                    botLog(member.name)
                except:
                    botLog("cant encode name")
                botLog(member.team)
                botLog(member.id)
                if not member.id in table:
                    table[member.id] = classes.steamBot.leaguePlayer()
                    table[member.id].account_id = member.id
                if(member.team == 0):
                    radiantCount +=1
                    radiantAverage += table[member.id].mmr
                if(member.team == 1):
                    direCount +=1
                    direAverage += table[member.id].mmr
            radiantAverage = (radiantAverage + 1400*(5-radiantCount))/5
            direAverage = (direAverage + 1400*(5-direCount))/5
            botLog(radiantAverage)
            botLog(direAverage)
            for member in msg.members:
                table[member.id].account_name = member.name
                ##TODO fancy bitwise stuff here
                if(winner == dOutcome.RadVictory):
                    if(str(member.team) == '0'):
                        table[member.id].new_mmr(direAverage, 1)
                    elif(str(member.team) == '1'):
                        table[member.id].new_mmr(radiantAverage, 0)
                elif(winner == dOutcome.DireVictory):
                    if(member.team == 0):
                        table[member.id].new_mmr(direAverage, 0)
                    elif(member.team == 1):
                        table[member.id].new_mmr(radiantAverage, 1)
                else:
                    botLog("member not updatesd")
                table[member.id].printStats()
            dumpTable(table)



    ##party invite event handler
    @dota.on('party_invite')
    def party_invite(msg):
        if(dota.party == None):
            botLog(msg)
            dota.respond_to_party_invite(msg.group_id, accept=True)

    ##lobby invite event handler
    @dota.on('lobby_invite')
    def lobby_invite(msg):
        if(dota.lobby == None):
            botLog("joining lobby")
            dota.respond_lobby_invite(msg.group_id, accept=True)

    @client.friends.on('friend_invite')
    def friend_invite(msg):
        client.friends.add(msg)

    @dota.on(dGCMsg.EMsgGCLobbyListResponse)
    def test6(msg):
        #botLog(msg)
        pass

    ##control bot from steam messages. soon to be removed (excpet probably tleave)
    @client.on(EMsg.ClientFriendMsgIncoming)
    def steam_message_handler(msg):
        if(len(chat_quick_decode(msg)) > 0):
            cMsg = chat_quick_decode(msg).lower().split()
            if(cMsg[0].startswith("!")):
                cMsg[0] = cMsg[0][1:]
            command = chat_command_translation[cMsg[0]] if cMsg[0] in chat_command_translation else classes.steamCommands.INVALID_COMMAND
            function_translation[command](cMsg, msg = msg)
        else:
            ##just someone typing
            pass

    @client.on('friend_invite')
    def accept_request(msg):
        botLog(msg)

    ##GC RELATED COMMANDS

    ##sets up and issues the create lobby command
    def _lobby_setup_backend():
        botLog("setting up lobby")
        d = {}
        d['game_name'] = "Kaede Lobby"
        d['server_region'] = 2
        d['allow_cheats'] = False
        d['visibility'] = 0
        d['cm_pick'] = 1
        d['allow_spectating'] = True
        ##for debug
        d['fill_with_bots'] = True
        d['allow_cheats'] = True
        ##end debug
        dota.create_practice_lobby(password="word", options=d)
        time.sleep(1)
        dota.join_practice_lobby_team(team=4)
        pass

    ##leaves current lobby
    def leave_lobby(*args, **kwargs):
        ##check if in lobby
        dota.leave_practice_lobby()
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving lobby")

    ##leaves current party
    def leave_party(*args, **kwargs):
        ##check if in party
        dota.leave_party()
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving party")

    ##make sure to use resp.lobbies
    def get_lobbies(game_mode=0, server_region = 0):
        jobid = dota.send_job(dGCMsg.EMsgGCLobbyList, {'game_mode' : game_mode, 'server_region' : server_region})
        resp = dota.wait_msg(jobid, timeout=10)
        return(resp)

    ##invite to party by ID
    ##automagically converts to a SteamID object
    def party_invite_me(*args, **kwargs):
        ##TODO verify that party invites will never be automagically rescinded
        if(not "msg" in kwargs):
            botLog("missing context from party_invite_me")
            return
        msg = kwargs["msg"]
        idd = msg.body.steamid_from
        dota.invite_to_party(SteamID(idd))
        client.get_user(SteamID(msg.body.steamid_from)).send_message("inviting to party")
        pass

    ##invite to lobby by ID
    ##automagically converts to a SteamID object
    def lobby_invite_me(*args, **kwargs):
        if(not "msg" in kwargs):
            botLog("missing context from lobby_invite_me")
            return
        msg = kwargs["msg"]
        idd = msg.body.steamid_from
        dota.invite_to_lobby(SteamID(idd))
        client.get_user(SteamID(idd)).send_message("inviting to lobby")
        leave_team_lobby()
        pass

    ##enters the "unassigned" section in lobby
    def leave_team_lobby(*args, **kwargs):
        dota.join_practice_lobby_team(team=4)
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving team")
        pass

    ##general lobby setup
    def setup_lobby(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(msg.body.steamid_from == kyouko_toshino.as_64):
                client.get_user(SteamID(msg.body.steamid_from)).send_message("setting up lobby")
                _lobby_setup_backend()
        pass

    ##launchs current lobby
    def launch_lobby(*args, **kwargs):
        dota.launch_practice_lobby()
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("launching lobby")
        ##add invites
        pass

    def exit_dota(*args, **kwargs):
        msg = kwargs['msg']
        if(msg.body.steamid_from == kyouko_toshino.as_64):
            exit()

    ##0 is good, anything else is bad
    def get_session_status():
        return(dota.connection_status)

    def get_status():
        lobby = dota.lobby
        party = dota.party
        return lobby, party

    def send_status(*args, **kwargs):
        msg = kwargs['msg']
        id = msg.body.steamid_from
        requester = client.get_user(SteamID(id))
        lobby_stat, party_stat = get_status()
        requester.send_message("Party: " + str("None" if party_stat == None else "Active"))
            ##TODO parse and send party info
        requester.send_message("Lobby: " + str("None" if lobby_stat == None else "Active"))
            ##TODO parse and send lobby info

    ##TODO: combine these two based on whther or not kwargs is msg or cmd
    def send_top_players(*args, **kwargs):
        msg = kwargs['msg']
        id = msg.body.steamid_from
        spots = chat_quick_decode(msg)[len("leaderboard")+1:].strip()
        requester = client.get_user(SteamID(id))
        top = get_top_players(spots)
        reply = "Top " + str(len(top)) + " players:"
        for player in top:
            reply += "\n" + str(player.account_name) +": " + str(player.mmr)
        requester.send_message(reply)

    def get_leaderboard_discord(*args, **kwargs):
        cmd = kwargs['cmd']
        channel = cmd.args[0]
        spots = cmd.args[1].strip()
        botLog(spots)
        top = get_top_players(spots)
        resp = "Top " + str(len(top)) + " players:"
        for player in top:
            resp += "\n" + str(player.account_name) +": " + str(player.mmr)
        dscQ.put(classes.command(classes.discordCommands.BROADCAST, [cmd.args[0], resp]))

    def get_status_discord(*args, **kwargs):
        cmd = kwargs['cmd']
        lobby, party = get_status()
        resp = "Party: " + str("None" if party == None else "Active") + "\n"
        resp += "Lobby: " + str("None" if lobby == None else "Active") + "\n"
        dscQ.put(classes.command(classes.discordCommands.BROADCAST, [cmd.args[0], resp]))

    def set_lobby_broadcast(*args, **kwargs):
        msg = kwargs['msg']
        dscQ.put(classes.command(classes.discordCommands.BROADCAST_LOBBY, [dota.lobby, msg]))

    def invalid_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("unknown command")

    def spawn_bot_flame(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("Wow you can spell request !!")
            cMsg = args[0]
            function_translation[classes.steamCommands.REQUEST_LOBBY_BOT](cMsg, msg = msg)

    def naw(*args, **kwargs):
        pass

    ##HELPER FUNCTIONS

    ##a quick decode macro for friend message protobuf
    def chat_quick_decode(string):
        return(string.body.message.decode("utf-8").rstrip('\x00'))

    def get_top_players(spots=3):
        sorted_table = sorted(table.values(), key=operator.attrgetter('mmr'), reverse=True)
        top = []
        try:
            spots = int(spots)
        except:
            spots = 3
            pass
        if(spots < 0):
            spots = 3
        if(spots == 0):
            return(sorted_table)
        for i in range(0, min(spots, len(sorted_table))):
            top.append(sorted_table[i])
        return(top)

    def clean_shutoff(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            botLog("shutting down")
            stop_event.set()

    def dumpTable(table):
        with open(TABLE_NAME,'wb') as f:
            pickle.dump(table, f)

    ##table arg breaks for some reason
    def openTable():
        if os.path.getsize(TABLE_NAME) > 0:
            with open(TABLE_NAME,'rb') as f:
                return(pickle.load(f))
        else:
            return({})

    def init_local_data():
        if(os.path.isfile(TABLE_NAME)):
            botLog("previous ranking table found... opening")

        else:
            botLog("no local ranking table.... generating one")
            dumpTable({})
            botLog("local ranking table created")
        return(openTable())

    def messageHandler(*args, **kwargs):
        kstQ = args[0]
        dscQ = args[1]

        cmd = kstQ.get()
        broadcast_counter = 0
        if(cmd):
            botLog("found steam command")
            function_translation[cmd.command](cmd = cmd)
        if(broadcast_game):
            botLog(broadcast_counter)
            if(broadcast_counter == 0):
                dscQ.put(classes.command(classes.discordCommands.BROADCAST_LOBBY, [dota.lobby]))
            broadcast_counter = (broadcast_counter + 1) % 60

        msgH = threading.Timer(1.0, messageHandler, [kstQ, dscQ])
        msgH.start()

    function_translation = {classes.steamCommands.LEAVE_LOBBY : leave_lobby, classes.steamCommands.LEAVE_TEAM : leave_team_lobby,
        classes.steamCommands.LEAVE_PARTY : leave_party, classes.steamCommands.STATUS : send_status,
        classes.steamCommands.LEADERBOARD : send_top_players, classes.steamCommands.PARTY_INVITE : party_invite_me,
        classes.steamCommands.LOBBY_INVITE : lobby_invite_me, classes.steamCommands.LAUNCH_LOBBY : launch_lobby,
        classes.steamCommands.STOP_BOT : exit_dota, classes.steamCommands.INHOUSE : invalid_command,
        classes.steamCommands.STATUS_4D : get_status_discord, classes.steamCommands.LEADERBOARD_4D : get_leaderboard_discord,
        classes.steamCommands.LOBBY_CREATE : setup_lobby , classes.steamCommands.TOURNAMENT_LOBBY_CREATE : invalid_command,
        classes.steamCommands.INVALID_COMMAND : invalid_command, classes.steamCommands.REQUEST_LOBBY_BOT_FLAME : spawn_bot_flame,
        classes.steamCommands.SHUTDOWN_BOT : clean_shutoff}

    table = init_local_data()

    msgH = threading.Timer(1.0, messageHandler, [kstQ, dscQ])
    msgH.start()

    lobby_function_translation = {classes.lobbyCommands.INVALID_COMMAND : naw, classes.lobbyCommands.BROADCAST : set_lobby_broadcast}

    client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)
    botLog("logged in")
    while(not stop_event.isSet()):
        client.sleep(5)
    client.disconnect()
    client.logout()
    return
    #client.run_forever()

if(__name__ == "__main__"):
    kstQ = queue.Queue()
    dscQ = queue.Queue()
    factoryQ = queue.Queue()
    dotaThread(kstQ, dscQ, factoryQ)
