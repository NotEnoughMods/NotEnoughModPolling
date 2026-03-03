import logging

ID = "reload"
permission = 3

logger = logging.getLogger("cmd.reload")


async def execute(self, name, params, channel, userdata, rank):
    if len(params) > 0 and params[0] in self.commands:
        cmd = params[0]
        path = self.commands[cmd][1]
        logger.debug("Reloading command at path: %s", path)

        # To load the plugin in a similar way to commandHandler's _load_modules method,
        # we need to retrieve the filename of the command from the path.
        path.rpartition("/")[2][0:-3]

        await self.send_message(channel, "Reloading " + path)
        self.commands[cmd] = (self._load_source("NEMP_" + cmd, path), path)

        try:
            if not callable(self.commands[cmd][0].setup):
                self.commands[cmd][0].setup = False
        except AttributeError:
            self.commands[cmd][0].setup = False
        else:
            if self.commands[cmd][0].setup:
                await self.commands[cmd][0].setup(self, False)

        await self.send_message(channel, "Done!")

    elif len(params) > 0 and params[0] not in self.commands:
        await self.send_message(channel, "Command does not exist")
    else:
        await self.send_message(channel, "Please specify a command.")


async def setup(self, Startup):
    entry = self.helper.new_help(ID)

    entry.add_description(
        "The 'reload' command allows you to reload specific commands. All changes made to the file will take effect."
    )
    entry.add_argument("command name", "The name of the command you want to reload", optional=True)
    entry.rank = permission

    self.helper.register_help(entry, overwrite=True)
