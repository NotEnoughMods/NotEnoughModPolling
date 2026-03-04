import logging

ID = "QUIT"

logger = logging.getLogger("irc.quit")


async def execute(self, send_msg, prefix, command, params):
    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    quit_reason = params[1:]
    logger.debug("User quit: %s (%s)", name, quit_reason)

    await self.events["userquit"].run_all_events(self, name, ident, host, quit_reason)

    for chan in self.channel_data:
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, _pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                del self.channel_data[chan]["Userlist"][i]
                break

    if self.auth_tracker.user_exists(name) and self.auth_tracker.is_registered(name):
        self.auth_tracker.unregister_user(name)
