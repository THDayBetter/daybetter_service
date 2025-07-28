# config_flow.py
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_USER_CODE

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USER_CODE): str,
})


class DayBetterServicesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for DayBetter Services (User Code style)."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            user_code = user_input[CONF_USER_CODE]

            # 使用 aiohttp 调用 DayBetter 授权接口
            session = async_get_clientsession(self.hass)
            try:
                # 假设这是 DayBetter 获取 token 的接口
                resp = await session.post("https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/integrate", json={
                    "hassCode": user_code
                })

                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 1 and data.get("data") and data["data"].get("hassCodeToken"):
                        # 保存 token 等信息
                        token = data["data"]["hassCodeToken"]
                        new_data = user_input.copy()
                        new_data["hassCodeToken"] = token

                        _LOGGER.info("DayBetter auth OK: %s", data.get("data"))
                        # 保存 token 和 refresh_token 等信息
                        return self.async_create_entry(
                            title="DayBetter Account",
                            data=new_data
                        )
                    else:
                        _LOGGER.error("DayBetter auth failed: %s", data.get("message"))
                        errors["base"] = "auth_failed"
                else:
                    errors["base"] = "auth_failed"
            except Exception as ex:
                _LOGGER.exception("Connection error during DayBetter auth: %s", ex)
                errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )
