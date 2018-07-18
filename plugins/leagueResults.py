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
import getopt

api = WebAPI(keys.STEAM_WEBAPI)
od = opendota.openDotaPlugin()
PICKLE_LOCATION = os.getcwd() + "/dataStores/leagueResults.pickle"
fileLock = asyncio.Lock()

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("MatchResult: " +  str(text), flush = True)
    except:
        print("MatchResult: Logging error. Probably some retard name", flush = True)

async def new_match_results(client):
    async with fileLock:
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
                
                await client.send_message(client.get_channel(league.channel_id), league.output_results())

                league.new_week()
                botLog("week reset")

        __save_leagues_internal(leagues)


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
        embed, match_det = create_min_embed(match, league.short_results)
        message = None
        await asyncio.sleep(0.3)
        if(embed is None):
            league.awaiting_processing[:] = [m for m in league.awaiting_processing if not m is None]
            return(False)

        radiant_team_id = match_det['radiant_team_id'] if ('radiant_team_id' in match_det) else 1
        dire_team_id = match_det['dire_team_id'] if ('dire_team_id' in match_det) else 2

        relevant_match = league.team_ids == [] or radiant_team_id in league.team_ids or dire_team_id in league.team_ids

        try:
            if(not league.roundup_only and relevant_match):
                message = await client.send_message(client.get_channel(league.channel_id), "**===============**", embed = embed)

                if(not league.short_results):
                    league.awaiting_opendota.append({"match" : match, "match_det" : match_det, "message" : message, "embed" : embed})
            
            botLog("Added match " + str(match_det["match_id"]))

            if(relevant_match):
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
                message = await client.edit_message(match_obj['message'], "**===============**", embed = embed)
                await asyncio.sleep(0.3)
        league.awaiting_opendota[i] = None

    league.awaiting_opendota[:] = [m for m in league.awaiting_opendota if not m is None]

    return(True)

def create_min_embed(match, short_results):
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
    emb.description = "**" + (radiant_name if match_det['radiant_win'] else dire_name) + "** Victory!\nMatch ID: " +  str(match['match_id']) + "\nhttps://www.dotabuff.com/matches/" + str(match['match_id']) + "\nhttps://www.opendota.com/matches/" +str(match['match_id'])

    if(not short_results):
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
        leagues = await load_leagues()
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
    async with fileLock:
        client = kwargs['client']
        cMsg = args[0]
        msg = kwargs['msg']
        cfg = kwargs['cfg']
        if(msg.author.server_permissions.manage_server or msg.author.id == '133811493778096128'):
            leagues = __load_leagues_internal()
            for league in leagues:
                league.new_week()
            await client.send_message(msg.channel, "League results reset for current week")
            __save_leagues_internal(leagues)
        else:
            client.add_reaction(msg, '❓')

async def add_league(*args, **kwargs):
    client = kwargs['client']
    msg = kwargs['msg']
    cfg = kwargs['cfg']
    cmd = kwargs['command']
    cMsg = args[0][1:]

    if(not msg.author.server_permissions.manage_server or not msg.author.id == '133811493778096128'):
        client.add_reaction(msg, '❓')
        return

    try:
        optlist, leagueArgs = getopt.getopt(cMsg, 'srhi:t:n:m:l:b:', ['help', 'league-ids=', 'num-teams=', 'league-name=', 'last-match=', 'team-ids=', 'short-results', 'roundup-only', 'best-of='])
    except Exception as e:
        await client.send_message(msg.channel, "Add League: " + str(e))
        return

    idList = None
    numTeams = None
    leagueName = None
    lastMatch = None
    teamList = None
    bestOf = None
    shortResults = None
    roundupOnly = None

    for o, v in optlist:

        if(o in ["-i", "--league-ids"]):
            tmp = v.split(',')
            idList = []
            for s in tmp:
                try:
                    idList.append(int(s))
                except:
                    await client.send_message(msg.channel, o  + " must supply a list of numbers")
                    return

        elif(o in ["-t", "--num-teams"]):
            try:
                numTeams = int(v)
            except:
                await client.send_message(msg.channel, o + " must supply a number")
                return

        elif(o in ["-n", "--league-name"]):
            leagueName = v.replace('_', ' ')

        elif(o in ["-m", "--last-match"]):
            try:
                lastMatch = int(v)
            except:
                await client.send_message(msg.channel, o + " must supply a number")
                return

        elif(o in ["-l", "--team-ids"]):
            tmp = v.split(',')
            teamList = []
            for s in tmp:
                try:
                    teamList.append(int(s))
                except:
                    await client.send_message(msg.channel, o + " must supply a list of numbers")
                    return

        elif(o in ['-b', "--best-of"]):
            try:
                bestOf = int(v)
            except:
                await client.send_message(msg.channel, o + " must supply a number")
                return

        elif(o in ['-s', '--short-results']):
            shortResults = True

        elif(o in ['-r', '--roundup-only']):
            roundupOnly = True

        elif(o in ["-h", "--help"]):
            base = "`!addleague` lets you add league results to the current channel.\n"
            if(cmd == classes.discordCommands.MODIFY_LEAGUE):
                "`!modifyleague` lets you add league results to the current channel.\nThis command is selective, so anything not specified will not be changed. Arguments that accept no input will simply be toggled if specified"
            await client.send_message(msg.channel, base +
            "Note: for arguments that accept lists, seperate values with commas only, no spaces\n\n**Args:**" 
            "\n\n\t`--league-ids=<int>,<int>,<int>,...`: *Required*. This lets you specify one or more league ids to track." 
            "\n\n\t`--num-teams=<int>` *Optional*. The bot will count the number of teams that have logged results, and post a roundup if it detects every team has played. If an odd number is specified, we assume 1 team has a bye per week."
            "\n\n\t`--league-name=<string>` *Required*. The name of the league. This should be a unique identifier per channel. If you want a space in your league name, use underscores instead, they will be converted. Will be displayed in results"
            "\n\n\t`--last-match=<int>` *Optional*. If specified, the bot will only track results strictly after the match id specified"
            "\n\n\t`--team-ids=<int>,<int>,<int>,...` *Optional*. Whitelist of team ids to track. If not specified, will track all matches on the specified tickets (league-ids)."
            "\n\n\t`--best-of=<int>` *Optional*. DOES NOT SUPPORT ANYTHING OTHER THAN 2 CURRENTLY. Sets the number of games per series. Used to calculate total games per week. Defaults to 2\n\t\tFormula is `((num-teams % 2 == 0) ? num-teams : num-teams - 1) / 2) * best-of`"
            "\n\n\t`--short-results` *Optional*. Flag that specifies that abridged result embeds should be used instead of the default longform ones"
            "\n\n\t`--roundup-only` *Optional*. Flag that if specified, means the bot won't post match results, only roundups. Overrides `--short-results`"
            "\n\n\t`--help` Displays this message")
            
            ##If someone requests help we do not want to populate team too
            return
        else:
            pass

    if(cmd == classes.discordCommands.ADD_NEW_LEAGUE):
        if(idList == None):
            await client.send_message(msg.channel, "Missing required parameter --league-ids")
            return
        
        if(leagueName == None):
            await client.send_message(msg.channel, "Missing required parameter --league-name")
            return

        ##Fill in default values
        numTeams = numTeams if not numTeams is None else 0
        lastMatch = lastMatch if not lastMatch is None else 0
        teamList = teamList if not teamList is None else []
        bestOf = bestOf if not teamList is None else 2
        shortResults = shortResults if not shortResults is None else False
        roundupOnly = roundupOnly if not roundupOnly is None else False

        ##The rest needs to be done under lock
        async with fileLock:
            leagueArray =  __load_leagues_internal()

            ##check for duplicates
            for league in leagueArray:
                if(league.league_name == leagueName and league.channel_id == msg.channel.id):
                    await client.send_message(msg.channel, "Duplicate league with name '" + leagueName + "' found for this channel. If you want to modify the league, use `!modifyleague`. Aborting.")
                    return

            leagueArray.append(classes.league(idList, leagueName, msg.channel.id, num_teams=numTeams, last_match=lastMatch, short_results=shortResults, roundup_only=roundupOnly, team_ids=teamList))
            __save_leagues_internal(leagueArray)
        
        await client.send_message(msg.channel, "Successfully added league " + leagueName)

    elif(cmd == classes.discordCommands.MODIFY_LEAGUE):

        if(leagueName == None):
            await client.send_message(msg.channel, "Missing required parameter --league-name")
            return
        
        async with fileLock:
            leagueArray =  __load_leagues_internal()

            found = False
            for league in leagueArray:
                if(league.league_name == leagueName and league.channel_id == msg.channel.id):
                    
                    found=True

                    if(not numTeams is None):
                        league.num_teams = numTeams
                        league.set_est_results()
                    
                    if(not idList is None):
                        league.league_ids = idList
                    
                    if(not teamList is None):
                        league.team_ids = teamList

                    if(not bestOf is None):
                        league.best_of = bestOf

                    if(not lastMatch is None):
                        league.set_last_matches(lastMatch)

                    if(not shortResults is None):
                        league.short_results = not league.short_results

                    if(not roundupOnly is None):
                        league.roundup_only = not league.roundup_only

            if(not found):
                await client.send_message("Unable to find league with name '" + leagueName + "' for this channel. If you want to create a new league, use `!addleauge`. Aborting.")
                return

            __save_leagues_internal(leagueArray)
        
        await client.send_message(msg.channel, "Successfully modified league " + leagueName)


def get_team_logo(ugc):
    return(api.ISteamRemoteStorage.GetUGCFileDetails(appid=570, ugcid=ugc))

def team_info(team_id):
    return(api.IDOTA2Match_570.GetTeamInfoByTeamID(start_at_team_id=team_id, teams_requested=1)['result']['teams'][0])


async def save_leagues(leagues):
    async with fileLock:
        try:
            __save_leagues_internal(leagues)
        except Exception as e:
            botLog("Error saving leagues: " + str(e))

def __save_leagues_internal(leagues):
    with open(PICKLE_LOCATION, "wb") as f:
        pickle.dump(leagues, f)

async def load_leagues():
    async with fileLock:
        try:
            leagues = __load_leagues_internal()
        except Exception as e:
            botLog("Error loading leagues: " + str(e))
            return None
        return(leagues)

def __load_leagues_internal():
    leagueArray = None
    if(os.path.isfile(PICKLE_LOCATION)):
        with open(PICKLE_LOCATION, 'rb') as f:
            leagueArray = pickle.load(f)
    else:
        leagueArray = []

    return(leagueArray)

def init(chat_command_translation, function_translation):
    ##Add league result commands
    function_translation[classes.discordCommands.OUTPUT_LEAGUE_RESULTS] = force_match_process
    chat_command_translation["leagueresults"] = classes.discordCommands.OUTPUT_LEAGUE_RESULTS
    
    ##Add new week commands
    function_translation[classes.discordCommands.LEAGUE_NEW_WEEK] = new_week
    chat_command_translation["leaguenewweek"] = classes.discordCommands.LEAGUE_NEW_WEEK
    
    ##Add new league commands
    function_translation[classes.discordCommands.ADD_NEW_LEAGUE] = add_league
    chat_command_translation["addleague"] = classes.discordCommands.ADD_NEW_LEAGUE

    ##Modify league commands
    function_translation[classes.discordCommands.MODIFY_LEAGUE] = add_league
    chat_command_translation["modifyleague"] = classes.discordCommands.MODIFY_LEAGUE

    return(chat_command_translation, function_translation)
