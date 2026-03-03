import json
import unittest

from NEMP import NEMP_Class


# From http://stackoverflow.com/a/14902564/134960
def dict_raise_on_duplicates(ordered_pairs):
    """Reject duplicate keys."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(f"duplicate key: {k!r}")
        else:
            d[k] = v
    return d


class TestModsJson(unittest.TestCase):
    def setUp(self):
        self.NEM = NEMP_Class.NotEnoughClasses

        with open("NEMP/mods.json") as f:
            self.mods = json.load(f, object_pairs_hook=dict_raise_on_duplicates)

    def test_parsers_exist(self):
        for mod, mod_info in self.mods.items():
            parser = mod_info["function"]
            self.assertTrue(
                parser.startswith("Check"),
                msg=f"Parser name {parser!r} for mod {mod!r} is invalid",
            )
            self.assertTrue(
                hasattr(self.NEM, parser),
                msg=f"Parser {parser!r} for mod {mod!r} doesn't exist",
            )

    def test_curse_parser(self):
        for mod, mod_info in self.mods.items():
            parser = mod_info["function"]

            if parser != "CheckCurse":
                continue

            msg = f"Mod {mod!r} has missing Curse parser information"

            self.assertIn("curse", mod_info, msg=msg)
            self.assertIn("id", mod_info["curse"], msg=msg)
            self.assertIn("regex", mod_info["curse"], msg=msg)
            self.assertNotIn("name", mod_info["curse"])
            self.assertNotIn("base_path", mod_info["curse"])

    def test_forgejson_parser(self):
        for mod, mod_info in self.mods.items():
            parser = mod_info["function"]

            if parser != "CheckForgeJson":
                continue

            msg = f"Mod {mod!r} has missing ForgeJson parser information"

            self.assertIn("forgejson", mod_info, msg=msg)
            self.assertIn("url", mod_info["forgejson"], msg=msg)
