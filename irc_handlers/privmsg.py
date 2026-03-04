import logging

ID = "PRIVMSG"

msg_log = logging.getLogger("PRIVMSG")


async def execute(self, send_msg, msgprefix, command, params):
    part1 = msgprefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    cmdprefix = self.cmdprefix
    splitted = params.split(" ", 1)

    channel = splitted[0]
    chat_message = splitted[1][1:]

    if channel[0] not in "#&":
        channel = name
        is_channel = False
        msg_log.info("Private message from '%s' [%s@%s]: %s", name, ident, host, chat_message)
    else:
        is_channel = True
        channel = self.get_channel_true_case(channel)

    msg_log.debug("<%s> %s", name, chat_message)

    chat_params = chat_message.rstrip().split(" ")

    for _i in range(chat_params.count("")):
        chat_params.remove("")

    try:
        chat_cmd = chat_params[0][1:].lower()
        used_prfx = chat_message[0]
    except IndexError:
        chat_cmd = ""
        used_prfx = ""

    if is_channel:
        rank = self.get_user_rank_num(channel, name)
    elif name in self.operators and self.auth_tracker.is_registered(name):
        rank = 3
    else:
        rank = 0

    if used_prfx == cmdprefix and chat_cmd in self.commands:
        banned_info = self.ban_list.check_ban(name, ident, host)

        if banned_info[0]:
            msg_log.info(
                "User '%s' uses command '%s', but user is globally banned.",
                name,
                chat_cmd,
            )
            msg_log.info("Ban information: %s", banned_info[1])

            return

        cmd = self.commands[chat_cmd]

        if not is_channel and not cmd.allow_private:
            return

        try:
            if rank >= cmd.permission:
                if is_channel:
                    msg_log.info(
                        "User '%s' uses command '%s' in channel '%s'",
                        name,
                        chat_cmd,
                        channel,
                    )
                    msg_log.debug(
                        "User info for '%s': [%s@%s] Used parameters: %s Rank: %s",
                        name,
                        ident,
                        host,
                        chat_params[1:],
                        rank,
                    )
                else:
                    msg_log.info("User '%s' uses command '%s'", name, chat_cmd)
                    msg_log.debug(
                        "User info for '%s': [%s@%s] Used parameters: %s Rank: %s",
                        name,
                        ident,
                        host,
                        chat_params[1:],
                        rank,
                    )
                    msg_log.debug(
                        "User '%s' - destination: '%s' (should be the same)",
                        name,
                        channel,
                    )

                await cmd.execute(self, name, chat_params[1:], channel, (ident, host), rank, is_channel)

        except KeyError:
            msg_log.exception("KeyError for command")
        except AttributeError:
            msg_log.exception("AttributeError for command")
    else:
        # if the message comes from a user, set channel to False
        # otherwise, set channel to the channel from which the message was received
        channel = (is_channel and channel) or False

        if not channel:
            msg_log.debug(
                "Passing a PM from user '%s' [%s@%s] to chat events: '%s'",
                name,
                ident,
                host,
                chat_message,
            )

        await self.events["chat"].run_all_events(
            self, {"name": name, "ident": ident, "host": host}, chat_message, channel
        )
