ID = "KICK"


async def execute(self, sendMsg, prefix, command, params):
    print("SOMEBODY WAS KICKED:")
    print(prefix)
    print(params)

    fields = params.split(" ")

    channel = fields[0]
    name = fields[1]
    kickreason = fields[2]

    chan = self.retrieveTrueCase(channel)

    await self.events["channelkick"].tryAllEvents(self, name, chan, kickreason)

    if chan:
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, _pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                del self.channel_data[chan]["Userlist"][i]
                break

    if self.auth_tracker.doesExist(name) and self.auth_tracker.isRegistered(name) and not self.userInSight(name):
        self.auth_tracker.unregisterUser(name)
