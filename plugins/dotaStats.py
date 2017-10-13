from plugins import opendota
from steam import SteamID
from wordcloud import WordCloud
from PIL import Image
import heatmap
import os
import pickle
import discord
import re
import classes
import difflib
import datetime
import colorsys
import io
import os

PLAYER_DICT_NAME = os.getcwd() + "/dataStores/ddDict.pickle"
MAP_IMAGE_NAME = os.getcwd() + "/dataStores/detailed_700.png"
player_dict = {}
client = None
url_matcher = r"\w+?.com\/(?:esports\/)?players\/(\d+)"
od = opendota.openDotaPlugin()
hero_dict = {}
hero_dict2 = {}
for j in od.get_heroes():
    hero_dict[j["localized_name"].lower()] = j
    hero_dict2[j["id"]] = j

##dict entry format: name : discord object, steamId object
##TODO: use difflib

def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("dotaStats: " +  str(text), flush = True)
    except:
        print("dotaStats: Logging error. Probably some retard name", flush = True)

########  ####  ######  ########    ########  #######   #######  ##        ######
##     ##  ##  ##    ##    ##          ##    ##     ## ##     ## ##       ##    ##
##     ##  ##  ##          ##          ##    ##     ## ##     ## ##       ##
##     ##  ##  ##          ##          ##    ##     ## ##     ## ##        ######
##     ##  ##  ##          ##          ##    ##     ## ##     ## ##             ##
##     ##  ##  ##    ##    ##          ##    ##     ## ##     ## ##       ##    ##
########  ####  ######     ##          ##     #######   #######  ########  ######

def load_player_dict():
    if(os.path.isfile(PLAYER_DICT_NAME)):
        with open(PLAYER_DICT_NAME, "rb") as f:
            return(pickle.load(f))
    return({})

def save_player_dict():
    with open(PLAYER_DICT_NAME, "wb") as f:
        pickle.dump(player_dict, f)

   ###     ######  ##    ## ##    ##  ######
  ## ##   ##    ##  ##  ##  ###   ## ##    ##
 ##   ##  ##         ####   ####  ## ##
##     ##  ######     ##    ## ## ## ##
#########       ##    ##    ##  #### ##
##     ## ##    ##    ##    ##   ### ##    ##
##     ##  ######     ##    ##    ##  ######

async def determine_request_type(msg, cMsg, client):
    req_index = -1
    player = None
    ##add is a special case
    if(cMsg[1] in ["add", "register"]):
        await associate_player(msg, cMsg, client)
        return
    if(cMsg[1] in ["match"]):
        ##catch commands that dont need a player specified
        req_index = 1
    ##determine who is being talked about
    elif(cMsg[1] in ["me", "my"]):
        req_index = 2
        player, resp = get_player_from_author(msg)
        if(player is None):
            await client.send_message(msg.channel, resp)
            return(res)
    else:
        for word in cMsg:
            if word in reqs.keys():
                req_index = cMsg.index(word)
                break
        if req_index is 0:
            await client.send_message(msg.channel, "Unable to determine what command is being requested")
        else:
            input_name = ' '.join(msg.content[1:].split()[1 : req_index]).strip()
            player, res = get_player_from_name(input_name)
            if(not res is None):
                await client.send_message(msg.channel, res)
                if(player is None):
                    return
    ##get the request function
    request = None
    botLog(req_index)
    botLog(cMsg[req_index])
    if(req_index == -1):
        await client.send_message(msg.channel, "Unable to determine what command is being requested")
    if(not cMsg[req_index] in reqs.keys()):
        possible_matches = difflib.get_close_matches(cMsg[req_index], reqs.keys())
        if(len(possible_matches) == 0):
            await client.send_message(msg.channel, "Unknown request. Check your spelling!")
            return
        else:
            await client.send_message(msg.channel, "Unknown request. Using best guess for request of `" + possible_matches[0] + "`")
            request = reqs[possible_matches[0]]
    else:
        request = reqs[cMsg[req_index]]
    ##find modifiers
    modifier_loc = []
    for i in range(req_index + 1, req_index + 1 + len(cMsg[req_index+1:])):
        if cMsg[i] in modifiers:
            modifier_loc.append(i)
    #determine modifiers
    params = {}
    for i in range(0, len(modifier_loc)):
        start_index = modifier_loc[i] + 1
        end_index = modifier_loc[i + 1] if not i == len(modifier_loc) - 1 else len(cMsg)
        r = modifiers[cMsg[modifier_loc[i]]](' '.join(cMsg[start_index : end_index]))
        if(not r[0] is None):
            params[r[0]] = r[1]
        else:
            await client.send_message(msg.channel, "Invalid parameter for modifier `" + cMsg[modifier_loc[i]] +"`, skipping...")
    botLog(params)
    req_specifier = None
    if(len(modifier_loc) == 0 and not req_index + 1 == len(cMsg)):
        req_specifier = ' '.join(cMsg[req_index + 1 :])
    elif(not len(modifier_loc) == 0 and not req_index + 1 == modifier_loc[0]):
        req_specifier = ' '.join(cMsg[req_index + 1 : modifier_loc[0]])
    if(not request is None):
        await request(cMsg, client = client, msg = msg, mod = req_specifier, player = player, params = params)
    else:
        await client.send_message(msg.channel, "Unknown error in command processing.")



async def associate_player(msg, cMsg, client):
    user = msg.author
    if(len(cMsg) > 2):
        player_id = None
        acceptable_links = ["opendota.com/players", "dotabuff.com/players", "dotabuff.com/esports/players"]
        if(any(x in cMsg[2] for x in acceptable_links)):
            botLog("found in link form")
            match = re.search(url_matcher, cMsg[2])
            if(not match is None):
                player_id = match.group(1)
            else:
                return(False)
            botLog(player_id)
        else:
            try:
                player_id = int(cMsg[2])
            except:
                player_id = None
                botLog("bad id provided")
                return(False)
        if(not player_id is None):
            acc = SteamID(player_id)
            r = od.get_players(acc.as_32)
            if('profile' in r):
                __associate_player_backend(user, acc)
                emb = steam_acc_embed_od(r)
                await client.send_message(msg.channel, "Associated *" + user.name + "* with: ", embed = emb)
                return(True)
            else:
                return(False)
        else:
            botLog("no info provided")
            return(False)


 ######  ########  ########  ######  #### ######## #### ######## ########   ######
##    ## ##     ## ##       ##    ##  ##  ##        ##  ##       ##     ## ##    ##
##       ##     ## ##       ##        ##  ##        ##  ##       ##     ## ##
 ######  ########  ######   ##        ##  ######    ##  ######   ########   ######
      ## ##        ##       ##        ##  ##        ##  ##       ##   ##         ##
##    ## ##        ##       ##    ##  ##  ##        ##  ##       ##    ##  ##    ##
 ######  ##        ########  ######  #### ##       #### ######## ##     ##  ######

async def get_players_wordcloud(*args, **kwargs):
    await __get_players_wordcloud(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'])



async def __get_players_wordcloud(msg, player, client, params):
    r = od.get_players_wordcloud(player["steam"].as_32, params = params)
    wordcloud_freq = r["my_word_counts"]
    if(len(wordcloud_freq) == 0):
        if(not 'hero_id' in params):
            await client.send_message(msg.channel, "Unable to get wordcloud data for " + player["discord"].name)
        else:
            await client.send_message(msg.channel, "Unable to get hero specific wordcloud data for " + player["discord"].name)
        return
    wc = WordCloud(background_color="white", scale=2, prefer_horizontal=0.5).generate_from_frequencies(wordcloud_freq)
    img = wc.to_image()
    imgBytes = io.BytesIO()
    img.save(imgBytes, format="PNG")
    imgBytes.seek(0)
    await client.send_file(msg.channel, imgBytes, filename="wordcloud.png" , content = player["discord"].name + "'s wordcloud:")



async def get_players_wardmap(*args, **kwargs):
    await __get_players_wardmap(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'], kwargs['mod'])

async def match_details(*args, **kwargs):
    await __match_details_backend(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'], kwargs['mod'])


async def __match_details_backend(msg, player, client, params, req_specifier=None):
    try:
        req_specifier = int(req_specifier)
    except:
        req_specifier = None
    if(req_specifier is None):
        await client.send_message(msg.channel, "Invalid match ID specified")
        return
    r = od.get_match(req_specifier, params = params)
    emb =  match_summary_embed(r)
    await client.send_message(msg.channel, " ", embed = emb)



async def __get_players_wardmap(msg, player, client, params, req_specifier=None):
    t = difflib.get_close_matches(str(req_specifier), ["obs", "observer", "sen", "sentry"])
    ward_type = True
    if(len(t) is 0):
        if(not req_specifier == None):
            await client.send_message(msg.channel, "Unable to determine requested ward type, defaulting to sentry")
    else:
        ward_type = True if ["obs", "observer", "sen", "sentry"].index(t[0]) < 3 else False
    wardmap = create_ward_heatmap(player['steam'].as_32, obs=ward_type, params = params)
    if(wardmap is None):
        if(not 'hero_id' in params):
            await client.send_message(msg.channel, "Unable to get wardmap data for " + player["discord"].name)
        else:
            await client.send_message(msg.channel, "Unable to get hero specific wardmap data for " + player["discord"].name)
        return
    await client.send_file(msg.channel, wardmap, filename="wardmap.png" , content = player["discord"].name + "'s " + ("observer" if ward_type else "sentry") + " wardmap:")



async def get_player_summary(*args, **kwargs):
    await __get_player_summary(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'], kwargs['mod'])



async def __get_player_summary(msg, player, client, params, num = None):
    #TODO: add checks for date and stuff too
    limit = None
    if(not any(x in params for x in ['date', 'limit'])):
        try:
            num = int(num)
        except Exception as e:
            await client.send_message(msg.channel, "Unknown number of games, defaulting to 20")
            num = None
        params['limit'] = num if not num is None else 20
        limit = str(params['limit']) + " games"
    else:
        if('limit' in params):
            limit = str(params['limit']) + " games"
        if('date' in params):
            if(not limit is None):
                limit += " , "
            else:
                limit = ''
            limit += str(params['date']) + " days"
    r = od.get_players_totals(player["steam"].as_32, params = params)
    ##TODO: switch to matches to allow varaible length
    r2 = od.get_players_recent_matches(player["steam"].as_32)#, params = params)
    r = rewrite_totals_object(r)
    emb = player_summary_embed(r, r2, player, params, limit=limit)
    await client.send_message(msg.channel, " ", embed = emb)
    pass



async def display_player_profile(*args, **kwargs):
    await __display_player_profile(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'])



async def __display_player_profile(msg, player, client, params):
    r = od.get_players(player["steam"].as_32)
    emb = steam_acc_embed_od(r)
    await client.send_message(msg.channel, "Your account is currently associated with: ", embed = emb)



async def player_on_hero_test(*args, **kwargs):
    await __get_hero_on_player_backend(kwargs['msg'], kwargs['client'], kwargs['mod'], kwargs['player'], params=kwargs['params'])



async def __get_hero_on_player_backend(msg, client, heroString, player, params=None):
    possible_matches = difflib.get_close_matches(heroString, hero_dict.keys())
    if(len(possible_matches) is 0):
        await client.send_message(msg.channel, "Please spell hero name correctly")
        return
    hero = hero_dict[possible_matches[0]]
    if(params is None):
        params = {}
    params["hero_id"] = hero["id"]
    r = od.get_players_heroes(player["steam"].as_32, params = params)
    hero_stats = r[0]
    emb = hero_card_embed(hero_stats, player, hero)
    await client.send_message(msg.channel, "", embed = emb)


######## ##     ## ########  ######## ########   ######
##       ###   ### ##     ## ##       ##     ## ##    ##
##       #### #### ##     ## ##       ##     ## ##
######   ## ### ## ########  ######   ##     ##  ######
##       ##     ## ##     ## ##       ##     ##       ##
##       ##     ## ##     ## ##       ##     ## ##    ##
######## ##     ## ########  ######## ########   ######

def hero_card_embed(res, player, hero):
    emb = discord.Embed()
    emb.title = player["discord"].name + " on " + hero["localized_name"]
    emb.type = "rich"
    emb.description = "Card still WIP"
    emb.set_thumbnail(url = "http://cdn.dota2.com/apps/dota2/images/heroes/" + hero["name"].replace("npc_dota_hero_", "") + "_full.png")
    emb.add_field(name = "Games Played", value = str(res["games"]), inline = True)
    emb.add_field(name = "Winrate", value = str(round(res["win"] * 100 / max(res["games"], 1), 2)) + "%", inline = True)
    emb.add_field(name = "Wins", value = str(res["win"]), inline = True)
    emb.add_field(name = "Loses", value = str(res["games"] - res["win"]), inline = True)
    emb.colour = get_wr_color(res["win"] / max(res["games"], 1))
    return(emb)

def steam_acc_embed_od(res):
    emb = discord.Embed()
    emb.title = res["profile"]["personaname"]
    emb.type = "rich"
    emb.description = "Steam ID64: " + res["profile"]["steamid"]
    emb.set_thumbnail(url = res["profile"]["avatarfull"])
    emb.add_field(name = "Steam Profile", value = res["profile"]["profileurl"], inline = False)
    emb.add_field(name = "Solo MMR", value = res["solo_competitive_rank"], inline = True)
    emb.add_field(name = "Party MMR", value = res["competitive_rank"], inline = True)
    emb.colour = discord.Colour.blue()
    return(emb)

def player_summary_embed(res, res2, player, params, limit = None):
    emb = discord.Embed()
    emb.title = player["discord"].name + "'s Summary"
    if(limit is None):
        emb.description = "All time"
    else:
        emb.description = "Recent " + limit
    emb.type = "rich"
    emb.set_thumbnail(url = player["discord"].avatar_url)
    emb.add_field(name = "Kills", value = get_totals_str(res["kills"]), inline = True)
    emb.add_field(name = "Deaths", value = get_totals_str(res["deaths"]), inline = True)
    emb.add_field(name = "Assists", value = get_totals_str(res["assists"]), inline = True)
    emb.add_field(name = "KDA", value = get_partial_totals_str(res["kda"]), inline = True)

    emb.add_field(name = "Last Hits", value = get_partial_totals_str(res["last_hits"]), inline = True)
    emb.add_field(name = "Denies", value = get_partial_totals_str(res["denies"]), inline = True)
    emb.add_field(name = "GPM", value = get_partial_totals_str(res["gold_per_min"]), inline = True)
    emb.add_field(name = "XPM", value = get_partial_totals_str(res["xp_per_min"]), inline = True)
    emb.add_field(name = "Recent Games", value = quick_recent_matches(res2, params['limit']), inline = False)
    return(emb)

def match_summary_embed(res):
    emb = discord.Embed()
    emb.title = "Match ID " + str(res["match_id"])
    emb.type = "rich"
    emb.description = "Radiant" if res["radiant_win"] else "Dire" + " Victory"
    rad_str = ""
    dire_str = ""
    for player in res["players"]:
        tmp = quick_player_info(player) + "\t\n\n"
        if(player["player_slot"] in range(0, 5)):
            rad_str += tmp
        elif(player["player_slot"] in range(128, 133)):
            dire_str += tmp
    ##TODO: add team names
    emb.add_field(name = "Match details:", value = quick_game_details(res), inline = False)
    emb.add_field(name = "Radiant:", value = rad_str)
    emb.add_field(name = "Dire:", value = dire_str)
    return(emb)


##     ## ####  ######   ######
###   ###  ##  ##    ## ##    ##
#### ####  ##  ##       ##
## ### ##  ##   ######  ##
##     ##  ##        ## ##
##     ##  ##  ##    ## ##    ##
##     ## ####  ######   ######

def quick_recent_matches(res, limit):
    outstr = ""
    limit = min(limit, 10)
    for i in range(0, limit):
        match = res[i]
        outstr += "`" + str(match["match_id"]) + "`: "
        outstr += "Won " if (match["radiant_win"] and match["player_slot"] in range(0, 5)) or (not match["radiant_win"] and match["player_slot"] in range(128, 133)) else "Lost "
        outstr += "as **" + hero_dict2[match["hero_id"]]["localized_name"] + "** "
        outstr += " KDA: " + str(match["kills"]) + "/" + str(match["deaths"]) + "/" + str(match["assists"])
        outstr += "\n" if not i == limit - 1 else ""
    return(outstr)



def quick_game_details(res):
    length = "**Duration:** " + str(res["duration"] // 60) + ":" + str(res["duration"] % 60)
    rad_score = res["radiant_score"]
    dire_score = res["dire_score"]
    score = "**Score:** " + str(rad_score) + " - " + str(dire_score)
    gold = res["radiant_gold_adv"][-1] ##Get last enty
    botLog(gold)
    xp = res["radiant_xp_adv"][-1] ##Get last entry
    botLog(xp)
    gold_str = "**Gold:** +" + str(abs(gold)) + (" Radiant" if gold >= 0 else " Dire")
    xp_str = "**Experience:** +" + str(abs(xp)) + (" Radiant" if xp >= 0 else " Dire")
    return(length + "\n" + score + "\n" + gold_str + "\n" + xp_str)


def quick_player_info(player):
    hero_name = hero_dict2[player["hero_id"]]["localized_name"]
    kda = str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"])
    name = player["personaname"] ##player["name"]
    last_hits = player["last_hits"]
    networth = player["gold_t"][-1]
    return("**" + name + "** *" + hero_name + "*\nKDA: " + kda + "\nLast Hits: " + str(last_hits) + "\nNetworth: " + str(networth))

def rewrite_totals_object(obj_in):
    obj_out = {}
    for item in obj_in:
        obj_out[item['field']] = item
    return(obj_out)

def get_partial_totals_str(field):
    n = float(field["n"])
    s = float(field['sum'])
    return(str(round(s / n, 2)))

def get_totals_str(field):
    n = float(field['n'])
    s = float(field['sum'])
    return(str(round(s / n, 2)) + "(" + str(round(s, 2)) + ")")

def get_player_from_author(msg):
    if(not msg.author.name in player_dict):
        resp  = "You are not registered. Please add your account with `!od add [opendota|dotabuff|steam_id32|steam_id64]`"
        return(None, resp)
    player = player_dict[msg.author.name]
    return(player, None)

def get_player_from_name(input_name):
    if(input_name in player_dict):
        player = player_dict[input_name]
        return(player, None)
    else:
        possible_matches = difflib.get_close_matches(input_name, player_dict.keys())
        if(len(possible_matches) is 0):
            resp = "Unable to find player. Are they registered?"
            return(None, resp)
        else:
            resp =  "Unable to match exact player. Using approximation '" + possible_matches[0] +"'\nIf this is incorrect, check your spelling and make sure they are registered."
            player = player_dict[possible_matches[0]]
            return(player, resp)

def scale_point(x, y):
    return([(512/127) * (float(x) - 64), (512/127) * (127 - (float(y) - 64))])

def create_ward_heatmap(player_id, obs=True, params = None):
    r = od.get_players_wardmap(player_id, params = params)
    j = r["obs"] if obs else r["sen"]
    pt_arr = []
    if(len(j) == 0):
        return(None)
    for x in j.keys():
        for y in j[x].keys():
            for i in range(0, int(j[x][y])):
                pt_arr.append(scale_point(x, y))
    hm = heatmap.Heatmap()
    background = Image.open(MAP_IMAGE_NAME)
    foreground = hm.heatmap(pt_arr, dotsize=35, size=(512, 512), opacity = 110)
    background.paste(foreground, (0,0), foreground)
    imgBytes = io.BytesIO()
    background.save(imgBytes, format="PNG")
    imgBytes.seek(0)
    return(imgBytes)

def get_wr_color(winrate):
    h = winrate / 3
    col = discord.Colour.default()
    r, g, b = colorsys.hsv_to_rgb(h, 1, 255)
    col.value = int(r) << 16 | int(g) << 8 | int(b)
    return(col)

def __associate_player_backend(user, steam_id):
    acc = SteamID(int(steam_id))
    global player_dict
    player_dict[user.name] = {"discord" : user, "steam" : acc}
    save_player_dict()

def init(chat_command_translation, function_translation):
    function_translation[classes.discordCommands.OPENDOTA] = open_dota_main
    chat_command_translation["od"] = classes.discordCommands.OPENDOTA
    global player_dict
    player_dict = load_player_dict()
    return(chat_command_translation, function_translation)

##     ##  #######  ########  #### ######## #### ######## ########   ######
###   ### ##     ## ##     ##  ##  ##        ##  ##       ##     ## ##    ##
#### #### ##     ## ##     ##  ##  ##        ##  ##       ##     ## ##
## ### ## ##     ## ##     ##  ##  ######    ##  ######   ########   ######
##     ## ##     ## ##     ##  ##  ##        ##  ##       ##   ##         ##
##     ## ##     ## ##     ##  ##  ##        ##  ##       ##    ##  ##    ##
##     ##  #######  ########  #### ##       #### ######## ##     ##  ######

def as_modifier(heroString):
    #TODO: functionize this
    possible_matches = difflib.get_close_matches(heroString, hero_dict.keys())
    if(len(possible_matches) is 0):
        return((None, None))
    hero_id = hero_dict[possible_matches[0]]["id"]
    return("hero_id", hero_id)

def on_modifier(sideString):
    side_dict = {"radiant" : 1, "dire" : 0}
    possible_matches = difflib.get_close_matches(sideString, side_dict.keys())
    if(len(possible_matches) is 0):
        return((None, None))
    side = side_dict[possible_matches[0]]
    return("is_radiant", side)

def recent_modifier(game_limit):
    if(game_limit is ''):
        game_limit = 20
    try:
        game_limit = int(game_limit)
    except:
        return((None, None))
    return("limit", game_limit)

def days_modifier(days_limit):
    if(days_limit is ''):
        days_limit = 30
    try:
        days_limit = int(days_limit)
    except:
        return((None, None))
    return("date", days_limit)

reqs = {"as" : player_on_hero_test, "wardmap" : get_players_wardmap,
        "wordcloud" : get_players_wordcloud, "setnick" : None,
        "add" : associate_player, "summary" : get_player_summary,
        "profile" : display_player_profile, "match" : match_details}
modifiers = {"on" : on_modifier, "recent" : recent_modifier,
            "as" : as_modifier, "days" : days_modifier}


async def open_dota_main(*args, **kwargs):
    if('msg' in kwargs):
        client = kwargs['client']
        msg = kwargs['msg']
        cMsg  = args[0]
        cfg = kwargs['cfg']
        if(not cfg.checkMessage("opendota", msg)):
            return
        await determine_request_type(msg, cMsg, client)
        return
