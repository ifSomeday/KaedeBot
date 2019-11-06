import discord
from discord.ext import commands

from enum import Enum, auto
import typing
import pickle
import os

from cogs import checks

from threading import Lock

class PermissionConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return(PermissionHandler.Permissions[argument.upper()])
        

class PermissionHandler(commands.Cog):


    def __init__(self, bot):
        self.bot = bot

        self.channelPermissions = {}
        self.guildPermissions = {}

        self.fileLock = Lock()
        self.channelPermissionPath = "{0}/dataStores/channelPermissions.pickle".format(os.getcwd())
        self.guildPermissionPath = "{0}/dataStores/guildPermissions.pickle".format(os.getcwd())

        self.__loadPermissions()


    def __loadPermissions(self):
        with(self.fileLock):
            if(os.path.isfile(self.channelPermissionPath)):
                with open(self.channelPermissionPath, "rb") as f:
                    self.channelPermissions = pickle.load(f)
            if(os.path.isfile(self.guildPermissionPath)):
                with open(self.guildPermissionPath, "rb") as f:
                    self.guildPermissions = pickle.load(f)


    def __savePermissions(self):
        with(self.fileLock):
            with open(self.channelPermissionPath, "wb") as f:
                pickle.dump(self.channelPermissions, f)
            with open(self.guildPermissionPath, "wb") as f:
                pickle.dump(self.guildPermissions, f)


    def permissionCheck(self, perm):
        async def predicate(ctx):
            self.is_enabled(ctx, perm)
        return(commands.check(predicate))


    @commands.command(name="addPerm")
    @checks.manageGuild()
    async def addPermission(self, ctx, perm: typing.Union[PermissionConverter, str], target : typing.Optional[str]):

        if(isinstance(perm, str)):
            await ctx.send("Permission `{0}` is not a valid permission type.".format(perm))
            return

        target = target and target.lower() in ["server", "all", "guild"]

        if(target):
            if(not ctx.guild.id in self.guildPermissions):
                self.guildPermissions[ctx.channel.guild.id] = []

            if(not perm in self.guildPermissions[ctx.guild.id]):
                self.guildPermissions[ctx.channel.guild.id].append(perm)
        else:
            if(not ctx.channel.id in self.channelPermissions):
                self.channelPermissions[ctx.channel.id] = []

            if(not perm in self.channelPermissions[ctx.channel.id]):
                self.channelPermissions[ctx.channel.id].append(perm)

        self.__savePermissions()
        #print(self.guildPermissions, self.channelPermissions)
        await ctx.send("Permissions updated for {0}".format("Guild" if target else "Channel"))


    @commands.command(name="removePerm")
    @checks.manageGuild()
    async def removePermission(self, ctx, perm: typing.Union[PermissionConverter, str], target : typing.Optional[str]):

        if(isinstance(perm, str)):
            await ctx.send("Permission `{0}` is not a valid permission type.".format(perm))
            return

        target = target and target.lower() in ["server", "all", "guild"]

        if(target):
            if(not ctx.guild.id in self.guildPermissions):
                self.guildPermissions[ctx.channel.guild.id] = []

            if(perm in self.guildPermissions[ctx.guild.id]):
                self.guildPermissions[ctx.channel.guild.id].remove(perm)
        else:
            if(not ctx.channel.id in self.channelPermissions):
                self.channelPermissions[ctx.channel.id] = []

            if(perm in self.channelPermissions[ctx.channel.id]):
                self.channelPermissions[ctx.channel.id].remove(perm)

        self.__savePermissions()
        #print(self.guildPermissions, self.channelPermissions)
        await ctx.send("Permissions updated for {0}".format("Guild" if target else "Channel"))


    @addPermission.error
    async def addPermissionError(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            print("command failed due to lack of permissions")
        else:
            print(error)


    @removePermission.error
    async def removePermissionError(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            print("command failed due to lack of permissions")
        else:
            print(error)

    def is_enabled(self, ctx, perm):
        if(ctx.channel.id in self.channelPermissions and perm in self.channelPermissions[ctx.channel.id]):
            return(True)
        elif(ctx.guild.id in self.guildPermissions and perm in self.guildPermissions[ctx.guild.id]):
            return(True)
        return(False)

    class Permissions(Enum):
        MEME = auto()
        IMAGEMACRO = auto()
        DELETION = auto()
        CHATRESPONSE = auto()
        FLOODCONTROL = auto()
        DRAFT = auto()
        OPENDOTA = auto()
        REWIND = auto()

def setup(bot):
    bot.add_cog(PermissionHandler(bot))