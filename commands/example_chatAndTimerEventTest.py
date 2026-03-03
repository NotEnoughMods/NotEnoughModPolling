ID = "chatevent"
permission = 3
privmsgEnabled = False

def timer(self, channels):
    self.sendChatMessage(self.send, channels[0], "pong")

def chatEvent(self, channels, userdata, message, currChannel):
    #print channels
    #print currChannel
    if channels != False:
        if currChannel in channels:
            self.sendChatMessage(self.send, currChannel, str(len(message)))
            if "start" in message:
                self.sendChatMessage(self.send, currChannel, "Starting time event")
                self.events["time"].addEvent("TimerTest", 10, timer, [currChannel], from_event = True)
            
            if "end" in message:
                self.sendChatMessage(self.send, currChannel, "Ending time event")
                self.events["time"].removeEvent("TimerTest", from_event = True)

def execute(self, name, params, channel, userdata, rank):
    #print "running"
    if len(params) == 1 and params[0] == "on":
        if not self.events["chat"].doesExist("TestFunc"):
            self.sendChatMessage(self.send, channel, "Turning chatevent on.")
            self.timerChannel = channel
            self.events["chat"].addEvent("TestFunc", chatEvent)
        else:
            self.sendChatMessage(self.send, channel, "chatevent is already running.")
            
    elif len(params) == 1 and params[0] == "off":
        if self.events["chat"].doesExist("TestFunc"):
            self.sendChatMessage(self.send, channel, "Turning chatevent off.") 
            self.events["chat"].removeEvent("TestFunc")
        else:
            self.sendChatMessage(self.send, channel, "chatevent isn't running!") 
    
    
    elif len(params) == 2 and params[0] == "add":
        channel = self.retrieveTrueCase(params[1])
        
        if channel != False:
            self.sendChatMessage(self.send, channel, "added") 
            self.events["chat"].addChannel("TestFunc", channel)
        
    elif len(params) == 2 and params[0] == "rem":
        channel = self.retrieveTrueCase(params[1])
        
        if channel != False:
            self.sendChatMessage(self.send, channel, "removed") 
            self.events["chat"].removeChannel("TestFunc", channel)