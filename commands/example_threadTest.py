ID = "threadevent"
permission = 3
privmsgEnabled = False

import time
import random
import os

def thread(self, pipe):
    #print channels
    #print currChannel
    while self.signal == False:
        rand = random.randint(10, 20)
        
        pipe.send("I will wait {0} seconds!".format(rand))
        time.sleep(rand)
        print(pipe.recv())
        print("success")

def threadChecker(self, channels):
    yes = self.threading.poll("threadTest")
    
    #print yes
    if yes:
        msg = self.threading.recv("threadTest")
        if isinstance(msg, dict) and "action" in msg and msg["action"] == "exceptionOccured":
            print("EXCEPTION")
            print(msg["traceback"])
        else:
            self.sendChatMessage(self.send, channels[0], "Message from Thread: "+msg)
            self.threading.send("threadTest", random.choice(["0", "1", "2", "3"]))
        #print "sent message"
    


def execute(self, name, params, channel, userdata, rank):
    #print "running"
    if len(params) == 1 and params[0] == "on":
        if not self.events["time"].doesExist("threadChecker"):
            self.sendChatMessage(self.send, channel, "Turning threadevent on.")
            self.timerChannel = channel
            self.events["time"].addEvent("threadChecker", 1, threadChecker, [channel])
            
            self.threading.addThread("threadTest", thread)
        else:
            self.sendChatMessage(self.send, channel, "threadevent is already running.")
            
    elif len(params) == 1 and params[0] == "off":
        if self.events["time"].doesExist("threadChecker"):
            self.sendChatMessage(self.send, channel, "Turning threadevent off.") 
            self.events["time"].removeEvent("threadChecker")
            
            self.threading.sigquitThread("threadTest")
        else:
            self.sendChatMessage(self.send, channel, "threadevent isn't running!") 
    
    
    elif len(params) == 2 and params[0] == "add":
        channel = self.retrieveTrueCase(params[1])
        
        if channel != False:
            self.sendChatMessage(self.send, channel, "added") 
            self.events["time"].addChannel("threadChecker", channel)
        
    elif len(params) == 2 and params[0] == "rem":
        channel = self.retrieveTrueCase(params[1])
        
        if channel != False:
            self.sendChatMessage(self.send, channel, "removed") 
            self.events["time"].removeChannel("threadChecker", channel)