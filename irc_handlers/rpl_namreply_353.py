ID = "353"


async def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ", 3)
    channel = data[2]
    users = data[3]
    print(users)
    for name in users[1:].split(" "):
        if "@" in name[0] or "+" in name[0]:
            self.channel_data[self.retrieveTrueCase(channel)]["Userlist"].append((name[1:], name[0]))
            name = name[1:]
        else:
            self.channel_data[self.retrieveTrueCase(channel)]["Userlist"].append((name, ""))

        if self.auth_tracker.doesExist(name) and not self.auth_tracker.isRegistered(name) and not self.auth_tracker.isQueued(name):
            # print "OK"
            await self.whoisUser(name)
    # print params
