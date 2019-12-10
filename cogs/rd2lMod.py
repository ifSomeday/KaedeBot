import discord
from discord.ext import commands
from cogs import checks

import asyncio
import os
import pickle
import typing

class RD2LMod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.fileLock = asyncio.Lock()
        self.filePath = "{0}/dataStores/rd2lBotless.pickle".format(os.getcwd())
        self.roleList = []
        self.loadRoleList()
        print(self.roleList)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if(member.id in self.roleList and member.guild.id == 308515912653340682):
            role = member.guild.get_role(619346514912739330)
            await member.add_roles(role)
            print("Re botlessed {0}".format(member.name))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print([x.name for x in member.roles])
        if(member.guild.id == 308515912653340682):
            await self.updateBotlessList(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        #308515912653340682
        if(after.guild.id == 308515912653340682):
            #await self.updateBotlessList(after)
            pass
            
            # https://discord.gg/PtCGry
    async def updateBotlessList(self, member):
        if(619346514912739330 in [x.id for x in member.roles]):
            if(not member.id in self.roleList):
                print("Added {0} to botless".format(member.name))
                ## self.roleList[member.id] = [x.id for x in member.roles]
                self.roleList.append(member.id)
                print(self.roleList)
                await self.saveRoleList()
        else:
            if(member.id in self.roleList):
                print("removed {0} from botless".format(member.name))
                ## self.roleList.pop(member.id)
                self.roleList.remove(member.id)
                print(self.roleList)
                await self.saveRoleList()


    @commands.command()
    @checks.me()
    async def role(self, ctx, member : discord.Member, r : typing.Union[int, str, None] = 619346514912739330):
        role = None
        if(r is None):
            return
        elif(isinstance(r, int)):
            role = ctx.guild.get_role(r)
        else:
            for tmp in ctx.guild.roles:
                if(r == tmp.name.lower()):
                    role = tmp
                    break
        if(not role is None):
            if not role.id in [x.id for x in member.roles]:
                print("added role: {0}".format(role.id))
                await member.add_roles(role)
            else:
                print("removed role: {0}".format(role.id))
                await member.remove_roles(role)
            await ctx.message.add_reaction('✅')



    def loadRoleList(self):
        self.botless = []
        if(os.path.isfile(self.filePath)):
            with open(self.filePath, "rb") as f:
                self.roleList = pickle.load(f)


    async def saveRoleList(self):
        async with self.fileLock:
            with open(self.filePath, "wb") as f:
                pickle.dump(self.roleList, f)


def setup(bot):
    bot.add_cog(RD2LMod(bot))