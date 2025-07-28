import logging
from homeassistant.components.light import LightEntity
from .const import DOMAIN
from homeassistant.components.light import (
    LightEntity, 
    SUPPORT_BRIGHTNESS, 
    SUPPORT_COLOR, 
    SUPPORT_COLOR_TEMP
)
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util.color import color_RGB_to_hs

_LOGGER = logging.getLogger(__name__)

# 设置轮询间隔
# UPDATE_INTERVAL = timedelta(seconds=30)

...

@property
def supported_features(self):
    return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_COLOR_TEMP

async def async_setup_entry(hass, entry, async_add_entities):
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    # 这里只添加类型为灯的设备（如deviceType==16为灯带，14~28、46）
    lights = [DayBetterLight(api, dev) for dev in devices if dev.get("deviceType") == 16 or dev.get("deviceType") in range(14, 18) or dev.get("deviceType") == 46]
    async_add_entities(lights)

class DayBetterLight(LightEntity):
    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._attr_name = device.get("deviceGroupName", "DayBetter Light")
        self._attr_unique_id = str(device.get("deviceName", "unknown"))
        self._is_on = device.get("deviceState", 0) == 1
        self._brightness = 255  # 默认最大亮度
        self._hs_color = (0.0, 0.0)  # 默认为白色（色相、饱和度）
        self._color_temp = 300  # 默认色温（mireds单位）

        # 按需轮询相关属性
        self._last_update = None
        self._last_activity = datetime.utcnow()
        self._update_interval = timedelta(seconds=30)  # 普通更新间隔
        self._fast_update_interval = timedelta(seconds=5)  # 快速更新间隔
        self._fast_update_until = None  # 快速更新结束时间
        self._idle_timeout = timedelta(minutes=5)  # 空闲超时时间

    @property
    def is_on(self):
        return self._is_on
    
    @property
    def brightness(self):
        """返回当前亮度 (0-255)"""
        return self._brightness

    @property
    def hs_color(self):
        return self._hs_color
    
    @property
    def color_temp(self):
        """返回当前色温 (mireds单位)"""
        return self._color_temp
    
    @property
    def min_mireds(self):
        """最小色温 (最冷的白光)"""
        return 150
    
    @property
    def max_mireds(self):
        """最大色温 (最暖的白光)"""
        return 500
    
    @property
    def supported_features(self):
        """支持亮度调节"""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_COLOR_TEMP


    @property
    def should_poll(self):
        """决定是否需要轮询"""
        now = datetime.utcnow()
        
        # 检查是否空闲超时
        if now - self._last_activity > self._idle_timeout:
            return False  # 空闲超时，停止轮询

        # 如果正在进行快速更新，或者距离上次更新已经超过普通间隔，则需要轮询
        if self._fast_update_until and datetime.utcnow() < self._fast_update_until:
            return True
            
        if self._last_update is None:
            return True
            
        return now - self._last_update > self._update_interval

    def _safe_int(self, value, default=0):
        """安全地将值转换为整数"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_hex_int(self, value, default=0):
        """安全地将十六进制字符串转换为整数"""
        if value is None:
            return default
        try:
            # 处理可能带 "0x" 前缀或不带前缀的十六进制字符串
            if isinstance(value, str):
                value = value.strip()
                if value.startswith("0x") or value.startswith("0X"):
                    return int(value, 16)
                else:
                    return int(value, 16)
            else:
                return int(value)
        except (ValueError, TypeError):
            return default

    def _update_activity(self):
        """更新活动时间"""
        self._last_activity = datetime.utcnow()
        
        # 重置快速更新时间（如果已过期）
        if self._fast_update_until and datetime.utcnow() > self._fast_update_until:
            self._fast_update_until = None
    async def async_update(self):
        """更新设备状态"""
        try:
            status = await self._api.fetch_device_status(self._device["deviceName"])
            if status:
                # 根据 API 返回更新状态
                on_value = status.get("on")
                if on_value is not None:
                    if isinstance(on_value, str):
                        self._is_on = on_value.lower() in ('true', '1', 'on')
                    else:
                        self._is_on = bool(on_value)
                
                brightness_value = status.get("brightness")
                if brightness_value is not None:
                    self._brightness = self._safe_int(brightness_value, self._brightness)
                
                # 更新颜色 - 从 RGB 转换为 HS
                r = self._safe_hex_int(status.get("r"))
                g = self._safe_hex_int(status.get("g"))
                b = self._safe_hex_int(status.get("b"))
                
                if r is not None and g is not None and b is not None:
                    # 确保 RGB 值在有效范围内
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b = max(0, min(255, b))
                    # 将 RGB 转换为 HS 格式
                    self._hs_color = color_RGB_to_hs(r, g, b)
                    
                # 更新色温（如果有的话）
                kelvin_value = status.get("kelvin")
                if kelvin_value is not None:
                    kelvin = self._safe_int(kelvin_value)
                    if kelvin > 0:
                        # 将开尔文转换为 mireds，避免除零错误
                        try:
                            self._color_temp = int(1000000 / kelvin)
                        except ZeroDivisionError:
                            pass  # 保持原值

                # 更新最后更新时间
                self._last_update = datetime.utcnow()

        except Exception as e:
            _LOGGER.error("Error updating device status: %s", e)

    async def async_turn_on(self, **kwargs):
        # 获取用户设置的亮度值
        brightness = kwargs.get("brightness")
        if brightness is not None:
            self._brightness = brightness

        # 处理颜色
        hs_color = kwargs.get("hs_color")
        if hs_color is not None:
            self._hs_color = hs_color

        # 处理色温
        color_temp = kwargs.get("color_temp")
        if color_temp is not None:
            self._color_temp = color_temp

        await self._api.control_device(
            self._device["deviceName"], 
            True, 
            brightness,
            hs_color,
            color_temp  # 传递色温参数
        )
        
        self._is_on = True
        
        # 触发快速更新模式（持续30秒）
        self._fast_update_until = datetime.utcnow() + timedelta(seconds=30)
        
        # 立即更新状态
        await self.async_update()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._api.control_device(
            self._device["deviceName"], 
            False, 
            None,
            None,
            None  # 关闭时不需要传递色温等参数
            )
        self._is_on = False
        
        # 触发快速更新模式（持续30秒）
        self._fast_update_until = datetime.utcnow() + timedelta(seconds=30)
        
        # 立即更新状态
        await self.async_update()
        self.async_write_ha_state()

    async def async_update_ha_state(self, force_refresh=False):
        """更新 Home Assistant 状态时更新活动时间"""
        self._update_activity()
        await super().async_update_ha_state(force_refresh)