import asyncio
import random, time, string
import edit_distance as ed
import discord
import aiohttp
import queue
import praw
import threading
import classes
import re
import sys
import pickle
import operator
import keys, BSJ, os, header
#import draftThread as dt
from steam import SteamID
from concurrent.futures import ProcessPoolExecutor
import tweepy
import logging
import datetime
import io

import zmq
from plugins import zmqutils

##COGS
from cogs import yuruYuri
from cogs import permissions

##plugins
from plugins import shadowCouncilSecret
#from plugins import dotaStats
#from plugins import leagueResults
from plugins import roleCommands
from plugins import develop
from plugins import commitlog
from plugins import youtubeRewind

kstQ = queue.Queue()
dscQ = queue.Queue()
factoryQ = queue.Queue()
draft_event = threading.Event()

logging.basicConfig(level=logging.INFO)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

shadow_council_lock = asyncio.Lock()

client = discord.ext.commands.Bot(command_prefix="%")
##Save Thread

BsjFacts = BSJ.BSJText()

draft_messages = []
media_messages = {}

cfg = classes.discordConfigHelper()

tweepy_auth = tweepy.OAuthHandler(keys.CONSUMER_KEY, keys.CONSUMER_SECRET)
tweepy_auth.set_access_token(keys.ACCESS_TOKEN, keys.ACCESS_SECRET)

tweepy_api = tweepy.API(tweepy_auth)


def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("DiscordBot: " +  str(text), flush = True)
    except:
        print("DiscordBot: Logging error. Probably some retard name", flush = True)

def deleteFilter(string):
    """
    Determines if a string is eligible for reviving through deletion feature
    """
    if(string.startswith("!") and (string[1:].split()[0].lower() in header.chat_command_translation)):
        return(True)
    if(not re.search(keys.SECRET_REGEX_FILTER, string) == None or not re.search(keys.SECRET_REGEX_FILTER2, string) == None):
        return(True)
    if("🐼" in string or "卐" in string):
        #...
        return(True)
    if(string.lower().startswith(".")):
        return(True)
    return(False)

async def cmdSendMsg(*args, **kwargs):
    """
    Sends a discord message. For use by external threads, utilizing the Discord command queue
    """
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        await cmd.args[0].send(cmd.args[1])

##Call and Response
async def processMessage(client, message):
    """
    processes all incoming messages, and determines what action, if any, should be taken
    """
    if(client.user.mentioned_in(message)):
        if(message.guild.id == header.HOME_SERVER or not message.mention_everyone):
            botLog("reaction to self mention")
            await message.add_reaction("🖕")
    
    ##try to add to rewind lib
    try:
        await youtubeRewind.onMessageProcessor(message)
    except Exception as e:
        botLog(e)
        pass

    if(len(message.attachments) > 0 and cfg.checkMessage("floodcontrol", message)):
        botLog("Checking floodcontrol")
        await spam_check("", msg=message, cb=None, command=None)
    
    if(isinstance(message.channel, discord.abc.PrivateChannel) and message.author.id == 133811493778096128):
        botLog("recieved PM")
        await pm_command(msg=message)
    
    if(message.channel.id == header.SHADOW_COUNCIL_CHANNEL):
        botLog("Shadow council message")
        await shadow_council(msg=message)
    
    if(message.author.id == 305094311928922114 and any(x in message.clean_content.lower() for x in header.CHRIS_FILTER )):
        await message.delete_message()
        return

    if(message.content.startswith('!') and (len(message.content) > 1)):
        botLog("Got command")

        cMsg = message.content.lower()[1:].split()
        command = header.chat_command_translation[cMsg[0]] if cMsg[0] in header.chat_command_translation else classes.discordCommands.INVALID_COMMAND
        botLog("Command is " + cMsg[0])
        await message.channel.trigger_typing()
        await function_translation[command](cMsg, msg = message, command = command, client = client, cfg = cfg)
    
    if((ed.distance(message.content.lower(), 'can i get a "what what" from my homies?!') < 6) and cfg.checkMessage("chatresponse", message)):
        botLog("What What from my homies")
        if(not str(message.author.id) == str(85148771226234880)):
            await message.channel.send("what what")
        else:
            await message.channel.send("quack quack")

async def pm_command(*args, **kwargs):
    """
    processes all incoming PMS, and determines what action, if any, should be taken
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        split_string = msg.content.find(' ')
        pm_channel = msg.content[0:split_string]
        pm_content = msg.content[(split_string + 1):]
        pm_content_array = pm_content.split()
        pm_content = ''
        for word in pm_content_array:
            if word.startswith('&'):
                try:
                    int(word[1:])
                    word = "<@" + word + ">"
                except Exception as e:
                    print(e)
                    pass
            pm_content += (word + " ")
        await client.get_channel(pm_channel).send(pm_content)




async def purge_memes(*args, **kwargs):
    """
    purges the meme database. Command is currently disabled
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(cfg.checkMessage("meme", msg)):
                msg = kwargs['msg']
                await msg.channel.send("That command is currently disabled.")

async def help_command(*args, **kwargs):
    """
    Displays an (outdated) help command
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        await msg.channel.send("Use !meme to get a spicy meme\nUse !newmeme to add your own dank memes\nUse !MsjMe to get BSJ memes\nUse !BsjName to get your BSJ Name\nUse !twitter to see my twitter counterpart")

async def bsj_meme(*args, **kwargs):
    """
    builds and sends a BSJ meme
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(cfg.checkMessage("meme", msg)):
            await msg.channel.send(BsjFacts.getFact())

async def bsj_name(*args, **kwargs):
    """
    Answers the biggest question in life... what does BSJ actually stand for?
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(cfg.checkMessage("meme", msg)):
            await msg.channel.send(BsjFacts.bsjName())

async def twitter(*args, **kwargs):
    """
    sends the bot's twitter
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(cfg.checkMessage("chatresponse", msg)):
            await msg.channel.send("Follow my twitter counterpart !!\nhttps://twitter.com/NameIsBot")

async def steam_status(*args, **kwargs):
    """
    Requests the steam bot return its status. Response from steam thread is placed into the Discord command queue
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(cfg.checkMessage("chatresponse", msg)):
            kstQ.put(classes.command(classes.steamCommands.STATUS_4D, [msg.channel]))

async def steam_leaderboard(*args, **kwargs):
    """
    Requests the steam inhouse leaderboard. Resposne from steam thread is placed into the Discord command queue
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        sMsg = msg.content.split()
        if(len(sMsg) > 1):
            spots =  sMsg[1]
        else :
            spots = 3
        kstQ.put(classes.command(classes.steamCommands.LEADERBOARD_4D, [msg.channel, str(spots)]))

async def image_macro_wrapper(*args, **kwargs):
    """
    Wrapper for image macro commands. Determines what image is being requested
    """
    if('msg' in kwargs):
        if(cfg.checkMessage("imagemacro", kwargs['msg'])):
            if(cfg.checkMessage("floodcontrol", kwargs['msg'])):
                await spam_check(args[0], msg=kwargs['msg'], command=kwargs['command'], cb=image_macro)
            else:
                await image_macro(args[0], msg=kwargs['msg'], command=kwargs['command'])

async def image_macro(*args, **kwargs):
    """
    Loads and sends the actual image macro
    """
    if('msg' in kwargs):
        msg = kwargs['msg']
        await msg.delete_message()
        if('command' in kwargs):
            command = kwargs['command']
            await msg.channel.send(file=discord.File(os.getcwd() + "/dataStores/" + header.chat_macro_translation[command]))


def featureListHelper(server, server_channels, glob_feat, single_feat, feat_type):
    if(server.id in cfg.config_dict[feat_type + "Server"]):
        glob_feat.append(feat_type)
    else:
        for ch in server_channels:
            if(ch.id in cfg.config_dict[feat_type + "Channel"]):
                single_feat.append(ch.name)
    return(glob_feat, single_feat)

def featureAppend(output, cList, fType):
    if(len(cList) == 0):
        return(output)
    else:
        output += ("\n\t* `" + fType + "` enabled in:" )
        for c in cList:
            output += (" " + c + ",")
        output = output[:-1]
        return(output)


async def permissionStatus(*args, **kwargs):
    if('msg' in kwargs and (kwargs['msg'].author.guild_permissions.manage_guild or kwargs['msg'].author.id == 133811493778096128)):
        msg = kwargs['msg']
        server = msg.guild
        cMsg = args[0]
        if(len(args[0]) > 1):
            try:
                server = client.get_guild(cMsg[1])
            except:
                server = msg.guild
        channel = msg.channel
        server_channels = list(msg.guild.channels)
        ##TODO: these are possible with clever use of for .. if .. in a single line
        glob_feat = []
        output = ""
        ch_output = ""
        for feature in cfg.valid_permission_types:
            glob_feat, feat = featureListHelper(server, server_channels, glob_feat, [], feature)
            ch_output = featureAppend(ch_output, feat, feature)
        if(len(glob_feat) > 0):
            output += "\t* Serverwide features enabled:"
            for f in glob_feat:
                output += (" `" + f + "`,")
            output = output[:-1]
        output += ch_output
        if(len(output) > 0):
            output = "Feature Status:\n" + output
        else:
            output = "Nothing currently enabled in this server"
        await msg.channel.send(output)

async def broadcast_draft_pick(*args, **kwargs):
    if('cmd' in kwargs):
        botLog("here")
        cmd = kwargs['cmd']
        #bChannel = client.get_channel(320033818083983361)
        resr = await build_draft_message(row = cmd.args[0])
        #bChannel = client.get_channel(303070764276645888)
        bChannel = client.get_channel(315212408740380672)
        draft_messages.append(await bChannel.send(resr))

async def build_draft_message(*args, **kwargs):
    row = kwargs['row']
    start = ""
    if(int(row[2]) == 1):
        start = "===============\n**ROUND " + str(row[1]) + "**\n===============\n"
    else:
        start = "----------\n"
    return(start + (header.base_draft_message % (str(row[1]), str(row[2]), str(row[0]), str(row[4]), str(row[5]), str(row[6]), str(row[7]))))

async def update_draft_message(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        playerIndex = int(cmd.args[0][0]) - 1
        message = draft_messages[playerIndex]
        resr = await build_draft_message(row = cmd.args[0])
        draft_messages[playerIndex] = await message.edit_message(resr)

async def broadcast_lobby(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        total_members = 0
        for member in cmd.args[0].members:
            if(member.team == 0 or member.team == 1):
                total_members += 1
        sid = SteamID(cmd.args[1].account_id)
        await client.get_channel(133812880654073857).send("Inhouse looking for members.\nLooking for " + str(10 - total_members) + " more players\nContact " + cmd.args[1].persona_name + " on steam.\n(<" + sid.community_url +">)")

async def toggle_draft(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        acceptable_ids= [133811493778096128, 85148771226234880, 166390891920097280, 96665903051046912, 127651622628229120]
        if(msg.author.id in acceptable_ids):
            if(draftEvent.is_set()):
                draftEvent.clear()
            else:
                draftEvent.set()
            await msg.channel.send("draft mode is now " + ("enabled" if draftEvent.is_set() else "disabled"))
        else:
            await msg.channel.send("you don't have permission to do that :(")

async def broadcast_match_res(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        bChannel = client.get_channel(213086692683415552)
        ##TODO: add this configurable
        await bChannel.send(cmd.args[0])

async def create_lobby(*args, **kwargs):
    return
    # if('msg' in kwargs):
    #     cMsg = args[0]
    #     msg = kwargs['msg']
    #     if(msg.channel.id == 321900902497779713 and sys.platform.startswith("linux")):
    #         return
    #     lobbyArgs = re.findall(r'"(.*?)"', " ".join(cMsg))
    #     await msg.channel.send("Creating lobby...")

    #     info = classes.gameInfo()

    #     info.lobbyName =  msg.author.name + " lobby"
    #     if(len(lobbyArgs) > 0):
    #         info.lobbyName = lobbyArgs[0]

    #     info.lobbyPassword = ''.join(random.choice(string.ascii_lowercase) for i in range(0, 6))
    #     if(len(lobbyArgs) > 1):
    #         info.lobbyPassword = lobbyArgs[1] 
        
    #     info.discordMessage = msg

    #     factoryQ.put(classes.command(classes.botFactoryCommands.SPAWN_SLAVE, [info]))


async def lobby_create_message(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        msg = cmd.args[2]
        botLog(str(cmd.args[:]))
        await msg.channel.send("Lobby created for " + msg.author.mention + " by " + cmd.args[3].name + "\nName: `" + cmd.args[0] + "`\nPassword: `" + cmd.args[1] + "`")


async def request_bot_list(*args, **kwargs):
    if('msg' in kwargs):
        factoryQ.put(classes.command(classes.botFactoryCommands.LIST_BOTS_D, [kwargs['msg']]))

async def print_bot_list(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        msg = cmd.args[0]
        l = cmd.args[1]
        s = ', '.join(l)
        if(len(l) is 0):
            await msg.channel.send("No bots are currently available")
        else:
            await msg.channel.send(("Currently available bots are: " + s))

async def spam_check(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        command = kwargs['command']
        callback = kwargs['cb']
        cMsg = args[0]
        if(msg.author.id in media_messages and not msg.author.id == header.MY_DISC_ID):
            if(time.time() - media_messages[msg.author.id] < 60):
                await msg.delete_message()
                await msg.channel.send(msg.author.mention + " please refrain from spamming !!")
                return
        media_messages[msg.author.id] = time.time()
        if(callback):
            await callback(cMsg, msg=msg, command=command)

def create_seal_embed(team, place, logo_url, captain, player_list, colour = None):
    emb = discord.Embed()
    emb.title = team
    emb.type = "rich"
    emb.description = place
    emb.set_thumbnail(url = logo_url)
    emb.add_field(name = "Captain", value = captain, inline = False)
    player_str = ""
    for i in range(0, len(player_list)):
        player_str += ("(" + str(i + 1) + ") - " + player_list[i] + "\n")
    emb.add_field(name = "Players", value = player_str, inline = False)
    if(not colour is None):
        emb.colour = colour
    return(emb)

async def seal_embeds(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        ##tree, me
        if(msg.author.id == 127651622628229120 or msg.author.id == 133811493778096128):
            ##Logo Links
            first_logo = "https://riki.dotabuff.com/t/l/17jEbIlSzl8.png"
            ##STILL NEED
            second_logo = "https://riki.dotabuff.com/t/l/16Tt2pSKWYU.png"
            ##STILL NEED
            third_logo_1 = "https://riki.dotabuff.com/t/l/17ObokfO12z.png"
            third_logo_2 = "https://riki.dotabuff.com/t/l/16EPjSj8HFF.png"

            ##Create embeds
            first = create_seal_embed("Sweet Jazz Esports", "First place", first_logo, "Clare" ,["FierySnake", "Mediocre", "Flying Monkey", "Fulcrum", "Ferris Euler"], colour = discord.Colour.gold())
            second = create_seal_embed("Knights of Lil B", "Second place", second_logo, "Satan" ,["Natnap", "Truckwaffle", 659, "MichaelJJackson", "Big Fella", "Polo"], colour = discord.Colour.dark_grey())
            third = create_seal_embed("Stud Squad", "Tied third/fourth place", third_logo_1, "UltraGunner" , ["Amane", "BigAug", "Zoompa", "Poiuys", "Blakkout"], colour = discord.Colour.dark_gold())
            fourth = create_seal_embed("Let Me See That Krussy", "Tied third/fourth place", third_logo_2, "Danny" , ["Anbokr", "dnm-", "Aku", "Rock", "Deadprez"], colour = discord.Colour.dark_gold())

            ##send embeds
            await msg.channel, "".send(embed = first)
            await msg.channel, "".send(embed = second)
            await msg.channel, "".send(embed = third)
            await msg.channel, "".send(embed = fourth)

async def honorary_champs(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        acceptable_ids= [112786843476439040, 109854391783149568, 85604200356007936, 133811493778096128, 166390891920097280, 166362994735972352]
        if(msg.author.id in acceptable_ids and cfg.checkMessage("chatresponse", msg)):
            logo = "https://cdn.discordapp.com/attachments/321372241830871040/322176298913103873/seal_clubbers_interface.png"
            champs = create_seal_embed("Seal Clubbers", "Honorary champions", logo, "Truckwaffle", ["waves", "Richie", "MANGO GIRL", "Krenn", "Will"], colour = discord.Colour.gold())
            await msg.channel, " ".send(embed = champs)
            await msg.delete_message()

async def bot_error_message(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        msg = cmd.args[0]
        await msg.channel.send("No bots are currently available")

async def shutdown_bot(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(msg.author.id  == 133811493778096128):
            factoryQ.put(classes.command(classes.botFactoryCommands.SHUTDOWN_BOT, []))

async def clean_shutoff(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']
        botLog("Tables saved")
        botLog("closing connection")
        client.logout()

async def pm_decoded_message(*args, **kwargs):
    if("msg" in kwargs):
        msg = kwargs["msg"]
        with io.StringIO(msg.clean_content) as f:
            await msg.author.send("Raw message attached below:", file=discord.File(f, msg.id + ".txt"))

async def my_color(*args, **kwargs):
    if("msg" in kwargs):
        msg = kwargs["msg"]
        if(cfg.checkMessage("chatresponse", msg)):
            await msg.channel.send("Your color is %s in RGB" % str(msg.author.color.to_tuple()))

async def test_function(*args, **kwargs):
    return
    #     msg = kwargs['msg']
    #     if(not msg.author.id == 133811493778096128):
    #         return
    #     mess = []
    #     count = 0
    #     for server in client.guilds:
    #         for channel in server.channels:
    #             botLog(channel)
    #             try:
    #                 async for message in client.logs_from(channel, limit=sys.maxsize):
    #                     mess.append(message)
    #             except:
    #                 botLog("Unable to get channel info")
    #     with open("newpickle", "wb") as f:
    #         pickle.dump(mess, f)
    #     botLog("done")

async def decode(*args, **kwargs):
    if("msg" in kwargs):
        msg = kwargs['msg']
        cMsg = args[0]
        try:
            target_msg = await msg.channel.fetch_message(cMsg[1])
        except:
            botLog("cant get")
        messageList = re.findall(r"<:(\w+):\d+>", target_msg.content)
        resp = "\n".join(messageList)
        resp = " ".join(re.sub(r'([a-z])([A-Z])', r'\1 \2', resp).split())
        await msg.delete_message()
        await msg.author.send(resp)


async def sc_lookup(*args, **kwargs):
    if('cmd' in kwargs):
        cmd = kwargs['cmd']

        msg_id = str(cmd.args[0])
        resp = cmd.args[1]

        channel = client.get_channel(header.SHADOW_COUNCIL_CHANNEL)
        
        try:
            msg = await channel.fetch_message(msg_id)
            botLog("found message")
            resp.put(msg)

        except Exception as e:
            print(e)
            botLog("unable to find message")
            resp.put(None)

        return


async def sc_update(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        cMsg = args[0]
        if(msg.author.id == header.GWENHWYFAR):   
            await msg.delete_message()
            await __unban_action(unbanAll=True)

            serv = client.get_guild(header.HOME_SERVER)
            role = None
            for r in serv.roles:
                if(r.id == 476129555774439426):
                    role = r

            await role.edit(mentionable=True)
            await client.get_channel(header.SHADOW_COUNCIL_CHANNEL).send(role.mention + " ".join(cMsg[1:]))
            await role.edit(mentionable=False)


async def invalid_command(*args, **kwargs):
    if('msg' in kwargs):
        msg = kwargs['msg']
        if(cfg.checkAny(msg)):
            pass
            ##await msg.channel.send("invalid command")

function_translation = {classes.discordCommands.SEND_MEME : send_meme, classes.discordCommands.NEW_MEME : add_meme,
    classes.discordCommands.PURGE_MEMES : purge_memes, classes.discordCommands.HELP : help_command,
    classes.discordCommands.BSJ_MEME : bsj_meme, classes.discordCommands.BSJ_NAME : bsj_name ,
    classes.discordCommands.TWITTER : twitter, classes.discordCommands.GET_STEAM_STATUS : steam_status,
    classes.discordCommands.GET_STEAM_LEADERBOARD : steam_leaderboard, classes.discordCommands.THUMBSUP : image_macro_wrapper,
    classes.discordCommands.AIRGUITAR : image_macro_wrapper, classes.discordCommands.CHEERLEADER : image_macro_wrapper,
    classes.discordCommands.INVALID_COMMAND : invalid_command, classes.discordCommands.BROADCAST : cmdSendMsg, classes.discordCommands.CHOCOLATE : image_macro_wrapper,
    classes.discordCommands.TOMATO : image_macro_wrapper, classes.discordCommands.TRANSFORM : image_macro_wrapper,
    classes.discordCommands.BROADCAST_LOBBY : broadcast_lobby, classes.discordCommands.SEND_OLD_MEME : send_meme,
    classes.discordCommands.BROADCAST_DRAFT_PICK : broadcast_draft_pick, classes.discordCommands.TOGGLE_DRAFT_MODE : toggle_draft,
    classes.discordCommands.UPDATE_DRAFT_PICK : update_draft_message, classes.discordCommands.BROADCAST_MATCH_RESULT : broadcast_match_res,
    classes.discordCommands.ADD_CHANNEL_PERMISSION : addRemovePermission, classes.discordCommands.REMOVE_CHANNEL_PERMISSION : addRemovePermission,
    classes.discordCommands.ADD_SERVER_PERMISSION : addRemovePermission, classes.discordCommands.REMOVE_SERVER_PERMISISON : addRemovePermission,
    classes.discordCommands.PERMISSION_STATUS : permissionStatus, classes.discordCommands.PERMISSION_HELP : permissionHelp,
    classes.discordCommands.CREATE_LOBBY : create_lobby, classes.discordCommands.FREE_BOT_LIST : request_bot_list,
    classes.discordCommands.BOT_LIST_RET : print_bot_list, classes.discordCommands.TEST_COMMAND : test_function,
    classes.discordCommands.SEAL_EMBEDS : seal_embeds, classes.discordCommands.HONORARY_CHAMPS : honorary_champs,
    classes.discordCommands.LOBBY_CREATE_MESSAGE : lobby_create_message, classes.discordCommands.REQUEST_SHUTDOWN : shutdown_bot,
    classes.discordCommands.SHUTDOWN_BOT : clean_shutoff, classes.discordCommands.NO_BOTS_AVAILABLE : bot_error_message,
    classes.discordCommands.EGIFT : egift_pp, classes.discordCommands.OMEGA_W : image_macro, classes.discordCommands.DECODE : decode,
    classes.discordCommands.YURU_YURI_FULL : yuru_yuri, classes.discordCommands.SHADOW_COUNCIL_UNBAN_ALL : shadow_council_unban_all,
    classes.discordCommands.SC_LOOKUP : sc_lookup, classes.discordCommands.NEW_CHALLENGE : new_challenge,
    classes.discordCommands.SC_UPDATE : sc_update, classes.discordCommands.MY_COLOR : my_color, classes.discordCommands.KC : kill_count}

async def messageHandler(kstQ, dscQ):
    await client.wait_until_ready()
    try:
        while(not client.is_closed()):
            while(dscQ.qsize() > 0):
                botLog("got command")
                cmd = dscQ.get()
                await function_translation[cmd.command](cmd = cmd)
            await asyncio.sleep(1)
    except Exception as e:
        botLog("Exception in messageHandler method")
        botLog(str(e))



async def league_results():
    await client.wait_until_ready()
    try:
        while(not client.is_closed()):
            await leagueResults.new_match_results(client)
            await asyncio.sleep(30)
    except Exception as e:
        botLog("Exception in leagueResults method")
        botLog(str(e))


async def logIp():
    await client.wait_until_ready()
    try:
        while(not client.is_closed()):
            async with aiohttp.get("https://api.ipify.org") as r:
                ip = await r.text()
                ip_channel = client.get_channel(439161581209649155)
                last = client.logs_from(ip_channel, limit=1)
                async for msg in last:
                    if(not msg.content == ip):
                        kyouko = await client.fetch_user(133811493778096128)
                        await ip_channel.send(kyouko.mention)
                        await ip_channel.send(ip)
            await asyncio.sleep(240)
    except Exception as e:
        botLog("Exception in logIp")
        botLog(str(e))

async def githubTracker():
    await client.wait_until_ready()
    try:
        while(not client.is_closed()):
            await commitlog.latest_commit(client)
            await asyncio.sleep(600)
    except Exception as e:
        botLog("Exception in githubTracker:")
        botLog(str(e))

async def tree_diary():
    await client.wait_until_ready()

    try:
        ##get channel
        channel = client.get_channel(321900902497779713)
        if(sys.platform.startswith('linux')):
            channel = client.get_channel(443169808482172968)
        while(not client.is_closed()):
            try:
                ##set up tweet tracking
                lastTweet = 0
                filePath = os.getcwd() + "/dataStores/lastTreeTweet.pickle"
                if(os.path.isfile(filePath)):
                    with open(filePath, "rb") as f:
                        lastTweet = pickle.load(f)
                currLastTweet = lastTweet

                ##iterate through status
                for status_short in tweepy.Cursor(tweepy_api.user_timeline, screen_name="@treebearddoto").items():
                    status = tweepy_api.get_status(status_short._json["id"], tweet_mode='extended')
                    if(status._json["id"] <= lastTweet):
                        break
                    else:

                        ##set up embed
                        print(status._json["full_text"])
                        text = re.sub(r'http\S+', '', status._json["full_text"], flags=re.MULTILINE)
                        emb = discord.Embed()
                        emb.description=text
                        emb.set_author(name="Treebeard (@Treebearddoto)", url="https://twitter.com/Treebearddoto", icon_url=status._json["user"]["profile_image_url"])
                        emb.set_footer(text="Twitter", icon_url="https://cdn.discordapp.com/attachments/321900902497779713/443205044222033921/Twitter_Social_Icon_Circle_Color.png")
                        emb.url="https://twitter.com/Treebearddoto/status/" + str(status._json["id"])
                        if("media" in status._json["entities"]):
                            media = status._json["entities"]["media"]
                            if(len(media) > 0):
                                emb.set_image(url=media[0]["media_url"])
                        await channel.send(embed=emb)
                        currLastTweet = max(currLastTweet, status._json["id"])

                        ##save last tweet
                        with open(filePath, "wb") as f:
                            pickle.dump(currLastTweet, f)
            except:
                print("WILLR: twitter error:", sys.exc_info())
            
            ##wait 2 minutes
            await asyncio.sleep(120)
    except Exception as e:
        botLog("Exception in treediary")
        botLog(str(e))

async def checkQueueZMQ():
    try:
        senderId, cmd = zmqutils.recvObjRouter(socket, zmq.DONTWAIT)
    except zmq.error.Again as e:
        ##botLog("Nothing to recv")
        pass
    except Exception as e:
        botLog("Unexpected recv exception: %s" % str(e))
    await asyncio.sleep(0.5)

@client.event
async def on_reaction_add(reaction, user):
    if(reaction.emoji == '🤖' and not reaction.message.author == client.user and not reaction.me and not reaction.message.content.startswith("!")):
        if(not any((r.me and r.emoji == '🤖') for r in reaction.message.reactions)):
            await reaction.message.add_reaction('🤖')
            #markovChaining.addSingle3(reaction.message.content, markovChaining.nd)
            if(cfg.checkMessage("meme", reaction.message)):
                await reaction.message.channel.send("Thanks, " + user.mention + " meme added from message by " + reaction.message.author.name)
        else:
            botLog("already reacted")
    elif(reaction.emoji == '❓' and reaction.message.channel.id == header.SHADOW_COUNCIL_CHANNEL):
        await pm_decoded_message(msg=reaction.message)

@client.event
async def on_ready():
    botLog("discord bot Online")
    await client.change_presence(activity=discord.Game(name='api.kaedebot.com'))

@client.event
async def on_message_delete(message):
    if(not message.author.id == header.GWENHWYFAR):
        botLog(message.author.name + " deleted message '" + message.clean_content + "' from channel " + message.channel.name + " in " + message.guild.name)
    if(cfg.checkMessage("deletion", message) and (not message.author.id == header.GWENHWYFAR)):
        if(deleteFilter(message.content)):
            return
        if(message.guild.id == 308515912653340682 and not message.author.id == 117446235715010569):
            return
        if(message.author.id == 305094311928922114 and any(x in message.clean_content.lower() for x in header.CHRIS_FILTER)):
            return
        await message.channel.send(message.author.mention + ' deleted message: "' + message.content + '"')

@client.event
async def on_message(message):
    await processMessage(client, message)

@client.event
async def on_member_join(member):
    if(member.id == 133811493778096128):
        for role in member.guild.roles:
            if(role.id == 203917322010886144):
                await member.add_roles(role)
    
    ##BAN CL
    if(member.id == 390261725145989120 and member.guild.id == 133812880654073857):
        member.ban()


@client.command()
async def test(ctx, arg1, arg2):
    await ctx.send('You passed {} and {}'.format(arg1, arg2))

context = zmq.Context()
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://*:9002")


##TODO: switch to entirely plugins approach
#header.chat_command_translation, function_translation = dotaStats.init(header.chat_command_translation, function_translation)
#header.chat_command_translation, function_translation = leagueResults.init(header.chat_command_translation, function_translation)
header.chat_command_translation, function_translation = roleCommands.init(header.chat_command_translation, function_translation)
header.chat_command_translation, function_translation = develop.init(header.chat_command_translation, function_translation)
header.chat_command_translation, function_translation = youtubeRewind.init(header.chat_command_translation, function_translation)

#client.loop.create_task(messageHandler(kstQ, dscQ))
#client.loop.create_task(saveTables())
#client.loop.create_task(league_results())
#client.loop.create_task(logIp())
##client.loop.create_task(tree_diary())
#client.loop.create_task(shadow_council_unban())
#client.loop.create_task(githubTracker())
#client.loop.create_task(checkQueueZMQ())

client.add_cog(yuruYuri.YuruYuri(client))
client.add_cog(permissions.Permissions(client))
#client.add_command(test)

client.run(keys.TOKEN)

if(__name__ == "__main__"):
    pass
    #drft = threading.Thread(target = dt.main, args=(kstQ, dscQ, draft_event,))
    #drft.start()
    #discBot(kstQ, dscQ, factoryQ, draft_event)
