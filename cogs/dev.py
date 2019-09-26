import discord
from discord.ext import commands
from cogs import checks

class DevTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
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

    @commands.command()
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

def setup(bot):
    bot.add_cog(DevTools(bot))