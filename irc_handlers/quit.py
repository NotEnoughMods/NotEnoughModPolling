ID = "QUIT"


async def execute(self, sendMsg, prefix, command, params):
    print("SOMEBODY LEFT SERVER:")
    print(prefix)
    print(params)

    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    quitReason = params[1:]
    print("SERVER LEAVE")
    print(name, ident, host)
    print(quitReason)

    await self.events["userquit"].tryAllEvents(self, name, ident, host, quitReason)

    for chan in self.channel_data:
        print(chan)
        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, _pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                del self.channel_data[chan]["Userlist"][i]
                break

    if self.auth_tracker.doesExist(name) and self.auth_tracker.isRegistered(name):
        print("HE DIED")
        self.auth_tracker.unregisterUser(name)
