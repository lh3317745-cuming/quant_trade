"""client 包：集中封装交易所客户端创建能力。

分模块职责：

- :mod:`client.okx`        —— 轻量 OKX 客户端（http + ccxt + OKXTrader），资产/持仓查询。
- :mod:`client.execution`  —— execution client（执行下单/撤单），标准 Factory + Config。
- :mod:`client.data`       —— data client（订阅实时行情），标准 Factory + Config。
- :mod:`client.node`       —— :func:`build_okx_node` 用 builder 模式编排三者（async，含可选杠杆启动钩子）。
- :mod:`client.leverage`   —— :func:`set_okx_leverage` / :class:`LeverageConfig` 设置杠杆倍数（唯一保留 ccxt 之处）。
- :mod:`client.account`    —— :class:`OKXAccount` 查询余额 / 现货持仓 / 策略持仓 / 交易头寸。
"""

from client.account import DEFAULT_POSITION_TYPES, OKXAccount, parse_amount
from client.data import build_data_client_config, create_data_client_factory
from client.execution import build_exec_client_config, create_exec_client_factory
from client.leverage import LeverageConfig, build_leverage_params, set_okx_leverage
from client.node import DEFAULT_CLIENT_NAME, build_okx_node
from client.okx import (
    DEFAULT_PROXY_URL,
    OKXClient,
    get_okx_credentials,
)

__all__ = [
    "DEFAULT_CLIENT_NAME",
    "DEFAULT_POSITION_TYPES",
    "DEFAULT_PROXY_URL",
    "LeverageConfig",
    "OKXAccount",
    "OKXClient",
    "build_data_client_config",
    "build_exec_client_config",
    "build_leverage_params",
    "build_okx_node",
    "create_data_client_factory",
    "create_exec_client_factory",
    "get_okx_credentials",
    "parse_amount",
    "set_okx_leverage",
]
