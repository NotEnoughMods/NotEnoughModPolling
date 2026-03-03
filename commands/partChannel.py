ID = "part"
permission = 3
privmsgEnabled = True

async def execute(self, name, params, channel, userdata, rank, isChannel):
    channels = []

    if len(params) == 0 and isChannel:
        channels.append(channel)
    elif len(params) == 0 and not isChannel:
        await self.sendNotice(name, "Please specify a channel")
        return
    else:
        for chanEntry in params:
            if chanEntry[0] != "#":
                chanEntry = "#"+chanEntry

            chan = self.retrieveTrueCase(chanEntry)
            if chan != False:
                channels.append(chan)
            else:
                print(chanEntry, "wat")

    partParams = ",".join(channels)
    print(partParams)
    print(channels)

    if len(partParams) > 0:
        await self.send("PART :"+partParams+"", 4)
        for chan in channels:
            del self.channelData[chan]

async def setup(self, Startup):
    entry = self.helper.newHelp(ID)

    entry.addDescription("The command tells the bot to part from one or several channels. Several channels are delimited with whitespace.")
    entry.addDescription("You can prepend # to each channel name yourself, or omit it. If omitted, the bot will add # to the channel name.")
    entry.addArgument("channel", "The name of the first channel the bot should part from.")
    entry.addArgument("other channels", "Other channels the bot should part from, each delimited by whitespace.", optional = True)
    entry.rank = 3

    self.helper.registerHelp(entry, overwrite = True)
    