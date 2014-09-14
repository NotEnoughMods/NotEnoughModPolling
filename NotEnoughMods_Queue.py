ID = "queue"
permission = 0

class NEM_Queue():
    updatequeue = []
NEM = NEM_Queue()

def execute(self, name, params, channel, userdata, rank):
    try:
        if len(params) > 0:
            if rankTranslate[rank] >= commands[params[0]]["rank"]:
                command = commands[params[0]]["function"]
                command(self, name, params, channel, userdata, rank)
            else:
                self.sendNotice(name, "You do not have permissions for this command!")
        else:
            self.sendChatMessage(self.send, channel, "{} item(s) in the queue.".format(len(NEM.updatequeue)))
    except KeyError as e:
        self.sendChatMessage(self.send, channel, str(e))
        self.sendChatMessage(self.send, channel, "invalid command!")
        self.sendChatMessage(self.send, channel, "see {}{} help for a list of commands".format(self.cmdprefix, ID))


def command_help(self, name, params, channel, userdata, rank):
    actualRank = rankTranslate[rank]
    paramCount = len(params)
    if paramCount > 1:
        # ok, info on a command, let's go!
        if params[1] in commands:
            commandInfo = commands[params[1]]
            if actualRank < commandInfo["rank"]:
                self.sendNotice(name, "You do not have permission for this command.")
                return
            if paramCount > 2:
                param = " ".join(params[2:])
                # We want info on an argument
                argInfo = {}
                for arg in commandInfo["args"]:
                    if param == arg["name"]:
                        argInfo = arg
                        break
                self.sendNotice(name, argInfo["description"])
            else:  # just the command
                # Lets compile the argStuff
                argStuff = ""
                argCount = len(commandInfo["args"])
                if argCount > 0:
                    for arg in commandInfo["args"]:
                        if arg["required"]:
                            argStuff = argStuff + " <" + arg["name"] + ">"
                        else:
                            argStuff = argStuff + " [" + arg["name"] + "]"
                # Send to IRC
                self.sendNotice(name, commandInfo["help"])
                self.sendNotice(name, "Use case: " + self.cmdprefix + ID + " " + params[1] + argStuff)
        else:
            self.sendNotice(name, "That isn't a command...")
            return
    else:
        # List the commands
                        #0,  1,  2,  3
        commandRanks = [[], [], [], []]
        for command, info in commands.iteritems():
            commandRanks[info["rank"]].append(command)

        self.sendNotice(name, "Available commands:")
        for i in range(0, actualRank):
            if len(commandRanks[i]) > 0:
                self.sendNotice(name, nameTranslate[i] + ": " + ", ".join(commandRanks[i]))

def command_show(self, name, params, channel, userdata, rank):
    i = 0
    if len(NEM.updatequeue) == 0:
        self.sendChatMessage(self.send, channel, "There are no items currently in the queue.")
        return
    for item in NEM.updatequeue:
        self.sendChatMessage(self.send, name, "{}: {}".format(i, item))
        i += 1

def command_add(self, name, params, channel, userdata, rank):
    NEM.updatequeue.append(" ".join(params[1:]))
    self.sendChatMessage(self.send, channel, "Success!")

def command_remove(self, name, params, channel, userdata, rank):
    if params[1].isdigit():
        del NEM.updatequeue[int(params[1])]
        self.sendChatMessage(self.send, channel, "Success!")
    else:
        self.sendChatMessage(self.send, channel, "'{}' is not a number.".format(params[1]))

def command_execute(self, name, params, channel, userdata, rank):
    if params[1].isdigit():
        index = int(params[1])
    else:
        self.sendChatMessage(self.send, channel, "'{}' is not a number.".format(params[2]))
        return

    if len(NEM.updatequeue) >= index and rank > 0:
        self.sendChatMessage(self.send, channel, NEM.updatequeue[index])
        del NEM.updatequeue[index]
        self.sendChatMessage(self.send, channel, "Success!")


rankTranslate = {
    "": 0,
    "+": 1,
    "@": 2,
    "@@": 3
}
nameTranslate = [
    "Guest",
    "Voice",
    "Operator",
    "Bot Admin"
]

commands = {
    "show": {
        "function": command_show,
        "rank": 0,
        "help": "This will query you with the contents of the queue.",
        "args": []
    },
    "add": {
        "function": command_add,
        "rank": 0,
        "help": "This will add a new item to the queue.",
        "args": [
            {
                "name": "modinfo",
                "description": "the command to relay to ModBot if approved.",
                "required": True
            }
        ]
    },
    "remove": {
        "function": command_remove,
        "rank": 1,
        "help": "This will remove an item from the queue. Usage: '=nemp queue del [index]'.",
        "args": [
            {
                "name": "index",
                "description": "the number attached to the item you wish to remove",
                "required": True
            }
        ]
    },
    "execute": {
        "function": command_execute,
        "rank": 1,
        "help": "Executes the given index for ModBot to do its work",
        "args": [
            {
                "name": "index",
                "description": "the number attached to the item you wish to relay to ModBot",
                "required": True
            }
        ]
    },
    "help": {
        "function": command_help,
        "rank": 0,
        "help": "Shows this info..?",
        "args": [
            {
                "name": "command",
                "description": "The command you want info for",
                "required": False
            }, {
                "name": "arg",
                "description": "The argument you want info for",
                "required": False
            }
        ]
    }
}
