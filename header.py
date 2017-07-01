import classes

## DISCORD DEFs ##

base_draft_message = ("Round: **%s** Pick: **%s** (Overall: **%s**)\n"
    "Captain **%s** picks Player **%s**\nPlayer MMR: **%s** Team Avg: **%s**")

approved_deletetion_channels = ['133812880654073857', '246680759421763585', '134961597163634688', '314261304300929024', '308662797837795328', '308662818607988736', '326188941369671680']

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
    "toggledraft" : classes.discordCommands.TOGGLE_DRAFT_MODE}
