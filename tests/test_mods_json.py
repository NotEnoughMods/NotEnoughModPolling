import json
from pathlib import Path

from mod_polling import poller


def dict_raise_on_duplicates(ordered_pairs):
    """Reject duplicate keys."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(f"duplicate key: {k!r}")
        d[k] = v
    return d


MODS_JSON = Path(__file__).parent.parent / "mod_polling" / "mods.json"


class TestModsJson:
    def setup_method(self):
        self.NEM = poller.ModPoller

        with open(MODS_JSON) as f:
            self.mods = json.load(f, object_pairs_hook=dict_raise_on_duplicates)

    def test_parsers_exist(self):
        for mod, mod_info in self.mods.items():
            parser = mod_info["function"]
            assert parser.startswith("Check"), f"Parser name {parser!r} for mod {mod!r} is invalid"
            assert hasattr(self.NEM, parser), f"Parser {parser!r} for mod {mod!r} doesn't exist"

    def test_curse_parser(self):
        for mod, mod_info in self.mods.items():
            if mod_info["function"] != "CheckCurse":
                continue

            msg = f"Mod {mod!r} has missing Curse parser information"

            assert "curse" in mod_info, msg
            assert "id" in mod_info["curse"], msg
            assert "regex" in mod_info["curse"], msg
            assert "name" not in mod_info["curse"]
            assert "base_path" not in mod_info["curse"]

    def test_forgejson_parser(self):
        for mod, mod_info in self.mods.items():
            if mod_info["function"] != "CheckForgeJson":
                continue

            msg = f"Mod {mod!r} has missing ForgeJson parser information"

            assert "forgejson" in mod_info, msg
            assert "url" in mod_info["forgejson"], msg
