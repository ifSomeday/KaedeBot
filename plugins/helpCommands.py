"""
Processes help requests
"""

def help_parser():
    pass



def od_help_parser(command, array=True):
    if(not array):
        command = command.lower().strip().split()
    #Assuming command starts post '!od help'
    out = []
    if(command is None):
        return(["this is theoretically impossible, <@133811493778096128>"])
    elif(len(command) is 1):
        ##SPECIFIERS
        if(command[0] == 'add'):
            out.append("**SPECIFIER:**\n`!od add [steamid32|steamid64|opendota|dotabuff]`:\n\t* This command registers you and allows you to use the `!od` command\n\t* This command does *not* require the player name specified between `od` and the specifier\n\t* This command must be provided your steamID or a link to your opendota/dotabuff.\n\t\\* *Note*: it does not matter which form of identification you provide, as they all provide the same functionality")
        elif(command[0] == 'as'):
            out.append("**SPECIFIER:**\n`!od <name|me|my> as <hero name>`:\n\t* This command displays a quick overview with your stats as a specified hero\n\t* For a more detailed look, try `!od <name|me|my> summary 0 as <hero name>`")
        elif(command[0] == 'last'):
            out.append("**SPECIFIER:**\n`!od <name|me|my> last`\n\t* This command displays info on the given users last match.\n\t* Modifiers can be used to refine the request, such as `!od my last as Naga Siren`.\n\t\\* *Note*: If the match has not been parsed, the bot will request a parse from OpenDota for you.")
        elif(command[0] == 'match'):
            out.append("**SPECIFIER:**\n`!od match <matchID|opendota|dotabuff>`\n\t* This command displays info on the requested match.\n\t* The match can be specified with a Match id, an OpenDota link, or a DotaBuff link\n\t\\* *Note*: If the match has not been parsed, the bot will request a parse from OpenDota for you.")
        elif(command[0] == "profile"):
            out.append("**SPECIFIER**\n`!od <name|me|my> profile`\n\t* This command displays the steam profile associated with the given user.")
        elif(command[0] == "summary"):
            out.append("**SPECIFIER:**\n`!od <name|me|my> summary [# of games]`\n\t* This command displays a summary of the last few games for the given user.\n\t* The number of games defaults to 20, but any number of games can be specified. A value of 0 or -1 results in all-time stats.\n\t\\* *Note*: The embed will display a max of 10 games. The info, however, will properly reflect the number of games requested")
        elif(command[0] == "update"):
            out.append("**SPECIFIER:**\n`!od update`\n\t* This command updates your profile. This will fix any issues with displaying the incorrect profile pictures.")
        elif(command[0] == "wardmap"):
            out.append("**SPECIFIER:**\n`!od <name|me|my> wardmap`\n\t* This command generates and display a heatmap that shows where the specified user places their wards.")
        elif(command[0] == "wordcloud"):
            out.append("**SPECIFIER:**\n`!od <name|me|my> wordcloud`\n\t* This command generates and displays a wordcloud for the words said by specified user in all chat.\n\t* Larger words are ones that are said more frequently.")
        ##MODIFIERS
        if(command[0] == 'as'):
            out.append("\n\n**MODIFIER:**\n`as <hero name>`\n\t* In its modifier form, `as` can be used to restrict the results to those on a certain hero\n\t* I.E. `!od my wordcloud as bane` would cause the wordcloud displayed to only include games in which the player picked bane.")
        elif(command[0] == 'against'):
            out.append("**MODIFIER:**\n`against <hero name>`\n\t* This modifier limits the results to those where the specified hero was on the opposing team.")
        elif(command[0] == 'days'):
            out.append("**MODIFIER:**\n`days <number>`\n\t* This modifier limits the results to the specified number of days.")
        elif(command[0] == 'on'):
            out.append("**MODIFIER:**\n`on <radiant|dire>`\n\t* This modifier limits the results to the specified side (Radiant or Dire).")
        elif(command[0] == 'recent'):
            out.append("**MODIFIER:**\n`recent <number>`\n\t* This modifier limits the results to the specified number of games.")
        elif(command[0] == 'with'):
            out.append("**MODIFIER:**\n`with <hero name>`\n\t* This modifier limits the results to those where the specified hero was on the user's team.")
        if(len(out) == 0):
            out.append("No help written for this command yet, bug my creator")
        return(out)
    else:
        return(["Please only provide one specifier or modifier"])
