ID = "join"
permission = 3
privmsgEnabled = True


async def execute(self, name, params, channel, userdata, rank, chan):

    channels = params
    finchan = []

    for chan in channels:
        if chan[0] != "#":
            finchan.append("#" + chan)
        else:
            finchan.append(chan)

    if len(finchan) > 0:
        await self.join_channel(self.send, finchan)
    else:
        await self.send_notice(name, "Please specify a channel")


async def setup(self, startup):
    entry = self.helper.new_help(ID)

    entry.add_description(
        "The command tells the bot to join one or several channels. Several channels are delimited with whitespace."
    )
    entry.add_description(
        "You can prepend # to each channel name yourself, or omit it. "
        "If omitted, the bot will add # to the channel name."
    )
    entry.add_argument("channel", "The name of the first channel the bot should join.")
    entry.add_argument(
        "other channels",
        "Other channels the bot should join, each delimited by whitespace.",
        optional=True,
    )
    entry.rank = 3

    self.helper.register_help(entry, overwrite=True)
