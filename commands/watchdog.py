from datetime import datetime

ID = "watchdog"
permission = 3
privmsgEnabled = True


def choose_singular_or_plural(num, singular, plural):
    if num > 1:
        return f"{num} {plural}"
    elif num == 1:
        return f"{num} {singular}"
    else:
        return None


async def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) == 0:
        uptime = datetime.now() - self.startupTime

        weeks = uptime.days // 7
        days = uptime.days % 7

        hours = uptime.seconds // (60 * 60)
        minutes = (uptime.seconds % (60 * 60)) // 60

        timeList = []

        weekString = choose_singular_or_plural(weeks, "week", "weeks")
        dayString = choose_singular_or_plural(days, "day", "days")
        hourString = choose_singular_or_plural(hours, "hour", "hours")
        minString = choose_singular_or_plural(minutes, "minute", "minutes")

        if weekString is not None:
            timeList.append(weekString)
        if dayString is not None:
            timeList.append(dayString)
        if hourString is not None:
            timeList.append(hourString)
        if minString is not None:
            timeList.append(minString)

        if len(timeList) == 0:
            timeList.append("Just started")

        await self.sendMessage(channel, "Uptime: " + ", ".join(timeList))

        stats = {}

        for eventType in self.events:
            average = None
            minimum = None
            maximum = None

            for event in self.events[eventType].__events__:
                eventStats = self.events[eventType].__events__[event]["stats"]

                if average is None:
                    average, minimum, maximum = (
                        eventStats["average"],
                        eventStats["min"],
                        eventStats["max"],
                    )
                else:
                    if eventStats["average"] is None:
                        continue

                    if eventStats["min"] < minimum:
                        minimum = eventStats["min"]
                    if eventStats["max"] > maximum:
                        maximum = eventStats["max"]
                    average = (average + eventStats["average"]) / 2

            stats[eventType] = [average, minimum, maximum]

        dataOutput = []

        for event in stats:
            average, minimum, maximum = stats[event]
            if average is None:
                average, minimum, maximum = 0, 0, 0

            # The micro prefix in unicode
            dataOutput.append(
                f"{event}: [{round(minimum / (10**-6), 2)}\u00b5s/"
                f"{round(maximum / (10**-6), 2)}\u00b5s/"
                f"{round(average / (10**-6), 2)}\u00b5s]"
            )

        finalString = "Event statistics: (min/max/average): " + ", ".join(dataOutput)

        await self.sendMessage(channel, finalString)

        threadInfo = []
        for threadName, threadData in self.threading.pool.items():
            timeDelta = threadData["thread"].timeDelta
            if timeDelta is None:
                timeDelta = 0

            threadInfo.append(f"{threadName} [{round(timeDelta, 2)}\u00b5s]")

        if len(threadInfo) == 0:
            await self.sendMessage(channel, "No threads running right now.")
        else:
            finalString = "The following threads are running: " + ", ".join(threadInfo)
            await self.sendMessage(channel, finalString)

    else:
        eventType = params[0]

        if eventType in self.events:
            eventStats = {}

            dataOutput = []

            for event in self.events[eventType].__events__:
                stats = self.events[eventType].__events__[event]["stats"]
                average, minimum, maximum = stats["average"], stats["min"], stats["max"]

                if average is None:
                    average, minimum, maximum = 0, 0, 0

                # The micro prefix in unicode
                dataOutput.append(
                    f"{event}: [{round(minimum / (10**-6), 2)}\u00b5s/"
                    f"{round(maximum / (10**-6), 2)}\u00b5s/"
                    f"{round(average / (10**-6), 2)}\u00b5s]"
                )

            await self.sendMessage(
                channel,
                "Statistics for event type '{}': {}".format(eventType, ", ".join(dataOutput)),
            )

        else:
            await self.sendMessage(channel, "No such event type.")
