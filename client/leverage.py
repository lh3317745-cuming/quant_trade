"""OKX 杠杆倍数设置（标准架构下全项目唯一保留 ccxt 的地方）。

背景：nautilus_trader 的 OKX execution client **没有杠杆倍数的标准配置**——
``OKXExecClientConfig.margin_mode`` 只能设逐仓/全仓（``ISOLATED`` / ``CROSS``），
不能设倍数（``lever`` 字段在模型里是只读的）。杠杆倍数只能通过 OKX 的
``/account/set-leverage`` 接口设置（账户级，设置一次后该品种该方向的下单即沿用），
而 nautilus OKX adapter 未暴露该接口，故此处保留 ccxt。

用法（在 ``node.run()`` / ``node.run_async()`` 之前调用一次即可）：

    from client import set_okx_leverage

    await set_okx_leverage("BTC-USDT", 10, td_mode="ISOLATED", position_side="long")

其余下单流程全走 ``strategy.order_factory``，与本模块无关。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ccxt.async_support as ccxt

from client.okx import DEFAULT_PROXY_URL, get_okx_credentials


@dataclass
class LeverageConfig:
    """杠杆设置配置（作为 ``build_okx_node`` 的可选启动钩子）。"""

    symbol: str          # 交易对，如 "BTC-USDT"
    leverage: int | str  # 杠杆倍数，如 10
    td_mode: str = "ISOLATED"          # "ISOLATED"（逐仓）/ "CROSS"（全仓）
    position_side: str | None = None   # "LONG"/"SHORT"，逐仓+双向持仓时必填


def _swap_inst_id(symbol: str) -> str:
    """把交易对转成 OKX 永续 ``instId``，如 ``BTC-USDT`` -> ``BTC-USDT-SWAP``。"""
    s = symbol.replace("/", "-")
    if s.upper().endswith(".OKX"):
        s = s[:-4]
    if not s.upper().endswith("-SWAP"):
        s = f"{s}-SWAP"
    return s


def build_leverage_params(
    symbol: str,
    leverage: int | str,
    *,
    td_mode: str = "ISOLATED",
    position_side: str | None = None,
) -> dict[str, Any]:
    """构造 ``privatePostAccountSetLeverage`` 请求参数（纯函数，便于测试）。

    - ``td_mode``：``"ISOLATED"``（逐仓）/ ``"CROSS"``（全仓）。
    - ``position_side``：``"LONG"`` / ``"SHORT"``。逐仓且双向持仓时必填。
    """
    inst_id = _swap_inst_id(symbol)
    mgn_mode = "isolated" if td_mode.upper() == "ISOLATED" else "cross"
    params: dict[str, Any] = {
        "instId": inst_id,
        "lever": str(leverage),
        "mgnMode": mgn_mode,
    }
    if mgn_mode == "isolated" and position_side:
        params["posSide"] = position_side.lower()
    return params


async def set_okx_leverage(
    symbol: str,
    leverage: int | str,
    *,
    td_mode: str = "ISOLATED",
    position_side: str | None = None,
    ccxt_client: Any = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    api_passphrase: str | None = None,
    proxy_url: str | None = DEFAULT_PROXY_URL,
) -> Any:
    """设置 OKX 合约/永续杠杆倍数，返回 OKX 原始响应。

    优先复用传入的 ``ccxt_client``；未传则用凭据临时创建并在用完后关闭。
    """
    own = ccxt_client is None
    if own:
        key, secret, passphrase = get_okx_credentials(api_key, api_secret, api_passphrase)
        ccxt_client = ccxt.okx({
            "apiKey": key,
            "secret": secret,
            "password": passphrase,
            "aiohttp_proxy": proxy_url,
        })
    try:
        params = build_leverage_params(
            symbol, leverage, td_mode=td_mode, position_side=position_side
        )
        return await ccxt_client.privatePostAccountSetLeverage(params)
    finally:
        if own:
            await ccxt_client.close()


__all__ = ["LeverageConfig", "build_leverage_params", "set_okx_leverage"]
