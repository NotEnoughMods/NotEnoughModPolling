import logging

ID = "part"
permission = 3
privmsg_enabled = True

logger = logging.getLogger("cmd.part")


async def execute(self, name, params, channel, userdata, rank, is_channel):
    channels = []

    if len(params) == 0 and is_channel:
        channels.append(channel)
    elif len(params) == 0 and not is_channel:
        await self.send_notice(name, "Please specify a channel")
        return
    else:
        for chan_entry in params:
            if chan_entry[0] != "#":
                chan_entry = "#" + chan_entry

            chan = self.get_channel_true_case(chan_entry)
            if chan:
                channels.append(chan)
            else:
                logger.debug("Unknown channel: %s", chan_entry)

    part_params = ",".join(channels)
    logger.debug("Parting: %s (channels=%s)", part_params, channels)

    if len(part_params) > 0:
        await self.send("PART :" + part_params + "", 4)
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
