import warnings
warnings.simplefilter("ignore", RuntimeWarning)

import socket
import time
import traceback
import queue
import datetime
import logging

from IRC_readwrite_threads import IRC_reader, IRC_writer, ThreadShuttingDown
from commandHandler import commandHandling
from configReader import Configuration

class IRC_Main():
    def __init__(self, configObj):
        config = configObj.config
        
        self.host = config.get("Connection Info", "server")
        self.port = config.getint("Connection Info", "port")
        
        self.name = config.get("Connection Info", "nickname")
        self.passw = config.get("Connection Info", "password")
        self.channels = configObj.getChannels()
        self.myident = config.get("Connection Info", "ident")
        self.realname = config.get("Connection Info", "realname")
        
        self.forceIPv6 = config.getboolean("Networking", "force ipv6")
        self.bindIP = config.get("Networking", "bind address")
            
        self.adminlist = configObj.getAdmins()
        self.prefix = config.get("Administration", "command prefix")
        self.loglevel = config.get("Administration", "logging level")
        
        self.nsAuth = False
        self.shutdown = False
        
        
        
    def start(self):
        if self.forceIPv6 == True:
            if socket.has_ipv6:
                try:
                    info = socket.getaddrinfo(self.host, self.port, socket.AF_INET6, socket.SOCK_STREAM, socket.SOL_TCP)
                    
                    # We grab the information from the first entry in the info list, 
                    # which is hopefully the one we require. 
                    # NOTE: Potential problem: Does it still work if the URL has no IPv6 address?
                    family, socktype, proto, canonname, sockaddr = info[0] 
                except socket.gaierror as error:
                    print("getaddrinfo failed! Maybe IPv6 isn't supported on this platform? Check your config!")
                    raise error
                
                self.serverConn = socket.socket(socket.AF_INET6)
                self.serverConn.settimeout(300)
                
                if self.bindIP != "":
                    self.serverConn.bind((self.bindIP, 0))
                
                self.serverConn.connect(sockaddr)
                
            else:
                raise RuntimeError("IPv6 isn't supported on this platform. Please check the config file.")
        else:
            self.serverConn = socket.create_connection((self.host, self.port), 300,
                                                       source_address = (self.bindIP, 0)) 
        
        self.readThread = IRC_reader(self.serverConn)
        self.writeThread = IRC_writer(self.serverConn)
        
        self.readThread.start()
        self.writeThread.start()
        
        self.writeThread.sendMsg('PASS ' + self.passw)
        self.writeThread.sendMsg('NICK ' + self.name)
        self.writeThread.sendMsg('USER {0} * * {1}'.format(self.myident, self.realname))
        self.comHandle = commandHandling(self.channels, self.prefix, self.name, self.myident, self.adminlist, self.loglevel)
        
        peerinfo = self.serverConn.getpeername()
        clientinfo = self.serverConn.getsockname()
        
        self.__root_logger__ = logging.getLogger("IRCMainLoop")
        
        self.__root_logger__.info("Connected to %s (IP address: %s, port: %s)",self.host, peerinfo[0], peerinfo[1])
        self.__root_logger__.debug("Local IP: %s, local port used by this connection: %s", clientinfo[0], clientinfo[1])
        
        self.__root_logger__.info("BOT IS NOW ONLINE: Starting to listen for server responses.")
        
        while self.shutdown == False:
            
            try:
                msg = self.readThread.readMsg()
                msgParts = msg.split(" ", 2)
                
                #print msgParts
                
                if msgParts[0][0] == ":":
                    prefix = msgParts[0][1:]
                else:
                    prefix = None
                
                if prefix == None:
                    command = msgParts[0]
                    
                    try:
                        commandParameters = msgParts[1]
                    except IndexError:
                        commandParameters = ""
                else:
                    command = msgParts[1]
                    try:
                        commandParameters = msgParts[2]
                    except IndexError:
                        commandParameters = ""
                
                
                self.comHandle.handle(self.writeThread.sendMsg, prefix, command, commandParameters, self.nsAuth)
                
            except queue.Empty:
                pass
            
            # Bugfix for when only the writeThread, i.e. the one that sends data to server, dies
            # we raise an exception so the main loop exits and the readThread is shut down too
            if self.writeThread.ready == False:
                self.__root_logger__.critical("Write Thread was shut down, raising exception.")
                raise ThreadShuttingDown("writeThread", time.time())
                
            
            self.comHandle.timeEventChecker()
            
            
            
            time.sleep(0.05)
            
        self.__root_logger__.info("Main loop has been stopped")
        self.readThread.ready = False
        self.writeThread.ready = False
        self.__root_logger__.info("Read and Write thread signaled to stop.")
        
    def customNickAuth(self, result):
        if isinstance(result, str): 
            self.nsAuth = result
        else:
            raise TypeError

def write_starting_date():
    startFile = open("lastStart.txt", "w")  
    startFile.write("Started at: "+str(datetime.datetime.today()))
    startFile.close()              

write_starting_date()    

configObj = Configuration()
configObj.loadConfig()
configObj.check_options()
 
bot = IRC_Main(configObj)   

try:
    bot.start()
except Exception as error:
    if getattr(bot, "__root_logger__", None) != None:
        bot.__root_logger__.exception("The bot has encountered an exception and had to shut down.")
        log = True
    else:
        print("Tried to log an error, but logger wasn't initialized.")
        log = False
    print("OH NO I DIED: "+str(error))
    traceb = str(traceback.format_exc())
    print(traceb)
    excFile = open("exception.txt", "w")
    excFile.write("Oh no! The bot died! \n"+str(traceb)+"\nTime of death: "+str(datetime.datetime.today())+"\n")
    excFile.write("-----------------------------------------------------\n")
    
    # Check if the attribute 'comhandle' is contained in 'bot'. If so, proceed with playback of packet log.
    # This is for the cases where the program crashes while comHandle is being initialized, resulting
    # in comHandle missing afterwards.
    if getattr(bot, "comHandle", None) != None: 
        for i in range(bot.comHandle.PacketsReceivedBeforeDeath.qsize()):
            msg = bot.comHandle.PacketsReceivedBeforeDeath.get(block = False)
            excFile.write(msg)
            excFile.write("\n")
        bot.comHandle.threading.sigquitAll()
        if log: bot.__root_logger__.debug("All threads were signaled to shut down.")
        
    excFile.write("-----------------------------------------------------\n")
    excFile.write("ReadThread Exception: \n")
    
    if getattr(bot, "readThread", None) != None: 
        excFile.write(str(bot.readThread.error)+" \n")
        bot.readThread.ready = False
    else:
        excFile.write("ReadThread not initialized\n")
    if log: bot.__root_logger__.info(u"Exception encountered by ReadThread (if any): %s\n", str(bot.readThread.error))
    
    excFile.write("-----------------------------------------------------\n")
    excFile.write("WriteThread Exception: \n")
    
    if getattr(bot, "writeThread", None) != None: 
        excFile.write(str(bot.writeThread.error)+" \n")
        #bot.writeThread.waitUntilEmpty()
        bot.writeThread.signal = True
    else:
        excFile.write("WriteThread not initialized\n")
    if log: bot.__root_logger__.info(u"Exception encountered by WriteThread (if any): %s\n", str(bot.writeThread.error))
    
    excFile.close()
    
    
    
    
    
    
if log: bot.__root_logger__.info("End of Session\n\n\n\n")
logging.shutdown()
