import asyncio
import asyncpg
import datetime
import discord
from discord.ext import tasks, commands
from . import shareFunc

class Setting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name = 'prefix', pass_context = True, aliases = ['pf'])
    @commands.guild_only()
    async def _prefix(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Prefix Subcommands", "`get`, `set` (admin), `reset`(admin).")

    @_prefix.command(name='reset', pass_context=True, aliases=['clear', 'c', 'rs'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _prefix_reset(self, ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            sql = 'DELETE FROM prefixes WHERE guild_id = ' + str(ctx.message.guild.id) + ';'
            await con.execute(sql)
            now = datetime.datetime.utcnow()
            print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(ctx.message.guild.id) + '> reset prefix to "lynn ".')
            await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Reset prefix to `lynn `, `Lynn `, `l!`, `L!`.")

    @_prefix.command(name='get', pass_context=True, aliases=['g'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _prefix_get(self, ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            sql = 'SELECT prefix from prefixes WHERE guild_id = ' + str(ctx.message.guild.id) + ';'
            customPrefix = await con.fetchrow(sql)
            if (customPrefix != None):
                await shareFunc.SendFieldOnlyEmbed(self,ctx,"Prefix", customPrefix[0])
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Custom prefix is not set")
            
    @_prefix.command(name='set', pass_context=True, aliases=['s'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _prefix_set(self, ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            if (arg != None):
                sql = 'SELECT prefix from prefixes WHERE guild_id = ' + str(ctx.message.guild.id) + ';'
                customPrefix = await con.fetchrow(sql)
                if (customPrefix != None):
                    try:
                        sql = 'UPDATE prefixes SET prefix = $1 WHERE guild_id = ' + str(ctx.message.guild.id) + ';'
                        await con.execute(sql, str(arg))
                    except:
                        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid input character")
                else:
                    sql = 'INSERT INTO prefixes(guild_id, prefix) VALUES($1, $2) ON CONFLICT DO NOTHING'
                    await con.execute(sql, ctx.message.guild.id, str(arg))
                now = datetime.datetime.utcnow()
                print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(ctx.message.guild.id) + '> set prefix to '+str(arg)+'.')
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Set prefix to `" + str(arg) + "`")
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `prefix set custom_prefix`")
        
def setup(bot):
    bot.add_cog(Setting(bot))