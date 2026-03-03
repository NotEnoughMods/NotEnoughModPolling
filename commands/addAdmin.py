import logging

ID = "addop"
permission = 3


def notInList(user, userlist):
    return all(name.lower() != user.lower() for name in userlist)


async def execute(self, username, params, channel, userdata, rank):
    names = params

    for name in names:
        if notInList(name, self.bot_userlist):
            self.bot_userlist.append(name)
            self.Bot_Auth.addUser(name)
            await self.whoisUser(name)

    logging.info("User '%s' has added user(s) '%s'", username, ", ".join(names))
    await self.sendChatMessage(self.send, channel, "Added " + ", ".join(names))
