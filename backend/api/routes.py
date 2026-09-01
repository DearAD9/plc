"""REST API route handlers for PLC status, data, variables, and reconnection."""

from datetime import datetime, timezone
import logging
from typing import List
from fastapi import APIRouter

from backend.models.plc_data import (
    HealthResponse,
    PLCDataSnapshot,
    PLCStatusResponse,
    PLCVariableConfig,
)
from backend.api.websocket import ws_manager

logger = logging.getLogger("api.routes")
api_router = APIRouter(prefix="/api", tags=["PLC API"])


def get_reader_service():
    """Dependency provider for PLCReaderService. Will be overridden or injected in main."""
    raise NotImplementedError("PLCReaderService dependency not bound.")


def create_api_router(reader_service) -> APIRouter:
    """Factory creating API routes bound to a specific PLCReaderService instance."""
    router = APIRouter(prefix="/api")

    @router.get(
        "/health",
        response_model=HealthResponse,
        summary="Backend & PLC Health Check",
        tags=["System"],
    )
    async def get_health():
        """
        Diagnostic health check endpoint providing backend uptime and PLC connection health.
        """
        is_connected = reader_service.client.is_connected
        return HealthResponse(
            status="ok" if is_connected else "degraded",
            backend_running=True,
            plc_connected=is_connected,
            timestamp=datetime.now(timezone.utc),
            active_websocket_connections=ws_manager.count,
        )

    @router.get(
        "/plc/status",
        response_model=PLCStatusResponse,
        summary="Get PLC Connection Status",
        tags=["PLC"],
    )
    async def get_plc_status():
        """
        Returns full diagnostic status of the Siemens PLC connection, rack, slot, and hardware details.
        """
        return reader_service.get_status()

    @router.get(
        "/plc/data",
        response_model=PLCDataSnapshot,
        summary="Get Latest Polled PLC Data",
        tags=["PLC"],
    )
    async def get_plc_data(include_details: bool = False):
        """
        Retrieve the latest engineering values parsed from the PLC Data Blocks.
        
        - **include_details**: If true, returns individual tag metadata, raw values, and qualities.
        """
        snapshot = reader_service.latest_snapshot
        if not include_details and snapshot.details:
            # Return slimmed snapshot without verbose details dict
            return PLCDataSnapshot(
                timestamp=snapshot.timestamp,
                plc_connected=snapshot.plc_connected,
                poll_duration_ms=snapshot.poll_duration_ms,
                variables=snapshot.variables,
                details=None,
                errors=snapshot.errors,
            )
        return snapshot

    @router.get(
        "/plc/variables",
        response_model=List[PLCVariableConfig],
        summary="Get List of Configured PLC Variables",
        tags=["PLC"],
    )
    async def get_plc_variables():
        """
        Returns the active configuration of all PLC tags (DB numbers, byte offsets, data types, units).
        """
        return reader_service.config.variables

    @router.post(
        "/plc/reconnect",
        summary="Trigger Manual PLC Reconnection",
        tags=["PLC"],
    )
    async def trigger_reconnect():
        """
        Triggers an immediate attempt to reconnect to the Siemens PLC.
        """
        success = await reader_service.force_reconnect()
        return {
            "success": success,
            "connected": reader_service.client.is_connected,
            "ip": reader_service.client.ip,
            "message": "Connected successfully" if success else f"Connection failed: {reader_service.client.last_error}",
        }

    return router
