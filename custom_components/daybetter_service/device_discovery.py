import logging
import json
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

async def fetch_devices(hass, access_token):
    """调用 API 获取设备列表"""
    url = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/devices"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    payload = {}

    session = async_get_clientsession(hass)
    resp = await session.post(url, json=payload, headers=headers)

    if resp.status == 200:
        data = await resp.json()
        return data.get("devices", [])
    else:
        _LOGGER.error("Failed to fetch devices: %s", await resp.text())
        return []