import aiohttp
import asyncio
import asyncpg
from bs4 import BeautifulSoup
import datetime
import discord
from discord.ext import tasks, commands
from .. import shareFunc

class NHentaiFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nhentai_update.add_exception_type(asyncpg.PostgresConnectionError)
        self.nhentai_update.start()
    
    def cog_unload(self):
        self.nhentai_update.cancel()

    @tasks.loop(minutes=10)
    async def nhentai_update(self):
        async with self.bot.dbPool.acquire() as con:
            async with aiohttp.ClientSession() as session:
                soup = None
                newestHentaiId = 0
                async with session.get("https://nhentai.net/") as response:
                    text = await response.read()
                    soup = BeautifulSoup(text.decode('utf-8'), 'html5lib')
                    newestHentaiId = eval(soup.find(id = 'content').contents[2].div.a['href'].split('/')[2])
                now = datetime.datetime.utcnow()
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name= str(self.bot.latestID) + " [" + now.strftime("%H:%M") + " UTC]"))
                print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <Checking for nhentai updates>. ' + str(newestHentaiId- self.bot.latestID) + ' hentai found.')
                if (newestHentaiId > self.bot.latestID):
                    for i in range(self.bot.latestID + 1, newestHentaiId+1):
                        link = "https://nhentai.net/g/"+ str(i) + "/"
                        async with session.get(link) as response:
                            text = await response.read()
                            soup = BeautifulSoup(text.decode('utf-8'), 'html5lib')
                            try:
                                cover = "'" + soup.find(id = 'cover').img['data-src'] + "'"
                            except:
                                cover = ""
                            info = soup.find(id = 'info')
                            try:
                                titleRaw = info.contents[0]
                                title = "'"
                                for titlePart in titleRaw.find_all('span'):  
                                    if (len(titlePart)>0):
                                        if (str(titlePart.contents[0]).find("'") != -1):
                                            splitTitle = titlePart.contents[0].split("'")
                                            title += splitTitle[0] + "''" + splitTitle[1]
                                        else:
                                            title += titlePart.contents[0]
                                title += "'"
                                allTags = info.find(id = 'tags')
                                parodies = "'{"
                                for parody in allTags.contents[0].find_all('a'):    
                                    parodies += (parody.span.contents[0]) + ","
                                parodies = parodies[:-1] + "}'"
                                if len(parodies) < 5:
                                    parodies = 'NULL'
                                characters = "'{"
                                for character in allTags.contents[1].find_all('a'):    
                                    characters += (character.span.contents[0]) + ","
                                characters = characters[:-1] + "}'"
                                if len(characters) < 5:
                                    characters = 'NULL'
                                tags = "'{"
                                for tag in allTags.contents[2].find_all('a'):    
                                    tags += (tag.span.contents[0]) + ","
                                tags = tags[:-1] + "}'"
                                if len(tags) < 5:
                                    tags = 'NULL'
                                artists = "'{"
                                for artist in allTags.contents[3].find_all('a'):    
                                    artists +=  (artist.span.contents[0]) + ","
                                artists = artists[:-1] + "}'"
                                if len(artists) < 5:
                                    artists = 'NULL'
                                groups = "'{"
                                for group in allTags.contents[4].find_all('a'):    
                                    groups += (group.span.contents[0]) + ","
                                groups = groups[:-1] + "}'"
                                if len(groups) < 5:
                                    groups = 'NULL'
                                languages = "'{"
                                for language in allTags.contents[5].find_all('a'):    
                                    languages += (language.span.contents[0]) + ","
                                languages = languages[:-1] + "}'"
                                if len(languages) < 5:
                                    languages = 'NULL'
                                categories = "'{"
                                for category in allTags.contents[6].find_all('a'):    
                                    categories += (category.span.contents[0]) + ","
                                categories = categories[:-1] + "}'"
                                if len(categories) < 5:
                                    categories = 'NULL'
                                pages = allTags.contents[7].find_all('a')[0].span.contents[0]
                                sql = 'SELECT * FROM hentai WHERE id = ($1)'
                                status = await con.execute(sql,i)
                                if (not eval(status[-1])):
                                    sql = 'INSERT INTO hentai(id) VALUES($1) ON CONFLICT DO NOTHING'
                                    await con.execute(sql, i)
                                    await con.execute("UPDATE hentai SET title = "+str(title)+", cover_url = "+str(cover)+", parodies = "+str(parodies)+", characters = "+str(characters)+", tags = "+str(tags)+", artists = "+str(artists)+", groups = "+str(groups)+", languages = "+str(languages)+", categories = "+str(categories)+", pages = "+str(pages)+" WHERE id = "+str(i))
                            except:
                                print("404 #ID: " + str(i))
                        await asyncio.sleep(0)
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name= str(newestHentaiId) + " [" + now.strftime("%H:%M") + " UTC]"))
                    channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels ORDER BY guild_id ASC;')
                    for i in range(self.bot.latestID+1, newestHentaiId+1):
                        hentaiRow = await con.fetchrow('SELECT * FROM hentai WHERE id = ' + str(i))
                        if (hentaiRow != None):
                            await shareFunc.Notify(self, hentaiRow, channelRows)
                        await asyncio.sleep(0)
                    await self.bot.GetLatestID()

def setup(bot):
    bot.add_cog(NHentaiFeed(bot))