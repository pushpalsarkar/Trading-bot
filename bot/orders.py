"""
Order placement business logic. Sits between the CLI layer (cli.py)
and the API layer (client.py): builds the request summary, calls the
client, formats the response, and turns any low-level exceptions into
a single OrderResult the CLI can render.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from binance.exceptions import BinanceAPIException, BinanceOrderException, BinanceRequestException
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .client import BinanceFuturesTestnetClient
from .validators import OrderRequest

logger = logging.getLogger("trading_bot")


@dataclass
class OrderResult:
    success: bool
    message: str
    request_summary: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Dict[str, Any]] = None


class OrderManager:
    """High-level order placement, wired to a BinanceFuturesTestnetClient."""

    def __init__(self, client: BinanceFuturesTestnetClient):
        self.client = client

    @staticmethod
    def _summarize_request(order: OrderRequest) -> Dict[str, Any]:
        summary = {
            "symbol": order.symbol,
            "side": order.side,
            "type": order.order_type,
            "quantity": order.quantity,
        }
        if order.price is not None:
            summary["price"] = order.price
        if order.stop_price is not None:
            summary["stopPrice"] = order.stop_price
        return summary

    def place_order(self, order: OrderRequest) -> OrderResult:
        request_summary = self._summarize_request(order)
        logger.info("Order request summary: %s", request_summary)

        try:
            response = self.client.create_order(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
            )
        except (BinanceAPIException, BinanceOrderException) as exc:
            msg = f"Binance API rejected the order: {exc}"
            logger.error(msg)
            return OrderResult(success=False, message=msg, request_summary=request_summary)
        except (Timeout, RequestsConnectionError) as exc:
            msg = f"Network error while contacting Binance Futures Testnet: {exc}"
            logger.error(msg)
            return OrderResult(success=False, message=msg, request_summary=request_summary)
        except (BinanceRequestException, RequestException) as exc:
            msg = f"Request error while contacting Binance Futures Testnet: {exc}"
            logger.error(msg)
            return OrderResult(success=False, message=msg, request_summary=request_summary)
        except Exception as exc:  # noqa: BLE001 - last line of defense, always logged
            msg = f"Unexpected error while placing order: {exc}"
            logger.exception(msg)
            return OrderResult(success=False, message=msg, request_summary=request_summary)

        formatted_response = {
            "orderId": response.get("orderId"),
            "status": response.get("status"),
            "executedQty": response.get("executedQty"),
            "avgPrice": response.get("avgPrice"),
            "side": response.get("side"),
            "type": response.get("type"),
            "symbol": response.get("symbol"),
        }
        logger.info("Order placed successfully: %s", formatted_response)

        return OrderResult(
            success=True,
            message="Order placed successfully.",
            request_summary=request_summary,
            response=formatted_response,
        )
