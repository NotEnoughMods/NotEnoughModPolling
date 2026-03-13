import asyncio
import contextlib
import datetime
import logging
import signal
import socket
import traceback

from command_router import CommandRouter
from config import Configuration
from irc_connection import IrcConnection


class IrcBot:
    def __init__(self, config_obj):
        config = config_obj.config

        self.host = config["connection"]["server"]
        self.port = config["connection"]["port"]
        self.name = config["connection"]["nickname"]
        self.password = config["connection"]["password"]
        self.ident = config["connection"]["ident"]
        self.realname = config["connection"]["realname"]

        self.force_ipv6 = config["networking"]["force_ipv6"]
        self.bind_ip = config["networking"]["bind_address"]

        self.adminlist = config["administration"]["operators"]
        self.prefix = config["administration"]["command_prefix"]
        self.loglevel = config["administration"]["logging_level"]
        self.channels = config["administration"]["channels"]

        self.nickserv_auth = False
        self.shutdown = False
        self._handler_tasks = set()
        self._logger = logging.getLogger("IRCMainLoop")

    async def start(self):
        self.conn = IrcConnection()

        local_addr = None
        family = 0

        if self.force_ipv6:
            if not socket.has_ipv6:
                raise RuntimeError("IPv6 isn't supported on this platform. Please check the config file.")
            family = socket.AF_INET6
            if self.bind_ip:
                local_addr = (self.bind_ip, 0)
        else:
            if self.bind_ip:
                local_addr = (self.bind_ip, 0)

        await self.conn.connect(self.host, self.port, local_addr=local_addr, family=family)

        # Start the write loop as a background task
        write_task = asyncio.create_task(self.conn.write_loop())

        if self.password:
            await self.conn.send_msg("PASS " + self.password)
        await self.conn.send_msg("NICK " + self.name)
        await self.conn.send_msg(f"USER {self.ident} * * {self.realname}")

        self.command_router = CommandRouter(
            self.channels,
            self.prefix,
            self.name,
            self.ident,
            self.adminlist,
            self.loglevel,
        )

        self._logger.info("Connected to %s", self.host)
        self._logger.info("BOT IS NOW ONLINE: Starting to listen for server responses.")

        # Timer event checker runs as a periodic background task
        timer_task = asyncio.create_task(self._timer_loop())

        try:
            async for msg in self.conn.read_lines():
                if self.shutdown:
                    break

                prefix, command, params = self._parse_message(msg)

                # Resolve waiters immediately (non-blocking)
                self.command_router._dispatch_waiters(prefix, command, params)

                # PING must respond instantly — run inline, no lock
                if command == "PING":
                    await self.command_router.handle(self.conn.send_msg, prefix, command, params, self.nickserv_auth)
                else:
                    # All other handlers run as tasks, serialized by lock
                    task = asyncio.create_task(self._locked_handle(prefix, command, params))
                    self._handler_tasks.add(task)
                    task.add_done_callback(self._handler_tasks.discard)
        except asyncio.CancelledError:
            self._logger.info("Main loop cancelled (shutdown)")
        finally:
            self._logger.info("Main loop has been stopped")
            self.command_router.task_pool.cancel_all()
            for t in self._handler_tasks:
                t.cancel()
            timer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer_task
            await self.command_router.close()
            await self.conn.send_msg("QUIT :Shutting down")
            try:
                await self.conn.flush(timeout=5)
            except TimeoutError:
                self._logger.warning("Timed out flushing write queue")
            write_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await write_task
            await self.conn.close()
            self._logger.info("Connection closed.")

    def _parse_message(self, msg):
        msg_parts = msg.split(" ", 2)
        prefix = msg_parts[0][1:] if msg_parts[0][0] == ":" else None
        if prefix is None:
            command = msg_parts[0]
            params = msg_parts[1] if len(msg_parts) > 1 else ""
        else:
            command = msg_parts[1]
            params = msg_parts[2] if len(msg_parts) > 2 else ""
        return prefix, command, params

    async def _locked_handle(self, prefix, command, params):
        async with self.command_router._handler_lock:
            await self.command_router.handle(self.conn.send_msg, prefix, command, params, self.nickserv_auth)

    async def _timer_loop(self):
        """Periodically check timer events."""
        try:
            while not self.shutdown:
                await self.command_router.check_timer_events()
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    def custom_nick_auth(self, result):
        if isinstance(result, str):
            self.nickserv_auth = result
        else:
            raise TypeError


def write_starting_date():
    with open("lastStart.txt", "w") as f:
        f.write("Started at: " + str(datetime.datetime.today()))


_shutdown_logger = logging.getLogger("IRCMainLoop")


def _handle_signal(sig, loop, main_task):
    for s in (signal.SIGTERM, signal.SIGINT):
        loop.remove_signal_handler(s)
    _shutdown_logger.info("Received %s, shutting down...", sig.name)
    if main_task and not main_task.done():
        main_task.cancel()


async def async_main():
    main_task = asyncio.current_task()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig, loop, main_task)

    write_starting_date()

    config_obj = Configuration()
    config_obj.load_config()
    config_obj.check_options()

    bot = IrcBot(config_obj)
    log = False

    try:
        await bot.start()
    except Exception as error:
        if getattr(bot, "_logger", None) is not None:
            bot._logger.exception("Fatal error during startup or runtime.")
            log = True
        else:
            print("Logger was not initialized, cannot write to log file.")

        print(f"Fatal error: {type(error).__name__}: {error}")
        traceb = traceback.format_exc()
        print(traceb)

        with open("exception.txt", "w") as excFile:
            excFile.write(f"Fatal error at {datetime.datetime.today()}\n")
            excFile.write(traceb + "\n")
            excFile.write("-----------------------------------------------------\n")

            if getattr(bot, "command_router", None) is not None:
                while not bot.command_router.recent_messages.empty():
                    msg = bot.command_router.recent_messages.get_nowait()
                    excFile.write(msg)
                    excFile.write("\n")
                bot.command_router.task_pool.cancel_all()
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
