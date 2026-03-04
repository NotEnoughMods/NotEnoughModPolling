import logging

ID = "PRIVMSG"

msg_log = logging.getLogger("PRIVMSG")


async def execute(self, send_msg, msgprefix, command, params):
    # print params, prefix

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
        perms = ""
        # print "HELP I'M GETTING PRIVMSGD BY ",name," : ",chat_message
        msg_log.info("Private message from '%s' [%s@%s]: %s", name, ident, host, chat_message)
    else:
        is_channel = True
        channel = self.get_channel_true_case(channel)
        perms = self.get_user_rank(channel, name)

    # print splitted, channel()

    # print msgprefix, params

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
    # print "ok"

    if name in self.operators and self.auth_tracker.is_registered(name):  # and (perms == "@" or perms == "+"):
        # print name + " is in Botlist"
        rank = 3
        perms = "@@"
    elif perms == "@":
        # print name + " is OP"
        rank = 2
    elif perms == "+":
        # print name + " is Voiced"
        rank = 1
    else:
        # print name + " is Nothing"
        rank = 0

    # rank = {"@" : 2, "+" : 1, "" : 0}[self.get_user_rank(channel, name)]
    # print self.commands
    # print chat_cmd
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

        try:
            support = self.commands[chat_cmd][0].privmsg_enabled
        except AttributeError:
            support = False

        try:
            if rank >= self.commands[chat_cmd][0].permission:
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
                        perms,
                    )
                else:
                    msg_log.info("User '%s' uses command '%s'", name, chat_cmd)
                    msg_log.debug(
                        "User info for '%s': [%s@%s] Used parameters: %s Rank: %s",
                        name,
                        ident,
                        host,
                        chat_params[1:],
                        perms,
                    )
                    msg_log.debug(
                        "User '%s' - destination: '%s' (should be the same)",
                        name,
                        channel,
                    )

                if support:
                    await self.commands[chat_cmd][0].execute(
                        self,
                        name,
                        chat_params[1:],
                        channel,
                        (ident, host),
                        perms,
                        is_channel,
                    )
                elif not support and is_channel:
                    await self.commands[chat_cmd][0].execute(self, name, chat_params[1:], channel, (ident, host), perms)

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
