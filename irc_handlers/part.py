ID = "PART"


async def execute(self, sendMsg, prefix, command, params):
    print("SOMEBODY LEFT CHANNEL:")
    print(prefix)
    print(params)

    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    print("CHANNEL LEAVE")

    if params.startswith(":"):
        chan_string = params.lstrip(":")
    else:
        param_list = params.split(" ")
        chan_string = param_list[0]

    channel = self.get_channel_true_case(chan_string)

    await self.events["channelpart"].run_all_events(self, name, ident, host, channel)

    if channel:
        for i in range(len(self.channel_data[channel]["Userlist"])):
            user, _pref = self.channel_data[channel]["Userlist"][i]
            if user == name:
                del self.channel_data[channel]["Userlist"][i]
                break
    else:
        self._logger.debug("Channel %s not found", params)

    if self.auth_tracker.user_exists(name) and self.auth_tracker.is_registered(name) and not self.is_user_visible(name):
        # print "OK, WE LOST SIGHT OF HIM"
        self.auth_tracker.unregister_user(name)
