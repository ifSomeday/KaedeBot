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
import asyncio

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

async def new_match_results(client):
    fileLock.acquire()
    leagues = __load_leagues_internal()

    res = True


    ##get lists of matches to process
    for league in leagues:
        res = await process_webapi_initial(league)
        if(not res):
            botLog("Stopping all WebAPI processing for this iteration.")
            break

    ## This also relies WebAPI, so skip if we failed earlier
    if(res):
        for league in leagues:
            res = await process_webapi_secondary(client, league)
            if(not res):
                botLog("Stopping secondary WebAPI processing for this iteration.")
                break

    for league in leagues:
        res = await process_opendota_match(client, league)
        if(not res):
            botLog("Stopping OpenDota processing for this iteration.")
            break

    for league in leagues:
        if(league.get_week_done()):
            if(sys.platform.startswith('linux')):
                botLog("Sending last message")
                ##await client.send_message(client.get_channel('369398485113372675'), league.output_results())
                pass
            else:
                await client.send_message(client.get_channel('321900902497779713'), league.output_results())
            league.new_week()
            botLog("week reset")

    __save_leagues_internal(leagues)

    fileLock.release()


##This function creates a list of all matches that need to be processed
async def process_webapi_initial(league):
    for i in range(0, len(league.league_ids)):
        try:
            matches = []
            matches = api.IDOTA2Match_570.GetMatchHistory(league_id=league.league_ids[i])["result"]
            match_list = matches['matches']
            await asyncio.sleep(0.3)
        except Exception as e:
            botLog("WebAPI error, trying again later: " + str(e))
            return(False)
        curr_last_match = league.last_matches[i]
        if(match_list is None):
            continue
        else:
            match_list.reverse()
            for match in match_list:
                if(match['match_id'] > curr_last_match):
                    league.awaiting_processing.append(match)
                    league.last_matches[i] = max(league.last_matches[i], match['match_id'])
    return(True)

##This function retreives a set of initial results and posts them
##It then stores the message so the opendota processing can update them
async def process_webapi_secondary(client, league):
    for i in range(len(league.awaiting_processing)):
        match = league.awaiting_processing[i]
        embed, match_det = create_min_embed(match)
        message = None
        await asyncio.sleep(0.3)
        if(embed is None):
            league.awaiting_processing[:] = [m for m in league.awaiting_processing if not m is None]
            return(False)
        try:
            if(sys.platform.startswith('linux')):
                botLog("Sending message")
                ##message = await client.send_message(client.get_channel('369398485113372675'), "**===============**", embed = embed)
                pass
            else:
                message = await client.send_message(client.get_channel('321900902497779713'), "**===============**", embed = embed)

            league.awaiting_opendota.append({"match" : match, "match_det" : match_det, "message" : message, "embed" : embed})
            botLog("Added match " + str(match_det["match_id"]))

            radiant_team_id = match_det['radiant_team_id'] if ('radiant_team_id' in match_det) else 1
            dire_team_id = match_det['dire_team_id'] if ('dire_team_id' in match_det) else 2

            league.add_result([radiant_team_id, dire_team_id], [match_det['radiant_name'] if ("radiant_name" in match_det) else "Radiant", match_det['dire_name'] if ("dire_name" in match_det) else "Dire"], 0 if match_det['radiant_win'] else 1)
            league.awaiting_processing[i] = None

        except Exception as e:
            botLog("Error sending/adding primary match info: " + str(e))

    league.awaiting_processing[:] = [m for m in league.awaiting_processing if not m is None]

    return(True)

async def process_opendota_match(client, league):
    for i in range(len(league.awaiting_opendota)):
        match_obj = league.awaiting_opendota[i]
        try:
            embed = process_match(match_obj["match_det"], match_obj["embed"])
        except Exception as e:
            botLog(str(e))
            botLog("Opendota API error, stopping all Opendota requests for current iteration and requesting a parse: " + str(match_obj["match"]["match_id"]))
            od.request_parse(match_obj["match_det"]['match_id'])
            continue
        if(embed is None):
            await client.delete_message(match_obj["message"])
        else:
            if(match_obj["message"] == None):
                botLog("FATAL: Match " + str(match_obj["match_det"]["match_id"]) + " has no valid mesage object\nRemoving from list")
            else:
                botLog("Editing message")
                ##message = await client.edit_message(match_obj['message'], "**===============**", embed = embed)
                await asyncio.sleep(0.3)
        league.awaiting_opendota[i] = None

    league.awaiting_opendota[:] = [m for m in league.awaiting_opendota if not m is None]

    return(True)

def create_min_embed(match):
    emb = discord.Embed()
    emb.type = "rich"

    try:
        match_det = api.IDOTA2Match_570.GetMatchDetails(match_id=match['match_id'])["result"]
        players = match_det["players"] ##We dont use this, but its a quick way to determine if the details are available
    except Exception as e:
        botLog("Unable to get WebAPI match details: " + str(e))
        return(None, None)

    radiant_name = match_det['radiant_name'] if ("radiant_name" in match_det) else "Radiant"
    dire_name = match_det['dire_name'] if ("dire_name" in match_det) else "Dire"

    emb.title = radiant_name.strip() + " vs " + dire_name.strip()
    emb.set_thumbnail(url="https://seal.gg/assets/seal.png")
    emb.description = "**" + (radiant_name if match_det['radiant_win'] else dire_name) + "** Victory!\nMatch ID: " +  str(match['match_id'])

    emb.add_field(name="Details", value="Further stats will be added as they become available") ##This is index 0

    col = discord.Colour.default()
    col.value = 73 << 16 | 122 << 8 | 129 ##seal logo light
    emb.colour = col

    return(emb, match_det)

def process_match(match_det, emb):

    od_match = {}
    od_match = od.get_match(match_det['match_id'])

    if(od_match["radiant_gold_adv"] is None):
        raise Exception("Match not parsed")
    elif(od_match["radiant_gold_adv"][-1] is None or not od_match["game_mode"] in [1, 2]):
        return(None)

    emb.add_field(name="Match Details", value=dotaStats.quick_game_details(od_match), inline=False)

    rad_str = ""
    dire_str = ""
    leavers = 0
    ##TODO: leaver status can be done earlier
    for player in od_match["players"]:
        tmp = dotaStats.quick_player_info(player) + "\t\n\n"
        if(player["player_slot"] in range(0, 5)):
            leavers += player["leaver_status"]
            rad_str += tmp
        elif(player["player_slot"] in range(128, 133)):
            dire_str += tmp
            leavers += player["leaver_status"]

    if(leavers > 8):
        botLog("Greater than 8 leavers detected, ignoring match: " + match_det["match_id"])
        return(None)

    emb.add_field(name="{:30s}".format(match_det['radiant_name'] if ("radiant_name" in match_det) else "Radiant"), value=rad_str, inline=True)
    emb.add_field(name="{:30s}".format(match_det['dire_name'] if ("dire_name" in match_det) else "Dire"), value=dire_str, inline=True)

    emb.remove_field(0) ##Removes the further details message

    return(emb)


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
                if(len(cMsg) == 1):
                    await client.send_message(msg.channel, output)
                else:
                    await client.send_message(client.get_channel(cMsg[1]), output)
            else:
                await client.send_message(msg.channel, "no results to output")
    else:
        client.add_reaction(msg, '❓')

async def new_week(*args, **kwargs):
    client = kwargs['client']
    cMsg = args[0]
    msg = kwargs['msg']
    cfg = kwargs['cfg']
    if(msg.author.server_permissions.manage_server or msg.author.id == '133811493778096128'):
        leagues = load_leagues()
        for league in leagues:
            league.new_week()
        save_leagues(leagues)
        await client.send_message(msg.channel, "League results reset for current week")
    else:
        client.add_reaction(msg, '❓')


def get_team_logo(ugc):
    return(api.ISteamRemoteStorage.GetUGCFileDetails(appid=570, ugcid=ugc))

def team_info(team_id):
    return(api.IDOTA2Match_570.GetTeamInfoByTeamID(start_at_team_id=team_id, teams_requested=1)['result']['teams'][0])


def save_leagues(leagues):
    try:
        fileLock.acquire()
        __save_leagues_internal(leagues)
    except Exception as e:
        botLog("Error saving leagues: " + str(e))
    finally:
        fileLock.release()

def __save_leagues_internal(leagues):
    with open(PICKLE_LOCATION, "wb")as f:
        pickle.dump(leagues, f)

def load_leagues():
    try:
        fileLock.acquire()
        leagues = __load_leagues_internal()
    except Exception as e:
        botLog("Error loading leagues: " + str(e))
    finally:
        fileLock.release()
    return(leagues)

def __load_leagues_internal():
    leagueArray = None
    if(os.path.isfile(PICKLE_LOCATION)):
        with open(PICKLE_LOCATION, 'rb') as f:
            leagueArray = pickle.load(f)
    else:
        leagueArray = [classes.league(header.LEAGUE_IDS, 16, league_name="SEAL", last_match=3753343743)]

    return(leagueArray)

def init(chat_command_translation, function_translation):
    function_translation[classes.discordCommands.OUTPUT_LEAGUE_RESULTS] = force_match_process
    chat_command_translation["leagueresults"] = classes.discordCommands.OUTPUT_LEAGUE_RESULTS
    function_translation[classes.discordCommands.LEAGUE_NEW_WEEK] = new_week
    chat_command_translation["leaguenewweek"] = classes.discordCommands.LEAGUE_NEW_WEEK
    return(chat_command_translation, function_translation)
