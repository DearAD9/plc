"""Asynchronous background PLC data reader and polling service."""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Callable, Coroutine, Dict, List, Optional, Set, Union
from collections import defaultdict

from backend.config import settings, load_plc_variable_config
from backend.models.plc_data import (
    PLCConfigFile,
    PLCDataSnapshot,
    PLCStatusResponse,
    PLCVariableConfig,
    PLCVariableValue,
)
from backend.plc.client import PLCClient
from backend.plc.datatypes import S7DataParser, S7DataTypeError

logger = logging.getLogger("plc.reader")


class PLCReaderService:
    """
    Background polling service that periodically reads configured tags from the Siemens PLC,
    converts raw data to engineering values, and broadcasts updates.
    """

    def __init__(
        self,
        client: Optional[PLCClient] = None,
        config: Optional[PLCConfigFile] = None,
        poll_interval: Optional[float] = None,
        reconnect_interval: Optional[float] = None,
    ):
        self.config = config or load_plc_variable_config()
        self.poll_interval = poll_interval if poll_interval is not None else settings.plc_poll_interval
        self.reconnect_interval = reconnect_interval if reconnect_interval is not None else settings.plc_reconnect_interval

        self.client = client or PLCClient(
            ip=settings.plc_ip,
            rack=settings.plc_rack,
            slot=settings.plc_slot,
            port=settings.plc_port,
            timeout_ms=settings.plc_timeout_ms,
        )

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._listeners: Set[Callable[[PLCDataSnapshot], Coroutine]] = set()

        self._last_successful_read: Optional[datetime] = None
        self._latest_snapshot: PLCDataSnapshot = PLCDataSnapshot(
            timestamp=datetime.now(timezone.utc),
            plc_connected=False,
            variables={},
            details={},
            errors={},
        )

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def latest_snapshot(self) -> PLCDataSnapshot:
        return self._latest_snapshot

    def subscribe(self, callback: Callable[[PLCDataSnapshot], Coroutine]) -> None:
        """Register a callback coroutine to receive real-time data snapshots."""
        self._listeners.add(callback)

    def unsubscribe(self, callback: Callable[[PLCDataSnapshot], Coroutine]) -> None:
        """Unregister a subscriber callback."""
        self._listeners.discard(callback)

    def reload_config(self, new_config: Optional[PLCConfigFile] = None) -> None:
        """Reload variable configuration dynamically."""
        self.config = new_config or load_plc_variable_config()
        logger.info("Reloaded PLC configuration with %d variables", len(self.config.variables))

    async def start(self) -> None:
        """Start the background polling task."""
        if self._running:
            logger.warning("PLCReaderService is already running.")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="plc_poll_worker")
        logger.info(
            "PLC Reader Service started (Poll Interval: %.2fs, Reconnect Interval: %.2fs)",
            self.poll_interval,
            self.reconnect_interval,
        )

    async def stop(self) -> None:
        """Stop the background polling task and disconnect from PLC."""
        if not self._running:
            return

        logger.info("Stopping PLC Reader Service...")
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Disconnect client
        await asyncio.to_thread(self.client.disconnect)
        self._latest_snapshot = PLCDataSnapshot(
            timestamp=datetime.now(timezone.utc),
            plc_connected=False,
            variables={},
            details={},
            errors={"system": "PLC service stopped"},
        )
        logger.info("PLC Reader Service stopped cleanly.")

    async def force_reconnect(self) -> bool:
        """Manually attempt an immediate reconnection to the PLC."""
        logger.info("Manual reconnection requested...")
        connected = await asyncio.to_thread(self.client.connect)
        return connected

    def get_status(self) -> PLCStatusResponse:
        """Generate current system and PLC status representation."""
        is_conn = self.client.is_connected
        cpu_info = self.client.get_cpu_info() if is_conn else None
        cpu_state = self.client.get_cpu_state() if is_conn else "OFFLINE"

        return PLCStatusResponse(
            connected=is_conn,
            ip=self.client.ip,
            rack=self.client.rack,
            slot=self.client.slot,
            port=self.client.port,
            poll_interval_seconds=self.poll_interval,
            reconnect_interval_seconds=self.reconnect_interval,
            total_configured_variables=len(self.config.variables),
            last_successful_read=self._last_successful_read,
            last_error=self.client.last_error,
            cpu_info=cpu_info,
            cpu_state=cpu_state,
        )

    async def _poll_loop(self) -> None:
        """Main async worker loop handling auto-reconnect and continuous polling."""
        while self._running:
            try:
                # 1. Connection check / Reconnect logic
                if not self.client.is_connected:
                    logger.info("Attempting to connect to Siemens PLC (%s)...", self.client.ip)
                    connected = await asyncio.to_thread(self.client.connect)
                    if not connected:
                        logger.warning(
                            "PLC connection attempt failed. Will retry in %.1f seconds...",
                            self.reconnect_interval,
                        )
                        # Publish disconnected snapshot
                        self._latest_snapshot = PLCDataSnapshot(
                            timestamp=datetime.now(timezone.utc),
                            plc_connected=False,
                            variables={},
                            details={},
                            errors={"connection": self.client.last_error or "PLC unreachable"},
                        )
                        await self._notify_subscribers(self._latest_snapshot)
                        await asyncio.sleep(self.reconnect_interval)
                        continue

                # 2. Read configured variables
                start_time = time.perf_counter()
                snapshot = await self._read_all_variables()
                duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                snapshot.poll_duration_ms = duration_ms

                self._latest_snapshot = snapshot
                if snapshot.plc_connected:
                    self._last_successful_read = snapshot.timestamp

                # 3. Broadcast to WebSockets
                await self._notify_subscribers(snapshot)

                # 4. Wait for next poll interval
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in PLC poll loop: %s", exc, exc_info=True)
                await asyncio.sleep(self.reconnect_interval)

    async def _read_all_variables(self) -> PLCDataSnapshot:
        """
        Perform a complete read cycle for all configured variables.
        Groups variables by DB to optimize network PDU requests.
        """
        now = datetime.now(timezone.utc)
        if not self.config.variables:
            return PLCDataSnapshot(
                timestamp=now,
                plc_connected=self.client.is_connected,
                variables={},
                details={},
                errors={},
            )

        variables_by_db: Dict[int, List[PLCVariableConfig]] = defaultdict(list)
        for var in self.config.variables:
            variables_by_db[var.db].append(var)

        parsed_variables: Dict[str, Union[float, int, bool, str, None]] = {}
        variable_details: Dict[str, PLCVariableValue] = {}
        variable_errors: Dict[str, str] = {}

        # Read each Data Block
        for db_num, db_vars in variables_by_db.items():
            try:
                # Determine memory span required for this DB
                min_byte = min(v.byte for v in db_vars)
                max_byte = max(v.byte + S7DataParser.get_required_byte_length(v) for v in db_vars)
                total_bytes_to_read = max_byte - min_byte

                # Execute read in threadpool so asyncio event loop stays non-blocking
                raw_bytes = await asyncio.to_thread(
                    self.client.read_db,
                    db_number=db_num,
                    start_byte=min_byte,
                    size=total_bytes_to_read,
                )

                # Parse each variable from the returned buffer
                for var in db_vars:
                    try:
                        scaled_val, raw_val = S7DataParser.parse_variable(
                            buffer=raw_bytes,
                            var_config=var,
                            buffer_start_offset=min_byte,
                        )
                        parsed_variables[var.name] = scaled_val
                        variable_details[var.name] = PLCVariableValue(
                            value=scaled_val,
                            raw_value=raw_val,
                            unit=var.unit,
                            quality="GOOD",
                            timestamp=now,
                            error=None,
                        )
                    except S7DataTypeError as parse_err:
                        error_msg = f"Parse error: {parse_err}"
                        parsed_variables[var.name] = None
                        variable_errors[var.name] = error_msg
                        variable_details[var.name] = PLCVariableValue(
                            value=None,
                            raw_value=None,
                            unit=var.unit,
                            quality="BAD",
                            timestamp=now,
                            error=error_msg,
                        )

            except Exception as db_err:
                logger.warning("Failed reading DB%d: %s", db_num, db_err)
                for var in db_vars:
                    error_msg = f"DB{db_num} read failed: {str(db_err)}"
                    parsed_variables[var.name] = None
                    variable_errors[var.name] = error_msg
                    variable_details[var.name] = PLCVariableValue(
                        value=None,
                        raw_value=None,
                        unit=var.unit,
                        quality="BAD",
                        timestamp=now,
                        error=error_msg,
                    )

        is_connected = self.client.is_connected
        return PLCDataSnapshot(
            timestamp=now,
            plc_connected=is_connected,
            variables=parsed_variables,
            details=variable_details,
            errors=variable_errors if variable_errors else None,
        )

    async def _notify_subscribers(self, snapshot: PLCDataSnapshot) -> None:
        """Broadcast data snapshot to all registered listeners asynchronously."""
        if not self._listeners:
            return

        # Snapshot copy of listeners to prevent modification during iteration
        listeners = list(self._listeners)
        coros = [listener(snapshot) for listener in listeners]
        if coros:
            # Shield individual listener failures from stopping the broadcast
            results = await asyncio.gather(*coros, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.debug("Subscriber notification error: %s", res)
