"""
Low-level Binance Futures REST client.

Handles authentication (HMAC-SHA256 signatures), request signing,
timestamping, and raw HTTP communication with the Binance Futures Testnet.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # milliseconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures REST API.

    Responsibilities:
    - Sign requests with HMAC-SHA256
    - Attach recvWindow and server timestamp
    - Handle HTTP-level and API-level errors
    - Log every outbound request and inbound response
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised against %s", self._base_url)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Return the Binance server timestamp in milliseconds."""
        data = self._get("/fapi/v1/time")
        return int(data["serverTime"])

    def get_exchange_info(self) -> Dict[str, Any]:
        """Return exchange metadata (symbols, filters, etc.)."""
        return self._get("/fapi/v1/exchangeInfo")

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a new order to the Futures exchange.

        Args:
            params: Order parameters as accepted by POST /fapi/v1/order.

        Returns:
            Full order response dict from Binance.
        """
        return self._post("/fapi/v1/order", params)

    def get_account(self) -> Dict[str, Any]:
        """Return account information including balances."""
        return self._get("/fapi/v2/account", signed=True)

    # ------------------------------------------------------------------
    # Private HTTP helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append timestamp, recvWindow, and HMAC signature to params."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params = self._sign(params)
        url = self._base_url + path
        logger.debug("GET %s params=%s", url, self._redact(params))
        try:
            response = self._session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as exc:
            logger.error("Network error on GET %s: %s", url, exc)
            raise
        return self._parse_response(response)

    def _post(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = self._sign(params)
        url = self._base_url + path
        logger.debug("POST %s body=%s", url, self._redact(params))
        try:
            response = self._session.post(url, data=params, timeout=10)
        except requests.exceptions.RequestException as exc:
            logger.error("Network error on POST %s: %s", url, exc)
            raise
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: requests.Response) -> Dict[str, Any]:
        logger.debug(
            "Response HTTP %s from %s", response.status_code, response.url
        )
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response body: %s", response.text[:500])
            response.raise_for_status()
            raise

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            # Binance error envelope: {"code": -XXXX, "msg": "..."}
            if int(data["code"]) < 0:
                logger.error(
                    "Binance API error code=%s msg=%s", data["code"], data.get("msg")
                )
                raise BinanceAPIError(int(data["code"]), data.get("msg", "Unknown error"))

        if not response.ok:
            logger.error(
                "HTTP error %s for %s: %s",
                response.status_code,
                response.url,
                response.text[:500],
            )
            response.raise_for_status()

        logger.debug("Parsed response: %s", data)
        return data

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of params with the signature masked for log safety."""
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***"
        return redacted
