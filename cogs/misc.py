import discord
from discord.ext import commands, tasks
from cogs import checks

import io
import asyncio
import aiohttp
import typing

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
        self.poll = None
        self.proposedName = ""
        self.steven2Url = "https://media.discordapp.net/attachments/389504390177751054/691562925227245598/steven2.png"


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


    @commands.Cog.listener()
    async def on_message(self, ctx):
        if("steven" in ctx.clean_content.lower() and ctx.guild.id == 133812880654073857):
            async with aiohttp.ClientSession() as session:
                async with session.get(self.steven2Url) as r:
                    if r.status == 200:
                        data = io.BytesIO(await r.read())
                        await ctx.channel.send(file=discord.File(data, "steven2.png"))        

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.channel)
    @checks.shrimpHole()
    async def rename(self, ctx, *, name : str):
        name = name.replace(" ", "_")
        if(len(name) < 2 or len(name) > 32):
            await ctx.send("Channel name must be between 2 and 32 characters")
            return

        self.proposedName = name 
        self.poll = await ctx.send("Petition to rename channel from `{}` to `{}`\nPetition will be active for 15 minutes, requires a net vote of +3.".format(ctx.channel.name, self.proposedName))
        
        await self.poll.add_reaction(self.bot.get_emoji(253705709596704769))
        await self.poll.add_reaction(self.bot.get_emoji(253705749937520640))
        try:       
            if(self.pollLoop.is_running()):
                await ctx.send("Previous petition on name `{}` has been canceled.".format(self.proposedName))
                self.pollLoop.restart()
            else:
                self.pollLoop.start()      
        except Exception as e:
            print(e)   

    @rename.error
    async def renameError(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("rename can only be used once every 5 minutes.\nPlease try again in {} seconds.".format(int(error.retry_after)))

    @tasks.loop(seconds=15, count=60)
    async def pollLoop(self):
        try:
            if(not self.poll == None):
                self.poll = await self.poll.channel.fetch_message(self.poll.id)
                reactions = self.poll.reactions
                vote = 0
                for r in reactions:
                    if r.emoji.id == 253705709596704769:
                        vote += r.count
                    elif r.emoji.id == 253705749937520640:
                        vote -= r.count
                if(vote > 2):
                    await self.poll.channel.edit(name=self.proposedName)
                    await self.poll.channel.send("Petition passed! Channel name changed to `{}`".format(self.proposedName))
                    self.poll = None
                    self.proposedName = ""
                    self.pollLoop.cancel()
        except Exception as e:
            print(e)

    @pollLoop.after_loop
    async def afterPollLoop(self):
        print("hi")
        if(not self.pollLoop.is_being_cancelled()):
            print("hi2")
            await self.poll.channel.send("Petition on new channel name `{}` failed.".format(self.proposedName))



"""
    @commands.command()
    async def flushed(self, ctx, emoji : typing.Union[discord.Emoji, discord.PartialEmoji]):
        print(emoji)
"""


def setup(bot):
    bot.add_cog(Misc(bot))
