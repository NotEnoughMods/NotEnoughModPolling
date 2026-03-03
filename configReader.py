import re
import configparser

class invalidConfig(Exception):
    def __init__(self, key, line):
        self.line = line+1
        self.key = key
    def __str__(self):
        return "Invalid data on line {0}: {1}".format(self.line, self.key)

def CreateDefaultConfig():
    Parser = configparser.ConfigParser(allow_no_value = True)
    
    Parser.add_section("Connection Info")
    Parser.set("Connection Info", "nickname", "MyIRCBot")
    Parser.set("Connection Info", "password", "foobar")
    Parser.set("Connection Info", "ident", "MyIRCBot")
    Parser.set("Connection Info", "realname", "RenolIRCBot")
    
    Parser.set("Connection Info", "server", "")
    Parser.set("Connection Info", "port", "6667")
    
    Parser.add_section("Administration")
    Parser.set("Administration", "bot operators", "")
    Parser.set("Administration", "channels", "")
    Parser.set("Administration", "command prefix", "=")
    Parser.set("Administration", "logging level", "INFO")
    
    Parser.add_section("Networking")
    Parser.set("Networking", "force IPv6", "False")
    Parser.set("Networking", "bind address", "")
    
    return Parser

class Configuration():
    def __init__(self):
        self.config = None
        
        self.configname = "config.cfg"
        
        self.mandatoryVariables = {"Connection Info" : {"nickname" : True, "password" : True, 
                                                        "ident" : True, "realname" : True, "server" : True,
                                                        "port" : True},
                                   "Administration" : {"bot operators" : False, "channels" : False,
                                                       "command prefix" : True, "logging level" : True},
                                   
                                   "Networking" : {"force ipv6" : True, "bind address" : False}
                                   
                                   }
        
        self.found = []
    
    def loadConfig(self):
        try:
            conFile = open(self.configname, "r")
        except IOError as error:
            config = CreateDefaultConfig()
    
            configFile = open(self.configname, "w")
            config.write(configFile)
            configFile.close()
            
            raise RuntimeError("The '{0}' file was missing. A new config file has been created. "
                               "Please fill in the information.".format(self.configname))
        else:
            self.config = configparser.ConfigParser()
            self.config.read_file(conFile)
    
    def check_options(self):
        for section in self.mandatoryVariables:
            options = self.mandatoryVariables[section]
            
            for option in options:
                val = self.config.get(section, option)
                
                if options[option] == True and val == "":
                    raise RuntimeError("Option '{0}' in section '{1}' has no value, but is required to have one. "
                                        "Please fill in the missing information.".format(option, section))
    
    def getChannels(self):
        chans = self.config.get("Administration", "channels").split(",")
        
        newchans = []
        for chan in chans:
            chan = chan.strip()
            if chans[0].isalnum():
                newchans.append("#"+chan)
            else:
                newchans.append(chan)
        
        return newchans
    
    def getAdmins(self):
        admins = self.config.get("Administration", "bot operators").split(",")
        
        newadmins = []
        for admin in admins:
            admin = admin.strip()
            newadmins.append(admin)
            
        return newadmins