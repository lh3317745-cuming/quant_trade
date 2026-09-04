"""OKX 交易操作封装（下单 / 撤单 / 查询挂单）。

``OKXTrader`` 持有一个 nautilus_trader 的 :class:`OKXHttpClient`，提供：
- 现货市价 / 限价单
- 合约 / 永续单
- 撤单与一键撤单
- 查询挂单

通常由 :class:`client.OKXClient` 在初始化时自动创建并挂到 ``client.trader``：

    from client import OKXClient

    client = OKXClient()
    await client.trader.place_spot_market_order("BTC-USDT", "BUY", "0.001")

也可手动创建：``trader = OKXTrader(client.http)``。

注意：``OKXHttpClient`` 的所有方法均为 **async**，必须 ``await``。
"""

from __future__ import annotations

import uuid
from typing import Any

from nautilus_trader.adapters.okx import OKXHttpClient, OKXInstrumentType, OKXTradeMode
from nautilus_trader.model import (
    AccountId,
    ClientOrderId,
    InstrumentId,
    OrderSide,
    OrderType,
    PositionSide,
    Price,
    Quantity,
    StrategyId,
    TimeInForce,
    TraderId,
    VenueOrderId,
)

# OKX 交易所标识（InstrumentId 的后缀，如 BTC-USDT.OKX）
OKX_VENUE = "OKX"

# 默认 trader / strategy id（place_order 必填，仅作标识用途）
DEFAULT_TRADER_ID = "T-001"
DEFAULT_STRATEGY_ID = "S-001"


def _new_client_order_id(prefix: str = "O") -> ClientOrderId:
    """生成唯一的客户端订单号（OKX 要求纯字母数字、1-32 字符，不能含 ``-``）。"""
    return ClientOrderId.from_str(f"{prefix}{uuid.uuid4().hex[:24]}")


def spot_instrument(symbol: str) -> InstrumentId:
    """把交易对转为现货 InstrumentId，如 ``BTC-USDT`` -> ``BTC-USDT.OKX``。"""
    s = symbol.replace("/", "-")
    if s.endswith(f".{OKX_VENUE}"):
        return InstrumentId.from_str(s)
    return InstrumentId.from_str(f"{s}.{OKX_VENUE}")


def swap_instrument(symbol: str) -> InstrumentId:
    """把交易对转为永续 InstrumentId，如 ``BTC-USDT`` -> ``BTC-USDT-SWAP.OKX``。"""
    s = symbol.replace("/", "-")
    if s.endswith(f".{OKX_VENUE}"):
        return InstrumentId.from_str(s)
    if not s.upper().endswith("-SWAP"):
        s = f"{s}-SWAP"
    return InstrumentId.from_str(f"{s}.{OKX_VENUE}")


def _to_order_type(order_type: str) -> OrderType:
    ot = order_type.upper()
    mapping = {"MARKET": OrderType.MARKET, "LIMIT": OrderType.LIMIT}
    return mapping[ot] if ot in mapping else OrderType.from_str(ot)


class OKXTrader:
    """OKX 交易封装，提供下单 / 撤单 / 查询挂单方法。"""

    def __init__(
        self,
        http_client: OKXHttpClient,
        ccxt_client: Any = None,
    ) -> None:
        self._client = http_client
        self._ccxt = ccxt_client  # 用于设置杠杆（合约单需要）

    # ------------------------------------------------------------------ #
    # 现货下单
    # ------------------------------------------------------------------ #
    async def place_spot_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float,
        *,
        trader_id: str = DEFAULT_TRADER_ID,
        strategy_id: str = DEFAULT_STRATEGY_ID,
    ) -> Any:
        """现货市价单。``side`` 取 ``"BUY"`` / ``"SELL"``；``quantity`` 为基础币数量。"""
        return await self._place_order(
            instrument_id=spot_instrument(symbol),
            td_mode=OKXTradeMode.CASH,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            trader_id=trader_id,
            strategy_id=strategy_id,
        )

    async def place_spot_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float,
        price: str | float,
        *,
        time_in_force: str = "GTC",
        post_only: bool | None = None,
        trader_id: str = DEFAULT_TRADER_ID,
        strategy_id: str = DEFAULT_STRATEGY_ID,
    ) -> Any:
        """现货限价单。``time_in_force`` 取 ``"GTC"`` / ``"IOC"`` / ``"FOK"`` 等。"""
        return await self._place_order(
            instrument_id=spot_instrument(symbol),
            td_mode=OKXTradeMode.CASH,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            post_only=post_only,
            trader_id=trader_id,
            strategy_id=strategy_id,
        )

    # ------------------------------------------------------------------ #
    # 合约 / 永续下单
    # ------------------------------------------------------------------ #
    async def place_swap_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float,
        *,
        order_type: str = "MARKET",
        price: str | float | None = None,
        td_mode: str = "ISOLATED",
        position_side: str | None = None,
        reduce_only: bool | None = None,
        time_in_force: str | None = None,
        leverage: int | str | None = None,
        take_profit_price: str | float | None = None,
        stop_loss_price: str | float | None = None,
        tp_trigger_price_type: str | None = None,
        sl_trigger_price_type: str | None = None,
        trader_id: str = DEFAULT_TRADER_ID,
        strategy_id: str = DEFAULT_STRATEGY_ID,
    ) -> Any:
        """永续/合约下单（区别于现货单，支持杠杆、止盈、止损）。

        ``order_type`` 取 ``"MARKET"`` / ``"LIMIT"``；``td_mode`` 取
        ``"ISOLATED"``（逐仓）/ ``"CROSS"``（全仓）；``position_side`` 取
        ``"LONG"`` / ``"SHORT"``（单向持仓模式下可省略）。限价单需提供 ``price``。

        合约特有参数：
        - ``leverage``：杠杆率（如 ``10`` 表示 10 倍），下单前自动调用 ``set_leverage``。
        - ``take_profit_price``：止盈触发价，传入则附加市价止盈单。
        - ``stop_loss_price``：止损触发价，传入则附加市价止损单。
        - ``tp_trigger_price_type`` / ``sl_trigger_price_type``：触发价类型
          ``"last"`` / ``"index"`` / ``"mark"``（默认 ``last``）。
        """
        # 1) 设置杠杆（合约单可选）
        if leverage is not None:
            await self.set_leverage(
                symbol, leverage, td_mode=td_mode, position_side=position_side
            )
        # 2) 附加止盈/止损 algo 订单
        attach_algo_ords = self._build_attach_algo_ords(
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            tp_trigger_price_type=tp_trigger_price_type,
            sl_trigger_price_type=sl_trigger_price_type,
        )
        return await self._place_order(
            instrument_id=swap_instrument(symbol),
            td_mode=OKXTradeMode.from_str(td_mode.upper()),
            side=side,
            order_type=_to_order_type(order_type),
            quantity=quantity,
            price=price,
            position_side=position_side,
            reduce_only=reduce_only,
            time_in_force=time_in_force,
            attach_algo_ords=attach_algo_ords,
            trader_id=trader_id,
            strategy_id=strategy_id,
        )

    async def set_leverage(
        self,
        symbol: str,
        leverage: int | str,
        *,
        td_mode: str = "ISOLATED",
        position_side: str | None = None,
    ) -> Any:
        """设置合约/永续杠杆率（通过 ccxt 调用 OKX set-leverage）。

        ``td_mode`` 取 ``"ISOLATED"``（逐仓）/ ``"CROSS"``（全仓）；
        逐仓且双向持仓时可通过 ``position_side``（``"LONG"`` / ``"SHORT"``）指定方向。
        """
        if self._ccxt is None:
            raise RuntimeError("OKXTrader 未绑定 ccxt 客户端，无法设置杠杆率")
        inst_id = str(swap_instrument(symbol).symbol)  # 如 BTC-USDT-SWAP
        mgn_mode = "isolated" if td_mode.upper() == "ISOLATED" else "cross"
        params: dict[str, Any] = {
            "instId": inst_id,
            "lever": str(leverage),
            "mgnMode": mgn_mode,
        }
        if mgn_mode == "isolated" and position_side:
            params["posSide"] = position_side.lower()
        return await self._ccxt.privatePostAccountSetLeverage(params)

    def _build_attach_algo_ords(
        self,
        *,
        take_profit_price: str | float | None,
        stop_loss_price: str | float | None,
        tp_trigger_price_type: str | None,
        sl_trigger_price_type: str | None,
    ) -> list[dict[str, Any]] | None:
        """构建附加止盈/止损参数。

        注意：nautilus_trader 的 ``place_order`` 在解析 ``attach_algo_ords``
        时使用 **snake_case** 键名（见其 ``parse_attach_algo_ords``），键名会被
        自动转换为 OKX 的 ``attachAlgoOrds`` camelCase 字段。因此这里必须传
        ``tp_trigger_px`` / ``sl_trigger_px`` 等 snake_case 键。
        """
        attach: dict[str, Any] = {}
        if take_profit_price is not None:
            attach["tp_trigger_px"] = str(take_profit_price)
            attach["tp_ord_px"] = "-1"  # 市价止盈
            if tp_trigger_price_type:
                attach["tp_trigger_px_type"] = tp_trigger_price_type
        if stop_loss_price is not None:
            attach["sl_trigger_px"] = str(stop_loss_price)
            attach["sl_ord_px"] = "-1"  # 市价止损
            if sl_trigger_price_type:
                attach["sl_trigger_px_type"] = sl_trigger_price_type
        return [attach] if attach else None

    # ------------------------------------------------------------------ #
    # 撤单
    # ------------------------------------------------------------------ #
    async def cancel_order(
        self,
        symbol: str,
        *,
        client_order_id: str | None = None,
        venue_order_id: str | None = None,
        is_swap: bool = False,
    ) -> Any:
        """撤单。``client_order_id`` 与 ``venue_order_id`` 至少提供一个。"""
        if not client_order_id and not venue_order_id:
            raise ValueError("client_order_id 与 venue_order_id 至少需提供一个")
        instrument_id = swap_instrument(symbol) if is_swap else spot_instrument(symbol)
        await self._ensure_instrument(instrument_id)
        return await self._client.cancel_order(
            instrument_id,
            ClientOrderId.from_str(client_order_id) if client_order_id else None,
            VenueOrderId.from_str(venue_order_id) if venue_order_id else None,
        )

    async def cancel_all_orders(self, symbol: str, *, is_swap: bool = False) -> Any:
        """一键撤销某交易对上的全部挂单。"""
        instrument_id = swap_instrument(symbol) if is_swap else spot_instrument(symbol)
        await self._ensure_instrument(instrument_id)
        return await self._client.cancel_all_orders(instrument_id)

    # ------------------------------------------------------------------ #
    # 查询挂单
    # ------------------------------------------------------------------ #
    async def get_open_orders(
        self,
        symbol: str | None = None,
        *,
        is_swap: bool = False,
        account_id: str = "OKX-001",
    ) -> list[Any]:
        """查询当前挂单（未成交的活跃订单）。

        - ``symbol`` 传入则只查该交易对；省略则查全部现货（或 ``is_swap=True`` 时全部合约）挂单。
        - 返回 ``OrderStatusReport`` 列表，空列表表示无挂单。
        """
        account = AccountId.from_str(account_id)
        instrument_id = (
            (swap_instrument(symbol) if is_swap else spot_instrument(symbol))
            if symbol
            else None
        )
        if instrument_id is not None:
            await self._ensure_instrument(instrument_id)
            return await self._client.request_order_status_reports(
                account, instrument_id=instrument_id, open_only=True
            )
        instrument_type = OKXInstrumentType.SWAP if is_swap else OKXInstrumentType.SPOT
        result = await self._client.request_instruments(instrument_type)
        instruments = result[0] if isinstance(result, tuple) else result
        for ins in instruments:
            self._client.cache_instrument(ins)
        return await self._client.request_order_status_reports(
            account, instrument_type=instrument_type, open_only=True
        )

    # ------------------------------------------------------------------ #
    # 内部实现
    # ------------------------------------------------------------------ #
    async def _ensure_instrument(self, instrument_id: InstrumentId) -> None:
        """确保交易品种已缓存到客户端（下单/撤单前必须先缓存）。"""
        symbol = str(instrument_id.symbol)
        if symbol in self._client.get_cached_symbols():
            return
        instrument = await self._client.request_instrument(instrument_id)
        self._client.cache_instrument(instrument)

    async def _place_order(
        self,
        *,
        instrument_id: InstrumentId,
        td_mode: OKXTradeMode,
        side: str,
        order_type: OrderType,
        quantity: str | float,
        price: str | float | None = None,
        time_in_force: str | None = None,
        post_only: bool | None = None,
        reduce_only: bool | None = None,
        position_side: str | None = None,
        attach_algo_ords: list[dict[str, Any]] | None = None,
        trader_id: str = DEFAULT_TRADER_ID,
        strategy_id: str = DEFAULT_STRATEGY_ID,
    ) -> Any:
        await self._ensure_instrument(instrument_id)
        return await self._client.place_order(
            trader_id=TraderId.from_str(trader_id),
            strategy_id=StrategyId.from_str(strategy_id),
            instrument_id=instrument_id,
            td_mode=td_mode,
            client_order_id=_new_client_order_id(),
            order_side=OrderSide.from_str(side.upper()),
            order_type=order_type,
            quantity=Quantity.from_str(str(quantity)),
            time_in_force=TimeInForce.from_str(time_in_force) if time_in_force else None,
            price=Price.from_str(str(price)) if price is not None else None,
            post_only=post_only,
            reduce_only=reduce_only,
            position_side=PositionSide.from_str(position_side.upper()) if position_side else None,
            attach_algo_ords=attach_algo_ords,
        )


__all__ = ["OKXTrader", "spot_instrument", "swap_instrument"]
