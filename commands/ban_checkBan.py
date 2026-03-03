
ID = "checkban"
permission = 3

def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        self.sendNotice(user, "Specify a user formated as username!ident@host.")
        
    if len(params) >= 1:
        userstring = params[0]
        
        bans = self.Banlist.getBans(matchingString=userstring)
        
        output = []
        for ban in bans:
            info = u"{pattern} [{group}] Reason: {reason}".format(
                pattern=self.Banlist.unescape_banstring(ban[1]),
                group=ban[0], reason=ban[2])
            output.append(info)
        
        output = u" | ".join(output)
        
        if len(output) == 0:
            self.sendNotice(user, "The user is not affected by any bans.")
        elif len(output) == 1:
            self.sendNotice(user, u"The user is affected by the following ban: {0}".format(output))
        elif len(output) > 1:
            self.sendNotice(user, u"The user is affected by the following bans:")
            self.sendNotice(user, output)