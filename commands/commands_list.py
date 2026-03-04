from command_router import Permission

PLUGIN_ID = "commands_list"


async def _commands(router, name, params, channel, userdata, rank, is_channel):
    group = {}
    for i in range(rank + 1):
        group[i] = []

    for cmd_name, cmd_entry in router.commands.items():
        cmdrank = cmd_entry.permission
        if rank >= cmdrank:
            group[cmdrank].append(cmd_name)

    await router.send_notice(name, "Available commands:")
    for i in group:
        group[i].sort()
        await router.send_notice(name, "{}: {}".format(Permission(i).name.capitalize(), " | ".join(group[i])))


COMMANDS = {
    "commands": {"execute": _commands, "permission": Permission.GUEST},
}
