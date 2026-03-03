ID = "318"

async def execute(self, sendMsg, prefix, command, params):
    print("WHOIS RESULT: ",prefix, command, params)
    
    fields = params.split(":")
    print(fields[0],fields[1])
    
    names = fields[0].split(" ")
    print(",".join(names))
    username = names[1]
    registeredAs = names[2]
    
    
    if self.Bot_Auth.isQueued(username) and self.Bot_Auth.doesExist(username):
        if not self.Bot_Auth.isRegistered(username):
            #print "User is not registered"
            self.Bot_Auth.unregisterUser(username)
        else:
            pass
            #print "User is registered"
        
    if self.Bot_Auth.isQueued(username):
        self.Bot_Auth.unqueueUser(username)