"""OKX data client（订阅实时行情）。

标准 nautilus_trader 架构下，data client 负责订阅 OKX 实时行情
（trades / quotes / bars / book / funding 等），并把数据推送到消息总线，
供已订阅的 :class:`~nautilus_trader.trading.Strategy` 通过
``on_bar`` / ``on_quote`` / ``on_trade`` 等回调消费。

它由 ``OKXDataClientFactory`` 创建，通过
``LiveNode.builder().add_data_client(name, factory, config)`` 注册。

本模块提供两个轻量助手：

- :func:`create_data_client_factory`：返回工厂实例。
- :func:`build_data_client_config`：构建带凭据的 ``OKXDataClientConfig``。
"""

from __future__ import annotations

from nautilus_trader.adapters.okx import (
    OKXDataClientConfig,
    OKXDataClientFactory,
    OKXEnvironment,
    OKXInstrumentType,
    OKXRegion,
)

from client.okx import DEFAULT_PROXY_URL, get_okx_credentials


def create_data_client_factory() -> OKXDataClientFactory:
    """返回 data client 工厂实例。

    工厂本身不能直接在 Python 侧 ``create``，只能通过
    ``LiveNodeBuilder.add_data_client`` 注册后由引擎创建。
    """
    return OKXDataClientFactory()


def build_data_client_config(
    *,
    instrument_types: list[OKXInstrumentType] | None = None,
    environment: OKXEnvironment = OKXEnvironment.LIVE,
    region: OKXRegion = OKXRegion.GLOBAL,
    api_key: str | None = None,
    api_secret: str | None = None,
    api_passphrase: str | None = None,
    proxy_url: str | None = DEFAULT_PROXY_URL,
    load_spreads: bool = False,
) -> OKXDataClientConfig:
    """构建 data client 配置（注入凭据）。

    参数
    ----
    instrument_types :
        需要加载的交易品种类型列表，如 ``[OKXInstrumentType.SWAP]``。
    environment :
        ``OKXEnvironment.LIVE`` / ``DEMO``，默认 LIVE。
    region :
        ``OKXRegion.GLOBAL`` / ``EEA`` / ``US``，默认 GLOBAL。
    api_key / api_secret / api_passphrase :
        显式传入，否则从 ``quant_learn/.env`` 读取。
    proxy_url :
        代理地址，默认 ``http://127.0.0.1:7897``。
    load_spreads :
        是否加载点差数据，默认 False。
    """
    key, secret, passphrase = get_okx_credentials(api_key, api_secret, api_passphrase)
    return OKXDataClientConfig(
        instrument_types=instrument_types,
        environment=environment,
        region=region,
        api_key=key,
        api_secret=secret,
        api_passphrase=passphrase,
        proxy_url=proxy_url,
        load_spreads=load_spreads,
    )


__all__ = ["create_data_client_factory", "build_data_client_config"]
