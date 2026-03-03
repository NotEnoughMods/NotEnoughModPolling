import time
import datetime
import queue
import os
import logging
import inspect

class LoggingModule():
    def __init__(self, loglevel = "INFO"):
        
        self.typeDict = {"NOTSET" : logging.NOTSET, "DEBUG" : logging.DEBUG, "INFO" : logging.INFO,
                         "WARNING" : logging.WARNING, "ERROR" : logging.ERROR, "CRITICAL" : logging.CRITICAL}
        self.logLevel = self.typeDict[loglevel.upper()]
        
        
        self.__create_directory__("BotLogs")
        
        self.date = datetime.date.today()
        
        # Each month, a new folder is created
        # Each day, a new file is created in the folder
        monthfoldername = self.date.strftime("%Y-%m")
        dayfilename = self.date.strftime("%d-%m-%Y")
        
        print(monthfoldername, dayfilename)
        self.__create_directory__("BotLogs/{0}".format(monthfoldername))
        
        logging.basicConfig(filename="BotLogs/{0}/{1}.log".format(monthfoldername, dayfilename),level=self.logLevel,
                            format='%(asctime)s [%(levelname)s] --[%(name)s:%(module)s/%(funcName)s]-- %(message)s', datefmt='%H:%M:%S')
        
        ## We create a console handler and configure it
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(self.logLevel)
        
        format = logging.Formatter('%(asctime)s  [%(levelname)s] --[%(name)s:%(module)s/%(funcName)s]-- %(message)s', datefmt='%H:%M:%S')
        consoleHandler.setFormatter(format)
        
        logging.getLogger().addHandler(consoleHandler)
        ## console handler configured, we should be good to go
        
        self.__log_logger__ = logging.getLogger("LoggingModule")
        self.__log_logger__.info("IRC Bot Logging Interface initialised.")
        
        offset, tzname = self.local_time_offset()
        if offset >= 0: offset = "+"+str(offset)
        else: offset = str(offset)
        
        self.__log_logger__.info("All time stamps are in UTC%s (%s)", offset, tzname)
        
        
        self.num = 0
    def __create_directory__(self, dirpath):
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
            print("created dir")
        elif not os.path.isdir(dirpath):
            raise RuntimeError("A file with the path {0} already exists, please delete or rename it.".format(dirpath))
        else:
            print("no dir needs to be created")
            pass
    
    def __switch_filehandle_daily__(self, *args):
        newDate = datetime.date.today()
        
        if self.date < newDate:
            
            self.__log_logger__.info("Switching Logfile Handler because a new day begins. Old date: %s, new date: %s", self.date, newDate)
            
            monthfoldername = newDate.strftime("%Y-%m")
            dayfilename = newDate.strftime("%d-%m-%Y")
            
            if self.date.month !=  newDate.month:
                self.__log_logger__.info("Creating new folder BotLogs/{0}".format(monthfoldername))
                self.__create_directory__("BotLogs/{0}".format(monthfoldername))
            self.__log_logger__.info("Creating new file BotLogs/{0}/{1}.log".format(monthfoldername, dayfilename))
            
            # We close the file handle of the root logger.
            # This should also affect all child loggers
            #
            # POTENTIAL BUG: is handlers[0] always the file handler pointing to the log file?
            # Should be tested with more than one handler.
            print(logging.getLogger().handlers)
            logging.getLogger().handlers[0].stream.close()
            logging.getLogger().removeHandler(logging.getLogger().handlers[0])
            
            filename="BotLogs/{0}/{1}.log".format(monthfoldername, dayfilename)
            
            
            # We create a new file handler with the options we used in __init__ which we add to the root logger
            # This should affect all custom loggers created in plugins, but it needs more testing
            newfile_handler = logging.FileHandler(filename)
            newfile_handler.setLevel = self.logLevel
            
            msgformat = logging.Formatter('%(asctime)s  [%(levelname)s] --[%(name)s:%(module)s/%(funcName)s]-- %(message)s', datefmt='%H:%M:%S')
            newfile_handler.setFormatter(msgformat)
            
            #logging.getLogger().addHandler(newfile_handler)
            self.__prependHandler__(logging.getLogger(), newfile_handler)
            
            self.__log_logger__.info("Logfile Handler switched. Continuing writing to new file. Old date: %s, new date: %s", self.date, newDate)
            
            offset, tzname = self.local_time_offset()
            if offset >= 0: offset = "+"+str(offset)
            else: offset = str(offset)
            
            self.__log_logger__.info("All time stamps are in UTC%s (%s)", offset, tzname)
            self.date = newDate
            
    # Returns UTC offset and name of time zone at current time
    # Based on http://stackoverflow.com/a/13406277
    # Thanks a lot, marr75!
    def local_time_offset(self):
        t = time.time()
    
        if time.localtime(t).tm_isdst and time.daylight:
            return -time.altzone // 3600, time.tzname[1]
        else:
            return -time.timezone // 3600, time.tzname[0]
    
    
    # Modification of logging's appendHandler function
    # It will add the handler to the front of the handler list
    # It is a bit of a hack, but it is required for making sure 
    # that the main file handler is added to the front of the list 
    def __prependHandler__(self, logger,  hdlr):
        logging._acquireLock()
        try:
            if not (hdlr in logger.handlers):
                logger.handlers.insert(0, hdlr)
        finally:
            logging._releaseLock()