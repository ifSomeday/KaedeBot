import discord
from discord.ext import commands
from cogs import checks

import pickle
from aiostream import stream

class DevTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @checks.me()
    async def reload(self, ctx, *args):
        for arg in args:
            self.bot.reload_extension(arg)

    @reload.error
    async def reloadError(self, ctx, error):
        if(isinstance(error, commands.CheckFailure)):
            print("unauthorized attempt of reload")
        else:
            await ctx.send(error)

    @commands.command(hidden=True)
    @checks.me()
    async def load(self, ctx, *args):
        for arg in args:
            self.bot.load_extension(arg)

    @load.error
    async def loadError(self, ctx, error):
        if(isinstance(error, commands.CheckFailure)):
            print("unauthorized attempt of load")
        else:
            await ctx.send(error)

    @commands.command(hidden=True)
    @checks.me()
    async def dumpChannel(self, ctx, channelId : int):
        ch = self.bot.get_channel(channelId)
        #messages = []
        #i = 0
        messages = await ch.history(limit=None).flatten()
        messages = [{   "id" : message.id,
                        "author" : message.author.name,
                        "authorId" : message.author.id,
                        "timestamp" : message.created_at,
                        "content" : message.content,
                        "clean_content" : message.clean_content } for message in messages]
        #async for message in ch.history(limit=None, oldest_first=True):
        #    i += 1
        #    if(i % 10000 == 0):
        #        print("Processed {0} messages...".format(i)) 
        #    messages.append(message)
        #print("Processed {0} messages...".format(i)) 
        with open("{0}_dump.pickle".format(ch.name), "wb") as f:
            pickle.dump(messages, f)
            pass
        print("done")


    @commands.command(hidden=True)
    @checks.me()
    async def msg(self, ctx, channel : discord.TextChannel, *, text : str):
        await channel.send(text)
        if(isinstance(ctx.channel, discord.TextChannel)):
            await ctx.message.delete()


def setup(bot):
    bot.add_cog(DevTools(bot))