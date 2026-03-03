import logging

ID = "addop"
permission = 3

def notInList(user, userlist):
    for name in userlist:
        if name.lower() == user.lower():
            return False
    
    return True

def execute(self, username, params, channel, userdata, rank):
    names = params
    
    for name in names:
        if notInList(name, self.bot_userlist):
            self.bot_userlist.append(name)
            self.Bot_Auth.addUser(name)
            self.whoisUser(name)
            
    logging.info("User '%s' has added user(s) '%s'", username, ", ".join(names))
    self.sendChatMessage(self.send, channel, "Added "+", ".join(names))