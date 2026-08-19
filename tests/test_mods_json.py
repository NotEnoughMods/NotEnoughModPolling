import json
from pathlib import Path

import pytest

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

LEGACY_CURSE_FILENAMES = (
    ("AdventOfAscension", "AoA-Tslat-1.1.3.jar", "Tslat-1.1.3"),
    ("AdventOfAscension", "AoA3-3.3.6.jar", "3.3.6"),
    ("AI-Improvements", "AIImprovements-1.7.10-0.0.1b8.jar", "0.0.1b8"),
    ("AI-Improvements", "AIImprovements-1.12-0.0.1b3.jar", "0.0.1b3"),
    ("AppleSkin", "AppleSkin-mc1.12-1.0.14.jar", "1.0.14"),
    ("Chisels&Bits", "chiselsandbits-14.33.jar", "14.33"),
    ("CoFHCore", "CoFHCore-[1.7.10]3.1.4-329.jar", "3.1.4-329"),
    ("CookingForBlockheads", "cookingbook-mc1.7.10-1.0.140.jar", "1.0.140"),
    ("CookingForBlockheads", "CookingForBlockheads_1.12.2-6.5.0.jar", "6.5.0"),
    ("DeathCounter", "DeathCounter-4.0.0.jar", "4.0.0"),
    ("DeathCounter", "DeathCounter-1.12.2-1.1.0.jar", "1.1.0"),
    ("Ding", "Ding-MC1.7.10v2.jar", "MC1.7.10v2"),
    ("Ding", "Ding-1.12.2-1.0.2.jar", "1.0.2"),
    ("ForgeMultipart", "ForgeMultipart-1.12.2-2.6.2.83-universal.jar", "2.6.2.83"),
    ("HardcoreQuestingMode", "HQM-The Journey-4.4.4.jar", "4.4.4"),
    ("IronChests", "ironchest-1.7.10-6.0.62.742-universal.jar", "6.0.62.742"),
    ("LimitedLives", "LimitedLives-4.0.0.jar", "4.0.0"),
    ("LimitedLives", "LimitedLives-1.12.1-1.0.1.jar", "1.0.1"),
    ("McJtyLib", "mcjtylib-1.8.1.jar", "1.8.1"),
    ("Ping", "Ping-1.7.X-1.0.3.B7-universal.jar", "1.0.3.B7"),
    ("RebornCore", "RebornCore-1.1.0.15-universal.jar", "1.1.0.15"),
    ("RebornCore", "RebornCore-1.12.2-3.19.5-universal.jar", "3.19.5"),
    ("RedstoneArsenal", "RedstoneArsenal-[1.7.10]1.1.2-92.jar", "1.1.2-92"),
    ("ThermalDynamics", "ThermalDynamics-[1.7.10]1.2.1-172.jar", "1.2.1-172"),
    ("ThermalExpansion", "ThermalExpansion-[1.7.10]4.1.5-248.jar", "4.1.5-248"),
    ("ThermalFoundation", "ThermalFoundation-[1.7.10]1.2.6-118.jar", "1.2.6-118"),
    ("iChunUtil", "iChunUtil-4.2.3.jar", "4.2.3"),
    ("iChunUtil", "iChunUtil-1.12.2-7.2.2.jar", "7.2.2"),
)

CURRENT_CURSE_FILENAMES = (
    ("AdventOfAscension", "AoA3-1.21.1-3.7.16.1.jar", "3.7.16.1"),
    ("AI-Improvements", "AI-Improvements-26.1.1-0.5.4.jar", "0.5.4"),
    ("AppleSkin", "appleskin-neoforge-mc26.2-3.0.10.jar", "3.0.10"),
    ("Chisels&Bits", "chisels-and-bits-neoforge-26.1.2.33.jar", "26.1.2.33"),
    ("CoFHCore", "cofh_core-1.20.1-11.0.2.56.jar", "11.0.2.56"),
    ("CookingForBlockheads", "1.20.6-cookingforblockheads-fabric-1.20.6-19.0.2.jar", "19.0.2"),
    ("DeathCounter", "DeathCounter-1.21.5-NeoForge-1.4.0.jar", "1.4.0"),
    ("Ding", "Ding-1.21.5-NeoForge-1.5.0.jar", "1.5.0"),
    ("ForgeMultipart", "CBMultipart-1.20.1-3.3.0.159-universal.jar", "3.3.0.159"),
    ("HardcoreQuestingMode", "HQM-1.20.6-5.19.0-fabric.jar", "5.19.0"),
    ("IronChests", "ironchest-1.21.11-neoforge-16.7.3.jar", "16.7.3"),
    ("LimitedLives", "LimitedLives-1.21.5-NeoForge-1.4.1.jar", "1.4.1"),
    ("McJtyLib", "mcjtylib-1.21-9.0.21.jar", "9.0.21"),
    ("Ping", "Ping-fabric-26.1.1-1.15.1.jar", "1.15.1"),
    ("RebornCore", "RebornCore-6.1.0.jar", "6.1.0"),
    ("RedstoneArsenal", "redstone_arsenal-1.20.1-8.0.1.24.jar", "8.0.1.24"),
    ("ThermalDynamics", "thermal_dynamics-1.20.1-11.0.1.23.jar", "11.0.1.23"),
    ("ThermalExpansion", "thermal_expansion-1.20.1-11.0.1.29.jar", "11.0.1.29"),
    ("ThermalFoundation", "thermal_foundation-1.20.1-11.0.6.70.jar", "11.0.6.70"),
    ("iChunUtil", "iChunUtil-1.21.5-Fabric-1.0.7.jar", "1.0.7"),
)


class TestModsJson:
    def setup_method(self):
        self.poller_cls = poller.ModPoller

        with open(MODS_JSON) as f:
            self.mods = json.load(f, object_pairs_hook=dict_raise_on_duplicates)

    def test_parsers_exist(self):
        for mod, mod_info in self.mods.items():
            parser = mod_info["parser"]
            assert hasattr(self.poller_cls, "check_" + parser), f"Parser {parser!r} for mod {mod!r} doesn't exist"

    def test_curse_parser(self):
        for mod, mod_info in self.mods.items():
            if mod_info["parser"] != "cfwidget":
                continue

            msg = f"Mod {mod!r} has missing Curse parser information"

            assert "curse" in mod_info, msg
            assert "id" in mod_info["curse"], msg
            assert "regex" in mod_info["curse"], msg
            assert "name" not in mod_info["curse"]
            assert "base_path" not in mod_info["curse"]

    def test_forgejson_parser(self):
        for mod, mod_info in self.mods.items():
            if mod_info["parser"] != "forge_json":
                continue

            msg = f"Mod {mod!r} has missing ForgeJson parser information"

            assert "forgejson" in mod_info, msg
            assert "url" in mod_info["forgejson"], msg

    def test_neoforge_parser(self):
        for mod, mod_info in self.mods.items():
            if mod_info["parser"] != "neoforge":
                continue

            msg = f"Mod {mod!r} has missing NeoForge parser information"

            assert "neoforge" in mod_info, msg
            assert "url" in mod_info["neoforge"], msg
            assert "fallback_url" in mod_info["neoforge"], msg

    @pytest.mark.parametrize(
        ("mod", "filename", "expected_version"),
        LEGACY_CURSE_FILENAMES + CURRENT_CURSE_FILENAMES,
    )
    def test_curse_filename_regressions(self, mod_poller, mod, filename, expected_version):
        # Match through the poller's own compile/search path so flag or matching changes fail here too.
        mod_poller.mods[mod] = self.mods[mod]
        mod_poller.compile_regex(mod)

        match = mod_poller.match_mod_regex(mod, filename)

        assert match, f"{mod} regex did not match {filename!r}"
        assert match.group("version") == expected_version
