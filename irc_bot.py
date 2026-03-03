import asyncio
import contextlib
import datetime
import logging
import socket
import traceback

from command_router import CommandRouter
from config import Configuration
from irc_connection import IrcConnection


class IrcBot:
    def __init__(self, configObj):
        config = configObj.config

        self.host = config.get("Connection Info", "server")
        self.port = config.getint("Connection Info", "port")

        self.name = config.get("Connection Info", "nickname")
        self.password = config.get("Connection Info", "password")
        self.channels = configObj.getChannels()
        self.ident = config.get("Connection Info", "ident")
        self.realname = config.get("Connection Info", "realname")

        self.forceIPv6 = config.getboolean("Networking", "force ipv6")
        self.bindIP = config.get("Networking", "bind address")

        self.adminlist = configObj.getAdmins()
        self.prefix = config.get("Administration", "command prefix")
        self.loglevel = config.get("Administration", "logging level")

        self.nickserv_auth = False
        self.shutdown = False

    async def start(self):
        self.conn = IrcConnection()

        local_addr = None
        family = 0

        if self.forceIPv6:
            if not socket.has_ipv6:
                raise RuntimeError("IPv6 isn't supported on this platform. Please check the config file.")
            family = socket.AF_INET6
            if self.bindIP:
                local_addr = (self.bindIP, 0)
        else:
            if self.bindIP:
                local_addr = (self.bindIP, 0)

        await self.conn.connect(self.host, self.port, local_addr=local_addr, family=family)

        # Start the write loop as a background task
        write_task = asyncio.create_task(self.conn.write_loop())

        if self.password:
            await self.conn.sendMsg("PASS " + self.password)
        await self.conn.sendMsg("NICK " + self.name)
        await self.conn.sendMsg(f"USER {self.ident} * * {self.realname}")

        self.command_router = CommandRouter(
            self.channels,
            self.prefix,
            self.name,
            self.ident,
            self.adminlist,
            self.loglevel,
        )

        self._logger = logging.getLogger("IRCMainLoop")
        self._logger.info("Connected to %s", self.host)
        self._logger.info("BOT IS NOW ONLINE: Starting to listen for server responses.")

        # Timer event checker runs as a periodic background task
        timer_task = asyncio.create_task(self._timer_loop())

        try:
            async for msg in self.conn.read_lines():
                if self.shutdown:
                    break

                msgParts = msg.split(" ", 2)

                prefix = msgParts[0][1:] if msgParts[0][0] == ":" else None

                if prefix is None:
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

                await self.command_router.handle(self.conn.sendMsg, prefix, command, commandParameters, self.nickserv_auth)
        finally:
            self._logger.info("Main loop has been stopped")
            timer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer_task
            await self.conn.close()
            write_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await write_task
            self._logger.info("Connection closed.")

    async def _timer_loop(self):
        """Periodically check timer events."""
        try:
            while not self.shutdown:
                await self.command_router.timeEventChecker()
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    def customNickAuth(self, result):
        if isinstance(result, str):
            self.nickserv_auth = result
        else:
            raise TypeError


def write_starting_date():
    with open("lastStart.txt", "w") as f:
        f.write("Started at: " + str(datetime.datetime.today()))


async def async_main():
    write_starting_date()

    configObj = Configuration()
    configObj.loadConfig()
    configObj.check_options()

    bot = IrcBot(configObj)
    log = False

    try:
        await bot.start()
    except Exception as error:
        if getattr(bot, "_logger", None) is not None:
            bot._logger.exception("The bot has encountered an exception and had to shut down.")
            log = True
        else:
            print("Tried to log an error, but logger wasn't initialized.")

        print("OH NO I DIED: " + str(error))
        traceb = str(traceback.format_exc())
        print(traceb)

        with open("exception.txt", "w") as excFile:
            excFile.write(
                "Oh no! The bot died! \n" + str(traceb) + "\nTime of death: " + str(datetime.datetime.today()) + "\n"
            )
            excFile.write("-----------------------------------------------------\n")

            if getattr(bot, "command_router", None) is not None:
                while not bot.command_router.recent_messages.empty():
                    msg = bot.command_router.recent_messages.get_nowait()
                    excFile.write(msg)
                    excFile.write("\n")
                bot.command_router.task_pool.sigquitAll()
                if log:
                    bot._logger.debug("All tasks were signaled to shut down.")

            excFile.write("-----------------------------------------------------\n")
            excFile.write("Connection Exception: \n")

            if getattr(bot, "conn", None) is not None:
                excFile.write(str(bot.conn.error) + " \n")
            else:
                excFile.write("Connection not initialized\n")

            excFile.write("-----------------------------------------------------\n")

    if log:
        bot._logger.info("End of Session\n\n\n\n")
    logging.shutdown()


if __name__ == "__main__":
    asyncio.run(async_main())
