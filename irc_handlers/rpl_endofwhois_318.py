ID = "318"


async def execute(self, sendMsg, prefix, command, params):
    print("WHOIS RESULT: ", prefix, command, params)

    fields = params.split(":")
    print(fields[0], fields[1])

    names = fields[0].split(" ")
    print(",".join(names))
    username = names[1]
    names[2]

    if self.auth_tracker.is_queued(username) and self.auth_tracker.user_exists(username):
        if not self.auth_tracker.is_registered(username):
            # print "User is not registered"
            self.auth_tracker.unregister_user(username)
        else:
            pass
            # print "User is registered"

    if self.auth_tracker.is_queued(username):
        self.auth_tracker.unqueue_user(username)
