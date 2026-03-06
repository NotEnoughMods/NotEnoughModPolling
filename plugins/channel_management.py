import logging

from command_router import Permission

PLUGIN_ID = "channel_management"

logger = logging.getLogger("cmd.channel_management")


async def _join(router, name, params, channel, userdata, rank, is_channel):
    channels = params
    finchan = []

    for chan in channels:
        if chan[0] != "#":
            finchan.append("#" + chan)
        else:
            finchan.append(chan)

    if len(finchan) > 0:
        await router.join_channel(router.send, finchan)
    else:
        await router.send_notice(name, "Please specify a channel")


async def _part(router, name, params, channel, userdata, rank, is_channel):
    channels = []

    if len(params) == 0 and is_channel:
        channels.append(channel)
    elif len(params) == 0 and not is_channel:
        await router.send_notice(name, "Please specify a channel")
        return
    else:
        for chan_entry in params:
            if chan_entry[0] != "#":
                chan_entry = "#" + chan_entry

            chan = router.get_channel_true_case(chan_entry)
            if chan:
                channels.append(chan)
            else:
                logger.debug("Unknown channel: %s", chan_entry)

    part_params = ",".join(channels)
    logger.debug("Parting: %s (channels=%s)", part_params, channels)

    if len(part_params) > 0:
        await router.send("PART :" + part_params + "", 4)
        for chan in channels:
            del router.channel_data[chan]


async def _rejoin(router, name, params, channel, userdata, rank, is_channel):
    channels = []
    if len(params) == 0:
        channels.append(channel)
    else:
        for chan in params:
            chan = router.get_channel_true_case(chan)
            if chan:
                if chan[0] != "#":
                    channels.append("#" + chan)
                else:
                    channels.append(chan)

    part_params = ",".join(channels)
    logger.debug("Rejoining: %s (channels=%s)", part_params, channels)
    await router.send("PART :" + part_params + "", 4)
    for chan in channels:
        del router.channel_data[chan]

    await router.join_channel(router.send, channels)


async def _channels(router, name, params, channel, userdata, rank, is_channel):
    channels = ", ".join(router.channel_data.keys())
    await router.send_notice(name, f"I'm currently connected to the following channels: {channels}")


async def setup(router, startup):
    entry = router.helper.new_help("join")
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
    router.helper.register_help(entry, overwrite=True)

    entry = router.helper.new_help("part")
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
    router.helper.register_help(entry, overwrite=True)

    entry = router.helper.new_help("rejoin")
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
    entry.rank = 3
    router.helper.register_help(entry, overwrite=True)


COMMANDS = {
    "join": {"execute": _join, "permission": Permission.ADMIN, "allow_private": True},
    "part": {"execute": _part, "permission": Permission.ADMIN, "allow_private": True},
    "rejoin": {"execute": _rejoin, "permission": Permission.ADMIN},
    "channels": {"execute": _channels, "permission": Permission.ADMIN, "allow_private": True},
}
