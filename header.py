import classes
import os

## DISCORD DEFs ##

base_draft_message = ("Round: **%s** Pick: **%s** (Overall: **%s**)\n"
    "Captain **%s** picks Player **%s**\nPlayer MMR: **%s** Team Avg: **%s**")

approved_deletetion_channels = ['133812880654073857', '246680759421763585', '134961597163634688', '314261304300929024', '308662797837795328', '308662818607988736', '326188941369671680', '102188880941285376']

anime_enough = ['133811493778096128', '146490789520867328', '127651622628229120', '225768977115250688', '162830306137735169', '85148771226234880']

chat_macro_translation = { classes.discordCommands.THUMBSUP : "Kyouko_Thumbs_up.gif", classes.discordCommands.AIRGUITAR : "Kyouko_air_guitar.gif",
    classes.discordCommands.CHEERLEADER : "Kyouko_Cheerleader.gif", classes.discordCommands.CHOCOLATE : "Kyouko_chocolate.gif",
    classes.discordCommands.TOMATO : "Kyouko_tomato.gif", classes.discordCommands.TRANSFORM : "Kyouko_transform.gif"}

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
    "removeserver" : classes.discordCommands.REMOVE_SERVER_PERMISISON, "featuresstatus" : classes.discordCommands.PERMISSION_STATUS,
    "featurehelp" : classes.discordCommands.PERMISSION_HELP
}

valid_permission_types = ["meme", "imagemacro", "deletion", "chatresponse", "floodcontrol", "draft"]

trusted_steam_ids = {
    ## Admins
    63813048 : "Tyrannosaurus X", 69243302 : "h!", 64908677 : "Danny", ##Treebeard : JK
    ## Captains
    102264839 : "Teresa", 96421460 : "Panda", 157808123 : "Smack", 66198763 : "MJJ",
    68025723 : "Kodos", 42291565 : "Crap", 17811638 : "Xag", 30999748 : "Dream",
    81718807 : "Truck", 316353271 : "StarEnd", 180022403 : "Henry", 1437926 : "Burgeoning",
    111747192 : "Mantis", 83611229 : "Blame", 3231124 : "Finite",
    ## Others
    83514255 : "Luke", 75419738 : "Toshino Kyouko !!", 100341395 : "Karen", 519770 : "Krenn"
}
