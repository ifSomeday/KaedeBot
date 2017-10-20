import gevent.monkey
import sys
if(sys.platform.startswith('linux')):
    gevent.monkey.patch_all()

from plugins import opendota
from plugins import dotaStats
from steam import WebAPI
import header
import pickle
import keys
import pickle
import discord
import asyncio
import classes
import os

api = WebAPI(keys.STEAM_WEBAPI)
od = opendota.openDotaPlugin()
PICKLE_LOCATION = os.getcwd() + "/dataStores/lastLeagueMatch.pickle"

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("MatchResult: " +  str(text), flush = True)
    except:
        print("MatchResult: Logging error. Probably some retard name", flush = True)


async def match_results(client):
    lastMatches = load_last_match()
    for i in range(0, len(header.LEAGUE_IDS)):
        if(i >= len(lastMatches)):
            lastMatches.append(0)
        matches = api.IDOTA2Match_570.GetMatchHistory(league_id=header.LEAGUE_IDS[i])["result"]
        for match in matches['matches']:
            if(match['match_id'] > lastMatches[i]):
                ##TODO: verify processing, then move lastMatch update after success
                lastMatches[i] = match['match_id']
                botLog("parsing: " + str(match['match_id']))
                success, emb = process_match(match)
                if(sys.platform.startswith('linux')):
                    await client.send_message(client.get_channel('325108273751523328'), " ", embed = emb)
    save_last_match(lastMatches)

def process_match(match):
    emb = discord.Embed()
    emb.type = "rich"

    match_det = api.IDOTA2Match_570.GetMatchDetails(match_id=match['match_id'])["result"]
    od_match = od.get_match(match['match_id'])

    radiant_name = match_det['radiant_name'] if ("radiant_name" in match_det) else "Radiant"
    dire_name = match_det['dire_name'] if ("dire_name" in match_det) else "Dire"
    emb.title = radiant_name.strip() + " vs " + dire_name.strip()

    winning_url = None
    ##field_name = 'radiant_logo' if match_det['radiant_win'] else 'dire_logo'
    ##if(field_name in match_det):
        ##winning_url = get_team_logo(match_det[field_name])
        ##if(not 'status' in winning_url):
            ##emb.set_thumbnail(url = winning_url['data']['url'])
            ##pass
    ##TODO: https://www.opendota.com/matches/3070176477
    emb.set_thumbnail(url="https://seal.gg/assets/seal.png")
    emb.description = "**" + (radiant_name if match_det['radiant_win'] else dire_name) + "** Victory!\nMatch ID: " +  str(match['match_id'])
    emb.add_field(name="Match Details", value=dotaStats.quick_game_details(od_match), inline=False)

    rad_str = ""
    dire_str = ""
    for player in od_match["players"]:
        tmp = dotaStats.quick_player_info(player) + "\t\n\n"
        if(player["player_slot"] in range(0, 5)):
            rad_str += tmp
        elif(player["player_slot"] in range(128, 133)):
            dire_str += tmp

    emb.add_field(name=radiant_name, value=rad_str, inline=True)
    emb.add_field(name=dire_name, value=dire_str, inline=True)

    col = discord.Colour.default()
    col.value = 73 << 16 | 122 << 8 | 129 ##seal logo light
    emb.colour = col

    return(True, emb)

def get_team_logo(ugc):
    return(api.ISteamRemoteStorage.GetUGCFileDetails(appid=570, ugcid=ugc))

def team_info(team_id):
    return(api.IDOTA2Match_570.GetTeamInfoByTeamID(start_at_team_id=team_id, teams_requested=1)['result']['teams'][0])


def save_last_match(matches):
    with open(PICKLE_LOCATION, "wb")as f:
        botLog(matches)
        pickle.dump(matches, f)

def load_last_match():
    if(os.path.isfile(PICKLE_LOCATION)):
        with open(PICKLE_LOCATION, 'rb') as f:
            return(pickle.load(f))
    else:
        tmp = [3504724775, 3504724775]##[0 for x in range(0, len(header.LEAGUE_IDS))]
        save_last_match(tmp)
        return(tmp)
