import logging

ID = "rejoin"
permission = 3

logger = logging.getLogger("cmd.rejoin")


async def execute(self, name, params, channel, userdata, rank):
    channels = []
    if len(params) == 0:
        channels.append(channel)
    else:
        for chan in params:
            chan = self.get_channel_true_case(chan)
            if chan:
                if chan[0] != "#":
                    channels.append("#" + chan)
                else:
                    channels.append(chan)

    partParams = ",".join(channels)
    logger.debug("Rejoining: %s (channels=%s)", partParams, channels)
    await self.send("PART :" + partParams + "", 4)
    for chan in channels:
        del self.channel_data[chan]

    await self.join_channel(self.send, channels)


async def setup(self, Startup):
    entry = self.helper.new_help(ID)

    entry.add_description(
        "The 'rejoin' command makes the bot rejoin either the current channel, or the channels you have specified."
    )
    entry.add_description("When rejoining several channels, the channel names should be delimited by spaces. ")
    entry.add_description(
        "There is no built-in limit on how many channels can be rejoined, but too many "
        "channels can cause the bot to exceed the 512 character limit on IRC."
    )
    entry.add_argument("channel 1", "The first channel to be rejoined.", optional=True)
    entry.add_argument("channel 2", "The second channel to be rejoined.", optional=True)
    entry.add_argument("channel n", "The n-th channel to be rejoined.", optional=True)
    entry.rank = permission

    self.helper.register_help(entry, overwrite=True)
