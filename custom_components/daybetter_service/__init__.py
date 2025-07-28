from .const import DOMAIN, CONF_TOKEN
from .daybetter_api import DayBetterApi

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    """集成入口，初始化 token 和设备"""
    token = entry.data.get(CONF_TOKEN)
    api = DayBetterApi(hass, token)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["api"] = api

    # 获取设备列表并保存
    devices = await api.fetch_devices()
    hass.data[DOMAIN]["devices"] = devices

    # 如果有 light.py，可以在此 forward entry
    # hass.async_create_task(
        # hass.config_entries.async_forward_entry_setup(entry, "light")
    await hass.config_entries.async_forward_entry_setups(entry, ["light"])
    # )
    return True

async def async_unload_entry(hass, entry):
    return True
