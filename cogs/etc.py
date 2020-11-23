import asyncio
import discord
from discord.ext import tasks, commands
from . import shareFunc

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name = "donate")
    async def _donate(self, ctx):
        if (ctx.invoked_subcommand is None):
            await ctx.send(self.bot.patreonLink)

    @_donate.command(name = "paypal")
    async def _donate_paypal(self, ctx):
        await ctx.send(self.bot.paypalLink)

    @commands.command(name = "invite", aliases = ['inv'])
    async def _invite(self, ctx):
        await ctx.send(self.bot.inviteLink)

    @commands.command(name = "support")
    async def _support(self, ctx):
        await ctx.send(self.bot.supportLink)

    @commands.command(name = "say")
    async def _say(self, ctx, *, arg):
        await ctx.send(arg)

    @commands.command(name = "saydelete", aliases = ['sayd'])
    async def _saydelete(self, ctx, *, arg):
        await ctx.send(arg)
        await ctx.message.delete()

    @commands.command(name = "hi", aliases = ['yo', 'sup', 'howdy', 'hello', 'greetings', 'greeting'])
    async def _hi(self, ctx):
        await ctx.send("Hello, degenerate user-san")
   

    


def setup(bot):
    bot.add_cog(Misc(bot))