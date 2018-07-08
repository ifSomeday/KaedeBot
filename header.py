import classes
import os
import sys

## DISCORD DEFs ##

base_draft_message = ("Round: **%s** Pick: **%s** (Overall: **%s**)\n"
    "Captain **%s** picks Player **%s**\nPlayer MMR: **%s** Team Avg: **%s**")

approved_deletetion_channels = ['133812880654073857', '246680759421763585', '134961597163634688', '314261304300929024', '308662797837795328', '308662818607988736', '326188941369671680', '102188880941285376']

anime_enough = ['133811493778096128', '146490789520867328', '127651622628229120', '225768977115250688', '162830306137735169', '85148771226234880']

chat_macro_translation = { classes.discordCommands.THUMBSUP : "Kyouko_Thumbs_up.gif", classes.discordCommands.AIRGUITAR : "Kyouko_air_guitar.gif",
    classes.discordCommands.CHEERLEADER : "Kyouko_Cheerleader.gif", classes.discordCommands.CHOCOLATE : "Kyouko_chocolate.gif",
    classes.discordCommands.TOMATO : "Kyouko_tomato.gif", classes.discordCommands.TRANSFORM : "Kyouko_transform.gif",
    classes.discordCommands.OMEGA_W : "abbaOmega.png"}

chat_command_translation = {"meme" : classes.discordCommands.SEND_MEME, "newmeme" : classes.discordCommands.NEW_MEME,
    "purgememes" : classes.discordCommands.PURGE_MEMES, "help" : classes.discordCommands.HELP,
    "bsjme" : classes.discordCommands.BSJ_MEME, "bsjname" : classes.discordCommands.BSJ_NAME,
    "twitter" : classes.discordCommands.TWITTER, "status" : classes.discordCommands.GET_STEAM_STATUS,
    "leaderboard" : classes.discordCommands.GET_STEAM_LEADERBOARD, "thumbsup" :  classes.discordCommands.THUMBSUP,
    "airguitar" :  classes.discordCommands.AIRGUITAR, "cheerleader" :  classes.discordCommands.CHEERLEADER,
    "chocolate" : classes.discordCommands.CHOCOLATE, "tomato" : classes.discordCommands.TOMATO,
    "transform" : classes.discordCommands.TRANSFORM, "oldmeme" : classes.discordCommands.SEND_OLD_MEME,
    "toggledraft" : classes.discordCommands.TOGGLE_DRAFT_MODE, "addchannel" : classes.discordCommands.ADD_CHANNEL_PERMISSION,
    "removechannel" : classes.discordCommands.REMOVE_CHANNEL_PERMISSION, "addserver" : classes.discordCommands.ADD_SERVER_PERMISSION,
    "removeserver" : classes.discordCommands.REMOVE_SERVER_PERMISISON, "featurestatus" : classes.discordCommands.PERMISSION_STATUS,
    "featurehelp" : classes.discordCommands.PERMISSION_HELP, "lobby" : classes.discordCommands.CREATE_LOBBY,
    "seal" : classes.discordCommands.CREATE_LOBBY, "bots" : classes.discordCommands.FREE_BOT_LIST,
    "supertest" : classes.discordCommands.TEST_COMMAND, "sealresults" : classes.discordCommands.SEAL_EMBEDS,
    "champs" : classes.discordCommands.HONORARY_CHAMPS, "shutdownbot" : classes.discordCommands.REQUEST_SHUTDOWN,
    "egift" : classes.discordCommands.EGIFT, "abbaomega" : classes.discordCommands.OMEGA_W,
    "decode" : classes.discordCommands.DECODE, "yy" : classes.discordCommands.YURU_YURI_FULL
}

HOME_SERVER = '133812880654073857'
MY_DISC_ID = '213099188584579072'
THE_FELLOWSHIP = '389285390005043212'

SHADOW_COUNCIL_FILE = os.getcwd() + "/datastores/shadow_council.pickle"
SHADOW_COUNCIL_CHANNEL = '463406700217499649'

YURU_YURI_HOME = "D:\\Pictures\\YuruYuriDump" if not sys.platform.startswith("linux") else (os.path.dirname(os.getcwd()) + "/YuruYuriPics") 

LEAGUE_IDS = ['5589', '5432', '8078']

##TODO: fill with captains
##TODO: dump to file so captains can specify other trustworth people

captain_steam_ids = {
    63813048 : "Tyrannosaurus X", 69243302 : "h!", 64908677 : "Danny", 96421460 : "Panda",

    83514255 : "Luke", 75419738 : "Toshino Kyouko !!", 100341395 : "Karen"
}

override_steam_ids = {
    ##TODO: look up treebeard
    63813048 : "Tyrannosaurus X", 69243302 : "h!", 64908677 : "Danny", 96421460 : "Panda",

    83514255 : "Luke", 75419738 : "Toshino Kyouko !!", 100341395 : "Karen"
}
