from __future__ import annotations

from typing import Any

from nautilus_trader.model import AccountId

from client import OKXClient, parse_amount
from env import auto_load_env


ACCOUNT_ID = AccountId.from_str("OKX-001")


def _state_name(state: Any) -> str:
    return {
        "running": "运行中",
        "stopped": "已停止",
        "cancelled": "已取消",
        "finished": "已结束",
    }.get(str(state or ""), str(state or ""))


@auto_load_env  # main 执行时自动加载 .env
async def main() -> None:
    try:
        okx = OKXClient()
    except ValueError as exc:
        print(exc)
        return

    try:
        balances = await okx.account.get_balance()
    except Exception as exc:
        print("获取余额失败:", type(exc).__name__, exc)
        await okx.close()
        return

    # get_balance() 返回 [{"ccy", "cash_bal", "liab"}]（已过滤 0 余额、按 cash 降序）。
    if not balances:
        print("OKX 账户暂无可用余额或负债。")
        await okx.close()
        return

    print("=" * 64)
    print("OKX 账户资产分布")
    print("=" * 64)
    print(f"{'币种':<12}{'可用余额(cash_bal)':>22}{'负债(liab)':>20}")
    print("-" * 64)
    for b in balances:
        print(f"{b['ccy']:<12}{b['cash_bal']:>22.8f}{b['liab']:>20.8f}")

    total_cash = sum(b["cash_bal"] for b in balances)
    print("-" * 64)
    print(f"币种数量：{len(balances)} 种")
    print(f"可用余额合计（各币种原值累加，非同质）：{total_cash:.8f}")

    # ---- 现货持仓（通过 ccxt 获取可用/冻结/总计完整字段） ----
    print()
    print("=" * 64)
    print("OKX 现货持仓")
    print("=" * 64)
    try:
        spot = await okx.account.get_spot_balance()
        total_map = spot["total"]
        free_map = spot["free"]
        used_map = spot["used"]
        spot_rows = [
            (ccy, free_map.get(ccy, 0.0), used_map.get(ccy, 0.0), total_amt)
            for ccy, total_amt in total_map.items()
            if total_amt != 0.0
        ]
        if not spot_rows:
            print("当前无现货持仓。")
        else:
            print(f"{'币种':<12}{'可用(free)':>20}{'冻结(used)':>20}{'总计(total)':>20}")
            print("-" * 64)
            for ccy, fr, us, tot in sorted(spot_rows, key=lambda x: -x[3]):
                print(f"{ccy:<12}{fr:>20.8f}{us:>20.8f}{tot:>20.8f}")
    except Exception as exc:
        print("获取现货持仓失败:", type(exc).__name__, exc)

    # ---- 现货策略持仓（策略交易 TradingBot：网格 / 信号 / 定投） ----
    print()
    print("=" * 64)
    print("OKX 现货策略持仓")
    print("=" * 64)

    strategy_rows = await okx.account.get_spot_strategy_positions()

    if not strategy_rows:
        print("当前无现货策略持仓。")
    else:
        print(f"{'类型':<8}{'交易对':<16}{'状态':<6}{'投入(USDT)':>14}{'网格数':>6}{'价格区间':>14}{'浮动盈亏':>14}{'网格利润':>14}{'总盈亏':>14}{'收益率':>10}")
        print("-" * 64)
        for kind, p in strategy_rows:
            inst = p.get("instId", "")
            state = _state_name(p.get("state"))
            investment = parse_amount(p.get("investment") or p.get("quoteSz") or p.get("totalInvestment"))
            grid_num = p.get("gridNum", "") or ""
            min_px = p.get("minPx", "") or ""
            max_px = p.get("maxPx", "") or ""
            px_range = f"{min_px}~{max_px}" if (min_px or max_px) else ""
            float_profit = parse_amount(p.get("floatProfit"))
            grid_profit = parse_amount(p.get("gridProfit"))
            total_pnl = parse_amount(p.get("totalPnl"))
            pnl_ratio = parse_amount(p.get("pnlRatio"))
            pnl_ratio_str = f"{pnl_ratio * 100:.2f}%" if pnl_ratio else ""
            print(f"{kind:<8}{inst:<16}{state:<6}{investment:>14.4f}{str(grid_num):>6}{px_range:>14}{float_profit:>14.4f}{grid_profit:>14.4f}{total_pnl:>14.4f}{pnl_ratio_str:>10}")

    # ---- 查询当前交易持仓（头寸） ----
    positions = await okx.account.get_positions(ACCOUNT_ID)

    print()
    print("=" * 64)
    print("OKX 当前交易持仓（头寸）")
    print("=" * 64)
    if not positions:
        print("当前无未平仓头寸。")
        await okx.close()
        return

    print(f"{'合约':<24}{'方向':>8}{'数量':>22}{'开仓均价':>20}")
    print("-" * 64)
    for p in positions:
        inst = getattr(p, "instrument_id", None)
        side = getattr(p, "position_side", None)
        qty = getattr(p, "quantity", None)
        avg_px = getattr(p, "avg_px_open", None)
        inst_str = str(inst)
        side_str = getattr(side, "name", str(side)) if side is not None else ""
        qty_str = f"{qty}" if qty is not None else ""
        avg_str = f"{avg_px}" if avg_px is not None else ""
        print(f"{inst_str:<24}{side_str:>8}{qty_str:>22}{avg_str:>20}")

    await okx.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
