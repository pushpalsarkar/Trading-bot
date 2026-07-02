"""
Thin wrapper around python-binance's Client, scoped to Binance Futures
Testnet (USDT-M). Keeping this isolated from orders.py / cli.py means
the underlying HTTP/SDK layer can be swapped out (e.g. for direct REST
calls) without touching business logic or the CLI.
"""

import logging
from typing import Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException, BinanceRequestException

logger = logging.getLogger("trading_bot")

FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceFuturesTestnetClient:
    """
    Wraps python-binance's Client, pointed at the Futures Testnet.

    All network calls are logged (request + response/error) before
    being handed back to the caller, so orders.py never has to worry
    about logging plumbing.
    """

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("API key and API secret are required.")

        # python-binance's `testnet=True` flag points both the spot
        # and futures endpoints at their respective testnets.
        self._client = Client(api_key, api_secret, testnet=True)

        # Belt-and-braces: explicitly set the futures base URL in case
        # the installed python-binance version doesn't fully honor
        # testnet=True for the futures endpoints.
        self._client.FUTURES_URL = FUTURES_TESTNET_BASE_URL + "/fapi"

        logger.debug("Initialized Binance Futures Testnet client (base_url=%s)", FUTURES_TESTNET_BASE_URL)

    def ping(self) -> bool:
        """Simple connectivity/credentials check."""
        logger.debug("REQUEST -> futures_ping()")
        try:
            self._client.futures_ping()
            logger.debug("RESPONSE <- futures_ping() OK")
            return True
        except (BinanceAPIException, BinanceRequestException) as exc:
            logger.error("futures_ping() failed: %s", exc)
            return False

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        logger.debug("REQUEST -> futures_symbol_ticker(symbol=%s)", symbol)
        try:
            ticker = self._client.futures_symbol_ticker(symbol=symbol)
            logger.debug("RESPONSE <- futures_symbol_ticker: %s", ticker)
            return float(ticker["price"])
        except (BinanceAPIException, BinanceRequestException) as exc:
            logger.error("futures_symbol_ticker(%s) failed: %s", symbol, exc)
            return None

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Places an order on Binance Futures Testnet and returns the raw
        API response as a dict. Raises BinanceAPIException /
        BinanceOrderException / BinanceRequestException on failure,
        which the caller (orders.py) is expected to catch.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type in {"STOP", "STOP_MARKET"}:
            params["stopPrice"] = stop_price
            if order_type == "STOP":
                params["price"] = price
                params["timeInForce"] = time_in_force

        logger.info("REQUEST -> futures_create_order(%s)", params)
        try:
            response = self._client.futures_create_order(**params)
            logger.info("RESPONSE <- futures_create_order: %s", response)
            return response
        except (BinanceAPIException, BinanceOrderException, BinanceRequestException) as exc:
            logger.error("futures_create_order failed for params=%s | error=%s", params, exc)
            raise
