import discord
from discord.ext import commands

class RuneScape(commands.Cog):

    
    def __init__(self, bot):
        self.bot = bot


    def permissionCheck():
        async def predicate(ctx):
            perms = ctx.bot.get_cog('PermissionHandler')
            return(perms.is_enabled(ctx, perms.Permissions.CHATRESPONSE))
        return(commands.check(predicate))


    @commands.command(name="kc")
    @permissionCheck()
    async def kc(self, ctx, raid):

        if(raid.lower() == "cox"):
            response = "Your Chambers of Xeric kill count is {0}."
            if(ctx.author.id == 92997797795602432):
                response = response.format("300+")
            elif(ctx.author.id == 480310636086034433):
                response = response.format("8") + " scrub..."
            else:
                response = response.format("1")
            await ctx.send(response)
        
        else:
            await ctx.send("Kill count for activity `{0}` has not been implemented yet.".format(raid))



def setup(bot):
    bot.add_cog(RuneScape(bot))