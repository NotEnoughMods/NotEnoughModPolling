ID = "checkban"
permission = 3


async def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        await self.send_notice(user, "Specify a user formated as username!ident@host.")

    if len(params) >= 1:
        userstring = params[0]

        bans = self.ban_list.get_bans(matchingString=userstring)

        output = []
        for ban in bans:
            info = f"{self.ban_list.unescape_banstring(ban[1])} [{ban[0]}] Reason: {ban[2]}"
            output.append(info)

        output = " | ".join(output)

        if len(output) == 0:
            await self.send_notice(user, "The user is not affected by any bans.")
        elif len(output) == 1:
            await self.send_notice(user, f"The user is affected by the following ban: {output}")
        elif len(output) > 1:
            await self.send_notice(user, "The user is affected by the following bans:")
            await self.send_notice(user, output)
