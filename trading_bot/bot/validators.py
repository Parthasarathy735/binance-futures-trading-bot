"""
Input validation for trading bot CLI parameters.
All validation raises ValueError with a descriptive message on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


class ValidationError(ValueError):
    """Raised when user-supplied trading parameters fail validation."""


def validate_symbol(symbol: str) -> str:
    """
    Normalise and validate a futures trading symbol.

    Args:
        symbol: Raw symbol string, e.g. 'btcusdt' or 'ETHUSDT'.

    Returns:
        Upper-cased symbol string.

    Raises:
        ValidationError: If the symbol is empty or contains illegal characters.
    """
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise ValidationError("Symbol must not be empty.")
    if not cleaned.isalnum():
        raise ValidationError(
            f"Symbol '{cleaned}' contains invalid characters. "
            "Use alphanumeric pairs only, e.g. BTCUSDT."
        )
    return cleaned


def validate_side(side: str) -> str:
    """
    Validate the order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Upper-cased side string.

    Raises:
        ValidationError: If side is not BUY or SELL.
    """
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValidationError(
            f"Side '{side}' is invalid. Choose from: {', '.join(sorted(VALID_SIDES))}."
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """
    Validate the order type.

    Args:
        order_type: One of MARKET, LIMIT, STOP_MARKET (case-insensitive).

    Returns:
        Upper-cased order type string.

    Raises:
        ValidationError: If the order type is unsupported.
    """
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type '{order_type}' is not supported. "
            f"Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return cleaned


def validate_quantity(quantity: str) -> Decimal:
    """
    Validate and parse order quantity.

    Args:
        quantity: String representation of quantity.

    Returns:
        Decimal quantity value.

    Raises:
        ValidationError: If quantity is not a positive number.
    """
    try:
        value = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(f"Quantity '{quantity}' is not a valid number.")

    if value <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got {value}.")

    return value


def validate_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """
    Validate and parse limit price.

    Args:
        price: String representation of price, or None.
        order_type: The order type; price is required for LIMIT orders.

    Returns:
        Decimal price value, or None for MARKET orders.

    Raises:
        ValidationError: If price is missing for a LIMIT order, or invalid.
    """
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            value = Decimal(str(price))
        except InvalidOperation:
            raise ValidationError(f"Price '{price}' is not a valid number.")
        if value <= 0:
            raise ValidationError(f"Price must be greater than zero, got {value}.")
        return value

    if order_type == "STOP_MARKET":
        if price is None:
            raise ValidationError("Stop price is required for STOP_MARKET orders.")
        try:
            value = Decimal(str(price))
        except InvalidOperation:
            raise ValidationError(f"Stop price '{price}' is not a valid number.")
        if value <= 0:
            raise ValidationError(f"Stop price must be greater than zero, got {value}.")
        return value

    # MARKET orders — price is irrelevant
    return None
