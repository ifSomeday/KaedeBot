import discord
from discord.ext import commands
from cogs import checks

import asyncio
import os
import pickle
import random
import re

class YoutubeRewind(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.fileLock = asyncio.Lock()
        self.filePath = "{0}/dataStores/rewind.pickle".format(os.getcwd())
        self.loadRewind()
        self.urlFinder = r"((?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/(?:watch\?v=)?\/?[^ \n]*)"


    @commands.command(name="rewind", help="Reposts a random YouTube video that has been posted in this channel in the past.\nGuaranteed to be better than YouTube's rewind.")
    @checks.permissionCheck("REWIND")
    async def rewind(self, ctx):
        if(not ctx.channel.id in self.videos):
            await ctx.send("Building library... please wait")
            await self.buildHistory(ctx)
        if(len(self.videos[ctx.channel.id]) == 0):
            await ctx.send("No videos in current channel, or library is still being built...\nTry again in a couple minutes")
        else:
            channelVideos = self.videos[ctx.channel.id]
            await ctx.send("Your YouTube rewind is\n{0}".format(random.choice(channelVideos)))


    @commands.Cog.listener()
    async def on_message(self, ctx):
        perms = self.bot.get_cog('PermissionHandler')
        if(perms.is_enabled(ctx, perms.Permissions["REWIND"]) and not ctx.author.id == self.bot.user.id):
            if(not ctx.channel.id in self.videos):
                await self.buildHistory(ctx)
            m = re.findall(self.urlFinder, ctx.clean_content)
            if(not m == []):
                addList = [video for video in m if not video in self.videos[ctx.channel.id]]
                self.videos[ctx.channel.id] += addList
                print("added {0} to rewind for channel {1}({2})".format(str(addList), ctx.channel.name, ctx.channel.id))
                await self.saveRewind()


    async def buildHistory(self, ctx):

        self.videos[ctx.channel.id] = []

        async for message in ctx.channel.history(limit=None, oldest_first=True):
            if(not message.author.id == self.bot.user.id):
                m = re.findall(self.urlFinder, message.content)
                if(not m == []):
                    for video in m:
                        print(m)
                        if (not video in self.videos[ctx.channel.id]):
                            self.videos[ctx.channel.id].append(video)
        await self.saveRewind()


    def loadRewind(self):
        self.videos = {}
        if(os.path.isfile(self.filePath)):
            with open(self.filePath, "rb") as f:
                self.videos = pickle.load(f)


    async def saveRewind(self):
        async with self.fileLock:
            with open(self.filePath, "wb") as f:
                pickle.dump(self.videos, f)


def setup(bot):
    bot.add_cog(YoutubeRewind(bot))