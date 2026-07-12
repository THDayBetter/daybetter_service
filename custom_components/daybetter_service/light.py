"""Support for DayBetter lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger("custom_components.daybetter_services")

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up DayBetter lights from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    devices = data["devices"]

    # Get light PIDs list
    pids_data = await api.fetch_pids()
    light_pids_str = pids_data.get("light", "")
    light_pids = set(light_pids_str.split(",")) if light_pids_str else set()

    # If a device is categorized as sensor, don't expose it as a light.
    # This avoids 温湿度计 误被创建成灯类实体的情况。
    sensor_pids_str = pids_data.get("sensor", "")
    sensor_pids = set(sensor_pids_str.split(",")) if sensor_pids_str else set()
    
    seen = set()
    lights = []
    for dev in devices:
        if dev.get("deviceMoldPid") not in light_pids:
            continue
        if dev.get("deviceMoldPid") in sensor_pids:
            continue
        device_name = dev.get("deviceName")
        if device_name in seen:
            continue
        seen.add(device_name)
        lights.append(DayBetterLight(api, dev))

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
        self._attr_brightness = 255
        self._attr_hs_color = (0.0, 0.0)
        self._attr_color_temp_kelvin = 3333  # Default color temperature (mireds unit)
        
        device_features = device.get("deviceFeatures", [])
        _LOGGER.debug("DayBetter Device: %s", device)
        
        # Home Assistant 2026.3.x 会对 supported_color_modes 做组合校验。
        # 为了确保实体能注册成功，这里采用“只声明一个最具体模式”的策略：
        # - 只要支持 HS，就只声明 HS（不再额外声明 BRIGHTNESS）
        # - 否则只声明 COLOR_TEMP
        # - 否则只声明 BRIGHTNESS
        supported_modes: set[ColorMode] = set()

        if 3 in device_features:
            supported_modes.add(ColorMode.HS)
        if 4 in device_features:
            supported_modes.add(ColorMode.COLOR_TEMP)
        if not supported_modes:
            supported_modes.add(ColorMode.BRIGHTNESS)
            
        self._attr_supported_color_modes = supported_modes
        
        if ColorMode.COLOR_TEMP in supported_modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ColorMode.HS in supported_modes:
            self._attr_color_mode = ColorMode.HS
        elif ColorMode.BRIGHTNESS in supported_modes:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.UNKNOWN
            
        if ColorMode.COLOR_TEMP in supported_modes:
            self._attr_min_color_temp_kelvin = 2000
            self._attr_max_color_temp_kelvin = 6666

        _LOGGER.debug(
            "Advertised supported_color_modes=%s color_mode=%s",
            self._attr_supported_color_modes,
            self._attr_color_mode,
        )   
        
        _LOGGER.debug(
            "Created %s (%s) supported=%s mode=%s",
            self.name,
            self.unique_id,
            self._attr_supported_color_modes,
            self._attr_color_mode,
        )
            
        self._device_features = device_features

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on
    
    @property
    def brightness(self) -> int | None:
        return self._attr_brightness

    @property
    def hs_color(self) -> tuple[float, float] | None:
        _LOGGER.debug("hs_color property called: %s", self._attr_hs_color)
        """Return the hue and saturation color value."""
        if self._attr_supported_color_modes and ColorMode.HS in self._attr_supported_color_modes:
            return self._attr_hs_color
        return None
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Get the brightness value set by the user
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        has_brightness = (
            self._attr_supported_color_modes
            and (
                ColorMode.BRIGHTNESS in self._attr_supported_color_modes
                or ColorMode.HS in self._attr_supported_color_modes
                or ColorMode.COLOR_TEMP in self._attr_supported_color_modes
            )
        )
        if brightness is not None and has_brightness:
            self._attr_brightness = brightness

        # Processing color
        hs_color = kwargs.get(ATTR_HS_COLOR)
        if hs_color is not None and self._attr_supported_color_modes and ColorMode.HS in self._attr_supported_color_modes:
            self._attr_hs_color = hs_color

        # Handle color temperature
        # Home Assistant uses color temperature in Kelvin.
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        if (
            color_temp_kelvin is not None
            and ColorMode.COLOR_TEMP in self._attr_supported_color_modes
        ):
            self._attr_color_temp_kelvin = color_temp_kelvin

        # Control equipment
        result = await self._api.control_device(
            self._device["deviceName"], 
            True, 
            brightness if has_brightness else None,
            hs_color if self._attr_supported_color_modes and ColorMode.HS in self._attr_supported_color_modes else None,
            (
                color_temp_kelvin
                if (
                    color_temp_kelvin is not None
                    and ColorMode.COLOR_TEMP in self._attr_supported_color_modes
                )
                else None
            )
        )
        
        # Update status based on control results
        if result.get("code") == 1:
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
        if result.get("code") == 1:
            self._is_on = False
            self.async_write_ha_state()
