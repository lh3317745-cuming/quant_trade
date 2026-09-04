"""交易下单模块。

基于 nautilus_trader 的 OKX 执行客户端 (``OKXHttpClient``) 封装的下单/撤单方法。

用法示例::

    import asyncio
    from client import OKXClient

    async def main():
        client = OKXClient()
        report = await client.trader.place_spot_market_order("BTC-USDT", "BUY", "0.001")
        print(report)

    asyncio.run(main())
"""

from annotations.env import auto_load_env, load_dotenv
from instrument.order import OKXTrader, spot_instrument, swap_instrument

__all__ = [
    "OKXTrader",
    "spot_instrument",
    "swap_instrument",
    "load_dotenv",
    "auto_load_env",
]
