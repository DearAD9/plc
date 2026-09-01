"""WebSocket connection management and streaming endpoints."""

import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.models.plc_data import PLCDataSnapshot

logger = logging.getLogger("api.websocket")
ws_router = APIRouter(tags=["WebSocket"])


class WebSocketManager:
    """Manages active WebSocket client connections and message broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    @property
    def count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection and track it."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total active clients: %d", self.count)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected WebSocket from active pool."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Remaining clients: %d", self.count)

    async def broadcast_snapshot(self, snapshot: PLCDataSnapshot) -> None:
        """Broadcast PLC data snapshot to all active connected clients."""
        if not self.active_connections:
            return

        # Serialize Pydantic model to JSON string with ISO datetime formatting
        message_json = snapshot.model_dump_json()

        # Iterate over copy of connection set
        disconnected = []
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message_json)
            except Exception as exc:
                logger.debug("Failed sending update to client: %s", exc)
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)


ws_manager = WebSocketManager()


def create_websocket_route(reader_service):
    """
    Creates and attaches the WebSocket endpoint using the given PLCReaderService.
    """
    @ws_router.websocket("/ws/plc")
    async def websocket_plc_stream(websocket: WebSocket):
        """
        Real-time WebSocket stream for Siemens PLC tag data.
        Streams updated tag values whenever the backend polling cycle completes.
        """
        await ws_manager.connect(websocket)

        # Immediately send current state on initial connection
        try:
            current_snapshot = reader_service.latest_snapshot
            await websocket.send_text(current_snapshot.model_dump_json())
        except Exception as exc:
            logger.debug("Failed to send initial snapshot: %s", exc)

        try:
            while True:
                # Keep connection open and listen for optional incoming client messages/pings
                data = await websocket.receive_text()
                # If client sends a ping or custom request, acknowledge it
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif data == "status":
                    status = reader_service.get_status()
                    await websocket.send_text(status.model_dump_json())
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception as exc:
            logger.debug("WebSocket exception: %s", exc)
            ws_manager.disconnect(websocket)

    return ws_router
