##TODO: fix imports

##library imports
import gevent.monkey

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


##general imports
import operator
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

def dotaThread(kstQ, dscQ):
    ##set up client
    client = SteamClient()
    dota = Dota2Client(client)

    debug = False

    TABLE_NAME = os.getcwd() + "/dataStores/ratings.pickle"
    table = {}

    r_pattern = re.compile('"(.*?)"')

    ##TODO programatically generate this
    bot_SteamID = SteamID(76561198384957078)
    me = SteamID(75419738)

    if(debug):
        logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

    ##TODO: move elsewhere
    chat_command_translation = {"lobby" : classes.steamCommands.LOBBY_CREATE, "invite" : classes.steamCommands.PARTY_INVITE,
    "linvite" : classes.steamCommands.LOBBY_INVITE, "lleave" : classes.steamCommands.LEAVE_LOBBY,
    "leave" : classes.steamCommands.LEAVE_PARTY, "tleave" : classes.steamCommands.LEAVE_TEAM,
    "die" : classes.steamCommands.STOP_BOT, "leaderboard" : classes.steamCommands.LEADERBOARD,
    "launch" : classes.steamCommands.LAUNCH_LOBBY, "status" : classes.steamCommands.STATUS,
    "inhouse" : classes.steamCommands.INHOUSE}

    ##DECORATED FUNCTIONS

    ##after logon, launch dota
    @client.on('logged_on')
    def start_dota():
        print("Logged into steam, starting dota", flush=True)
        dota.launch()
        pass

    ##At this point dota is ready
    @dota.on('ready')
    def ready0():
        print("Dota is ready", flush=True)

    @dota.on('notready')
    def reload():
        print("out of dota, restarting...", flush=True)
        dota.exit()
        dota.launch()
        pass

    @client.on('disconnected')
    def restart():
        print("disconnected from steam. Attempting to relog...", flush=True)
        client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)

    ##dota lobby on lobby change event handler
    @dota.on('lobby_changed')
    def lobby_change_handler(msg):
        lobby_stat, party_stat = get_status()
        if(not lobby_stat == None):
            if(len(lobby_stat.members) <= 1 and not lobby_stat.leader_id == bot_SteamID.as_64):
                print("Lobby is dead, leaving",flush = True)
                leave_lobby()
        pass

    @dota.on('party_changed')
    def party_change_handler(msg):
        lobby_stat, party_stat = get_status()
        if(not party_stat == None):
            if(len(party_stat.members) <= 1):
                print("lobby is dead, leaving",flush = True)
                leave_party()
        pass
    #   leave_team_lobby()

    ##dota lobby shared object create event handler
    @dota.socache.on(('new', dEType.CSODOTALobby))
    def got_a_new_item(obj):
        #dota.channels.join_channel("Lobby_%s" % dota.lobby.lobby_id,channel_type=3)
        #leave_team_lobby()
        pass
        #print(obj)

    ##dota lobby shared object multiple update event handler
    @dota.socache.on(('updated', dEType.CSODOTALobby))
    def got_status_update(obj):
        ##match_outcome = obj.match_outcome
        pass
        #print(obj)

    @dota.on('lobby_new')
    def on_lobby_joined(msg):
        leave_team_lobby()
        dota.channels.join_channel("Lobby_%s" % msg.lobby_id,channel_type=3)

    ##lobby removed event handler
    @dota.on('lobby_removed')
    def lobby_removed(msg):
        print(msg, flush=True)
        dota.channels.leave_channel("Lobby_%s" % msg.lobby_id)
        ##state 3 is postgame
        ##game_state
        if(msg.game_state == dGState.DOTA_GAMERULES_STATE_POST_GAME):
            winner = msg.match_outcome
            if(winner == dOutcome.RadVictory):
                print("radiant wins!", flush=True)
            elif(winner == dOutcome.DireVictory):
                print("dire wins!", flush=True)
            else:
                print("lobby died", flush=True)
                return
            direCount = 0
            radiantCount = 0
            direAverage  = 0
            radiantAverage = 0
            for member in msg.members:
                try:
                    print(member.name, flush=True)
                except:
                    print("cant encode name")
                print(member.team, flush=True)
                print(member.id, flush=True)
                if not member.id in table:
                    table[member.id] = steamBot.classes.leaguePlayer()
                    table[member.id].account_id = member.id
                if(member.team == 0):
                    radiantCount +=1
                    radiantAverage += table[member.id].mmr
                if(member.team == 1):
                    direCount +=1
                    direAverage += table[member.id].mmr
            radiantAverage = (radiantAverage + 1400*(5-radiantCount))/5
            direAverage = (direAverage + 1400*(5-direCount))/5
            print(radiantAverage, flush=True)
            print(direAverage, flush=True)
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
                    print("member not updatesd", flush=True)
                table[member.id].printStats()
            dumpTable(table)



    ##party invite event handler
    @dota.on('party_invite')
    def party_invite(msg):
        if(dota.party == None):
            print(msg, flush=True)
            dota.respond_to_party_invite(msg.group_id, accept=True)

    ##lobby invite event handler
    @dota.on('lobby_invite')
    def lobby_invite(msg):
        if(dota.lobby == None):
            print(msg, flush=True)
            dota.respond_lobby_invite(msg.group_id, accept=True)

    @client.friends.on('friend_invite')
    def friend_invite(msg):
        client.friends.add(msg)

    @dota.on(dGCMsg.EMsgGCLobbyListResponse)
    def test6(msg):
        #print(msg)
        pass

    ##control bot from steam messages. soon to be removed (excpet probably tleave)
    @client.on(EMsg.ClientFriendMsgIncoming)
    def i_got_a_message(msg):
        ##TODO determine what commands should need priviledge, seperate out those that dont, to avoid current cude duplication
        if(not str(msg.body.steamid_from) == str(76561198035685466) and not str(msg.body.steamid_from) == str(76561198060607123)):
            if(len(chat_quick_decode(msg)) > 0):
                if(chat_quick_decode(msg).lower() == "lleave"):
                    leave_lobby()
                    client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving lobby")
                elif(chat_quick_decode(msg).lower() == "tleave"):
                    leave_team_lobby()
                    client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving team")
                elif(chat_quick_decode(msg).lower() == "leave"):
                        leave_party()
                        client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving party")
                elif(chat_quick_decode(msg).lower() == 'status'):
                        send_status(msg.body.steamid_from)
                elif(chat_quick_decode(msg).lower().startswith('leaderboard')):
                    send_top_players(msg.body.steamid_from, chat_quick_decode(msg)[len("leaderboard")+1:])
                else:
                    client.get_user(SteamID(msg.body.steamid_from)).send_message("i only respond to my master :O")
            return
        elif(len(chat_quick_decode(msg)) > 0):
            #TODO: split on space, so args can be passed to commands
            cMsg = chat_quick_decode(msg).lower().split()
            command = chat_command_translation[cMsg[0]] if cMsg[0] in chat_command_translation else classes.steamCommands.INVALID_COMMAND
            function_translation[command](cMsg, msg = msg)

        else:
            ##just someone typing
            pass

    @client.on('friend_invite')
    def accept_request(msg):
        print(msg, flush=True)


    ##GC RELATED COMMANDS

    ##sets up and issues the create lobby command
    def _lobby_setup_backend():
        print("setting up lobby", flush=True)
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
            print("missing context from party_invite_me")
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
            print("missing context from lobby_invite_me")
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
        _lobby_setup_backend()
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("setting up lobby")
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
        print(spots)
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




    def invalid_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            client.get_user(SteamID(msg.body.steamid_from)).send_message("unknown command")

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
            print("previous ranking table found... opening", flush=True)

        else:
            print("no local ranking table.... generating one", flush=True)
            dumpTable({})
            print("local ranking table created", flush=True)
        return(openTable())

    table = init_local_data()

    function_translation = {classes.steamCommands.LEAVE_LOBBY : leave_lobby, classes.steamCommands.LEAVE_TEAM : leave_team_lobby,
        classes.steamCommands.LEAVE_PARTY : leave_party, classes.steamCommands.STATUS : send_status,
        classes.steamCommands.LEADERBOARD : send_top_players, classes.steamCommands.PARTY_INVITE : party_invite_me,
        classes.steamCommands.LOBBY_INVITE : lobby_invite_me, classes.steamCommands.LAUNCH_LOBBY : launch_lobby,
        classes.steamCommands.STOP_BOT : exit_dota, classes.steamCommands.INHOUSE : None,
        classes.steamCommands.STATUS_4D : get_status_discord, classes.steamCommands.LEADERBOARD_4D : get_leaderboard_discord,
        classes.steamCommands.LOBBY_CREATE : setup_lobby , classes.steamCommands.TOURNAMENT_LOBBY_CREATE : None,
        classes.steamCommands.INVALID_COMMAND : invalid_command}

    def messageHandler(*args, **kwargs):
        kstQ = args[0]
        dscQ = args[1]

        cmd = kstQ.get()
        if(cmd):
            print("found steam command", flush=True)
            function_translation[cmd.command](cmd = cmd)

        msgH = threading.Timer(1.0, messageHandler, [kstQ, dscQ])
        msgH.start()

    msgH = threading.Timer(1.0, messageHandler, [kstQ, dscQ])
    msgH.start()

    client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)
    print("logged in", flush=True)


    client.run_forever()