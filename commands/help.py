import logging

ID = "help"
permission = 0

help_log = logging.getLogger("HelpModule")


async def execute(self, name, params, channel, userdata, rank):
    if len(params) > 0:
        cmdname = params[0]

        try:
            help = self.helper.getCmdHelp(cmdname)
        except KeyError as error:
            print(str(error))
            await self.sendNotice(name, "No such command exists.")
            return
    else:
        await self.sendNotice(name, "Specify a command you want to know more about.")
        return

    if self.rankconvert[rank] < help.rank:
        await self.sendNotice(name, "Command is restricted.")
        help_log.debug("Looking up command '%s', but it is restricted.", name, cmdname)
        return

    if help.custom_handler is not None:
        help.__run_custom_handler__(self, name, params, channel, userdata, rank)

    elif len(params) == 1:
        help_log.debug("Looking up command '%s'", name, cmdname)
        arglist = [self.cmdprefix + cmdname]

        for arg in help.arguments:
            argname = arg[0]
            optional = arg[2]

            if not optional:
                arglist.append("<" + arg[0] + ">")
            else:
                arglist.append("(" + arg[0] + ")")

        await self.sendNotice(name, "Command usage: " + " ".join(arglist))

        if len(help.description) == 1:
            await self.sendNotice(name, "Command description: " + help.description[0])
        elif len(help.description) > 1:
            await self.sendNotice(name, "Command description: " + help.description[0])
            for line in help.description[1:]:
                await self.sendNotice(name, line)
        else:
            await self.sendNotice(name, "Command description: No description given.")

    elif len(params) > 1:
        cmdname = params[0]
        argname = " ".join(params[1:])

        found = False

        help_log.debug("Looking up argument '%s' for command '%s'", argname, cmdname)

        for arg in help.arguments:
            if argname.lower() == arg[0].lower():
                optional_or_required = (not arg[2] and "REQUIRED") or "OPTIONAL"

                await self.sendNotice(
                    name,
                    f"Argument description for '{arg[0]}' [{optional_or_required}]: {arg[1]}",
                )
                found = True
                break

        if not found:
            await self.sendNotice(name, "The command does not have such an argument")
    else:
        await self.sendNotice(name, "No arguments provided.")


def test(self, name, params, channel, userdata, rank):
    print(name)


async def setup(self, Startup):
    entry = self.helper.newHelp(ID)

    entry.addDescription(
        "The 'help' command shows you the descriptions and arguments of commands that have "
        "added an entry to the internal Help Database."
    )
    entry.addDescription("You can only view the help of a command if you are authorized to use the command.")
    entry.addArgument("command name", "The name of the command you want to know about.")
    entry.addArgument(
        "argument name",
        "The name of the argument you want to know about.",
        optional=True,
    )
    entry.rank = 0

    self.helper.registerHelp(entry, overwrite=True)
