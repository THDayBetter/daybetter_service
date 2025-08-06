"""DayBetter API client."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.color import color_hs_to_RGB

_LOGGER = logging.getLogger(__name__)

class DayBetterApi:
    """DayBetter API client."""

    def __init__(self, hass, token: str) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.token = token

    async def fetch_devices(self) -> list[dict[str, Any]]:
        """Get list of devices."""
        session = async_get_clientsession(self.hass)
        url = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/devices"
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.post(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
            else:
                _LOGGER.error("Failed to fetch devices: %s", await resp.text())
                return []

    async def control_device(
        self, 
        device_name: str, 
        action: bool, 
        brightness: int | None, 
        hs_color: tuple[float, float] | None, 
        color_temp: int | None
    ) -> dict[str, Any]:
        """Control a device."""
        session = async_get_clientsession(self.hass)
        url = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/control"
        headers = {"Authorization": f"Bearer {self.token}"}

        # Priority: color temperature > color > brightness > switch
        if color_temp is not None:
            # Convert mireds to Kelvin
            kelvin = int(1000000 / color_temp)
            payload = {
                "deviceName": device_name, 
                "type": 4,  # Type 4 is color temperature control
                "kelvin": kelvin
            }
        elif hs_color is not None:
            r, g, b = color_hs_to_RGB(*hs_color)
            payload = {
                "deviceName": device_name, 
                "type": 3, 
                "red": r,
                "green": g,
                "blue": b
            }
        elif brightness is not None:
            payload = {
                "deviceName": device_name, 
                "type": 2, 
                "brightness": brightness
            }
        else:
            # Type 1 control switch is used by default
            payload = {"deviceName": device_name, "type": 1, "on": action}
            
        async with session.post(url, headers=headers, json=payload) as resp:
            return await resp.json()