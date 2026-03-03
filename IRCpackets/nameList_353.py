ID = "353"

def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ", 3)
    channel = data[2]
    users = data[3]
    print(users)
    for name in users[1:].split(" "):
        if "@" in name[0] or "+" in name[0]:
            self.channelData[self.retrieveTrueCase(channel)]["Userlist"].append((name[1:], name[0]))
            name = name[1:]
        else:
            self.channelData[self.retrieveTrueCase(channel)]["Userlist"].append((name, ""))
            
        if self.Bot_Auth.doesExist(name) and not self.Bot_Auth.isRegistered(name) and not self.Bot_Auth.isQueued(name):
            #print "OK"
            self.whoisUser(name)
    #print params