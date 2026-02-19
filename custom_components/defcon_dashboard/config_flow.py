from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class DefconDashboardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Enforce single instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="DEFCON Dashboard",
            data={}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return None
