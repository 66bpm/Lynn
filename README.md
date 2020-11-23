

# Lynn
A specialized Discord bot that notifies h-manga and h-doujinshi updates from nhentai. Use me if you don't want to open a web browser and get into incognito mode. [Invite Lynn](https://discord.com/api/oauth2/authorize?client_id=462920710424231936&permissions=3501248&scope=bot)


## Hello, degenerate user-san.
I am a specialized Discord bot that notifies h-manga and h-doujinshi updates from nhentai. Use me if you don't want to open a web browser and get into incognito mode.

- Setup channel as a hentai feed channel.
- Setup filter to include/exclude what you want and don't want to see.
- Get random or recent hentai by tag, character, parody, artist, group, or language.


## How to set an update channel (Admin only)
First we need to set up a channel using "lynn set" or "lynn set #channel". The channel you set will be the place where Lynn notifies new hentais. The bot checks nhentai every 10 mins. If there are new hentais bot will send them to setup channel.

Please give Lynn permission to manage a channel, send message, and embed link
To remove the setup channel, use "lynn unset" or "lynn unset #channel"

The setup will come with initial excluded tags that are related to substance, child pornography, and violence.

Currently Lynn doesn't have a website. Please use help command or visit [support server](https://discord.gg/aaqvqbeMCm) for more information.


Use "lynn help" to learn more about commands.


#### How inclusion filter works:
If new hentai has any tag in channel's tag inclusion, the hentai will be shown.
Else bot won't send a message


#### How exclusion filter works:
If new hentai has any tag in channel's tag exclusion, the hentai will be not shown.
Else bot will  send a message


#### How language filter works:
Similar to inclusion, but for language. Currently nhentai (or at least majority of them) are either in english, chinese, or japanese
