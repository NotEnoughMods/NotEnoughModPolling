ID = "oplist"
permission = 2

def execute(self, name, params, channel, userdata, rank):
    if len(self.bot_userlist) > 0:
        self.sendChatMessage(self.send, channel, "The following users are Operators of this bot: "+", ".join(self.bot_userlist))
    if len(self.bot_userlist) == 0:
        self.sendChatMessage(self.send, channel, "Nobody is Operator of this bot!")
    