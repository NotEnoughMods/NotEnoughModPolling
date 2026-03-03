import logging

ID = "part"
permission = 3
privmsgEnabled = True

logger = logging.getLogger("cmd.part")


async def execute(self, name, params, channel, userdata, rank, isChannel):
    channels = []

    if len(params) == 0 and isChannel:
        channels.append(channel)
    elif len(params) == 0 and not isChannel:
        await self.send_notice(name, "Please specify a channel")
        return
    else:
        for chanEntry in params:
            if chanEntry[0] != "#":
                chanEntry = "#" + chanEntry

            chan = self.get_channel_true_case(chanEntry)
            if chan:
                channels.append(chan)
            else:
                logger.debug("Unknown channel: %s", chanEntry)

    partParams = ",".join(channels)
    logger.debug("Parting: %s (channels=%s)", partParams, channels)

    if len(partParams) > 0:
        await self.send("PART :" + partParams + "", 4)
        for chan in channels:
            del self.channel_data[chan]


async def setup(self, startup):
    entry = self.helper.new_help(ID)

    entry.add_description(
        "The command tells the bot to part from one or several channels. "
        "Several channels are delimited with whitespace."
    )
    entry.add_description(
        "You can prepend # to each channel name yourself, or omit it. "
        "If omitted, the bot will add # to the channel name."
    )
    entry.add_argument("channel", "The name of the first channel the bot should part from.")
    entry.add_argument(
        "other channels",
        "Other channels the bot should part from, each delimited by whitespace.",
        optional=True,
    )
    entry.rank = 3

    self.helper.register_help(entry, overwrite=True)
