from plugins import opendota
import os
import pickle
import discord
import re
import classes
import difflib
import datetime
from steam import SteamID

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

def load_player_dict():
    if(os.path.isfile(PLAYER_DICT_NAME)):
        with open(PLAYER_DICT_NAME, "rb") as f:
            return(pickle.load(f))

def save_player_dict():
    with open(PLAYER_DICT_NAME, "wb") as f:
        pickle.dump(player_dict, f)

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

async def associate_player(msg, cMsg, user, client):
    if(len(cMsg) > 2):
        player_id = None
        acceptable_links = ["opendota.com/players", "dotabuff.com/players", "dotabuff.com/esports/players"]
        if(any(x in cMsg[2] for x in acceptable_links)):
            botLog("found in link form")
            match = re.search(url_matcher, cMsg[2])
            player_id = match.group(1)
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
            botLog("no info provided")
            return(False)

async def display_self_association(msg, cMsg, client):
    if(msg.author.name in player_dict):
        player = player_dict[msg.author.name]
        r = od.get_players(player["steam"].as_32)
        emb = steam_acc_embed_od(r)
        await client.send_message(msg.channel, "Your account is currently associated with: ", embed = emb)

async def player_on_hero(msg, cMsg, client):
    on_index = cMsg.index("on")
    player = None
    if(on_index == 1):
        player = player_dict[msg.author.name]
    elif(on_index < len(cMsg) - 1):
        pass
    hero = cMsg[on_index + 1]
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

def hero_card_embed(res, player, hero):
    emb = discord.Embed()
    emb.title = player["discord"].name + " on " + hero["localized_name"]
    emb.type = "rich"
    ##emb.description = ""TODO: date time stuff
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


async def open_dota_main(*args, **kwargs):
    if('msg' in kwargs):
        client = kwargs['client']
        msg = kwargs['msg']
        cMsg  = args[0]
        sender, players, failed, success = get_players_message(msg)
        if(cMsg[1] == "add"):
            botLog("adding player")
            res = await associate_player(msg, cMsg, msg.author, client)
            if(not res):
                await client.send_message(msg.channel, "Please provide your opendota, dotabuff, steam id32, or steam id64")
        elif(cMsg[1] == "me"):
            await display_self_association(msg, cMsg, client)
        elif("on" in cMsg):
            await player_on_hero(msg, cMsg, client)
        else:
            pass



        #await client.send_message(msg.channel, "test")
