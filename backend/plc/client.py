"""Thread-safe Siemens Snap7 PLC Client wrapper."""

from __future__ import annotations
import logging
import threading
from typing import Any, Dict, Optional

try:
    import snap7
    from snap7.client import Client
    SNAP7_AVAILABLE = True
except (ImportError, Exception):
    SNAP7_AVAILABLE = False
    snap7 = None
    Client = None

logger = logging.getLogger("plc.client")


class PLCClient:
    """
    Dedicated client for communicating with Siemens S7 PLCs using Snap7.
    Thread-safe, read-only, with automatic connection state checking.
    """

    def __init__(
        self,
        ip: str = "192.168.0.100",
        rack: int = 0,
        slot: int = 1,
        port: int = 102,
        timeout_ms: int = 5000,
    ) -> None:
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.port = port
        self.timeout_ms = timeout_ms

        self._client: Optional[Client] = None
        self._lock = threading.Lock()
        self._connected = False
        self._last_error: Optional[str] = None

        if not SNAP7_AVAILABLE:
            logger.error(
                "The 'python-snap7' package or Snap7 shared library is not installed. "
                "PLC communication will be unavailable until installed."
            )

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to the PLC."""
        with self._lock:
            client = self._client
            if client is None or not self._connected:
                return False
            try:
                # Ask Snap7 client directly for its underlying socket connection state
                return client.get_connected()
            except Exception:
                self._connected = False
                return False

    @property
    def last_error(self) -> Optional[str]:
        """Return the last recorded error message."""
        return self._last_error

    def connect(self) -> bool:
        """
        Attempt to establish a connection to the Siemens PLC.
        Returns True if successful, False otherwise.
        """
        if not SNAP7_AVAILABLE or Client is None:
            self._last_error = "python-snap7 library is not installed or available."
            return False

        with self._lock:
            # Clean up existing client if needed
            if self._client is not None:
                try:
                    if self._client.get_connected():
                        self._client.disconnect()
                except Exception:
                    pass
                self._client = None

            try:
                logger.info(
                    "Connecting to Siemens PLC at %s (Rack: %d, Slot: %d, Port: %d)...",
                    self.ip,
                    self.rack,
                    self.slot,
                    self.port,
                )
                new_client = Client()
                
                # Connect to PLC using IP, Rack, Slot, and Port
                new_client.connect(self.ip, self.rack, self.slot, self.port)

                if new_client.get_connected():
                    self._client = new_client
                    self._connected = True
                    self._last_error = None
                    logger.info("PLC connection established successfully: %s", self.ip)
                    return True
                else:
                    self._client = None
                    self._connected = False
                    self._last_error = (
                        f"Failed to establish connection to {self.ip}:{self.port} "
                        f"(Rack: {self.rack}, Slot: {self.slot})"
                    )
                    logger.warning("PLC connection failed: %s", self._last_error)
                    return False

            except Exception as exc:
                self._client = None
                self._connected = False
                self._last_error = f"Connection error to {self.ip}: {str(exc)}"
                logger.warning("PLC connection exception: %s", self._last_error)
                return False

    def disconnect(self) -> None:
        """Gracefully disconnect from the PLC."""
        with self._lock:
            client = self._client
            self._client = None
            self._connected = False

            if client is not None:
                try:
                    if client.get_connected():
                        logger.info("Disconnecting from Siemens PLC at %s...", self.ip)
                        client.disconnect()
                except Exception as exc:
                    logger.debug("Error during PLC disconnect: %s", exc)
                finally:
                    logger.info("PLC disconnected.")

    def read_db(self, db_number: int, start_byte: int, size: int) -> bytearray:
        """
        Read a block of bytes from a specific Data Block (DB).
        
        :param db_number: Data Block number (e.g. 1 for DB1)
        :param start_byte: Starting byte offset in the DB
        :param size: Number of bytes to read
        :return: bytearray of raw PLC data
        :raises ConnectionError: If not connected or connection drops
        :raises RuntimeError: If Snap7 read operation fails
        """
        if not SNAP7_AVAILABLE:
            raise RuntimeError("python-snap7 library is not installed.")

        with self._lock:
            client = self._client
            if client is None or not client.get_connected():
                self._connected = False
                raise ConnectionError(f"Cannot read DB{db_number}: PLC is not connected ({self.ip})")

            try:
                # Snap7 db_read: (db_number, start_byte, size) -> bytearray
                data: bytearray = client.db_read(db_number, start_byte, size)
                return data
            except Exception as exc:
                self._connected = False
                self._last_error = f"Error reading DB{db_number} [byte {start_byte}..{start_byte+size}]: {exc}"
                logger.warning(self._last_error)
                raise RuntimeError(self._last_error) from exc

    def get_cpu_state(self) -> str:
        """Query PLC CPU operational state (e.g., RUN, STOP, UNKNOWN, OFFLINE)."""
        with self._lock:
            client = self._client
            if client is None or not self._connected:
                return "OFFLINE"

            try:
                state = client.get_cpu_state()
                return state.upper() if state else "UNKNOWN"
            except Exception as exc:
                logger.debug("Failed to get CPU state: %s", exc)
                return "UNKNOWN"

    def get_cpu_info(self) -> Dict[str, Any]:
        """Query Siemens PLC CPU hardware and firmware information."""
        with self._lock:
            client = self._client
            if client is None or not self._connected:
                return {}

            info_dict: Dict[str, Any] = {}
            try:
                cpu_info = client.get_cpu_info()
                if cpu_info:
                    info_dict = {
                        "module_type_name": cpu_info.ModuleTypeName.decode("ascii", errors="ignore").strip() if hasattr(cpu_info, "ModuleTypeName") else None,
                        "serial_number": cpu_info.SerialNumber.decode("ascii", errors="ignore").strip() if hasattr(cpu_info, "SerialNumber") else None,
                        "as_name": cpu_info.ASName.decode("ascii", errors="ignore").strip() if hasattr(cpu_info, "ASName") else None,
                        "module_name": cpu_info.ModuleName.decode("ascii", errors="ignore").strip() if hasattr(cpu_info, "ModuleName") else None,
                    }
            except Exception as exc:
                logger.debug("Could not retrieve CPU info: %s", exc)

            try:
                order_code = client.get_order_code()
                if order_code and hasattr(order_code, "OrderCode"):
                    info_dict["order_code"] = order_code.OrderCode.decode("ascii", errors="ignore").strip()
                elif order_code and hasattr(order_code, "Code"):
                    info_dict["order_code"] = order_code.Code.decode("ascii", errors="ignore").strip()
            except Exception as exc:
                logger.debug("Could not retrieve order code: %s", exc)

            return info_dict
