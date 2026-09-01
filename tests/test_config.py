"""Unit tests for configuration loading and validation."""

import json
import pytest
from backend.config import load_plc_variable_config
from backend.models.plc_data import DataTypeEnum, PLCConfigFile, PLCVariableConfig


def test_load_default_config():
    config = load_plc_variable_config("config/plc_config.json")
    assert len(config.variables) > 0
    assert any(v.name == "voltage" for v in config.variables)
    assert any(v.type == DataTypeEnum.BOOL for v in config.variables)


def test_duplicate_variable_name_fails():
    with pytest.raises(ValueError, match="Duplicate variable name"):
        PLCConfigFile(
            variables=[
                PLCVariableConfig(name="duplicate", db=1, byte=0, type=DataTypeEnum.REAL),
                PLCVariableConfig(name="duplicate", db=1, byte=4, type=DataTypeEnum.REAL),
            ]
        )


def test_bool_missing_bit_fails():
    with pytest.raises(ValueError, match="bit' offset"):
        PLCVariableConfig(name="bool_tag", db=1, byte=0, type=DataTypeEnum.BOOL, bit=None)
