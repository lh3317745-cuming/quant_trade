"""OKX 账户信息查询（余额 / 现货持仓 / 策略持仓 / 交易头寸）。

标准 nautilus_trader 架构里，execution / data client 由 LiveNode 编排；
而账户余额、持仓等**查询能力**走独立的 :class:`OKXAccount`，复用
``OKXHttpClient``（nautilus 下单客户端）与 ccxt（补充字段 / 策略持仓）。

- :meth:`OKXAccount.get_balance`             —— 账户各币种余额（cash_bal / liab）。
- :meth:`OKXAccount.get_spot_balance`        —— 现货持仓（free / used / total）。
- :meth:`OKXAccount.get_spot_strategy_positions` —— 现货策略持仓（网格 / 信号 / 定投）。
- :meth:`OKXAccount.get_positions`           —— 合约交易头寸（SWAP / FUTURES / MARGIN）。

通常由 :class:`client.OKXClient` 自动创建并挂到 ``client.account``，也可独立构造：

    account = OKXAccount(okx.http, okx.ccxt)
    balances = await account.get_balance()
"""

from __future__ import annotations

from typing import Any

from nautilus_trader.adapters.okx import OKXHttpClient, OKXInstrumentType

# 合约头寸查询覆盖的品种类型
DEFAULT_POSITION_TYPES = (
    OKXInstrumentType.SWAP,
    OKXInstrumentType.FUTURES,
    OKXInstrumentType.MARGIN,
)


def parse_amount(x: Any) -> float:
    """把 OKX 返回的金额字段尽量解析成 float，失败回退 0.0。"""
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x))
        except Exception:
            return 0.0


def _state_name(state: Any) -> str:
    return {
        "running": "运行中",
        "stopped": "已停止",
        "cancelled": "已取消",
        "finished": "已结束",
    }.get(str(state or ""), str(state or ""))


class OKXAccount:
    """OKX 账户查询封装：余额 / 现货持仓 / 策略持仓 / 交易头寸。"""

    def __init__(
        self,
        http_client: OKXHttpClient,
        ccxt_client: Any = None,
    ) -> None:
        self.http = http_client
        self.ccxt = ccxt_client

    # ------------------------------------------------------------------ #
    # 余额
    # ------------------------------------------------------------------ #
    async def get_balance(self) -> list[dict[str, Any]]:
        """账户各币种余额。

        返回 ``[{"ccy", "cash_bal", "liab"}]``（已过滤 0 余额币种，
        按可用余额降序排列）。底层调用 nautilus ``OKXHttpClient.get_balance()``。
        """
        balances = await self.http.get_balance()
        rows: list[dict[str, Any]] = []
        for b in balances:
            cash = parse_amount(b.cash_bal)
            liab = parse_amount(b.liab)
            if cash == 0.0 and liab == 0.0:
                continue
            rows.append({"ccy": b.ccy, "cash_bal": cash, "liab": liab})
        rows.sort(key=lambda r: -r["cash_bal"])
        return rows

    # ------------------------------------------------------------------ #
    # 现货持仓
    # ------------------------------------------------------------------ #
    async def get_spot_balance(self) -> dict[str, dict[str, float]]:
        """现货持仓（free / used / total 三张表）。

        底层走 ccxt ``fetch_balance()``；返回
        ``{"free": {...}, "used": {...}, "total": {...}}``。
        """
        if self.ccxt is None:
            raise RuntimeError("OKXAccount 未绑定 ccxt 客户端，无法查询现货持仓")
        bal = await self.ccxt.fetch_balance()
        return {
            "free": {k: parse_amount(v) for k, v in (bal.get("free") or {}).items()},
            "used": {k: parse_amount(v) for k, v in (bal.get("used") or {}).items()},
            "total": {k: parse_amount(v) for k, v in (bal.get("total") or {}).items()},
        }

    # ------------------------------------------------------------------ #
    # 现货策略持仓（TradingBot：网格 / 信号 / 定投）
    # ------------------------------------------------------------------ #
    async def get_spot_strategy_positions(self) -> list[tuple[str, dict[str, Any]]]:
        """现货策略持仓，返回 ``[(策略类型, 原始 dict), ...]``。

        覆盖网格（grid）、信号（signal）、定投（recurring / dca）。
        """
        if self.ccxt is None:
            raise RuntimeError("OKXAccount 未绑定 ccxt 客户端，无法查询策略持仓")
        rows: list[tuple[str, dict[str, Any]]] = []

        try:
            grid = await self.ccxt.privateGetTradingBotGridOrdersAlgoPending({
                "instType": "SPOT",
                "algoOrdType": "grid",
            })
            for g in grid.get("data") or []:
                rows.append(("现货网格", g))
        except Exception:
            pass

        try:
            sig = await self.ccxt.privateGetTradingBotSignalPositions({
                "instType": "SPOT",
                "algoOrdType": "signal",
            })
            for s in sig.get("data") or []:
                rows.append(("现货信号", s))
        except Exception:
            pass

        for algo in ("recurring", "dca"):
            try:
                dca = await self.ccxt.privateGetTradingBotDcaOngoingList({"algoOrdType": algo})
                for d in dca.get("data") or []:
                    rows.append(("现货定投", d))
            except Exception:
                pass

        return rows

    # ------------------------------------------------------------------ #
    # 交易头寸
    # ------------------------------------------------------------------ #
    async def get_positions(
        self,
        account_id: str,
        instrument_types: tuple[OKXInstrumentType, ...] = DEFAULT_POSITION_TYPES,
    ) -> list[Any]:
        """合约/永续交易头寸。

        底层调用 nautilus ``request_position_status_reports``，遍历
        SWAP / FUTURES / MARGIN 三种品种类型。返回 ``list[PositionStatusReport]``。
        """
        positions: list[Any] = []
        for itype in instrument_types:
            try:
                reports = self.http.request_position_status_reports(
                    account_id, instrument_type=itype
                )
                if hasattr(reports, "__await__"):
                    reports = await reports
            except Exception:
                continue
            if isinstance(reports, (list, tuple)):
                positions.extend(reports)
        return positions


__all__ = ["OKXAccount", "DEFAULT_POSITION_TYPES", "parse_amount"]
