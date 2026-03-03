import time

ID = "time"
permission = 2
privmsgEnabled = True


def execute(self, name, params, channel, userdata, rank, chan):
    self.sendMessage(channel, __create_date())
    
def __create_date():
    local_derp = time.localtime()
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