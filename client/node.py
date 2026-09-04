"""OKX 流程编排：用 builder 模式组装 execution client + data client + 策略。

这是标准 nautilus_trader 的 live 架构入口。核心是 :func:`build_okx_node`，
它把三种能力用 ``LiveNode.builder`` 链式组装：

- **execution client**（执行下单/撤单）→ ``add_exec_client``
- **data client**（订阅行情）       → ``add_data_client``
- **策略**（消费行情、计算指标、下单）→ ``node.add_strategy``

``build_okx_node`` 是 async 的，因为其中包含一个**可选的杠杆启动钩子**
（``leverage`` 参数）：传入 :class:`~client.leverage.LeverageConfig` 时，
在组装节点前先 ``await`` 设置杠杆倍数。

    node = await build_okx_node(
        "OKX-LIVE", "T-001",
        strategy=my_strategy,
        leverage=LeverageConfig("BTC-USDT", 10, position_side="long"),
    )
    node.run()
"""

from __future__ import annotations

from nautilus_trader.adapters.okx import OKXDataClientConfig, OKXExecClientConfig
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId
from nautilus_trader.trading import Strategy

from client.data import build_data_client_config, create_data_client_factory
from client.execution import build_exec_client_config, create_exec_client_factory
from client.leverage import LeverageConfig, set_okx_leverage

# 默认 client 名（与 OKXDataClientFactory/OKXExecutionClientFactory.name() 一致）
DEFAULT_CLIENT_NAME = "OKX"


async def build_okx_node(
    name: str,
    trader_id: str,
    *,
    strategy: Strategy | None = None,
    exec_config: OKXExecClientConfig | None = None,
    data_config: OKXDataClientConfig | None = None,
    environment: Environment = Environment.LIVE,
    leverage: LeverageConfig | None = None,
) -> LiveNode:
    """用 builder 模式组装一个 OKX LiveNode（async）。

    参数
    ----
    name :
        LiveNode 名称（用于日志/状态标识），如 ``"OKX-LIVE"``。
    trader_id :
        交易者 ID，如 ``"T-001"``。
    strategy :
        可选，需要注册到节点的策略实例（其 ``on_start`` 里订阅行情）。
    exec_config :
        可选，execution client 配置；缺省时用默认参数构建（自动注入凭据）。
    data_config :
        可选，data client 配置；缺省时用默认参数构建（自动注入凭据）。
    environment :
        nautilus 运行环境（``nautilus_trader.common.Environment``），默认 LIVE。
    leverage :
        可选杠杆启动钩子。传入 :class:`~client.leverage.LeverageConfig` 时，
        在组装节点前先设置杠杆倍数；传 ``None`` 则跳过（用账户默认杠杆）。

    返回
    ----
    LiveNode
        已注册 execution/data client（以及可选策略）但尚未运行的节点，
        调用方执行 ``node.run()`` 启动。
    """
    # 可选的杠杆启动钩子
    if leverage is not None:
        await set_okx_leverage(
            leverage.symbol,
            leverage.leverage,
            td_mode=leverage.td_mode,
            position_side=leverage.position_side,
        )

    if exec_config is None:
        exec_config = build_exec_client_config(trader_id)
    if data_config is None:
        data_config = build_data_client_config()

    builder = LiveNode.builder(name, TraderId.from_str(trader_id), environment)

    # 注册 data client（订阅行情）
    builder.add_data_client(
        DEFAULT_CLIENT_NAME,
        create_data_client_factory(),
        data_config,
    )

    # 注册 execution client（执行下单/撤单）
    builder.add_exec_client(
        DEFAULT_CLIENT_NAME,
        create_exec_client_factory(),
        exec_config,
    )

    node = builder.build()

    if strategy is not None:
        node.add_strategy(strategy)

    return node


__all__ = ["build_okx_node", "DEFAULT_CLIENT_NAME"]
