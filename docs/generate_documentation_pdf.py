"""Generate the System Scanner Pro full-project documentation PDF.

Run from the project root:
    python docs/generate_documentation_pdf.py

Requires: pip install reportlab
Output: docs/SystemScanner_Project_Documentation.pdf
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "SystemScanner_Project_Documentation.pdf")
VERSION = "3.0"
GENERATED = datetime.now().strftime("%B %d, %Y")

BRAND = colors.HexColor("#0f2b46")
ACCENT = colors.HexColor("#1d6fb8")
LIGHT = colors.HexColor("#eef4fb")
MID = colors.HexColor("#8aa5c4")
GRID = colors.HexColor("#d8e2ee")
GOOD = colors.HexColor("#1d7a46")
WARN = colors.HexColor("#b7791f")
BAD = colors.HexColor("#b02a37")
CODE_BG = colors.HexColor("#f4f6f9")

PAGE_W, PAGE_H = A4
MARGIN = 1.6 * cm


def para(text, style=None):
    if style is None:
        style = BODY
    return Paragraph(text, style)


def h1(text):
    return KeepTogether([Spacer(1, 6), para(text, H1), Spacer(1, 2)])


def h2(text):
    return KeepTogether([Spacer(1, 4), para(text, H2), Spacer(1, 1)])


def h3(text):
    return KeepTogether([Spacer(1, 2), para(text, H3)])


def bullets(items):
    flow = [para("", BODY)]
    for it in items:
        flow.append(para("&#8226;&nbsp;&nbsp;" + it, BODY))
    return flow


def code_block(text):
    lines = [("&nbsp;&nbsp;" + l) if l.strip() else "&nbsp;" for l in text.splitlines()]
    style = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=8.4, leading=11)
    wrapped = []
    for l in lines:
        txt = l.replace("&nbsp;", "\u00a0").replace("&#8226;", "\u2022")
        for line in simpleSplit(txt, "Courier", 9, PAGE_W - 2 * MARGIN - 18):
            wrapped.append(line)
    table_rows = [[para(x, style)] for x in wrapped]
    t2 = Table(table_rows, colWidths=[PAGE_W - 2 * MARGIN])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
    ]))
    return t2


def endpoint_table(rows, widths=None):
    if widths is None:
        widths = [1.1 * cm, 6.6 * cm, PAGE_W - 2 * MARGIN - 7.7 * cm]
    header = [para("<b>Method</b>", TH), para("<b>Endpoint</b>", TH), para("<b>Purpose</b>", TH)]
    body = [header]
    method_colors = [BRAND]
    for row in rows:
        m, e = row[0], row[1]
        p = row[2] if len(row) > 2 else ""
        method_bg = ACCENT
        if m.upper() in ("POST",):
            method_bg = GOOD
        elif m.upper() in ("PUT", "PATCH"):
            method_bg = WARN
        elif m.upper() == "DELETE":
            method_bg = BAD
        body.append([
            para(f"<b>{m.upper()}</b>", ParagraphStyle("m", parent=TH, textColor=colors.white, alignment=TA_CENTER)),
            para(e, CODE_STYLE),
            para(p, BODY),
        ])
        method_colors.append(method_bg)
    t = Table(body, colWidths=widths, repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]
    for i in range(1, len(body)):
        style.append(("BACKGROUND", (0, i), (0, i), method_colors[i]))
    t.setStyle(TableStyle(style))
    return t


def field_table(rows):
    header = [para("<b>Field</b>", TH), para("<b>Type</b>", TH), para("<b>Purpose</b>", TH)]
    body = [header]
    for f, t, d in rows:
        body.append([para(f, CODE_STYLE), para(t, BODY), para(d, BODY)])
    t = Table(body, colWidths=[3.2 * cm, 3.2 * cm, PAGE_W - 2 * MARGIN - 6.4 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return t


styles = getSampleStyleSheet()
TITLE = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold",
                       fontSize=30, leading=36, textColor=colors.white, alignment=0)
SUBTITLE = ParagraphStyle("Subtitle", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=13, leading=18, textColor=colors.HexColor("#cfe0f2"))
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=16, leading=20, textColor=BRAND, spaceBefore=10, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=12.5, leading=16, textColor=ACCENT, spaceBefore=8, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold",
                    fontSize=11, leading=14, textColor=BRAND, spaceBefore=6, spaceAfter=2)
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=9.5, leading=13, alignment=TA_JUSTIFY, spaceAfter=4)
TH = ParagraphStyle("TH", parent=styles["Normal"], fontName="Helvetica-Bold",
                    fontSize=9, leading=11, textColor=colors.white)
CODE_STYLE = ParagraphStyle("Code", parent=styles["Normal"], fontName="Courier",
                            fontSize=8.6, leading=11)
NOTE = ParagraphStyle("Note", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=9, leading=12, textColor=BRAND, backColor=LIGHT,
                      borderPadding=6, borderColor=ACCENT, borderWidth=0.5, spaceAfter=6)
SMALL = ParagraphStyle("Small", parent=styles["Normal"], fontName="Helvetica",
                       fontSize=8, leading=10, textColor=MID)


def cover_story():
    return [
        Spacer(1, 3.2 * cm),
        para("SYSTEM SCANNER PRO", TITLE),
        para("v" + VERSION, ParagraphStyle("ver", parent=SUBTITLE, fontSize=16, textColor=ACCENT)),
        Spacer(1, 0.5 * cm),
        para("AI-Powered Distributed Endpoint Monitoring and Remote Scanning Platform", SUBTITLE),
        Spacer(1, 0.3 * cm),
        para("Full Project Documentation &#8212; Architecture, Client Connection Lifecycle, ",
             ParagraphStyle("sub2", parent=SUBTITLE, fontSize=11, textColor=colors.HexColor("#a9c4dd"))),
        para("API Reference, Data Models, Security, Deployment &amp; Operations",
             ParagraphStyle("sub3", parent=SUBTITLE, fontSize=11, textColor=colors.HexColor("#a9c4dd"))),
        Spacer(1, 4.6 * cm),
        para(f"Generated {GENERATED}", ParagraphStyle("gen", parent=SMALL, textColor=colors.HexColor("#7f97b3"))),
    ]


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 0.6 * cm, PAGE_W, 0.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, PAGE_H - 0.42 * cm, "SYSTEM SCANNER PRO  \u2014  PROJECT DOCUMENTATION")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.42 * cm, f"v{VERSION}")
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, 0.85 * cm, PAGE_W - MARGIN, 0.85 * cm)
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 0.6 * cm, "System Scanner Pro \u2014 Internal Documentation")
    canvas.drawRightString(PAGE_W - MARGIN, 0.6 * cm, f"Page {doc.page}")
    canvas.restoreState()


def footer_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 0.6 * cm, PAGE_W, 0.6 * cm, stroke=0, fill=1)
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.4 * cm, bottomMargin=1.3 * cm,
        title=f"System Scanner Pro v{VERSION} \u2014 Project Documentation",
        author="System Scanner Pro",
        subject="Full project documentation",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    cover_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="cover")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=footer_cover),
        PageTemplate(id="Content", frames=[frame], onPage=header_footer),
    ])

    E = []
    E.extend(cover_story())
    E.append(PageBreak())

    # ── 1. Overview ──────────────────────────────────────────────────────
    E.append(h1("1. Project Overview"))
    E.append(para(
        "System Scanner Pro is an AI-powered distributed endpoint monitoring and remote scanning platform. "
        "It pairs a centralized Django admin server with lightweight Python client agents that run on every "
        "managed machine. Agents collect hardware and software inventory, stream real-time heartbeats, monitor "
        "system events (USB, files, processes, software), and execute scheduled or on-demand scans. "
        "The admin dashboard provides fleet-wide visibility with live WebSocket updates, change detection, "
        "alerts, predictive analytics, and report generation.", BODY))
    E.append(h2("Key Capabilities"))
    E.extend(bullets([
        "<b>Distributed scanning</b> &#8212; one admin server, any number of client agents, cross-platform "
        "(Windows / Linux / macOS).",
        "<b>Real-time communication</b> &#8212; WebSocket command channel with automatic HTTP polling fallback.",
        "<b>Connection lifecycle management</b> &#8212; registration, approval, heartbeat monitoring, blocking, "
        "soft-delete and re-registration.  See section 3.",
        "<b>Event monitoring</b> &#8212; USB, file, process and software change detection with offline disk queue.",
        "<b>Scheduled scanning</b> &#8212; APScheduler-driven interval/daily/weekly/monthly scans with offline "
        "queue for unreachable devices.",
        "<b>AI-ready analytics</b> &#8212; anomaly detection, feature store, and predictive failure-risk scoring.",
        "<b>Reporting</b> &#8212; fleet / device / alert reports in PDF and CSV.",
        "<b>Security</b> &#8212; JWT auth, HMAC-signed agent traffic, API keys, RBAC and full audit logging.",
    ]))

    # ── 2. Architecture ──────────────────────────────────────────────────
    E.append(h1("2. Architecture"))
    E.append(code_block(
        "  ADMIN SERVER (Django)\n"
        "  |-- REST API (DRF)          |-- WebSocket Consumer\n"
        "  |-- Event Bus (pub/sub)     |-- APScheduler\n"
        "  |-- Anomaly Detection       |-- Feature Store\n"
        "  |-- Predictive Analytics    |-- Reports (PDF/CSV)\n"
        "  |-- SQLite / PostgreSQL\n"
        "        ^ TCP (HTTP + WebSocket)     ^ UDP (discovery, port 45000)\n"
        "  CLIENT AGENTS (1..N)\n"
        "  |-- Scanner (HW/SW)         |-- Event Monitors (USB/File/Proc/SW)\n"
        "  |-- Offline Queue (disk)    |-- Exponential Backoff\n"
        "  |-- Heartbeat Watchdog      |-- WebSocket client (real-time cmds)\n"
        "  |-- UDP discovery listener"
    ))
    E.append(h2("Components"))
    E.append(endpoint_table([
        ("", "<b>admin/</b>", "Django admin server: REST API, WebSocket consumers, scheduler, analytics, reports, templates."),
        ("", "<b>client/</b>", "Standalone agent: communicator, discovery, fingerprint, key management, scanner, event monitors."),
        ("", "<b>api/</b>", "Serverless entry point (Vercel) used for cloud registration/discovery."),
        ("", "<b>build/</b>", "PyInstaller build scripts producing admin and client executables."),
        ("", "<b>deploy/</b>", "Deployment helper scripts (Vercel / serverless)."),
    ]))

    # ── 3. Connection Lifecycle ──────────────────────────────────────────
    E.append(h1("3. Client Connection Lifecycle"))
    E.append(para(
        "The connection lifecycle is the core of the platform. A machine moves through "
        "<b>creation</b> (registration) &#8594; <b>approval</b> &#8594; <b>monitoring</b> (heartbeat / "
        "WebSocket) and finally <b>deletion</b>. Both sides &#8212; admin server and client agent &#8212; "
        "coordinate through a well-defined REST + WebSocket contract.", BODY))

    E.append(h2("3.1 Connection Creation (Registration)"))
    E.append(para(
        "On first run the client generates a registration key and a hardware fingerprint (persisted to "
        "<b>client_key.json</b>), discovers the admin URL (UDP broadcast, cloud discovery, or manual entry), "
        "and calls <font name='Courier'>POST /api/register</font>. The server logic is in "
        "<font name='Courier'>admin/scanner_api/views.py &#8594; RegisterClientView</font>."))
    E.append(code_block(
        "POST /api/register\n"
        "{\n"
        '  "registration_key":   "ABC123...",   # unique per installation\n'
        '  "hostname":           "DESKTOP-7X",\n'
        '  "platform":           "Windows",\n'
        '  "client_version":     "1.0.0",\n'
        '  "device_fingerprint": "A1B2..."        # motherboard+CPU+disk+MAC hash\n'
        "}\n"
        "200 -> {\"status\": \"ok\", \"auto_approved\": true|false}\n"
        "201 -> created; 403 -> key marked deleted (reinstall required)"
    ))
    E.append(para(
        "Registration resolution order: (1) if the key already exists the record is refreshed (hostname, "
        "IP, fingerprint, last-seen) and the previous approved state is preserved; (2) if the same hardware "
        "fingerprint already exists under a different key, the device is <b>re-registered</b> by re-pointing "
        "the old record to the new key (survives reinstall); (3) otherwise a brand-new <font name='Courier'>"
        "Client</font> row is created with status <b>pending</b> (or <b>online</b> if auto-approve is on)."))
    E.append(para(
        "Ownership: newly registered clients inherit the <b>company</b> and <b>owner</b> of the admin server "
        "client record, so fleet data stays partitioned per company.", NOTE))

    E.append(h2("3.2 Approval"))
    E.append(para(
        "Unless auto-approve is enabled in Settings, a registered client stays <b>pending</b> until an admin "
        "approves it. Approval flips <font name='Courier'>approved=True</font>, sets status online and assigns "
        "ownership. It can be done individually, in bulk, or automatically."))
    E.append(endpoint_table([
        ("POST", "/api/approve", "Approve a single client by registration_key."),
        ("POST", "/api/approve-multiple", "Bulk approve list of registration_keys."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/approve", "Approve via the monitoring module."),
        ("GET", "/api/clients/&lt;key&gt;/status", "Client-side poll: \"approved\" or \"pending\"."),
    ]))
    E.append(para(
        "Auto-approve is controlled by the <font name='Courier'>auto_approve</font> Setting (Settings page or "
        "<font name='Courier'>PUT /api/settings</font>).", NOTE))

    E.append(h2("3.3 Ongoing Connection (Heartbeat + WebSocket)"))
    E.append(para(
        "Once approved, the client maintains the connection through two parallel channels:"))
    E.extend(bullets([
        "<b>HTTP heartbeat</b> &#8212; every 30 seconds <font name='Courier'>POST /api/ping</font> "
        "(or <font name='Courier'>/api/monitoring/agent/heartbeat-public</font>). Refreshes "
        "<font name='Courier'>last_seen</font>, <font name='Courier'>last_ip</font>, hostname and version, and "
        "sets status online. Carries CPU/RAM/disk metrics.",
        "<b>WebSocket channel</b> &#8212; <font name='Courier'>ws://HOST/ws/agent/&lt;agent_id&gt;/</font>. "
        "Authenticated with HMAC signature + timestamp; used for real-time commands (scan_now, config_update) "
        "and event streaming. Falls back to HTTP polling if the upgrade is rejected (e.g. serverless).",
    ]))
    E.append(para(
        "Offline behaviour: if the admin is unreachable the client applies exponential backoff with jitter, "
        "persists events to a disk queue, and replays them on reconnect. The heartbeat watchdog restarts a "
        "crashed heartbeat thread automatically. A device is flagged <b>offline</b> when no heartbeat arrives "
        "within the stale threshold (default 120 s).", NOTE))

    E.append(h2("3.4 Connection Deletion"))
    E.append(para(
        "Deletion is a <b>soft delete</b>: the server sets <font name='Courier'>deleted=True</font> so the "
        "device vanishes from dashboards while its historical scans/audit trail remain for compliance. "
        "The deletion also publishes a <font name='Courier'>DEVICE_DELETED</font> event on the event bus "
        "(broadcast to live dashboards) and records an activity-log entry."))
    E.append(endpoint_table([
        ("DELETE", "/api/clients/&lt;key&gt;", "Delete a single client (soft delete)."),
        ("POST", "/api/clients/delete-multiple", "Bulk soft-delete list of registration_keys."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/block", "Block a device (deny re-registration/approval)."),
    ]))
    E.append(para(
        "After deletion, a re-registration attempt with the same key is rejected with 403 "
        "(\u201cClient has been removed. Reinstall required.\u201d). The fingerprint re-registration path is "
        "ignored once <font name='Courier'>deleted=True</font>, so the operator must un-block or re-register "
        "deliberately."))
    E.append(para(
        "Deletion is not a hard database purge. To permanently remove a device, delete the row directly or "
        "perform a full factory reset (section 8).", NOTE))

    E.append(h2("3.5 Connection Settings &amp; Reset"))
    E.append(para(
        "The server can publish its own connection URL and token that client agents use for auto-configuration."))
    E.append(endpoint_table([
        ("GET", "/api/settings/connection", "Return stored admin server URL + connection token."),
        ("POST", "/api/settings/connection", "Explicitly generate a new URL + token (never auto-generates)."),
        ("PUT", "/api/settings/connection", "Regenerate only the connection token."),
    ]))
    E.extend(bullets([
        "<b>Reset admin bind IP</b> &#8212; <font name='Courier'>python admin/main.py --reset</font>.",
        "<b>Reset a client admin URL</b> &#8212; delete <font name='Courier'>client_config.json</font> and "
        "re-run; or edit <font name='Courier'>admin_url</font> directly.",
        "<b>Re-register a client</b> &#8212; delete <font name='Courier'>client_key.json</font>; a new key is "
        "generated and the fingerprint re-links the device to the existing record.",
        "<b>Full reset</b> &#8212; delete the DB (<font name='Courier'>admin/data/scanner.db</font>) plus "
        "client key/config files, then restart both sides.",
    ]))

    # ── 4. Features ──────────────────────────────────────────────────────
    E.append(h1("4. Feature Set"))
    E.append(h2("4.1 Core Platform"))
    E.extend(bullets([
        "<b>Hardware scanning</b> &#8212; CPU, RAM, storage, motherboard, GPU, OS, network, software, "
        "peripherals, antivirus, Windows updates and user accounts (Windows/Linux/macOS).",
        "<b>Admin dashboard</b> &#8212; real-time overview with stats, charts, search/filter and bulk actions.",
        "<b>Change detection</b> &#8212; automatic diff between consecutive scans with change alerts.",
        "<b>Client management</b> &#8212; approval workflow, heartbeat monitoring, stale detection, grouping.",
    ]))
    E.append(h2("4.2 Real-Time (WebSocket)"))
    E.extend(bullets([
        "Live dashboard pushes device updates, alerts and health changes instantly.",
        "Agent command channel (scan_now, config_update).",
        "Event broadcasting of hardware/software changes to all connected dashboards.",
        "Graceful auto-reconnect on both server and client.",
    ]))
    E.append(h2("4.3 Client Event Monitoring"))
    E.append(endpoint_table([
        ("5 s", "USB Monitor", "Device insertion/removal (cross-platform)."),
        ("Real-time", "File Monitor", "Watchdog on critical system paths / Windows Event Log."),
        ("10 s", "Process Monitor", "New/terminated/suspicious processes."),
        ("60 s", "Software Monitor", "Installed/removed application changes."),
    ], widths=[1.9 * cm, 3.4 * cm, PAGE_W - 2 * MARGIN - 5.3 * cm]))
    E.append(para(
        "Events are batched and delivered over WebSocket (preferred) or HTTP (fallback). Offline events are "
        "persisted to disk and replayed on reconnect.", NOTE))
    E.append(h2("4.4 Scheduled Scanning &amp; AI"))
    E.extend(bullets([
        "APScheduler with interval, daily, weekly, monthly or once schedules.",
        "Offline scan queue &#8212; pending scans delivered when the device comes back.",
        "<b>Anomaly detection</b> &#8212; z-score (2.5&#963;), IQR (1.5&#215;), trend (50%), static thresholds "
        "and compound signals.",
        "<b>Predictive analytics</b> &#8212; disk-full time, failure-risk score (0-100), 30/60/90-day capacity "
        "forecast.",
        "<b>Feature store</b> &#8212; 20+ ML-ready features extracted per device.",
    ]))

    # ── 5. API Reference ─────────────────────────────────────────────────
    E.append(h1("5. REST API Reference"))
    E.append(para(
        "All endpoints below are relative to the admin base URL (e.g. <font name='Courier'>http://SERVER</font>)."))

    E.append(h2("5.1 Client Registration &amp; Communication"))
    E.append(endpoint_table([
        ("POST", "/api/register", "Register / refresh a client connection (creation)."),
        ("POST", "/api/approve", "Approve a single client."),
        ("POST", "/api/approve-multiple", "Bulk approve clients."),
        ("POST", "/api/ping", "Client heartbeat (online status + metrics)."),
        ("GET", "/api/clients/&lt;key&gt;/status", "Check approval status."),
    ]))
    E.append(h2("5.2 Client Deletion &amp; Management"))
    E.append(endpoint_table([
        ("GET", "/api/clients", "List non-deleted clients."),
        ("GET", "/api/clients/&lt;key&gt;", "Full client detail + scan diff."),
        ("DELETE", "/api/clients/&lt;key&gt;", "Soft-delete a client connection."),
        ("POST", "/api/clients/delete-multiple", "Bulk soft-delete clients."),
        ("PUT", "/api/clients/&lt;key&gt;/manual", "Update manual fields."),
        ("GET/POST", "/api/clients/&lt;key&gt;/addons", "List / add addon devices."),
        ("DELETE", "/api/clients/&lt;key&gt;/addons/&lt;id&gt;", "Remove an addon device."),
        ("GET/PUT", "/api/clients/&lt;key&gt;/scan-config", "Get / update scan interval + enabled."),
        ("POST", "/api/clients/&lt;key&gt;/scan-now", "Trigger an immediate scan."),
        ("GET", "/api/clients/&lt;key&gt;/scan-results", "Latest scan result."),
    ]))
    E.append(h2("5.3 Scan Management"))
    E.append(endpoint_table([
        ("POST", "/api/scan", "Submit scan data from a client."),
        ("POST", "/api/scan/local", "Scan the admin server machine."),
        ("POST", "/api/scan/all", "Trigger scan on all approved clients."),
        ("GET", "/api/scan/history", "List historical scans."),
    ]))
    E.append(h2("5.4 Monitoring Module"))
    E.append(endpoint_table([
        ("POST", "/api/monitoring/agent/register", "Agent (client) registration."),
        ("POST", "/api/monitoring/agent/heartbeat", "HMAC-signed agent heartbeat."),
        ("POST", "/api/monitoring/agent/heartbeat-public", "Public heartbeat (registration key only)."),
        ("POST", "/api/monitoring/agent/inventory", "Submit hardware/software inventory."),
        ("GET", "/api/monitoring/agent/version-check", "Check for newer agent versions."),
        ("GET", "/api/monitoring/agent/pending-scans", "Fetch queued scans for an agent."),
        ("GET", "/api/monitoring/dashboard", "Aggregate dashboard stats."),
        ("GET", "/api/monitoring/devices", "List monitored devices."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;", "Device detail."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/approve", "Approve device."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/block", "Block device (connection revocation)."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/metrics", "Device metrics."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/history", "Device history."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/alerts", "Device alerts."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/hardware", "Hardware inventory."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/software", "Software inventory."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/heartbeats", "Heartbeat history."),
        ("GET", "/api/monitoring/alerts", "List all alerts."),
        ("POST", "/api/monitoring/alerts/&lt;uuid&gt;/action", "Ack / resolve / dismiss alert."),
        ("POST", "/api/monitoring/devices/bulk", "Bulk device actions."),
    ]))
    E.append(h2("5.5 Scheduled Scanning"))
    E.append(endpoint_table([
        ("GET", "/api/monitoring/schedules/status", "Scheduler runtime status."),
        ("GET", "/api/monitoring/schedules/pending", "Pending scans."),
        ("GET/POST", "/api/monitoring/schedules", "List / create schedules."),
        ("GET/PUT/DELETE", "/api/monitoring/schedules/&lt;uuid&gt;", "Get / update / delete a schedule."),
        ("POST", "/api/monitoring/schedules/&lt;uuid&gt;/toggle", "Enable or disable a schedule."),
        ("GET", "/api/monitoring/schedules/&lt;uuid&gt;/history", "Schedule run history."),
    ]))
    E.append(h2("5.6 Reports"))
    E.append(endpoint_table([
        ("GET", "/api/monitoring/reports/fleet/pdf", "Fleet summary PDF."),
        ("GET", "/api/monitoring/reports/fleet/csv", "Fleet CSV export."),
        ("GET", "/api/monitoring/reports/device/&lt;uuid&gt;/pdf", "Device detail PDF."),
        ("GET", "/api/monitoring/reports/device/&lt;uuid&gt;/csv", "Device CSV export."),
        ("GET", "/api/monitoring/reports/alerts/pdf", "Alert history PDF."),
        ("GET", "/api/monitoring/reports/alerts/csv", "Alert history CSV."),
    ]))
    E.append(h2("5.7 Authentication &amp; Security"))
    E.append(endpoint_table([
        ("POST", "/api/auth/login", "Session login."),
        ("POST", "/api/auth/logout", "Session logout."),
        ("GET", "/api/auth/me", "Current user profile."),
        ("GET/PUT", "/api/auth/profile", "Get / update profile."),
        ("POST", "/api/auth/change-password", "Change password."),
        ("POST", "/api/auth/upload-avatar", "Upload profile avatar."),
        ("GET", "/api/auth/login-history", "Login history."),
        ("GET", "/api/auth/audit-logs", "Audit log trail."),
        ("GET", "/api/auth/active-sessions", "Active sessions."),
        ("POST", "/api/auth/token/obtain", "Obtain JWT access + refresh tokens."),
        ("POST", "/api/auth/token/refresh", "Refresh the access token."),
        ("POST", "/api/auth/token/verify", "Validate a token."),
        ("GET/POST", "/api/auth/api-keys", "List / create API keys."),
        ("DELETE", "/api/auth/api-keys/&lt;id&gt;", "Revoke an API key."),
        ("GET", "/api/admin/users", "List admin users."),
        ("POST", "/api/admin/users", "Create admin user."),
        ("DELETE", "/api/admin/users/&lt;id&gt;", "Delete admin user."),
        ("GET", "/api/admin/stats", "System statistics."),
    ]))
    E.append(h2("5.8 Settings &amp; Organizations"))
    E.append(endpoint_table([
        ("GET/PUT", "/api/settings", "Global settings (auto-approve, stale threshold, scan interval)."),
        ("GET/PUT", "/api/settings/organization", "Organization profile."),
        ("GET/PUT", "/api/settings/security", "Security settings."),
        ("GET/PUT", "/api/settings/notifications", "Notification settings."),
        ("GET/POST/PUT", "/api/settings/connection", "Connection URL + token management."),
        ("GET/PUT", "/api/settings/dashboard", "Dashboard widget settings."),
        ("GET", "/api/activity-log", "Recent activity log."),
        ("GET", "/api/groups", "List client groups."),
        ("POST", "/api/groups", "Create a client group."),
        ("DELETE", "/api/groups/&lt;id&gt;", "Delete a client group."),
    ]))
    E.append(h2("5.9 Organization Modules (Locations / Departments / Employees)"))
    E.append(endpoint_table([
        ("GET/POST", "/api/locations", "List / create locations."),
        ("GET/PUT/DELETE", "/api/locations/&lt;uuid&gt;", "Get / update / delete a location."),
        ("GET", "/api/locations/&lt;uuid&gt;/dashboard", "Location dashboard."),
        ("GET/POST", "/api/departments", "List / create departments."),
        ("GET/PUT/DELETE", "/api/departments/&lt;uuid&gt;", "Department CRUD."),
        ("GET/POST", "/api/employees", "List / create employees."),
        ("GET/PUT/DELETE", "/api/employees/&lt;uuid&gt;", "Employee CRUD."),
        ("GET", "/api/assignments", "Asset assignments."),
        ("GET", "/api/org/audit-logs", "Organization audit logs."),
        ("GET", "/api/org/stats", "Organization dashboard stats."),
    ]))
    E.append(h2("5.10 Asset Management"))
    E.append(endpoint_table([
        ("GET/POST", "/api/assets", "List / create assets."),
        ("GET/PUT/DELETE", "/api/assets/&lt;uuid&gt;", "Asset CRUD."),
        ("POST", "/api/assets/&lt;uuid&gt;/assign", "Assign asset to an employee."),
        ("POST", "/api/assets/&lt;uuid&gt;/return", "Return an assigned asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/transfer", "Transfer asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/retire", "Retire asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/dispose", "Dispose asset."),
        ("GET", "/api/assets/&lt;uuid&gt;/history", "Asset history."),
        ("GET", "/api/assets/&lt;uuid&gt;/qr", "Asset QR code."),
        ("GET", "/api/assets/dashboard", "Asset dashboard."),
        ("GET", "/api/assets/analytics", "Asset analytics."),
        ("GET", "/api/executive-analytics", "Executive analytics."),
        ("GET", "/api/global-search", "Global search."),
    ]))

    E.append(h2("5.11 WebSocket Endpoints"))
    E.append(endpoint_table([
        ("WS", "ws://HOST/ws/dashboard/", "Admin dashboard real-time updates (fleet events)."),
        ("WS", "ws://HOST/ws/agent/&lt;agent_id&gt;/", "Agent command/control channel (HMAC auth)."),
    ]))

    # ── 6. Data Models ───────────────────────────────────────────────────
    E.append(h1("6. Data Models"))
    E.append(h2("6.1 Client &amp; Fleet (scanner_api)"))
    E.append(field_table([
        ("Company", "Model", "Organization; isolates fleet data between tenants."),
        ("ClientGroup", "Model", "User-defined grouping for clients."),
        ("Client", "Model", "A registered device: key, fingerprint, approval, status, heartbeat fields, scan config."),
        ("ScanResult", "Model", "One scan payload per client; source of change detection."),
        ("AddonDevice", "Model", "Secondary devices attached to a client."),
        ("ActivityLog", "Model", "Auditable admin actions (approve, delete, scan, settings)."),
        ("Setting", "Model", "Key/value global or per-company settings."),
        ("AdministratorProfile", "Model", "Admin user profile + company binding."),
        ("AuditLog / LoginHistory / LoginAttempt", "Model", "Security and auth audit records."),
        ("DeviceFingerprint", "Model", "Hardware fingerprint registry."),
    ]))
    E.append(h2("6.2 Monitoring (monitoring)"))
    E.append(field_table([
        ("DeviceMonitoringInfo", "Model", "Monitored device record (agent_id, secret, status)."),
        ("HardwareInventory", "Model", "Structured hardware inventory payload."),
        ("SoftwareInventory", "Model", "Installed software snapshot."),
        ("DeviceHeartbeat", "Model", "Heartbeat history per device."),
        ("DeviceMetrics", "Model", "CPU/RAM/disk metric series."),
        ("DeviceHistory", "Model", "Event/history timeline per device."),
        ("DeviceAlert", "Model", "Alert record with severity + status."),
        ("AgentVersion / AgentSecret", "Model", "Agent release tracking and HMAC secrets."),
        ("ScheduledScan", "Model", "User-defined scan schedule (interval/daily/weekly/...)."),
        ("PendingScan", "Model", "Queued scan for an offline device."),
        ("ScanScheduleLog", "Model", "Log of schedule executions."),
    ]))

    # ── 7. Security ──────────────────────────────────────────────────────
    E.append(h1("7. Security"))
    E.append(endpoint_table([
        ("JWT", "Authentication", "Access/refresh token pairs for API access (PyJWT)."),
        ("API Keys", "Programmatic access", "Rate limiting + optional IP restrictions."),
        ("RBAC", "Authorization", "Super admin / admin / viewer permission classes."),
        ("HMAC", "Agent traffic", "Agent &harr; server messages signed with HMAC-SHA256."),
        ("Sessions", "Admin panel", "Cookie-based Django sessions for the dashboard."),
        ("Rate Limiter", "Monitoring", "Per-agent/endpoint rate limiting."),
    ]))
    E.extend(bullets([
        "All admin API views enforce company/owner visibility (data isolation).",
        "Every significant action writes an <font name='Courier'>ActivityLog</font> / audit record.",
        "Connection tokens are generated with <font name='Courier'>secrets.token_hex</font>.",
        "Secrets live in <font name='Courier'>.env</font>; the file is git-ignored.",
    ]))

    # ── 8. Setup & Operations ────────────────────────────────────────────
    E.append(h1("8. Setup &amp; Operations"))
    E.append(h2("8.1 Quick Start"))
    E.append(code_block(
        "cd admin-client\n"
        "pip install -r requirements.txt\n"
        "python admin/main.py                 # admin server on port 80\n"
        "python client/main.py                # client agent (any machine)\n"
        "\n"
        "Default admin login:  admin / admin123\n"
        "Dashboard:            http://localhost\n"
        "UDP discovery port:   45000"
    ))
    E.append(h2("8.2 Management Commands"))
    E.append(code_block(
        "python admin/manage.py migrate            # apply DB migrations\n"
        "python admin/manage.py scan_local         # scan the admin machine\n"
        "python admin/manage.py scan_all           # trigger scans on all clients\n"
        "python admin/manage.py stale_checker      # mark stale clients offline\n"
        "python admin/manage.py alert_checker      # evaluate offline alerts\n"
        "python admin/manage.py health_checker     # recompute health scores\n"
        "python admin/manage.py offline_detector   # mark offline devices\n"
        "python admin/manage.py createsuperuser    # create a Django superuser"
    ))
    E.append(h2("8.3 Reset Procedures"))
    E.append(endpoint_table([
        ("Reset admin IP", "python admin/main.py --reset", "Re-prompt for the bind address."),
        ("Reset admin password", "Delete admin/data/scanner.db then re-run", "Recreates DB + default admin."),
        ("Reset client", "Delete client/client_key.json", "New key + fingerprint re-link on re-run."),
        ("Reset client URL", "Delete client_config.json", "Re-prompts for the admin URL."),
        ("Full factory reset", "Delete DB + client key/config files", "Brand-new state on both sides."),
    ]))
    E.append(h2("8.4 Running as a Service"))
    E.append(code_block(
        "# Windows scheduled task\n"
        'schtasks /create /tn "SystemScanner" /tr "C:\\path\\SystemScannerClient.exe http://SERVER" /sc onstart\n'
        "\n"
        "# Linux systemd unit /etc/systemd/system/scanner-client.service\n"
        "[Service]\n"
        "ExecStart=/usr/bin/python3 /path/to/client/main.py http://SERVER\n"
        "Restart=always\n"
        "RestartSec=10\n"
        "\n"
        "# macOS launchd (~/Library/LaunchAgents/com.scanner.client.plist)\n"
        "<dict><key>RunAtLoad</key><true/><key>KeepAlive</key><true/></dict>"
    ))

    # ── 9. Configuration ─────────────────────────────────────────────────
    E.append(h1("9. Configuration"))
    E.append(h2("9.1 Environment Variables"))
    E.append(field_table([
        ("DJANGO_SECRET_KEY", "string", "Django secret key (override the insecure default in prod)."),
        ("DJANGO_DEBUG", "bool", "Django debug mode."),
        ("SUPABASE_DATABASE_URL", "postgres URL", "Optional PostgreSQL connection (else SQLite)."),
        ("SUPABASE_URL", "string", "Optional Supabase project URL for cloud discovery."),
    ]))
    E.append(h2("9.2 Network Ports"))
    E.append(endpoint_table([
        ("80 (TCP)", "Web + API + WebSocket", "Admin dashboard, REST API and WS upgrade."),
        ("45000 (UDP)", "Auto-discovery", "Server broadcasts; clients listen to find the admin."),
    ]))
    E.append(h2("9.3 Admin CLI Options"))
    E.append(endpoint_table([
        ("--port PORT", "Server port", "Default 80."),
        ("--host HOST", "Bind address", "Prompted on first run."),
        ("--debug", "Debug mode", "Enables Django debug."),
        ("--username / --password", "Default admin", "admin / admin123."),
        ("--reset", "Re-ask bind IP", "\u2014"),
    ]))
    E.append(h2("9.4 Database Locations"))
    E.append(endpoint_table([
        ("Development", "admin/data/scanner.db", "SQLite file next to the server."),
        ("Windows (packaged)", "%APPDATA%\\SystemScannerPro\\scanner.db", "Per-user app data."),
        ("Linux (packaged)", "~/.local/share/SystemScannerPro/scanner.db", "XDG data home."),
        ("macOS (packaged)", "~/Library/Application Support/SystemScannerPro/scanner.db", "App support dir."),
    ]))
    E.append(h2("9.5 Building Executables"))
    E.append(code_block(
        "pip install pyinstaller\n"
        "python build/build.py all      # build admin + client\n"
        "python build/build.py admin    # build admin only\n"
        "python build/build.py client   # build client only\n"
        "python build/build.py clean    # clean build artifacts\n"
        "\n"
        "SystemScannerAdmin.exe --port 8080 --username admin --password mypass\n"
        "SystemScannerClient.exe http://192.168.1.100:80"
    ))

    # ── 10. Deployment ───────────────────────────────────────────────────
    E.append(h1("10. Deployment"))
    E.append(h2("10.1 Vercel / Serverless"))
    E.extend(bullets([
        "<font name='Courier'>vercel.json</font> + <font name='Courier'>api/index.py</font> expose the Django "
        "app as a serverless function.",
        "WebSocket is unavailable on Vercel &#8212; clients automatically fall back to HTTP polling.",
        "Use PostgreSQL/Supabase (via <font name='Courier'>SUPABASE_DATABASE_URL</font>) since the file system "
        "is ephemeral.",
        "<font name='Courier'>python deploy_vercel.py</font> assists with deployment.",
    ]))
    E.append(h2("10.2 nginx Reverse Proxy (Production HTTPS)"))
    E.append(code_block(
        "server { listen 80; server_name scanner.yourcompany.com; "
        "return 301 https://$host$request_uri; }\n"
        "server { listen 443 ssl; server_name scanner.yourcompany.com;\n"
        "  ssl_certificate /etc/letsencrypt/live/scanner.yourcompany.com/fullchain.pem;\n"
        "  ssl_certificate_key /etc/letsencrypt/live/scanner.yourcompany.com/privkey.pem;\n"
        "  location / { proxy_pass http://127.0.0.1:80; "
        "proxy_set_header Host $host; proxy_set_header X-Forwarded-Proto $scheme; }\n"
        "  location /ws/ { proxy_pass http://127.0.0.1:80; proxy_http_version 1.1;\n"
        "    proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection \"upgrade\";\n"
        "    proxy_set_header Host $host; proxy_read_timeout 86400; } }\n"
        "\n"
        "sudo certbot --nginx -d scanner.yourcompany.com\n"
        "python admin/main.py --host 127.0.0.1 --port 80"
    ))
    E.append(h2("10.3 Cloud Discovery"))
    E.append(para(
        "The admin server can register itself with the cloud discovery registry so remote clients find it "
        "without a static IP or domain. Registration data lives in the Supabase/registry backend and is "
        "queried by the client during startup (<font name='Courier'>setup_cloud_discovery.sql</font> + "
        "<font name='Courier'>admin/main.py &#8594; register_with_cloud_discovery</font>)."))

    # ── 11. Troubleshooting ──────────────────────────────────────────────
    E.append(h1("11. Troubleshooting"))
    E.append(endpoint_table([
        ("Client cannot connect", "Verify server running, firewall allows port 80 TCP + 45000 UDP, and server binds 0.0.0.0."),
        ("Client \u201cConnection failed\u201d", "Admin offline or URL missing http:// prefix."),
        ("WebSocket not connecting", "Check port 80; if behind nginx ensure /ws/ proxy headers; check browser console."),
        ("Client stays Pending", "Approve from dashboard or enable auto-approve in Settings."),
        ("No live updates", "The \u201cLive\u201d badge must be green on the monitoring page; server needs WS enabled."),
        ("Scheduler warning (no such table)", "Run python admin/manage.py migrate."),
        ("Events not sent", "Verify \u201c[OK] 4 event monitors active\u201d in client output."),
    ], widths=[4.4 * cm, PAGE_W - 2 * MARGIN - 4.4 * cm]))

    # ── 12. Appendix ─────────────────────────────────────────────────────
    E.append(h1("12. Appendix"))
    E.append(h2("12.1 Scan Data Collected"))
    E.append(field_table([
        ("Processor", "Snapshot", "Manufacturer, model, serial, cores, threads, speed, cache."),
        ("RAM", "Snapshot", "Per-module manufacturer, capacity, serial, frequency, form factor."),
        ("Storage", "Snapshot", "Disks (model, serial, size, interface) + partitions (fs, mount)."),
        ("Motherboard", "Snapshot", "Manufacturer, model, serial, BIOS version."),
        ("GPU", "Snapshot", "Name, vendor, dedicated memory."),
        ("OS", "Snapshot", "Name, version, build, architecture, install date."),
        ("Network", "Snapshot", "Interfaces (name, MAC, IPv4, status)."),
        ("Peripherals", "Snapshot", "Keyboards, mice, audio, webcams, printers, USB devices."),
        ("Software", "Snapshot", "Installed apps (name, version, publisher)."),
        ("Windows Updates", "Snapshot", "KB IDs + descriptions (Windows only)."),
        ("Antivirus", "Snapshot", "AV products + firewall status (Windows only)."),
        ("User Accounts", "Snapshot", "Local user accounts."),
    ]))
    E.append(h2("12.2 Device Status Indicators"))
    E.append(endpoint_table([
        ("Online", "Green dot", "Heartbeats received (every 30 s)."),
        ("Offline", "Red dot", "No heartbeat for over the stale threshold (120 s)."),
        ("Pending", "Yellow dot", "Registered but not yet approved."),
        ("Blocked", "Purple dot", "Blocked by admin (connection revoked)."),
    ]))
    E.append(h2("12.3 Event Bus Event Types"))
    E.append(para(
        "hw_component_added, hw_component_removed, hw_component_modified, sw_installed, sw_removed, "
        "sw_version_changed, sw_unauthorized, sw_antivirus_removed, health_level_changed, "
        "health_score_updated, alert_created/acknowledged/resolved/dismissed, device_registered, "
        "device_status_changed, device_approved, device_blocked, device_deleted, device_offline, "
        "device_online, agent_version_changed, heartbeat_received, scan_completed, scan_scheduled.", BODY))
    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=0.7, color=GRID))
    E.append(Spacer(1, 3))
    E.append(para(
        "This document was generated from the project source and configuration. Connection creation and "
        "deletion behaviour is defined in <font name='Courier'>admin/scanner_api/views.py</font> "
        "(RegisterClientView, ClientDetailView.delete, DeleteMultipleView) and the client "
        "<font name='Courier'>client/communicator.py</font>.", SMALL))

    doc.build(E)

    pages = doc.page
    return pages


if __name__ == "__main__":
    pages = build()
    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"OK: {OUTPUT}")
    print(f"Pages: {pages}  |  Size: {size_kb:.1f} KB")
