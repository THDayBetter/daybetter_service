"""Support for DayBetter lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up DayBetter lights from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    devices = data["devices"]

    light_pids = {
            "P01E", "P021", "P024", "P025", "P027", "P02B", "P032", "P035", "P037", "P038",
            "P039", "P03B", "P03D", "P03E", "P03F", "P040", "P041", "P042", "P043", "P045",
            "P046", "P048", "P049", "P04E", "P04F", "P050", "P051", "P054", "P055", "P056",
            "P058", "P059", "P05A", "P05B", "P05C", "P05D", "P05E", "P064", "P067", "P069",
            "P06F", "P072", "P073", "P074", "P076", "P078", "P079", "P07A", "P07B", "P07C",
            "P07E", "P086"
        }
    
    lights = [
        DayBetterLight(api, dev) 
        for dev in devices 
        if dev.get("deviceMoldPid") in light_pids
    ]    
    async_add_entities(lights)

class DayBetterLight(LightEntity):
    """Representation of a DayBetter light."""

    def __init__(self, api, device: dict[str, Any]) -> None:
        """Initialize the light."""
        self._api = api
        self._device = device
        self._attr_name = device.get("deviceGroupName", "DayBetter Light")
        self._attr_unique_id = str(device.get("deviceName", "unknown"))
        self._is_on = device.get("deviceState", 0) == 1
        self._brightness = 255  # Default maximum brightness
        self._hs_color = (0.0, 0.0)  # The default is white (hue, saturation)
        self._color_temp = 300  # Default color temperature (mireds unit)
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS, ColorMode.HS, ColorMode.COLOR_TEMP}
        self._min_mireds = 150
        self._max_mireds = 500

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on
    
    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        return self._brightness

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value."""
        return self._hs_color
    
    @property
    def color_temp(self) -> int | None:
        """Return the color temperature."""
        return self._color_temp
    
    @property
    def min_mireds(self) -> int:
        """Return the coldest color temp that this light supports."""
        return self._min_mireds
    
    @property
    def max_mireds(self) -> int:
        """Return the warmest color temp that this light supports."""
        return self._max_mireds

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Get the brightness value set by the user
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            self._brightness = brightness

        # Processing color
        hs_color = kwargs.get(ATTR_HS_COLOR)
        if hs_color is not None:
            self._hs_color = hs_color

        # Handle color temperature
        color_temp = kwargs.get(ATTR_COLOR_TEMP)
        if color_temp is not None:
            self._color_temp = color_temp

        # Control equipment
        result = await self._api.control_device(
            self._device["deviceName"], 
            True, 
            brightness,
            hs_color,
            color_temp
        )
        
        # Update status based on control results
        if result.get("code", 1):
            self._is_on = True
            if brightness is not None:
                self._brightness = brightness
            if hs_color is not None:
                self._hs_color = hs_color
            if color_temp is not None:
                self._color_temp = color_temp
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Control equipment
        result = await self._api.control_device(
            self._device["deviceName"], 
            False, 
            None,
            None,
            None
        )
        
        # Update status based on control results
        if result.get("code", 1):
            self._is_on = False
            self.async_write_ha_state()