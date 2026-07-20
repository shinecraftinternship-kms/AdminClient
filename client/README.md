# System Scanner Pro - Client Agent

Python agent that runs on endpoint machines, scans hardware/software, monitors system events, and reports to the admin server via HTTP + WebSocket.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ (stdlib) |
| Communication | HTTP (requests) + WebSocket (websockets) |
| Event Monitoring | watchdog (file), pyusb (USB), psutil (process) |
| Discovery | UDP broadcast + Supabase cloud discovery |
| Resilience | Exponential backoff, offline queue, heartbeat watchdog |

## Project Structure

```
client/
├── main.py              # Entry point — registration, heartbeat, scan loop
├── scanner.py           # Hardware/software scan collection
├── communicator.py      # HTTP + WebSocket communication with admin
├── config.py            # Admin URL prompt and discovery
├── discovery.py         # Supabase cloud discovery
├── fingerprint.py       # Hardware fingerprint generation
├── key_manager.py       # Registration key management
├── metrics.py           # Live metrics collection (CPU, RAM, disk)
├── events/
│   ├── dispatcher.py    # Batched event sending (WS/HTTP)
│   ├── usb_monitor.py   # USB device insertion/removal
│   ├── file_monitor.py  # Critical file changes (watchdog)
│   ├── process_monitor.py   # Process start/stop detection
│   └── software_monitor.py  # Software install/uninstall
├── scans/               # Local scan result backups
├── client_key.json      # Registration key + fingerprint (auto-generated)
└── client_config.json   # Admin URL + scan settings (auto-generated)
```

## Requirements

- Python 3.10+
- pip
- Network access to the admin server

## Quick Start

### 1. Install Dependencies

From the repo root:

```bash
cd admin-client
pip install -r requirements.txt
```

Or from the client directory:

```bash
cd admin-client/client
pip install -r ../requirements.txt
```

### 2. Start the Client

**Interactive (prompts for admin URL):**

```bash
python client/main.py
```

**With known admin URL:**

```bash
python client/main.py http://ADMIN-SERVER-IP
```

**With Vercel-deployed admin:**

```bash
python client/main.py https://your-project.vercel.app
```

### 3. First-Time Setup Flow

When you run the client for the first time:

```
==========================================================
  System Scanner Pro Client v1.0.0
  Runs on this machine and reports to admin server
  WebSocket + HTTP fallback communication
  Event monitoring: USB, File, Process, Software
==========================================================

  Your Registration Key: ABCD1234
  Device Fingerprint:    A1B2C3D4E5F6G7H8

  First-time setup required.
  Enter admin server URL (e.g., http://192.168.1.100:80): _
```

Enter the admin server URL and press Enter.

### 4. What Happens Next

1. **Registers** with the admin server
2. **Waits for approval** (if auto-approve is off in admin settings)
3. **Performs initial hardware scan** (CPU, RAM, storage, GPU, OS, network, software, peripherals)
4. **Starts heartbeat loop** (every 30 seconds)
5. **Connects WebSocket** for real-time commands from admin
6. **Starts event monitors:**
   - USB device changes (every 5 seconds)
   - Critical file modifications (real-time via watchdog)
   - Process start/stop (every 10 seconds)
   - Software install/uninstall (every 60 seconds)
7. **Performs scheduled scans** at the configured interval (default: every hour)

### 5. Approve the Client

On the admin dashboard (`http://ADMIN-IP`):
1. You'll see the new client with a yellow "Pending" dot
2. Click **Approve** (or use bulk actions)

Once approved, the client starts reporting heartbeat data, health scores, and alerts.

## Configuration Files

| File | Purpose | Auto-Generated |
|------|---------|---------------|
| `client_key.json` | Registration key + hardware fingerprint | Yes |
| `client_config.json` | Admin URL + scan settings | Yes |
| `scans/` | Local scan result backups | Yes |

> **Do NOT delete `client_key.json`** unless you want to re-register the device with a new identity.

### client_key.json

```json
{
  "registration_key": "ABCD1234",
  "fingerprint": "A1B2C3D4E5F6G7H8"
}
```

### client_config.json

```json
{
  "admin_url": "http://192.168.1.100:80",
  "scan_interval": 3600,
  "auto_start": true
}
```

## Command-Line Options

```bash
# Pass admin URL directly (skips prompt)
python client/main.py http://ADMIN-SERVER-IP

# The URL must start with http:// or https://
python client/main.py https://your-project.vercel.app
```

## Event Monitors

| Monitor | What It Detects | Poll Interval |
|---------|----------------|---------------|
| USB Monitor | Device insertion/removal | 5 seconds |
| File Monitor | Changes to critical system paths | Real-time (watchdog) |
| Process Monitor | New/terminated processes | 10 seconds |
| Software Monitor | Installed/removed applications | 60 seconds |

Events are batched and sent via WebSocket (preferred) or HTTP (fallback). When offline, events are persisted to disk and replayed on reconnect.

## Heartbeat & Communication

The client uses two communication channels:

### HTTP Heartbeat (Fallback)
- Pings admin server every 30 seconds
- Includes CPU, RAM, disk usage metrics
- Triggers scans when admin requests

### WebSocket (Primary)
- Real-time bidirectional communication
- Receives scan commands, config updates instantly
- Auto-reconnects on disconnect
- Falls back to HTTP when unavailable

### Offline Resilience

| Feature | Behavior |
|---------|----------|
| Exponential Backoff | HTTP retries with jitter on connection failures |
| Offline Event Queue | Events persisted to disk when offline, replayed on reconnect |
| Heartbeat Watchdog | Auto-restarts heartbeat thread if it crashes |
| Cloud Discovery | Periodically checks Supabase for admin IP changes |
| UDP Discovery | Listens for admin broadcasts on same network |

## Scanning

### Automatic Scanning

- **Initial scan** — Performed immediately on registration approval
- **Scheduled scans** — Configured via admin dashboard (default: every hour)
- **Heartbeat scans** — Client sends CPU/RAM/disk metrics every 30 seconds
- **Event monitors** — USB, file, process, and software changes detected continuously

### Manual Trigger

From the admin dashboard or API:
```bash
curl -X POST http://ADMIN/api/clients/YOUR-KEY/scan-now
```

### Scan Data Collected

| Category | Items |
|----------|-------|
| **Processor** | Manufacturer, model, serial, cores, threads, speed, cache |
| **RAM** | Manufacturer, capacity per module, serial, frequency, form factor |
| **Storage** | Disks (model, serial, size, interface), partitions (filesystem, mount) |
| **Motherboard** | Manufacturer, model, serial, BIOS version |
| **GPU** | Name, vendor, dedicated memory |
| **OS** | Name, version, build, architecture, install date |
| **Network** | Interfaces (name, MAC, IPv4, status) |
| **Peripherals** | Keyboards, mice, audio, webcams, printers, USB devices |
| **Software** | Installed applications (name, version, publisher) |
| **Windows Updates** | KB IDs and descriptions (Windows only) |
| **Antivirus** | Antivirus products and firewall status (Windows only) |
| **User Accounts** | Local user accounts |

## Running as a Background Service

### Windows (Scheduled Task)

```cmd
schtasks /create /tn "SystemScanner" /tr "C:\path\to\SystemScannerClient.exe http://SERVER" /sc onstart
```

### Linux (systemd)

Create `/etc/systemd/system/scanner-client.service`:

```ini
[Unit]
Description=System Scanner Client
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/client/main.py http://SERVER
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable scanner-client
sudo systemctl start scanner-client
sudo systemctl status scanner-client
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.scanner.client.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.scanner.client</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/client/main.py</string>
        <string>http://SERVER</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.scanner.client.plist
```

## Building Executables

### Prerequisites

```bash
pip install pyinstaller
```

### Build

From the repo root:

```bash
python build/build.py client    # Build client only
python build/build.py all       # Build both admin and client
```

### Running Packaged Executable

```cmd
SystemScannerClient.exe http://192.168.1.100:80
SystemScannerClient.exe https://your-project.vercel.app
```

## Stopping the Client

```bash
# Press Ctrl+C in the terminal
# The client shuts down gracefully:
# - Stops all event monitors
# - Flushes pending events
# - Closes WebSocket connection
```

## Reset / Re-Registration

### Reset a Client (New Identity)

```bash
# Delete the client's saved key and fingerprint
rm client/client_key.json    # Linux/macOS
del client\client_key.json   # Windows

# Run client again — generates new key and re-registers
python client/main.py
```

### Change Admin Server URL

```bash
rm client_config.json
python client/main.py   # Prompts for new admin URL
```

Or edit `client_config.json` directly and change `"admin_url"`.

### Full Factory Reset

```bash
rm client/client_key.json
rm client/client_config.json
rm -rf client/scans/
python client/main.py
```

## Device Identity

- Each device is identified by a **hardware fingerprint** (motherboard + CPU + disk + MAC)
- The fingerprint survives IP changes, hostname changes, and re-registration
- The `client_key.json` stores the device's registration key — do not delete unless you want to re-register

## Online/Offline Status

| Status | Indicator | Meaning |
|--------|-----------|---------|
| Online | Green dot | Device is actively sending heartbeats (every 30s) |
| Offline | Red dot | No heartbeat received in over 120 seconds |
| Pending | Yellow dot | Device registered but not yet approved |
| Blocked | Purple dot | Device blocked by admin |

## Network Requirements

| Port | Protocol | Purpose |
|------|----------|---------|
| 80 (or custom) | TCP | Admin web dashboard + API + WebSocket |
| 45000 | UDP | Auto-discovery (admin broadcasts, clients listen) |

> For Vercel-deployed admin, only port 443 (HTTPS) is needed. UDP discovery is not available.

## Troubleshooting

### Client can't connect to admin server

1. Verify the admin server is running: open `http://SERVER-IP` in a browser
2. Check firewall allows port 80 (TCP) and 45000 (UDP)
3. Try auto-discovery: run client without arguments on the same network
4. Check the admin server is bound to `0.0.0.0` (not just `127.0.0.1`)

### Client shows "Connection failed"

- Admin server might be offline — check the terminal running it
- Network issue — try `ping SERVER-IP`
- Wrong URL — make sure you include `http://` or `https://` prefix

### Client stays "Pending" forever

- Admin must approve the client from the dashboard
- Or enable auto-approve in admin Settings (`/settings/`)

### WebSocket not connecting

- Check that the admin server port is accessible (WebSocket uses same port as HTTP)
- If admin is on Vercel, WebSocket is not supported — client will use HTTP fallback
- If behind nginx, ensure `/ws/` location has WebSocket proxy headers

### Event monitors not starting

- Check that required packages are installed: `pip install watchdog`
- Look for `[OK] 4 event monitors active` in client output
- If offline, events are queued to disk and will be replayed when reconnected

### Heartbeat errors

- Consecutive errors trigger auto-discovery (cloud + UDP)
- After 5 failures, client tries to find admin via alternative methods
- Heartbeat watchdog auto-restarts the heartbeat thread if it crashes

### Client can't reach Vercel-deployed admin

- Use the full URL: `https://your-project.vercel.app`
- Ensure `https://` prefix is included
- Vercel has cold start delays — first request may take 5-10 seconds

## License

Internal use.
