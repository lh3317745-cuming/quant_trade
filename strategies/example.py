"""示例策略：订阅行情 → 计算指标 → order_factory 下单。

演示标准 nautilus_trader 策略的完整闭环：

1. ``on_start`` 里用 :meth:`subscribe_bars` 订阅行情（数据由 data client 推送）。
2. ``on_bar`` 里用 :class:`ExponentialMovingAverage` 计算快/慢均线。
3. 金叉/死叉时用 :attr:`order_factory` 构造订单，再 :meth:`submit_order` 提交，
   由 execution client 路由到 OKX。

``dry_run=True``（默认）时只打印信号、不真实下单，方便首次接入验证行情链路。
"""

from __future__ import annotations

from dataclasses import dataclass

from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model import (
    Bar,
    BarType,
    InstrumentId,
    OrderSide,
    Quantity,
    TimeInForce,
)
from nautilus_trader.trading import Strategy


@dataclass
class EmaCrossConfig:
    """EMA 交叉策略配置（纯 Python dataclass，不要继承 StrategyConfig）。"""

    instrument_id: str  # e.g. "BTC-USDT-SWAP.OKX"
    bar_type: str       # e.g. "BTC-USDT-SWAP.OKX-1-MINUTE-LAST-EXTERNAL"
    fast_period: int = 10
    slow_period: int = 30
    trade_size: str = "0.01"  # 下单数量（字符串，经 Quantity.from_str 解析）
    dry_run: bool = True      # True：只打印信号不下单；False：真实下单


class EmaCrossStrategy(Strategy):
    """双均线（EMA）交叉示例策略。"""

    def __init__(self, config: EmaCrossConfig):
        super().__init__(config)
        self._config = config
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type)
        self.trade_size = Quantity.from_str(config.trade_size)

        # 指标
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)

    def on_start(self) -> None:
        # 订阅行情：数据经 data client 进入消息总线，再分发到本策略
        self.subscribe_bars(self.bar_type)
        self.log.info(f"EmaCrossStrategy started, subscribed {self.bar_type}")

    def on_stop(self) -> None:
        self.log.info("EmaCrossStrategy stopped")

    def on_bar(self, bar: Bar) -> None:
        # 计算指标
        self.fast_ema.handle_bar(bar)
        self.slow_ema.handle_bar(bar)

        if not (self.fast_ema.initialized and self.slow_ema.initialized):
            return

        fast = self.fast_ema.value
        slow = self.slow_ema.value

        self.log.info(
            f"EMA {self.instrument_id}: fast={fast:.6f} slow={slow:.6f} "
            f"close={bar.close}"
        )

        if self._config.dry_run:
            return  # 只观察，不下单

        # 金叉做多 / 死叉平多（简化演示；实盘需更完整的状态机）
        if fast > slow and self.portfolio.is_net_flat(self.instrument_id):
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self.trade_size,
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order)
        elif fast < slow and self.portfolio.is_net_long(self.instrument_id):
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.SELL,
                quantity=self.trade_size,
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order)


__all__ = ["EmaCrossConfig", "EmaCrossStrategy"]
