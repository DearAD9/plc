"""Application configuration and environment variable loader."""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.models.plc_data import PLCConfigFile, PLCVariableConfig

logger = logging.getLogger("plc.config")


class Settings(BaseSettings):
    """Application Settings loaded from environment or .env file."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # PLC Connection Settings
    plc_ip: str = Field(default="192.168.0.100", validation_alias="PLC_IP")
    plc_rack: int = Field(default=0, validation_alias="PLC_RACK")
    plc_slot: int = Field(default=1, validation_alias="PLC_SLOT")
    plc_port: int = Field(default=102, validation_alias="PLC_PORT")
    plc_timeout_ms: int = Field(default=5000, validation_alias="PLC_TIMEOUT_MS")

    # Polling & Reconnection Settings
    plc_poll_interval: float = Field(default=1.0, validation_alias="PLC_POLL_INTERVAL")
    plc_reconnect_interval: float = Field(default=5.0, validation_alias="PLC_RECONNECT_INTERVAL")

    # Configuration file path
    config_path: str = Field(default="config/plc_config.json", validation_alias="CONFIG_PATH")

    # Server settings
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    cors_origins: List[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")


# Global settings instance
settings = Settings()


def load_plc_variable_config(filepath: Optional[str] = None) -> PLCConfigFile:
    """Load and validate the PLC variable configuration JSON file."""
    path_to_load = Path(filepath or settings.config_path)
    
    if not path_to_load.is_absolute():
        # Resolve relative to current working directory or backend root
        base_dir = Path.cwd()
        path_to_load = base_dir / path_to_load

    if not path_to_load.exists():
        logger.warning("Configuration file not found at '%s'. Using empty variable list.", path_to_load)
        return PLCConfigFile(description="Empty fallback config", variables=[])

    try:
        with open(path_to_load, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = PLCConfigFile.model_validate(data)
        logger.info("Successfully loaded %d PLC variables from '%s'", len(config.variables), path_to_load)
        return config
    except json.JSONDecodeError as exc:
        logger.error("JSON syntax error in '%s': %s", path_to_load, exc)
        raise
    except Exception as exc:
        logger.error("Failed to parse PLC configuration from '%s': %s", path_to_load, exc)
        raise
