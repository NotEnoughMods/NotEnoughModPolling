import logging

ID = "NICK"

logger = logging.getLogger("irc.nick")


async def execute(self, send_msg, prefix, command, params):
    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    new_name = params[1:]
    logger.debug("Nick change: %s -> %s", name, new_name)

    if self.auth_tracker.user_exists(name):
        self.auth_tracker.unregister_user(name)

    if self.auth_tracker.user_exists(new_name):
        await self.whois_user(new_name)

    affected_channels = []
    for chan in self.channel_data:
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                self.channel_data[chan]["Userlist"][i] = (new_name, pref)
                affected_channels.append(chan)
                break

    await self.events["nickchange"].run_all_events(self, name, new_name, ident, host, affected_channels)
