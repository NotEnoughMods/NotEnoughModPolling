import datetime
import logging
import os
import time


class LoggingModule:
    def __init__(self, loglevel="INFO"):

        self.type_dict = {
            "NOTSET": logging.NOTSET,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        self.log_level = self.type_dict[loglevel.upper()]

        self._create_directory("BotLogs")

        self.date = datetime.date.today()

        # Each month, a new folder is created
        # Each day, a new file is created in the folder
        monthfoldername = self.date.strftime("%Y-%m")
        dayfilename = self.date.strftime("%d-%m-%Y")

        self._create_directory(f"BotLogs/{monthfoldername}")

        logging.basicConfig(
            filename=f"BotLogs/{monthfoldername}/{dayfilename}.log",
            level=self.log_level,
            format="%(asctime)s [%(levelname)s] %(name)s:%(module)s/%(funcName)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        ## We create a console handler and configure it
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)

        format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(module)s/%(funcName)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(format)

        logging.getLogger().addHandler(console_handler)
        ## console handler configured, we should be good to go

        self._logger = logging.getLogger("LoggingModule")
        self._logger.info("IRC Bot Logging Interface initialised.")

        offset, tzname = self.local_time_offset()
        offset = "+" + str(offset) if offset >= 0 else str(offset)

        self._logger.info("All time stamps are in UTC%s (%s)", offset, tzname)

        self.num = 0

    def _create_directory(self, dirpath):
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
        elif not os.path.isdir(dirpath):
            raise RuntimeError(f"A file with the path {dirpath} already exists, please delete or rename it.")

    def _switch_filehandle_daily(self, *args):
        new_date = datetime.date.today()

        if self.date < new_date:
            self._logger.info(
                "Switching Logfile Handler because a new day begins. Old date: %s, new date: %s",
                self.date,
                new_date,
            )

            monthfoldername = new_date.strftime("%Y-%m")
            dayfilename = new_date.strftime("%d-%m-%Y")

            if self.date.month != new_date.month:
                self._logger.info(f"Creating new folder BotLogs/{monthfoldername}")
                self._create_directory(f"BotLogs/{monthfoldername}")
            self._logger.info(f"Creating new file BotLogs/{monthfoldername}/{dayfilename}.log")

            # We close the file handle of the root logger.
            # This should also affect all child loggers
            #
            # POTENTIAL BUG: is handlers[0] always the file handler pointing to the log file?
            # Should be tested with more than one handler.
            self._logger.debug("Current root handlers: %s", logging.getLogger().handlers)
            logging.getLogger().handlers[0].stream.close()
            logging.getLogger().removeHandler(logging.getLogger().handlers[0])

            filename = f"BotLogs/{monthfoldername}/{dayfilename}.log"

            # We create a new file handler with the options we used in __init__ which we add to the root logger
            # This should affect all custom loggers created in plugins, but it needs more testing
            newfile_handler = logging.FileHandler(filename)
            newfile_handler.setLevel = self.log_level

            msgformat = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(module)s/%(funcName)s: %(message)s",
                datefmt="%H:%M:%S",
            )
            newfile_handler.setFormatter(msgformat)

            # logging.getLogger().addHandler(newfile_handler)
            self._prepend_handler(logging.getLogger(), newfile_handler)

            self._logger.info(
                "Logfile Handler switched. Continuing writing to new file. Old date: %s, new date: %s",
                self.date,
                new_date,
            )

            offset, tzname = self.local_time_offset()
            offset = "+" + str(offset) if offset >= 0 else str(offset)

            self._logger.info("All time stamps are in UTC%s (%s)", offset, tzname)
            self.date = new_date

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
    def _prepend_handler(self, logger, hdlr):
        logging._acquireLock()
        try:
            if hdlr not in logger.handlers:
                logger.handlers.insert(0, hdlr)
        finally:
            logging._releaseLock()
