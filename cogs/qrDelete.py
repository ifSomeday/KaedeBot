import discord
from discord.ext import commands

import aiohttp
import asyncio
from io import BytesIO
from PIL import Image
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol

class QRDelete(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx):
        urls = []
        for attachment in ctx.attachments:
            urls.append(attachment.url)
        for embed in ctx.embeds:
            urls.append(embed.thumbnail.proxy_url)
        for url in urls:
            img = await self.loadImage(url)
            if(len(decode(img, symbols=[ZBarSymbol.QRCODE])) > 0):
                try:
                    await ctx.delete()
                except:
                    await ctx.channel.send("Be careful when scanning QR codes!\nAnyone promising you free Nitro or something similar is trying to steal your account!")


    async def loadImage(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                return(Image.open(BytesIO(await r.read())))


def setup(bot):
    bot.add_cog(QRDelete(bot))