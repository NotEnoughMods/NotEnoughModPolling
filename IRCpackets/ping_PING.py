ID = "PING"



def execute(self, sendMsg, prefix, command, params):
    print("RECEIVED PING: "+params)
    
    
    derp = params.strip()
    if derp[0] == ":":
        toSend = derp[1:]
    else:
        toSend = derp
    
    sendMsg("PONG "+derp, 0)