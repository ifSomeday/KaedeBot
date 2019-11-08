import discord
from discord.ext import commands
from cogs import checks


class Flavor(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self, ctx):
        if(self.bot.user.mentioned_in(ctx)):
            await ctx.add_reaction("🖕")


def setup(bot):
    bot.add_cog(Flavor(bot))