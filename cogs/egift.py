import discord
from discord.ext import commands
from cogs import checks

class Egift(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command("egift", help="Displays the donation message")
    @checks.permissionCheck("EGIFT")
    async def egift(self, ctx):
        await ctx.send("Please consider donating to Planned Parenthood:\nhttps://www.plannedparenthood.org/")
        

def setup(bot):
    bot.add_cog(Egift(bot))