import logging

ID = "KICK"

logger = logging.getLogger("irc.kick")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("Channel kick: %s %s", prefix, params)

    fields = params.split(" ")

    channel = fields[0]
    name = fields[1]
    kickreason = fields[2]

    chan = self.get_channel_true_case(channel)

    await self.events["channelkick"].run_all_events(self, name, chan, kickreason)

    if chan:
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, _pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                del self.channel_data[chan]["Userlist"][i]
                break

    if self.auth_tracker.user_exists(name) and self.auth_tracker.is_registered(name) and not self.is_user_visible(name):
        self.auth_tracker.unregister_user(name)
