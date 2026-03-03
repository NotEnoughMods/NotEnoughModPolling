import logging

ID = "PRIVMSG"

msg_log = logging.getLogger("PRIVMSG")

def execute(self, sendMsg, msgprefix, command, params):
    #print params, prefix
    
    part1 = msgprefix.partition("!")
    part2 = part1[2].partition("@")
    
    name = part1[0]
    ident = part2[0]
    host = part2[2]
    
    cmdprefix = self.cmdprefix
    splitted = params.split(" ", 1)
    
    channel = splitted[0]
    chatMessage = splitted[1][1:]
    
    if channel[0] not in "#&":
        channel = name
        is_channel = False
        perms = ""
        #print "HELP I'M GETTING PRIVMSGD BY ",name," : ",chatMessage
        msg_log.info("Private message from '%s' [%s@%s]: %s", name, ident, host, chatMessage)
    else: 
        is_channel = True
        channel = self.retrieveTrueCase(channel)
        perms = self.userGetRank(channel, name)
        
    #print splitted, channel()
    
    
    #print msgprefix, params
    
    print("<"+name+"> "+chatMessage)
    
    chatParams = chatMessage.rstrip().split(" ")
    
    for i in range(chatParams.count("")):
        chatParams.remove("")
    
    try:
        chatCmd = chatParams[0][1:].lower()
        usedPrfx = chatMessage[0]
    except IndexError:
        chatCmd = ""
        usedPrfx = ""
    #print "ok"
    
    
    
    if name in self.bot_userlist and self.Bot_Auth.isRegistered(name): #and (perms == "@" or perms == "+"):
        #print name + " is in Botlist"
        rank = 3
        perms = "@@"
    elif perms == "@":
        #print name + " is OP"
        rank = 2
    elif perms == "+":
        #print name + " is Voiced"
        rank = 1
    else:
        #print name + " is Nothing"
        rank = 0
        
    #rank = {"@" : 2, "+" : 1, "" : 0}[self.userGetRank(channel, name)]
    #print self.commands
    #print chatCmd
    if usedPrfx == cmdprefix and chatCmd in self.commands:
        bannedInfo = self.Banlist.checkBan(name, ident, host)
        
        if bannedInfo[0] == True:
            msg_log.info("User '%s' uses command '%s', but user is globally banned.",
                         name, chatCmd)
            msg_log.info("Ban information: %s", 
                         bannedInfo[1])
            
            return
            
        
        try:
            support = self.commands[chatCmd][0].privmsgEnabled
        except AttributeError:
            support = False
            
        try:
            if rank >= self.commands[chatCmd][0].permission:
                if is_channel == True:
                    msg_log.info("User '%s' uses command '%s' in channel '%s'", 
                                 name , chatCmd, channel)
                    msg_log.debug("User info for '%s': [%s@%s] Used parameters: %s Rank: %s", 
                                  name, ident, host, chatParams[1:], perms)
                else:
                    msg_log.info("User '%s' uses command '%s'", name , chatCmd)
                    msg_log.debug("User info for '%s': [%s@%s] Used parameters: %s Rank: %s", 
                                  name, ident, host, chatParams[1:], perms)
                    msg_log.debug("User '%s' - destination: '%s' (should be the same)", name, channel)
                    
                if support == True:
                    self.commands[chatCmd][0].execute(self, name, chatParams[1:], channel, (ident, host), perms, is_channel)
                elif support == False and is_channel == True:
                    self.commands[chatCmd][0].execute(self, name, chatParams[1:], channel, (ident, host), perms)
                    
        except KeyError as error:
            print("KeyError for command: "+str(error))
        except AttributeError as error:
            print("AttributeError for command: "+str(error))
    else:
        # if the message comes from a user, set channel to False
        # otherwise, set channel to the channel from which the message was received
        channel = is_channel == True and channel or False
        
        if channel == False: 
            msg_log.debug("Passing a PM from user '%s' [%s@%s] to chat events: '%s'", name, ident, host, chatMessage)
        
        self.events["chat"].tryAllEvents(self, {"name" : name, "ident" : ident, "host" : host}, chatMessage, channel)
            
            