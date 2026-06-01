"""Order orchestration layer.

Sits between the CLI and the API client — validates inputs, prints a
human-readable request summary, calls the client, and displays the
response or error.
"""

from colorama import Fore, Style, init

from bot.client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from bot.logging_config import logger
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

init(autoreset=True)


# ── Display helpers ──────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'═' * 15} {title} {'═' * 15}")


def _row(label: str, value: str, color=Fore.WHITE) -> None:
    print(f"  {Fore.BLUE}{label:<18}{color}{value}")


# ── Main entry point ────────────────────────────────────────────────────────

def execute_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None = None,
    stop_price: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    dry_run: bool = False,
) -> bool:
    """Validate → summarise → execute → display result.

    Returns *True* on success, *False* on failure.
    """

    # ── 1. Validate ──────────────────────────────────────────────────────
    _header("VALIDATING INPUTS")
    try:
        v_symbol = validate_symbol(symbol)
        v_side = validate_side(side)
        v_type = validate_order_type(order_type)
        v_qty = validate_quantity(quantity)
        v_price = validate_price(price, v_type)
        v_stop = validate_stop_price(stop_price, v_type)
        logger.info(f"{Fore.GREEN}✓ All inputs validated successfully.")
    except ValidationError as exc:
        logger.error(f"{Fore.RED}✗ Validation failed: {exc}")
        return False
    except Exception as exc:
        logger.error(f"{Fore.RED}✗ Unexpected validation error: {exc}")
        return False

    # ── 2. Request summary ───────────────────────────────────────────────
    _header("ORDER REQUEST SUMMARY")
    _row("Symbol", v_symbol, Fore.YELLOW)
    _row("Side", v_side, Fore.GREEN if v_side == "BUY" else Fore.RED)
    _row("Order Type", v_type, Fore.MAGENTA)
    _row("Quantity", str(v_qty), Fore.YELLOW)
    if v_type in ("LIMIT", "STOP_LIMIT"):
        _row("Price", f"{v_price} USDT", Fore.YELLOW)
    if v_type in ("STOP_LIMIT", "STOP_MARKET"):
        _row("Stop Price", f"{v_stop} USDT", Fore.YELLOW)
    _row(
        "Mode",
        "DRY-RUN (simulated)" if dry_run else "LIVE TESTNET",
        Fore.CYAN,
    )
    print(f"{Fore.CYAN}{'═' * 48}\n")

    # ── 3. Execute ───────────────────────────────────────────────────────
    try:
        client = BinanceFuturesClient(
            api_key=api_key, api_secret=api_secret, dry_run=dry_run
        )
        logger.debug(
            "Dispatching %s %s for %.6f %s", v_type, v_side, v_qty, v_symbol
        )

        response = client.place_order(
            symbol=v_symbol,
            side=v_side,
            order_type=v_type,
            quantity=v_qty,
            price=v_price if v_type in ("LIMIT", "STOP_LIMIT") else None,
            stop_price=v_stop if v_type in ("STOP_LIMIT", "STOP_MARKET") else None,
        )

        # ── 4. Response details ──────────────────────────────────────────
        _header("ORDER RESPONSE DETAILS")

        oid = response.get("orderId")
        status = response.get("status")
        exec_qty = response.get("executedQty", "0.00")
        avg_price = response.get("avgPrice", "0.00")
        if not avg_price or float(avg_price) == 0.0:
            avg_price = response.get("price", "0.00")

        _row("Order ID", str(oid), Fore.YELLOW)
        _row(
            "Status",
            str(status),
            Fore.GREEN if status in ("FILLED", "NEW") else Fore.RED,
        )
        _row("Executed Qty", str(exec_qty), Fore.YELLOW)
        _row("Avg / Limit Price", f"{avg_price} USDT", Fore.YELLOW)
        if "STOP" in v_type:
            _row(
                "Stop Trigger",
                f"{response.get('stopPrice', '0.00')} USDT",
                Fore.YELLOW,
            )
        print(f"{Fore.CYAN}{'═' * 48}")

        # ── 5. Success ───────────────────────────────────────────────────
        print(
            f"\n{Fore.GREEN}{Style.BRIGHT}"
            f"✔ SUCCESS — Order placed (ID: {oid})\n"
        )
        logger.info("Order success — ID: %s, Status: %s", oid, status)
        return True

    except BinanceAPIError as exc:
        _header("ORDER FAILED")
        logger.error(
            f"{Fore.RED}✗ API error [{exc.code}]: {exc.message}"
        )
        print(
            f"\n{Fore.RED}{Style.BRIGHT}"
            f"✘ FAILED — API error {exc.code}: {exc.message}\n"
        )
        return False

    except BinanceNetworkError as exc:
        _header("CONNECTION FAILED")
        logger.error(f"{Fore.RED}✗ Network error: {exc}")
        print(
            f"\n{Fore.RED}{Style.BRIGHT}"
            f"✘ FAILED — Could not reach Binance Testnet.\n"
        )
        return False

    except Exception as exc:
        _header("UNEXPECTED ERROR")
        logger.error(f"{Fore.RED}✗ {exc}", exc_info=True)
        print(
            f"\n{Fore.RED}{Style.BRIGHT}"
            f"✘ FAILED — Unexpected error. See logs for details.\n"
        )
        return False
