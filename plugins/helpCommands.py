"""
Processes help requests
"""

def help_parser():
    pass



def od_help_parser(command, array=True):
    if(not array):
        command = command.lower().strip().split()
    #Assuming command starts post '!od help'
    if(command is None):
        return("this is theoretically impossible, <@133811493778096128>")
    elif(len(command) is 1):
        ##Should attempt to be alphabetical
        if(command[0] == 'add'):
            print("we are here")
            return("**SPECIFIER:**\n`!od add [steamid32|steamid64|opendota|dotabuff]`:\n\t* This command registers you and allows you to use the `!od` command\n\t* This command does *not* require the player name specified between `od` and the specifier\n\t* This command must be provided your steamID or a link to your opendota/dotabuff.\n\t\\* *Note*: it does not matter which form of identification you provide, as they all provide the same functionality")
        elif(command[0] == 'as'):
            return("**SPECIFIER:**\n`!od <name|me|my> as <hero name>`:\n\tThis command displays a quick overview with your stats as a specified hero\n\tFor a more detailed look, try `!od <name|me|my> summary 0 as <hero name>`\n\n**MODIFIER:**\n\tIn its modifier form, `as` can be used to restrict the results to those on a certain hero\n\tI.E. `!od my wordcloud as bane` would cause the wordcloud displayed to only include games in which the player picked bane")
        else:
            return("No help written for this command yet, bug my creator")
    else:
        return("Please only specify one specifier or modifier to get help with")
