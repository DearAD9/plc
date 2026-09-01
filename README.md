# Siemens S7 PLC Communication Service (Snap7 + FastAPI)

A production-ready, read-only Siemens PLC communication backend built with **Python 3.11+**, **Snap7** (`python-snap7`), **FastAPI**, **WebSockets**, and **Pydantic**. 

Continuously polls configured Siemens Data Blocks (DB), parses S7 binary data types (BOOL, BYTE, WORD, DWORD, INT, DINT, REAL, LREAL, STRING), applies scaling/offsets, and streams clean JSON data via REST APIs and WebSockets to modern dashboards (React, Next.js, Vue, etc.).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Siemens S7 PLC                          │
│   (S7-1200 / S7-1500 / S7-300 / S7-400 / ET200 / Logo)  │
│                   192.168.0.100                         │
└────────────────────────────┬────────────────────────────┘
                             │  ISO-on-TCP (Port 102)
                             │  Snap7 Protocol (Read-Only)
┌────────────────────────────▼────────────────────────────┐
│              PLC Communication Service                  │
│                                                         │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │   PLCClient Wrapper  │    │   S7 Binary Parser   │  │
│  │  (Auto-Reconnect,    │───►│ (Big-Endian Unpacker,│  │
│  │   Thread-Safe Lock)  │    │  Scaling & Offsets)  │  │
│  └──────────────────────┘    └──────────────────────┘  │
│             │                                           │
│  ┌──────────▼───────────┐    ┌──────────────────────┐  │
│  │  PLCReader Poller    │───►│  In-Memory Snapshot  │  │
│  │  (Async Background)  │    │  (Cached State)      │  │
│  └──────────┬───────────┘    └──────────┬───────────┘  │
└─────────────┼───────────────────────────┼───────────────┘
              │                           │
   WebSocket Updates (JSON)        REST API Requests
              │                           │
┌─────────────▼───────────────────────────▼───────────────┐
│             Web Dashboard / Client Applications         │
│               (React / Next.js / Python / BI)           │
└─────────────────────────────────────────────────────────┘
```

---

## Siemens PLC & TIA Portal Prerequisites

For modern Siemens PLCs (**S7-1200** and **S7-1500**), two settings are mandatory in TIA Portal:

### 1. Enable PUT/GET Communication
1. Open your project in **TIA Portal**.
2. Double-click the PLC under **Device configuration**.
3. In the Inspector window at the bottom, select **Properties** -> **Protection & Security** -> **Connection mechanisms**.
4. Check **"Permit access with PUT/GET communication from remote partner"**.
5. Download hardware configuration to the PLC.

### 2. Disable "Optimized Block Access" for Data Blocks
Snap7 accesses memory by direct byte offsets (`DB1.DBD0`, `DB1.DBX16.0`, etc.).
1. Right-click the Data Block (e.g., `DB1`) in the project tree -> **Properties**.
2. Select **Attributes**.
3. **Uncheck** the box for **"Optimized block access"** (standard block access will be enabled).
4. Re-compile and download the Data Block to the PLC.

---

## Siemens Rack and Slot Reference

| PLC Family | Typical Rack | Typical Slot | Notes |
| :--- | :---: | :---: | :--- |
| **S7-1200** | `0` | `1` | Default configuration |
| **S7-1500** | `0` | `1` | Default configuration |
| **S7-300** | `0` | `2` | CPU is always located in Slot 2 |
| **S7-400** | `0` | `2` or `3` | Depending on power supply module width |
| **LOGO! 0BA7/0BA8** | `0` | `0` | TSAP configured as 0x2000 / 0x0200 |
| **WinAC RTX** | `0` | `2` | Software PLC |

---

## Network Requirements

The host PC and the PLC must reside on the same IP subnet or have an active routing path.

* **PLC IP**: `192.168.0.100` (Subnet mask: `255.255.255.0`)
* **Host PC IP**: e.g., `192.168.0.50` (Subnet mask: `255.255.255.0`)

### Connectivity Check
Open PowerShell / Command Prompt:
```powershell
ping 192.168.0.100
```
> [!NOTE]
> A successful `ping` confirms IP reachability, but does not guarantee Snap7 access (firewalls may block port 102, or PUT/GET may be disabled in TIA Portal). Use `python test_plc.py` for full protocol validation.

---

## Installation & Windows Quick Start

### Step 1: Clone or Navigate to Directory
```powershell
cd "d:\Dev\pr 1"
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Settings
Copy the template configuration:
```powershell
copy .env.example .env
```
Edit `.env` if your PLC IP or Rack/Slot differs:
```env
PLC_IP=192.168.0.100
PLC_RACK=0
PLC_SLOT=1
PLC_PORT=102
PLC_POLL_INTERVAL=1.0
PLC_RECONNECT_INTERVAL=5.0
CONFIG_PATH=config/plc_config.json
LOG_LEVEL=INFO
```

### Step 5: Run Standalone Diagnostic Tool
Verify network reachability and test tag reads without starting the full web server:
```powershell
python test_plc.py
```

### Step 6: Start FastAPI Development Server
```powershell
uvicorn backend.main:app --reload
```
Or start directly with Python:
```powershell
python -m backend.main
```

### Step 7: Access Documentation & Endpoints
* **Swagger UI (Interactive API Docs)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Service Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Configuring PLC Variables (`config/plc_config.json`)

PLC variables are defined in JSON without modifying any Python code.

### Supported Data Types
* **`BOOL`**: 1-bit boolean flag (requires `bit` 0–7)
* **`BYTE`**: 8-bit unsigned integer (0 to 255)
* **`WORD`**: 16-bit unsigned integer (0 to 65,535)
* **`DWORD`**: 32-bit unsigned integer (0 to 4,294,967,295)
* **`INT`**: 16-bit signed integer (-32,768 to 32,767)
* **`DINT`**: 32-bit signed integer (-2,147,483,648 to 2,147,483,647)
* **`REAL`**: 32-bit IEEE-754 single-precision float
* **`LREAL`**: 64-bit IEEE-754 double-precision float
* **`STRING`**: Siemens S7 String with header (specifies max string length)

### Example `config/plc_config.json`
```json
{
  "description": "Siemens PLC Data Block Variable Configuration",
  "variables": [
    {
      "name": "voltage",
      "db": 1,
      "byte": 0,
      "type": "REAL",
      "unit": "V",
      "description": "Main bus supply voltage"
    },
    {
      "name": "motor_running",
      "db": 1,
      "byte": 16,
      "bit": 0,
      "type": "BOOL",
      "description": "Drive motor run feedback"
    },
    {
      "name": "raw_sensor_counts",
      "db": 1,
      "byte": 18,
      "type": "INT",
      "scale": 0.1,
      "offset": 0.0,
      "unit": "°C",
      "description": "Scaled temperature sensor raw input"
    },
    {
      "name": "recipe_name",
      "db": 1,
      "byte": 40,
      "type": "STRING",
      "string_max_length": 32,
      "description": "Active production recipe identifier"
    }
  ]
}
```

---

## REST API Reference

### 1. `GET /api/health`
Health check endpoint reporting backend uptime and PLC connectivity.
```json
{
  "status": "ok",
  "backend_running": true,
  "plc_connected": true,
  "timestamp": "2026-08-30T08:00:00.123456",
  "active_websocket_connections": 1
}
```

### 2. `GET /api/plc/status`
Connection state, hardware details, CPU mode, and poll intervals.
```json
{
  "connected": true,
  "ip": "192.168.0.100",
  "rack": 0,
  "slot": 1,
  "port": 102,
  "poll_interval_seconds": 1.0,
  "reconnect_interval_seconds": 5.0,
  "total_configured_variables": 14,
  "last_successful_read": "2026-08-30T08:00:01.450120",
  "last_error": null,
  "cpu_info": {
    "module_type_name": "CPU 1214C DC/DC/DC",
    "serial_number": "S C-D6U...",
    "as_name": "PLC_1",
    "module_name": "PLC_1"
  },
  "cpu_state": "RUN"
}
```

### 3. `GET /api/plc/data`
Returns the latest cached snapshot of all parsed engineering values.
```json
{
  "timestamp": "2026-08-30T08:00:02.012450",
  "plc_connected": true,
  "poll_duration_ms": 14.52,
  "variables": {
    "voltage": 230.5,
    "current": 12.4,
    "power": 2858.2,
    "frequency": 50.01,
    "motor_running": true,
    "alarm_active": false,
    "emergency_stop": true,
    "raw_sensor_counts": 24.5,
    "part_counter": 1450,
    "status_word": 65280,
    "system_fault_code": 0,
    "machine_state_code": 2,
    "total_energy_kwh": 1845.89214,
    "recipe_name": "BATCH_A42"
  },
  "errors": null
}
```

### 4. `GET /api/plc/variables`
Returns the list of all configured variables, addresses, data types, units, and descriptions.

### 5. `POST /api/plc/reconnect`
Forces an immediate reconnection attempt to the PLC.

---

## WebSocket API (`WS /ws/plc`)

Streams live PLC data snapshots whenever a poll cycle completes.

### JavaScript Client Example
```javascript
const socket = new WebSocket('ws://localhost:8000/ws/plc');

socket.onopen = () => {
  console.log('Connected to PLC WebSocket stream');
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('PLC Live Data:', data);
  if (data.plc_connected) {
    document.getElementById('voltage').innerText = data.variables.voltage + ' V';
    document.getElementById('motor').innerText = data.variables.motor_running ? 'ON' : 'OFF';
  }
};

socket.onclose = () => {
  console.warn('PLC WebSocket disconnected');
};
```

---

## Error Handling & Resiliency

* **PLC Offline / Network Drop**: The background polling service catches connection drops, updates `plc_connected=False`, and enters an automatic reconnection loop without crashing or blocking the HTTP server.
* **Bad Tag Offset / Bounds**: If a single variable in a Data Block has an invalid offset or format, the parser flags that tag with `quality: "BAD"` and records an error entry while continuing to parse all other valid tags.
* **Thread Safety**: All calls to the native Snap7 C library are protected by a thread synchronization lock.
* **Safety (Read-Only)**: The client exclusively performs read operations (`db_read`). No write methods or memory-modifying calls exist in the service.

---

## Project Structure

```
d:\Dev\pr 1/
├── backend/
│   ├── main.py                  # FastAPI server, lifespan, CORS, and startup
│   ├── config.py                # Pydantic Settings & JSON config loader
│   ├── plc/
│   │   ├── client.py            # Thread-safe Snap7 client & reconnection logic
│   │   ├── reader.py            # Async background poller & WebSocket broadcaster
│   │   └── datatypes.py         # Siemens S7 Big-Endian binary parsers & scalers
│   ├── api/
│   │   ├── routes.py            # REST endpoints (/status, /data, /variables, /reconnect, /health)
│   │   └── websocket.py         # WebSocket broadcaster (/ws/plc)
│   └── models/
│       └── plc_data.py          # Pydantic data schemas & enums
│
├── config/
│   └── plc_config.json          # Variable tag definitions (DB, offsets, types, scaling)
│
├── tests/
│   ├── test_datatypes.py        # Unit tests for binary parsers & scalers
│   ├── test_config.py           # Unit tests for JSON validation
│   └── test_api.py              # Integration tests for REST endpoints
│
├── test_plc.py                  # Standalone CLI diagnostic tool
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore patterns
└── README.md                    # System documentation
```


---

## React Dashboard (Frontend)

Quick start:

  1. Backend:  .\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
  2. Frontend: cd frontend, then: npm install, npm run dev

Open http://localhost:5173

Tabs: Dashboard / Variables / Charts / Settings
Dashboard is read-only — never writes to the PLC.
#   p l c  
 