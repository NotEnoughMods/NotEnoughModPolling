import json
from unittest.mock import MagicMock, patch

import pytest

from ban_list import BanList
from bot_events import MsgEvent, StandardEvent, TimerEvent
from mod_polling.poller import ModPoller


@pytest.fixture
def minimal_config_yml(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "github:\n"
        "  client_id: test\n"
        "  client_secret: test\n"
        "polling:\n"
        "  host_delay: 0\n"
        "  auto_start: false\n"
        "  interval: 60\n"
        "  channel: '#test'\n"
        "irc:\n"
        "  staff_channel: '#test'\n"
    )
    return config


@pytest.fixture
def minimal_mods_json(tmp_path):
    mods = {
        "TestMod": {
            "function": "CheckForgeJson",
            "active": True,
            "forgejson": {"url": "https://example.com/forge.json", "mcversion": "1.12.2"},
        },
        "CurseMod": {
            "function": "CheckCurse",
            "active": True,
            "curse": {
                "id": "12345",
                "regex": r"CurseMod-(?P<version>[0-9.]+)\.jar",
            },
        },
    }
    path = tmp_path / "mods.json"
    path.write_text(json.dumps(mods))
    return path


@pytest.fixture
def minimal_version_blocklist(tmp_path):
    path = tmp_path / "version_blocklist.yml"
    path.write_text("- '\\.jar'\n- 'src'\n")
    return path


@pytest.fixture
def minimal_mc_mapping(tmp_path):
    path = tmp_path / "mc_mapping.yml"
    path.write_text("'1.4.6': '1.4.7'\n")
    return path


@pytest.fixture
def mod_poller(tmp_path, minimal_config_yml, minimal_mods_json, minimal_version_blocklist, minimal_mc_mapping):
    """Create a ModPoller with patched file I/O so no real files are needed."""
    import builtins

    _real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        p = str(path)
        if "config.yml" in p:
            return _real_open(minimal_config_yml, *args, **kwargs)
        elif "mods.json" in p:
            return _real_open(minimal_mods_json, *args, **kwargs)
        elif "version_blocklist.yml" in p:
            return _real_open(minimal_version_blocklist, *args, **kwargs)
        elif "mc_mapping.yml" in p:
            return _real_open(minimal_mc_mapping, *args, **kwargs)
        else:
            return _real_open(path, *args, **kwargs)

    mock_env = MagicMock()
    with (
        patch("builtins.open", side_effect=fake_open),
        patch("mod_polling.poller.Environment", return_value=mock_env),
    ):
        poller = ModPoller()

    poller.session = MagicMock()
    poller.mc_blocklist = set()
    return poller


@pytest.fixture
def ban_list(tmp_path):
    return BanList(tmp_path / "test.db")


@pytest.fixture
def standard_event():
    return StandardEvent()


@pytest.fixture
def timer_event():
    return TimerEvent()


@pytest.fixture
def msg_event():
    return MsgEvent()
