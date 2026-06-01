"""Input validators for CLI arguments.

Each function either returns a cleaned/normalised value or raises
``ValidationError`` with a human-readable explanation.
"""

import re


class ValidationError(ValueError):
    """Raised when a user-supplied value fails validation."""
    pass


# ── Symbol ───────────────────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """Validate and normalise a trading-pair symbol (e.g. BTCUSDT)."""
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")

    cleaned = symbol.strip().upper()
    if not re.match(r"^[A-Z0-9]{3,20}$", cleaned):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Must be alphanumeric and 3–20 characters (e.g. BTCUSDT)."
        )
    return cleaned


# ── Side ─────────────────────────────────────────────────────────────────────

def validate_side(side: str) -> str:
    """Validate order side — must be BUY or SELL."""
    if not side:
        raise ValidationError("Side cannot be empty.")

    cleaned = side.strip().upper()
    if cleaned not in ("BUY", "SELL"):
        raise ValidationError(
            f"Invalid side: '{side}'. Must be either 'BUY' or 'SELL'."
        )
    return cleaned


# ── Order type ───────────────────────────────────────────────────────────────

VALID_ORDER_TYPES = ("MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT")


def validate_order_type(order_type: str) -> str:
    """Validate order type against supported set."""
    if not order_type:
        raise ValidationError("Order type cannot be empty.")

    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Supported: {', '.join(VALID_ORDER_TYPES)}."
        )
    return cleaned


# ── Quantity ─────────────────────────────────────────────────────────────────

def validate_quantity(quantity: str) -> float:
    """Validate that quantity is a positive number."""
    if not quantity:
        raise ValidationError("Quantity cannot be empty.")
    try:
        val = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity must be a number. Got: '{quantity}'")
    if val <= 0:
        raise ValidationError(
            f"Quantity must be greater than zero. Got: {val}"
        )
    return val


# ── Price ────────────────────────────────────────────────────────────────────

def validate_price(price: str, order_type: str) -> float:
    """Validate price — required for LIMIT and STOP_LIMIT orders."""
    ot = order_type.upper()
    if ot in ("LIMIT", "STOP_LIMIT"):
        if not price:
            raise ValidationError(
                f"Price is required for {ot} orders."
            )
        try:
            val = float(price)
        except (ValueError, TypeError):
            raise ValidationError(f"Price must be a number. Got: '{price}'")
        if val <= 0:
            raise ValidationError(
                f"Price must be greater than zero. Got: {val}"
            )
        return val

    # For MARKET / STOP_MARKET price is optional; return 0.0 if absent
    if price:
        try:
            return float(price)
        except (ValueError, TypeError):
            pass
    return 0.0


# ── Stop price ───────────────────────────────────────────────────────────────

def validate_stop_price(stop_price: str, order_type: str) -> float:
    """Validate stop price — required for STOP_LIMIT and STOP_MARKET orders."""
    ot = order_type.upper()
    if ot in ("STOP_LIMIT", "STOP_MARKET"):
        if not stop_price:
            raise ValidationError(
                f"Stop price is required for {ot} orders."
            )
        try:
            val = float(stop_price)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Stop price must be a number. Got: '{stop_price}'"
            )
        if val <= 0:
            raise ValidationError(
                f"Stop price must be greater than zero. Got: {val}"
            )
        return val

    if stop_price:
        try:
            return float(stop_price)
        except (ValueError, TypeError):
            pass
    return 0.0
