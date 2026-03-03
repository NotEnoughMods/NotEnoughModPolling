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
            self.auth_tracker.unregister_user(correctName)
            self.auth_tracker.remove_user(correctName)
            if self.auth_tracker.is_queued(correctName):
                self.auth_tracker.unqueue_user(correctName)
        else:
            notremoved.append(name)

    if len(removed) > 0:
        logging.info("User '%s' has removed user(s) '%s'", username, ", ".join(removed))
        await self.send_chat_message(self.send, channel, "Removed " + ", ".join(removed))
    if len(notremoved) > 0:
        await self.send_chat_message(self.send, channel, "Didn't remove " + ", ".join(notremoved))
