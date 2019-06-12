from steam import SteamClient
from steam import SteamID
from dota2 import Dota2Client
import dota2

import threading
import keys

from steam.enums.emsg import EMsg
from dota2.enums import EDOTAGCMsg as dGCMsg
from dota2.enums import ESOMsg as dEMsg
from dota2.enums import ESOType as dEType
from dota2.enums import DOTA_GameState as dGState
from dota2.enums import EMatchOutcome as dOutcome
from dota2.enums import GCConnectionStatus as dConStat
from dota2.enums import EGCBaseClientMsg as dGCbase

done = threading.Event()

match_lock = threading.Lock()

client = SteamClient()
dota = Dota2Client(client)

teamToScout = [76561197991626842, 76561198004570608, 76561198038931818, 76561198091038529, 76561198157285590, 76561198035657373]

teamToScout = [SteamID(x).as_32 for x in teamToScout]
print(teamToScout)

matches = []
matchIds = []
sharedMatches = []

def requestPlayerInfo(accid):
    
    print("requesting {0}".format(accid))

    jobId = dota.request_player_match_history(account_id=accid, matches_requested=10,
                                                request_id=accid, start_at_match_id=0, 
                                                include_practice_matches=True, 
                                                include_custom_games=True)

def parsePlayerInfo():
    print("parsing player info")
    for pMatchList in matches:
        for match in pMatchList:
            if(not match.match_id in matchIds):
                matchIds.append(match.match_id)
            elif(not match.match_id in sharedMatches):
                sharedMatches.append(match.match_id)
    
    print(sharedMatches)

    done.set()


def scout():
    for player in teamToScout:
        requestPlayerInfo(player)
    print("done retrieving player info")

    #print(matches)

    
    #parsePlayerInfo()


def dotaHistoryHandler(request, history):
    #print(history)
    #print(request)
    with match_lock:
        matches.append(history)
        if(len(matches) == len(teamToScout)):
            parsePlayerInfo()
    #print(matches)


def steamLogonHandler():
    print("logged on")

    dota.launch()


def dotaReadyHandler():
    print("dota is ready")

    client.sleep(5)

    scout()


##callbacks
client.on("logged_on", steamLogonHandler)
dota.on("ready", dotaReadyHandler)
dota.on("player_match_history", dotaHistoryHandler)


client.cli_login(username=keys.STEAM_USERNAME, password=keys.STEAM_PASSWORD)


while(not done.isSet()):
    client.sleep(1)

print("scouting done")