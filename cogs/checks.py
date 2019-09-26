import discord
from discord.ext import commands

def me():
    async def predicate(ctx):
        return (ctx.author.id == 133811493778096128)
    return(commands.check(predicate))

def permissionCheck(perm):
    async def predicate(ctx):
        perms = ctx.bot.get_cog('PermissionHandler')
        return(perms.is_enabled(ctx, perms.Permissions[perm]))
    return(commands.check(predicate))

def manageGuild():
    async def predicate(ctx):
        return (ctx.author.guild_permissions.manage_guild or ctx.author.id == 133811493778096128)
    return(commands.check(predicate))
