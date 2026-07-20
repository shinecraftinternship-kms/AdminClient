# System Scanner Pro - Admin Server

AI-powered distributed endpoint monitoring admin panel with real-time dashboard, client management, scheduled scanning, JWT security, and predictive analytics.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x + DRF 3.15 + Django Channels 4.x |
| Database | SQLite (dev) / Supabase PostgreSQL (production) |
| WebSocket | Django Channels (InMemoryChannelLayer, Redis for production) |
| Scheduler | APScheduler 3.x |
| Auth | JWT (PyJWT) + Session + API Keys |
| Frontend | Django templates + vanilla JS + Bootstrap 5.3 + Chart.js |
| Reports | ReportLab (PDF) + Python csv (CSV) |
| Vercel Adapter | Mangum (WSGI → Lambda) |

## Project Structure

```
admin/
├── main.py                 # Entry point — starts Django server
├── manage.py               # Django management commands
├── requirements.txt        # Python dependencies
├── django_admin/
│   ├── settings.py         # Django settings (DB, auth, channels)
│   ├── urls.py             # URL routing
│   ├── wsgi.py             # WSGI application
│   └── asgi.py             # ASGI application (WebSocket)
├── scanner_api/
│   ├── views.py            # REST API views
│   ├── urls.py             # API URL patterns
│   ├── models.py           # Database models
│   ├── middleware.py        # Session timeout, security headers
│   ├── auth.py             # JWT + API key authentication
│   └── supabase_client.py  # Supabase cloud discovery
├── monitoring/
│   ├── views.py            # Monitoring dashboard views
│   ├── models.py           # Alerts, schedules, device health
│   └── consumers.py        # WebSocket consumers
├── maintenance/            # Maintenance scheduling module
├── intelligence/           # AI analytics dashboard module
├── templates/              # HTML templates (Bootstrap 5)
├── static/                 # CSS, JS, images
└── data/                   # SQLite database (dev only)
```

## Local Development

### Prerequisites

- Python 3.10+
- pip

### 1. Install Dependencies

```bash
cd admin-client
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
cp .env.template .env
```

Edit `.env` with your values:

| Variable | Purpose | Required |
|----------|---------|----------|
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `DJANGO_DEBUG` | Debug mode (`True`/`False`) | Yes |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts (`*` for all) | Yes |
| `DB_NAME` | PostgreSQL database name | For production |
| `DB_USER` | PostgreSQL username | For production |
| `DB_PASSWORD` | PostgreSQL password | For production |
| `DB_HOST` | PostgreSQL host | For production |
| `DB_PORT` | PostgreSQL port (default: 5432) | For production |
| `SUPABASE_URL` | Supabase project URL | Optional |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Optional |

### 3. Start the Server

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

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port PORT` | Server port | 80 |
| `--host HOST` | Bind address | Prompts on first run |
| `--debug` | Enable Django debug mode | False |
| `--username NAME` | Default admin username | admin |
| `--password PASS` | Default admin password | admin123 |
| `--reset` | Re-ask for bind IP | — |

---

## Vercel Deployment

### Architecture

Vercel deploys the admin as a **serverless Django application** using [Mangum](https://mangum.io/) to adapt WSGI to AWS Lambda. The entry point is `api/index.py`.

```
Vercel Edge Network
    ├── /static/*  → Static files (CSS, JS, images)
    └── /*         → api/index.py (Mangum → Django WSGI)
```

### Prerequisites

1. A **Vercel account** (free tier works)
2. A **GitHub repository** with this code
3. A **Supabase project** with a PostgreSQL database (free tier works)

### Step-by-Step Deployment

#### 1. Set Up Supabase Database

1. Go to [supabase.com](https://supabase.com) and create a project
2. In the SQL Editor, run the migrations:
   ```sql
   -- The admin server will auto-migrate on first boot,
   -- but for Vercel you need to pre-create tables.
   -- Copy the SQL from setup_cloud_discovery.sql and run it.
   ```
3. Note your database credentials:
   - Host: `db.your-project.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - User: `postgres`
   - Password: (from project settings)

#### 2. Connect Repository to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Framework Preset: **Other**
4. Root Directory: `./` (the repo root, NOT the admin/ folder)

#### 3. Configure Build Settings

| Setting | Value |
|---------|-------|
| Build Command | `echo done` |
| Output Directory | `.` |
| Install Command | `pip install -r requirements.txt` |

> The existing `vercel.json` in the repo root already handles routing.

#### 4. Set Environment Variables in Vercel

Go to your Vercel project → **Settings → Environment Variables** and add:

| Variable | Value |
|----------|-------|
| `DJANGO_SECRET_KEY` | A long random string (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` ) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `*` |
| `DATABASE_URL` | `postgresql://postgres:YOUR_PASSWORD@db.your-project.supabase.co:5432/postgres` |
| `DB_NAME` | `postgres` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | Your Supabase database password |
| `DB_HOST` | `db.your-project.supabase.co` |
| `DB_PORT` | `5432` |
| `SUPABASE_URL` | `https://your-project.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Your Supabase service role key |

Set these for **all environments** (Production, Preview, Development).

#### 5. Deploy

Push to your repository's main branch. Vercel will auto-deploy.

```bash
git add .
git commit -m "Deploy admin to Vercel"
git push
```

Your admin panel will be live at: `https://your-project.vercel.app`

#### 6. Run Initial Migration

After deployment, you need to create the database tables. Open the Vercel terminal or run locally with the production database:

```bash
# Set the same env vars locally, then:
python admin/manage.py migrate
```

Or add a one-time migration script in Vercel's build step.

#### 7. Create Admin User

```bash
python admin/manage.py createsuperuser
```

### Vercel Limitations

| Feature | Status | Workaround |
|---------|--------|------------|
| REST API | Works | Full functionality |
| Static Files | Works | Served via `/static/` route |
| Sessions / Auth | Works | Uses database-backed sessions |
| WebSocket | **Not supported** | Vercel serverless doesn't support long-lived connections. Use a separate WebSocket server (e.g., Railway, Render) or use polling |
| UDP Auto-Discovery | **Not supported** | Clients must connect via URL directly |
| APScheduler | **Not supported** | Use Vercel Cron Jobs or external scheduler (e.g., cron-job.org) to call API endpoints |
| SQLite | **Not supported** | Use Supabase PostgreSQL (serverless is stateless) |
| Django manage.py shell | **Not supported** | Use Supabase SQL Editor or connect via `psql` |

### Vercel Cron Jobs (for Scheduled Scans)

Add to `vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/cron/health-check",
      "schedule": "*/5 * * * *"
    }
  ]
}
```

Then create the endpoint in `api/cron/health_check.py` that calls the health check logic.

### Static Files on Vercel

Static files are served from `admin/static/`. The `vercel.json` routes `/static/*` to this directory. Make sure to run `collectstatic` before deploying:

```bash
python admin/manage.py collectstatic --noinput
```

### Updating the Deployed Admin

```bash
git add .
git commit -m "Update admin"
git push
```

Vercel auto-deploys on every push to main.

---

## Dashboard Pages

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

### Admin

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/users` | List admin users |
| POST | `/api/admin/users` | Create admin user |
| DELETE | `/api/admin/users/<id>` | Delete admin user |
| GET | `/api/admin/stats` | System statistics |
| GET/PUT | `/api/settings` | Global settings |

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
python admin/manage.py collectstatic        # Collect static files (for deployment)
```

## Domain Name Setup

### Option 1: Custom Domain on Vercel

1. Go to Vercel project → **Settings → Domains**
2. Add your domain (e.g., `scanner.yourcompany.com`)
3. Update DNS records as instructed by Vercel
4. Update `DJANGO_ALLOWED_HOSTS` env var to include your domain

### Option 2: Nginx Reverse Proxy (Self-Hosted)

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

## Troubleshooting

### Vercel: 502 Bad Gateway
- Check that `api/index.py` and `mangum` are in `requirements.txt`
- Verify environment variables are set correctly in Vercel dashboard

### Vercel: Static files not loading
- Run `python admin/manage.py collectstatic --noinput` locally before pushing
- Check `vercel.json` routes for static files

### Vercel: Database connection refused
- Ensure `DATABASE_URL`, `DB_HOST`, `DB_PASSWORD` are correct
- Check Supabase project is active (not paused on free tier)
- Verify your IP is allowed in Supabase connection settings

### WebSocket not connecting
- Vercel does not support WebSocket. Deploy a separate WebSocket server or use polling mode

### Scheduler warning on startup
```bash
python admin/manage.py migrate
```

### Client can't reach Vercel-deployed admin
- Use the full Vercel URL: `https://your-project.vercel.app`
- Ensure the URL doesn't have a trailing slash
- Check that `DJANGO_ALLOWED_HOSTS` includes `*` or your Vercel domain

## Environment Variables Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | insecure default |
| `DJANGO_DEBUG` | Debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hostnames | `*` |
| `DATABASE_URL` | Full PostgreSQL connection string | — (uses SQLite) |
| `DB_NAME` | PostgreSQL database name | — |
| `DB_USER` | PostgreSQL username | — |
| `DB_PASSWORD` | PostgreSQL password | — |
| `DB_HOST` | PostgreSQL host | — |
| `DB_PORT` | PostgreSQL port | `5432` |
| `SUPABASE_URL` | Supabase project URL | — |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | — |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret | — |

## License

Internal use.
