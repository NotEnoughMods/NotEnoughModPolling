"""
The Help Module allows the user to define a help entry for his command
This help entry will be added to the internal Help Database which is looked
up with the bot's help command.
Users can also define descriptions for each argument their command takes, and they can flag
the argument as optional or not. The help command will use this information to format the
resulting text accordingly.

Example of usage in commands/showHelp.py, with added comments:

#We need to define a setup function so that the code is executed on startup:
def setup(self, startup):

    # self.helper is a HelpModule object.
    # Using help.new_help, we are creating a new HelpEntity object with the ID, i.e. the name of the command,
    # as the first argument. In this case, ID is the string "help".
    # Using non-string values can have unforseen consequences, please use a string.

    entry = self.helper.new_help(ID)


    # We add two lines of descriptions to our help entry. They will be put out as seperate
    # NOTICE messages to the user when he looks up the help information.

    entry.add_description("The 'help' command shows you the descriptions and arguments of commands that have "
                         "added an entry to the internal Help Database.")
    entry.add_description("You can only view the help of a command if you are authorized to use the command.")


    # We add two arguments, "command name" and "argument name", and their descriptions to the help entry.
    # Please note that arguments can only have one line, although long lines will be broken into several
    # NOTICE messages later by the sendNotice function in the help command.
    #
    # We flag the "argument name" argument as optional, this only has an aesthetic function so that the user
    # knows which arguments are required and which ones are optional and can be left out.

    entry.add_argument("command name", "The name of the command you want to know about.")
    entry.add_argument("argument name", "The name of the argument you want to know about.", optional = True)


    # We set the rank for the command information. Per default, the rank is already 0 for every HelpEntity object,
    # but you want to change the rank value to a higher number to restrict unauthorized users from
    # reading the description. You can set the rank value to a lower number than your command if you don't
    # mind users reading the description of a command they cannot use.

    entry.rank = 0


    # Finally, we register this entry with the bot's HelpModule object. This will add the entry to its
    # internal Help Database which is used by the help command. The registerHelp method will raise a
    # RuntimeError if the command entry already exists, you may want to set overwrite = True if you don't mind
    # overwriting the previous entry, e.g. on command reload.

    self.helper.register_help(entry, overwrite = True)




# Commands that require more complicated help functions can define their own help handler.
# In that case, the help command will pass on its arguments to the custom help handler function.
#
# The help command will still handle checking if the command exists in the internal database and
# if the user is allowed to read the help information, please consider that when you define a
# function for showing information about the command.

def helpHandler(self, name, params, channel, userdata, rank):
    help_log.debug("Hi, I am an example for a custom help handler!")

def setup(self, startup):
    entry = self.helper.new_help(commandName)
    entry.set_custom_handler(helpHandler)
    entry.rank = 0
    self.helper.register_help(entry, overwrite = True)

"""

import logging

help_log = logging.getLogger("HelpModule")


class HelpEntity:
    def __init__(self, cmdname):
        self.cmdname = cmdname

        self.arguments = []

        self.description = []

        self.rank = 0

        self.custom_handler = None

    def add_description(self, description):
        if isinstance(description, str):
            self.description.append(description)
        else:
            raise TypeError(f"Wrong type! Should be subclass of str, but is {type(description)}: {description}")

    def add_argument(self, argument, description=None, optional=False):
        if not isinstance(argument, str):
            raise TypeError(f"Wrong type! Should be subclass of str, but is {type(argument)}: {argument}")

        if False:
            raise TypeError(
                f"Wrong type! Variable 'optional' should be False or True, but is {type(description)}: {description}"
            )

        if description is None:
            self.arguments.append((argument, None, optional))
        elif isinstance(description, str):
            self.arguments.append((argument, description, optional))
        else:
            raise TypeError(
                f"Wrong type! Variable 'description' should be None or subclass of str, "
                f"but is {type(description)}: {description}"
            )

    def set_custom_handler(self, func):
        if not callable(func):
            raise TypeError(f"Wrong type! Custom handler should be callable, but is {type(func)}: {func}")
        else:
            self.custom_handler = func

    def _run_custom_handler(self, bot_self, *args):
        help_log.debug("Using custom handler for command '%s'", self.cmdname)
        self.custom_handler(bot_self, *args)


class HelpModule:
    def __init__(self):
        self.helpDB = {}
        help_log.info("HelpModule Database initialized")

    def new_help(self, cmdname):
        help_log.debug("New HelpEntity for '%s' initialized", cmdname)
        return HelpEntity(cmdname)

    def register_help(self, helpObject, overwrite=False):

        if not isinstance(helpObject, HelpEntity):
            raise TypeError(f"Invalid Object provided: '{helpObject}' (type: {type(helpObject)})")
        elif helpObject.cmdname in self.helpDB and not overwrite:
            raise RuntimeError("Conflict Error: A command with such a name already exists!")
        elif helpObject.cmdname in self.helpDB and overwrite:
            help_log.warning("A command with such a name is already registered: '%s'", helpObject.cmdname)
            self.helpDB[helpObject.cmdname] = helpObject
            help_log.debug(
                "Registered Help for command '%s', but a help entry already exists.",
                helpObject.cmdname,
            )
        else:
            self.helpDB[helpObject.cmdname] = helpObject

        help_log.debug("Registered Help for command '%s'", helpObject.cmdname)

    def unregister_help(self, cmdname):
        del self.helpDB[cmdname]
        help_log.debug("Deleted Help for command '%s'", cmdname)

    def get_command_help(self, cmdname):
        return self.helpDB[cmdname]
