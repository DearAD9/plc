"""Pydantic models for PLC configuration, tag data, and API payloads."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class DataTypeEnum(str, Enum):
    """Supported Siemens S7 Data Types."""
    BOOL = "BOOL"
    BYTE = "BYTE"
    WORD = "WORD"
    DWORD = "DWORD"
    INT = "INT"
    DINT = "DINT"
    REAL = "REAL"
    LREAL = "LREAL"
    STRING = "STRING"


class PLCVariableConfig(BaseModel):
    """Configuration for a single PLC variable / tag to read from a Data Block."""
    name: str = Field(..., description="Unique human-readable identifier for the variable")
    db: int = Field(..., ge=1, description="Data Block number (e.g. 1 for DB1)")
    byte: int = Field(..., ge=0, description="Start byte offset within the Data Block")
    bit: Optional[int] = Field(None, ge=0, le=7, description="Bit offset (0-7), required when type is BOOL")
    type: DataTypeEnum = Field(..., description="Siemens S7 data type")
    string_max_length: Optional[int] = Field(254, ge=1, le=254, description="Max character length for STRING data type")
    scale: Optional[float] = Field(None, description="Optional multiplier scaling factor (e.g. 0.1)")
    offset: Optional[float] = Field(None, description="Optional offset added after scaling")
    unit: Optional[str] = Field(None, description="Engineering unit (e.g. 'V', 'kW', '°C')")
    description: Optional[str] = Field(None, description="Optional variable description")

    @model_validator(mode="after")
    def validate_variable(self) -> "PLCVariableConfig":
        if self.type == DataTypeEnum.BOOL and self.bit is None:
            raise ValueError(f"Variable '{self.name}' has type BOOL but 'bit' offset (0-7) is missing.")
        return self


class PLCConfigFile(BaseModel):
    """Structure of the JSON configuration file."""
    description: Optional[str] = Field("PLC Variable Configuration", description="Description of the configuration file")
    variables: List[PLCVariableConfig] = Field(default_factory=list, description="List of configured PLC variables")

    @field_validator("variables")
    @classmethod
    def validate_unique_names(cls, vars_list: List[PLCVariableConfig]) -> List[PLCVariableConfig]:
        names = set()
        for v in vars_list:
            if v.name in names:
                raise ValueError(f"Duplicate variable name '{v.name}' found in configuration.")
            names.add(v.name)
        return vars_list


class PLCVariableValue(BaseModel):
    """Detailed value structure for an individual PLC variable."""
    value: Union[float, int, bool, str, None] = Field(None, description="Parsed (and scaled) value")
    raw_value: Union[float, int, bool, str, None] = Field(None, description="Raw unscaled value from PLC memory")
    unit: Optional[str] = Field(None, description="Engineering unit")
    quality: str = Field("GOOD", description="Data quality: GOOD, BAD, or UNCERTAIN")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the read")
    error: Optional[str] = Field(None, description="Error message if reading this specific tag failed")


class PLCDataSnapshot(BaseModel):
    """Global snapshot of all configured PLC variables returned by REST / WebSockets."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the read cycle")
    plc_connected: bool = Field(False, description="True if the PLC is actively connected and reachable")
    poll_duration_ms: Optional[float] = Field(None, description="Time taken to read all variables in milliseconds")
    variables: Dict[str, Union[float, int, bool, str, None]] = Field(
        default_factory=dict,
        description="Clean key-value mapping of variable names to parsed engineering values"
    )
    details: Optional[Dict[str, PLCVariableValue]] = Field(
        None,
        description="Optional extended metadata and qualities per variable"
    )
    errors: Optional[Dict[str, str]] = Field(
        None,
        description="Dictionary of variable names to error descriptions if any individual read failed"
    )


class PLCStatusResponse(BaseModel):
    """Status endpoint response model."""
    connected: bool = Field(..., description="PLC connection status")
    ip: str = Field(..., description="Configured PLC IP address")
    rack: int = Field(..., description="Configured Rack number")
    slot: int = Field(..., description="Configured Slot number")
    port: int = Field(..., description="Configured S7 port (default 102)")
    poll_interval_seconds: float = Field(..., description="Configured polling frequency")
    reconnect_interval_seconds: float = Field(..., description="Configured reconnect retry interval")
    total_configured_variables: int = Field(..., description="Number of variables loaded from configuration")
    last_successful_read: Optional[datetime] = Field(None, description="Timestamp of the most recent successful read")
    last_error: Optional[str] = Field(None, description="Last recorded error message, if any")
    cpu_info: Optional[Dict[str, Any]] = Field(None, description="Siemens CPU module info if connected")
    cpu_state: Optional[str] = Field(None, description="PLC state: RUN, STOP, UNKNOWN")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field("ok", description="Overall backend health: 'ok' or 'degraded'")
    backend_running: bool = Field(True, description="Backend process status")
    plc_connected: bool = Field(..., description="PLC connection status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Current server UTC timestamp")
    active_websocket_connections: int = Field(0, description="Count of connected WebSocket clients")
