import discord
from discord.ext import commands
import keys
import argparse
import os

## set up our arg parser
parser = argparse.ArgumentParser(description='KaedeBot for Discord')
parser.add_argument('--add-prefix', dest='prefix', action='store_const', const=True, default=False, help="automatically prefix each extension with 'cogs.'")
parser.add_argument('extensions', metavar='E', type=str, nargs='*', help='an extension to load, no arguments loads everything')

## load arguments
args = parser.parse_args()
loadList = args.extensions
prefix = args.prefix

## set up client
client = commands.Bot(command_prefix='!')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

## if we didnt specify extensions to load, prepare all for loading
if(len(loadList) == 0):
    print("No extensions specified, loading all...")
    path = "%s/cogs/" % os.getcwd()
    loadList = [ ("cogs.%s" % f).replace('.py', '') for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

## load extensions
for extension in loadList:
    if(extension and not extension.startswith("cogs.")):
        extension = "cogs." + extension
    try:
        client.load_extension(extension)
    except Exception as e:
        print("FAILED to load extension: %s\n%s" % (extension, e))
    else:
        print("Loaded extension: %s" % extension)


## start client
client.run(keys.TOKEN)