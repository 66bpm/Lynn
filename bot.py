from discord.ext import commands, tasks

import traceback, sys
import discord
import asyncio
import asyncpg
import json

async def get_prefix(bot, message):
    prefixes = ['lynn ','l!', 'Lynn ', 'L!']
    guild = message.guild
    if guild:
        async with bot.dbPool.acquire() as con:
            sql = 'SELECT prefix from prefixes WHERE guild_id = ' + str(message.guild.id) + ';'
            customPrefix = await con.fetchrow(sql)
            if (customPrefix != None):
                return commands.when_mentioned_or(customPrefix[0])(bot, message)
    
    return commands.when_mentioned_or(*prefixes)(bot, message)

class LynnBot(commands.Bot):
    def __init__(self, prefix, settingData):
        super().__init__(
            command_prefix=prefix,
            description="LynnBot"
        )

        self.dbPool = None

        self.latestID = 0
        self.credentials = settingData["dbcredentials"]
        self.safeExclusion = settingData["exclusion"]
        self.embedColor = eval(settingData["color"])
        self.initialExtensions = settingData["cogs"]

        donateLink = settingData["donate"]
        self.patreonLink = donateLink["patreon"]
        self.paypalLink = donateLink["paypal"]

        self.inviteLink = settingData["botInvite"]
        self.supportLink = settingData["serverInvite"]

    async def InitialConfig(self):
        #setup cogs
        for extension in self.initialExtensions:
            try:
                self.load_extension(str(extension))
            except:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    async def DatabaseCleanup(self):
        async with self.dbPool.acquire() as con:
            guildRows = await con.fetch('SELECT DISTINCT guild_id FROM channels')
            for guildID in guildRows:   
                guild = self.get_guild(guildID[0])
                if (guild != None):
                    channelsRows = await con.fetch('SELECT channel_id FROM channels WHERE guild_id = '+str(guildID[0]))
                    for channelID in channelsRows:
                        try:
                            channel = self.get_channel(channelID[0])
                            if channel is None:
                                await con.execute('DELETE FROM channels WHERE channel_id = '+str(channelID[0]) +';')
                        except:
                            print("Delete a channel " + str(channelID[0]))
                            await con.execute('DELETE FROM channels WHERE channel_id = '+str(channelID[0]) +';')
                else:
                    await con.execute('DELETE FROM channels WHERE guild_id = '+str(guildID[0])+';')
                    await con.execute('DELETE FROM prefixes WHERE guild_id = '+str(guildID[0])+';')
    
    async def GetLatestID(self):
        async with self.dbPool.acquire() as con:
            row = await con.fetchrow("SELECT id FROM hentai ORDER BY 1 DESC LIMIT 1;")
            self.latestID = row[0]

    async def on_guild_remove(self, guild):
        async with self.dbPool.acquire() as con:
            await con.execute('DELETE FROM channels WHERE guild_id = '+str(guild.id)+';')
            await con.execute('DELETE FROM prefixes WHERE guild_id = '+str(guild.id)+';')

    async def on_guild_join(self,guild):
        def check(event):
            return event.target.id == client.user.id
        bot_entry = await guild.audit_logs(action=discord.AuditLogAction.bot_add).find(check)
        await bot_entry.user.send("Hi, degenerate user-san.\nThank you for inviting me into your server. Please join the support server to learn more about me.\n\n" + self.supportLink)

    async def on_ready(self):
        print('Logged on as', self.user)

        self.dbPool = await asyncpg.create_pool(**self.credentials)
        await self.DatabaseCleanup()
        await self.GetLatestID()

        await self.InitialConfig()        
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="nhentai"))

with open('config.json', 'r') as json_file:
    data = json.load(json_file)

botToken = str(data["token"])
settingData = data["settings"]

client = LynnBot(get_prefix, settingData)
client.run(botToken, bot=True, reconnect =True)