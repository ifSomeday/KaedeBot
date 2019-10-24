import discord
from discord.ext import commands
from cogs import checks

class CsTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    @checks.me()
    async def hex(self, ctx, num: int):
        await ctx.send("{0}".format(hex(num)))

    
    @hex.error
    async def hexError(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("Unable to convert to hex.")
        else:
            print(error)


    @commands.command()
    @checks.me()
    async def dec(self, ctx, num):
        await ctx.send("{0}".format(int(num, 16)))

    
    @dec.error
    async def decError(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("Unable to convert to dec.")
        else:
            print(error)


    
def setup(bot):
    bot.add_cog(CsTools(bot))