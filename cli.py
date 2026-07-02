#!/usr/bin/env python3
"""
CLI entry point for the Simplified Trading Bot (Binance Futures Testnet).

Examples:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    python cli.py --symbol ETHUSDT --side SELL --type LIMIT \\
        --quantity 0.05 --price 3200.5

    python cli.py --symbol BTCUSDT --side BUY --type STOP \\
        --quantity 0.01 --price 60500 --stop-price 60400

Credentials can be supplied via --api-key / --api-secret, or (preferred,
so they never end up in shell history) via a .env file / environment
variables BINANCE_API_KEY and BINANCE_API_SECRET.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    COLOR = True
except ImportError:  # colorama is optional, CLI still works without color
    COLOR = False

from bot.client import BinanceFuturesTestnetClient
from bot.logging_config import setup_logger
from bot.orders import OrderManager
from bot.validators import ValidationError, build_order_request


def _c(text: str, color: str) -> str:
    if not COLOR:
        return text
    return f"{color}{text}{Style.RESET_ALL}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET / LIMIT / STOP orders on Binance Futures Testnet (USDT-M).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument("--price", required=False, help="Order price (required for LIMIT / STOP)")
    parser.add_argument("--stop-price", dest="stop_price", required=False, help="Stop trigger price (required for STOP)")

    parser.add_argument("--api-key", dest="api_key", required=False, help="Binance Futures Testnet API key")
    parser.add_argument("--api-secret", dest="api_secret", required=False, help="Binance Futures Testnet API secret")

    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip the confirmation prompt and place the order immediately"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and print the order summary WITHOUT sending anything to Binance",
    )
    return parser


def confirm(summary: dict) -> bool:
    print(_c("\nOrder Request Summary:", Fore.CYAN if COLOR else ""))
    for key, value in summary.items():
        print(f"  {key:<10}: {value}")
    answer = input(_c("\nSubmit this order to Binance Futures Testnet? [y/N]: ", Fore.YELLOW if COLOR else ""))
    return answer.strip().lower() in {"y", "yes"}


def main() -> int:
    load_dotenv()  # pulls BINANCE_API_KEY / BINANCE_API_SECRET from a .env file if present
    logger = setup_logger()

    parser = build_parser()
    args = parser.parse_args()

    # --- Validate input -------------------------------------------------
    try:
        order = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(_c(f"Invalid input: {exc}", Fore.RED if COLOR else ""))
        return 1

    request_summary = {
        "symbol": order.symbol,
        "side": order.side,
        "type": order.order_type,
        "quantity": order.quantity,
        "price": order.price,
        "stopPrice": order.stop_price,
    }
    request_summary = {k: v for k, v in request_summary.items() if v is not None}

    if args.dry_run:
        print(_c("[DRY RUN] No request will be sent to Binance.", Fore.YELLOW if COLOR else ""))
        for key, value in request_summary.items():
            print(f"  {key:<10}: {value}")
        logger.info("Dry run only. Request summary: %s", request_summary)
        return 0

    if not args.yes:
        if not confirm(request_summary):
            print("Cancelled.")
            return 0

    # --- Resolve credentials --------------------------------------------
    api_key = args.api_key or os.getenv("BINANCE_API_KEY")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        msg = (
            "Missing API credentials. Pass --api-key/--api-secret, or set "
            "BINANCE_API_KEY / BINANCE_API_SECRET in your environment or a .env file."
        )
        logger.error(msg)
        print(_c(msg, Fore.RED if COLOR else ""))
        return 1

    # --- Place the order --------------------------------------------------
    try:
        client = BinanceFuturesTestnetClient(api_key, api_secret)
    except ValueError as exc:
        logger.error("Client initialization failed: %s", exc)
        print(_c(str(exc), Fore.RED if COLOR else ""))
        return 1

    manager = OrderManager(client)
    result = manager.place_order(order)

    print(_c("\nOrder Request:", Fore.CYAN if COLOR else ""))
    for key, value in result.request_summary.items():
        print(f"  {key:<10}: {value}")

    if result.success:
        print(_c("\n✔ " + result.message, Fore.GREEN if COLOR else ""))
        print(_c("Order Response:", Fore.CYAN if COLOR else ""))
        for key, value in result.response.items():
            print(f"  {key:<12}: {value}")
        return 0

    print(_c("\n✘ " + result.message, Fore.RED if COLOR else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
