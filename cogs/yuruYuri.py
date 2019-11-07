import discord
from discord.ext import commands
import random
import header
import os

from cogs import checks

class YuruYuri(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        

    @commands.command(name="yy", help="Displays an image or gif from the anime Yuru Yuri\nPlease report questionable content to the developer.")
    @checks.permissionCheck('IMAGEMACRO')
    async def yy(self, ctx, *args):
        cMsg = args[0] if args else None
        files = os.listdir(header.YURU_YURI_HOME)
        image = 0
        try:
            image = int(cMsg[1])
            if(not (image >= 0 and image < len(files))):
                raise(ValueError("A number outside the bounderies [0,"+ str(len(files)) + "] has been picked" ))
        except:
            await ctx.channel.send("Unknown input, picking random image")
            image = random.randint(0, len(files) - 1)
        await ctx.channel.send("Yuru Yuri Image " + str(image) + "/" + str(len(files)))
        await ctx.channel.send(file=discord.File(header.YURU_YURI_HOME + "/" + files[image]))


def setup(bot):
    bot.add_cog(YuruYuri(bot))