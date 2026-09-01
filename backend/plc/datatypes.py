"""Siemens S7 binary data type parsing, scaling, and conversions."""

import struct
from typing import Any, Optional, Tuple, Union
from backend.models.plc_data import DataTypeEnum, PLCVariableConfig


class S7DataTypeError(Exception):
    """Exception raised when binary parsing of S7 data types fails."""
    pass


class S7DataParser:
    """Parser for Siemens S7 Big-Endian binary memory buffers."""

    # Size requirements in bytes for each data type
    TYPE_SIZES = {
        DataTypeEnum.BOOL: 1,
        DataTypeEnum.BYTE: 1,
        DataTypeEnum.WORD: 2,
        DataTypeEnum.DWORD: 4,
        DataTypeEnum.INT: 2,
        DataTypeEnum.DINT: 4,
        DataTypeEnum.REAL: 4,
        DataTypeEnum.LREAL: 8,
    }

    @classmethod
    def get_required_byte_length(cls, var_config: PLCVariableConfig) -> int:
        """Calculate the total byte length needed in the memory buffer for a variable."""
        if var_config.type == DataTypeEnum.STRING:
            # S7 STRING: 1 byte max_len + 1 byte current_len + max_len characters
            max_len = var_config.string_max_length or 254
            return 2 + max_len
        return cls.TYPE_SIZES.get(var_config.type, 1)

    @staticmethod
    def get_bool(buffer: Union[bytes, bytearray], byte_offset: int, bit_offset: int) -> bool:
        """Extract a boolean value at a specific byte and bit offset (0-7)."""
        if byte_offset >= len(buffer):
            raise S7DataTypeError(
                f"Byte offset {byte_offset} out of bounds for buffer length {len(buffer)}"
            )
        if not (0 <= bit_offset <= 7):
            raise S7DataTypeError(f"Bit offset {bit_offset} must be between 0 and 7")
        
        byte_val = buffer[byte_offset]
        return bool(byte_val & (1 << bit_offset))

    @staticmethod
    def get_byte(buffer: Union[bytes, bytearray], byte_offset: int) -> int:
        """Extract an unsigned 8-bit integer (BYTE / USINT)."""
        if byte_offset >= len(buffer):
            raise S7DataTypeError(
                f"Byte offset {byte_offset} out of bounds for buffer length {len(buffer)}"
            )
        return buffer[byte_offset]

    @staticmethod
    def get_word(buffer: Union[bytes, bytearray], byte_offset: int) -> int:
        """Extract an unsigned 16-bit integer (WORD / UINT) using Big-Endian byte order."""
        if byte_offset + 2 > len(buffer):
            raise S7DataTypeError(
                f"Need 2 bytes at offset {byte_offset}, but buffer length is {len(buffer)}"
            )
        return struct.unpack_from(">H", buffer, byte_offset)[0]

    @staticmethod
    def get_dword(buffer: Union[bytes, bytearray], byte_offset: int) -> int:
        """Extract an unsigned 32-bit integer (DWORD / UDINT) using Big-Endian byte order."""
        if byte_offset + 4 > len(buffer):
            raise S7DataTypeError(
                f"Need 4 bytes at offset {byte_offset}, but buffer length is {len(buffer)}"
            )
        return struct.unpack_from(">I", buffer, byte_offset)[0]

    @staticmethod
    def get_int(buffer: Union[bytes, bytearray], byte_offset: int) -> int:
        """Extract a signed 16-bit integer (INT) using Big-Endian byte order."""
        if byte_offset + 2 > len(buffer):
            raise S7DataTypeError(
                f"Need 2 bytes at offset {byte_offset}, but buffer length is {len(buffer)}"
            )
        return struct.unpack_from(">h", buffer, byte_offset)[0]

    @staticmethod
    def get_dint(buffer: Union[bytes, bytearray], byte_offset: int) -> int:
        """Extract a signed 32-bit integer (DINT) using Big-Endian byte order."""
        if byte_offset + 4 > len(buffer):
            raise S7DataTypeError(
                f"Need 4 bytes at offset {byte_offset}, but buffer length is {len(buffer)}"
            )
        return struct.unpack_from(">i", buffer, byte_offset)[0]

    @staticmethod
    def get_real(buffer: Union[bytes, bytearray], byte_offset: int) -> float:
        """Extract a 32-bit IEEE-754 single-precision float (REAL) using Big-Endian byte order."""
        if byte_offset + 4 > len(buffer):
            raise S7DataTypeError(
                f"Need 4 bytes at offset {byte_offset}, but buffer length is {len(buffer)}"
            )
        val = struct.unpack_from(">f", buffer, byte_offset)[0]
        # Return clean rounded float to prevent IEEE-754 representation noise (e.g. 12.400000095)
        return round(val, 6)

    @staticmethod
    def get_lreal(buffer: Union[bytes, bytearray], byte_offset: int) -> float:
        """Extract a 64-bit IEEE-754 double-precision float (LREAL) using Big-Endian byte order."""
        if byte_offset + 8 > len(buffer):
            raise S7DataTypeError(
                f"Need 8 bytes at offset {byte_offset}, but buffer length is {len(buffer)}"
            )
        val = struct.unpack_from(">d", buffer, byte_offset)[0]
        return round(val, 8)

    @staticmethod
    def get_string(
        buffer: Union[bytes, bytearray],
        byte_offset: int,
        max_length: Optional[int] = None
    ) -> str:
        """
        Extract a Siemens S7 STRING.
        Siemens S7 STRING format in DB:
          - Byte 0: Max length allocated in PLC (e.g. 254)
          - Byte 1: Current actual string length
          - Byte 2 .. 2+len-1: String ASCII characters
        """
        if byte_offset + 2 > len(buffer):
            raise S7DataTypeError(
                f"Need at least 2 header bytes for STRING at offset {byte_offset}, buffer is {len(buffer)}"
            )
        
        max_len = buffer[byte_offset]
        current_len = buffer[byte_offset + 1]

        # Sanity validation on lengths
        if max_length is not None:
            max_len = min(max_len, max_length)
        
        actual_len = min(current_len, max_len)

        if byte_offset + 2 + actual_len > len(buffer):
            raise S7DataTypeError(
                f"String payload ({actual_len} chars) exceeds buffer length {len(buffer)} at offset {byte_offset}"
            )

        chars = buffer[byte_offset + 2 : byte_offset + 2 + actual_len]
        return chars.decode("latin-1", errors="replace").strip("\x00")

    @classmethod
    def parse_variable(
        cls,
        buffer: Union[bytes, bytearray],
        var_config: PLCVariableConfig,
        buffer_start_offset: int = 0
    ) -> Tuple[Union[float, int, bool, str], Union[float, int, bool, str]]:
        """
        Parse raw binary buffer into (parsed_value, raw_value).
        
        :param buffer: Raw byte array from PLC db_read
        :param var_config: Variable configuration
        :param buffer_start_offset: The DB starting byte offset that this buffer corresponds to
        :return: Tuple of (scaled_value, raw_value)
        """
        rel_offset = var_config.byte - buffer_start_offset
        if rel_offset < 0:
            raise S7DataTypeError(
                f"Variable '{var_config.name}' byte offset {var_config.byte} precedes buffer start {buffer_start_offset}"
            )

        var_type = var_config.type
        raw_val: Any

        if var_type == DataTypeEnum.BOOL:
            bit_idx = var_config.bit if var_config.bit is not None else 0
            raw_val = cls.get_bool(buffer, rel_offset, bit_idx)
            return raw_val, raw_val

        elif var_type == DataTypeEnum.BYTE:
            raw_val = cls.get_byte(buffer, rel_offset)
        elif var_type == DataTypeEnum.WORD:
            raw_val = cls.get_word(buffer, rel_offset)
        elif var_type == DataTypeEnum.DWORD:
            raw_val = cls.get_dword(buffer, rel_offset)
        elif var_type == DataTypeEnum.INT:
            raw_val = cls.get_int(buffer, rel_offset)
        elif var_type == DataTypeEnum.DINT:
            raw_val = cls.get_dint(buffer, rel_offset)
        elif var_type == DataTypeEnum.REAL:
            raw_val = cls.get_real(buffer, rel_offset)
        elif var_type == DataTypeEnum.LREAL:
            raw_val = cls.get_lreal(buffer, rel_offset)
        elif var_type == DataTypeEnum.STRING:
            raw_val = cls.get_string(buffer, rel_offset, var_config.string_max_length)
            return raw_val, raw_val
        else:
            raise S7DataTypeError(f"Unsupported data type '{var_type}' for variable '{var_config.name}'")

        # Apply scaling and offset if configured and numeric
        scaled_val = raw_val
        if isinstance(raw_val, (int, float)):
            if var_config.scale is not None:
                scaled_val = scaled_val * var_config.scale
            if var_config.offset is not None:
                scaled_val = scaled_val + var_config.offset
            if isinstance(scaled_val, float):
                scaled_val = round(scaled_val, 6)

        return scaled_val, raw_val
