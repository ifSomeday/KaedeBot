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
import threading
import classes
import os

api = WebAPI(keys.STEAM_WEBAPI)
od = opendota.openDotaPlugin()
PICKLE_LOCATION = os.getcwd() + "/dataStores/lastLeagueMatch.pickle"
fileLock = threading.Lock()

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("MatchResult: " +  str(text), flush = True)
    except:
        print("MatchResult: Logging error. Probably some retard name", flush = True)

async def match_results(client):
    leagues = load_leagues()
    ##curr_last_matches = [0 for i in range(len(lastMatches))]
    for league in leagues:
        for i in range(0, len(league.league_ids)):
            try:
                matches = api.IDOTA2Match_570.GetMatchHistory(league_id=header.LEAGUE_IDS[i])["result"]
                match_list = matches['matches']
            except:
                botLog("Steam API error, trying again later")
                return
            curr_last_match = league.last_matches[i]
            if(match_list is None):
                pass
            else:
                match_list.reverse()
                for match in match_list:
                    if(match['match_id'] > curr_last_match):
                        botLog("parsing: " + str(match['match_id']))
                        try:
                            emb = process_match(match, league)
                            league.last_matches[i] = max(league.last_matches[i], match['match_id'])
                            save_leagues(leagues)
                        except Exception as e:
                            botLog(e)
                            botLog("requesting parse for failed match " + str(match['match_id']))
                            od.request_parse(match['match_id'])
                            break ##should allow the rest of the tickets to process
                        if(not emb is None):
                            if(sys.platform.startswith('linux')):
                                ##DMDT:
                                ##await client.send_message(client.get_channel('325108273751523328'), "**===============**", embed = emb)
                                ##SEAL:
                                await client.send_message(client.get_channel('369398485113372675'), "**===============**", embed = emb)
                            else:
                                botLog("would be sending match " + str(match['match_id']))
        if(league.get_week_done()):
            await client.send_message(client.get_channel('369398485113372675'), league.output_results())
            await new_week(None, client=None, msg=None, cfg=None, internal=True)
    save_leagues(leagues)

async def force_match_process(*args, **kwargs):
    client = kwargs['client']
    cMsg = args[0]
    msg = kwargs['msg']
    cfg = kwargs['cfg']
    if(msg.author.server_permissions.manage_server or msg.author.id == '133811493778096128'):
        leagues = load_leagues()
        ##TODO: print specific leagues. for now we do all
        for league in leagues:
            output = league.output_results()
            if(not output == ""):
                await client.send_message(msg.channel, output)
            else:
                await client.send_message(msg.channel, "no results to output")
    else:
        client.add_reaction(msg, '❓')

async def new_week(*args, **kwargs):
    client = kwargs['client']
    cMsg = args[0]
    msg = kwargs['msg']
    cfg = kwargs['cfg']
    ##TODO: bug with internal
    botLog('internal' in kwargs)
    if('internal' in kwargs or msg.author.server_permissions.manage_server or msg.author.id == '133811493778096128'):
        leagues = load_leagues()
        ##TODO: reset specific leagues. for now we do all
        for league in leagues:
            league.new_week()
        save_leagues(leagues)
        if(not 'internal' in kwargs):
            await client.send_message(msg.channel, "League results reset for current week")
        else:
            botLog("reset week")
    else:
        client.add_reaction(msg, '❓')


def process_match(match, league):
    emb = discord.Embed()
    emb.type = "rich"

    match_det = api.IDOTA2Match_570.GetMatchDetails(match_id=match['match_id'])["result"]
    od_match = od.get_match(match['match_id'])

    radiant_name = match_det['radiant_name'] if ("radiant_name" in match_det) else "Radiant"
    dire_name = match_det['dire_name'] if ("dire_name" in match_det) else "Dire"
    emb.title = radiant_name.strip() + " vs " + dire_name.strip()

    ##TODO: https://www.opendota.com/matches/3070176477
    emb.set_thumbnail(url="https://seal.gg/assets/seal.png")
    emb.description = "**" + (radiant_name if match_det['radiant_win'] else dire_name) + "** Victory!\nMatch ID: " +  str(match['match_id'])
    emb.add_field(name="Match Details", value=dotaStats.quick_game_details(od_match), inline=False)

    rad_str = ""
    dire_str = ""
    leavers = 0
    for player in od_match["players"]:
        tmp = dotaStats.quick_player_info(player) + "\t\n\n"
        if(player["player_slot"] in range(0, 5)):
            leavers += player["leaver_status"]
            rad_str += tmp
        elif(player["player_slot"] in range(128, 133)):
            dire_str += tmp
            leavers += player["leaver_status"]

    if(leavers > 8):
        botLog("Greater than 8 leavers detected, ignoring match")
        botLog(match['match_id'])
        return(None)

    emb.add_field(name="{:30s}".format(radiant_name), value=rad_str, inline=True)
    emb.add_field(name="{:30s}".format(dire_name), value=dire_str, inline=True)

    col = discord.Colour.default()
    col.value = 73 << 16 | 122 << 8 | 129 ##seal logo light
    emb.colour = col

    radiant_team_id = match_det['radiant_team_id'] if ('radiant_team_id' in match_det) else 1
    dire_team_id = match_det['dire_team_id'] if ('dire_team_id' in match_det) else 2
    league.add_result([radiant_team_id, dire_team_id], [radiant_name, dire_name], 0 if match_det['radiant_win'] else 1)

    return(emb)

def get_team_logo(ugc):
    return(api.ISteamRemoteStorage.GetUGCFileDetails(appid=570, ugcid=ugc))

def team_info(team_id):
    return(api.IDOTA2Match_570.GetTeamInfoByTeamID(start_at_team_id=team_id, teams_requested=1)['result']['teams'][0])


def save_leagues(leagues):
    fileLock.acquire()
    try:
        with open(PICKLE_LOCATION, "wb")as f:
            pickle.dump(leagues, f)
    finally:
        fileLock.release()

def load_leagues():
    fileLock.acquire()
    leagueArray = None
    try:
        if(os.path.isfile(PICKLE_LOCATION)):
            with open(PICKLE_LOCATION, 'rb') as f:
                leagueArray = pickle.load(f)
        else:
            leagueArray = [classes.league(header.LEAGUE_IDS, 16, league_name="SEAL", last_match=3705569606)]
    finally:
        fileLock.release()
    return(leagueArray)

def init(chat_command_translation, function_translation):
    function_translation[classes.discordCommands.OUTPUT_LEAGUE_RESULTS] = force_match_process
    chat_command_translation["leagueresults"] = classes.discordCommands.OUTPUT_LEAGUE_RESULTS
    function_translation[classes.discordCommands.LEAGUE_NEW_WEEK] = new_week
    chat_command_translation["leaguenewweek"] = classes.discordCommands.LEAGUE_NEW_WEEK
    return(chat_command_translation, function_translation)
