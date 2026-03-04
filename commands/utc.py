import time

ID = "utc"
permission = 0
privmsg_enabled = True


async def execute(self, name, params, channel, userdata, rank, chan):
    utc_time = time.time()

    destination = channel if chan else name

    if len(params) > 0:
        tz_parameter = params[0]
        sign = tz_parameter[0]

        if sign == "+":
            sign = 1
        elif sign == "-":
            sign = -1
        else:
            await self.send_chat_message(
                self.send,
                destination,
                "Incorrect format. Check help about the command.",
            )
            return

        timeoffset = tz_parameter[1:]

        if ":" in timeoffset:
            hour, minute = timeoffset.split(":", 1)

            if not hour.isdigit() or not minute.isdigit():
                await self.send_chat_message(
                    self.send,
                    destination,
                    "Incorrect time offset. Needs to be a number.",
                )
                return

            tz_offset_hour = sign * int(hour)
            tz_offset_minute = sign * int(minute)

        else:
            if not timeoffset.isdigit():
                await self.send_chat_message(
                    self.send,
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
        datestring = __create_date(offset_utc_time)
    except ValueError:
        await self.send_message(
            destination,
            "Intergalactic timezones not supported. Please put in a smaller number.",
        )
        return

    await self.send_message(destination, datestring)


def __create_date(time_arg):
    local_derp = time_arg
    datetimestring = time.strftime("%I:%M%p, {0} of %B %Y", local_derp)
    day = time.strftime("%d", local_derp)
    day = day.lstrip("0")

    return datetimestring.format(format_day_of_month(day))


def choose_st_nd_rd_th(number):
    if number.endswith("1"):
        return "st"
    elif number.endswith("2"):
        return "nd"
    elif number.endswith("3"):
        return "rd"
    else:
        return "th"


def format_day_of_month(day):
    if len(day) > 1:
        if day[-2] == 1:
            return day + "th"
        else:
            return day + choose_st_nd_rd_th(day)
    else:
        return day + choose_st_nd_rd_th(day)


async def setup(self, startup):
    entry = self.helper.new_help(ID)

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

    self.helper.register_help(entry, overwrite=True)
