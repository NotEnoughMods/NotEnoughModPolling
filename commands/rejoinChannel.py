ID = "rejoin"
permission = 3

async def execute(self, name, params, channel, userdata, rank):
    channels = []
    if len(params) == 0:
        channels.append(channel)
    else:
        for chan in params:
            chan = self.retrieveTrueCase(chan)
            if chan != False:
                if chan[0] != "#":
                    channels.append("#"+chan)
                else:
                    channels.append(chan)


    partParams = ",".join(channels)
    print(partParams)
    print(channels)
    await self.send("PART :"+partParams+"", 4)
    for chan in channels:
        del self.channelData[chan]

    await self.joinChannel(self.send, channels)

async def setup(self, Startup):
    entry = self.helper.newHelp(ID)

    entry.addDescription("The 'rejoin' command makes the bot rejoin either the current channel, or the channels you have specified.")
    entry.addDescription("When rejoining several channels, the channel names should be delimited by spaces. ")
    entry.addDescription("There is no built-in limit on how many channels can be rejoined, but too many channels can cause the bot to exceed the 512 character limit on IRC.")
    entry.addArgument("channel 1", "The first channel to be rejoined.", optional = True)
    entry.addArgument("channel 2", "The second channel to be rejoined.", optional = True)
    entry.addArgument("channel n", "The n-th channel to be rejoined.", optional = True)
    entry.rank = permission

    self.helper.registerHelp(entry, overwrite = True)