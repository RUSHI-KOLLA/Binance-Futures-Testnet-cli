"""Binance Futures Testnet REST client.

Handles HMAC-SHA256 request signing, server-time synchronisation, structured
logging of every request/response cycle, and graceful error mapping.
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from bot.logging_config import logger


# ── Custom exceptions ────────────────────────────────────────────────────────

class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error payload."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")


class BinanceNetworkError(Exception):
    """Raised when a network-level failure prevents the request."""
    pass


# ── Client ───────────────────────────────────────────────────────────────────

class BinanceFuturesClient:
    """Lightweight, dependency-free REST client for Binance USDT-M Futures
    Testnet (https://testnet.binancefuture.com).

    Parameters
    ----------
    api_key : str, optional
        Testnet API key.  Required for authenticated endpoints.
    api_secret : str, optional
        Testnet API secret.  Required for authenticated endpoints.
    dry_run : bool
        When *True*, authenticated calls return realistic mock responses
        instead of hitting the exchange.
    """

    BASE_URL = "https://demo-fapi.binance.com"

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        dry_run: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.dry_run = dry_run

        if not dry_run and (not api_key or not api_secret):
            logger.warning(
                "API credentials missing — real trades will fail. "
                "Use --dry-run to simulate."
            )

    # ── helpers ──────────────────────────────────────────────────────────

    def _server_timestamp(self) -> int:
        """Fetch the exchange clock to avoid timestamp-drift rejections."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/fapi/v1/time", timeout=5
            )
            resp.raise_for_status()
            ts = resp.json().get("serverTime")
            if ts:
                return int(ts)
        except Exception as exc:
            logger.debug("Server time sync failed, using local clock: %s", exc)
        return int(time.time() * 1000)

    def _sign(self, params: dict) -> str:
        """Compute HMAC-SHA256 signature over the query string."""
        qs = urlencode(params)
        return hmac.new(
            self.api_secret.encode(),
            qs.encode(),
            hashlib.sha256,
        ).hexdigest()

    # ── core request dispatcher ──────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        signed: bool = False,
    ) -> dict:
        """Send an HTTP request, log it, and return the JSON body.

        Raises
        ------
        BinanceAPIError
            If the exchange returns an error payload (HTTP ≥ 400).
        BinanceNetworkError
            If the request cannot be completed due to connectivity.
        ValueError
            If credentials are missing for a signed request.
        """
        params = params or {}

        # Dry-run: return mock data for signed (trading) endpoints
        if self.dry_run and signed:
            # Generate realistic mock parameters to log
            params["timestamp"] = params.get("timestamp") or self._server_timestamp()
            params["signature"] = "a8c9b2d3e4f50123456789abcdef0123456789abcdef0123456789abcdef0123"
            
            # Log the outgoing simulated request (mask signature)
            url = f"{self.BASE_URL}{path}"
            safe = {k: ("***" if k == "signature" else v) for k, v in params.items()}
            logger.debug("REQ  %s %s  params=%s", method, url, safe)
            
            # Get the mock response
            mock_res = self._mock_response(params)
            
            # Log the simulated response body
            import json
            logger.debug("RESP 200  body=%s", json.dumps(mock_res))
            return mock_res

        url = f"{self.BASE_URL}{path}"
        headers: dict[str, str] = {}

        if signed:
            if not self.api_key or not self.api_secret:
                raise ValueError(
                    "API Key and Secret are required for signed requests. "
                    "Configure .env or use --dry-run."
                )
            headers["X-MBX-APIKEY"] = self.api_key
            params["timestamp"] = self._server_timestamp()
            params["signature"] = self._sign(params)

        # Log the outgoing request (mask the signature)
        safe = {k: ("***" if k == "signature" else v) for k, v in params.items()}
        logger.debug("REQ  %s %s  params=%s", method, url, safe)

        try:
            resp = requests.request(
                method, url, headers=headers,
                params=params if method == "GET" else None,
                data=params if method != "GET" else None,
                timeout=10,
            )

            logger.debug("RESP %s  body=%s", resp.status_code, resp.text)

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    raise BinanceAPIError(body.get("code", resp.status_code),
                                         body.get("msg", resp.text))
                except (ValueError, KeyError):
                    raise BinanceAPIError(resp.status_code, resp.text)

            return resp.json()

        except BinanceAPIError:
            raise  # already logged above
        except requests.RequestException as exc:
            logger.error("Network error: %s", exc)
            raise BinanceNetworkError(f"Network error: {exc}") from exc

    # ── public helpers ───────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return *True* if the Testnet API is reachable."""
        try:
            self._request("GET", "/fapi/v1/ping")
            return True
        except Exception:
            return False

    def get_exchange_info(self) -> dict:
        """Fetch exchange-wide trading rules and symbol info."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    # ── order placement ──────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
    ) -> dict:
        """Place an order on Binance Futures Testnet.

        Supports MARKET, LIMIT, STOP_MARKET, and STOP_LIMIT.
        """
        params: dict = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            params["price"] = str(price)
            params["timeInForce"] = "GTC"
        elif order_type == "STOP_MARKET":
            params["stopPrice"] = str(stop_price)
        elif order_type == "STOP_LIMIT":
            params["price"] = str(price)
            params["stopPrice"] = str(stop_price)
            params["timeInForce"] = "GTC"

        logger.info(
            "Placing %s %s order for %s %s …",
            order_type, side, quantity, symbol,
        )
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    # ── mock / dry-run ───────────────────────────────────────────────────

    def _mock_response(self, params: dict) -> dict:
        """Return a realistic mock order response for dry-run mode."""
        import random

        symbol = params.get("symbol", "BTCUSDT")
        side = params.get("side", "BUY")
        otype = params.get("type", "MARKET")
        qty = params.get("quantity", "1.0")
        price = params.get("price", "50000.00")
        stop = params.get("stopPrice", "0.00")

        oid = random.randint(100_000_000, 999_999_999)

        mock = {
            "orderId": oid,
            "symbol": symbol,
            "status": "FILLED" if otype == "MARKET" else "NEW",
            "clientOrderId": f"bot_{oid}",
            "price": price if otype in ("LIMIT", "STOP_LIMIT") else "0.00",
            "avgPrice": price if otype == "MARKET" else "0.00",
            "origQty": qty,
            "executedQty": qty if otype == "MARKET" else "0.00",
            "cumQty": qty if otype == "MARKET" else "0.00",
            "cumQuote": str(float(qty) * float(price)) if otype == "MARKET" else "0.00",
            "timeInForce": "GTC",
            "type": otype,
            "reduceOnly": False,
            "side": side,
            "positionSide": "BOTH",
            "stopPrice": stop if "STOP" in otype else "0.00",
            "workingType": "CONTRACT_PRICE",
            "origType": otype,
            "updateTime": int(time.time() * 1000),
        }

        return mock
