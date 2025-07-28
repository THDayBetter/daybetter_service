# token_manager.py
import logging
import os
import json
from datetime import datetime
from homeassistant.helpers.storage import STORAGE_DIR

_LOGGER = logging.getLogger(__name__)

TOKEN_STORAGE_PATH = "daybetter_token.json"


class TokenManager:
    def __init__(self, hass, user_code):
        self.hass = hass
        self.user_code = user_code
        self.token_path = os.path.join(hass.config.path(STORAGE_DIR), TOKEN_STORAGE_PATH)

    async def load_token(self):
        """从本地加载已保存的 token"""
        if not os.path.exists(self.token_path):
            return None

        try:
            with open(self.token_path, "r") as f:
                return json.load(f)
        except Exception as ex:
            _LOGGER.warning("Failed to load token: %s", ex)
            return None

    async def save_token(self, token_data):
        """将 token 保存到本地"""
        try:
            with open(self.token_path, "w") as f:
                json.dump(token_data, f)
        except Exception as ex:
            _LOGGER.error("Failed to save token: %s", ex)

    async def get_access_token(self):
        """获取有效的 access_token"""
        token_data = await self.load_token()
        if token_data:
            return token_data["access_token"]

        # 使用 user_code 获取新 token
        url = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0/hass/integrate"  # 修改为新域名
        payload = {
            "hassCode": self.user_code
        }
        session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        resp = await session.post(url, json=payload)
        if resp.status == 200:
            data = await resp.json()
            await self.save_token(data)
            return data.get("access_token")

        return None

    def is_token_valid(self, token_data):
        """检查 token 是否在有效期内"""
        expires_at = token_data.get("expires_at")
        if not expires_at:
            return False
        return datetime.fromtimestamp(expires_at) > datetime.now()
