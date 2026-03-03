ID = "QUIT"

def execute(self, sendMsg, prefix, command, params):
    print("SOMEBODY LEFT SERVER:")
    print(prefix)
    print(params)
    
    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")
    
    name = part1[0]
    ident = part2[0]
    host = part2[2]
    
    quitReason = params[1:]
    print("SERVER LEAVE")
    print(name, ident, host)
    print(quitReason)

    self.events["userquit"].tryAllEvents(self, name, ident, host, quitReason)
    
    for chan in self.channelData:
        print(chan)
        for i in range(len(self.channelData[chan]["Userlist"])):
            user, pref = self.channelData[chan]["Userlist"][i]
            if user == name:
                del self.channelData[chan]["Userlist"][i]
                break
    
    if self.Bot_Auth.doesExist(name) and self.Bot_Auth.isRegistered(name):
        print("HE DIED")
        self.Bot_Auth.unregisterUser(name)