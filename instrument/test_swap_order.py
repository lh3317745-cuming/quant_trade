"""合约下单测试脚本（远离市价的 10 倍杠杆限价单 + 止盈止损）。

安全策略：
1. 先查询当前市价；
2. 挂一笔远低于市价的 BUY 限价单（不会立即成交）；
3. 10 倍杠杆，附带止盈（市价上方）和止损（市价下方）；
4. 打印下单回报后立即撤单。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from annotations.env import auto_load_env  # noqa: E402
from client import OKXClient  # noqa: E402


@auto_load_env
async def main() -> None:
    client = OKXClient()
    trader = client.trader

    # 1. 查询市价
    ticker = await client.ccxt.fetch_ticker("BTC/USDT:USDT")
    last = float(ticker["last"])
    print(f"== 当前 BTC-USDT-SWAP 市价: {last:.2f} ==")

    # 2. 远离市价的限价单（市价的 50%，做多不会立即成交）
    buy_price = round(last * 0.5, 1)
    # 止盈/止损相对「开仓价」计算：做多单止盈 > 开仓价，止损 < 开仓价
    tp_price = round(buy_price * 1.10, 1)
    sl_price = round(buy_price * 0.95, 1)
    quantity = "0.01"  # 1 张 = 0.01 BTC

    print(f"== 下单：合约限价单 BUY 0.01 BTC @ {buy_price}（10 倍杠杆）==")
    print(f"   止盈 {tp_price} / 止损 {sl_price}")
    report = await trader.place_swap_order(
        "BTC-USDT",
        "BUY",
        quantity,
        order_type="LIMIT",
        price=buy_price,
        td_mode="ISOLATED",
        position_side="LONG",
        leverage=10,
        take_profit_price=tp_price,
        stop_loss_price=sl_price,
        tp_trigger_price_type="mark",
        sl_trigger_price_type="mark",
    )
    d = report.to_dict() if hasattr(report, "to_dict") else report
    print("  下单回报:", d)

    client_order_id = None
    if isinstance(d, dict):
        client_order_id = d.get("client_order_id") or d.get("cl_ord_id") or d.get("ordId")
    print("  提取的 client_order_id:", client_order_id)

    # 3. 撤单
    print("== 撤单 ==")
    await asyncio.sleep(2)
    cancel_report = await trader.cancel_order(
        "BTC-USDT", client_order_id=client_order_id, is_swap=True
    )
    print("  cancel result:", cancel_report)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
