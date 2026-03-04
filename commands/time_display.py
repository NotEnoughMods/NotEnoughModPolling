import time

from command_router import Permission

PLUGIN_ID = "time_display"


def _choose_st_nd_rd_th(number):
    if number.endswith("1"):
        return "st"
    elif number.endswith("2"):
        return "nd"
    elif number.endswith("3"):
        return "rd"
    else:
        return "th"


def _format_day_of_month(day):
    if len(day) > 1:
        if day[-2] == 1:
            return day + "th"
        else:
            return day + _choose_st_nd_rd_th(day)
    else:
        return day + _choose_st_nd_rd_th(day)


def _create_date(time_arg):
    datetimestring = time.strftime("%I:%M%p, {0} of %B %Y", time_arg)
    day = time.strftime("%d", time_arg)
    day = day.lstrip("0")
    return datetimestring.format(_format_day_of_month(day))


async def _time(router, name, params, channel, userdata, rank, is_channel):
    await router.send_message(channel, _create_date(time.localtime()))


async def _utc(router, name, params, channel, userdata, rank, is_channel):
    utc_time = time.time()

    destination = channel if is_channel else name

    if len(params) > 0:
        tz_parameter = params[0]
        sign = tz_parameter[0]

        if sign == "+":
            sign = 1
        elif sign == "-":
            sign = -1
        else:
            await router.send_chat_message(
                router.send,
                destination,
                "Incorrect format. Check help about the command.",
            )
            return

        timeoffset = tz_parameter[1:]

        if ":" in timeoffset:
            hour, minute = timeoffset.split(":", 1)

            if not hour.isdigit() or not minute.isdigit():
                await router.send_chat_message(
                    router.send,
                    destination,
                    "Incorrect time offset. Needs to be a number.",
                )
                return

            tz_offset_hour = sign * int(hour)
            tz_offset_minute = sign * int(minute)

        else:
            if not timeoffset.isdigit():
                await router.send_chat_message(
                    router.send,
                    destination,
                    "Incorrect time offset. Needs to be a number.",
                )
                return

            tz_offset_hour = sign * int(timeoffset)
            tz_offset_minute = 0

    else:
        tz_offset_hour = 0
        tz_offset_minute = 0

    offset_time = utc_time + 3600 * tz_offset_hour + 60 * tz_offset_minute

    try:
        offset_utc_time = time.gmtime(offset_time)
        datestring = _create_date(offset_utc_time)
    except ValueError:
        await router.send_message(
            destination,
            "Intergalactic timezones not supported. Please put in a smaller number.",
        )
        return

    await router.send_message(destination, datestring)


async def setup(router, startup):
    entry = router.helper.new_help("utc")

    entry.add_description(
        "The 'utc' command shows the current time in UTC. Optionally, you can set a "
        "offset according to which the time will be modified. "
    )
    entry.add_description(
        "This allows you to check the time in different time zones, if you know the offset value for that time zone."
    )
    entry.add_argument(
        "UTC offset",
        "The offset value for the UTC time. Format needs to be +<hour> or -<hour>, "
        "where you replace <hour> with a hour value. You can also specify the minutes, "
        "in which case the format is +<hour>:<minute> or -<hour>:<minute>.",
        optional=True,
    )
    entry.rank = 0

    router.helper.register_help(entry, overwrite=True)


COMMANDS = {
    "time": {"execute": _time, "permission": Permission.OP, "allow_private": True},
    "utc": {"execute": _utc, "permission": Permission.GUEST, "allow_private": True},
}
