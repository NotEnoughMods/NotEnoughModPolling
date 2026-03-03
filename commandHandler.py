import importlib.util
import os
import queue
import logging

from time import strftime
from timeit import default_timer
from datetime import datetime

import centralizedThreading
from BotEvents import TimerEvent, MsgEvent, StandardEvent
from IRC_registration import trackVerification
from CommandHelp import HelpModule
from IRCLogging import LoggingModule
from BanList import BanList



class commandHandling():
    def __init__(self, channels, cmdprefix, name, ident, adminlist, loglevel):
        
        self.LoggingModule = LoggingModule(loglevel)
        self.__CMDHandler_log__ = logging.getLogger("CMDHandler")
        
        self.name = name
        self.ident = ident
        self.Plugin = self.__LoadModules__("IRCpackets")
        self.commands = self.__LoadModules__("commands")
        
        self.bot_userlist = adminlist
        self.Bot_Auth = trackVerification(adminlist)
        
        self.channels = channels
        self.channelData = {}
        
        self.topic = {}
        self.cmdprefix = cmdprefix
        
        self.events = {"time" : TimerEvent(), "chat" : MsgEvent(),
                       "channeljoin" : StandardEvent(),
                       "channelpart" : StandardEvent(),
                       "channelkick" : StandardEvent(),
                       "userquit" : StandardEvent(),
                       "nickchange" : StandardEvent()}
        
        self.events["time"].addEvent("LogfileSwitch", 60, self.LoggingModule.__switch_filehandle_daily__)
        
        self.server = None
        self.latency = None
        self.rankconvert = {"@@" : 3, "@" : 2, "+" : 1, "" : 0}
        self.startupTime = datetime.now()
        
        self.PacketsReceivedBeforeDeath = queue.Queue(maxsize = 50)
        
        self.threading = centralizedThreading.ThreadPool()
        self.Banlist = BanList("BannedUsers.db")
        
        self.helper = HelpModule()
        self.auth = None
        
        
        
        
        
    def handle(self, send, prefix, command, params, auth):
        self.send = send
        
        ## In the next few lines I implement a basic logger so the logs can be put out when the bot dies.
        ## Should come in handy when looking at what or who caused trouble
        ## There is room for 50 entries, number can be increased or lowered at a later point
        try:
            self.PacketsReceivedBeforeDeath.put(u"{0} {1} {2}".format(prefix, command, params), False)
        except queue.Full:
            self.PacketsReceivedBeforeDeath.get(block = False)
            self.PacketsReceivedBeforeDeath.put(u"{0} {1} {2}".format(prefix, command, params), False)
        
        
        try:
            if command in self.Plugin:
                self.Plugin[command][0].execute(self, send, prefix, command, params)
            else:
                # 0 is the lowest possible log level. Messages about unimplemented packets are
                # very common, so they will clutter up the file even if logging is set to DEBUG
                self.__CMDHandler_log__.log(0, "Unimplemented Packet: %s", command)
        except KeyError as error:
            #print "Unknown command '"+command+"'"
            self.__CMDHandler_log__.exception("Missing channel or other KeyError caught")
            print("Missing channel or other KeyError caught: "+str(error))
            
    
    def timeEventChecker(self):
        self.events["time"].tryAllEvents(self)
    
    def userGetRank(self, channel, username):
        #print self.channelData[channel]["Userlist"]
        for user in self.channelData[channel]["Userlist"]:
            if user[0].lower() == username.lower():
                return user[1]
    
    def userGetRankNum(self, channel, username):
        if username in self.bot_userlist and self.Bot_Auth.isRegistered(username):
            return 3
        else:
            for user in self.channelData[channel]["Userlist"]:
                if user[0].lower() == username.lower():
                    if user[1] == "@@":
                        return 2
                    else:
                        return self.rankconvert[user[1]]
            
            return -1 # No user found
            
    def retrieveTrueCase(self, channel):
        for chan in self.channelData:
            if chan.lower() == channel.lower():
                return chan
        return False
    
    # A wrapper for sendChatMessage that does not require a send argument.
    def sendMessage(self, channel, msg, msgsplitter = None, splitAt = " "):
        self.sendChatMessage(self.send, channel, msg, msgsplitter, splitAt)
    
    def sendChatMessage(self, send, channel, msg, msgsplitter = None, splitAt = " "):
        # we calculate a max length value based on what the server would send to other users 
        # if this bot sent a message.
        # Private messages from the server look like this:
        # nick!user@hostname PRIVMSG target :Hello World!
        # Nick is the username of the bot, user is the identification name of the bot and can be
        # different from the nick, it will prefix the hostname. target is the channel 
        # to which we send the message. At the end, we add a constant (25) to the length to account
        # for whitespaces and other characters and eventual oddities. 
        # The Hostname will be limited to 63, regardless of the actual length.
        # 7 characters for the PRIVSM string
        
        # if you want to create your own tweaked message splitter, 
        # provide it as the fourth argument to self.sendChatMessage
        # otherwise, the default one, i.e. self.defaultsplitter, is used
        if msgsplitter == None:
            msgsplitter = self.defaultsplitter
            
        prefixLen = len(self.name) + len(self.ident) + 63 + 7 + len(channel) + 25
        remaining = 512-prefixLen
        #print remaining
        
        if len(msg)+prefixLen > 512:
            msgpart = msgsplitter(msg, remaining, splitAt)
            self.__CMDHandler_log__.debug("Breaking message %s into parts %s", msg, msgpart)
            
            for part in msgpart:
                #send("PRIVMSG {0} :{1}".format(channel, part))
                #send("PRIVMSG "+str(channel)+" :"+str(part))
                send(u"PRIVMSG {0} :{1}".format(channel, part))
                self.__CMDHandler_log__.debug("Sending parted message to channel/user %s: '%s'", channel, msg)
        else:
            #send("PRIVMSG {0} :{1}".format(channel, msg))
            #send("PRIVMSG "+channel+" :"+msg)
            send(u"PRIVMSG {0} :{1}".format(channel, msg))
            self.__CMDHandler_log__.debug("Sending to channel/user %s: '%s'", channel, msg)
            
    def sendNotice(self, destination, msg, msgsplitter = None, splitAt = " "):
        # Works the same as sendChatMessage
        # Only difference is that this message is sent as a NOTICE,
        # and it does not require a send parameter.
        if msgsplitter == None:
            msgsplitter = self.defaultsplitter
                                                            #NOTICE
        prefixLen = len(self.name) + len(self.ident) + 63 + 6 + len(destination) + 25
        remaining = 512-prefixLen
        #print remaining
        
        if len(msg)+prefixLen > 512:
            msgpart = msgsplitter(msg, remaining, splitAt)
            self.__CMDHandler_log__.debug("Breaking message %s into parts %s", msg, msgpart)
            
            for part in msgpart:
                #self.send("NOTICE "+str(destination)+" :"+str(part))
                self.send(u"NOTICE {0} :{1}".format(destination, part))
                self.__CMDHandler_log__.debug("Sending parted notice to channel/user %s: '%s'", destination, msg)
        else:
            #self.send("NOTICE "+str(destination)+" :"+str(msg))
            self.send(u"NOTICE {0} :{1}".format(destination, msg))
            self.__CMDHandler_log__.debug("Sending notice to channel/user %s: '%s'", destination, msg)
        
    def defaultsplitter(self, msg, length, splitAt):
        
        start = 0
        end = length
        items = []
        
        
        while end <= len(msg):
            splitpos = msg[start:end].rfind(splitAt)
    
            # case 1: whitespace has not been found, ergo: 
            # message is too long, so we split it at the position specified by 'end'
            if splitpos < 0: 
                items.append(msg[start:end])
                start = end
            # case 2: whitespace has been found, ergo:
            # we split it at the whitespace
            # splitpos is a value local to msg[start:end], so we need to add start to it to get a global value
            else:
                items.append(msg[start:start+splitpos])
                start = start+splitpos+len(splitAt)
                
            end = start + length
        
        # Check if there is any remaining data
        # If so, append the remaining data to the list
        if start < len(msg):
            items.append(msg[start:])
        
        # remove all empty strings in the list because they are not needed nor desired
        for i in range(items.count("")):
            items.remove("")
                
        return items
    
    
    
    ## writeQueue adds a specified string to the internal queue of the bot.
    ## This functions handles marking the string with a DebugEntry prefix and the time
    ## at which the entry was added. You can also specify a name that will be added to
    ## the entry so that you can identify which module or command has created the entry.
    ##
    ##
    ## Please note that at the time of this writing the queue can hold a maximum of 50 entries.
    ## Adding new entries will kick the oldest entries out of the queue, so you should be 
    ## conservative with the usage of writeQueue.
    # UPDATE: writeQueue is now deprecated, please use Python's logging module.
    # The logging module allows you to have seperate info and debug messages which will
    # be written automatically into log files. These are not limited to an arbitrary 
    # number and will (should) not disappear on repeated crashes. Read up on how to use the logging module.
    # writeQueue messages will be written to the log files for the sake of improved compatibility
    def writeQueue(self, string, modulename = "no_name_given"):
        entryString = "DebugEntry at {0} [{1!r}]: {2!r}".format(strftime("%H:%M:%S (%z)"), modulename, string)
        self.__CMDHandler_log__.debug("Added DebugEntry: '%s'", entryString)
        try:
            self.PacketsReceivedBeforeDeath.put(entryString, False)
        except queue.Full:
            self.PacketsReceivedBeforeDeath.get(block = False)
            self.PacketsReceivedBeforeDeath.put(entryString, False)
    
    def joinChannel(self, send, channel):
        if isinstance(channel, str):
            if channel not in self.channelData:
                #self.channels.append(channel)
                self.channelData[channel] = {"Userlist" : [], "Topic" : "", "Mode" : ""}
            send("JOIN "+channel, 5)
            self.__CMDHandler_log__.info("Joining channel: '%s'", channel)
            
        elif isinstance(channel, list):
            for chan in channel:
                if chan not in self.channelData:
                    #self.channels.append(channel)
                    self.channelData[chan] = {"Userlist" : [], "Topic" : "", "Mode" : ""}
                    
            send("JOIN "+",".join(channel), 3)
            self.__CMDHandler_log__.info("Joining several channels: '%s'", channel)
        else:
            self.__CMDHandler_log__.error("Trying to join a channel, but channel is not list or string: %s [%s]", channel, type(channel))
            raise TypeError
        print(self.channelData)
    
    def whoisUser(self, user):
        self.send("WHOIS {0}".format(user))
        self.Bot_Auth.queueUser(user)
        self.__CMDHandler_log__.debug("Sending WHOIS for user '%s'", user)
    
    def userInSight(self, user):
        print(self.channelData)
        self.__CMDHandler_log__.debug("Checking if user '%s' is in the following channels: %s", user, self.channelData.keys())
        for channel in self.channelData:
            for userD in self.channelData[channel]["Userlist"]:
                if user == userD[0]:
                    return True
                    self.__CMDHandler_log__.debug("Yes, he is (at least) in channel '%s'", channel)
        return False
        self.__CMDHandler_log__.debug("No, user is out of sight.")
    
    def __ListDir__(self, dir):
        files = os.listdir(dir)
        newlist = []
        self.__CMDHandler_log__.debug("Listing files in directory '%s'", dir)
        for i in files: 
            if not i.startswith("__init__") and i.endswith(".py"):
                newlist.append(i)
                
        return newlist
    
    @staticmethod
    def _load_source(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def __LoadModules__(self,path):
        ModuleList = self.__ListDir__(path)
        self.__CMDHandler_log__.info("Loading modules in path '%s'...", path)
        Packet = {}
        for i in ModuleList:
            self.__CMDHandler_log__.debug("Loading file %s in path '%s'", i, path)
            module = self._load_source("RenolIRC_"+i[0:-3], path+"/"+i)
            #print i
            Packet[module.ID] = (module, path+"/"+i)
            
            try:
                if not callable(module.__initialize__):
                    module.__initialize__ = False
                    self.__CMDHandler_log__.log(0, "File %s does not use an initialize function", i)
            except AttributeError:
                module.__initialize__ = False
                self.__CMDHandler_log__.log(0, "File %s does not use an initialize function", i)
            
                
            Packet[module.ID] = (module, path+"/"+i)
            #Packet[i[1].lower()].PATH = path + "/"+i[2]
            #self.Packet[i[1]] = self.Packet[i[1]].EXEC()
        
        print("ALL MODULES LOADED"   )
        self.__CMDHandler_log__.info("Modules in path '%s' loaded.", path)
        return Packet
    
    