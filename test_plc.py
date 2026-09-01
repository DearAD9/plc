"""Standalone Command-Line Diagnostic & Connection Test Utility for Siemens S7 PLC."""

import json
import os
import socket
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.config import settings, load_plc_variable_config
from backend.plc.client import PLCClient, SNAP7_AVAILABLE
from backend.plc.datatypes import S7DataParser, S7DataTypeError


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def check_tcp_port(ip: str, port: int = 102, timeout: float = 3.0) -> bool:
    """Test raw TCP socket connectivity to ISO-on-TCP port 102."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def run_diagnostic():
    print_banner("Siemens S7 PLC Diagnostic & Connection Tester")
    
    ip = settings.plc_ip
    rack = settings.plc_rack
    slot = settings.plc_slot
    port = settings.plc_port

    print(f" Target Configuration:")
    print(f"   * PLC IP Address : {ip}")
    print(f"   * PLC Rack       : {rack}")
    print(f"   * PLC Slot       : {slot}")
    print(f"   * Port           : {port} (ISO-on-TCP)")
    print(f"   * Config File    : {settings.config_path}")
    print("-" * 70)

    # 1. Check Python Snap7 library
    print(f" [1/4] Checking python-snap7 library...")
    if not SNAP7_AVAILABLE:
        print("   [FAILED] python-snap7 is not installed or snap7.dll is missing.")
        print("   -> Install with: pip install python-snap7")
        print("   -> On Windows, ensure snap7.dll is in PATH or Python environment.")
        return 1
    print("   [OK] python-snap7 library is available.")

    # 2. Check Network Port Reachability
    print(f"\n [2/4] Testing TCP reachability ({ip}:{port})...")
    is_port_open = check_tcp_port(ip, port)
    if is_port_open:
        print(f"   [OK] Port {port} is OPEN and reachable on {ip}.")
    else:
        print(f"   [WARNING] Cannot open TCP connection to {ip}:{port}.")
        print("   Possible reasons:")
        print("     1. PLC is powered off or disconnected.")
        print("     2. PC and PLC are on different subnets (e.g. PC: 192.168.1.x, PLC: 192.168.0.x).")
        print("     3. Windows Firewall or router blocking port 102.")

    # 3. Attempt Snap7 Connection
    print(f"\n [3/4] Establishing Snap7 S7 protocol connection...")
    client = PLCClient(ip=ip, rack=rack, slot=slot, port=port)
    connected = client.connect()

    if not connected:
        print(f"   [FAILED] Could not connect to PLC: {client.last_error}")
        print("\n Diagnostic Recommendations:")
        print("   * Verify PLC IP: Ping test with 'ping " + ip + "'")
        print("   * For S7-1200 / S7-1500:")
        print("       - In TIA Portal -> PLC Properties -> Protection & Security -> Connection mechanisms:")
        print("         ENABLE 'Permit access with PUT/GET communication from remote partner'")
        print("   * For S7-300 / S7-400:")
        print("       - Typically Rack 0, Slot 2 (CPU)")
        print("   * For S7-1200 / S7-1500:")
        print("       - Typically Rack 0, Slot 1 (CPU)")
        return 1

    print(f"   [OK] Connected to PLC at {ip} successfully!")

    # CPU State and Info
    cpu_state = client.get_cpu_state()
    cpu_info = client.get_cpu_info()
    print(f"   * PLC CPU State  : {cpu_state}")
    if cpu_info:
        print(f"   * Module Type    : {cpu_info.get('module_type_name', 'N/A')}")
        print(f"   * Serial Number  : {cpu_info.get('serial_number', 'N/A')}")
        print(f"   * AS Name        : {cpu_info.get('as_name', 'N/A')}")
        print(f"   * Order Code     : {cpu_info.get('order_code', 'N/A')}")

    # 4. Test Variable Reads from Configuration
    print(f"\n [4/4] Testing Data Block reads from configuration...")
    try:
        config = load_plc_variable_config()
    except Exception as exc:
        print(f"   [FAILED] Could not load config: {exc}")
        client.disconnect()
        return 1

    if not config.variables:
        print("   [INFO] No variables configured in configuration file.")
        client.disconnect()
        return 0

    print(f"   Loaded {len(config.variables)} variable definitions. Executing test reads:\n")
    print(f"   {'Variable Name':<20} | {'Address':<12} | {'Type':<8} | {'Value':<18} | {'Unit':<6} | {'Status'}")
    print("   " + "-" * 75)

    success_count = 0
    fail_count = 0

    for var in config.variables:
        addr_str = f"DB{var.db}.DBX{var.byte}.{var.bit}" if var.type.value == "BOOL" else f"DB{var.db}.DBD{var.byte}" if var.type.value in ["REAL", "DWORD", "DINT"] else f"DB{var.db}.DBW{var.byte}"
        req_len = S7DataParser.get_required_byte_length(var)

        try:
            raw_bytes = client.read_db(var.db, var.byte, req_len)
            scaled_val, raw_val = S7DataParser.parse_variable(raw_bytes, var, buffer_start_offset=var.byte)
            unit_str = var.unit or ""
            val_display = str(scaled_val) if scaled_val is not None else "None"
            print(f"   {var.name:<20} | {addr_str:<12} | {var.type.value:<8} | {val_display:<18} | {unit_str:<6} | [OK]")
            success_count += 1
        except Exception as read_err:
            print(f"   {var.name:<20} | {addr_str:<12} | {var.type.value:<8} | {'ERROR':<18} | {'':<6} | [FAILED]")
            print(f"     -> Error details: {read_err}")
            fail_count += 1

    print("   " + "-" * 75)
    print(f"   Summary: {success_count} read successfully, {fail_count} failed.")

    if fail_count > 0:
        print("\n Notes for failed Data Block reads:")
        print("   * In TIA Portal, open the Data Block properties -> Attributes:")
        print("     UNCHECK 'Optimized block access' so standard byte offset addressing is available.")
        print("   * Verify that the DB number exists on the PLC and has sufficient allocated length.")

    # Clean shutdown
    client.disconnect()
    print_banner("Diagnostic Complete")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    exit_code = run_diagnostic()
    sys.exit(exit_code)
