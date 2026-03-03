ID = "newload"
permission = 3


async def execute(self, name, params, channel, userdata, rank):
    files = self.__ListDir__("commands")
    currentlyLoaded = [self.commands[cmd][1] for cmd in self.commands]

    for item in currentlyLoaded:
        filename = item.partition("/")[2]
        files.remove(filename)

    if len(files) == 0:
        await self.sendMessage(channel, "No new commands found.")
    else:
        if len(files) == 1:
            await self.sendMessage(channel, "1 new command found.")
        else:
            await self.sendMessage(channel, f"{len(files)} new commands found.")

        for filename in files:
            path = "commands/" + filename
            module = self._load_source("RenolIRC_" + filename[0:-3], path)
            cmd = module.ID

            self.commands[cmd] = (module, path)

            try:
                if not callable(module.setup):
                    module.setup = False
                    self._logger.debug(f"File {filename} does not use a setup function")
            except AttributeError:
                module.setup = False
                self._logger.debug(f"File {filename} does not use a setup function")

            if module.setup:
                await module.setup(self, True)

            await self.sendMessage(channel, f"{path} has been loaded.")
            self._logger.info(f"File {filename} has been newly loaded.")


async def setup(self, Startup):
    entry = self.helper.newHelp(ID)

    entry.addDescription(
        "The 'newload' command will load any newly added plugins that have not been "
        "loaded yet without reloading other plugins."
    )
    entry.rank = permission

    self.helper.registerHelp(entry, overwrite=True)
