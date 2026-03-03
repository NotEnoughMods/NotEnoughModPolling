ID = "join"
permission = 3
privmsgEnabled = True

def execute(self, name, params, channel, userdata, rank, chan):
    
    channels = params
    finchan = []
    
    for chan in channels:
        if chan[0] != "#":
            finchan.append("#"+chan)
        else:
            finchan.append(chan)
    
    if len(finchan) > 0:
        self.joinChannel(self.send, finchan)
    else:
        self.sendNotice(name, "Please specify a channel")
        
def __initialize__(self, Startup):
    entry = self.helper.newHelp(ID)
    
    entry.addDescription("The command tells the bot to join one or several channels. Several channels are delimited with whitespace.")
    entry.addDescription("You can prepend # to each channel name yourself, or omit it. If omitted, the bot will add # to the channel name.")
    entry.addArgument("channel", "The name of the first channel the bot should join.")
    entry.addArgument("other channels", "Other channels the bot should join, each delimited by whitespace.", optional = True)
    entry.rank = 3
    
    self.helper.registerHelp(entry, overwrite = True)