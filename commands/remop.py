import logging

ID = "remop"
permission = 3


def not_in_list(user, userlist):
    for name in userlist:
        if name.lower() == user.lower():
            return (False, name)

    return (True, "NOPE")


async def execute(self, username, params, channel, userdata, rank):
    names = params
    notremoved = []
    removed = []

    for name in names:
        result, correct_name = not_in_list(name, self.operators)
        if not result and correct_name != username:
            self.operators.remove(correct_name)
            removed.append(correct_name)
            self.auth_tracker.unregister_user(correct_name)
            self.auth_tracker.remove_user(correct_name)
            if self.auth_tracker.is_queued(correct_name):
                self.auth_tracker.unqueue_user(correct_name)
        else:
            notremoved.append(name)

    if len(removed) > 0:
        logging.info("User '%s' has removed user(s) '%s'", username, ", ".join(removed))
        await self.send_chat_message(self.send, channel, "Removed " + ", ".join(removed))
    if len(notremoved) > 0:
        await self.send_chat_message(self.send, channel, "Didn't remove " + ", ".join(notremoved))
