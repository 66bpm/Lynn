import asyncio
import discord
from discord.ext import tasks, commands
from . import shareFunc

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cogDir = 'cogs.'

    @commands.command(name = "load", hidden = True)
    @commands.is_owner()
    async def _load(self, ctx, cog:str):
        try:
            self.bot.load_extension(self.cogDir + cog)
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, '`['+ cog + ']` loaded.')
        except:
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, '`['+ cog + ']` failed to load extension.')

    @commands.command(name = "unload", hidden = True)
    @commands.is_owner()
    async def _unload(self, ctx, cog:str):
        try:
            self.bot.unload_extension(self.cogDir + cog)
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, '`['+ cog + ']` unloaded.')
        except:
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, '`['+ cog + ']` failed to unload extension.')

    @commands.command(name = "reload", hidden = True)
    @commands.is_owner()
    async def _reload(self, ctx, cog:str):
        try:
            self.bot.reload_extension(self.cogDir + cog)
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, '`['+ cog + ']` reloaded.')
        except:
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, '`['+ cog + ']` failed to reload extension.')

def setup(bot):
    bot.add_cog(Owner(bot))