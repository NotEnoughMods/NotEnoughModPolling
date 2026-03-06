import json
import logging
import re
import shutil
from pathlib import Path
from urllib.parse import quote as urlquote

import aiohttp
import yaml

PLUGIN_ID = "nem_relay"

relay_logger = logging.getLogger("NEM_Relay")

CONFIG_FILE = Path("config/nem_relay.yml")
CONFIG_EXAMPLE = Path("config/nem_relay.yml.example")

MODBOT_REGEX = re.compile(
    r"\x0312(?P<list>.+?)\x03\] \x0306(?P<mod>.+?)\x03(?P<dev> \(dev\))? "
    r"(?P<phrasing>added at|updated to) \x03(?:03|05)(?P<version>.+?)\x03"
)

RELAY_EVENT = "NEM_Discord_Relay"


def _load_config():
    if not CONFIG_FILE.exists():
        if CONFIG_EXAMPLE.exists():
            shutil.copy(CONFIG_EXAMPLE, CONFIG_FILE)
            relay_logger.info("Created %s from example. Please fill in the webhook URL.", CONFIG_FILE)
        else:
            relay_logger.warning("No config at %s — relay will be disabled.", CONFIG_FILE)
            return {}

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f) or {}


class Plugin:
    def __init__(self):
        self.session = None
        self.webhook_url = None
        self.listen_channel = "#notenoughmods"
        self.listen_nick = "ModBot"

    async def setup(self, router, startup):
        config = _load_config()

        if self.session:
            await self.session.close()

        self.webhook_url = config.get("discord", {}).get("webhook_url", "")
        self.listen_channel = config.get("nem", {}).get("listen_channel", "#notenoughmods")
        self.listen_nick = config.get("nem", {}).get("listen_nick", "ModBot")

        if not self.webhook_url:
            relay_logger.info("Discord webhook URL not configured — relay disabled.")
            return

        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "NEM-Relay/1.0"},
        )

        if not router.events["chat"].event_exists(RELAY_EVENT):
            router.events["chat"].add_event(RELAY_EVENT, self._on_chat, channel=[])

    async def teardown(self, router):
        if router.events["chat"].event_exists(RELAY_EVENT):
            router.events["chat"].remove_event(RELAY_EVENT)
        if self.session:
            await self.session.close()
            self.session = None

    async def _on_chat(self, router, _channels, userdata, message, channel):
        if not self.webhook_url or not self.session:
            return

        if not channel or channel.lower() != self.listen_channel.lower():
            return

        if userdata["name"] != self.listen_nick:
            return

        match = MODBOT_REGEX.search(message)
        if not match:
            return

        mc_version = match.group("list")
        mod_name = match.group("mod")
        version = match.group("version")
        phrasing = match.group("phrasing")
        is_dev = bool(match.group("dev"))

        nem_plugin = router.plugins["nem"].instance
        mod_data = await self._lookup_mod(nem_plugin, mc_version, mod_name)

        long_url = mod_data.get("longurl", "") if mod_data else ""

        embed = {
            "title": f"{mod_name} {phrasing} {version}",
            "url": long_url or None,
            "color": 0xA74F32 if is_dev else 0x77AF12,
            "fields": [
                {"name": "Minecraft", "value": mc_version, "inline": True},
                {"name": "Version", "value": version, "inline": True},
                {"name": "Version type", "value": "Dev" if is_dev else "Release", "inline": True},
            ],
        }

        if long_url:
            embed["fields"].append({"name": "URL", "value": long_url, "inline": True})

        payload = json.dumps({"embeds": [embed]})

        try:
            async with self.session.post(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status >= 400:
                    relay_logger.warning("Discord webhook returned %s", resp.status)
        except Exception:
            relay_logger.exception("Failed to send Discord webhook")

    async def _lookup_mod(self, nem_plugin, mc_version, mod_name):
        try:
            jsonres = await nem_plugin.fetch_json(
                f"https://bot.notenoughmods.com/{urlquote(mc_version)}.json",
                cache=True,
            )
            if jsonres:
                for mod in jsonres:
                    if mod["name"] == mod_name:
                        return mod
        except Exception:
            relay_logger.exception("Failed to look up mod %s in %s", mod_name, mc_version)
        return None
