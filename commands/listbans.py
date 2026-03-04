from ban_list import NoSuchBanGroup

ID = "listbans"
permission = 3


async def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        groups = self.ban_list.get_groups()

        await self.send_notice(
            user,
            "Specify a group. The following groups are currently defined: {}".format(", ".join(groups)),
        )

    elif len(params) >= 1:
        group_name = params[0]

        try:
            bans = [self.ban_list.unescape_banstring(ban_tuple[1]) for ban_tuple in self.ban_list.get_bans(group_name)]
            output = ", ".join(bans)

            if len(bans) == 0:
                await self.send_notice(user, f"The group '{group_name}' contains no bans.")
            elif len(bans) == 1:
                await self.send_notice(
                    user,
                    f"The group '{group_name}' contains the following ban: {output}",
                )
            elif len(bans) > 1:
                await self.send_notice(
                    user,
                    f"The group '{group_name}' contains the following bans:",
                )
                await self.send_notice(user, output)

        except NoSuchBanGroup as error:
            await self.send_notice(user, f"Ban group '{error.group}' does not exist.")
