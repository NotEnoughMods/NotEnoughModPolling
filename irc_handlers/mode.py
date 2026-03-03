ID = "MODE"


async def execute(self, sendMsg, prefix, command, params):
    print(prefix, params)
    splitted = params.split(" ")

    print(splitted)
    if len(splitted) == 3:
        chan = self.retrieveTrueCase(splitted[0])
        modes = splitted[1]
        name = splitted[2]

        add = modes[0] == "+"
        perm = ""

        if self.auth_tracker.doesExist(name) and not self.auth_tracker.isRegistered(name) and not self.auth_tracker.isQueued(name):
            await self.whoisUser(name)

        for char in modes[1:]:
            if char == "v" and perm == "":
                perm = "+"
            if char == "o":
                perm = "@"

        for i in range(len(self.channel_data[chan]["Userlist"])):
            user, pref = self.channel_data[chan]["Userlist"][i]
            if user == name:
                if add:
                    if pref != "@":
                        self.channel_data[chan]["Userlist"][i] = (user, perm)
                else:
                    self.channel_data[chan]["Userlist"][i] = (user, "")

                break

    # if modes[0] == "+" and "v" in modes:
    #    pass

    # NyanServ!nyaaaaaan@kitty.services.esper.net #SinZationalMinecraft +v Yoshi2
