'''
My daddy told me never make a method longer than your screen
looks like i fucked that right up
'''

##library imports
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

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
import logging
import time
import re
import os
import pickle
from threading import Thread
##need STEAM_USERNAME and STEAM_PASS in keys.py
import keys
import classes

def dotaThread():
    ##set up client
    client = SteamClient()
    dota = Dota2Client(client)

    debug = False

    TABLE_NAME = os.getcwd() + "/ratings.pickle"
    table = {}

    r_pattern = re.compile('"(.*?)"')

    me = SteamID(75419738)

    ##DECORATED FUNCTIONS

    logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

    ##after logon, launch dota
    @client.on('logged_on')
    def start_dota():
        dota.launch()
        pass

    ##At this point dota is ready
    @dota.on('ready')
    def ready0():
        print("Dota is ready")

    @dota.on('notready')
    def reload():
        print("starting dota")
        dota.exit()
        dota.launch()
        pass

    @client.on('disconnected')
    def restart():
        client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)

    ##dota lobby on lobby change event handler
    @dota.on('lobby_changed')
    def fix_self(msg):
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
        print(msg)
        dota.channels.leave_channel("Lobby_%s" % msg.lobby_id)
        ##state 3 is postgame
        ##game_state
        if(msg.game_state == dGState.DOTA_GAMERULES_STATE_POST_GAME):
            winner = msg.match_outcome
            if(winner == dOutcome.RadVictory):
                print("radiant wins!")
            elif(winner == dOutcome.DireVictory):
                print("dire wins!")
            else:
                print("lobby died")
                return
            direCount = 0
            radiantCount = 0
            direAverage  = 0
            radiantAverage = 0
            for member in msg.members:
                print(member.name)
                print(member.team)
                print(member.id)
                if not member.id in table:
                    table[member.id] = classes.leaguePlayer()
                    table[member.id].account_id = member.id
                if(member.team == 0):
                    radiantCount +=1
                    radiantAverage += table[member.id].mmr
                if(member.team == 1):
                    direCount +=1
                    direAverage += table[member.id].mmr
            radiantAverage = (radiantAverage + 1400*(5-radiantCount))/5
            direAverage = (direAverage + 1400*(5-direCount))/5
            print(radiantAverage)
            print(direAverage)
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
                    print("member not updatesd")
                table[member.id].printStats()
            dumpTable(table)



    ##party invite event handler
    @dota.on('party_invite')
    def party_invite(msg):
        if(dota.party == None):
            print(msg)
            dota.respond_to_party_invite(msg.group_id, accept=True)

    ##lobby invite event handler
    @dota.on('lobby_invite')
    def lobby_invite(msg):
        if(dota.lobby == None):
            print(msg)
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
        print(msg.body.steamid_from)
        if(not str(msg.body.steamid_from) == str(76561198035685466) or not str(msg.body.steamid_from) == str(76561198060607123)):
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
                else:
                    client.get_user(SteamID(msg.body.steamid_from)).send_message("i only respond to my master :O")
            return
        elif(len(chat_quick_decode(msg)) > 0):
            if(chat_quick_decode(msg).lower() == "lobby"):
                setup_lobby()
                client.get_user(SteamID(msg.body.steamid_from)).send_message("setting up lobby")
            elif(chat_quick_decode(msg).lower() == "invite"):
                party_invite_me(msg.body.steamid_from)
                client.get_user(SteamID(msg.body.steamid_from)).send_message("inviting to party")
            elif(chat_quick_decode(msg).lower() == "linvite"):
                lobby_invite_me(msg.body.steamid_from)
                client.get_user(SteamID(msg.body.steamid_from)).send_message("inviting to lobby")
            elif(chat_quick_decode(msg).lower() == "lleave"):
                leave_lobby()
                client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving lobby")
            elif(chat_quick_decode(msg).lower() == "leave"):
                leave_party()
                client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving party")
            elif(chat_quick_decode(msg).lower() == "tleave"):
                leave_team_lobby()
                client.get_user(SteamID(msg.body.steamid_from)).send_message("leaving team")
            elif(chat_quick_decode(msg).lower() == "launch"):
                launch_lobby()
                client.get_user(SteamID(msg.body.steamid_from)).send_message("launching lobby")
            elif(chat_quick_decode(msg).lower() == 'die'):
                exit()
            elif(chat_quick_decode(msg).lower().startswith('inhouse')):
                command = chat_quick_decode(msg)[len('inhouse')+1:]
                params = r_pattern.findall(command)
                if(len(params) == 0):
                    client.get_user(SteamID(msg.body.steamid_from)).send_message("please put quotes around the lobby name and password")
                else:
                    lobbies = get_lobbies(server_region=1, game_mode = 0).lobbies
                    for lobby in lobbies:
                        #print(lobby)
                        try:
                            #print(lobby.name)
                            pass
                        except:
                            #print("unprintable name")
                            pass
                        if lobby.name == params[0]:
                            print(lobby)
            elif(chat_quick_decode(msg).lower() == 'test'):
                print(dota.lobby)
            else:
                client.get_user(SteamID(msg.body.steamid_from)).send_message(chat_quick_decode(msg).lower())

        else:
            ##just someone typing
            pass

    @client.on('friend_invite')
    def accept_request(msg):
        print(msg)


    ##GC RELATED COMMANDS

    ##sets up and issues the create lobby command
    def _lobby_setup_backend():
        print("setting up lobby")
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
    def leave_lobby():
        ##check if in lobby
        dota.leave_practice_lobby()

    ##leaves current party
    def leave_party():
        ##check if in party
        dota.leave_party()

    ##make sure to use resp.lobbies
    def get_lobbies(game_mode=0, server_region = 0):
        jobid = dota.send_job(dGCMsg.EMsgGCLobbyList, {'game_mode' : game_mode, 'server_region' : server_region})
        resp = dota.wait_msg(jobid, timeout=10)
        return(resp)

    ##invite to party by ID
    ##automagically converts to a SteamID object
    def party_invite_me(idd):
        dota.invite_to_party(SteamID(idd))
        pass

    ##invite to lobby by ID
    ##automagically converts to a SteamID object
    def lobby_invite_me(idd):
        dota.invite_to_lobby(SteamID(idd))
        leave_team_lobby()
        pass

    ##enters the "unassigned" section in lobby
    def leave_team_lobby():
        dota.join_practice_lobby_team(team=4)
        pass

    ##general lobby setup
    def setup_lobby():
        _lobby_setup_backend()
        pass

    ##launchs current lobby
    def launch_lobby():
        dota.launch_practice_lobby()
        ##add invites
        pass

    ##0 is good, anything else is bad
    def get_session_status():
        return(dota.connection_status)

    ##HELPER FUNCTIONS

    ##a quick decode macro for friend message protobuf
    def chat_quick_decode(string):
        return(string.body.message.decode("utf-8").rstrip('\x00'))

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
            print("previous table found... opening")

        else:
            print("no local table.... generating one")
            dumpTable({})
            print("local table created")
        return(openTable())

    table = init_local_data()

    print(table)

    client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)
    print("logged in")
    client.run_forever()


pbThread = Thread(target = dotaThread)
pbThread.start()
pbThread.join()
#login client. make sure to populate keys.py properly


##remove this if not running as a standalone bot
