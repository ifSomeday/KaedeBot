import discord
from discord.ext import commands
from cogs import checks

import asyncio
import os
import pickle
import typing
import random

class Memes(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.fileLock = asyncio.Lock()
        self.NONWORD = "\n\n"
        self.filePath = "{0}/dataStores/memes.pickle".format(os.getcwd())
        self.loadMemes()


    @commands.command(name="newMeme", help="Adds a meme to the bot's meme database")
    @checks.permissionCheck("MEME")
    async def addMeme(self, ctx, *, meme):

        if(ctx.message.author.id == self.bot.user.id):
            return

        await self.__addMeme(meme)

        await self.saveMemes()
        await ctx.message.add_reaction("🤖")


    async def __addMeme(self, meme):

        word1 = word2 = word3 = self.NONWORD
        async with self.fileLock:
            for word in meme.split():
                table = self.memes.setdefault((word1, word2, word3), [])
                if(not word in table):
                    table.append(word)
                word1, word2, word3 = word2, word3, word

            table = self.memes.setdefault((word1, word2, word3), [])
            if(not self.NONWORD in table):
                table.append(self.NONWORD)


    @commands.command(name="meme", help="Generates a meme using the bot's built-in meme database.")
    @checks.permissionCheck("MEME")
    async def getMeme(self, ctx, *, builder: typing.Optional[str]):

        word1 = word2 = word3 = self.NONWORD
        output = ""

        if(builder):
            for text in builder.split():
                word1, word2, word3 = word2, word3, text
            output = "{0} ".format(builder)

        
        if(not (word1, word2, word3) in self.memes):
            word1 = word2 = word3 = self.NONWORD
            output = "Unable to match supplied text. Generating random meme...\n\n"

        async with self.fileLock:
            while True:
                newWord = random.choice(self.memes[(word1, word2, word3)])
                if(newWord == self.NONWORD or len(output + newWord) + 1 > 2000):
                    await ctx.send(output)
                    return
                output += newWord + " "
                word1, word2, word3 = word2, word3, newWord


    @commands.command("purgeMemes", hidden=True)
    @checks.me()
    async def purgeMemes(self, ctx):
        if(os.path.isfile(self.filePath)):
            os.remove(self.filePath)
            await ctx.send("Purged meme database")


    @commands.command("indexMemeChannel", hidden=True)
    @checks.me()
    async def indexMemeChannel(self, ctx):

        await ctx.send("Adding channel to meme database")

        async for message in ctx.channel.history(limit=None, oldest_first=True):
            if(not message.author.id == self.bot.user.id):
                if(message.clean_content.lower().startswith("!newmeme") or message.clean_content.lower().startswith("!addmeme")):
                    meme = " ".join(message.clean_content.split()[1:]).strip()
                    if(len(meme) > 0):
                        await self.__addMeme(meme)
        await self.saveMemes()

        await ctx.send("Successfully added channel to meme database")


    @addMeme.error
    async def addMemeError(self, ctx, error):
        if (isinstance(error, commands.MissingRequiredArgument)):
            await ctx.send("Missing required argument: meme")
        else:
            print(error)


    def loadMemes(self):
        self.memes = {}
        if(os.path.isfile(self.filePath)):
            with open(self.filePath, "rb") as f:
                self.memes = pickle.load(f)


    async def saveMemes(self):
        async with self.fileLock:
            with open(self.filePath, "wb") as f:
                pickle.dump(self.memes, f)




def setup(bot):
    bot.add_cog(Memes(bot))