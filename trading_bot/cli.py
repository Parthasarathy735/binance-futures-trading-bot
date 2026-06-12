#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Trading Bot.

Usage examples:
  python cli.py --api-key KEY --api-secret SECRET \\
      --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  python cli.py --api-key KEY --api-secret SECRET \\
      --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500

  python cli.py --api-key KEY --api-secret SECRET \\
      --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --price 58000

Credentials can also be supplied via environment variables:
  BINANCE_API_KEY and BINANCE_API_SECRET
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

from bot import (
    BinanceClient,
    OrderManager,
    OrderRequest,
    ValidationError,
    setup_logging,
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
)

BANNER = r"""
  ____  _                               ____        _
 | __ )(_)_ __   __ _ _ __   ___ ___  | __ )  ___ | |_
 |  _ \| | '_ \ / _` | '_ \ / __/ _ \ |  _ \ / _ \| __|
 | |_) | | | | | (_| | | | | (_|  __/ | |_) | (_) | |_
 |____/|_|_| |_|\__,_|_| |_|\___\___| |____/ \___/ \__|
  Binance Futures Testnet — USDT-M
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place Market, Limit, or Stop-Market orders on Binance Futures Testnet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Credentials — optional here so env vars can supply them
    creds = parser.add_argument_group("API Credentials")
    creds.add_argument(
        "--api-key",
        default=os.environ.get("BINANCE_API_KEY"),
        metavar="KEY",
        help="Binance API key (or set BINANCE_API_KEY env var).",
    )
    creds.add_argument(
        "--api-secret",
        default=os.environ.get("BINANCE_API_SECRET"),
        metavar="SECRET",
        help="Binance API secret (or set BINANCE_API_SECRET env var).",
    )

    # Order parameters
    order = parser.add_argument_group("Order Parameters")
    order.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT.")
    order.add_argument(
        "--side", required=True, choices=["BUY", "SELL"], help="BUY or SELL."
    )
    order.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        help="Order type.",
    )
    order.add_argument("--quantity", required=True, help="Order quantity.")
    order.add_argument(
        "--price",
        default=None,
        help="Limit price (required for LIMIT) or stop-trigger price (required for STOP_MARKET).",
    )

    # Misc
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--base-url",
        default="https://testnet.binancefuture.com",
        help="Binance base URL (default: testnet).",
    )

    return parser


def print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
) -> None:
    print("\n" + "─" * 55)
    print("  ORDER REQUEST SUMMARY")
    print("─" * 55)
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Type       : {order_type}")
    print(f"  Quantity   : {quantity}")
    if price is not None:
        label = "Stop Price" if order_type == "STOP_MARKET" else "Limit Price"
        print(f"  {label:<11}: {price}")
    print("─" * 55)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(args.log_level)

    print(BANNER)

    # ── Credential check ─────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        parser.error(
            "API credentials are required. Pass --api-key / --api-secret "
            "or set BINANCE_API_KEY / BINANCE_API_SECRET environment variables."
        )

    # ── Input validation ─────────────────────────────────────────────
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity = validate_quantity(args.quantity)
        price = validate_price(args.price, order_type)
    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n  ✗  Validation error: {exc}\n")
        return 1

    # ── Request summary ──────────────────────────────────────────────
    print_request_summary(symbol, side, order_type, quantity, price)

    # ── Build OrderRequest ───────────────────────────────────────────
    request = OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price if order_type == "LIMIT" else None,
        stop_price=price if order_type == "STOP_MARKET" else None,
    )

    # ── API client + order placement ─────────────────────────────────
    client = BinanceClient(
        api_key=args.api_key,
        api_secret=args.api_secret,
        base_url=args.base_url,
    )
    manager = OrderManager(client)

    print("\n  Submitting order…\n")
    result = manager.place(request)

    # ── Output result ────────────────────────────────────────────────
    print("─" * 55)
    print("  ORDER RESPONSE")
    print("─" * 55)
    print(result.display())
    print("─" * 55 + "\n")

    if result.success:
        logger.info(
            "CLI order complete | id=%s status=%s",
            result.order_id,
            result.status,
        )
        return 0
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
