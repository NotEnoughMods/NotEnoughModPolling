import logging

ID = "353"

logger = logging.getLogger("irc.rpl.353")


async def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ", 3)
    channel = data[2]
    users = data[3]
    logger.debug("RPL_NAMREPLY for %s: %s", channel, users)
    for name in users[1:].split(" "):
        if "@" in name[0] or "+" in name[0]:
            self.channel_data[self.get_channel_true_case(channel)]["Userlist"].append((name[1:], name[0]))
            name = name[1:]
        else:
            self.channel_data[self.get_channel_true_case(channel)]["Userlist"].append((name, ""))

        if self.auth_tracker.user_exists(name) and not self.auth_tracker.is_registered(name):
            await self.whois_user(name)
