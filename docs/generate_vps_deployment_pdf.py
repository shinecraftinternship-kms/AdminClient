"""Generate the System Scanner Pro VPS deployment guide PDF.

Run from the project root:
    python docs/generate_vps_deployment_pdf.py

Requires: pip install reportlab
Output: docs/VPS_Deployment_Guide.pdf
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    Paragraph,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "VPS_Deployment_Guide.pdf")
GENERATED = datetime.now().strftime("%B %d, %Y")

BRAND = colors.HexColor("#0f2b46")
ACCENT = colors.HexColor("#1d6fb8")
LIGHT = colors.HexColor("#eef4fb")
GRID = colors.HexColor("#d8e2ee")
MID = colors.HexColor("#8aa5c4")
CODE_BG = colors.HexColor("#f4f6f9")

PAGE_W, PAGE_H = A4
MARGIN = 1.6 * cm

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=18, leading=22, textColor=BRAND, spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13, leading=17, textColor=ACCENT, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontName="Helvetica",
                      fontSize=9.5, leading=13.5, spaceAfter=5)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12, bulletIndent=2, spaceAfter=3)
TH = ParagraphStyle("TH", parent=styles["Normal"], fontName="Helvetica-Bold",
                    fontSize=9, leading=11, textColor=colors.white)
CODE_STYLE = ParagraphStyle("CODE", parent=styles["Normal"], fontName="Courier",
                            fontSize=8.4, leading=11)
SMALL = ParagraphStyle("SMALL", parent=styles["Normal"], fontName="Helvetica",
                       fontSize=8, leading=10, textColor=MID)
TITLE = ParagraphStyle("TITLE", parent=styles["Title"], fontName="Helvetica-Bold",
                       fontSize=26, leading=32, textColor=colors.white)
SUBTITLE = ParagraphStyle("SUBTITLE", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=11.5, leading=16, textColor=colors.HexColor("#cfe0f2"))


def para(text, style=BODY):
    return Paragraph(text, style)


def h1(text):
    return KeepTogether([Spacer(1, 4), para(text, H1), Spacer(1, 1)])


def h2(text):
    return KeepTogether([Spacer(1, 3), para(text, H2), Spacer(1, 1)])


def bullets(items):
    flow = []
    for it in items:
        flow.append(Paragraph("&#8226;&nbsp;&nbsp;" + it, BULLET))
    return flow


def note(text):
    p = Paragraph(text, ParagraphStyle("note", parent=BODY, fontSize=9, leading=12,
                                       textColor=BRAND, backColor=LIGHT, borderPadding=6,
                                       borderColor=ACCENT, borderWidth=0.5, spaceAfter=6))
    return p


def code_block(text):
    lines = [("&nbsp;&nbsp;" + l) if l.strip() else "&nbsp;" for l in text.splitlines()]
    style = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=8.4, leading=11)
    wrapped = []
    for l in lines:
        txt = l.replace("&nbsp;", "\u00a0").replace("&#8226;", "\u2022")
        txt = txt.replace("<", "&lt;").replace(">", "&gt;")
        for line in simpleSplit(txt, "Courier", 9, PAGE_W - 2 * MARGIN - 18):
            wrapped.append(line)
    t = Table([[para(x, style)] for x in wrapped], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
    ]))
    return t


def info_table(rows, widths=None, key="Key"):
    if widths is None:
        widths = [4.4 * cm, PAGE_W - 2 * MARGIN - 4.4 * cm]
    body = [[para(f"<b>{key}</b>", TH), para("<b>Description</b>", TH)]]
    for k, v in rows:
        body.append([para(f"<b>{k}</b>", ParagraphStyle("k", parent=BODY, fontName="Helvetica-Bold")),
                     para(v, BODY)])
    t = Table(body, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return t


def url_table(rows, widths=None):
    if widths is None:
        widths = [8.6 * cm, PAGE_W - 2 * MARGIN - 8.6 * cm]
    body = [[para("<b>Format</b>", TH), para("<b>Purpose</b>", TH)]]
    for fmt, purpose in rows:
        body.append([para(fmt, CODE_STYLE), para(purpose, BODY)])
    t = Table(body, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return t


def problem_table(rows):
    body = [[para("<b>Symptom</b>", TH), para("<b>Fix</b>", TH)]]
    for s, f in rows:
        body.append([para(s, BODY), para(f, BODY)])
    t = Table(body, colWidths=[6.0 * cm, PAGE_W - 2 * MARGIN - 6.0 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return t


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 0.6 * cm, PAGE_W, 0.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, PAGE_H - 0.42 * cm, "SYSTEM SCANNER PRO  \u2014  VPS DEPLOYMENT GUIDE")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.42 * cm, "Production")
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, 0.85 * cm, PAGE_W - MARGIN, 0.85 * cm)
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 0.6 * cm, "System Scanner Pro \u2014 Internal Deployment Documentation")
    canvas.drawRightString(PAGE_W - MARGIN, 0.6 * cm, f"Page {doc.page}")
    canvas.restoreState()


def cover_decor(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 0.6 * cm, PAGE_W, 0.6 * cm, stroke=0, fill=1)
    canvas.restoreState()


story = []

# ── Cover ────────────────────────────────────────────────────────────────
story.append(Spacer(1, 3.0 * cm))
story.append(para("SYSTEM SCANNER PRO", TITLE))
story.append(para("VPS DEPLOYMENT GUIDE", ParagraphStyle("V", parent=SUBTITLE, fontSize=16,
                                                         textColor=ACCENT)))
story.append(Spacer(1, 0.5 * cm))
story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
story.append(Spacer(1, 0.6 * cm))
story.append(para(
    "Complete reference for running the admin server on a Linux VPS (Debian/Ubuntu): "
    "connection, directory layout, service format, connection URL formats, environment "
    "variables, database, firewall, TLS, and troubleshooting.", SUBTITLE))
story.append(Spacer(1, 0.6 * cm))
story.append(para(
    "The VPS hosts the Django + Daphne admin server behind nginx. Client agents connect "
    "over HTTPS + WebSocket to register, stream heartbeats, receive scheduled scans, and "
    "report scan data. A shared Supabase PostgreSQL database is used in production so "
    "multiple deployment targets (VPS and Vercel) see the same data.", SUBTITLE))
story.append(Spacer(1, 4.5 * cm))
story.append(para(f"Generated {GENERATED}", SMALL))
story.append(NextPageTemplate("main"))
story.append(PageBreak())

# ── 1. Overview ──────────────────────────────────────────────────────────
story.append(h1("1. Overview"))
story.append(info_table([
    ("Web server / reverse proxy", "nginx (public TCP 80/443)"),
    ("App server (ASGI)", "Daphne via <font face='Courier'>admin/main.py --asgi</font> "
                          "(binds <font face='Courier'>127.0.0.1:8000</font>)"),
    ("Database", "Supabase PostgreSQL (via <font face='Courier'>DATABASE_URL</font>)"),
    ("WebSocket", "Django Channels served by Daphne, proxied through nginx "
                  "<font face='Courier'>/ws/</font>"),
    ("Discovery", "UDP broadcast on port 45000 (LAN) + Supabase cloud registry (WAN)"),
    ("TLS", "certbot / Let's Encrypt"),
    ("Process manager", "systemd (<font face='Courier'>system-scanner-admin.service</font>)"),
]))

# ── 2. Prerequisites ─────────────────────────────────────────────────────
story.append(h1("2. Prerequisites"))
story.extend(bullets([
    "A VPS reachable from the internet (Debian/Ubuntu recommended)",
    "DNS <b>A record</b> pointing your domain at the VPS public IP",
    "Python 3.10+ available on the server",
    "Firewall open for TCP 80/443 and UDP 45000",
    "A Supabase project (PostgreSQL) with the schema installed "
    "(<font face='Courier'>setup_new_supabase.sql</font>)",
    "A populated <font face='Courier'>.env</font> next to the repo on the server",
]))

# ── 3. Connecting to the VPS ─────────────────────────────────────────────
story.append(h1("3. Connecting to the VPS (SSH)"))
story.append(para("Standard password / PEM-key SSH from any machine:"))
story.append(code_block(
    "# With password (or default key)\n"
    "ssh root@YOUR.VPS.IP\n"
    "\n"
    "# With a PEM private key (AWS / DigitalOcean / GCP style)\n"
    "ssh -i /path/to/key.pem ubuntu@YOUR.VPS.IP\n"
    "\n"
    "# With a specific port\n"
    "ssh -p 2222 root@YOUR.VPS.IP"))
story.append(para("Copy the project to the server (the install script expects it at "
                  "<font face='Courier'>/opt/scanner-admin</font>):"))
story.append(code_block(
    "# With scp\n"
    "scp -r ./admin-client root@YOUR.VPS.IP:/opt/scanner-admin\n"
    "\n"
    "# With rsync\n"
    "rsync -avP ./admin-client/ root@YOUR.VPS.IP:/opt/scanner-admin/"))
story.append(note("APP_DIR is <font face='Courier'>/opt/scanner-admin</font> by default. "
                  "Override it with the <font face='Courier'>APP_DIR</font> environment variable."))

# ── 4. Server Layout ─────────────────────────────────────────────────────
story.append(h1("4. Server Layout / Format"))
story.append(para("Once deployed, the server looks like this:"))
story.append(code_block(
    "/opt/scanner-admin                # APP_DIR (repo)\n"
    "|-- .env                          # secrets + configuration (required)\n"
    "|-- requirements.txt\n"
    "|-- admin/\n"
    "|   |-- main.py                   # entrypoint (Django + Daphne + discovery)\n"
    "|   |-- django_admin/\n"
    "|   |   |-- settings.py\n"
    "|   |   `-- asgi.py               # Channels ASGI app\n"
    "|   `-- scanner_api/              # models, views, supabase_client, ...\n"
    "|-- venv/                         # Python virtualenv\n"
    "`-- deploy/\n"
    "    |-- install.sh                # provisioning script (run as root)\n"
    "    |-- register_server.sh        # manual cloud-discovery registration\n"
    "    |-- nginx/scanner.conf        # reverse proxy template\n"
    "    `-- systemd/system-scanner-admin.service\n"
    "\n"
    "/etc/systemd/system/system-scanner-admin.service   # app is a systemd service\n"
    "/etc/nginx/sites-available/scanner.conf            # nginx site (symlinked into sites-enabled)"))

# ── 5. Environment Variables ─────────────────────────────────────────────
story.append(h1("5. Environment Variables (.env Format)"))
story.append(para("Copy <font face='Courier'>.env.template</font> to the server as "
                  "<font face='Courier'>.env</font>. All values are read by the systemd unit via "
                  "<font face='Courier'>EnvironmentFile=/opt/scanner-admin/.env</font>."))
story.append(code_block(
    "# Django\n"
    'DJANGO_SECRET_KEY="django-insecure-change-me-in-production-abc123"\n'
    "DJANGO_DEBUG=True\n"
    'DJANGO_ALLOWED_HOSTS="*"\n'
    "\n"
    "# Supabase PostgreSQL (Django ORM)\n"
    '# NOTE: direct db.<ref>.supabase.co is IPv6-only. For IPv4-only networks use\n'
    "# the Supavisor shared pooler (session mode, port 5432), username postgres.<ref>.\n"
    'DATABASE_URL="postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"\n'
    "\n"
    "# Supabase Client (Direct API queries)\n"
    'SUPABASE_URL="https://<project-ref>.supabase.co"\n'
    'SUPABASE_SERVICE_KEY="<service-role-jwt>"\n'
    'SUPABASE_JWT_SECRET="<jwt-secret>"'))
story.append(info_table([
    ("DJANGO_SECRET_KEY", "Django secret used to sign sessions / tokens"),
    ("DJANGO_DEBUG", "Set <font face='Courier'>False</font> in production"),
    ("DJANGO_ALLOWED_HOSTS", "Hosts allowed to serve the app "
                             "(<font face='Courier'>*</font> with <font face='Courier'>--host 0.0.0.0</font>)"),
    ("DATABASE_URL", "Postgres connection string for the Django ORM"),
    ("SUPABASE_URL", "Supabase REST host used by the client registry queries"),
    ("SUPABASE_SERVICE_KEY", "Service-role key for direct Supabase API calls"),
    ("SUPABASE_JWT_SECRET", "JWT secret for verifying Supabase tokens"),
]))
story.append(note("<b>Never commit .env to git.</b> .env is gitignored; only "
                  "<font face='Courier'>.env.template</font> is tracked."))

# ── 6. Server Components ─────────────────────────────────────────────────
story.append(h1("6. Server Components"))
story.append(h2("6.1 systemd service"))
story.append(code_block(
    "[Unit]\n"
    "Description=System Scanner Pro Admin Server (Daphne ASGI)\n"
    "After=network-online.target\n"
    "Wants=network-online.target\n"
    "\n"
    "[Service]\n"
    "Type=simple\n"
    "User=scanner\n"
    "Group=scanner\n"
    "WorkingDirectory=/opt/scanner-admin\n"
    "Environment=DJANGO_SETTINGS_MODULE=django_admin.settings\n"
    "EnvironmentFile=/opt/scanner-admin/.env\n"
    "# Daphne binds the private backend port; nginx proxies public 80/443 -> 8000.\n"
    "ExecStart=/opt/scanner-admin/venv/bin/python admin/main.py --host 127.0.0.1 --port 8000 --asgi --domain scanner.example.com\n"
    "Restart=on-failure\n"
    "RestartSec=5\n"
    "KillSignal=SIGINT\n"
    "\n"
    "[Install]\n"
    "WantedBy=multi-user.target"))
story.append(info_table([
    ("--host 127.0.0.1", "Bind only the private backend port (nginx proxies it)"),
    ("--port 8000", "Backend port nginx forwards to"),
    ("--asgi", "Serve with Daphne (WebSocket support)"),
    ("--domain scanner.example.com", "Registers <font face='Courier'>https://&lt;domain&gt;</font> "
                                     "in the Supabase cloud registry for WAN discovery"),
]))
story.append(h2("6.2 nginx"))
story.append(para("Templated from <font face='Courier'>deploy/nginx/scanner.conf</font>. "
                  "Responsibilities: HTTP → HTTPS redirect on port 80, TLS termination on 443 "
                  "(certbot certificates), reverse proxy REST + static to "
                  "<font face='Courier'>http://127.0.0.1:8000</font>, and WebSocket proxying "
                  "(<font face='Courier'>/ws/</font>) with Upgrade headers."))
story.append(url_table([
    ("/", "REST API + dashboard (proxy to 127.0.0.1:8000)"),
    ("/ws/", "WebSocket (real-time dashboard, agent commands); "
             "<font face='Courier'>proxy_read_timeout 86400</font> with Upgrade/Connection headers"),
    ("/static/", "Static assets (optional; whitenoise also serves them)"),
], widths=[3.4 * cm, PAGE_W - 2 * MARGIN - 3.4 * cm]))
story.append(h2("6.3 Install script"))
story.append(code_block(
    "# From the server, with the repo at /opt/scanner-admin\n"
    "cd /opt/scanner-admin\n"
    "DOMAIN=scanner.example.com ./deploy/install.sh"))
story.append(para("Performs: package install → service user creation → venv + pip install "
                  "→ systemd unit install → nginx site install → certbot TLS. Re-run it any "
                  "time to re-apply configuration."))

# ── 7. Connection URL Formats ────────────────────────────────────────────
story.append(h1("7. Connection URL Formats"))
story.append(h2("7.1 Admin dashboard"))
story.append(url_table([
    ("https://&lt;domain&gt;/", "Dashboard"),
    ("https://&lt;domain&gt;/login/", "Admin login (default: admin / admin123)"),
], widths=[9.4 * cm, PAGE_W - 2 * MARGIN - 9.4 * cm]))
story.append(h2("7.2 Client connect URL (paste-to-connect)"))
story.append(para("Each admin gets a unique connect URL that clients accept as a "
                  "command-line argument:"))
story.append(code_block(
    "https://<domain>/connect/<username>/<company>/"))
story.append(code_block(
    'python client/main.py https://scanner.example.com/connect/admin/mycompany/\n'
    'SystemScannerClient.exe https://scanner.example.com/connect/admin/mycompany/\n'
    "\n"
    "# Alternative - base admin URL (clients auto-parse it)\n"
    "python client/main.py https://scanner.example.com"))
story.append(note("The connect page is public; anyone visiting it sees connection instructions. "
                  "Clients still start as <b>pending</b> and require explicit admin approval."))
story.append(h2("7.3 WebSocket endpoints (real-time)"))
story.append(url_table([
    ("wss://&lt;domain&gt;/ws/dashboard/", "Admin dashboard real-time updates"),
    ("wss://&lt;domain&gt;/ws/agent/&lt;agent_id&gt;/", "Agent command / control channel"),
], widths=[11.0 * cm, PAGE_W - 2 * MARGIN - 11.0 * cm]))
story.append(para("In production use <font face='Courier'>wss://</font> (TLS). In development "
                  "on plain HTTP use <font face='Courier'>ws://</font>."))
story.append(h2("7.4 REST API base"))
story.append(para("All API routes live under <font face='Courier'>https://&lt;domain&gt;/api/...</font> "
                  "(registration, heartbeat, scan submit, monitoring, scheduling, JWT, reports). "
                  "See the README 'API Endpoints' table for the full list."))
story.append(h2("7.5 Ports"))
story.append(url_table([
    ("80 / TCP", "HTTP → HTTPS redirect"),
    ("443 / TCP", "HTTPS dashboard + API + WebSocket"),
    ("8000 / TCP", "Private backend (loopback only - do not expose this to the internet)"),
    ("45000 / UDP", "LAN auto-discovery (admin broadcasts, clients listen)"),
], widths=[4.6 * cm, PAGE_W - 2 * MARGIN - 4.6 * cm]))
story.append(h2("7.6 Database connection string format"))
story.append(code_block(
    "postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:6543/postgres?sslmode=require"))
story.append(info_table([
    ("User", "<font face='Courier'>postgres.&lt;project-ref&gt;</font> (session mode via Supavisor)"),
    ("Host", "<font face='Courier'>aws-0-&lt;region&gt;.pooler.supabase.com</font> (IPv4-friendly pooler)"),
    ("Port", "<font face='Courier'>6543</font> (session mode; transaction mode uses 5432)"),
    ("Database", "<font face='Courier'>postgres</font> (default database name)"),
    ("Param", "<font face='Courier'>sslmode=require</font> (always require TLS)"),
]))

# ── 8. Firewall ──────────────────────────────────────────────────────────
story.append(h1("8. Firewall"))
story.append(para("Open on the VPS:"))
story.append(code_block(
    "ufw allow 80/tcp    # HTTP\n"
    "ufw allow 443/tcp   # HTTPS\n"
    "ufw allow 45000/udp # client auto-discovery\n"
    "ufw enable"))

# ── 9. Client-to-Server Resolution ───────────────────────────────────────
story.append(h1("9. Client-to-Server Resolution Order"))
story.append(para("When a client starts, it finds the admin server in this order:"))
story.append(code_block(
    "1. Explicit connect URL / CLI argument  (https://<domain>/connect/.../)\n"
    "2. ADMIN_SERVER_URL environment variable\n"
    "3. Supabase cloud registry  (the VPS registers itself on startup via --domain)\n"
    "4. Cached client_config.json\n"
    "5. UDP LAN discovery  (port 45000, same network)\n"
    "6. Manual prompt"))

# ── 10. Cloud Discovery ──────────────────────────────────────────────────
story.append(h1("10. Cloud Discovery Registration"))
story.append(para("<b>Automatic (normal path):</b> the systemd unit passes "
                  "<font face='Courier'>--domain scanner.example.com</font>, and "
                  "<font face='Courier'>admin/main.py</font> calls "
                  "<font face='Courier'>register_server_in_registry(domain, 443, \"https\")</font> "
                  "on startup."))
story.append(para("<b>Manual (fallback):</b>"))
story.append(code_block(
    "cd /opt/scanner-admin\n"
    "./deploy/register_server.sh scanner.example.com        # https, port 443\n"
    "./deploy/register_server.sh 1.2.3.4 80 http            # IP with explicit port/protocol"))
story.append(note("<b>Only one production admin</b> should be registered in the cloud registry at a "
                  "time. A local/dev panel must NOT call <font face='Courier'>--cloud</font>, or clients "
                  "will bounce between two 'admin systems' and never see the correct server."))

# ── 11. Operational Tasks ────────────────────────────────────────────────
story.append(h1("11. Operational Tasks"))
story.append(h2("Start / stop / restart"))
story.append(code_block(
    "systemctl start system-scanner-admin\n"
    "systemctl stop system-scanner-admin\n"
    "systemctl restart system-scanner-admin\n"
    "systemctl --no-pager --full status system-scanner-admin"))
story.append(h2("Logs"))
story.append(code_block(
    "journalctl -u system-scanner-admin -f        # follow app logs\n"
    "tail -f /var/log/nginx/access.log            # nginx access log\n"
    "tail -f /var/log/nginx/error.log             # nginx error log"))
story.append(h2("Health check"))
story.append(code_block("curl -I https://<domain>/__health   # expect HTTP 200"))
story.append(h2("Apply a code update"))
story.append(code_block(
    "cd /opt/scanner-admin\n"
    "git pull                                   # pull new source\n"
    "venv/bin/pip install -r requirements.txt   # new dependencies\n"
    "python admin/manage.py migrate             # apply DB migrations\n"
    "systemctl restart system-scanner-admin     # restart the service\n"
    "nginx -t && systemctl reload nginx         # reload nginx if config changed"))
story.append(h2("Renew TLS"))
story.append(code_block(
    "certbot renew --dry-run    # test the Let's Encrypt auto-renew timer\n"
    "systemctl reload nginx"))

# ── 12. Troubleshooting ──────────────────────────────────────────────────
story.append(h1("12. Troubleshooting"))
story.append(problem_table([
    ("Client says 'Checking...' forever",
     "The client registered but needs <b>admin approval</b> on the dashboard. Check "
     "https://&lt;domain&gt;/ for a pending client."),
    ("Client can't reach the server",
     "Confirm the DNS A record points to the VPS IP; open TCP 80/443; check "
     "<font face='Courier'>systemctl status system-scanner-admin</font>."),
    ("Cloud discovery fails at startup",
     ".env missing or misconfigured SUPABASE_URL / SUPABASE_SERVICE_KEY; run "
     "<font face='Courier'>./deploy/register_server.sh</font>."),
    ("WebSocket won't connect",
     "Ensure the nginx /ws/ block has Upgrade/Connection: upgrade headers; use "
     "wss:// in production."),
    ("502 Bad Gateway",
     "Daphne is down (<font face='Courier'>systemctl restart system-scanner-admin</font>) "
     "or nginx isn't proxying to 127.0.0.1:8000."),
    ("Scheduler warning on startup",
     "Run <font face='Courier'>python admin/manage.py migrate</font>."),
    ("DB connection errors",
     "The direct db.&lt;ref&gt;.supabase.co host is IPv6-only - switch DATABASE_URL to the "
     "Supavisor pooler (see section 7.6)."),
    ("Two 'admin systems' / clients bouncing",
     "A dev panel called --cloud and registered itself. Only the single production admin "
     "should register in the registry."),
]))

doc = BaseDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=1.4 * cm, bottomMargin=1.4 * cm,
    title="System Scanner Pro - VPS Deployment Guide",
    author="System Scanner Pro",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[frame], onPage=cover_decor),
    PageTemplate(id="main", frames=[frame], onPage=page_decor),
])
doc.multiBuild(story)
print(f"PDF written: {OUTPUT}")