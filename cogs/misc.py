import discord
from discord.ext import commands
from cogs import checks

class NotLearnedEnough(commands.CheckFailure):
    pass

def any_role():
    async def predicate(ctx):
        if(len(ctx.author.roles) > 1):
            return(True)
        raise NotLearnedEnough("You must prove yourself first...")
    return(commands.check(predicate))

def dmdt():
    async def predicate(ctx):
        return(ctx.guild.id == 133812880654073857)
    return(commands.check(predicate))

class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    @any_role()
    @dmdt()
    async def scholar(self, ctx):
        r = ctx.guild.get_role(679457575283982366)
        m = ""
        if(r in ctx.author.roles):
            await ctx.author.remove_roles(r, reason="Removing access to the forbidden knowledge...")
            m = "The knowledge was too much for you...\nCome back when you are ready."
        else:
            await ctx.author.add_roles(r, reason="Granting access to the forbidden knowledge...")
            m = "You have been granted access to the forbidden knowledge...\nUse it wisely."
        try:
            await ctx.author.send(m)
        except:
            await ctx.message.add_reaction('✅')

    @scholar.error
    async def scholarError(self, ctx, error):
        if isinstance(error, NotLearnedEnough):
            await ctx.send(error)


def setup(bot):
    bot.add_cog(Misc(bot))