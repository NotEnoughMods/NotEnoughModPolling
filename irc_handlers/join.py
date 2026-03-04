import logging

ID = "JOIN"

logger = logging.getLogger("irc.join")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("Channel join: %s %s", prefix, params)

    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    if not params.startswith(":"):
        param_list = params.split(" ")
        chan = param_list[0]
    else:
        chan = params.lstrip(":")

    channel = self.get_channel_true_case(chan)

    if self.auth_tracker.user_exists(name) and not self.auth_tracker.is_registered(name):
        await self.whois_user(name)

    await self.events["channeljoin"].run_all_events(self, name, ident, host, channel)

    if channel:
        nothere = True
        for derp in self.channel_data[channel]["Userlist"]:
            if derp[0] == name:
                nothere = False
                break

        if nothere:
            self.channel_data[channel]["Userlist"].append((name, ""))
        else:
            self._logger.debug(
                "%s has joined channel %s, but he is already in the user list!",
                name,
                channel,
            )
    else:
        self._logger.debug(
            "Channel mismatch: %s has joined channel '%s', But get_channel_true_case returned False.",
            name,
            params,
        )
