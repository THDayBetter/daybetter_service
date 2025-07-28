import logging
from homeassistant.util.color import color_hs_to_RGB
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

class DayBetterApi:
    def __init__(self, hass, token):
        self.hass = hass
        self.token = token

    async def fetch_devices(self):
        """获取设备列表"""
        # session = self.hass.helpers.aiohttp_client.async_get_clientsession()
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

    async def control_device(self, deviceName, action, brightness, hs_color, color_temp):
        """控制设备（示例）"""
        # session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        session = async_get_clientsession(self.hass)
        url = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/control"
        headers = {"Authorization": f"Bearer {self.token}"}

        # 优先级：色温 > 颜色 > 亮度 > 开关
        if color_temp is not None:
            # 将 mireds 转换为开尔文
            kelvin = int(1000000 / color_temp)
            payload = {
                "deviceName": deviceName, 
                "type": 4,  # 假设type 4为色温控制
                "kelvin": kelvin
            }
        elif hs_color is not None:
            r, g, b = color_hs_to_RGB(*hs_color)
            payload = {
                "deviceName": deviceName, 
                "type": 3, 
                "red": r,
                "green": g,
                "blue": b
            }
        elif brightness is not None:
            payload = {
                "deviceName": deviceName, 
                "type": 2, 
                "brightness": brightness
            }
        else:
            # 默认使用 type 1 控制开关
            payload = {"deviceName": deviceName, "type": 1, "on": action}
            
        async with session.post(url, headers=headers, json=payload) as resp:
            return await resp.json()
        
    async def fetch_device_status(self, deviceName):
        """获取单个设备状态"""
        session = async_get_clientsession(self.hass)
        url = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/device"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"deviceName": deviceName}
        
        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
                else:
                    _LOGGER.warning("Failed to fetch device status: %s", await resp.text())
                    return {}
        except Exception as e:
            _LOGGER.error("Error fetching device status: %s", e)
            return {}