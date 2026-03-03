ID = "NICK"


async def execute(self, sendMsg, prefix, command, params):
    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    newName = params[1:]
    print("NICKCHANGE")

    if self.auth_tracker.doesExist(name):
        self.auth_tracker.unregisterUser(name)

    if self.auth_tracker.doesExist(newName):
        await self.whoisUser(newName)

    affectedChannels = []
    for chan in self.channel_data:
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                self.channel_data[chan]["Userlist"][i] = (newName, pref)
                affectedChannels.append(chan)
                break

    await self.events["nickchange"].tryAllEvents(self, name, newName, ident, host, affectedChannels)
