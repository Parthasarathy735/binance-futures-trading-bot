"""
Order placement logic for Binance Futures.

Provides a high-level OrderManager that translates validated user intent
into Binance API calls and returns structured result objects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceClient, BinanceAPIError

logger = logging.getLogger("trading_bot.orders")


@dataclass
class OrderRequest:
    """Holds validated parameters for a single order."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None       # LIMIT price
    stop_price: Optional[Decimal] = None  # STOP_MARKET trigger price


@dataclass
class OrderResult:
    """Structured summary of a placed order."""

    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def display(self) -> str:
        """Return a human-readable summary string."""
        if not self.success:
            return f"  ✗  Order FAILED: {self.error_message}"

        lines = [
            "  ✓  Order placed successfully",
            f"     Order ID      : {self.order_id}",
            f"     Client ID     : {self.client_order_id}",
            f"     Symbol        : {self.symbol}",
            f"     Side          : {self.side}",
            f"     Type          : {self.order_type}",
            f"     Status        : {self.status}",
            f"     Orig Qty      : {self.orig_qty}",
            f"     Executed Qty  : {self.executed_qty}",
        ]
        if self.avg_price and self.avg_price != "0":
            lines.append(f"     Avg Price     : {self.avg_price}")
        if self.price and self.price != "0":
            lines.append(f"     Limit Price   : {self.price}")
        return "\n".join(lines)


class OrderManager:
    """
    High-level interface for placing futures orders.

    Wraps BinanceClient and translates OrderRequest objects into
    the correct API parameters for each order type.
    """

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    def place(self, request: OrderRequest) -> OrderResult:
        """
        Place an order based on the supplied OrderRequest.

        Args:
            request: Validated order parameters.

        Returns:
            OrderResult describing success or failure.
        """
        params = self._build_params(request)

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            request.side,
            request.order_type,
            request.symbol,
            request.quantity,
            request.price or "N/A",
        )

        try:
            response = self._client.place_order(params)
            logger.info(
                "Order accepted | id=%s status=%s executedQty=%s",
                response.get("orderId"),
                response.get("status"),
                response.get("executedQty"),
            )
            return self._parse_success(response)

        except BinanceAPIError as exc:
            logger.error("Binance API rejected order: %s", exc)
            return OrderResult(success=False, error_message=str(exc))

        except Exception as exc:
            logger.error("Unexpected error placing order: %s", exc, exc_info=True)
            return OrderResult(success=False, error_message=f"Unexpected error: {exc}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_params(request: OrderRequest) -> Dict[str, Any]:
        """Convert an OrderRequest into Binance API params dict."""
        params: Dict[str, Any] = {
            "symbol": request.symbol,
            "side": request.side,
            "type": request.order_type,
            "quantity": str(request.quantity),
        }

        if request.order_type == "LIMIT":
            params["price"] = str(request.price)
            params["timeInForce"] = "GTC"  # Good-Till-Cancelled

        elif request.order_type == "STOP_MARKET":
            params["stopPrice"] = str(request.stop_price)

        return params

    @staticmethod
    def _parse_success(response: Dict[str, Any]) -> OrderResult:
        """Map a successful Binance response to an OrderResult."""
        return OrderResult(
            success=True,
            order_id=response.get("orderId"),
            client_order_id=response.get("clientOrderId"),
            symbol=response.get("symbol"),
            side=response.get("side"),
            order_type=response.get("type"),
            status=response.get("status"),
            orig_qty=response.get("origQty"),
            executed_qty=response.get("executedQty"),
            avg_price=response.get("avgPrice"),
            price=response.get("price"),
            raw_response=response,
        )
