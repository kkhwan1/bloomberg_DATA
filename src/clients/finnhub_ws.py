"""
Finnhub WebSocket client for real-time market data streaming.

Provides WebSocket connection management with automatic reconnection,
subscription handling, and callback-based message processing.
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any

import websocket

from src.config import APIConfig


logger = logging.getLogger(__name__)


class FinnhubWebSocket:
    """
    WebSocket client for Finnhub real-time market data.

    Features:
    - Automatic reconnection with exponential backoff (max 5 attempts)
    - Thread-safe subscription management
    - Callback-based message processing
    - Data normalization to standard format

    Example:
        >>> def on_message(data):
        ...     print(f"Received: {data}")
        >>>
        >>> ws = FinnhubWebSocket(api_key="your_key", on_message_callback=on_message)
        >>> ws.connect()
        >>> ws.subscribe(["AAPL", "MSFT"])
        >>> # ... receive real-time data ...
        >>> ws.unsubscribe(["MSFT"])
        >>> ws.disconnect()
    """

    WS_URL_TEMPLATE = "wss://ws.finnhub.io?token={api_key}"
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_BASE_DELAY = 1  # seconds
    RECONNECT_MAX_DELAY = 60  # seconds
    PING_INTERVAL = 30  # seconds
    PING_TIMEOUT = 10  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize Finnhub WebSocket client.

        Args:
            api_key: Finnhub API key. If None, reads from APIConfig.
            on_message_callback: Function called with normalized trade data.
                                Expected signature: callback(data: Dict[str, Any])
        """
        self.api_key = api_key or APIConfig.FINNHUB_API_KEY
        if not self.api_key:
            raise ValueError("Finnhub API key is required. Set FINNHUB_API_KEY in .env")

        self.on_message_callback = on_message_callback
        self.ws_url = self.WS_URL_TEMPLATE.format(api_key=self.api_key)

        # WebSocket connection state
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._connected = False
        self._should_reconnect = True
        self._reconnect_attempts = 0

        # Subscription management
        self._subscribed_symbols: set[str] = set()
        self._lock = threading.Lock()

        logger.info("FinnhubWebSocket client initialized")

    def connect(self) -> bool:
        """
        Establish WebSocket connection to Finnhub.

        Returns:
            True if connection successful, False otherwise.
        """
        if self._connected:
            logger.warning("WebSocket already connected")
            return True

        try:
            self._should_reconnect = True
            self._reconnect_attempts = 0

            self._ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # Run WebSocket in separate thread
            self._ws_thread = threading.Thread(
                target=self._ws.run_forever,
                kwargs={
                    'ping_interval': self.PING_INTERVAL,
                    'ping_timeout': self.PING_TIMEOUT
                },
                daemon=True
            )
            self._ws_thread.start()

            # Wait for connection to establish (with timeout)
            timeout = 10  # seconds
            start_time = time.time()
            while not self._connected and time.time() - start_time < timeout:
                time.sleep(0.1)

            if self._connected:
                logger.info("WebSocket connection established")
                return True
            else:
                logger.error("WebSocket connection timeout")
                return False

        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            return False

    def disconnect(self) -> None:
        """
        Close WebSocket connection and cleanup resources.
        """
        logger.info("Disconnecting WebSocket...")
        self._should_reconnect = False

        if self._ws:
            self._ws.close()

        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=5)

        self._connected = False
        self._ws = None
        self._ws_thread = None

        with self._lock:
            self._subscribed_symbols.clear()

        logger.info("WebSocket disconnected")

    def subscribe(self, symbols: List[str]) -> None:
        """
        Subscribe to real-time trades for given symbols.

        Args:
            symbols: List of stock symbols (e.g., ["AAPL", "MSFT"])
        """
        if not self._connected:
            logger.warning("Cannot subscribe: WebSocket not connected")
            return

        with self._lock:
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if symbol_upper not in self._subscribed_symbols:
                    self._send_subscription_message("subscribe", symbol_upper)
                    self._subscribed_symbols.add(symbol_upper)
                    logger.info(f"Subscribed to {symbol_upper}")

    def unsubscribe(self, symbols: List[str]) -> None:
        """
        Unsubscribe from real-time trades for given symbols.

        Args:
            symbols: List of stock symbols to unsubscribe from
        """
        if not self._connected:
            logger.warning("Cannot unsubscribe: WebSocket not connected")
            return

        with self._lock:
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if symbol_upper in self._subscribed_symbols:
                    self._send_subscription_message("unsubscribe", symbol_upper)
                    self._subscribed_symbols.remove(symbol_upper)
                    logger.info(f"Unsubscribed from {symbol_upper}")

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._connected

    @property
    def subscribed_symbols(self) -> List[str]:
        """Get list of currently subscribed symbols."""
        with self._lock:
            return list(self._subscribed_symbols)

    def _send_subscription_message(self, message_type: str, symbol: str) -> None:
        """
        Send subscription/unsubscription message to Finnhub.

        Args:
            message_type: "subscribe" or "unsubscribe"
            symbol: Stock symbol
        """
        if not self._ws:
            return

        message = {
            "type": message_type,
            "symbol": symbol
        }

        try:
            self._ws.send(json.dumps(message))
            logger.debug(f"Sent {message_type} message for {symbol}")
        except Exception as e:
            logger.error(f"Failed to send {message_type} message: {e}")

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        """WebSocket connection opened callback."""
        self._connected = True
        self._reconnect_attempts = 0
        logger.info("WebSocket connection opened")

        # Resubscribe to symbols after reconnection
        with self._lock:
            if self._subscribed_symbols:
                logger.info(f"Resubscribing to {len(self._subscribed_symbols)} symbols")
                for symbol in list(self._subscribed_symbols):
                    self._send_subscription_message("subscribe", symbol)

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """
        WebSocket message received callback.

        Args:
            ws: WebSocket instance
            message: Raw JSON message string
        """
        try:
            data = json.loads(message)

            # Finnhub sends trade data in this format
            if data.get("type") == "trade" and "data" in data:
                for trade in data["data"]:
                    normalized_data = self._normalize_trade_data(trade)

                    if self.on_message_callback:
                        try:
                            self.on_message_callback(normalized_data)
                        except Exception as e:
                            logger.error(f"Error in message callback: {e}")

            elif data.get("type") == "ping":
                # Respond to ping messages
                logger.debug("Received ping")

            else:
                # Log other message types for debugging
                logger.debug(f"Received message: {data.get('type', 'unknown')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """
        WebSocket error callback.

        Args:
            ws: WebSocket instance
            error: Exception that occurred
        """
        logger.error(f"WebSocket error: {error}")

    def _on_close(
        self,
        ws: websocket.WebSocketApp,
        close_status_code: Optional[int],
        close_msg: Optional[str]
    ) -> None:
        """
        WebSocket connection closed callback.

        Args:
            ws: WebSocket instance
            close_status_code: Connection close status code
            close_msg: Connection close message
        """
        self._connected = False
        logger.warning(
            f"WebSocket closed - Code: {close_status_code}, "
            f"Message: {close_msg}"
        )

        # Attempt reconnection if enabled
        if self._should_reconnect:
            self._attempt_reconnection()

    def _attempt_reconnection(self) -> None:
        """
        Attempt to reconnect with exponential backoff.

        Max attempts: 5
        Delay: 1s, 2s, 4s, 8s, 16s (capped at 60s)
        """
        if self._reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
            logger.error(
                f"Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) "
                f"reached. Giving up."
            )
            self._should_reconnect = False
            return

        self._reconnect_attempts += 1

        # Exponential backoff with cap
        delay = min(
            self.RECONNECT_BASE_DELAY * (2 ** (self._reconnect_attempts - 1)),
            self.RECONNECT_MAX_DELAY
        )

        logger.info(
            f"Reconnection attempt {self._reconnect_attempts}/"
            f"{self.MAX_RECONNECT_ATTEMPTS} in {delay}s..."
        )

        time.sleep(delay)

        # Create new WebSocket connection
        try:
            self._ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            self._ws_thread = threading.Thread(
                target=self._ws.run_forever,
                kwargs={
                    'ping_interval': self.PING_INTERVAL,
                    'ping_timeout': self.PING_TIMEOUT
                },
                daemon=True
            )
            self._ws_thread.start()

        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            # Will retry on next close event

    def _normalize_trade_data(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Finnhub trade data to standard format.

        Finnhub format:
            {
                "s": "AAPL",           # symbol
                "p": 150.25,           # price
                "v": 100,              # volume
                "t": 1704672000000     # timestamp (milliseconds)
            }

        Normalized format:
            {
                "symbol": "AAPL",
                "price": 150.25,
                "volume": 100,
                "timestamp": "2026-01-07T16:00:00Z",
                "source": "finnhub"
            }

        Args:
            trade: Raw trade data from Finnhub

        Returns:
            Normalized trade data dictionary
        """
        # Convert milliseconds timestamp to ISO 8601 format
        timestamp_ms = trade.get("t", 0)
        timestamp_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

        return {
            "symbol": trade.get("s", ""),
            "price": trade.get("p", 0.0),
            "volume": trade.get("v", 0),
            "timestamp": timestamp_dt.isoformat().replace("+00:00", "Z"),
            "source": "finnhub"
        }
