ID = "319"

async def execute(self, sendMsg, prefix, command, params):
    #print "WHOIS WHAT", prefix, params
    print(params)
    
    fields = params.split(":")
    
    userinfo = fields[0].split(" ")
    channelinfo = fields[1].split(" ")
    
    name = userinfo[1]
    
    print(userinfo, channelinfo)
