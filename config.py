import shutil
from pathlib import Path

import yaml

CONFIG_FILE = Path("config.yml")
CONFIG_EXAMPLE = Path("config.yml.example")


class Configuration:
    def __init__(self):
        self.config = None

        self.mandatory_options = {
            "connection": {
                "nickname": True,
                "password": False,
                "ident": True,
                "realname": True,
                "server": True,
                "port": True,
            },
            "administration": {
                "operators": False,
                "channels": False,
                "command_prefix": True,
                "logging_level": True,
            },
            "networking": {"force_ipv6": True, "bind_address": False},
        }

    def load_config(self):
        if not CONFIG_FILE.exists():
            shutil.copy(CONFIG_EXAMPLE, CONFIG_FILE)
            raise RuntimeError(
                f"'{CONFIG_FILE}' was missing. A new config file has been created from "
                f"'{CONFIG_EXAMPLE}'. Please fill in the information."
            )

        with open(CONFIG_FILE) as f:
            self.config = yaml.safe_load(f)

    def check_options(self):
        for section, options in self.mandatory_options.items():
            for option, required in options.items():
                val = self.config.get(section, {}).get(option)

                if required and (val is None or val == ""):
                    raise RuntimeError(
                        f"Option '{option}' in section '{section}' has no value, but is required to have one. "
                        "Please fill in the missing information."
                    )
