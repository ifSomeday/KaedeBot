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

PLAYER_DICT_NAME = os.getcwd() + "/dataStores/ddDict.pickle"
MAP_IMAGE_NAME = os.getcwd() + "/dataStores/detailed_700.png"
player_dict = {}
client = None
url_matcher = r"\w+?.com\/(?:esports\/)?players\/(\d+)"
od = opendota.openDotaPlugin()
hero_dict = {}
for j in od.get_heroes():
    hero_dict[j["localized_name"].lower()] = j

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

def __associate_player_backend(user, steam_id):
    acc = SteamID(int(steam_id))
    global player_dict
    player_dict[user.name] = {"discord" : user, "steam" : acc}
    save_player_dict()

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
    ##determine who is being talked about
    if(cMsg[1] in ["me", "my"]):
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
    if(req_index == -1):
        await client.send_message(msg.channel, "Unable to deterine what command is being requested")
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
    botLog(params)
    req_specifier = None
    if(len(modifier_loc) == 0 and not req_index + 1 == len(cMsg)):
        req_specifier = ' '.join(cMsg[req_index + 1 :])
    elif(not len(modifier_loc) == 0 and not req_index + 1 == modifier_loc[0]):
        req_specifier = ' '.join(cMsg[req_index + 1 : modifier_loc[0]])
    if(not request is None):
        await request(cMsg, client = client, msg = msg, mod = req_specifier, player = player, params = params)


async def get_players_wordcloud(*args, **kwargs):
    await __get_players_wordcloud(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'])

async def __get_players_wordcloud(msg, player, client, params):
    r = od.get_players_wordcloud(player["steam"].as_32, params = params)
    wordcloud_freq = r["my_word_counts"]
    wc = WordCloud(background_color="white", scale=2, prefer_horizontal=0.5).generate_from_frequencies(wordcloud_freq)
    img = wc.to_image()
    imgBytes = io.BytesIO()
    img.save(imgBytes, format="PNG")
    imgBytes.seek(0)
    await client.send_file(msg.channel, imgBytes, filename="wordcloud.png" , content = player["discord"].name + "'s wordcloud:")


async def get_players_wardmap(*args, **kwargs):
    await __get_players_wardmap(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'], kwargs['mod'])

async def __get_players_wardmap(msg, player, client, params, req_specifier=None):
    wardmap = create_ward_heatmap(player['steam'].as_32, obs=True, params = params)
    await client.send_file(msg.channel, wardmap, filename="wardmap.png" , content = player["discord"].name + "'s wardmap:")

async def get_player_summary(*args, **kwargs):
    await __get_player_summary(kwargs['msg'], kwargs['player'], kwargs['client'], kwargs['params'], kwargs['mod'])

async def __get_player_summary(msg, player, client, params, num = None):
    #TODO: add checks for date and stuff too
    if(not 'limit' in params):
        params['limit'] = 20
    r = od.get_players_totals(player["steam"].as_32, params = params)
    r = rewrite_totals_object(r)
    emb = player_summary_embed(r, player, params['limit'])
    await client.send_message(msg.channel, " ", embed = emb)
    pass

async def associate_player(msg, cMsg, user, client):
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

async def display_self_association(msg, cMsg, client):
    if(msg.author.name in player_dict):
        player = player_dict[msg.author.name]
        r = od.get_players(player["steam"].as_32)
        emb = steam_acc_embed_od(r)
        await client.send_message(msg.channel, "Your account is currently associated with: ", embed = emb)
    else:
        await client.send_message(msg.channel, "You are not registered. Please add your account with `!od add [opendota|dotabuff|steam_id32|steam_id64]`")

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

def player_summary_embed(res, player, num = None):
    emb = discord.Embed()
    emb.title = player["discord"].name + "'s Summary"
    if(num is None):
        emb.description = "Alltime games"
    else:
        emb.description = "Recent " + str(num) + " games"
    emb.type = "rich"
    emb.set_thumbnail(url = player["discord"].avatar_url)
    emb.add_field(name = "Kills", value = get_totals_str(res["kills"]), inline = True)
    emb.add_field(name = "Deaths", value = get_totals_str(res["deaths"]), inline = True)
    emb.add_field(name = "Assists", value = get_totals_str(res["assists"]), inline = True)
    emb.add_field(name = "KDA", value = str(res["kda"]['sum'] / res["kda"]["n"]), inline = True)
    return(emb)


##     ## ####  ######   ######
###   ###  ##  ##    ## ##    ##
#### ####  ##  ##       ##
## ### ##  ##   ######  ##
##     ##  ##        ## ##
##     ##  ##  ##    ## ##    ##
##     ## ####  ######   ######

def rewrite_totals_object(obj_in):
    obj_out = {}
    for item in obj_in:
        obj_out[item['field']] = item
    return(obj_out)

def get_totals_str(field):
    n = float(field['n'])
    s = float(field['sum'])
    return( str(s / n) + "(" +str(s) + ")")

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

def get_players_message(msg):
    sender = None
    players = []
    failed = []
    success = True
    if(msg.author.name in player_dict):
        sender = player_dict[msg.author.name]
    else:
        success = False
    for user in msg.mentions:
        if(user.id in player_dict):
            players.append(player_dict[user.name])
        else:
            failed.append(user)
            ##dont use these additional mentions for now
            #success = False
    return(sender, players, failed, success)

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

################################

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


reqs = {"as" : player_on_hero_test, "wardmap" : get_players_wardmap,
        "wordcloud" : get_players_wordcloud, "setnick" : None,
        "add" : associate_player, "summary" : get_player_summary}
modifiers = {"on" : on_modifier, "since" : "since mod", "after" : "afte mod", "past" : "past mod", "as" : as_modifier}


async def open_dota_main(*args, **kwargs):
    if('msg' in kwargs):
        client = kwargs['client']
        msg = kwargs['msg']
        if(not msg.server.id == '133812880654073857'):
            return
        cMsg  = args[0]
        if(not msg.server.id == "213086692683415552"):
            return
        sender, players, failed, success = get_players_message(msg)
        await determine_request_type(msg, cMsg, client)
        #
        #
        return
        #
        #
        if(cMsg[1] == "add"):
            res = await associate_player(msg, cMsg, msg.author, client)
            if(not res):
                await client.send_message(msg.channel, "Unable to register.\nPlease provide your opendota/dotabuff link, or steam ID32/ID64\n`!od add [opendota|dotabuff|steam_id32|steam_id64]`")
        elif(cMsg[1] == "me" and len(cMsg) == 2):
            await display_self_association(msg, cMsg, client)
        elif("on" in cMsg):
            if("as" in cMsg):
                await player_on_hero_with_side(msg, cMsg, client)
            else:
                await player_on_hero(msg, cMsg, client)
        elif("wordcloud" in cMsg):
            await get_players_wordcloud(msg, cMsg, client)
        else:
            await client.send_message(msg.channel, "Unknown command")


        #await client.send_message(msg.channel, "test")
