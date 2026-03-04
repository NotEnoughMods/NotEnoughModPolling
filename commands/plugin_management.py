import logging

from command_router import CommandEntry, Permission, PluginEntry

PLUGIN_ID = "plugin_management"

logger = logging.getLogger("cmd.plugin_management")


async def _reload(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 0:
        await router.send_message(channel, "Please specify a command.")
        return

    cmd_name = params[0]

    if cmd_name not in router.commands:
        await router.send_message(channel, "Command does not exist")
        return

    plugin_id = router.commands[cmd_name].plugin_id
    plugin = router.plugins[plugin_id]
    path = plugin.path

    logger.debug("Reloading plugin '%s' at path: %s", plugin_id, path)
    await router.send_message(channel, "Reloading " + path)

    module = router._load_source("NEMP_" + plugin_id, path)

    # Unregister old commands
    for old_cmd in plugin.command_names:
        del router.commands[old_cmd]

    # Build new entries
    setup_fn = getattr(module, "setup", None)
    if setup_fn is not None and not callable(setup_fn):
        setup_fn = None

    teardown_fn = getattr(module, "teardown", None)
    if teardown_fn is not None and not callable(teardown_fn):
        teardown_fn = None

    new_command_names = []
    for new_cmd_name, cmd_info in module.COMMANDS.items():
        router.commands[new_cmd_name] = CommandEntry(
            execute=cmd_info["execute"],
            permission=cmd_info["permission"],
            allow_private=cmd_info.get("allow_private", False),
            plugin_id=module.PLUGIN_ID,
        )
        new_command_names.append(new_cmd_name)

    router.plugins[module.PLUGIN_ID] = PluginEntry(
        module=module,
        path=path,
        command_names=tuple(new_command_names),
        setup=setup_fn,
        teardown=teardown_fn,
    )

    # If old plugin_id differs from new one, clean up
    if plugin_id != module.PLUGIN_ID:
        del router.plugins[plugin_id]

    if setup_fn:
        await setup_fn(router, False)

    await router.send_message(channel, "Done!")


async def _newload(router, name, params, channel, userdata, rank, is_channel):
    files = router._list_dir("commands")
    currently_loaded = {plugin.path for plugin in router.plugins.values()}

    new_files = [f for f in files if "commands/" + f not in currently_loaded]

    if len(new_files) == 0:
        await router.send_message(channel, "No new commands found.")
    else:
        if len(new_files) == 1:
            await router.send_message(channel, "1 new command found.")
        else:
            await router.send_message(channel, f"{len(new_files)} new commands found.")

        for filename in new_files:
            filepath = "commands/" + filename
            module = router._load_source("NEMP_" + filename[:-3], filepath)

            plugin_id = module.PLUGIN_ID

            setup_fn = getattr(module, "setup", None)
            if setup_fn is not None and not callable(setup_fn):
                setup_fn = None

            teardown_fn = getattr(module, "teardown", None)
            if teardown_fn is not None and not callable(teardown_fn):
                teardown_fn = None

            command_names = []
            for cmd_name, cmd_info in module.COMMANDS.items():
                router.commands[cmd_name] = CommandEntry(
                    execute=cmd_info["execute"],
                    permission=cmd_info["permission"],
                    allow_private=cmd_info.get("allow_private", False),
                    plugin_id=plugin_id,
                )
                command_names.append(cmd_name)

            router.plugins[plugin_id] = PluginEntry(
                module=module,
                path=filepath,
                command_names=tuple(command_names),
                setup=setup_fn,
                teardown=teardown_fn,
            )

            if setup_fn:
                await setup_fn(router, True)

            await router.send_message(channel, f"{filepath} has been loaded.")
            logger.info("File %s has been newly loaded.", filename)


async def _hardreload(router, name, params, channel, userdata, rank, is_channel):
    await router.send_chat_message(router.send, channel, "Reloading..")
    router.protocol_handlers = router._load_protocol_handlers("irc_handlers")
    await router.send_chat_message(router.send, channel, "Done!")


async def setup(router, startup):
    entry = router.helper.new_help("reload")
    entry.add_description(
        "The 'reload' command allows you to reload specific commands. All changes made to the file will take effect."
    )
    entry.add_argument("command name", "The name of the command you want to reload", optional=True)
    entry.rank = 3
    router.helper.register_help(entry, overwrite=True)

    entry = router.helper.new_help("newload")
    entry.add_description(
        "The 'newload' command will load any newly added plugins that have not been "
        "loaded yet without reloading other plugins."
    )
    entry.rank = 3
    router.helper.register_help(entry, overwrite=True)


COMMANDS = {
    "reload": {"execute": _reload, "permission": Permission.ADMIN},
    "newload": {"execute": _newload, "permission": Permission.ADMIN},
    "hardreload": {"execute": _hardreload, "permission": Permission.ADMIN},
}
