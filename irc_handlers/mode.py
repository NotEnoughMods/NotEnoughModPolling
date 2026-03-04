import logging

ID = "MODE"

logger = logging.getLogger("irc.mode")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("Mode change: %s %s", prefix, params)
    splitted = params.split(" ")

    if len(splitted) == 3:
        chan = self.get_channel_true_case(splitted[0])
        modes = splitted[1]
        name = splitted[2]

        add = modes[0] == "+"
        perm = ""

        if self.auth_tracker.user_exists(name) and not self.auth_tracker.is_registered(name):
            await self.whois_user(name)

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
