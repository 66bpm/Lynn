import asyncio
import asyncpg
import discord

async def GetSimilar(cog, table, key, value):
    async with cog.bot.dbPool.acquire() as con:
        sql = "(SELECT DISTINCT "+str(key)+" FROM "+str(table)+" WHERE "+str(key)+" > '"+ str(value)+ "' ORDER BY "+str(key)+" LIMIT 2) UNION ALL (SELECT DISTINCT "+str(key)+" FROM "+str(table)+" WHERE "+str(key)+" < '"+str(value)+"' ORDER BY "+str(key)+" DESC LIMIT 2);"
        rows = await con.fetch(sql)
        if (rows != None):
            similar = ""
            for ele in rows:
                similar += "`"+ str(ele[0]) + "`, "
            return similar[:-2]
        else:
            return "-"

async def SetToString(data, textWhenNone):
    if (data != None):
        outinc = ""
        for ele in data:
            outinc += "`" + str(ele) + "`, "
        return outinc[:-2]
    return "`" + textWhenNone + "`"

async def EmbedFormatter(cog, row):
    id = str(row[0])
    title = str(row[1])
    cover = str(row[2])
    parodies = await SetToString(row[3], "")
    characters = await SetToString(row[4], "")
    tags = await SetToString(row[5], "")
    artists = await SetToString(row[6], "")
    groups = await SetToString(row[7], "")
    languages = await SetToString(row[8], "")
    categories = await SetToString(row[9], "")
    pages = str(row[10])
    link = "https://nhentai.net/g/"+ id + "/"
    embedMessage = discord.Embed(
            title = title,
            url = link,
            color = discord.Color(cog.bot.embedColor),
            description = "#"+ str(id)
    )
    if len(parodies) > 2:
        embedMessage.add_field(name="Parodies", value= parodies, inline=False)
    if len(characters) > 2:
        embedMessage.add_field(name="Characters", value= characters, inline=False)
    if len(tags) > 2:
        embedMessage.add_field(name="Tags", value= tags, inline=False)
    if len(artists) > 2:
        embedMessage.add_field(name="Aatists", value= artists, inline=False)
    if len(groups) > 2:
        embedMessage.add_field(name="Groups", value= groups, inline=False)
    if len(languages) > 2:
        embedMessage.add_field(name="Languages", value= languages, inline=False)
    if len(categories) > 2:
        embedMessage.add_field(name="Categories", value= categories, inline=False)
    if len(pages) > 2:
        embedMessage.add_field(name="Pages", value= pages, inline=False)

    embedMessage.set_image(url=cover)
    return embedMessage

async def IsExistInDatabase(cog, table, key, value):
    async with cog.bot.dbPool.acquire() as con:
        sql = 'SELECT * FROM '+str(table)+' WHERE '+str(key)+' = '+ str(value)
        status = await con.execute(sql)
        if (eval(status[-1])):
            return True
        return False

async def SendDescriptionOnlyEmbed(cog, ctx, description):
    embedMessage = discord.Embed(
                color = discord.Color(cog.bot.embedColor),
                description = description
            )
    await ctx.send(embed = embedMessage)

async def SendFieldOnlyEmbed(cog, ctx, name, value):
    embedMessage = discord.Embed(
                color = discord.Color(cog.bot.embedColor),
            )
    embedMessage.add_field(name=name, value= value, inline=False)
    await ctx.send(embed = embedMessage)

async def Notify(cog, hentaiRow, channelRows):
        messages = []
        embedMessage = await EmbedFormatter(cog, hentaiRow)
        if (hentaiRow[5] != None): 
            tags = set(hentaiRow[5])
        else:
            tags = None
        if (hentaiRow[8] != None):
            hlan = set(hentaiRow[8])
        else:
            hlan = None
        for channelRow in channelRows:
            channel = cog.bot.get_channel(channelRow[0])
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