from datetime import datetime

ID = "watchdog"
permission = 3
privmsg_enabled = True


def choose_singular_or_plural(num, singular, plural):
    if num > 1:
        return f"{num} {plural}"
    elif num == 1:
        return f"{num} {singular}"
    else:
        return None


async def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) == 0:
        uptime = datetime.now() - self.startup_time

        weeks = uptime.days // 7
        days = uptime.days % 7

        hours = uptime.seconds // (60 * 60)
        minutes = (uptime.seconds % (60 * 60)) // 60

        time_list = []

        week_string = choose_singular_or_plural(weeks, "week", "weeks")
        day_string = choose_singular_or_plural(days, "day", "days")
        hour_string = choose_singular_or_plural(hours, "hour", "hours")
        min_string = choose_singular_or_plural(minutes, "minute", "minutes")

        if week_string is not None:
            time_list.append(week_string)
        if day_string is not None:
            time_list.append(day_string)
        if hour_string is not None:
            time_list.append(hour_string)
        if min_string is not None:
            time_list.append(min_string)

        if len(time_list) == 0:
            time_list.append("Just started")

        await self.send_message(channel, "Uptime: " + ", ".join(time_list))

        stats = {}

        for event_type in self.events:
            average = None
            minimum = None
            maximum = None

            for event in self.events[event_type]._events:
                event_stats = self.events[event_type]._events[event]["stats"]

                if average is None:
                    average, minimum, maximum = (
                        event_stats["average"],
                        event_stats["min"],
                        event_stats["max"],
                    )
                else:
                    if event_stats["average"] is None:
                        continue

                    if event_stats["min"] < minimum:
                        minimum = event_stats["min"]
                    if event_stats["max"] > maximum:
                        maximum = event_stats["max"]
                    average = (average + event_stats["average"]) / 2

            stats[event_type] = [average, minimum, maximum]

        data_output = []

        for event in stats:
            average, minimum, maximum = stats[event]
            if average is None:
                average, minimum, maximum = 0, 0, 0

            # The micro prefix in unicode
            data_output.append(
                f"{event}: [{round(minimum / (10**-6), 2)}\u00b5s/"
                f"{round(maximum / (10**-6), 2)}\u00b5s/"
                f"{round(average / (10**-6), 2)}\u00b5s]"
            )

        final_string = "Event statistics: (min/max/average): " + ", ".join(data_output)

        await self.send_message(channel, final_string)

        task_info = []
        for task_name, task_data in self.task_pool.pool.items():
            time_delta = task_data["handle"].time_delta
            if time_delta is None:
                time_delta = 0

            task_info.append(f"{task_name} [{round(time_delta, 2)}\u00b5s]")

        if len(task_info) == 0:
            await self.send_message(channel, "No tasks running right now.")
        else:
            final_string = "The following tasks are running: " + ", ".join(task_info)
            await self.send_message(channel, final_string)

    else:
        event_type = params[0]

        if event_type in self.events:
            event_stats = {}

            data_output = []

            for event in self.events[event_type]._events:
                stats = self.events[event_type]._events[event]["stats"]
                average, minimum, maximum = stats["average"], stats["min"], stats["max"]

                if average is None:
                    average, minimum, maximum = 0, 0, 0

                # The micro prefix in unicode
                data_output.append(
                    f"{event}: [{round(minimum / (10**-6), 2)}\u00b5s/"
                    f"{round(maximum / (10**-6), 2)}\u00b5s/"
                    f"{round(average / (10**-6), 2)}\u00b5s]"
                )

            await self.send_message(
                channel,
                "Statistics for event type '{}': {}".format(event_type, ", ".join(data_output)),
            )

        else:
            await self.send_message(channel, "No such event type.")
