from __future__ import annotations

from homeassistant import config_entries
from .const import DOMAIN


class DefconDashboardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for DEFCON Dashboard."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="DEFCON Dashboard",
            data={}
        )
