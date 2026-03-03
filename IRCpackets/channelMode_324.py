ID = "324"

def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ")
    
    channel = data[1]
    mode = data[2]
    
    self.channelData[self.retrieveTrueCase(channel)]["Mode"] = mode