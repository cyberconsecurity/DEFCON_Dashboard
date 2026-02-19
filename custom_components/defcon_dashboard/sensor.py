from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=5)

DEFCON_URL = "https://www.defconlevel.com/raised-levels"

COMMANDS = {
    "CYBERCOM": "https://www.defconlevel.com/cybercom",
    "SOCOM": "https://www.defconlevel.com/socom",
    "STRATCOM": "https://www.defconlevel.com/stratcom",
    "TRANSCOM": "https://www.defconlevel.com/transcom",
    "BIOCOM": "https://www.defconlevel.com/biocom",
    "DISASTERCOM": "https://www.defconlevel.com/disastercom",
    "FINCOM": "https://www.defconlevel.com/fincom",
    "SPACECOM": "https://www.defconlevel.com/alerts/space-command",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = DefconCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    entities: list[SensorEntity] = [
        DefconLevelSensor(coordinator),
    ]

    for name, url in COMMANDS.items():
        entities.append(DefconCommandSensor(coordinator, name, url))

    async_add_entities(entities)


# -------------------------------------------------------------------
# Coordinator
# -------------------------------------------------------------------

class DefconCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant) -> None:
        self._last_states: dict[str, str] = {}

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="DEFCON Dashboard Coordinator",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(DEFCON_URL, timeout=20) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status}")
                    html = await resp.text()

            now = datetime.now(timezone.utc)

            # DEFCON level
            match = re.search(r"DEFCON\s+([1-5])", html)
            defcon_level = int(match.group(1)) if match else None

            data = {
                "updated": now.isoformat(),
                "defcon_level": defcon_level,
                "commands": {},
            }

            for command, url in COMMANDS.items():
                # SPACECOM sometimes uses "Space Command"
                found = (
                    command in html
                    or (command == "SPACECOM" and "Space Command" in html)
                )

                state = "raised" if found else "normal"
                prev = self._last_states.get(command)
                changed = prev is not None and prev != state

                flash_until = (
                    now + timedelta(minutes=10) if changed else None
                )

                self._last_states[command] = state

                data["commands"][command] = {
                    "state": state,
                    "url": url,
                    "changed": changed,
                    "flash_until": flash_until.isoformat() if flash_until else None,
                }

            return data

        except Exception as err:
            raise UpdateFailed(str(err)) from err


# -------------------------------------------------------------------
# Sensors
# -------------------------------------------------------------------

class DefconLevelSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "DEFCON Threat Level"
    _attr_unique_id = "defcon_dashboard_defcon_level"
    _attr_icon = "mdi:alert-decagram"

    @property
    def native_value(self):
        return self.coordinator.data.get("defcon_level")

    @property
    def extra_state_attributes(self):
        return {
            "updated": self.coordinator.data.get("updated"),
            "source": "defconlevel.com",
        }


class DefconCommandSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:shield-alert"

    def __init__(self, coordinator, name: str, url: str):
        super().__init__(coordinator)
        self.command = name
        self.url = url
        self._attr_name = f"DEFCON {name}"
        self._attr_unique_id = f"defcon_dashboard_{name.lower()}"

    @property
    def native_value(self):
        return self.coordinator.data["commands"][self.command]["state"]

    @property
    def extra_state_attributes(self):
        cmd = self.coordinator.data["commands"][self.command]
        now = datetime.now(timezone.utc)

        flashing = False
        if cmd["flash_until"]:
            flashing = now < datetime.fromisoformat(cmd["flash_until"])

        return {
            "url": cmd["url"],
            "changed": cmd["changed"],
            "flash": flashing,
            "updated": self.coordinator.data.get("updated"),
        }
