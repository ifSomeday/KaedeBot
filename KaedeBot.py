import discord
from discord.ext import commands
import keys


client = commands.Bot(command_prefix='!')

def me():
    async def predicate(ctx):
        return (ctx.author.id == 133811493778096128)
    return(commands.check(predicate))

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.command()
@me()
async def reload(ctx, *args):
    for arg in args:
        client.reload_extension(arg)

@reload.error
async def reloadError(ctx, error):
    if(isinstance(error, commands.CheckFailure)):
        print("unauthorized attempt of reload")
    else:
        await ctx.send(error)

@client.command()
@me()
async def load(ctx, *args):
    for arg in args:
        client.load_extension(arg)

@load.error
async def loadError(ctx, error):
    if(isinstance(error, commands.CheckFailure)):
        print("unauthorized attempt of load")
    else:
        await ctx.send(error)

client.load_extension('cogs.permissions')
client.load_extension('cogs.yuruYuri')
client.load_extension('cogs.runescape')

client.run(keys.TOKEN)