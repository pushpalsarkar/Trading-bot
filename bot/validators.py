"""
Input validation for the trading bot CLI.

Keeping validation separate from the CLI and the client means both
the CLI layer and any future callers (e.g. a web UI, a test suite)
can reuse the same rules without duplicating logic.
"""

import re
from dataclasses import dataclass
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP", "STOP_MARKET"}
SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(Exception):
    """Raised when CLI input fails validation."""


@dataclass
class OrderRequest:
    """A validated, normalized order request ready to send to the API layer."""

    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected an uppercase alphanumeric "
            f"trading pair such as BTCUSDT or ETHUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Order side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required (MARKET, LIMIT, or STOP).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}.")
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return quantity


def validate_price(price, required: bool) -> Optional[float]:
    if price is None or price == "":
        if required:
            raise ValidationError("Price is required for LIMIT and STOP orders.")
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError("Price must be greater than 0.")
    return price


def build_order_request(symbol: str, side: str, order_type: str, quantity, price=None, stop_price=None) -> OrderRequest:
    """
    Validate all raw CLI inputs and return a normalized OrderRequest.
    Raises ValidationError with a human-readable message on the first
    failure encountered.
    """
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)

    needs_price = order_type in {"LIMIT", "STOP"}
    price = validate_price(price, required=needs_price)

    stop_price_val = None
    if order_type in {"STOP", "STOP_MARKET"}:
        if stop_price is None or stop_price == "":
            raise ValidationError(f"Stop price is required for {order_type} orders.")
        stop_price_val = validate_price(stop_price, required=True)

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price_val,
    )
