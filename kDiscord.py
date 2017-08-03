import asyncio
import random, time
import edit_distance as ed
import discord
import queue
import praw
import threading
import classes
import markovChaining, keys, BSJ, os, header
from steam import SteamID
from concurrent.futures import ProcessPoolExecutor

def discBot(kstQ, dscQ, draftEvent):

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
        try:
            print("DiscordBot: " +  str(text), flush = True)
        except:
            print(sBot.name + ": Logging error. Probably some retard name", flush = True)

    async def sendMessage(channel, string):
        await client.send_message(channel, string)

    async def cmdSendMsg(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            await sendMessage(cmd.args[0], cmd.args[1])

    ##Call and Response
    async def processMessage(client, message):
        if(len(message.attachments) > 0 and cfg.checkMessage("floodcontrol", message)):
            await spam_check("", msg=message, cb=None, command=None)

        if(message.channel.is_private and message.author.id == '133811493778096128'):
            await pm_command(msg=message)

        if(message.content.startswith('!') and (len(message.content) > 1)):
            ##TODO: prettier implementation of this:
            cMsg = message.content.lower()[1:].split()
            command = header.chat_command_translation[cMsg[0]] if cMsg[0] in header.chat_command_translation else classes.discordCommands.INVALID_COMMAND
            if((not command == classes.discordCommands.TOGGLE_DRAFT_MODE) and (message.server.id == '315211723231461386') or (message.server.id == '308515912653340682')):
                return
            await client.send_typing(message.channel)
            await function_translation[command](cMsg, msg = message, command = command)

        if((ed.distance(message.content.lower(), 'can i get a "what what" from my homies?!') < 6) and cfg.checkMessage("chatresponse", message)):
            if(not str(message.author.id) == str(85148771226234880)):
                await client.send_message(message.channel, "what what")
            else:
                await client.send_message(message.channel, "quack quack")

    async def pm_command(*args, **kwargs):
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
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):##any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
                table = markovChaining.nd if kwargs['command'] == classes.discordCommands.SEND_MEME else markovChaining.d
                await client.send_message(msg.channel, markovChaining.generateText(table, builder = args[0][1:]))
            else:
                await client.send_message(msg.channel, "Please use that command in an appropriate channel.")

    async def add_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            markovChaining.addSingle(msg.content[len("!newmeme"):], markovChaining.nd)
            await client.send_message(msg.channel, "new meme added, thanks!")

    async def purge_memes(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "That command is currently disabled.")

    async def help_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "Use !meme to get a spicy meme\nUse !newmeme to add your own dank memes\nUse !MsjMe to get BSJ memes\nUse !BsjName to get your BSJ Name\nUse !twitter to see my twitter counterpart")

    async def bsj_meme(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):
                await client.send_message(msg.channel, BsjFacts.getFact())
            else:
                await client.send_message(msg.channel, "Please use that command in an appropriate channel.")

    async def bsj_name(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(cfg.checkMessage("meme", msg)):
                await client.send_message(msg.channel, BsjFacts.bsjName())
            else:
                await client.send_message(msg.channel, "Please use that command in an appropriate channel.")

    async def twitter(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "Follow my twitter counterpart !!\nhttps://twitter.com/NameIsBot")

    async def steam_status(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            kstQ.put(classes.command(classes.steamCommands.STATUS_4D, [msg.channel]))

    async def steam_leaderboard(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            sMsg = msg.content.split()
            if(len(sMsg) > 1):
                spots =  sMsg[1]
            else :
                spots = 3
            kstQ.put(classes.command(classes.steamCommands.LEADERBOARD_4D, [msg.channel, str(spots)]))

    async def image_macro_wrapper(*args, **kwargs):
        if('msg' in kwargs):
            if(cfg.checkMessage("imagemacro", kwargs['msg'])):
                await spam_check(args[0], msg=kwargs['msg'], command=kwargs['command'], cb=image_macro)

    async def image_macro(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            await client.delete_message(msg)
            if('command' in kwargs):
                command = kwargs['command']
                await client.send_file(msg.channel, os.getcwd() + "/dataStores/" + header.chat_macro_translation[command])
            else:
                await client.send_message(msg.channel, "Sorry, you aren't anime enough. Please contact a weeb if you believe this is in error.")


    async def addRemovePermission(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            cMsg = args[0]
            command = kwargs['command']
            if(msg.author.server_permissions.manage_server):
                perm_type = cMsg[1].strip().lower()
                if(perm_type in header.valid_permission_types):
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
                    await client.send_message(msg.channel, "Invalid feature. More information available through !permissionHelp")
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
        if('msg' in kwargs and kwargs['msg'].author.server_permissions.manage_server):
            msg = kwargs['msg']
            server = msg.server
            channel = msg.channel
            server_channels = list(msg.server.channels)
            ##TODO: these are possible with clever use of for .. if .. in a single line
            glob_feat = []
            glob_feat, meme_feat = featureListHelper(server, server_channels, glob_feat, [], "meme")
            glob_feat, macro_feat = featureListHelper(server, server_channels, glob_feat, [], "imagemacro")
            glob_feat, dele_feat = featureListHelper(server, server_channels, glob_feat, [], "deletion")
            glob_feat, chat_feat = featureListHelper(server, server_channels, glob_feat, [], "chatresponse")
            glob_feat, flood_feat = featureListHelper(server, server_channels, glob_feat, [], "floodcontrol")
            glob_feat, draft_feat = featureListHelper(server, server_channels, glob_feat, [], "draft")
            output = ""
            if(len(glob_feat) > 0):
                output += "\t* Serverwide features enabled:"
                for f in glob_feat:
                    output += (" `" + f + "`,")
                output = output[:-1]
            output = featureAppend(output, meme_feat, "meme")
            output = featureAppend(output, macro_feat, "iamgemacro")
            output = featureAppend(output, dele_feat, "deletion")
            output = featureAppend(output, chat_feat, "chatresponse")
            output = featureAppend(output, flood_feat, "floodcontrol")
            output = featureAppend(output, draft_feat, "draft")
            if(len(output) > 0):
                output = "Feature Status:\n" + output
            else:
                output = "Nothing currently enabled in this server"
            await client.send_message(msg.channel, output)

    async def permissionHelp(*args, **kwargs):
        if('msg' in kwargs and kwargs['msg'].author.server_permissions.manage_server):
            msg = kwargs['msg']
            await client.send_message(msg.channel, "use commands `!addchannel <feature> [<channel id>]`, `!addserver <feature>`, `!removehannel <feature> [<channel id>]` and `!removeserver <feature>` to set up the bot." +
            "\n\nYou must have the Discord permission *Manage Server* to use this command.\n\nIf using the optional `<channel id>`, the channel must be in the current server.\n\nObviously features can be enabled serverwide, or by channel. " +
            "\n\nThe valid feature types are as follows:\n\t* `meme` handles the `!meme` and `!bsjMe` related commands\n\t* `imagemacro` handles the various *Yuru Yuri* related image macro commands" +
            "\n\t* `deletion` turns on the deletion tracking feature\n\t* `chatresponse` turns on the flavor chat responses\n\t* `floodcontrol` turns on the anti image spam feature (bot needs permission to delete messages)" +
            "\n\t* `draft` makes the channel a draft channel (currently disabled)\n\nUse command `!featureStatus` to see the bots current configuration")

    async def broadcast_draft_pick(*args, **kwargs):
        if('cmd' in kwargs):
            cmd = kwargs['cmd']
            #bChannel = client.get_channel('320033818083983361')
            resr = await build_draft_message(row = cmd.args[0])
            bChannel = client.get_channel('315212408740380672')
            draft_messages.append(await client.send_message(bChannel, resr))

    async def build_draft_message(*args, **kwargs):
        row = kwargs['row']
        start = "----------\n" if(not int(row[0]) == 1) else ""
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
        return
        if('msg' in kwargs):
            msg = kwargs['msg']
            if(msg.author.id == '127651622628229120' or msg.author.id == '133811493778096128' or msg.author.id == '85148771226234880'):
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
            await client.send_message(bChannel, cmd.args[0])

    async def spam_check(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
            command = kwargs['command']
            callback = kwargs['cb']
            cMsg = args[0]
            if(not any(name in msg.channel.name for name in ['meme', 'meming', 'afk'])):
                if(msg.author.id in media_messages and not msg.author.id == '213099188584579072'):
                    if(time.time() - media_messages[msg.author.id] < 60):
                        await client.delete_message(msg)
                        await client.send_message(msg.channel, msg.author.mention + " please refrain from spamming !!")
                else:
                    media_messages[msg.author.id] = time.time()
                    if(callback):
                        await callback(cMsg, msg=msg, command=command)
            elif(callback):
                await callback(cMsg, msg=msg, command=command)

    async def invalid_command(*args, **kwargs):
        if('msg' in kwargs):
            msg = kwargs['msg']
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
        classes.discordCommands.PERMISSION_STATUS : permissionStatus, classes.discordCommands.PERMISSION_HELP : permissionHelp}

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

    @client.event
    async def on_ready():
        botLog("discord bot Online")
        await client.change_presence(game=discord.Game(name='Yuru Yuri San Hai !!'))

    @client.event
    async def on_message_delete(message):
        if(cfg.checkMessage("deletion", message) and (not message.author.id == '213099188584579072')):
            if(message.content.startswith("!") and (message.content[1:].split()[0].lower() in header.chat_command_translation)):
                return
            await client.send_message(message.channel, message.author.mention + ' deleted message: "' + message.content + '"')

    @client.event
    async def on_message(message):
        await processMessage(client, message)

    client.loop.create_task(messageHandler(kstQ, dscQ))
    client.loop.create_task(saveTables())
    client.run(keys.TOKEN)

if(__name__ == "__main__"):
    kstQ = queue.Queue()
    dscQ = queue.Queue()
    draft_event = threading.Event()
    discBot(kstQ, dscQ, draft_event)
