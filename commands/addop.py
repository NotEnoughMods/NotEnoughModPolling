import logging

ID = "addop"
permission = 3


def not_in_list(user, userlist):
    return all(name.lower() != user.lower() for name in userlist)


async def execute(self, username, params, channel, userdata, rank):
    names = params

    for name in names:
        if not_in_list(name, self.operators):
            self.operators.append(name)
            self.auth_tracker.add_user(name)
            await self.whois_user(name)

    logging.info("User '%s' has added user(s) '%s'", username, ", ".join(names))
    await self.send_chat_message(self.send, channel, "Added " + ", ".join(names))
