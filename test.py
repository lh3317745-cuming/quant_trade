
from __future__ import annotations

from nautilus_trader.adapters.okx import OKX
from nautilus_trader.adapters.okx import OKXDataClientConfig
from nautilus_trader.adapters.okx import OKXDataClientFactory
from nautilus_trader.adapters.okx import OKXEnvironment
from nautilus_trader.adapters.okx import OKXInstrumentType
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import BarType
from nautilus_trader.model import ClientId
from nautilus_trader.model import InstrumentId
from nautilus_trader.model import TraderId
from nautilus_trader.testkit import DataTesterConfig


OKX_ENVIRONMENT = OKXEnvironment.LIVE
TRADER_ID = TraderId.from_str("TESTER-001")
INSTRUMENT_TYPES = [OKXInstrumentType.SWAP]
INSTRUMENT_ID = InstrumentId.from_str(f"ETH-USDT-SWAP.{OKX}")
BAR_TYPE = BarType.from_str(f"{INSTRUMENT_ID}-1-MINUTE-LAST-EXTERNAL")
proxy_url = "http://127.0.0.1:7897"

def main() -> None:
    """
    Run the example.
    """
    node = (
        LiveNode.builder("OKX-DATA-TESTER-001", TRADER_ID, Environment.LIVE)
        .add_data_client(
            None,
            OKXDataClientFactory(),
            OKXDataClientConfig(
                instrument_types=INSTRUMENT_TYPES,
                environment=OKX_ENVIRONMENT,
                proxy_url=proxy_url
            ),
        )
        .build()
    )
    node.add_builtin_actor(
        "DataTester",
        DataTesterConfig(
            client_id=ClientId.from_str(OKX),
            instrument_ids=[INSTRUMENT_ID],
            bar_types=[BAR_TYPE],
            subscribe_book_deltas=True,
            subscribe_quotes=True,
            subscribe_trades=True,
            subscribe_mark_prices=True,
            subscribe_index_prices=True,
            subscribe_funding_rates=True,
            subscribe_bars=True,
            request_instruments=True,
            request_trades=True,
            request_bars=True,
            request_book_snapshot=True,
            request_funding_rates=True,
            manage_book=True,
            log_data=True,
        ),
    )

    node.run()


if __name__ == "__main__":
    main()