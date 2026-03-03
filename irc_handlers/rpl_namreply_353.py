ID = "353"


async def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ", 3)
    channel = data[2]
    users = data[3]
    print(users)
    for name in users[1:].split(" "):
        if "@" in name[0] or "+" in name[0]:
            self.channel_data[self.get_channel_true_case(channel)]["Userlist"].append((name[1:], name[0]))
            name = name[1:]
        else:
            self.channel_data[self.get_channel_true_case(channel)]["Userlist"].append((name, ""))

        if (
            self.auth_tracker.user_exists(name)
            and not self.auth_tracker.is_registered(name)
            and not self.auth_tracker.is_queued(name)
        ):
            # print "OK"
            await self.whois_user(name)
    # print params
