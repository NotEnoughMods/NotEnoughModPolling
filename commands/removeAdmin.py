import logging

ID = "remop"
permission = 3

def notInList(user, userlist):
    for name in userlist:
        if name.lower() == user.lower():
            return (False, name)
    
    return (True, "NOPE")

def execute(self, username, params, channel, userdata, rank):
    names = params
    notremoved = []
    removed = []
    
    for name in names:
        result, correctName =  notInList(name, self.bot_userlist)
        if result == False and correctName != username:
            self.bot_userlist.remove(correctName)
            removed.append(correctName)
            self.Bot_Auth.unregisterUser(correctName)
            self.Bot_Auth.remUser(correctName)
            if self.Bot_Auth.isQueued(correctName): self.Bot_Auth.unqueueUser(correctName)
        else:
            notremoved.append(name)
    
    if len(removed) > 0:
        logging.info("User '%s' has removed user(s) '%s'", username, ", ".join(removed))
        self.sendChatMessage(self.send, channel, "Removed "+", ".join(removed))
    if len(notremoved) > 0:
        self.sendChatMessage(self.send, channel, "Didn't remove "+", ".join(notremoved))
    