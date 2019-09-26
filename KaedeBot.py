import discord
from discord.ext import commands
import keys


client = commands.Bot(command_prefix='!')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

client.load_extension('cogs.dev')
client.load_extension('cogs.permissions')
client.load_extension('cogs.yuruYuri')
client.load_extension('cogs.runescape')

client.run(keys.TOKEN)