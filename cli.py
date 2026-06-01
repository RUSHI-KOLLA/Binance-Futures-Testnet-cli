#!/usr/bin/env python3
"""CLI entry point for the Binance Futures Testnet Trading Bot.

Supports two modes:
  • **Direct mode** — pass all arguments on the command line (great for
    scripting and automation).
  • **Interactive mode** — launches a guided wizard when run without
    arguments (or with ``-i``).
"""

import argparse
import os
import sys

from colorama import Fore, Style, init
from dotenv import load_dotenv

from bot.logging_config import logger
from bot.orders import execute_order

init(autoreset=True)

# Load .env from the project root
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def _credentials():
    """Read API credentials from environment variables."""
    return os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_API_SECRET")


# ── Interactive wizard ───────────────────────────────────────────────────────

def _interactive(api_key: str | None, api_secret: str | None) -> None:
    """Step-by-step interactive order placement using ``questionary``."""
    try:
        import questionary
    except ImportError:
        logger.error(
            "%squestionary not installed. "
            "Run  pip install -r requirements.txt  first.",
            Fore.RED,
        )
        sys.exit(1)

    print(
        f"\n{Fore.GREEN}{Style.BRIGHT}"
        "==========================================\n"
        "  🚀  Binance Futures Testnet Trading Bot\n"
        f"=========================================={Style.RESET_ALL}\n"
    )

    # Symbol
    sym = questionary.select(
        "Select trading symbol:",
        choices=[
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
            "Custom (type manually)",
        ],
    ).ask()
    if sym == "Custom (type manually)":
        sym = questionary.text(
            "Enter symbol (e.g. ADAUSDT):",
            validate=lambda t: len(t.strip()) >= 3 or "Min 3 characters.",
        ).ask()
    if not sym:
        return

    # Side
    side = questionary.select("Select side:", choices=["BUY", "SELL"]).ask()
    if not side:
        return

    # Order type
    otype = questionary.select(
        "Select order type:",
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"],
    ).ask()
    if not otype:
        return

    # Quantity
    qty = questionary.text(
        "Enter quantity:",
        validate=lambda t: (
            True
            if t.strip() and t.strip().replace(".", "", 1).isdigit()
            else "Enter a positive number."
        ),
    ).ask()
    if not qty:
        return

    # Price (conditional)
    price = None
    if otype in ("LIMIT", "STOP_LIMIT"):
        price = questionary.text(
            "Enter limit price (USDT):",
            validate=lambda t: (
                True
                if t.strip() and t.strip().replace(".", "", 1).isdigit()
                else "Enter a positive number."
            ),
        ).ask()
        if not price:
            return

    # Stop price (conditional)
    stop_price = None
    if otype in ("STOP_MARKET", "STOP_LIMIT"):
        stop_price = questionary.text(
            "Enter trigger / stop price (USDT):",
            validate=lambda t: (
                True
                if t.strip() and t.strip().replace(".", "", 1).isdigit()
                else "Enter a positive number."
            ),
        ).ask()
        if not stop_price:
            return

    # Dry-run toggle
    dry = questionary.confirm(
        "Dry-run (simulated)?", default=not bool(api_key)
    ).ask()

    # Confirmation
    if not questionary.confirm(
        f"Place {otype} {side} order now?", default=True
    ).ask():
        logger.info("%sOrder cancelled by user.", Fore.YELLOW)
        return

    execute_order(
        symbol=sym,
        side=side,
        order_type=otype,
        quantity=qty,
        price=price,
        stop_price=stop_price,
        api_key=api_key,
        api_secret=api_secret,
        dry_run=dry,
    )


# ── CLI argument parser ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Place orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("-s", "--symbol", help="Trading pair (e.g. BTCUSDT)")
    parser.add_argument(
        "-d", "--side", choices=["BUY", "SELL"], help="Order side"
    )
    parser.add_argument(
        "-t", "--type",
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"],
        help="Order type",
    )
    parser.add_argument("-q", "--quantity", help="Order quantity")
    parser.add_argument(
        "-p", "--price", help="Limit price (required for LIMIT / STOP_LIMIT)"
    )
    parser.add_argument(
        "--stop-price",
        help="Trigger price (required for STOP_MARKET / STOP_LIMIT)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate the order locally (no API call)",
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true",
        help="Launch the interactive wizard",
    )

    args = parser.parse_args()
    api_key, api_secret = _credentials()

    # Interactive mode when no trading flags are supplied (or -i)
    has_flags = any([args.symbol, args.side, args.type, args.quantity])
    if args.interactive or not has_flags:
        _interactive(api_key, api_secret)
        return

    # Direct mode — all four core flags are mandatory
    missing = []
    if not args.symbol:
        missing.append("--symbol")
    if not args.side:
        missing.append("--side")
    if not args.type:
        missing.append("--type")
    if not args.quantity:
        missing.append("--quantity")
    if missing:
        print(
            f"{Fore.RED}Missing required arguments: {', '.join(missing)}\n"
            "Tip: run without arguments for interactive mode."
        )
        parser.print_help()
        sys.exit(1)

    ok = execute_order(
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
        api_key=api_key,
        api_secret=api_secret,
        dry_run=args.dry_run,
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
