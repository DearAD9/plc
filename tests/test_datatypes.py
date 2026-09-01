"""Unit tests for Siemens S7 data type parsers and scalers."""

import struct
import pytest
from backend.models.plc_data import DataTypeEnum, PLCVariableConfig
from backend.plc.datatypes import S7DataParser, S7DataTypeError


def test_parse_bool():
    # Byte value 0b00000101 = 5 (bit 0 = True, bit 1 = False, bit 2 = True)
    buffer = bytearray([0b00000101])
    
    var_bit0 = PLCVariableConfig(name="bit0", db=1, byte=0, bit=0, type=DataTypeEnum.BOOL)
    var_bit1 = PLCVariableConfig(name="bit1", db=1, byte=0, bit=1, type=DataTypeEnum.BOOL)
    var_bit2 = PLCVariableConfig(name="bit2", db=1, byte=0, bit=2, type=DataTypeEnum.BOOL)

    val0, _ = S7DataParser.parse_variable(buffer, var_bit0)
    val1, _ = S7DataParser.parse_variable(buffer, var_bit1)
    val2, _ = S7DataParser.parse_variable(buffer, var_bit2)

    assert val0 is True
    assert val1 is False
    assert val2 is True


def test_parse_byte_and_int():
    # Byte 250, INT -1234
    buffer = bytearray([250]) + bytearray(struct.pack(">h", -1234))
    
    var_byte = PLCVariableConfig(name="b_val", db=1, byte=0, type=DataTypeEnum.BYTE)
    var_int = PLCVariableConfig(name="i_val", db=1, byte=1, type=DataTypeEnum.INT)

    val_b, _ = S7DataParser.parse_variable(buffer, var_byte)
    val_i, _ = S7DataParser.parse_variable(buffer, var_int)

    assert val_b == 250
    assert val_i == -1234


def test_parse_dint_and_word_dword():
    # Word 65500, DWORD 4000000, DINT -500000
    b_word = struct.pack(">H", 65500)
    b_dword = struct.pack(">I", 4000000)
    b_dint = struct.pack(">i", -500000)
    buffer = bytearray(b_word + b_dword + b_dint)

    var_word = PLCVariableConfig(name="w", db=1, byte=0, type=DataTypeEnum.WORD)
    var_dword = PLCVariableConfig(name="dw", db=1, byte=2, type=DataTypeEnum.DWORD)
    var_dint = PLCVariableConfig(name="di", db=1, byte=6, type=DataTypeEnum.DINT)

    assert S7DataParser.parse_variable(buffer, var_word)[0] == 65500
    assert S7DataParser.parse_variable(buffer, var_dword)[0] == 4000000
    assert S7DataParser.parse_variable(buffer, var_dint)[0] == -500000


def test_parse_real_and_lreal_with_scaling():
    # REAL 230.5 with scale 0.5, LREAL 12345.6789
    b_real = struct.pack(">f", 230.5)
    b_lreal = struct.pack(">d", 12345.6789)
    buffer = bytearray(b_real + b_lreal)

    var_real_scaled = PLCVariableConfig(
        name="voltage_scaled", db=1, byte=0, type=DataTypeEnum.REAL, scale=0.5, offset=10.0
    )
    var_lreal = PLCVariableConfig(
        name="energy", db=1, byte=4, type=DataTypeEnum.LREAL
    )

    scaled_val, raw_val = S7DataParser.parse_variable(buffer, var_real_scaled)
    # raw is 230.5; scaled is 230.5 * 0.5 + 10 = 115.25 + 10 = 125.25
    assert raw_val == 230.5
    assert scaled_val == 125.25

    lreal_val, _ = S7DataParser.parse_variable(buffer, var_lreal)
    assert lreal_val == 12345.6789


def test_parse_s7_string():
    # S7 string: Max length 16, current length 5, chars 'HELLO'
    text = "HELLO"
    header = bytes([16, len(text)])
    payload = text.encode("ascii")
    buffer = bytearray(header + payload)

    var_str = PLCVariableConfig(
        name="recipe", db=1, byte=0, type=DataTypeEnum.STRING, string_max_length=16
    )

    parsed_str, raw_str = S7DataParser.parse_variable(buffer, var_str)
    assert parsed_str == "HELLO"
    assert raw_str == "HELLO"


def test_out_of_bounds_handling():
    buffer = bytearray([1, 2])
    var_real = PLCVariableConfig(name="too_short", db=1, byte=0, type=DataTypeEnum.REAL)
    
    with pytest.raises(S7DataTypeError):
        S7DataParser.parse_variable(buffer, var_real)
