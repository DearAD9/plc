"""FastAPI Application entry point for Siemens Snap7 PLC Communication Service."""

from contextlib import asynccontextmanager
import logging
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings, load_plc_variable_config
from backend.plc.client import PLCClient
from backend.plc.reader import PLCReaderService
from backend.api.routes import create_api_router
from backend.api.websocket import ws_manager, create_websocket_route

# ==============================================================================
# Logging Configuration
# ==============================================================================
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)-14s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("backend.main")

# ==============================================================================
# Service Initialization
# ==============================================================================
config_file = load_plc_variable_config()

plc_client = PLCClient(
    ip=settings.plc_ip,
    rack=settings.plc_rack,
    slot=settings.plc_slot,
    port=settings.plc_port,
    timeout_ms=settings.plc_timeout_ms,
)

plc_reader = PLCReaderService(
    client=plc_client,
    config=config_file,
    poll_interval=settings.plc_poll_interval,
    reconnect_interval=settings.plc_reconnect_interval,
)

# Connect PLCReader updates directly to WebSocket broadcaster
plc_reader.subscribe(ws_manager.broadcast_snapshot)


# ==============================================================================
# Lifespan Management (Startup & Shutdown)
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager handling startup tasks and clean shutdown."""
    logger.info("=" * 60)
    logger.info("Siemens PLC Snap7 Communication Service Starting")
    logger.info("Target PLC: %s (Rack: %d, Slot: %d, Port: %d)", settings.plc_ip, settings.plc_rack, settings.plc_slot, settings.plc_port)
    logger.info("Poll Interval: %.2fs | Reconnect Interval: %.2fs", settings.plc_poll_interval, settings.plc_reconnect_interval)
    logger.info("=" * 60)

    # Start background polling service
    await plc_reader.start()

    yield

    # Graceful shutdown
    logger.info("Shutting down Siemens PLC Service...")
    await plc_reader.stop()
    logger.info("Shutdown complete.")


# ==============================================================================
# FastAPI App Creation
# ==============================================================================
app = FastAPI(
    title="Siemens S7 PLC Communication API",
    description=(
        "Production-ready REST and WebSocket API service for communicating with "
        "Siemens S7-300 / S7-400 / S7-1200 / S7-1500 PLCs via Snap7 protocol (Read-Only)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration for frontend dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST Routes and WebSocket Routes
app.include_router(create_api_router(plc_reader))
app.include_router(create_websocket_route(plc_reader))


@app.get("/", tags=["System"])
async def root():
    """Service metadata and quick links."""
    return JSONResponse(
        content={
            "service": "Siemens S7 PLC Communication API",
            "version": "1.0.0",
            "documentation": "/docs",
            "health_endpoint": "/api/health",
            "plc_status_endpoint": "/api/plc/status",
            "plc_data_endpoint": "/api/plc/data",
            "websocket_endpoint": "/ws/plc",
            "target_plc": {
                "ip": settings.plc_ip,
                "rack": settings.plc_rack,
                "slot": settings.plc_slot,
                "port": settings.plc_port,
            },
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
