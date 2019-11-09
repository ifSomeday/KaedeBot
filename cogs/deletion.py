import discord
from discord.ext import commands
from cogs import checks

import os
import asyncio
import pickle
import typing
from datetime import datetime
import io


class Deletion(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logFile = "{0}/dataStores/deletionLog.pickle".format(os.getcwd())
        self.logSettingsFile = "{0}/dataStores/deletionLogSettings.pickle".format(os.getcwd())
        self.logLock = asyncio.Lock()
        self.logSettingsLock = asyncio.Lock()
        self.loadLog()
        self.loadSettings()


    @commands.Cog.listener()
    async def on_message_delete(self, ctx):

        if(self.bot.user.id == ctx.author.id):
            return

        channelLog = self.log.setdefault(ctx.channel.id, [])

        channelLog.append({ "authorId" : ctx.author.id,
            "mention" : ctx.author.mention,
            "message" : ctx.clean_content,
            "time" : ctx.created_at,
            "delTime" : datetime.now(),
            "channel" : ctx.channel.name,
            "guild" : ctx.guild.name })

        if((ctx.channel.id in self.logSettings["channels"] or ctx.author.id in self.logSettings["users"].setdefault(ctx.channel.id, [])) and not ctx.author.id in self.logSettings["blacklist"].setdefault(ctx.channel.id, [])):
            await ctx.channel.send("Message Deleted:\n`[{0}]` {1} : {2}".format(ctx.created_at.strftime("%H:%M:%S"), ctx.author.mention, ctx.clean_content))

        await self.saveLog()


    @commands.group(help="Tracks deleted messages and can optionally repost them.")
    @checks.manageGuild()
    async def deletion(self, ctx):
        if(ctx.invoked_subcommand is None):
            await ctx.send("Invalid deletion command passed.")

    @deletion.group(name="message", help="Contains settings for reposting deleted messages")
    @checks.manageGuild()
    async def deletionMessages(self, ctx):
        if(ctx.invoked_subcommand is None):
            await ctx.send("Invalid deletion message command passed.")        


    @deletionMessages.command(name = "enable", help="Enables deletion messages for a specified User or Channel.")
    async def enableDeletion(self, ctx, target : typing.Union[discord.Member, discord.TextChannel]):

        if(isinstance(target, discord.Member)):

            channelUsers = self.logSettings["users"].setdefault(ctx.channel.id, [])

            if(not target.id in channelUsers):
                channelUsers.append(target.id)
                await ctx.send("Started tracking User {0}.".format(target.name))
                
            else:
                await ctx.send("User {0} is already being tracked.".format(target.name))

            channelBlacklist = self.logSettings["blacklist"].setdefault(ctx.channel.id, [])

            if(target.id in channelBlacklist):
                channelBlacklist.remove(target.id)
                await ctx.send("Removed User {0} from blacklist.".format(target.name))

        elif(isinstance(target, discord.TextChannel)):

            channelList = self.logSettings.setdefault("channels", [])

            if(not target.id in self.logSettings["channels"]):
                self.logSettings["channels"].append(target.id)
                await ctx.send("Started tracking Channel {0}".format(target.name))

            else:
                await ctx.send("Already tracking Channel {0}".format(target.name))


        await self.saveSettings()


    @deletionMessages.command(name = "disable", help="Disables deletion messages for a specified User or Channel.")
    async def disableDeletion(self, ctx, target : typing.Union[discord.Member, discord.TextChannel]):

        if(isinstance(target, discord.Member)):

            channelUsers = self.logSettings["users"].setdefault(ctx.channel.id, [])

            if(target.id in channelUsers):
                channelUsers.remove(target.id)
                await ctx.send("Stopped tracking User {0}.".format(target.name))
                
            else:
                await ctx.send("User {0} was not being tracked.".format(target.name))


        elif(isinstance(target, discord.TextChannel)):

            channelList = self.logSettings.setdefault("channels", [])

            if(target.id in channelList):
                channelList.remove(target.id)
                await ctx.send("Stopped tracking Channel {0}".format(target.name))
                
            else:
                await ctx.send("Channel {0} was not being tracked.".format(target.name))

        await self.saveSettings()

    @deletionMessages.command(name = "blacklist", help="Blacklists a user from deletion messages.")
    async def deletionBlacklist(self, ctx, member : discord.Member):

        channelBlacklist = self.logSettings["blacklist"].setdefault(ctx.channel.id, [])
        if(not member.id in channelBlacklist):
            channelBlacklist.append(member.id)
            await ctx.send("Added User {0} to blacklist.".format(member.name))
        else:
            await ctx.send("User {0} already in blacklist. Use `!deletion enable {0}` to remove.".format(member.name))

        channelUsers = self.logSettings["users"].setdefault(ctx.channel.id, [])
        if(member.id in channelUsers):
            channelUsers.remove(member.id)

        await self.saveSettings()
    

    @deletion.command(name = "log", help="Displays recent deleted messages for specified User or Channel.")
    async def deletionLog(self, ctx, target : typing.Union[discord.Member, discord.TextChannel], count : typing.Optional[int] = 5):

        log = self.log.setdefault(ctx.channel.id, [])
        output = ""

        if(isinstance(target, discord.Member)):
            log = list(filter(lambda d: d["authorId"] == target.id, log))
            deletionText = "\n".join(["`[{0}]` {1}".format(x["time"].strftime("%H:%M:%S"), x["message"]) for x in log[-count:]])
            deletionCount = min(count, len(log))
            output = "Last {0} deleted messages from User {1}:\n{2}".format(deletionCount, target.mention, deletionText)
        elif(isinstance(target, discord.TextChannel)):
            deletionText = "\n".join(["`[{0}]` {1} : {2}".format(x["time"].strftime("%H:%M:%S"), x["mention"], x["message"]) for x in log[-count:]])
            deletionCount = min(count, len(log))
            output = "Last {0} deleted messages from Channel {1}:\n{2}".format(deletionCount, target.mention, deletionText)
        else:
            return
            
        if(len(log) == 0):
            await ctx.send("No logs found for {0}.".format(target.mention))
            return

        await ctx.send(output)

            
        
    @deletion.command(name = "dump", help="Dumps specified deleted messages to a file and makes it available to download.")
    async def deletionDump(self, ctx, target : typing.Union[discord.Member, discord.TextChannel]):

        log = []
        f = None

        if(isinstance(target, discord.Member)):
            for channelId, channelLog in self.log.items():
                if(not ctx.guild.get_channel(channelId) == None):
                    log += list(filter(lambda d: d["authorId"] == target.id, channelLog))
            deletionText = "\n".join(["[{0}] {1} - {2} : {3}".format(x["time"].strftime("%H:%M:%S"), x["guild"], x["channel"], x["message"]) for x in log])
            f = discord.File(io.StringIO(deletionText), filename="{0}.txt".format(target.name.replace("_", "-")))
            
        elif(isinstance(target, discord.TextChannel)):
            log = self.log.setdefault(ctx.channel.id, [])
            deletionText = "\n".join(["[{0}] {1} : {2}".format(x["time"].strftime("%H:%M:%S"), ctx.bot.get_user(x["authorId"]).name, x["message"]) for x in log])
            f = discord.File(io.StringIO(deletionText), filename="{0}.txt".format(target.name.replace("_", "-")))

        

        await ctx.send("Found {0} entries.".format(len(log)), file=f)


    @deletion.command(name = "status", help="Displays the current deletion tracking settings for the guild.")
    async def deletionStatus(self, ctx):

        channelTracking = []
        userTracking = []
        blacklist = []

        for channel in ctx.guild.channels:
            if channel.id in self.logSettings["channels"]:
                channelTracking.append("`{0}`".format(channel.name))
            userTracking += ["`{0}`".format(ctx.bot.get_user(x).name) for x in self.logSettings["users"].setdefault(channel.id, [])]
            blacklist += ["`{0}`".format(ctx.bot.get_user(x).name) for x in self.logSettings["blacklist"].setdefault(channel.id, [])]
        
        if(len(blacklist) + len(channelTracking) + len(userTracking) == 0):
            await ctx.send("No deletion tracking active in this guild.")
        else:
            output = "**Currently Tracking in {0}:**".format(ctx.guild.name)
            if(len(channelTracking) > 0):
                output += "\n\n**Channels:**\n\t{0}".format("\n\t".join(channelTracking))
            if(len(userTracking) > 0):
                output += "\n\n**Users:**\n\t{0}".format("\n\t".join(userTracking))
            if(len(blacklist) > 0):
                output += "\n\n**BlackList:**\n\t{0}".format("\n\t".join(blacklist))
            await ctx.send(output)
        



    @enableDeletion.error
    @disableDeletion.error
    @deletionLog.error
    async def enableDeletionError(self, ctx, error):
        if(isinstance(error, commands.BadUnionArgument)):
            await ctx.send("Invalid target specified.\nTarget can either be a User or Channel.")
        else:
            print(error)


    @deletionBlacklist.error
    async def enableDeletionError(self, ctx, error):
        if(isinstance(error, commands.BadArgument)):
            await ctx.send("Please specify a valid User to blacklist.")
        else:
            print(error)
       

    def loadLog(self):
        self.log = {}
        if(os.path.isfile(self.logFile)):
            with open(self.logFile, "rb") as f:
                self.log = pickle.load(f)


    def loadSettings(self):
        self.logSettings = {"channels" : [], "users" : {}, "blacklist" : {}}
        if(os.path.isfile(self.logSettingsFile)):
            with open(self.logSettingsFile, "rb") as f:
                self.logSettings = pickle.load(f)


    async def saveLog(self):
        async with self.logLock:
            with open(self.logFile, "wb") as f:
                pickle.dump(self.log, f)


    async def saveSettings(self):
        async with self.logSettingsLock:
            with open(self.logSettingsFile, "wb") as f:
                pickle.dump(self.logSettings, f)


def setup(bot):
    bot.add_cog(Deletion(bot))