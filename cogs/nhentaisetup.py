import aiohttp
import asyncio
import asyncpg
from bs4 import BeautifulSoup
import datetime
import discord
from discord.ext import tasks, commands
from . import shareFunc

def to_lower(argument):
    return argument.lower()

class NHentai_Feed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nhentai_update.add_exception_type(asyncpg.PostgresConnectionError)
        self.nhentai_update.start()
    
    def cog_unload(self):
        self.nhentai_update.cancel()

    async def ReturnChannelIfExist(self, ctx, arg):
        if arg == None:
            return ctx.message.channel
        else:
            try:
                channel_input = eval(arg.split("#")[1][:-1])
                return self.bot.get_channel(channel_input)
            except:
                return None

    async def GetTags(self, _type:str, col_name:str):
        async with self.bot.dbPool.acquire() as con:
            async with aiohttp.ClientSession() as session:
                pageNumber = 1
                soup = None
                async with session.get("https://nhentai.net/" +_type + "/?page=" + str(pageNumber)) as response:
                    text = await response.read()
                    soup = BeautifulSoup(text.decode('utf-8'), 'html5lib')
                tagContainer = soup.find(id = 'tag-container')
                while(len(tagContainer.contents) > 0):
                    for tagSection in tagContainer.contents:
                        tags = tagSection.find_all('a')
                        for tag in tags:
                            sql = 'SELECT * FROM '+_type+' WHERE '+col_name+' = ($1)'
                            status = await con.execute(sql,str(tag.span.contents[0]))
                            if (not eval(status[-1])):
                                sql = 'INSERT INTO '+_type+'('+col_name+') VALUES($1) ON CONFLICT DO NOTHING'
                                await con.execute(sql,str(tag.span.contents[0]))
                    pageNumber += 1
                    async with session.get("https://nhentai.net/" +_type + "/?page=" + str(pageNumber)) as response:
                        text = await response.read()
                        soup = BeautifulSoup(text.decode('utf-8'), 'html5lib')
                        tagContainer = soup.find(id = 'tag-container')

    async def GetChannelProperty(self, ctx, arg, get_type, key, embed_title, embed_non_text):
        async with self.bot.dbPool.acquire() as con:
            channel = await self.ReturnChannelIfExist(ctx, arg)
            if channel != None:
                is_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',channel.id)
                if (is_exist):
                    row = await con.fetchrow('SELECT '+str(key)+' FROM channels WHERE channel_id = '+str(channel.id))
                    outmsg = await shareFunc.SetToString(row[0], embed_non_text)
                    await shareFunc.SendFieldOnlyEmbed(self,ctx,embed_title, outmsg)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `get "+str(get_type)+" #channel_name`")

    async def UpdateField(self, table, key, value, primary_key, primary_value):
        async with self.bot.dbPool.acquire() as con:
            await con.execute("UPDATE "+str(table)+" SET "+str(key)+" = '"+str(value)+"' WHERE "+str(primary_key)+" = "+str(primary_value))

    async def AddRemove(self, ctx, _type, operation, *args):
        async with self.bot.dbPool.acquire() as con:
            key = ''
            lookupTable = ''
            lookupKey = ''
            if (_type == 'include'):
                key = 'included_tags'
                lookupTable = 'tags'
                lookupKey = 'tag_name'
            elif (_type == 'exclude'):
                key = 'excluded_tags'
                lookupTable = 'tags'
                lookupKey = 'tag_name'
            elif (_type == 'language'):
                key = 'languages'
                lookupTable = 'languages'
                lookupKey = 'language_name'
            channel = None
            if len(args)>0:
                try:
                    channel_input = eval(args[0].split("#")[1][:-1])
                    channel = self.bot.get_channel(channel_input)
                    if (len(args) > 1):
                        tagArgs = args[1:]
                    else:
                        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `"+str(_type)+" "+str(operation)+" tag1 tag1 ... tagN` or `"+str(_type)+" "+str(operation)+" #channel_name tag1 tag1 ... tagN`")
                        return
                except:
                    channel = ctx.message.channel
                    tagArgs = args
                if channel != None:
                    is_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',channel.id)
                    if (is_exist):
                        tagsToDo = list()
                        tagsToFindSimilar = list()
                        tagsCannotOperate = list()
                        tagsDone = list()
                        for arg in tagArgs:
                            is_tag_exist = await shareFunc.IsExistInDatabase(self, lookupTable, lookupKey, "'" + str(arg) + "'")
                            if (is_tag_exist):
                                tagsToDo.append(str(arg))
                            else:
                                tagsToFindSimilar.append(str(arg))
                        row = await con.fetchrow('SELECT '+str(key)+' FROM channels WHERE channel_id = '+str(channel.id))
                        tagsInDB = list()
                        if (row[0] != None):
                            tagsInDB = list(row[0])
                        if operation == 'add':
                            for tag in tagsToDo:
                                if len(tagsInDB) > 0:
                                    if tag in tagsInDB:
                                        tagsCannotOperate.append(tag)
                                    else:
                                        tagsInDB.append(tag)
                                        tagsDone.append(tag)
                                else:
                                    tagsInDB.append(tag)
                                    tagsDone.append(tag)
                            if len(tagsInDB) > 0:
                                updatestr = "{"
                                for tag in tagsInDB:
                                    updatestr += tag + ","
                                updatestr = updatestr[:-1] + "}"
                                await self.UpdateField('channels', key, updatestr, 'channel_id', channel.id)
                        elif operation == 'remove':
                            for tag in tagsToDo:
                                if len(tagsInDB) > 0:
                                    if tag in tagsInDB:
                                        tagsDone.append(tagsInDB.pop(tagsInDB.index(tag)))
                                    else:
                                        tagsCannotOperate.append(tag)
                                else:
                                    tagsCannotOperate.append(tag)
                            if len(tagsInDB) > 0:
                                updatestr = "{"
                                for tag in tagsInDB:
                                    updatestr += tag + ","
                                updatestr = updatestr[:-1] + "}"
                                await self.UpdateField('channels', key, updatestr, 'channel_id', channel.id)
                            else:
                                await con.execute("UPDATE channels SET "+str(key)+" = NULL WHERE channel_id = "+str(channel.id))
                        outsimilar = ""
                        for tag in tagsToFindSimilar:
                            similar = await shareFunc.GetSimilar(self, lookupTable, lookupKey, tag)
                            outsimilar += "Countdn't find `" + str(tag) + "`. Similar results: " + similar + ".\n"
                        embedMessage = discord.Embed(
                                color = discord.Color(self.bot.embedColor),
                                description = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/)"
                            )
                        fieldName = ""
                        if (len(tagsDone) > 0):
                            outsuccess = await shareFunc.SetToString(tagsDone, "-")
                            now = datetime.datetime.utcnow()
                            print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(channel.id) + '> <' + str(_type) + '> <' + str(operation) + '> ' + outsuccess)
                            if (operation == 'add'):
                                fieldName = "Successfully added"
                            elif (operation == 'remove'):
                                fieldName = "Successfully removed"
                            embedMessage.add_field(name= fieldName, value= outsuccess, inline=False)
                        if (len(tagsCannotOperate)> 0):
                            outexists = await shareFunc.SetToString(tagsCannotOperate, "-")
                            if (operation == 'add'):
                                fieldName = "Already exists in the channel " + str(_type) + "d " + str(lookupTable) + "."
                            elif (operation == 'remove'):
                                fieldName = "Doesn't exists in the channel " + str(_type) + "d " + str(lookupTable) + "."
                            embedMessage.add_field(name=fieldName, value= outexists, inline=False)
                        if (len(outsimilar)>0):
                            embedMessage.add_field(name="Error", value= outsimilar[:-1], inline=False)
                        await ctx.send(embed = embedMessage)
                    else:
                        outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `"+str(_type)+" "+str(operation)+" tag1 tag1 ... tagN` or `"+str(_type)+" "+str(operation)+" #channel_name tag1 tag1 ... tagN`")

    async def CloneSetting(self, ctx, _type, *args):
        async with self.bot.dbPool.acquire() as con:
            if (len(args[0]) < 2):
                await shareFunc.SendDescriptionOnlyEmbed(self,ctx,"Invalid argument. Please use `clone "+str(_type)+" #origin #target1 #target2 ... #targetN`")
            else:
                try:
                    origin_input = eval(args[0][0].split("#")[1][:-1])
                    origin = self.bot.get_channel(origin_input)
                except:
                    origin = None
                if origin != None:
                    is_origin_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',origin.id)
                    if (is_origin_exist):
                        targets = args[0][1:]
                        invalid_target = []
                        valid_target = []
                        for target in targets:
                            try:
                                target_input = eval(target.split("#")[1][:-1])
                                target_channel = self.bot.get_channel(target_input)
                                valid_target.append(target_channel)
                            except:
                                invalid_target.append(str(target))
                        key = None
                        if (_type == 'include'):
                            key = 'included_tags'
                        elif (_type == 'exclude'):
                            key = 'excluded_tags'
                        elif (_type == 'language'):
                            key = 'languages' 
                        for target in valid_target:
                            is_target_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',target.id)
                            if (not is_target_exist):
                                sql = 'INSERT INTO channels(channel_id, guild_id) VALUES('+str(target.id)+', '+str(ctx.message.guild.id)+') ON CONFLICT DO NOTHING'
                                status = await con.execute(sql)
                                if (eval(status[-1])):
                                    await self.UpdateField('channels', 'excluded_tags', self.bot.safeExclusion, 'channel_id', target.id)
                                    await target.edit(nsfw=True)
                            if (_type != 'all'):
                                sql = 'UPDATE channels SET ' + str(key) + ' = (SELECT '+str(key)+ ' FROM channels WHERE channel_id = '+ str(origin.id) +' ) WHERE channel_id = ' + str(target.id) 
                                await con.execute(sql)
                            else:
                                sql = 'UPDATE channels SET included_tags = (SELECT included_tags FROM channels WHERE channel_id = '+str(origin.id)+' ), excluded_tags = (SELECT excluded_tags FROM channels WHERE channel_id = '+str(origin.id)+' ), languages = (SELECT languages FROM channels WHERE channel_id = '+str(origin.id)+' ) WHERE channel_id = '+ str(target.id) 
                                await con.execute(sql)
                            now = datetime.datetime.utcnow()
                            print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(target.id) + '> is cloned from ['+ str(origin.id) +'].')
                        embedMessage = discord.Embed(
                                color = discord.Color(self.bot.embedColor),
                                description = "Cloning `"+str(_type)+"` filter from ["+str(origin)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(origin.id) + "/)"
                        )
                        if (len(valid_target) > 0):
                            outfield = ""
                            for target in valid_target:
                                outfield += "["+str(target)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(target.id) + "/)\n"
                            embedMessage.add_field(name="To", value= outfield[:-1], inline=False)
                        if (len(invalid_target) > 0):
                            outfield = ""
                            for target in invalid_target:
                                outfield += str(target)+ "\n"
                            embedMessage.add_field(name="Invalid targets", value= outfield[:-1], inline=False)
                        await ctx.send(embed = embedMessage)
                    else:
                        outmsg = "Origin channel ["+str(origin)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(origin.id) + "/) is not set."
                        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
                else:
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx,"Invalid argument. Please use `clone "+str(_type)+" #origin #target1 #target2 ... #targetN`")

    async def Reset(self, ctx, _type, arg):
        async with self.bot.dbPool.acquire() as con:
            channel = await self.ReturnChannelIfExist(ctx, arg)
            if channel != None:
                is_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',channel.id)
                if (is_exist):
                    key = ''
                    if (_type == 'include'):
                        key = 'included_tags'
                    elif (_type == 'exclude'):
                        key = 'excluded_tags'
                    elif (_type == 'language'):
                        key = 'languages'
                    await con.execute("UPDATE channels SET "+str(key)+" = NULL WHERE channel_id = "+str(channel.id))
                    now = datetime.datetime.utcnow()
                    print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(channel.id) + '> <' + str(_type) + '> <reset> ')
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, "Successfully reset `" + str(_type) + "` at ["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/)")
                    return channel
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self,ctx, "Invalid argument. Please use `"+str(_type)+" reset #channel_name`")

    async def ResetAll(self, ctx, _type, arg):
        async with self.bot.dbPool.acquire() as con:
            channel = await self.ReturnChannelIfExist(ctx, arg)
            if channel != None:
                is_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',channel.id)
                if (is_exist):
                    await con.execute("UPDATE channels SET included_tags = NULL, excluded_tags = NULL, languages = NULL WHERE channel_id = "+str(channel.id))
                    now = datetime.datetime.utcnow()
                    print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(channel.id) + '> <reset all> ')
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, "Successfully reset `all` filters at ["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/)")
                    return channel

                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self,ctx, "Invalid argument. Please use `"+str(_type)+" #channel_name`")

    async def Notify(self, hentaiRow, channelRows):
        messages = []
        embedMessage = await shareFunc.EmbedFormatter(self, hentaiRow)
        if (hentaiRow[5] != None): 
            tags = set(hentaiRow[5])
        else:
            tags = None
        if (hentaiRow[8] != None):
            hlan = set(hentaiRow[8])
        else:
            hlan = None
        for channelRow in channelRows:
            channel = self.bot.get_channel(channelRow[0])
            if (channelRow[1] != None):
                incl = set(channelRow[1])
            else:
                incl = None
            if (channelRow[2] != None):
                excl = set(channelRow[2])
            else:
                excl = None
            if (channelRow[3] != None):
                lan = set(channelRow[3])
            else:
                lan = None
            if (channel!= None):
                if (tags == None and incl == None):
                    message = await channel.send(embed = embedMessage)
                    messages.append(message)
                elif (tags != None):
                    tagFlag = tags
                    if (incl != None):
                        tagFlag = tags.intersection(incl)
                    if (len(tagFlag) > 0):
                        if (excl != None):
                            tagFlag = tags.intersection(excl)
                        else:
                            tagFlag = set()
                        if (len(tagFlag) < 1):
                            lanFlag = hlan
                            if (lan != None):
                                lanFlag = hlan.intersection(lan)
                            if (len(lanFlag) > 0):
                                message = await channel.send(embed = embedMessage)
                                messages.append(message)
        return messages

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async with self.bot.dbPool.acquire() as con:
            await con.execute('DELETE FROM channels WHERE channel_id = '+str(channel.id))
            now = datetime.datetime.utcnow()
            print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(channel.id) + '> is deleted.')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, str(error))
    
    @commands.group(name = "fetch", hidden = True)
    @commands.is_owner()
    async def _fetch(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Fetch subcommands", "tags, artists, characters, parodies, groups, hentai")


    @_fetch.command(name="tags", hidden = True, aliases=['tag', 't'])
    @commands.is_owner()
    async def _fetch_tags(self, ctx):
        now = datetime.datetime.utcnow()
        await self.GetTags('tags','tag_name')
        print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] tags table updated.')

    @_fetch.command(name="artists", hidden = True, aliases=['artist','ats', 'as', 'a'])
    @commands.is_owner()
    async def _fetch_artists(self, ctx):
        now = datetime.datetime.utcnow()
        await self.GetTags('artists','artist_name')
        print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] artists table updated.')

    @_fetch.command(name="characters", hidden = True, aliases=['character', 'char', 'ch', 'c'])
    @commands.is_owner()
    async def _fetch_characters(self, ctx):
        now = datetime.datetime.utcnow()
        await self.GetTags('characters','character_name')
        print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] characters table updated.')

    @_fetch.command(name="parodies", hidden = True, aliases=['parody', 'prd', 'p'])
    @commands.is_owner()
    async def _fetch_parodies(self, ctx):
        now = datetime.datetime.utcnow()
        await self.GetTags('parodies','parody_name')
        print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] parodies table updated.')

    @_fetch.command(name="groups", hidden = True, aliases=['group', 'g'])
    @commands.is_owner()
    async def _fetch_groups(self, ctx):
        now = datetime.datetime.utcnow()
        await self.GetTags('groups','group_name')
        print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] groups table updated.')

    @_fetch.command(name="hentai", hidden = True, aliases=['h'])
    @commands.is_owner()
    async def _fetch_hentai(self, ctx):
        async with self.bot.dbPool.acquire() as con:
            async with aiohttp.ClientSession() as session:
                soup = None
                newestHentaiId = 0
                async with session.get("https://nhentai.net/") as response:
                    text = await response.read()
                    soup = BeautifulSoup(text.decode('utf-8'), 'html5lib')
                    newestHentaiId = eval(soup.find(id = 'content').contents[2].div.a['href'].split('/')[2])
                for i in range(1, newestHentaiId+1):
                    print("Doing #ID: " + str(i))
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

    @commands.command(name='set', pass_context=True, aliases=['s'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _set(self, ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            channel = await self.ReturnChannelIfExist(ctx, arg)
            if channel != None:
                now = datetime.datetime.utcnow()
                sql = 'INSERT INTO channels(channel_id, guild_id) VALUES('+str(channel.id)+', '+str(ctx.message.guild.id)+') ON CONFLICT DO NOTHING'
                status = await con.execute(sql)
                if (eval(status[-1])):
                    await self.UpdateField('channels', 'excluded_tags', self.bot.safeExclusion, 'channel_id', channel.id)
                    print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(channel.id) + '> set.')
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) has been set."
                    await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
                    await channel.edit(nsfw=True)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is already set."
                    await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, "Invalid argument. Please use `set #channel_name`")

    @commands.command(name='unset', pass_context=True, aliases=['us'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _unset(self, ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            channel = await self.ReturnChannelIfExist(ctx, arg)
            if channel != None:
                now = datetime.datetime.utcnow()
                sql = 'DELETE FROM channels WHERE channel_id = '+str(channel.id)
                status = await con.execute(sql)
                if (eval(status[-1])):
                    print('[' + now.strftime("%Y-%m-%d %H:%M:%S") +'] <' + str(ctx.message.channel.id) + '> unset.')
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) has been unset."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
                    await channel.edit(nsfw=False)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self,ctx, "Invalid argument. Please use `unset #channel_name`")
    
    @commands.group(name='get', pass_context=True, aliases=['g'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _get(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Include Subcommands", "`include`, `exclude`, `language`, `channels`, `channel`.")

    @_get.command(name='include', pass_context=True, aliases=['inc', 'in', 'i'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _get_include(self, ctx, arg = None):
        await self.GetChannelProperty(ctx, arg, 'include', 'included_tags', 'Included Tags', "all")
    
    @_get.command(name='exclude', pass_context=True, aliases=['exc', 'ex', 'e'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _get_exclude(self, ctx, arg = None):
        await self.GetChannelProperty(ctx, arg, 'exclude', 'excluded_tags', 'Excluded Tags', "none")
    
    @_get.command(name='language', pass_context=True, aliases=['lan', 'ln', 'l'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _get_language(self, ctx, arg = None):
        await self.GetChannelProperty(ctx, arg, 'language', 'languages', 'Languages', "all")
    
    @_get.command(name='allchannels', pass_context=True, aliases=['chans', 'chs', 'cs', 'allchan', 'allchans', 'ac', 'allc'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _get_all_channels(self, ctx):
        async with self.bot.dbPool.acquire() as con:
            outmsg = ""
            rows = await con.fetch('SELECT channel_id FROM channels WHERE guild_id = '+str(ctx.message.guild.id))
            for row in rows:
                channel = self.bot.get_channel(row[0])
                outmsg += "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/)\n"
            outmsg = outmsg[:-1]
            embedMessage = discord.Embed(
                        color = discord.Color(self.bot.embedColor),
                        description = "Total Channels: " + str(len(rows))
                    )
            embedMessage.add_field(name="Channels", value= outmsg, inline=False)
            await ctx.send(embed = embedMessage)

    @_get.command(name='channelinfo', pass_context=True, aliases=['channel', 'chan', 'ch', 'c', 'ci'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _get_channelinfo(self, ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            channel = await self.ReturnChannelIfExist(ctx, arg)

            if channel != None:
                is_exist = await shareFunc.IsExistInDatabase(self,'channels','channel_id',channel.id)
                if (is_exist):
                    row = await con.fetchrow('SELECT included_tags, excluded_tags, languages FROM channels WHERE channel_id = '+str(channel.id))
                    outinc = await shareFunc.SetToString(row[0], "`all`")
                    outexc = await shareFunc.SetToString(row[1], "`none`")
                    outlan = await shareFunc.SetToString(row[2], "`all`")
                    embedMessage = discord.Embed(
                                color = discord.Color(self.bot.embedColor),
                                description = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/)"
                            )
                    embedMessage.add_field(name="Included Tags", value= outinc, inline=False)
                    embedMessage.add_field(name="Excluded Tags", value= outexc, inline=False)
                    embedMessage.add_field(name="Language", value= outlan, inline=False)
                    await ctx.send(embed = embedMessage)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
            else:
                await shareFunc.SendDescriptionOnlyEmbed(self,ctx, "Invalid argument. Please use `get channelinfo #channel_name`")

    @commands.group(name='include', pass_context=True, aliases=['inc', 'in', 'i'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _include(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Include Subcommands", "`add`, `remove`, `reset`.")

    @_include.command(name='add', pass_context=True, aliases=['a', '+'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _include_add(self, ctx, *args: to_lower):
        await self.AddRemove(ctx, 'include', 'add', *args)

    @_include.command(name='remove', pass_context=True, aliases=['rm', 'r', '-'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _include_remove(self, ctx, *args: to_lower):
        await self.AddRemove(ctx, 'include', 'remove', *args)

    @_include.command(name='reset', pass_context=True, aliases=['clear', 'c', 'rs'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _include_reset(self, ctx, arg = None):
        await self.Reset(ctx, 'include', arg)
        
    @commands.group(name='exclude', pass_context=True, aliases=['exc', 'ex', 'e'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _exclude(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Exclude Subcommands", "`add`, `remove`, `reset`, `resetunsafe`.")

    @_exclude.command(name='add', pass_context=True, aliases=['a', '+'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _exclude_add(self, ctx, *args: to_lower):
        await self.AddRemove(ctx, 'exclude', 'add', *args)

    @_exclude.command(name='remove', pass_context=True, aliases=['rm', 'r', '-'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _exclude_remove(self, ctx, *args: to_lower):
        await self.AddRemove(ctx, 'exclude', 'remove', *args)

    @_exclude.command(name='reset', pass_context=True, aliases=['clear', 'c', 'rs'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _exclude_reset(self, ctx, arg = None):
        channel = await self.Reset(ctx, 'exclude', arg)
        await self.UpdateField('channels', 'excluded_tags', self.bot.safeExclusion, 'channel_id', channel.id)

    @_exclude.command(name='resetunsafe', pass_context=True, aliases=['rsus','us'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _exclude_reset_unsafe(self, ctx, arg = None):
        await self.Reset(ctx, 'exclude', arg)

    @commands.group(name='language', pass_context=True, aliases=['lan', 'ln', 'l'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _language(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Langauge Subcommands", "`add`, `remove`, `reset`.")

    @_language.command(name='add', pass_context=True, aliases=['a', '+'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _language_add(self, ctx, *args: to_lower):
        await self.AddRemove(ctx, 'language', 'add', *args)

    @_language.command(name='remove', pass_context=True, aliases=['rm', 'r', '-'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _language_remove(self, ctx, *args: to_lower):
        await self.AddRemove(ctx, 'language', 'remove', *args)

    @_language.command(name='reset', pass_context=True, aliases=['clear', 'c', 'rs'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _language_reset(self, ctx, arg = None):
        await self.Reset(ctx, 'language', arg)

    
    @commands.command(name='reset', pass_context=True, aliases=['rs'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _reset(self, ctx, arg = None):
        channel = await self.ResetAll(ctx, 'reset', arg)
        await self.UpdateField('channels', 'excluded_tags', self.bot.safeExclusion, 'channel_id', channel.id)

    @commands.command(name='resetunsafe', pass_context=True, aliases=['rsus'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _reset_unsafe(self, ctx, arg = None):
        await self.ResetAll(ctx, 'resetunsafe', arg)

    @commands.group(name='clone', pass_context=True, aliases=['cln', 'cl', 'c'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _clone(self,ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Clone Subcommands", "`include`, `exclude`, `language`, `all`.")

    @_clone.command(name='include', pass_context=True, aliases=['inc', 'in', 'i'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _clone_include(self, ctx, *args):
        await self.CloneSetting(ctx, 'include', args)

    @_clone.command(name='exclude', pass_context=True, aliases=['exc', 'ex', 'e'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _clone_exclude(self, ctx, *args):
        await self.CloneSetting(ctx, 'exclude', args)

    @_clone.command(name='language', pass_context=True, aliases=['lan', 'ln', 'l'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _clone_language(self, ctx, *args):
        await self.CloneSetting(ctx, 'include', args)

    @_clone.command(name='all', pass_context=True, aliases=['a'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _clone_all(self, ctx, *args):
        await self.CloneSetting(ctx, 'all', args)

    @commands.group(name='test', pass_context=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _test(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self,ctx,"Test Subcommands", "`channel`, `guild`.")

    @_test.command(name='channel', pass_context=True, aliases=['c', 'ch'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _test_channel(self, ctx, *args):
        async with self.bot.dbPool.acquire() as con:
            channel = None
            if len(args)>0:
                try:
                    channel_input = eval(args[0].split("#")[1][:-1])
                    channel = self.bot.get_channel(channel_input)
                    if (len(args) > 1):
                        testLimit = args[1]
                    else:
                        testLimit = 10
                except:
                    channel = ctx.message.channel
                    testLimit = args[0]

                if channel != None:
                    is_exist = await shareFunc.IsExistInDatabase(self, 'channels','channel_id',channel.id)
                    if (is_exist):
                        try:
                            num = eval(testLimit)
                            if (num > 20):
                                num = 20
                            elif (num < 1):
                                num = 1
                        except:
                            num = 10

                        channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels WHERE channel_id = ' + str(channel.id) + ';')
                        hentaiRows = await con.fetch('SELECT * FROM hentai ORDER BY id DESC LIMIT ' + str(num) +';')
        
                        for i in range (len(hentaiRows)-1, -1, -1):
                            await self.Notify(hentaiRows[i], channelRows)

                    else:
                        outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                        await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)
            else:
                channel = ctx.message.channel
                is_exist = await shareFunc.IsExistInDatabase(self, 'channels','channel_id',channel.id)
                if (is_exist):
                    num = 10

                    channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels WHERE channel_id = ' + str(channel.id) + ';')
                    hentaiRows = await con.fetch('SELECT * FROM hentai ORDER BY id DESC LIMIT ' + str(num) +';')
                    for i in range (len(hentaiRows)-1, -1, -1):
                        await self.Notify(hentaiRows[i], channelRows)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self,ctx, outmsg)


    @_test.command(name='guild', pass_context=True, aliases=['g', 'server', 'sv', 's'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _test_guild(self,ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            num = 10
            if (arg != None):
                try:
                    num = eval(arg)
                    if (num > 20):
                        num = 20
                    elif (num < 1):
                        num = 1
                except:
                    num = 10
            channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels WHERE guild_id = '+str(ctx.message.guild.id))
            if (len(channelRows) > 0):
                hentaiRows = await con.fetch('SELECT * FROM hentai ORDER BY id DESC LIMIT ' + str(num) +';')
                for i in range (len(hentaiRows)-1, -1, -1):
                    await self.Notify(hentaiRows[i], channelRows)
            else:
                outmsg = "No set channels."
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
    
    @commands.group(name='testdelete', pass_context=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _testdelete(self, ctx):
        if (ctx.invoked_subcommand is None):
            await shareFunc.SendFieldOnlyEmbed(self, ctx,"Testdelete Subcommands", "`channel`, `guild`.")

    @_testdelete.command(name='channel', pass_context=True, aliases=['c', 'ch'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _testdelete_channel(self, ctx, *args):
        async with self.bot.dbPool.acquire() as con:
            channel = None
            if len(args)>0:
                try:
                    channel_input = eval(args[0].split("#")[1][:-1])
                    channel = self.bot.get_channel(channel_input)
                    if (len(args) > 1):
                        testLimit = args[1]
                    else:
                        testLimit = 10
                except:
                    channel = ctx.message.channel
                    testLimit = args[0]

                if channel != None:
                    is_exist = await shareFunc.IsExistInDatabase(self, 'channels','channel_id',channel.id)
                    if (is_exist):
                        try:
                            num = eval(testLimit)
                            if (num > 20):
                                num = 20
                            elif (num < 1):
                                num = 1
                        except:
                            num = 10
                        channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels WHERE channel_id = ' + str(channel.id) + ';')
                        hentaiRows = await con.fetch('SELECT * FROM hentai ORDER BY id DESC LIMIT ' + str(num) +';')
                        msg = []
                        for i in range (len(hentaiRows)-1, -1, -1):
                            m = await self.Notify(hentaiRows[i], channelRows)
                            msg += m
                        await asyncio.sleep(10)
                        for message in msg:
                            await message.delete()
                    else:
                        outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                        await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
            else:
                channel = ctx.message.channel
                is_exist = await shareFunc.IsExistInDatabase(self, 'channels','channel_id',channel.id)
                if (is_exist):
                    num = 10

                    channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels WHERE channel_id = ' + str(channel.id) + ';')
                    hentaiRows = await con.fetch('SELECT * FROM hentai ORDER BY id DESC LIMIT ' + str(num) +';')
                    for i in range (len(hentaiRows)-1, -1, -1):
                        await self.Notify(hentaiRows[i], channelRows)
                else:
                    outmsg = "["+str(channel)+"](https://discordapp.com/channels/"+str(ctx.message.guild.id) + "/" + str(channel.id) + "/) is not set."
                    await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)


    @_testdelete.command(name='guild', pass_context=True, aliases=['g', 'server', 'sv', 's'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _testdelete_guild(self,ctx, arg = None):
        async with self.bot.dbPool.acquire() as con:
            num = 10
            if (arg != None):
                try:
                    num = eval(arg)
                    if (num > 20):
                        num = 20
                    elif (num < 1):
                        num = 1
                except:
                    num = 10
            channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels WHERE guild_id = '+str(ctx.message.guild.id))
            if (len(channelRows) > 0):
                msg = []
                hentaiRows = await con.fetch('SELECT * FROM hentai ORDER BY id DESC LIMIT ' + str(num) +';')
                for i in range (len(hentaiRows)-1, -1, -1):
                    m = await self.Notify(hentaiRows[i], channelRows)
                    msg += m
                
                await asyncio.sleep(10)
                for message in msg:
                    message.delete()
            else:
                outmsg = "No set channels."
                await shareFunc.SendDescriptionOnlyEmbed(self, ctx, outmsg)
     
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
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name= str(newestHentaiId) + " [" + now.strftime("%H:%M") + " UTC]"))
                    channelRows = await con.fetch('SELECT channel_id, included_tags, excluded_tags, languages FROM channels ORDER BY guild_id ASC;')
                    for i in range(self.bot.latestID+1, newestHentaiId+1):
                        hentaiRow = await con.fetchrow('SELECT * FROM hentai WHERE id = ' + str(i))
                        await self.Notify(hentaiRow, channelRows)
                    await self.bot.GetLatestID()

def setup(bot):
    bot.add_cog(NHentai_Feed(bot))