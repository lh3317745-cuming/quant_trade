"""OKX execution client（执行下单 / 撤单 / 账户查询）。

标准 nautilus_trader 架构下，execution client 负责把策略提交的订单路由到
OKX 交易所。它由 ``OKXExecutionClientFactory`` 创建，通过
``LiveNode.builder().add_exec_client(name, factory, config)`` 注册。

本模块提供两个轻量助手：

- :func:`create_exec_client_factory`：返回工厂实例。
- :func:`build_exec_client_config`：构建带凭据的 ``OKXExecClientConfig``。

使用方式见 :func:`client.node.build_okx_node`，它把 execution client 与
data client、策略一起用 builder 模式组装。
"""

from __future__ import annotations

from nautilus_trader.adapters.okx import (
    OKXEnvironment,
    OKXExecClientConfig,
    OKXExecutionClientFactory,
    OKXInstrumentType,
    OKXMarginMode,
    OKXRegion,
)
from nautilus_trader.model import AccountId, TraderId

from client.okx import DEFAULT_PROXY_URL, get_okx_credentials


def create_exec_client_factory() -> OKXExecutionClientFactory:
    """返回 execution client 工厂实例。

    工厂本身不能直接在 Python 侧 ``create``，只能通过
    ``LiveNodeBuilder.add_exec_client`` 注册后由引擎创建。
    """
    return OKXExecutionClientFactory()


def build_exec_client_config(
    trader_id: str,
    *,
    account_id: str = "OKX-001",
    instrument_types: list[OKXInstrumentType] | None = None,
    environment: OKXEnvironment = OKXEnvironment.LIVE,
    region: OKXRegion = OKXRegion.GLOBAL,
    margin_mode: OKXMarginMode | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    api_passphrase: str | None = None,
    proxy_url: str | None = DEFAULT_PROXY_URL,
) -> OKXExecClientConfig:
    """构建 execution client 配置（注入凭据）。

    参数
    ----
    trader_id :
        交易者 ID（必填），如 ``"T-001"``。
    account_id :
        OKX 账户 ID，默认 ``"OKX-001"``。
    instrument_types :
        需要加载的交易品种类型列表，如 ``[OKXInstrumentType.SWAP]``。
    environment :
        ``OKXEnvironment.LIVE`` / ``DEMO``，默认 LIVE。
    region :
        ``OKXRegion.GLOBAL`` / ``EEA`` / ``US``，默认 GLOBAL。
    margin_mode :
        保证金模式 ``OKXMarginMode.ISOLATED``（逐仓）/ ``CROSS``（全仓）。
        不传则由 OKX 账户默认决定。
    api_key / api_secret / api_passphrase :
        显式传入，否则从 ``quant_learn/.env`` 读取。
    proxy_url :
        代理地址，默认 ``http://127.0.0.1:7897``。
    """
    key, secret, passphrase = get_okx_credentials(api_key, api_secret, api_passphrase)
    return OKXExecClientConfig(
        trader_id=TraderId.from_str(trader_id),
        account_id=AccountId.from_str(account_id),
        instrument_types=instrument_types,
        environment=environment,
        region=region,
        api_key=key,
        api_secret=secret,
        api_passphrase=passphrase,
        proxy_url=proxy_url,
        margin_mode=margin_mode,
    )


__all__ = ["create_exec_client_factory", "build_exec_client_config"]
