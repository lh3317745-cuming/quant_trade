"""OKX 客户端创建能力。

集中封装 OKX 客户端的创建逻辑，并组合交易能力：

- ``http``：nautilus_trader 的 :class:`OKXHttpClient`（下单 / 撤单 / 账户查询）
- ``ccxt``：ccxt 的 OKX 异步客户端（补充字段 / 策略持仓查询）
- ``account``：:class:`client.account.OKXAccount` 账户查询封装（余额 / 持仓）
- ``trader``：:class:`instrument.order.OKXTrader` 交易器（下单 / 撤单 / 查询挂单）

初始化时可传入 ``trader`` 参数；不传则自动用 ``http`` 创建并挂到 ``self.trader``。

    client = OKXClient()
    await client.trader.place_spot_market_order("BTC-USDT", "BUY", "0.001")

凭据来源：优先使用显式传参，否则从 ``quant_learn/.env`` 读取
``OKX_API_KEY`` / ``OKX_API_SECRET`` / ``OKX_API_PASSPHRASE``
（依赖最外侧 ``main`` 启动时由 ``@auto_load_env`` 自动加载）。
"""

from __future__ import annotations

import os
from typing import Any

import ccxt.async_support as ccxt
from nautilus_trader.adapters.okx import OKXHttpClient

# 默认代理（本机 Clash 等代理地址）
DEFAULT_PROXY_URL = "http://127.0.0.1:7897"


def get_okx_credentials(
    api_key: str | None = None,
    api_secret: str | None = None,
    api_passphrase: str | None = None,
) -> tuple[str, str, str]:
    """返回 ``(api_key, api_secret, api_passphrase)``。

    优先使用显式传参，否则从 ``os.environ`` 读取（依赖最外侧 ``main`` 启动时
    由 ``@auto_load_env`` 自动加载的 .env，此处不再重复加载）。
    """
    key = api_key or os.environ.get("OKX_API_KEY")
    secret = api_secret or os.environ.get("OKX_API_SECRET")
    passphrase = api_passphrase or os.environ.get("OKX_API_PASSPHRASE")
    if not (key and secret and passphrase):
        raise ValueError(
            "缺少 OKX 凭据：请在 quant_learn/.env 中配置 "
            "OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE，或通过参数传入"
        )
    return key, secret, passphrase


class OKXClient:
    """OKX 客户端封装：持有 http / ccxt 客户端，并可组合一个交易器 ``trader``。"""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        api_passphrase: str | None = None,
        proxy_url: str | None = DEFAULT_PROXY_URL,
        trader: Any = None,
    ) -> None:
        key, secret, passphrase = get_okx_credentials(api_key, api_secret, api_passphrase)
        self._key = key
        self._secret = secret
        self._passphrase = passphrase
        self._proxy_url = proxy_url

        # nautilus_trader 客户端（下单 / 撤单 / 账户查询）
        self.http = OKXHttpClient(
            api_key=key,
            api_secret=secret,
            api_passphrase=passphrase,
            proxy_url=proxy_url,
        )

        # ccxt 异步客户端（补充字段 / 策略持仓查询）
        self.ccxt = ccxt.okx({
            "apiKey": key,
            "secret": secret,
            "password": passphrase,
            "aiohttp_proxy": proxy_url,
        })

        # 账户查询封装（余额 / 现货持仓 / 策略持仓 / 交易头寸）
        from client.account import OKXAccount  # noqa: PLC0415

        self.account = OKXAccount(self.http, self.ccxt)

        # 交易器：可外部传入，也可自动用 self.http + self.ccxt 创建（延迟导入避免循环依赖）
        if trader is None:
            from instrument.order import OKXTrader  # noqa: PLC0415

            trader = OKXTrader(self.http, self.ccxt)
        self.trader = trader

    async def close(self) -> None:
        """关闭 ccxt 会话（如需复用请先调用）。"""
        if hasattr(self.ccxt, "close"):
            await self.ccxt.close()
