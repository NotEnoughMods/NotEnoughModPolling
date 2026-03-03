import time

ID = "004"

def pinger(self, channels):
    if self.server != None:
        self.send("PING "+self.server, 0)
        #print "PING SENT TO "+self.server
        self.lastPing = time.time()
        
def execute(self, sendMsg, prefix, command, params):
    split = params.split(" ")
    
    server = split[1]
    if server[0] == ":":
        server = server[1:]
    
    self.server = server
    self.events["time"].addEvent("server pinger", 20, pinger)