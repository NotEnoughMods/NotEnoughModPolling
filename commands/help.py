import logging

from command_router import Permission

PLUGIN_ID = "help"

help_log = logging.getLogger("HelpModule")


async def _help(router, name, params, channel, userdata, rank, is_channel):
    if len(params) > 0:
        cmdname = params[0]

        try:
            help = router.helper.get_command_help(cmdname)
        except KeyError:
            help_log.error("Command not found: %s", cmdname)
            await router.send_notice(name, "No such command exists.")
            return
    else:
        await router.send_notice(name, "Specify a command you want to know more about.")
        return

    if rank < help.rank:
        await router.send_notice(name, "Command is restricted.")
        help_log.debug("Looking up command '%s', but it is restricted.", name, cmdname)
        return

    if help.custom_handler is not None:
        help._run_custom_handler(router, name, params, channel, userdata, rank)

    elif len(params) == 1:
        help_log.debug("Looking up command '%s'", name, cmdname)
        arglist = [router.cmdprefix + cmdname]

        for arg in help.arguments:
            argname = arg[0]
            optional = arg[2]

            if not optional:
                arglist.append("<" + arg[0] + ">")
            else:
                arglist.append("(" + arg[0] + ")")

        await router.send_notice(name, "Command usage: " + " ".join(arglist))

        if len(help.description) == 1:
            await router.send_notice(name, "Command description: " + help.description[0])
        elif len(help.description) > 1:
            await router.send_notice(name, "Command description: " + help.description[0])
            for line in help.description[1:]:
                await router.send_notice(name, line)
        else:
            await router.send_notice(name, "Command description: No description given.")

    elif len(params) > 1:
        cmdname = params[0]
        argname = " ".join(params[1:])

        found = False

        help_log.debug("Looking up argument '%s' for command '%s'", argname, cmdname)

        for arg in help.arguments:
            if argname.lower() == arg[0].lower():
                optional_or_required = (not arg[2] and "REQUIRED") or "OPTIONAL"

                await router.send_notice(
                    name,
                    f"Argument description for '{arg[0]}' [{optional_or_required}]: {arg[1]}",
                )
                found = True
                break

        if not found:
            await router.send_notice(name, "The command does not have such an argument")
    else:
        await router.send_notice(name, "No arguments provided.")


async def setup(router, startup):
    entry = router.helper.new_help("help")

    entry.add_description(
        "The 'help' command shows you the descriptions and arguments of commands that have "
        "added an entry to the internal Help Database."
    )
    entry.add_description("You can only view the help of a command if you are authorized to use the command.")
    entry.add_argument("command name", "The name of the command you want to know about.")
    entry.add_argument(
        "argument name",
        "The name of the argument you want to know about.",
        optional=True,
    )
    entry.rank = 0

    router.helper.register_help(entry, overwrite=True)


COMMANDS = {
    "help": {"execute": _help, "permission": Permission.GUEST},
}
