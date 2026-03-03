import logging

ID = "remop"
permission = 3


def notInList(user, userlist):
    for name in userlist:
        if name.lower() == user.lower():
            return (False, name)

    return (True, "NOPE")


async def execute(self, username, params, channel, userdata, rank):
    names = params
    notremoved = []
    removed = []

    for name in names:
        result, correctName = notInList(name, self.operators)
        if not result and correctName != username:
            self.operators.remove(correctName)
            removed.append(correctName)
            self.auth_tracker.unregisterUser(correctName)
            self.auth_tracker.remUser(correctName)
            if self.auth_tracker.isQueued(correctName):
                self.auth_tracker.unqueueUser(correctName)
        else:
            notremoved.append(name)

    if len(removed) > 0:
        logging.info("User '%s' has removed user(s) '%s'", username, ", ".join(removed))
        await self.sendChatMessage(self.send, channel, "Removed " + ", ".join(removed))
    if len(notremoved) > 0:
        await self.sendChatMessage(self.send, channel, "Didn't remove " + ", ".join(notremoved))
