import asyncio
import asyncpg
import discord
from discord.ext import tasks, commands
from random import seed, randint, choice
import time
from . import shareFunc

def to_lower(argument):
    return argument.lower()

class NHentai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        milliseconds = int(round(time.time() * 1000))
        seed(milliseconds)

    @commands.group(name='nhentai', pass_context=True, aliases=['nh'])    
    @commands.is_nsfw()
    async def _nhentai(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Nhentai Subcommands (nsfw)", "`get`, `random`, `recent`.")

    @_nhentai.command(name='get', pass_context=True, aliases=['g'])
    @commands.is_nsfw()
    async def _nhentai_get(self, ctx, arg):
        if (arg != None):
            if (str(arg).isdigit()):
                async with self.bot.dbPool.acquire() as con:
                    row = await con.fetchrow('SELECT * FROM hentai WHERE id = '+str(arg)+';')
                    if (row != None):
                        embedMessage = await shareFunc.EmbedFormatter(self, row)
                        await ctx.send(embed = embedMessage)
                    else:
                        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Error. Hentai is not found")
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `nhentai get digits`")
        else:
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `nhentai get digits`")

    @_nhentai.group(name='random', pass_context=True, aliases=['rand', 'ran', 'rd'])
    @commands.is_nsfw()
    async def _nhentai_random(self, ctx):
        if (ctx.invoked_subcommand is None):
            async with self.bot.dbPool.acquire() as con:
                magicNumber = randint(1, self.bot.latestID)
                row = None
                while (row == None):
                    row = await con.fetchrow('SELECT * FROM hentai WHERE id = '+str(magicNumber)+';')
                    embedMessage = await shareFunc.EmbedFormatter(self, row)
                    await ctx.send(embed = embedMessage)
                    magicNumber = randint(1, self.bot.latestID)

    async def RandomWithType(self, ctx, key, value, table):
        is_exist = await shareFunc.IsExistInDatabase(self, table, key, "'"+ value +"'")
        if (is_exist):
            async with self.bot.dbPool.acquire() as con:
                sql = "SELECT * FROM hentai WHERE '"+ value +"' = ANY("+table+")"
                rows = await con.fetch(sql)
                embedMessage = await shareFunc.EmbedFormatter(self, choice(rows))
                await ctx.send(embed = embedMessage)
        else:
            similar = await shareFunc.GetSimilar(self, table, key, value)
            outmsg = "Countdn't find `" + str(value) + "`. Similar results: " + similar + "."
            await shareFunc.SendFieldOnlyEmbed(self, ctx, "Error", outmsg)

    @_nhentai_random.command(name = 'parody', pass_context=True, aliases=['parodies', 'p'])
    @commands.is_nsfw()
    async def _nhentai_random_parody(self, ctx, arg: to_lower):
        await self.RandomWithType(ctx, 'parody_name',arg, 'parodies')

    @_nhentai_random.command(name = 'character', pass_context=True, aliases=['characters', 'char', 'c'])
    @commands.is_nsfw()
    async def _nhentai_random_character(self, ctx, arg: to_lower):
        await self.RandomWithType(ctx, 'character_name',arg, 'characters')
    
    @_nhentai_random.command(name = 'tag', pass_context=True, aliases=['tags', 't'])
    @commands.is_nsfw()
    async def _nhentai_random_tag(self, ctx, arg: to_lower):
        await self.RandomWithType(ctx, 'tag_name',arg, 'tags')

    @_nhentai_random.command(name = 'artist', pass_context=True, aliases=['artists', 'a'])
    @commands.is_nsfw()
    async def _nhentai_random_artist(self, ctx, arg: to_lower):
        await self.RandomWithType(ctx, 'artist_name',arg, 'artists')

    @_nhentai_random.command(name = 'group', pass_context=True, aliases=['groups', 'g'])
    @commands.is_nsfw()
    async def _nhentai_random_group(self, ctx, arg: to_lower):
        await self.RandomWithType(ctx, 'group_name',arg, 'groups')

    @_nhentai_random.command(name = 'language', pass_context=True, aliases=['languages', 'lang', 'lan', 'ln', 'l'])
    @commands.is_nsfw()
    async def _nhentai_random_language(self, ctx, arg: to_lower):
        await self.RandomWithType(ctx, 'language_name',arg, 'languages')

    @_nhentai.group(name='recent', pass_context=True, aliases=['rct', 'rec', 'rc'])
    @commands.is_nsfw()
    async def _nhentai_recent(self, ctx):
        if (ctx.invoked_subcommand is None):
            async with self.bot.dbPool.acquire() as con:
                rows = await con.fetch("SELECT id, title FROM hentai ORDER BY id DESC LIMIT 5")
                embedMessage = discord.Embed(
                            title = "5 recent hentai",
                            color = discord.Color(self.bot.embedColor),
                        )
                for row in rows:
                    title = "[" + str(row[1]) + "](https://nhentai.net/g/"+ str(row[0]) + "/)"
                    embedMessage.add_field(name=str(row[0]), value= title, inline=False)
                await ctx.send(embed = embedMessage)

    async def GetRecentWithType(self, ctx, key, value, table):
        is_exist = await shareFunc.IsExistInDatabase(self, table, key, "'"+ value +"'")
        if (is_exist):
            async with self.bot.dbPool.acquire() as con:
                sql = "SELECT * FROM hentai WHERE '"+ value +"' = ANY("+table+") ORDER BY id DESC LIMIT 5"
                rows = await con.fetch(sql)
                embedMessage = discord.Embed(
                            title = "5 recent `"+ str(value) +"` hentai",
                            color = discord.Color(self.bot.embedColor),
                        )
                for row in rows:
                    title = "[" + str(row[1]) + "](https://nhentai.net/g/"+ str(row[0]) + "/)"
                    embedMessage.add_field(name=str(row[0]), value= title, inline=False)
                await ctx.send(embed = embedMessage)
        else:
            similar = await shareFunc.GetSimilar(self, table, key, value)
            outmsg = "Countdn't find `" + str(value) + "`. Similar results: " + similar + "."
            await shareFunc.SendFieldOnlyEmbed(self, ctx, "Error", outmsg)

    
    @_nhentai_recent.command(name = 'parody', pass_context=True, aliases=['parodies', 'p'])
    @commands.is_nsfw()
    async def _nhentai_recent_parody(self, ctx, arg:to_lower):
        await self.GetRecentWithType(ctx, 'parody_name',arg, 'parodies')

    @_nhentai_recent.command(name = 'character', pass_context=True, aliases=['characters', 'char', 'c'])
    @commands.is_nsfw()
    async def _nhentai_recent_character(self, ctx, arg: to_lower):
        await self.GetRecentWithType(ctx, 'character_name',arg, 'characters')
    
    @_nhentai_recent.command(name = 'tag', pass_context=True, aliases=['tags', 't'])
    @commands.is_nsfw()
    async def _nhentai_recent_tag(self, ctx, arg: to_lower):
        await self.GetRecentWithType(ctx, 'tag_name',arg, 'tags')

    @_nhentai_recent.command(name = 'artist', pass_context=True, aliases=['artists', 'a'])
    @commands.is_nsfw()
    async def _nhentai_recent_artist(self, ctx, arg: to_lower):
        await self.GetRecentWithType(ctx, 'artist_name',arg, 'artists')

    @_nhentai_recent.command(name = 'group', pass_context=True, aliases=['groups', 'g'])
    @commands.is_nsfw()
    async def _nhentai_recent_group(self, ctx, arg: to_lower):
        await self.GetRecentWithType(ctx, 'group_name',arg, 'groups')

    @_nhentai_recent.command(name = 'language', pass_context=True, aliases=['languages', 'lang', 'lan', 'ln', 'l'])
    @commands.is_nsfw()
    async def _nhentai_recent_language(self, ctx, arg: to_lower):
        await self.GetRecentWithType(ctx, 'language_name',arg, 'languages')

def setup(bot):
    bot.add_cog(NHentai(bot))