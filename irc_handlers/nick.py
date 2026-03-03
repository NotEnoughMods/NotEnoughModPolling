import logging

ID = "NICK"

logger = logging.getLogger("irc.nick")


async def execute(self, sendMsg, prefix, command, params):
    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    newName = params[1:]
    logger.debug("Nick change: %s -> %s", name, newName)

    if self.auth_tracker.user_exists(name):
        self.auth_tracker.unregister_user(name)

    if self.auth_tracker.user_exists(newName):
        await self.whois_user(newName)

    affectedChannels = []
    for chan in self.channel_data:
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                self.channel_data[chan]["Userlist"][i] = (newName, pref)
                affectedChannels.append(chan)
                break

    await self.events["nickchange"].run_all_events(self, name, newName, ident, host, affectedChannels)
