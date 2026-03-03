

ID = "JOIN"

async def execute(self, sendMsg, prefix, command, params):
    print("SOMEBODY JOINED CHANNEL:")
    print(prefix)
    print(params)
    
    part1 = prefix.partition("!")
    part2 = part1[2].partition("@")
    
    name = part1[0]
    ident = part2[0]
    host = part2[2]

    if not params.startswith(":"):
        param_list = params.split(" ")
        chan = param_list[0]
    else:
        chan = params.lstrip(":")

    channel = self.retrieveTrueCase(chan)
    
    if self.Bot_Auth.doesExist(name) and not self.Bot_Auth.isRegistered(name):
            await self.whoisUser(name)
    
    await self.events["channeljoin"].tryAllEvents(self, name, ident, host, channel)
    
    if channel != False:
        nothere = True
        for derp in self.channelData[channel]["Userlist"]:
            if derp[0] == name:
                nothere = False
                break
        
        if nothere:
            self.channelData[channel]["Userlist"].append((name, ""))
        else:
            self.__CMDHandler_log__.debug("%s has joined channel %s, "
                                          "but he is already in the user list!", name, channel)
    else:
        self.__CMDHandler_log__.debug("Channel mismatch: %s has joined channel '%s', "
                                      "But retrieveTrueCase returned False.", name, params)