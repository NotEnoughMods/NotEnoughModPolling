ID = "say"
permission = 4

def execute(self, name, params, channel, userdata, rank):
    print("Executing.. ")
    result = " ".join(params)
    print(result)
    self.sendChatMessage(self.send, channel, result)
    