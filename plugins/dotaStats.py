from plugins import opendota
from steam import SteamID
from wordcloud import WordCloud
import os
import pickle
import discord
import re
import classes
import difflib
import datetime

PLAYER_DICT_NAME = os.getcwd() + "/dataStores/ddDict.pickle"
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

async def get_players_wordcloud(msg, cMsg, client):
    player = None
    if(len(cMsg) == 2 or (any(x in cMsg for x in ["me", "my"]))):
        botLog("for author")
        if(msg.author.name in player_dict):
            player = player_dict[msg.author.name]
        else:
            await client.send_message(msg.channel, "You are not registered. Please add your account with `!od add [opendota|dotabuff|steam_id32|steam_id64]`")
            return
    else:
        botLog("for user")
        wc_index = cMsg.index("wordcloud")
        if(not wc_index == len(cMsg) - 1):
            await client.send_message(msg.channel, "Invalid format.\nTry `!od [me|my|player_name] wordcloud`")
            return
        else:
            botLog("entering")
            input_name = ' '.join(msg.content[1:].split()[1 : wc_index]).strip()
            if(input_name in player_dict):
                player = player_dict[input_name]
            else:
                possible_matches = difflib.get_close_matches(input_name, player_dict.keys())
                botLog(possible_matches)
                if(len(possible_matches) is 0):
                    await client.send_message(msg.channel, "Unable to find player. Are they registered?")
                    return
                else:
                    await client.send_message(msg.channel, "Unable to match exact player. Using approximation '" + possible_matches[0] +"'\nIf this is incorrect, check your spelling and make sure they are registered.")
                    player = player_dict[possible_matches[0]]
    botLog("preparing get")
    r = od.get_players_wordcloud(player["steam"].as_32)
    wordcloud_freq = r["my_word_counts"]
    botLog("got")
    wc = WordCloud(background_color="white", sacle=2, prefer_horizontal=0.5).generate_from_frequencies(wordcloud_freq)
    img = wc.to_image()
    botLog("made image")
    await client.send_message(msg.channel, fp=img, filename="wordcloud.png" )

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

async def player_on_hero(msg, cMsg, client):
    on_index = cMsg.index("on")
    player = None
    botLog(on_index)
    botLog(cMsg)
    if(on_index == 1 or (on_index == 2 and cMsg[1] == "me")):
        if(not msg.author.name in player_dict):
            await client.send_message(msg.channel, "You are not registered. Please add your account with `!od add [opendota|dotabuff|steam_id32|steam_id64]`")
            return
        player = player_dict[msg.author.name]
    elif(on_index < len(cMsg) - 1):
        input_name = ' '.join(msg.content[1:].split()[1 : on_index]).strip()
        if(input_name in player_dict):
            player = player_dict[input_name]
        else:
            possible_matches = difflib.get_close_matches(input_name, player_dict.keys())
            botLog(possible_matches)
            if(len(possible_matches) is 0):
                await client.send_message(msg.channel, "Unable to find player. Are they registered?")
                return
            else:
                await client.send_message(msg.channel, "Unable to match exact player. Using approximation '" + possible_matches[0] +"'\nIf this is incorrect, check your spelling and make sure they are registered.")
                player = player_dict[possible_matches[0]]
    hero = ' '.join(cMsg[on_index + 1:])
    possible_matches = difflib.get_close_matches(hero, hero_dict.keys())
    botLog(possible_matches)
    if(len(possible_matches) is 0):
        await client.send_message(msg.channel, "Please spell hero name correctly")
        return
    hero = hero_dict[possible_matches[0]]
    r = od.get_players_heroes(player["steam"].as_32, params = {"hero_id" :hero["id"]})
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
    emb.add_field(name = "Winrate", value = str(round(res["win"] * 100 / res["games"], 2)) + "%", inline = True)
    emb.add_field(name = "Wins", value = str(res["win"]), inline = True)
    emb.add_field(name = "Loses", value = str(res["games"] - res["win"]), inline = True)
    emb.colour = discord.Colour.green()
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

##     ## ####  ######   ######
###   ###  ##  ##    ## ##    ##
#### ####  ##  ##       ##
## ### ##  ##   ######  ##
##     ##  ##        ## ##
##     ##  ##  ##    ## ##    ##
##     ## ####  ######   ######

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

def init(chat_command_translation, function_translation):
    function_translation[classes.discordCommands.OPENDOTA] = open_dota_main
    chat_command_translation["od"] = classes.discordCommands.OPENDOTA
    global player_dict
    player_dict = load_player_dict()
    return(chat_command_translation, function_translation)


async def open_dota_main(*args, **kwargs):
    if('msg' in kwargs):
        client = kwargs['client']
        msg = kwargs['msg']
        cMsg  = args[0]
        if(not msg.server.id == 213086692683415552):
            return
        sender, players, failed, success = get_players_message(msg)
        if(cMsg[1] == "add"):
            res = await associate_player(msg, cMsg, msg.author, client)
            if(not res):
                await client.send_message(msg.channel, "Unable to register.\nPlease provide your opendota/dotabuff link, or steam ID32/ID64\n`!od add [opendota|dotabuff|steam_id32|steam_id64]`")
        elif(cMsg[1] == "me" and len(cMsg) == 2):
            await display_self_association(msg, cMsg, client)
        elif("on" in cMsg):
            await player_on_hero(msg, cMsg, client)
        elif("wordcloud" in cMsg):
            botLog("getting wordcloud")
            await get_players_wordcloud(msg, cMsg, client)
        else:
            pass



        #await client.send_message(msg.channel, "test")
