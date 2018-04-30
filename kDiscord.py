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
from plugins import dotaStats
from plugins import leagueResults
#import draftThread as dt
import markovChaining, keys, BSJ, os, header
from steam import SteamID
from concurrent.futures import ProcessPoolExecutor

def discBot(kstQ, dscQ, factoryQ, draftEvent):

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = discord.Client()
    markovChaining.init()
    ##Save Thread

    BsjFacts = BSJ.BSJText()

    draft_messages = []
    media_messages = {}

    cfg = classes.discordConfigHelper()


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
        Determines if a string is eligible for revivign through deletion feature
        """
        botLog(string)
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
            await client.send_message(cmd.args[0], cmd.args[1])

    ##Call and Response
    async def processMessage(client, message):
        """
        processes all incoming messages, and determines what action, if any, should be taken
        """
        if(client.user.mentioned_in(message)):
            if(message.server.id == header.HOME_SERVER or not message.mention_everyone):
                await client.add_reaction(message, "🖕")
        if(message.author.id == "305094311928922114" and (message.content.lower().contains("facebook") or message.content.lower().contains("fb"))):
            client.delete_message(message)
        if(len(message.attachments) > 0 and cfg.checkMessage("floodcontrol", message)):
            await spam_check("", msg=message, cb=None, command=None)
        if(message.channel.is_private and message.author.id == '133811493778096128'):
            await pm_command(msg=message)
        if(message.content.startswith('!') and (len(message.content) > 1)):
            ##TODO: prettier implementation of this:
            cMsg = message.content.lower()[1:].split()
            command = header.chat_command_translation[cMsg[0]] if cMsg[0] in header.chat_command_translation else classes.discordCommands.INVALID_COMMAND
            await client.send_typing(message.channel)
            await function_translation[command](cMsg, msg = message, command = command, client = client, cfg = cfg)
        if((ed.distance(message.content.lower(), 'can i get a "what what" from my homies?!') < 6) and cfg.checkMessage("chatresponse", message)):
            if(not str(message.author.id) == str(85148771226234880)):
                await client.send_message(message.channel, "what what")
            else:
                await client.send_message(message.channel, "quack quack")

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
            await client.send_message(client.get_channel(pm_channel), pm_content)

    async def send_meme(*args, **kwargs):
        """
        builds, validates, and sends a meme message
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):##any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
                table = markovChaining.nd if kwargs['command'] == classes.discordCommands.SEND_MEME else markovChaining.d
                i = 0
                meme_base = msg.content.split()
                st = time.time()
                meme = markovChaining.generateText3(table, builder = meme_base[1:])
                while((meme.strip().startswith("!") or len(meme.strip()) == 0) and i < 10):
                    i += 1
                    meme = markovChaining.generateText3(table, builder = [])
                    botLog("Invalid meme, rebuilding")
                if(meme.strip().startswith("!") or len(meme.strip()) == 0):
                    return
                et1 = time.time()
                meme = re.sub(r"@everyone", r"everyone", meme)
                for s in re.finditer(r"<@(\d+)>", meme):
                    meme = meme.replace(s.group(0), (await client.get_user_info(s.group(1))).name)
                et2 = time.time()
                botLog("build meme: " + str(et1 - st) + "\treplace: " + str(et2 - et1))
                await client.send_message(msg.channel, meme)

    async def add_meme(*args, **kwargs):
        """
        adds a new meme
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):
                markovChaining.addSingle3(msg.content[len("!newmeme"):], markovChaining.nd)
                await client.send_message(msg.channel, "new meme added, thanks!")

    async def purge_memes(*args, **kwargs):
        """
        purges the meme database. Command is currently disabled
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):
                    msg = kwargs['msg']
                    await client.send_message(msg.channel, "That command is currently disabled.")

    async def help_command(*args, **kwargs):
        """
        Displays an (outdated) help command
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "Use !meme to get a spicy meme\nUse !newmeme to add your own dank memes\nUse !MsjMe to get BSJ memes\nUse !BsjName to get your BSJ Name\nUse !twitter to see my twitter counterpart")

    async def bsj_meme(*args, **kwargs):
        """
        builds and sends a BSJ meme
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):
                await client.send_message(msg.channel, BsjFacts.getFact())

    async def bsj_name(*args, **kwargs):
        """
        Answers the biggest question in life... what does BSJ actually stand for?
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):
                await client.send_message(msg.channel, BsjFacts.bsjName())

    async def twitter(*args, **kwargs):
        """
        sends the bot's twitter
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("chatresponse", msg)):
                await client.send_message(msg.channel, "Follow my twitter counterpart !!\nhttps://twitter.com/NameIsBot")

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
            await client.delete_message(msg)
            if('command' in kwargs):
                command = kwargs['command']
                await client.send_file(msg.channel, os.getcwd() + "/dataStores/" + header.chat_macro_translation[command])

    async def addRemovePermission(*args, **kwargs):
        """
        Adds or removes a permission to a server or channel
        Handles request validation and overrides
        """
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            command = kwargs['command']
            if(msg.author.server_permissions.manage_server or msg.author.id == '133811493778096128'):
                perm_type = cMsg[1].strip().lower()
                if(perm_type in cfg.valid_permission_types):
                    ##TODO: better, but can be simplified
                    append_type = "Server"
                    obj_id = msg.server.id
                    if(command == classes.discordCommands.ADD_CHANNEL_PERMISSION or command == classes.discordCommands.REMOVE_CHANNEL_PERMISSION):
                        append_type = "Channel"
                        obj_id = msg.channel.id
                    if(len(cMsg) > 2):
                        if(cMsg[2] == msg.server.id or (cMsg[2] in list(chan.id for chan in msg.server.channels))):
                            obj_id = cMsg[2]
                        else:
                            obj_id = None
                            if(msg.author.id == '133811493778096128'):
                                await client.send_message(msg.channel, "overriding server exclusion...")
                            else:
                                await client.send_message(msg.channel, "ID must be this server, or a channel in this server !!")
                            return
                    if(command == classes.discordCommands.ADD_CHANNEL_PERMISSION or command == classes.discordCommands.ADD_SERVER_PERMISSION):
                        cfg.addElement(perm_type + append_type, obj_id)
                    else:
                        cfg.delElement(perm_type + append_type, obj_id)
                elif(perm_type == "all"):
                    ##TODO: better, but can be simplified
                    if(command == classes.discordCommands.ADD_CHANNEL_PERMISSION or command == classes.discordCommands.ADD_SERVER_PERMISSION):
                        cfg.addAll(msg, command == classes.discordCommands.ADD_CHANNEL_PERMISSION)
                    elif(command == classes.discordCommands.REMOVE_CHANNEL_PERMISSION or command == classes.discordCommands.REMOVE_SERVER_PERMISISON):
                        cfg.removeAll(msg, command == classes.discordCommands.REMOVE_CHANNEL_PERMISSION)
                else:
                    await client.send_message(msg.channel, "Invalid feature. More information available through !featureHelp")
                    return
                cfg.saveDict()
                await client.send_message(msg.channel, "Done !!")
            else:
                await client.send_message(msg.channel, "You need the *Manage Server* Discord permission to do that !!")

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
        if('msg' in kwargs and (kwargs['msg'].author.server_permissions.manage_server or kwargs['msg'].author.id == '133811493778096128')):
            msg = kwargs['msg']
            server = msg.server
            cMsg = args[0]
            if(len(args[0]) > 1):
                try:
                    server = client.get_server(cMsg[1])
                except:
                    server = msg.server
            channel = msg.channel
            server_channels = list(msg.server.channels)
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
            await client.send_message(msg.channel, output)

    async def permissionHelp(*args, **kwargs):
        if('msg' in kwargs and kwargs['msg'].author.server_permissions.manage_server):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "use commands `!addchannel <feature> [<channel id>]`, `!addserver <feature>`, `!removehannel <feature> [<channel id>]` and `!removeserver <feature>` to set up the bot." +
            "\n\nYou must have the Discord permission *Manage Server* to use these commands.\n\nIf using the optional `<channel id>`, the channel must be in the current server.\n\nObviously features can be enabled serverwide, or by channel. " +
            "\n\nThe valid feature types are as follows:\n\t* `meme` handles the `!meme` and `!bsjMe` related commands\n\t* `imagemacro` handles the various *Yuru Yuri* related image macro commands" +
            "\n\t* `deletion` turns on the deletion tracking feature\n\t* `chatresponse` turns on the flavor chat responses\n\t* `floodcontrol` turns on the anti image spam feature (bot needs permission to delete messages)" +
            "\n\t* `draft` makes the channel a draft channel (currently disabled)\n\nUse command `!featureStatus` to see the bots current configuration")

    async def broadcast_draft_pick(*args, **kwargs):
        if('cmd' in kwargs):
            botLog("here")
            cmd = kwargs['cmd']
            #bChannel = client.get_channel('320033818083983361')
            resr = await build_draft_message(row = cmd.args[0])
            #bChannel = client.get_channel('303070764276645888')
            bChannel = client.get_channel('315212408740380672')
            draft_messages.append(await client.send_message(bChannel, resr))

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
            draft_messages[playerIndex] = await client.edit_message(message, resr)

    async def broadcast_lobby(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            total_members = 0
            for member in cmd.args[0].members:
                if(member.team == 0 or member.team == 1):
                    total_members += 1
            sid = SteamID(cmd.args[1].account_id)
            await client.send_message(client.get_channel('133812880654073857'), "Inhouse looking for members.\nLooking for " + str(10 - total_members) + " more players\nContact " + cmd.args[1].persona_name + " on steam.\n(<" + sid.community_url +">)")

    async def toggle_draft(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            acceptable_ids= ["133811493778096128", "85148771226234880", "166390891920097280", "96665903051046912", "127651622628229120"]
            if(msg.author.id in acceptable_ids):
                if(draftEvent.is_set()):
                    draftEvent.clear()
                else:
                    draftEvent.set()
                await client.send_message(msg.channel, "draft mode is now " + ("enabled" if draftEvent.is_set() else "disabled"))
            else:
                await client.send_message(msg.channel, "you don't have permission to do that :(")

    async def broadcast_match_res(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            bChannel = client.get_channel('213086692683415552')
            ##TODO: add this configurable
            await client.send_message(bChannel, cmd.args[0])

    async def create_lobby(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(msg.channel.id == '321900902497779713' and sys.platform.startswith("linux")):
                return
            ##TODO: verify here
            ##TODO: get name
            await client.send_message(msg.channel, "Creating lobby...")
            lobby_name =  msg.author.name + " lobby"
            lobby_password = ''.join(random.choice(string.ascii_lowercase) for i in range(0, 6))
            factoryQ.put(classes.command(classes.botFactoryCommands.SPAWN_SLAVE, [lobby_name, lobby_password, msg]))

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
                await client.send_message(msg.channel, "No bots are currently available")
            else:
                await client.send_message(msg.channel, ("Currently available bots are: " + s))

    async def spam_check(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            command = kwargs['command']
            callback = kwargs['cb']
            cMsg = args[0]
            if(msg.author.id in media_messages and not msg.author.id == header.MY_DISC_ID):
                if(time.time() - media_messages[msg.author.id] < 60):
                    await client.delete_message(msg)
                    await client.send_message(msg.channel, msg.author.mention + " please refrain from spamming !!")
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
            if(msg.author.id == "127651622628229120" or msg.author.id == "133811493778096128"):
                ##Logo Links
                first_logo = "https://riki.dotabuff.com/t/l/17jEbIlSzl8.png"
                ##STILL NEED
                second_logo = "https://riki.dotabuff.com/t/l/16Tt2pSKWYU.png"
                ##STILL NEED
                third_logo_1 = "https://riki.dotabuff.com/t/l/17ObokfO12z.png"
                third_logo_2 = "https://riki.dotabuff.com/t/l/16EPjSj8HFF.png"

                ##Create embeds
                first = create_seal_embed("Sweet Jazz Esports", "First place", first_logo, "Clare" ,["FierySnake", "Mediocre", "Flying Monkey", "Fulcrum", "Ferris Euler"], colour = discord.Colour.gold())
                second = create_seal_embed("Knights of Lil B", "Second place", second_logo, "Satan" ,["Natnap", "Truckwaffle", "659", "MichaelJJackson", "Big Fella", "Polo"], colour = discord.Colour.dark_grey())
                third = create_seal_embed("Stud Squad", "Tied third/fourth place", third_logo_1, "UltraGunner" , ["Amane", "BigAug", "Zoompa", "Poiuys", "Blakkout"], colour = discord.Colour.dark_gold())
                fourth = create_seal_embed("Let Me See That Krussy", "Tied third/fourth place", third_logo_2, "Danny" , ["Anbokr", "dnm-", "Aku", "Rock", "Deadprez"], colour = discord.Colour.dark_gold())

                ##send embeds
                await client.send_message(msg.channel, "", embed = first)
                await client.send_message(msg.channel, "", embed = second)
                await client.send_message(msg.channel, "", embed = third)
                await client.send_message(msg.channel, "", embed = fourth)

    async def honorary_champs(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            acceptable_ids= ["112786843476439040", "109854391783149568", "85604200356007936", "133811493778096128", "166390891920097280", "166362994735972352"]
            if(msg.author.id in acceptable_ids and cfg.checkMessage("chatresponse", msg)):
                logo = "https://cdn.discordapp.com/attachments/321372241830871040/322176298913103873/seal_clubbers_interface.png"
                champs = create_seal_embed("Seal Clubbers", "Honorary champions", logo, "Truckwaffle", ["waves", "Richie", "MANGO GIRL", "Krenn", "Will"], colour = discord.Colour.gold())
                await client.send_message(msg.channel, " ", embed = champs)
                await client.delete_message(msg)

    async def lobby_create_message(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            msg = cmd.args[2]
            await client.send_message(msg.channel, "Lobby created for " + msg.author.mention + "\nName: `" + cmd.args[0] + "`\nPassword: `" + cmd.args[1] + "`")


    async def bot_error_message(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            msg = cmd.args[0]
            await client.send_message(msg.channel, "No bots are currently available")

    async def shutdown_bot(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(msg.author.id  == '133811493778096128'):
                factoryQ.put(classes.command(classes.botFactoryCommands.SHUTDOWN_BOT, []))

    async def clean_shutoff(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            botLog("Tables saved")
            markovChaining.dumpAllTables()
            botLog("closing connection")
            client.logout()

    async def egift_pp(*args, **kwargs):
        if('msg'in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "Please consider donating to Planned Parenthood:\nhttps://www.plannedparenthood.org/")

    async def test_function(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(not msg.author.id == '133811493778096128'):
                return
            mess = []
            count = 0
            for channel in client.get_server('308515912653340682').channels:
                botLog(channel)
                try:
                    async for message in client.logs_from(channel, limit=sys.maxsize):
                        mess.append(message)
                except:
                    botLog("Unable to get channel info")
            with open("newpickle", "wb") as f:
                pickle.dump(mess, f)
            botLog("done")

    async def decode(*args, **kwargs):
        if("msg" in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            try:
                target_msg = await client.get_message(msg.channel, cMsg[1])
            except:
                botLog("cant get")
            messageList = re.findall(r"<:(\w+):\d+>", target_msg.content)
            resp = "\n".join(messageList)
            resp = " ".join(re.sub(r'([a-z])([A-Z])', r'\1 \2', resp).split())
            await client.delete_message(msg)
            await client.send_message(msg.author, resp)



    async def invalid_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkAny(msg)):
                await client.send_message(msg.channel, "invalid command")

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
        classes.discordCommands.EGIFT : egift_pp, classes.discordCommands.OMEGA_W : image_macro, classes.discordCommands.DECODE : decode}

    async def messageHandler(kstQ, dscQ):
        await client.wait_until_ready()
        while(not client.is_closed):
            while(dscQ.qsize() > 0):
                cmd = dscQ.get()
                await function_translation[cmd.command](cmd = cmd)
            await asyncio.sleep(1)

    async def saveTables():
        await client.wait_until_ready()
        while(not client.is_closed):
            markovChaining.dumpAllTables()
            botLog("saving")
            await asyncio.sleep(1800)

    async def league_results():
        await client.wait_until_ready()
        while(not client.is_closed):
            await leagueResults.new_match_results(client)
            await asyncio.sleep(120)

    async def logIp():
        await client.wait_until_ready()
        while(not client.is_closed):
            async with aiohttp.get("https://api.ipify.org") as r:
                ip = await r.text()
                ip_channel = client.get_channel("439161581209649155")
                last = client.logs_from(ip_channel, limit=1)
                async for msg in last:
                    if(not msg.content == ip):
                        kyouko = await client.get_user_info("133811493778096128")
                        await client.send_message(ip_channel, kyouko.mention)
                        await client.send_message(ip_channel, ip)
            await asyncio.sleep(240)

    @client.event
    async def on_reaction_add(reaction, user):
        if(reaction.emoji == '🤖' and not reaction.message.author == client.user and not reaction.me and not reaction.message.content.startswith("!")):
            if(not any((r.me and r.emoji == '🤖') for r in reaction.message.reactions)):
                await client.add_reaction(reaction.message, '🤖')
                markovChaining.addSingle3(reaction.message.content, markovChaining.nd)
                if(cfg.checkMessage("meme", reaction.message)):
                    await client.send_message(reaction.message.channel, "Thanks, " + user.mention + " meme added from message by " + reaction.message.author.name)
            else:
                botLog("already reacted")

    @client.event
    async def on_ready():
        botLog("discord bot Online")
        await client.change_presence(game=discord.Game(name='Yuru Yuri San Hai !!'))

    @client.event
    async def on_message_delete(message):
        ##TEMP joke on aura
        if(message.server.id == "133812880654073857" and message.author.id == "195348139216076800"):
            await client.send_message(message.channel, message.author.mention + ' deleted message: "' + message.content + '"')
            return
        if(cfg.checkMessage("deletion", message) and (not message.author.id == header.MY_DISC_ID)):
            if(deleteFilter(message.content)):
                return
            if(message.server.id == '308515912653340682' and not message.author.id == "117446235715010569"):
                return
            if(message.author.id == "305094311928922114" and (message.content.lower().contains("facebook") or message.content.lower().contains("fb"))):
                return
            await client.send_message(message.channel, message.author.mention + ' deleted message: "' + message.content + '"')

    @client.event
    async def on_message(message):
        await processMessage(client, message)

    @client.event
    async def on_member_join(member):
        if(member.id == "133811493778096128"):
            for role in member.server.roles:
                print(role.name + " " +role.id)
                if(role.id == "203917322010886144"):
                    await client.add_roles(member, role)

    ##TODO: switch to entirely plugins approach
    header.chat_command_translation, function_translation = dotaStats.init(header.chat_command_translation, function_translation)
    header.chat_command_translation, function_translation = leagueResults.init(header.chat_command_translation, function_translation)

    client.loop.create_task(messageHandler(kstQ, dscQ))
    client.loop.create_task(saveTables())
    client.loop.create_task(league_results())
    client.loop.create_task(logIp())
    client.run(keys.TOKEN)

if(__name__ == "__main__"):
    kstQ = queue.Queue()
    dscQ = queue.Queue()
    factoryQ = queue.Queue()
    draft_event = threading.Event()
    #drft = threading.Thread(target = dt.main, args=(kstQ, dscQ, draft_event,))
    #drft.start()
    discBot(kstQ, dscQ, factoryQ, draft_event)
