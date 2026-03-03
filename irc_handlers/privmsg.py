import logging

ID = "PRIVMSG"

msg_log = logging.getLogger("PRIVMSG")


async def execute(self, sendMsg, msgprefix, command, params):
    # print params, prefix

    part1 = msgprefix.partition("!")
    part2 = part1[2].partition("@")

    name = part1[0]
    ident = part2[0]
    host = part2[2]

    cmdprefix = self.cmdprefix
    splitted = params.split(" ", 1)

    channel = splitted[0]
    chatMessage = splitted[1][1:]

    if channel[0] not in "#&":
        channel = name
        is_channel = False
        perms = ""
        # print "HELP I'M GETTING PRIVMSGD BY ",name," : ",chatMessage
        msg_log.info("Private message from '%s' [%s@%s]: %s", name, ident, host, chatMessage)
    else:
        is_channel = True
        channel = self.get_channel_true_case(channel)
        perms = self.get_user_rank(channel, name)

    # print splitted, channel()

    # print msgprefix, params

    msg_log.debug("<%s> %s", name, chatMessage)

    chatParams = chatMessage.rstrip().split(" ")

    for _i in range(chatParams.count("")):
        chatParams.remove("")

    try:
        chatCmd = chatParams[0][1:].lower()
        usedPrfx = chatMessage[0]
    except IndexError:
        chatCmd = ""
        usedPrfx = ""
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
    # print chatCmd
    if usedPrfx == cmdprefix and chatCmd in self.commands:
        bannedInfo = self.ban_list.check_ban(name, ident, host)

        if bannedInfo[0]:
            msg_log.info(
                "User '%s' uses command '%s', but user is globally banned.",
                name,
                chatCmd,
            )
            msg_log.info("Ban information: %s", bannedInfo[1])

            return

        try:
            support = self.commands[chatCmd][0].privmsgEnabled
        except AttributeError:
            support = False

        try:
            if rank >= self.commands[chatCmd][0].permission:
                if is_channel:
                    msg_log.info(
                        "User '%s' uses command '%s' in channel '%s'",
                        name,
                        chatCmd,
                        channel,
                    )
                    msg_log.debug(
                        "User info for '%s': [%s@%s] Used parameters: %s Rank: %s",
                        name,
                        ident,
                        host,
                        chatParams[1:],
                        perms,
                    )
                else:
                    msg_log.info("User '%s' uses command '%s'", name, chatCmd)
                    msg_log.debug(
                        "User info for '%s': [%s@%s] Used parameters: %s Rank: %s",
                        name,
                        ident,
                        host,
                        chatParams[1:],
                        perms,
                    )
                    msg_log.debug(
                        "User '%s' - destination: '%s' (should be the same)",
                        name,
                        channel,
                    )

                if support:
                    await self.commands[chatCmd][0].execute(
                        self,
                        name,
                        chatParams[1:],
                        channel,
                        (ident, host),
                        perms,
                        is_channel,
                    )
                elif not support and is_channel:
                    await self.commands[chatCmd][0].execute(self, name, chatParams[1:], channel, (ident, host), perms)

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
                chatMessage,
            )

        await self.events["chat"].run_all_events(
            self, {"name": name, "ident": ident, "host": host}, chatMessage, channel
        )
