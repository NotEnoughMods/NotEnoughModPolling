ID = "332"

def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ", 2)
    
    channel = data[1]
    topic = data[2][1:]
    #timestamp = data[3]
    
    try:
        self.channelData[self.retrieveTrueCase(channel)]["Topic"] = topic
    except:
        pass
    
    #print prefix, params