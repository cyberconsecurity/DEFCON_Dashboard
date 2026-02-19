from __future__ import annotations

import datetime
import logging
import re
import requests

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = datetime.timedelta(minutes=5)

COMMANDS = {
    "CYBERCOM": "https://www.defconlevel.com/alerts/cyber-command",
    "SOCOM": "https://www.defconlevel.com/alerts/special-operations-command",
    "STRATCOM": "https://www.defconlevel.com/alerts/strategic-command",
    "TRANSCOM": "https://www.defconlevel.com/alerts/transportation-command",
    "BIOCOM": "https://www.defconlevel.com/alerts/biological-command",
    "DISASTERCOM": "https://www.defconlevel.com/alerts/disaster-command",
    "FINCOM": "https://www.defconlevel.com/alerts/financial-command",
    "SPACECOM": "https://www.defconlevel.com/alerts/space-command",
}

async def async_setup_entry(hass, entry, async_add_entities):
    sensors = []
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="DEFCON Command Coordinator",
        update_interval=SCAN_INTERVAL,
        update_method=_async_update_data,
    )

    await coordinator.async_config_entry_first_refresh()

    for name, url in COMMANDS.items():
        sensors.append(DefconCommandSensor(coordinator, name, url))

    async_add_entities(sensors)


async def _async_update_data():
    data = {}
    for name, url in COMMANDS.items():
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            # Find "Level X" (e.g. Level 2)
            level_match = re.search(r"Level\s+(\d)", resp.text, re.IGNORECASE)
            level = int(level_match.group(1)) if level_match else None

            state = "raised" if level and level <= 3 else "normal"

            data[name] = {
                "state": state,
                "level": level,
                "url": url,
                "last_updated": datetime.datetime.utcnow().isoformat(),
            }

        except Exception as err:
            _LOGGER.error("Error fetching %s: %s", name, err)
            data[name] = {
                "state": "unknown",
                "level": None,
                "url": url,
            }

    return data


class DefconCommandSensor(SensorEntity):
    def __init__(self, coordinator, name, url):
        self.coordinator = coordinator
        self._name = name
        self._url = url

        self._attr_name = f"DEFCON {name.upper()}"
        self._attr_unique_id = f"defcon_{name}"
        self._attr_icon = "mdi:shield-alert"

    @property
    def native_value(self):
        return self.coordinator.data[self._name]["state"]

    @property
    def extra_state_attributes(self):
        return {
            "level": self.coordinator.data[self._name]["level"],
            "url": self._url,
            "last_updated": self.coordinator.data[self._name].get("last_updated"),
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()
