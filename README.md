# System Scanner Pro v3.0

AI-powered distributed endpoint monitoring and remote scanning platform with real-time WebSocket communication, client event monitoring, scheduled scanning, JWT security, and predictive analytics.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ADMIN SERVER (Django)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ REST API │ │WebSocket │ │ Event Bus│ │  APScheduler     │   │
│  │ (DRF)    │ │Consumer  │ │ (pub/sub)│ │  (scheduled scans)│  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
│       │             │            │                 │             │
│  ┌────┴─────────────┴────────────┴─────────────────┴─────────┐  │
│  │                    SQLite / PostgreSQL                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │  Anomaly   │ │  Feature   │ │ Predictive │ │  Reports    │  │
│  │ Detection  │ │  Store     │ │ Analytics  │ │ (PDF/CSV)   │  │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │ TCP (HTTP + WebSocket)        │ UDP (discovery)
┌──────────┴──────────┐          ┌─────────┴──────────────────┐
│   CLIENT AGENT 1    │          │     CLIENT AGENT N         │
│ ┌─────────────────┐ │          │ ┌────────────────────────┐  │
│ │ Event Monitors  │ │          │ │ USB / File / Process / │  │
│ │ (USB/File/Proc) │ │          │ │ Software monitors      │  │
│ └─────────────────┘ │          │ └────────────────────────┘  │
│ ┌─────────────────┐ │          │ ┌────────────────────────┐  │
│ │ Scanner         │ │          │ │ Offline Queue (disk)   │  │
│ │ (HW/SW scan)    │ │          │ │ Exponential Backoff    │  │
│ └─────────────────┘ │          │ │ Heartbeat Watchdog     │  │
│ ┌─────────────────┐ │          │ └────────────────────────┘  │
│ │ WebSocket Client│ │          └─────────────────────────────┘
│ │ (real-time cmd) │ │
│ └─────────────────┘ │
└─────────────────────┘
```

## Features

### Core
- **Hardware Scanning** — CPU, RAM, storage, motherboard, GPU, OS, network, software, peripherals, antivirus (Windows/Linux/macOS)
- **Admin Dashboard** — Real-time client overview with stats, charts, search/filter, bulk actions
- **Change Detection** — Automatic diff between scans, alerts on hardware/software changes
- **Client Management** — Registration with approval workflow, heartbeat monitoring, stale detection, grouping
- **Authentication** — Login-protected admin panel with JWT tokens, API keys, and RBAC permissions

### Real-Time (WebSocket)
- **Live Dashboard** — WebSocket connection pushes device updates, alerts, and health changes instantly
- **Agent Commands** — Send scan_now, config_update commands via WebSocket to agents
- **Event Broadcasting** — Hardware/software changes broadcast to all connected dashboards
- **Auto-Reconnect** — Both server and client handle disconnects gracefully

### Client Event Monitoring
- **USB Monitor** — Detects USB device insertion/removal (cross-platform)
- **File Monitor** — Watchdog on critical system paths (Windows Event Log, /etc, /usr)
- **Process Monitor** — Detects new/terminated/suspicious processes
- **Software Monitor** — Detects installed/removed software changes
- **Event Dispatcher** — Batches events and sends via WebSocket or HTTP

### Scheduled Scanning
- **APScheduler Integration** — Schedule scans at intervals, daily, weekly, monthly, or once
- **Offline Queue** — Pending scans queued for devices that are offline
- **WebSocket Dispatch** — Scheduled scans sent as real-time commands

### Security
- **JWT Authentication** — Access/refresh token pairs for API access
- **API Keys** — Programmatic access with rate limiting and IP restrictions
- **RBAC** — Super admin, admin, viewer roles with permission classes
- **HMAC Signatures** — Agent communication signed with HMAC-SHA256

### Client Resilience
- **Exponential Backoff** — HTTP retries with jitter on connection failures
- **Offline Event Queue** — Events persisted to disk when offline, replayed on reconnect
- **Heartbeat Watchdog** — Auto-restarts heartbeat thread if it crashes

### Reports
- **PDF Reports** — Fleet summary, device detail, alert history (ReportLab)
- **CSV Exports** — Fleet inventory, device alerts, per-device export

### AI-Ready
- **Anomaly Detection** — Z-score, IQR, trend-based statistical detection
- **Feature Store** — 20+ ML-ready features extracted from device metrics
- **Predictive Analytics** — Disk full prediction, failure risk scoring, capacity forecasting

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x + DRF 3.15 + Django Channels 4.x |
| Database | SQLite (default), PostgreSQL/Supabase (production) |
| WebSocket | Django Channels (InMemoryChannelLayer, Redis for production) |
| Scheduler | APScheduler 3.x |
| Auth | JWT (PyJWT) + Session + API Keys |
| Frontend | Django templates + vanilla JS + Bootstrap 5.3 + Chart.js |
| Reports | ReportLab (PDF) + Python csv (CSV) |
| Client | Python stdlib + websockets + watchdog |
| Build | PyInstaller 6.x |

## Requirements

- Python 3.10+
- pip

## Quick Start

### 1. Install Dependencies

```bash
cd admin-client
pip install -r requirements.txt
```

### 2. Start the Admin Server

```bash
python admin/main.py
```

First run will:
- Create the SQLite database at `admin/data/scanner.db`
- Create a default admin user (`admin` / `admin123`)
- Prompt for the IP address to bind to (use `0.0.0.0` for all interfaces)
- Start UDP auto-discovery on port 45000
- Start the Django server on port 80

**Dashboard:** Open `http://localhost` in your browser.

**Default login:** `admin` / `admin123`

### 3. Start a Client Agent

On any machine you want to monitor:

```bash
python client/main.py
```

First run will:
- Generate a unique registration key (saved to `client_key.json`)
- Generate a hardware fingerprint (saved to `client_key.json`)
- Prompt for the admin server URL (or auto-discover via UDP)
- Register with the admin server
- Wait for admin approval
- Perform an initial hardware scan
- Enter a heartbeat loop (pings every 30 seconds)
- Start WebSocket connection for real-time commands
- Start event monitors (USB, File, Process, Software)

### 4. Approve the Client

1. Open the admin dashboard at `http://localhost`
2. You'll see the new client with a yellow "Pending" dot
3. Click **Approve** (or use bulk actions to approve multiple)

Once approved, the client starts reporting heartbeat data, health scores, and alerts.

## How to Add a Domain Name

### Option 1: Use a Domain Name for the Admin Server

If you have a domain (e.g., `scanner.yourcompany.com`):

1. Point your domain's DNS A record to the admin server's public IP
2. Open `admin/django_admin/settings.py` and add your domain to `ALLOWED_HOSTS`:
   ```python
   ALLOWED_HOSTS = ["0.0.0.0", "127.0.0.1", "localhost", "scanner.yourcompany.com"]
   ```
3. Restart the admin server
4. Clients connect using:
   ```bash
   python client/main.py http://scanner.yourcompany.com
   ```

### Option 2: Use a Domain with HTTPS (Production)

For production with HTTPS:

1. Install nginx as a reverse proxy:
   ```bash
   # Ubuntu/Debian
   sudo apt install nginx certbot python3-certbot-nginx
   ```

2. Create nginx config at `/etc/nginx/sites-available/scanner`:
   ```nginx
   server {
       listen 80;
       server_name scanner.yourcompany.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl;
       server_name scanner.yourcompany.com;

       ssl_certificate /etc/letsencrypt/live/scanner.yourcompany.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/scanner.yourcompany.com/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:80;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /ws/ {
           proxy_pass http://127.0.0.1:80;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_read_timeout 86400;
       }
   }
   ```

3. Enable the site and get SSL:
   ```bash
   sudo ln -s /etc/nginx/sites-available/scanner /etc/nginx/sites-enabled/
   sudo certbot --nginx -d scanner.yourcompany.com
   sudo systemctl reload nginx
   ```

4. Run the admin server on localhost:
   ```bash
   python admin/main.py --host 127.0.0.1 --port 80
   ```

5. Clients connect using:
   ```bash
   python client/main.py http://scanner.yourcompany.com
   ```

### Option 3: Use a Free Dynamic DNS (No Domain Needed)

If you don't have a domain, the system has built-in auto-discovery:

1. Start the admin server on port 80
2. Clients on the same network automatically discover the admin via UDP broadcast (port 45000)
3. No manual URL entry needed after the first client connects

For remote access without a domain, use the admin server's public IP directly:
```bash
python client/main.py http://YOUR.PUBLIC.IP.ADDRESS
```

## How to Reset the Domain / Admin URL

### Reset the Admin Server Bind Address

```bash
python admin/main.py --reset
# Prompts for a new bind address
```

### Reset a Client's Admin URL

On the client machine:

**Option A — Delete config and re-run:**
```bash
# Windows
del client_config.json

# Linux/macOS
rm client_config.json

# Re-run — it will prompt for the new admin URL
python client/main.py
```

**Option B — Edit the config file directly:**
```bash
# Edit client_config.json and change "admin_url"
# Then restart the client
```

### Reset All Clients to Use a New Server

1. Start the new admin server
2. On each client machine, delete `client_key.json` and `client_config.json`
3. Run `python client/main.py http://NEW.SERVER.ADDRESS`
4. Approve each client from the new admin dashboard

## How to Scan

### Automatic Scanning

Once a client is approved, scanning happens automatically:

- **Initial scan** — Performed immediately on registration approval
- **Scheduled scans** — Configured via the admin dashboard or API (default: every hour)
- **Heartbeat scans** — Client sends CPU/RAM/disk metrics every 30 seconds
- **Event monitors** — USB, file, process, and software changes detected continuously

### Manual Scanning

**From the Admin Dashboard:**
1. Go to the Dashboard (`/`)
2. Click **Scan Server** to scan the admin machine
3. Click **Scan All** to trigger a scan on all online clients
4. Go to a client detail page and click **Scan Now** for a single client

**From the Command Line:**
```bash
# Scan the admin server machine
python admin/manage.py scan_local

# Trigger scan on all clients
python admin/manage.py scan_all
```

**From the API:**
```bash
# Scan a specific client
curl -X POST http://localhost/api/clients/YOUR-KEY/scan-now

# Scan all clients
curl -X POST http://localhost/api/scan/all

# Scan the admin server
curl -X POST http://localhost/api/scan/local
```

### Viewing Scan Results

1. **Dashboard** (`/`) — Overview of all clients
2. **Client Detail** (`/client/<key>/`) — Full scan data for one client
3. **Scan History** (`/scans/`) — Browse all historical scans
4. **Monitoring Dashboard** (`/monitoring/`) — Health scores, alerts, real-time updates

## How to Run the Client System

### First-Time Setup

```bash
cd admin-client
python client/main.py
```

You'll see:
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

### With a Known Admin URL

```bash
python client/main.py http://192.168.1.100:80
```

### What the Client Does

1. Registers with the admin server
2. Waits for admin approval (if auto-approve is off)
3. Performs initial hardware scan
4. Starts heartbeat loop (every 30 seconds)
5. Connects WebSocket for real-time commands
6. Starts event monitors:
   - USB device changes
   - Critical file modifications
   - Process start/stop
   - Software install/uninstall
7. Performs scheduled scans at the configured interval

### Client Data Files

| File | Purpose |
|------|---------|
| `client_key.json` | Registration key + hardware fingerprint |
| `client_config.json` | Admin URL + scan settings |
| `scans/` | Local scan result backups |

### Stopping the Client

```bash
# Press Ctrl+C in the terminal
# The client shuts down gracefully:
# - Stops all event monitors
# - Flushes pending events
# - Closes WebSocket connection
```

### Running as a Background Service

**Windows (as a scheduled task):**
```cmd
schtasks /create /tn "SystemScanner" /tr "C:\path\to\SystemScannerClient.exe http://SERVER" /sc onstart
```

**Linux (systemd):**
```ini
# /etc/systemd/system/scanner-client.service
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
```

**macOS (launchd):**
```xml
<!-- ~/Library/LaunchAgents/com.scanner.client.plist -->
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

## Admin Server CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port PORT` | Server port | 80 |
| `--host HOST` | Bind address | Prompts on first run |
| `--debug` | Enable Django debug mode | False |
| `--username NAME` | Default admin username | admin |
| `--password PASS` | Default admin password | admin123 |
| `--reset` | Re-ask for bind IP | — |

## Management Commands

```bash
python admin/manage.py migrate              # Apply database migrations
python admin/manage.py scan_local           # Scan the admin server machine
python admin/manage.py scan_all             # Trigger scan on all clients
python admin/manage.py stale_checker        # Mark stale clients offline
python admin/manage.py alert_checker        # Check for offline alerts
python admin/manage.py health_checker       # Recalculate health scores
python admin/manage.py offline_detector     # Detect and mark offline devices
python admin/manage.py createsuperuser      # Create a new Django superuser
python admin/manage.py changepassword       # Change a user's password
```

## How to Reset Everything

### Reset Admin Server IP

```bash
python admin/main.py --reset
```

### Reset Admin Password

```bash
# Option 1: From the admin web panel
# 1. Go to /admin-page/
# 2. Delete the old admin user
# 3. Create a new admin user

# Option 2: Delete the database
rm admin/data/scanner.db
python admin/main.py   # Re-creates DB + default admin user
```

### Reset a Client (Clear Registration)

```bash
# Delete the client's saved key and fingerprint
rm client/client_key.json
# OR on Windows:
del client\client_key.json

# Run client again — it generates a new key and re-registers
python client/main.py
```

### Reset a Client's Admin URL

```bash
rm client_config.json
python client/main.py   # Prompts for new admin URL
```

### Full Factory Reset (Delete Everything)

```bash
# Delete the database
rm admin/data/scanner.db

# Delete client keys
rm client/client_key.json
rm client/client_config.json

# Start fresh
python admin/main.py
python client/main.py
```

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Client overview with stats, charts, search/filter, bulk actions |
| `/login/` | Login | Admin authentication |
| `/logout/` | Logout | End session |
| `/client/<key>/` | Client Detail | Full client info, scan data, manual fields, add-ons, scan config |
| `/settings/` | Settings | Auto-approve, stale threshold, scan interval, groups, system info |
| `/admin-page/` | Admin Panel | User management, scan change notifications, activity log, stats |
| `/account/` | Account | Profile view and password change |
| `/scans/` | Scan History | Browse all scan results with device details and filtering |
| `/audit-log/` | Audit Log | Security and admin action audit trail |
| `/monitoring/` | Monitoring | Real-time device health, alerts, WebSocket status |
| `/employees/` | Employees | Employee management |
| `/departments/` | Departments | Department management |
| `/locations/` | Locations | Location management |
| `/assets/` | Assets | Asset management |
| `/asset-dashboard/` | Asset Dashboard | Asset analytics |
| `/intelligence/` | Intelligence | AI analytics dashboard |
| `/maintenance/` | Maintenance | Maintenance scheduling |
| `/licenses/` | Licenses | Software license tracking |

## API Endpoints

### Client Registration & Communication
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/register` | Register a client |
| POST | `/api/approve` | Approve a client |
| POST | `/api/ping` | Client heartbeat |
| GET | `/api/clients/<key>/status` | Check approval status |

### Scan Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/scan` | Submit scan data |
| POST | `/api/scan/local` | Scan the admin server |
| POST | `/api/scan/all` | Trigger scan on all clients |
| GET | `/api/scan/history` | List all scans |
| GET | `/api/clients/<key>/scan-results` | Latest scan for a client |
| POST | `/api/clients/<key>/scan-now` | Trigger scan on a client |
| GET/PUT | `/api/clients/<key>/scan-config` | Get/update scan config |

### Monitoring
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/monitoring/dashboard` | Aggregate dashboard stats |
| GET | `/api/monitoring/devices` | List all monitored devices |
| GET | `/api/monitoring/devices/<key>` | Device detail |
| POST | `/api/monitoring/devices/<key>/approve` | Approve device |
| POST | `/api/monitoring/devices/<key>/block` | Block device |
| GET | `/api/monitoring/alerts` | List all alerts |
| POST | `/api/monitoring/alerts/<id>/action` | Ack/resolve/dismiss alert |

### Scheduled Scanning
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/monitoring/schedules` | List schedules |
| POST | `/api/monitoring/schedules` | Create schedule |
| PUT | `/api/monitoring/schedules/<id>` | Update schedule |
| POST | `/api/monitoring/schedules/<id>/toggle` | Enable/disable |
| GET | `/api/monitoring/schedules/status` | Scheduler status |

### Reports
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/monitoring/reports/fleet/pdf` | Fleet PDF report |
| GET | `/api/monitoring/reports/fleet/csv` | Fleet CSV export |
| GET | `/api/monitoring/reports/device/<key>/pdf` | Device PDF report |
| GET | `/api/monitoring/reports/device/<key>/csv` | Device CSV export |
| GET | `/api/monitoring/reports/alerts/pdf` | Alerts PDF report |
| GET | `/api/monitoring/reports/alerts/csv` | Alerts CSV export |

### JWT Authentication
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/token/obtain` | Get JWT access + refresh tokens |
| POST | `/api/auth/token/refresh` | Refresh access token |
| POST | `/api/auth/token/verify` | Validate a token |
| GET | `/api/auth/api-keys` | List your API keys |
| POST | `/api/auth/api-keys` | Create a new API key |
| DELETE | `/api/auth/api-keys/<id>` | Revoke an API key |

### WebSocket Endpoints
| URL | Purpose |
|-----|---------|
| `ws://HOST/ws/dashboard/` | Admin dashboard real-time updates |
| `ws://HOST/ws/agent/<agent_id>/` | Agent command/control channel |

### Admin
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/users` | List admin users |
| POST | `/api/admin/users` | Create admin user |
| DELETE | `/api/admin/users/<id>` | Delete admin user |
| GET | `/api/admin/stats` | System statistics |
| GET/PUT | `/api/settings` | Global settings |

## Client Event Monitors

| Monitor | What It Detects | Poll Interval |
|---------|----------------|---------------|
| USB Monitor | Device insertion/removal | 5 seconds |
| File Monitor | Changes to critical system paths | Real-time (watchdog) |
| Process Monitor | New/terminated processes | 10 seconds |
| Software Monitor | Installed/removed applications | 60 seconds |

Events are batched and sent via WebSocket (preferred) or HTTP (fallback). When offline, events are persisted to disk and replayed on reconnect.

## Anomaly Detection

The system detects anomalies using:

| Method | Description | Threshold |
|--------|-------------|-----------|
| Z-score | Values N standard deviations from mean | N=2.5 |
| IQR | Interquartile range outliers | 1.5x IQR |
| Trend | Rapid changes vs baseline | 50% change |
| Threshold | Static rules (CPU>95%, etc.) | Configurable |
| Compound | Multiple signals combined | Higher confidence |

## Predictive Analytics

| Prediction | Method | Output |
|------------|--------|--------|
| Disk full time | Linear regression on disk usage trend | Hours until capacity |
| Failure risk | Multi-factor risk score (0-100) | Risk level + factors |
| Capacity needs | Trend extrapolation at 30/60/90 days | Predicted utilization |

## Environment Variables (.env)

Copy `.env.template` to `.env` and configure:

```bash
cp .env.template .env
```

| Variable | Purpose | Default |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | insecure default |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `SUPABASE_DATABASE_URL` | PostgreSQL connection (optional) | SQLite |
| `SUPABASE_URL` | Supabase project URL (optional) | — |

## Network Requirements

| Port | Protocol | Purpose |
|------|----------|---------|
| 80 (or custom) | TCP | Admin web dashboard + API + WebSocket |
| 45000 | UDP | Auto-discovery (admin broadcasts, clients listen) |

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

## Database Location

| Run Type | Database Path |
|----------|--------------|
| Development | `admin/data/scanner.db` |
| Windows (packaged) | `%APPDATA%\SystemScannerPro\scanner.db` |
| Linux (packaged) | `~/.local/share/SystemScannerPro/scanner.db` |
| macOS (packaged) | `~/Library/Application Support/SystemScannerPro/scanner.db` |

## Building Executables

### Prerequisites

```bash
pip install pyinstaller
```

### Build

```bash
python build/build.py all     # Build both admin and client
python build/build.py admin   # Build admin only
python build/build.py client  # Build client only
python build/build.py clean   # Clean build artifacts
```

### Running Packaged Executables

**Admin:**
```cmd
SystemScannerAdmin.exe --port 8080 --username admin --password mypass
SystemScannerAdmin.exe --reset   # Re-enter bind IP
```

**Client:**
```cmd
SystemScannerClient.exe http://192.168.1.100:80
```

## Scan Data Collected

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

## Troubleshooting

### Client can't connect to admin server

1. Verify the admin server is running: open `http://SERVER-IP` in a browser
2. Check firewall allows port 80 (TCP) and 45000 (UDP)
3. Try auto-discovery: run client without arguments on the same network
4. Check the admin server is bound to `0.0.0.0` (not just `127.0.0.1`)

### Client shows "Connection failed"

- Admin server might be offline — check the terminal running it
- Network issue — try `ping SERVER-IP`
- Wrong URL — make sure you include `http://` prefix

### WebSocket not connecting

- Check that port 80 is accessible (WebSocket uses the same port as HTTP)
- If behind nginx, ensure the `/ws/` location has WebSocket proxy headers
- Check browser console for WebSocket errors

### Client stays "Pending" forever

- Admin must approve the client from the dashboard
- Or enable auto-approve in Settings (`/settings/`)

### No real-time updates on dashboard

- Open browser console (F12) and check for WebSocket connection status
- The "Live" badge should be green in the top-right of the monitoring page
- If red, check that the admin server has WebSocket support enabled

### Scheduler warning on startup

```
WARNING Could not start scheduler: no such table: monitoring_scheduled_scans
```

Run migrations:
```bash
python admin/manage.py migrate
```

### Events not being sent

- Check that event monitors started (look for "[OK] 4 event monitors active" in client output)
- If offline, events are queued to disk and will be replayed when reconnected

## License

Internal use.
