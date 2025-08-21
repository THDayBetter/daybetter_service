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
            "P058", "P059", "P05A", "P05B", "P05C", "P05D", "P05E", "P05F", "P064", "P067", 
            "P069", "P06F", "P072", "P073", "P074", "P076", "P078", "P079", "P07A", "P07B", 
            "P07C", "P07E", "P086"
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
        
        device_features = device.get("deviceFeatures", [])
        
        supported_modes = set()
        
        if 2 in device_features:
            supported_modes.add(ColorMode.BRIGHTNESS)
            
        if 3 in device_features:
            supported_modes.add(ColorMode.HS)
            
        if 4 in device_features:
            supported_modes.add(ColorMode.COLOR_TEMP)
            
        if not supported_modes:
            supported_modes.add(ColorMode.BRIGHTNESS)
            
        self._attr_supported_color_modes = supported_modes
        
        if ColorMode.HS in supported_modes:
            self._attr_color_mode = ColorMode.HS
        elif ColorMode.COLOR_TEMP in supported_modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in supported_modes:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.UNKNOWN
            
        if 4 in device_features:
            self._min_mireds = 150
            self._max_mireds = 500
            
        self._device_features = device_features

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on
    
    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if self._attr_supported_color_modes and ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            return self._brightness
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value."""
        if self._attr_supported_color_modes and ColorMode.HS in self._attr_supported_color_modes:
            return self._hs_color
        return None
    
    @property
    def color_temp(self) -> int | None:
        """Return the color temperature."""
        if self._attr_supported_color_modes and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return self._color_temp
        return None
    
    @property
    def min_mireds(self) -> int:
        """Return the coldest color temp that this light supports."""
        if self._attr_supported_color_modes and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return getattr(self, '_min_mireds', 153)
        return 153
    
    @property
    def max_mireds(self) -> int:
        """Return the warmest color temp that this light supports."""
        if self._attr_supported_color_modes and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return getattr(self, '_max_mireds', 500)
        return 500

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Get the brightness value set by the user
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None and self._attr_supported_color_modes and ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            self._brightness = brightness

        # Processing color
        hs_color = kwargs.get(ATTR_HS_COLOR)
        if hs_color is not None and self._attr_supported_color_modes and ColorMode.HS in self._attr_supported_color_modes:
            self._hs_color = hs_color

        # Handle color temperature
        color_temp = kwargs.get(ATTR_COLOR_TEMP)
        if color_temp is not None and self._attr_supported_color_modes and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            self._color_temp = color_temp

        # Control equipment
        result = await self._api.control_device(
            self._device["deviceName"], 
            True, 
            brightness if self._attr_supported_color_modes and ColorMode.BRIGHTNESS in self._attr_supported_color_modes else None,
            hs_color if self._attr_supported_color_modes and ColorMode.HS in self._attr_supported_color_modes else None,
            color_temp if self._attr_supported_color_modes and ColorMode.COLOR_TEMP in self._attr_supported_color_modes else None
        )
        
        # Update status based on control results
        if result.get("code", 1):
            self._is_on = True
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