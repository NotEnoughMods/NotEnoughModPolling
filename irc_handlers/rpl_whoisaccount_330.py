ID = "330"


async def execute(self, sendMsg, prefix, command, params):
    print("WHOIS END: ", prefix, "-", command, "-", params)
    fields = params.split(":")
    print(fields[0], fields[1])

    names = fields[0].split(" ")
    # print ",".join(names)
    username = names[1]
    registeredAs = names[2]

    if fields[1].strip() == "is logged in as":
        # print "OK, NOW I AM SUPPOSED TO DO SOMETHING"
        if self.Bot_Auth.doesExist(username) and self.Bot_Auth.isQueued(username):
            # print "OK, user is queued, we need to do something"

            if self.Bot_Auth.doesExist(registeredAs):
                self.Bot_Auth.registerUser(username)
                # print "Yep, User is registered :D"
            else:
                self.Bot_Auth.unregisterUser(username)
                # print "nope, User is not registered :("
    else:
        print("NONSTANDARD FIELD: " + fields[1])
