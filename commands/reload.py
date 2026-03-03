ID = "reload"
permission = 3


async def execute(self, name, params, channel, userdata, rank):
    if len(params) > 0 and params[0] in self.commands:
        cmd = params[0]
        path = self.commands[cmd][1]
        print(path)

        # To load the plugin in a similar way to commandHandler's __LoadModules__ method,
        # we need to retrieve the filename of the command from the path.
        path.rpartition("/")[2][0:-3]

        await self.sendMessage(channel, "Reloading " + path)
        self.commands[cmd] = (self._load_source("RenolIRC_" + cmd, path), path)

        try:
            if not callable(self.commands[cmd][0].setup):
                self.commands[cmd][0].setup = False
        except AttributeError:
            self.commands[cmd][0].setup = False
        else:
            if self.commands[cmd][0].setup:
                await self.commands[cmd][0].setup(self, False)

        await self.sendMessage(channel, "Done!")

    elif len(params) > 0 and params[0] not in self.commands:
        await self.sendMessage(channel, "Command does not exist")
    else:
        await self.sendMessage(channel, "Please specify a command.")


async def setup(self, Startup):
    entry = self.helper.newHelp(ID)

    entry.addDescription(
        "The 'reload' command allows you to reload specific commands. All changes made to the file will take effect."
    )
    entry.addArgument("command name", "The name of the command you want to reload", optional=True)
    entry.rank = permission

    self.helper.registerHelp(entry, overwrite=True)
