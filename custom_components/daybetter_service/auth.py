# auth.py

DAYBETTER_API = "https://cloud.v2.dbiot.link/daybetter/hass/api/v1.0"


async def login(session, username, password):
    """尝试登录 DayBetter 并返回 token 或用户信息"""
    async with session.post(f"{DAYBETTER_API}/login", json={
        "username": username,
        "password": password
    }) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            raise Exception("Login failed")
