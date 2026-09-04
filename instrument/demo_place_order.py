"""OKX 下单/撤单演示脚本。

演示流程（默认安全模式）：
1. 挂一笔远离市价、不会成交的极小现货限价单；
2. 打印下单回报；
3. 等待 2 秒后按客户端订单号撤单；
4. 打印撤单结果。

用法（在 quant_learn 目录下）：
    .venv\\Scripts\\python.exe instrument/demo_place_order.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 保证可从任意工作目录导入 instrument 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from annotations.env import auto_load_env  # noqa: E402
from client import OKXClient  # noqa: E402


@auto_load_env  # 在 main 执行时自动加载 .env
async def main() -> None:
    client = OKXClient()
    trader = client.trader

    # 1. 现货限价单（价格 1000，远低于市价，不会成交）
    print("== 下单：现货限价单 BTC-USDT BUY 0.00001 @ 1000 ==")
    report = await trader.place_spot_limit_order(
        "BTC-USDT", "BUY", "0.00001", "1000", time_in_force="GTC"
    )
    d = report.to_dict() if hasattr(report, "to_dict") else report
    print("  下单回报:", d)
    client_order_id = d.get("client_order_id") or d.get("cl_ord_id")
    print("  提取的 client_order_id:", client_order_id)

    # 2. 撤单
    print("== 撤单 ==")
    await asyncio.sleep(2)
    cancel_report = await trader.cancel_order(
        "BTC-USDT", client_order_id=client_order_id
    )
    print("  cancel result:", cancel_report)


if __name__ == "__main__":
    asyncio.run(main())
