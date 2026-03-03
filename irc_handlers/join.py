ID = "JOIN"


async def execute(self, sendMsg, prefix, command, params):
    print("SOMEBODY JOINED CHANNEL:")
    print(prefix)
    print(params)

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

    channel = self.retrieveTrueCase(chan)

    if self.auth_tracker.doesExist(name) and not self.auth_tracker.isRegistered(name):
        await self.whoisUser(name)

    await self.events["channeljoin"].tryAllEvents(self, name, ident, host, channel)

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
            "Channel mismatch: %s has joined channel '%s', But retrieveTrueCase returned False.",
            name,
            params,
        )
