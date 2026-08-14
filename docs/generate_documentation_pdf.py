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
from reportlab.platypus.tableofcontents import TableOfContents

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
    p = para(text, H1)
    setattr(p, "_toc_entry", (0, text))
    return KeepTogether([Spacer(1, 6), p, Spacer(1, 2)])


def h2(text):
    p = para(text, H2)
    setattr(p, "_toc_entry", (1, text))
    return KeepTogether([Spacer(1, 4), p, Spacer(1, 1)])


def h3(text):
    p = para(text, H3)
    setattr(p, "_toc_entry", (2, text))
    return KeepTogether([Spacer(1, 2), p])


def bullets(items):
    flow = [para("", BODY)]
    for it in items:
        flow.append(para("&#8226;&nbsp;&nbsp;" + it, BODY))
    return flow


def note(text):
    return para(text, NOTE)


def code_block(text):
    lines = [("&nbsp;&nbsp;" + l) if l.strip() else "&nbsp;" for l in text.splitlines()]
    style = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=8.4, leading=11)
    wrapped = []
    for l in lines:
        txt = l.replace("&nbsp;", "\u00a0").replace("&#8226;", "\u2022")
        txt = txt.replace("<", "&lt;").replace(">", "&gt;")
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
        style.append(("BACKGROUND", (0, i), (0, i), method_bg))
    t.setStyle(TableStyle(style))
    return t


def field_table(rows, widths=None):
    if widths is None:
        widths = [3.2 * cm, 3.2 * cm, PAGE_W - 2 * MARGIN - 6.4 * cm]
    header = [para("<b>Field</b>", TH), para("<b>Type</b>", TH), para("<b>Purpose</b>", TH)]
    body = [header]
    for f, t, d in rows:
        body.append([para(f, CODE_STYLE), para(t, BODY), para(d, BODY)])
    tbl = Table(body, colWidths=widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return tbl


def kv_table(rows, widths=None):
    if widths is None:
        widths = [5.0 * cm, PAGE_W - 2 * MARGIN - 5.0 * cm]
    body = []
    for k, v in rows:
        body.append([para(f"<b>{k}</b>", ParagraphStyle("k", parent=BODY, fontName="Helvetica-Bold")), para(v, BODY)])
    tbl = Table(body, colWidths=widths)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return tbl


def component_table(rows):
    widths = [3.4 * cm, PAGE_W - 2 * MARGIN - 3.4 * cm]
    header = [para("<b>Component</b>", TH), para("<b>Description</b>", TH)]
    body = [header]
    for name, desc in rows:
        body.append([para(f"<b>{name}</b>", ParagraphStyle("c", parent=BODY, fontName="Helvetica-Bold")), para(desc, BODY)])
    tbl = Table(body, colWidths=widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]))
    return tbl


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


class DocTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, "_toc_entry"):
            level, text = getattr(flowable, "_toc_entry")
            self.notify("TOCEntry", (level, text, self.page))


def cover_story():
    return [
        Spacer(1, 3.2 * cm),
        para("SYSTEM SCANNER PRO", TITLE),
        para("v" + VERSION, ParagraphStyle("ver", parent=SUBTITLE, fontSize=16, textColor=ACCENT)),
        Spacer(1, 0.5 * cm),
        para("AI-Powered Distributed Endpoint Monitoring and Remote Scanning Platform", SUBTITLE),
        Spacer(1, 0.3 * cm),
        para("Complete System Documentation &#8212; every module, every connection, end to end.",
             ParagraphStyle("sub2", parent=SUBTITLE, fontSize=11, textColor=colors.HexColor("#a9c4dd"))),
        Spacer(1, 1.6 * cm),
        para(
            "This document explains the whole platform: the admin server, the client agents, "
            "the REST and WebSocket protocols that link them, the database, the analytics, "
            "the security model, and every way the pieces connect. Read the Connection "
            "Lifecycle (section 8) and How Everything Connects (section 15) for the full "
            "end-to-end picture.",
            ParagraphStyle("sub4", parent=SUBTITLE, fontSize=10, leading=15,
                           textColor=colors.HexColor("#cfe0f2"))),
        Spacer(1, 4.6 * cm),
        para(f"Generated {GENERATED}", ParagraphStyle("gen", parent=SMALL, textColor=colors.HexColor("#7f97b3"))),
    ]


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 0.6 * cm, PAGE_W, 0.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, PAGE_H - 0.42 * cm, "SYSTEM SCANNER PRO  \u2014  COMPLETE SYSTEM DOCUMENTATION")
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


def toc():
    t = TableOfContents()
    t.levelStyles = [
        ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=10.5, leading=16,
                       leftIndent=0, firstLineIndent=0, textColor=BRAND),
        ParagraphStyle("toc2", fontName="Helvetica", fontSize=9.5, leading=13,
                       leftIndent=16, firstLineIndent=0, textColor=colors.HexColor("#33516e")),
        ParagraphStyle("toc3", fontName="Helvetica", fontSize=8.5, leading=11,
                       leftIndent=30, firstLineIndent=0, textColor=MID),
    ]
    return t


# ─────────────────────────────────────────────────────────────────────────────
# 1. Executive Summary
# ─────────────────────────────────────────────────────────────────────────────
def s01(E):
    E.append(h1("1. Executive Summary"))
    E.append(para(
        "System Scanner Pro is an AI-powered distributed endpoint monitoring and remote scanning platform. "
        "It combines a centralized <b>Django admin server</b> with lightweight <b>Python client agents</b> "
        "that run on every managed machine. Agents collect hardware and software inventory, stream live "
        "metrics, monitor system events (USB, files, processes, software), and execute scheduled or "
        "on-demand scans. The admin dashboard provides fleet-wide visibility with real-time WebSocket "
        "updates, change detection, alerts, predictive analytics, and report generation."))
    E.append(h2("1.1 The One-Sentence Summary"))
    E.append(para(
        "One admin server centrally owns the fleet; many client agents report to it continuously; "
        "a two-channel protocol (REST for registration/heartbeats/scans, WebSocket for real-time "
        "commands and events) keeps both sides in sync; and an analytics layer turns the stream of "
        "inventory, metrics, and events into health scores, alerts, anomalies, and predictions."))
    E.append(h2("1.2 What This Document Covers"))
    E.extend(bullets([
        "<b>Architecture</b> &#8212; how the admin server, client agent, discovery services, and deployment "
        "targets fit together (section 3).",
        "<b>Connection lifecycle</b> &#8212; registration, approval, heartbeat, WebSocket, deletion, and reset "
        "(section 8). This is the heart of the platform.",
        "<b>Every module</b> &#8212; scanner_api, monitoring, intelligence, maintenance, and the client agent "
        "(sections 9&#8211;14).",
        "<b>End-to-end flows</b> &#8212; concrete scenarios showing which component calls which endpoint and "
        "which event fires next (section 15).",
        "<b>Security</b> &#8212; JWT, API keys, sessions, HMAC agent authentication, tenant isolation "
        "(section 16).",
        "<b>Full API and WebSocket reference</b> &#8212; every endpoint and every message (sections 17&#8211;18).",
        "<b>Operations</b> &#8212; deployment, building executables, configuration, administration, "
        "troubleshooting (sections 23&#8211;27).",
    ]))
    E.append(h2("1.3 How to Read This Document"))
    E.append(para(
        "If you want to understand the <b>concept and how everything links</b>, read sections 2&#8211;8 first, "
        "then section 15 (scenarios). If you are integrating or extending the API, read sections 9&#8211;12 "
        "with sections 17&#8211;18 as the reference. If you operate or deploy the system, read sections 5, "
        "6, 23&#8211;27. A glossary and appendices are at the end."))


# ─────────────────────────────────────────────────────────────────────────────
# 2. System Overview
# ─────────────────────────────────────────────────────────────────────────────
def s02(E):
    E.append(h1("2. System Overview"))
    E.append(h2("2.1 What It Does"))
    E.extend(bullets([
        "<b>Inventories machines</b> &#8212; CPU, RAM, storage, motherboard, GPU, OS, network, peripherals, "
        "software, antivirus, Windows updates, and user accounts.",
        "<b>Keeps machines visible</b> &#8212; heartbeats every 30 seconds, online/offline status, health "
        "scores, and live dashboards.",
        "<b>Detects change</b> &#8212; diffs between consecutive scans and reports added/removed/modified "
        "hardware and software.",
        "<b>Monitors behaviour</b> &#8212; USB insertions, critical file changes, process starts/stops, and "
        "software install/uninstall, streamed as events.",
        "<b>Acts remotely</b> &#8212; admin can push scan_now and config_update commands to any agent in "
        "real time over WebSocket.",
        "<b>Predicts problems</b> &#8212; disk-full time, failure-risk scores, and 30/60/90-day capacity "
        "forecasts from the metric stream.",
        "<b>Reports and exports</b> &#8212; fleet, device, and alert reports in PDF and CSV, plus a full "
        "report engine with scheduled reports.",
    ]))
    E.append(h2("2.2 Who It Is For"))
    E.extend(bullets([
        "<b>IT administrators</b> &#8212; fleet inventory, asset tracking, and remote scan control.",
        "<b>Security teams</b> &#8212; USB/process/software change monitoring, unauthorized software and "
        "antivirus-removal alerts.",
        "<b>Asset / compliance managers</b> &#8212; asset lifecycle, licenses, warranties, maintenance, "
        "compliance and audit trails.",
        "<b>Operations teams</b> &#8212; predictive failure risk and capacity planning.",
    ]))
    E.append(h2("2.3 Design Goals and Principles"))
    E.append(kv_table([
        ("Distributed first", "One admin server; any number of agents on Windows, Linux, or macOS."),
        ("Real-time first", "WebSocket for commands and events; HTTP only as a fallback."),
        ("Self-healing client", "Exponential backoff, offline queues, heartbeat watchdog, and re-discovery "
                               "keep the agent alive without operator help."),
        ("Data isolation", "Every admin server owns its own database; within a server, companies partition "
                           "fleet data and every action is tenant-scoped."),
        ("Approval before trust", "Devices are never silently accepted; an admin approves them, and "
                                   "re-approval is required after deletion."),
        ("Auditable", "Activity logs, device history, and immutable audit logs record who did what."),
        ("AI-ready", "A feature store and prediction pipeline are built in, ready to feed ML models."),
    ]))
    E.append(h2("2.4 Platform Scope"))
    E.append(kv_table([
        ("Admin server", "Django 5.x + DRF + Channels; runs on any host that can run Python 3.10+."),
        ("Client agent", "Python 3.10+ using only the standard library plus websockets and watchdog."),
        ("Databases", "SQLite for local/self-hosted; PostgreSQL (Supabase) for cloud/serverless."),
        ("Browsers", "Any modern browser; frontend is Django templates + vanilla JS + Bootstrap 5.3 + Chart.js."),
        ("Cloud targets", "Vercel (serverless Django via api/index.py) with automatic HTTP-polling fallback."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Architecture
# ─────────────────────────────────────────────────────────────────────────────
def s03(E):
    E.append(h1("3. System Architecture"))
    E.append(para(
        "The platform is split into two runtimes that talk over the network: the <b>admin server</b> "
        "(a Django application) and the <b>client agent</b> (a standalone Python process). A small set of "
        "auxiliary services supports them: UDP discovery, a cloud registry, and a serverless entry point."))
    E.append(h2("3.1 High-Level Architecture"))
    E.append(code_block(
        "                       ADMIN SERVER (Django)\n"
        "   +----------------------------------------------------------+\n"
        "   |  scanner_api  (REST core, auth, assets, org)             |\n"
        "   |  monitoring   (agents, devices, WS, scheduler, AI)       |\n"
        "   |  intelligence (alerts, notifications, reports, audit)    |\n"
        "   |  maintenance  (maintenance, warranties, licenses)        |\n"
        "   |  Event Bus (pub/sub) + APScheduler + Channels            |\n"
        "   |  SQLite  OR  PostgreSQL/Supabase                         |\n"
        "   +----+-------------------+----------------+----------------+\n"
        "        |                   |                |\n"
        "        | TCP  HTTP + WebSocket              | UDP (45000)\n"
        "        |                   |                |\n"
        "   +----+----------+  +-----+--------+  +----+----------+\n"
        "   | CLIENT AGENT |  | CLIENT AGENT |  |  UDP DISCOVERY |\n"
        "   | scanner      |  | ... (1..N)   |  |  broadcast     |\n"
        "   | monitors     |  | event queues |  |  listener      |\n"
        "   | websocket    |  | backoff      |  |                |\n"
        "   +-------------+  +--------------+  +----------------+\n"
        "        |\n"
        "   +----+----------------+   +------------------------------------+\n"
        "   | CLOUD REGISTRY      |   | VERCEL (serverless Django, when used)|\n"
        "   | (Supabase table     |   | api/index.py, HTTP only, polls      |\n"
        "   |  server_registry)   |   | WebSocket is auto-disabled          |\n"
        "   +---------------------+   +------------------------------------+"
    ))
    E.append(h2("3.2 Admin Server Components"))
    E.append(component_table([
        ("scanner_api", "Core Django app. Owns the Client / ScanResult / Setting models, the REST API at "
                        "/api/, authentication (session, cookie, JWT, API keys), middleware, tenant isolation, "
                        "and the organization + asset-management modules."),
        ("monitoring", "Monitoring app. Agent registration/heartbeat/inventory endpoints, device management, "
                       "alerts, WebSocket consumers, the event bus, APScheduler-based scheduled scanning, "
                       "anomaly detection, feature store, predictive analytics, health scoring, change "
                       "detection, and PDF/CSV reports."),
        ("intelligence", "AI/insight app. Cross-module alert management, notification centre, immutable "
                         "audit logs, compliance logs, a report engine with scheduled reports, and a "
                         "dashboard analytics snapshot."),
        ("maintenance", "Maintenance app. Maintenance records, warranties, downtime, software licenses, "
                        "license assignments, compliance records, and maintenance analytics."),
        ("django_admin", "Project configuration: settings.py, url routing, ASGI (Channels WebSocket) and "
                         "WSGI entry points."),
        ("Background threads", "UDP discovery listener/broadcaster (port 45000), admin self-client "
                               "heartbeat loop, admin self-scan, and cloud-registry refresh every 300 s."),
    ]))
    E.append(h2("3.3 Client Agent Components"))
    E.append(component_table([
        ("main.py", "Entry point. Resolves the admin URL, registers, waits for approval, runs the initial "
                    "scan, starts the heartbeat loop, WebSocket client, event monitors, and the scheduled "
                    "scan loop. Also handles background/autostart mode on Windows."),
        ("communicator.py", "HTTP client (Communicator) with exponential backoff and an in-memory offline "
                            "queue, plus the WebSocket client with auto-reconnect and Vercel detection."),
        ("config.py", "Loads/saves client_config.json, prompts for the admin URL, and performs UDP "
                      "discovery of the admin server."),
        ("discovery.py", "Queries the cloud registry (Supabase server_registry table) to find the admin "
                         "server's public address."),
        ("fingerprint.py", "Computes a stable hardware fingerprint from motherboard serial, CPU id, disk "
                           "serial, and MAC addresses, hashed with SHA-256."),
        ("key_manager.py", "Creates/persists the registration key and device fingerprint in client_key.json."),
        ("scanner.py", "Collects the full hardware/software inventory on Windows/Linux/macOS."),
        ("metrics.py", "Collects live CPU, RAM, disk, uptime, and network reachability for heartbeats."),
        ("events/", "USB, file, process, and software monitors plus the batching EventDispatcher with a "
                    "disk-persisted offline queue."),
    ]))
    E.append(h2("3.4 Communication Channels"))
    E.append(kv_table([
        ("REST (HTTP)", "Registration, approval status, heartbeat, scan submission, scan config, "
                        "monitoring agent register/heartbeat/inventory, pending scans, reports, and all "
                        "admin panel APIs. Uses JSON over HTTP(S)."),
        ("WebSocket (agent)", "ws://HOST/ws/agent/&lt;agent_id&gt;/ &#8212; authenticated with HMAC; the "
                              "admin sends scan_now/config_update/ping commands; the agent streams "
                              "heartbeats, scan results, and events."),
        ("WebSocket (dashboard)", "ws://HOST/ws/dashboard/ &#8212; pushes fleet events, alerts, and health "
                                  "changes to open admin dashboards in real time."),
        ("UDP discovery", "Port 45000. The admin broadcasts ADMIN_HERE and answers DISCOVER_ADMIN; agents "
                          "listen and switch to the discovered admin."),
        ("Cloud registry", "Supabase server_registry table. The admin publishes its public URL/IP; agents "
                           "query it when they cannot reach the admin directly."),
    ]))
    E.append(h2("3.5 End-to-End Data Flow"))
    E.append(para(
        "A single lifecycle flows through every subsystem. The arrows show where each hop is handled:"))
    E.append(code_block(
        "1. Agent starts -> key_manager (client_key.json) -> config (admin URL)\n"
        "2. Agent calls POST /api/register         (scanner_api.RegisterClientView)\n"
        "3. Agent polls POST /api/ping             (scanner_api.PingClientView)   [every 30 s]\n"
        "4. Agent registers monitoring identity    (monitoring.AgentRegisterView) -> AgentSecret\n"
        "5. Agent sends POST /api/monitoring/agent/heartbeat-public (metrics)\n"
        "6. Heartbeat -> DeviceHeartbeat row -> health score -> DeviceAlert checks\n"
        "   -> event bus events -> subscribers -> WebSocket broadcast to dashboards\n"
        "7. Agent submits scans (POST /api/scan or /api/monitoring/agent/inventory)\n"
        "   -> ScanResult / HardwareInventory / SoftwareInventory\n"
        "   -> change detection -> event bus -> alerts + notifications\n"
        "8. Admin pushes a command: scheduler or API -> notify_agent() -> WebSocket group\n"
        "   agent_<id> -> AgentConsumer.send_command -> agent runs scan_now\n"
        "9. Offline agent: schedules create PendingScan -> agent pulls on reconnect\n"
        "   via GET /api/monitoring/agent/pending-scans"
    ))
    E.append(h2("3.6 Deployment Topologies"))
    E.append(kv_table([
        ("Self-hosted (single host)", "Admin server on a LAN host bound to 0.0.0.0:80; agents on the same "
                                      "LAN use UDP auto-discovery. SQLite database."),
        ("VPS / dedicated", "Admin behind nginx with HTTPS; agents use the public domain/IP; optional "
                            "cloud-registry registration; SQLite or PostgreSQL."),
        ("Vercel serverless", "api/index.py adapts Django to serverless. PostgreSQL/Supabase required. "
                              "No WebSocket, no UDP, no APScheduler; agents fall back to HTTP polling."),
        ("Multi-tenant", "One server, many companies; every list/detail view is company-scoped and the "
                         "URL prefix /&lt;user&gt;-&lt;company&gt;/ reinforces isolation."),
    ]))
    E.append(h2("3.7 Networking and Ports"))
    E.append(endpoint_table([
        ("80 / custom (TCP)", "Web + API + WebSocket", "Admin dashboard, REST API, and WebSocket upgrade."),
        ("443 (TCP)", "HTTPS", "Production TLS (nginx or Vercel)."),
        ("45000 (UDP)", "Auto-discovery", "Admin broadcasts ADMIN_HERE and listens for DISCOVER_ADMIN."),
    ], widths=[3.2 * cm, 4.2 * cm, PAGE_W - 2 * MARGIN - 7.4 * cm]))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Technology Stack
# ─────────────────────────────────────────────────────────────────────────────
def s04(E):
    E.append(h1("4. Technology Stack"))
    E.append(kv_table([
        ("Backend", "Django 5.x, Django REST Framework 3.15, Django Channels 4.x (WebSocket), "
                    "APScheduler 3.x (scheduling)."),
        ("Database", "SQLite (default/self-hosted), PostgreSQL / Supabase (production/serverless) via "
                     "dj-database-url + psycopg2."),
        ("Authentication", "Django sessions, signed cookie fallback, JWT (PyJWT), API keys (SHA-256 "
                           "hashed), HMAC-SHA256 for agent traffic."),
        ("WebSocket", "Channels InMemoryChannelLayer (capacity 1000); Redis recommended for horizontal "
                      "scale but not required."),
        ("Frontend", "Django templates, vanilla JavaScript, Bootstrap 5.3, Chart.js."),
        ("Reports", "ReportLab (PDF), Python csv and openpyxl (XLSX), qrcode + Pillow (QR codes)."),
        ("Client agent", "Python 3.10+ standard library, websockets, watchdog."),
        ("Build", "PyInstaller 6.x (onefile executables for admin and client)."),
        ("Serverless", "Mangum (WSGI to Lambda) via api/index.py on Vercel."),
        ("Cloud registry", "Supabase REST (PostgREST) server_registry table."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 5. Repository Layout
# ─────────────────────────────────────────────────────────────────────────────
def s05(E):
    E.append(h1("5. Repository Layout"))
    E.append(para(
        "Everything lives in one repository. The layout below is the map used throughout this document."))
    E.append(code_block(
        "admin-client/\n"
        "|-- admin/                    # Admin server (Django)\n"
        "|   |-- main.py               #   Entry point: migrate, superuser, threads, runserver\n"
        "|   |-- manage.py             #   Django management commands\n"
        "|   |-- runtime.py            #   Frozen/data-dir helpers (packaged builds)\n"
        "|   |-- scanner.py            #   Local machine scan (admin self-scan)\n"
        "|   |-- scanner_api/          #   Core app: models, views, auth, middleware, assets/org\n"
        "|   |-- monitoring/           #   Agents, devices, WS, scheduler, AI, reports\n"
        "|   |-- intelligence/         #   Cross-module alerts, notifications, audit, reports\n"
        "|   |-- maintenance/          #   Maintenance, warranties, downtime, licenses\n"
        "|   |-- django_admin/         #   settings.py, urls.py, asgi.py, wsgi.py\n"
        "|   |-- templates/ static/    #   Admin panel HTML/JS/CSS\n"
        "|   `-- data/                 #   SQLite DB + installer artifacts (dev)\n"
        "|-- client/                   # Client agent (standalone Python)\n"
        "|   |-- main.py               #   Agent entry point\n"
        "|   |-- communicator.py       #   HTTP + WebSocket transport\n"
        "|   |-- config.py             #   Config + admin URL prompt + UDP discovery\n"
        "|   |-- discovery.py          #   Cloud registry discovery\n"
        "|   |-- fingerprint.py        #   Hardware fingerprint\n"
        "|   |-- key_manager.py        #   Registration key + fingerprint storage\n"
        "|   |-- scanner.py            #   Hardware/software inventory collection\n"
        "|   |-- metrics.py            #   Live CPU/RAM/disk metrics\n"
        "|   |-- events/               #   USB/file/process/software monitors + dispatcher\n"
        "|   `-- scans/                #   Local scan result backups\n"
        "|-- api/index.py              # Vercel serverless WSGI bootstrap\n"
        "|-- build_client.py           # PyInstaller build script (client + admin)\n"
        "|-- deploy_vercel.py          # Manual Vercel -> cloud-registry registration\n"
        "|-- setup_cloud_discovery.sql # Supabase server_registry schema\n"
        "|-- vercel.json  runtime.txt  # Vercel config\n"
        "|-- requirements.txt  .env.template\n"
        "|-- docs/                     # This document + generator\n"
        "`-- .github/workflows/        # Hourly cloud-registry safety-net workflow"
    ))
    E.append(h2("5.1 Two Runtimes, One Codebase"))
    E.append(para(
        "The admin folder and client folder are independent Python runtimes. The admin uses the full "
        "Django dependency stack from requirements.txt. The client deliberately depends on almost nothing: "
        "it uses the Python standard library for HTTP (urllib) and system probing, and optionally uses "
        "websockets and watchdog. This keeps the installed agent small, reliable, and easy to freeze into "
        "a single .exe with PyInstaller."))


# ─────────────────────────────────────────────────────────────────────────────
# 6. Quick Start
# ─────────────────────────────────────────────────────────────────────────────
def s06(E):
    E.append(h1("6. Quick Start"))
    E.append(h2("6.1 Prerequisites"))
    E.extend(bullets([
        "Python 3.10 or newer on the admin host and on every client machine.",
        "Network access between agents and the admin (TCP 80/custom for HTTP+WS, UDP 45000 for discovery).",
    ]))
    E.append(h2("6.2 Install"))
    E.append(code_block(
        "cd admin-client\n"
        "pip install -r requirements.txt"
    ))
    E.append(h2("6.3 Start the Admin Server"))
    E.append(code_block(
        "python admin/main.py\n"
        "\n"
        "# First run prompts for the bind IP (0.0.0.0 for all interfaces), then:\n"
        "# - runs migrations (creates admin/data/scanner.db)\n"
        "# - creates the default admin user  admin / admin123\n"
        "# - creates the admin self-client\n"
        "# - starts UDP discovery on port 45000 (listen + broadcast)\n"
        "# - registers the public IP in the cloud registry\n"
        "# - serves the dashboard on port 80\n"
        "\n"
        "# Dashboard:  http://localhost\n"
        "# Login:      admin / admin123"
    ))
    E.append(h2("6.4 Start a Client Agent"))
    E.append(code_block(
        "python client/main.py          # interactive: enter admin URL\n"
        "python client/main.py http://192.168.1.100:80   # or pass it directly\n"
        "\n"
        "# On first run the agent:\n"
        "# 1. Generates registration key + hardware fingerprint (client_key.json)\n"
        "# 2. Resolves the admin URL (argument / env / cloud / UDP / prompt)\n"
        "# 3. Registers (POST /api/register) and waits for approval\n"
        "# 4. Runs the initial hardware scan and submits it\n"
        "# 5. Registers its monitoring identity (AgentSecret)\n"
        "# 6. Starts the 30-second heartbeat loop\n"
        "# 7. Starts the WebSocket client (if supported)\n"
        "# 8. Starts USB/file/process/software event monitors"
    ))
    E.append(h2("6.5 Approve the Client"))
    E.extend(bullets([
        "Open the dashboard (http://localhost) and find the new client with a yellow Pending dot.",
        "Click Approve (single or bulk). Approval flips approved=True and status to online.",
        "If auto-approve is enabled in Settings, approval is automatic.",
    ]))
    E.append(h2("6.6 What Happens Next"))
    E.append(para(
        "After approval the agent reports heartbeats and metrics every 30 seconds, submits scheduled "
        "scans (default every hour), streams detected events, and can receive scan_now / config_update "
        "commands. The dashboard and monitoring pages update live through WebSocket. Section 15 walks "
        "through these flows in detail."))


# ─────────────────────────────────────────────────────────────────────────────
# 7. Core Concepts
# ─────────────────────────────────────────────────────────────────────────────
def s07(E):
    E.append(h1("7. Core Concepts"))
    E.append(h2("7.1 Client, Agent, Device"))
    E.append(kv_table([
        ("Client", "The server-side record of a machine: registration_key, fingerprint, approval, status, "
                   "last_seen, scan config, owner, and company."),
        ("Agent", "The client-side process running on a machine. It owns the registration key and "
                  "fingerprint and talks to the admin server."),
        ("Device (monitoring)", "The monitoring view of a client (DeviceMonitoringInfo), carrying "
                                "monitoring status, health, IP, OS, agent version, and heartbeat counters."),
        ("Monitoring agent", "The agent's identity in the monitoring module: an agent_id (UUID) paired "
                             "with an HMAC secret (AgentSecret)."),
    ]))
    E.append(h2("7.2 Registration Key vs Hardware Fingerprint"))
    E.append(para(
        "The <b>registration key</b> is an 8-character random identifier generated on first run and "
        "persisted in client_key.json. It is the address used by every HTTP call. The <b>hardware "
        "fingerprint</b> is a SHA-256 hash (truncated to 16 hex chars) of motherboard serial, CPU id, "
        "disk serial, and MAC addresses. It survives IP changes, hostname changes, and even re-installs, "
        "which lets the server re-link a re-registering machine to its existing record."))
    E.append(h2("7.3 Approval Workflow"))
    E.append(para(
        "New devices are pending until an admin approves them (unless auto-approve is on). Deletion is a "
        "soft delete; a deleted device that pings again is resurrected as <b>pending</b> and must be "
        "approved again. This is a strict trust model: no device is ever silently re-admitted."))
    E.append(h2("7.4 Heartbeat and Health"))
    E.append(para(
        "Every 30 seconds the agent pings the server. The server refreshes last_seen, marks the client "
        "online, stores a DeviceHeartbeat with CPU/RAM/disk metrics, recomputes the health score, and "
        "evaluates threshold alerts. If no heartbeat arrives within the stale threshold (default 120 s) "
        "the client is marked offline."))
    E.append(h2("7.5 Device States"))
    E.append(endpoint_table([
        ("Pending", "Registered, not approved", "Yellow dot; appears in dashboards, needs approval."),
        ("Online", "Heartbeating now", "Green dot; last heartbeat within the stale threshold."),
        ("Offline", "No heartbeat", "Red dot; last heartbeat beyond the stale threshold."),
        ("Blocked", "Admin revoked", "Purple dot; agent secrets deactivated, re-approval impossible "
                                     "until unblocked."),
        ("Maintenance / Inactive", "Operator set", "Used by the monitoring module for administrative "
                                                   "statuses."),
    ], widths=[3.0 * cm, 4.4 * cm, PAGE_W - 2 * MARGIN - 7.4 * cm]))
    E.append(h2("7.6 Companies and Tenants"))
    E.append(para(
        "A Company is the tenant entity. Every admin user is bound to a company through an "
        "AdministratorProfile. Clients, settings, groups, locations, departments, employees, and assets "
        "all carry a company foreign key, and every list/detail API is company-scoped. The UI enforces "
        "this with a URL prefix: /&lt;user&gt;-&lt;company&gt;/."))
    E.append(h2("7.7 The Admin Self-Client"))
    E.append(para(
        "The admin server also registers itself as a client (key ADMIN-&lt;hostname&gt;) so it appears on "
        "its own dashboard, keeps a heartbeat loop alive, and can run local scans of its host machine. "
        "Its key is stored in the Setting admin_client_key and its identity is skipped from fingerprint "
        "re-linking to avoid hijack."))


# ─────────────────────────────────────────────────────────────────────────────
# 8. Connection Lifecycle
# ─────────────────────────────────────────────────────────────────────────────
def s08(E):
    E.append(h1("8. Client Connection Lifecycle"))
    E.append(para(
        "The connection lifecycle is the core of the platform. A machine moves through <b>creation</b> "
        "(registration) &#8594; <b>approval</b> &#8594; <b>monitoring</b> (heartbeat + WebSocket) and "
        "finally <b>deletion</b>. Both sides coordinate through a well-defined REST + WebSocket contract. "
        "This section is the reference for how a machine becomes part of the fleet."))
    E.append(h2("8.1 Connection Creation (Registration)"))
    E.append(para(
        "On first run the client generates a registration key and hardware fingerprint (persisted to "
        "client_key.json), resolves the admin URL, and calls POST /api/register. The server logic lives "
        "in admin/scanner_api/views.py (RegisterClientView)."))
    E.append(code_block(
        "POST /api/register\n"
        "{\n"
        '  "registration_key":   "Q69REJ58",     # unique per installation\n'
        '  "hostname":           "DESKTOP-7X",\n'
        '  "platform":           "Windows",\n'
        '  "client_version":     "1.6.1",\n'
        '  "device_fingerprint": "3BB3C334AF6021BF"   # motherboard+CPU+disk+MAC hash\n'
        "}\n"
        "200 -> {\"status\": \"ok\", \"approved\": true|false, \"auto_approved\": ...}\n"
        "201 -> created\n"
        "403 -> key marked deleted (reinstall required)"
    ))
    E.append(h3("Registration resolution order"))
    E.extend(bullets([
        "<b>Key exists and is deleted</b> &#8594; the row is re-surfaced as pending; it is never "
        "auto-approved. The device must be approved again.",
        "<b>Key exists and is active</b> &#8594; hostname/platform/version/last_seen/IP are refreshed; "
        "approval is kept only when auto-approve is on, and if the fingerprint changed the approval is "
        "reset to pending (prevents stolen-key reuse).",
        "<b>Key is new but the fingerprint already exists</b> &#8594; the existing device row is "
        "re-keyed to the new registration key (survives reinstalls). The admin self-client is excluded "
        "from this re-link.",
        "<b>Otherwise</b> &#8594; a brand-new Client row is created as pending (or online if "
        "auto-approve is enabled).",
    ]))
    E.append(note(
        "Newly registered clients inherit the company and owner of the admin server's self-client, so "
        "fleet data stays partitioned per company from the moment of registration."))
    E.append(h2("8.2 Approval"))
    E.append(para(
        "Unless auto-approve is enabled, a registered client stays pending until an admin approves it. "
        "Approval flips approved=True, sets status online, and assigns ownership."))
    E.append(endpoint_table([
        ("POST", "/api/approve", "Approve a single client by registration_key."),
        ("POST", "/api/approve-multiple", "Bulk approve a list of registration_keys."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/approve", "Approve via the monitoring module."),
        ("GET", "/api/clients/&lt;key&gt;/status", "Client-side poll: approved or pending."),
    ]))
    E.append(note(
        "Auto-approve is controlled by the auto_approve Setting (Settings page or PUT /api/settings). "
        "On Vercel it is forced to false so every device requires manual approval."))
    E.append(h2("8.3 Ongoing Connection (Heartbeat + WebSocket)"))
    E.append(para(
        "Once approved, the client maintains the connection through two parallel channels:"))
    E.extend(bullets([
        "<b>HTTP heartbeat</b> &#8212; every 30 seconds POST /api/ping refreshes last_seen, last_ip, "
        "hostname, and version and marks the client online. It carries CPU/RAM/disk metrics (via "
        "/api/monitoring/agent/heartbeat-public), returns trigger_scan when the admin asked for one, and "
        "flushes the agent's offline queue.",
        "<b>WebSocket channel</b> &#8212; ws://HOST/ws/agent/&lt;agent_id&gt;/ authenticated with HMAC "
        "signature + timestamp. Used for real-time commands (scan_now, config_update) and event "
        "streaming. Falls back to HTTP polling when the upgrade is rejected (for example on Vercel).",
    ]))
    E.append(para(
        "Offline behaviour: if the admin is unreachable the client applies exponential backoff with "
        "jitter, persists events to a disk queue, and replays them on reconnect. The heartbeat watchdog "
        "restarts a crashed heartbeat thread automatically. A device is flagged offline when no heartbeat "
        "arrives within the stale threshold (default 120 s).", NOTE))
    E.append(h2("8.4 Connection Deletion"))
    E.append(para(
        "Deletion is a <b>soft delete</b>: the server sets deleted=True so the device vanishes from "
        "dashboards while its historical scans and audit trail remain. Deletion also publishes a "
        "DEVICE_DELETED event on the event bus and records an ActivityLog entry."))
    E.append(endpoint_table([
        ("DELETE", "/api/clients/&lt;key&gt;", "Soft-delete a single client."),
        ("POST", "/api/clients/delete-multiple", "Bulk soft-delete a list of registration_keys."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/block", "Block a device (revoke connection)."),
    ]))
    E.append(para(
        "After deletion, a re-registration attempt with the same key is rejected with 403 (\u201cClient "
        "has been removed. Reinstall required.\u201d). The fingerprint re-registration path is ignored "
        "once deleted=True, so the operator must un-block or re-register deliberately. Deletion is not a "
        "hard purge; for a permanent wipe, delete the row directly or do a full factory reset (section "
        "26).", NOTE))
    E.append(h2("8.5 Connection Settings and Reset"))
    E.append(endpoint_table([
        ("GET", "/api/settings/connection", "Return stored admin server URL + connection token."),
        ("POST", "/api/settings/connection", "Explicitly generate a new URL + token."),
        ("PUT", "/api/settings/connection", "Regenerate only the connection token."),
    ]))
    E.extend(bullets([
        "<b>Reset admin bind IP</b> &#8212; python admin/main.py --reset.",
        "<b>Reset a client admin URL</b> &#8212; delete client_config.json and re-run, or edit admin_url.",
        "<b>Re-register a client</b> &#8212; delete client_key.json; a new key is generated and the "
        "fingerprint re-links the device to the existing record.",
        "<b>Full reset</b> &#8212; delete the database plus client key/config files, then restart both sides.",
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 9. Scanner API Module (Core)
# ─────────────────────────────────────────────────────────────────────────────
def s09(E):
    E.append(h1("9. Scanner API Module (Core)"))
    E.append(para(
        "scanner_api is the heart of the admin server. It owns the fleet data models, the agent-facing "
        "registration/heartbeat/scan endpoints, all authentication, the middleware stack, and the "
        "organization + asset-management modules."))
    E.append(h2("9.1 Core Data Models"))
    E.append(h3("Company, ClientGroup, Client, ScanResult"))
    E.append(field_table([
        ("Company", "Model", "The tenant entity. Unique name + slug; isolates fleet data."),
        ("ClientGroup", "Model", "User-defined grouping for clients (company-scoped)."),
        ("Client", "Model", "A registered device: registration_key (unique), hostname, platform, status "
                            "(pending/online/offline), approved, last_seen, last_ip, device_fingerprint, "
                            "scan_interval, scan_enabled, scan_requested, owner (User), company, group, "
                            "tags, purchase/vendor/warranty fields, notes, deleted (soft-delete). "
                            "is_stale property uses max(scan_interval*2, stale_threshold_seconds)."),
        ("ScanResult", "Model", "One scan payload per client (JSON scan_data); source of change detection. "
                                "Indexed [client, -created_at]."),
        ("AddonDevice", "Model", "Secondary device attached to a client (name, serial, cost, category)."),
    ]))
    E.append(h3("Settings and Audit"))
    E.append(field_table([
        ("Setting", "Model", "Key/value global or per-company settings; class helpers Setting.get/set."),
        ("ActivityLog", "Model", "Auditable admin actions: register, approve, scan, scan_request, delete, "
                                 "update, login, setting_change."),
        ("AuditLog", "Model", "Immutable security trail: login success/failure, logout, password changed, "
                              "and other security events."),
        ("LoginHistory", "Model", "Per-user login sessions with browser/OS/location and duration."),
        ("LoginAttempt", "Model", "Failed-login counting for account lockout."),
        ("AdministratorProfile", "Model", "1:1 with User; company binding, timezone, currency, date format, "
                                          "dashboard default, notification flags, MFA fields."),
        ("DeviceFingerprint", "Model", "Trusted browser/device fingerprint registry for a user."),
    ]))
    E.append(h3("Organization and Asset Models"))
    E.append(field_table([
        ("Location", "Model", "Office/building/floor/room/address; company-scoped, status Active/Archived/Closed."),
        ("Department", "Model", "Company department with head, budget, and location."),
        ("Employee", "Model", "Employee with code, email, department, designation, manager, location, status."),
        ("EmployeeAssetAssignment", "Model", "Tracks which Client (device) is assigned to which employee."),
        ("OrgAuditLog", "Model", "Immutable audit of employee/department/location changes."),
        ("AssetCategory", "Model", "Category tree for assets."),
        ("AssetVendor", "Model", "Vendor master data."),
        ("Asset", "Model", "The asset: auto asset_id AST######, category, manufacturer/model, QR/barcode, "
                           "financial fields, warranty block, 13-state lifecycle, optional client link, "
                           "assigned_to employee."),
        ("AssetAssignment", "Model", "Asset &#8594; employee assignment record."),
        ("AssetTransfer", "Model", "Transfer of an asset between employees/departments/locations."),
        ("AssetHistory", "Model", "Immutable, append-only history of asset actions with JSON snapshots."),
        ("AssetDocument", "Model", "Base64-stored documents attached to an asset."),
        ("ApiKey", "Model", "API key with SHA-256 key_hash, rate limit, allowed IPs, expiry, last_used."),
    ]))
    E.append(h2("9.2 Agent-Facing Endpoints"))
    E.append(endpoint_table([
        ("POST", "/api/register", "Register / refresh a client (section 8.1)."),
        ("POST", "/api/approve", "Approve a single client."),
        ("POST", "/api/approve-multiple", "Bulk approve clients."),
        ("POST", "/api/ping", "Heartbeat; returns trigger_scan when requested; resurrects soft-deleted "
                              "clients as pending."),
        ("POST", "/api/scan", "Submit a scan result; updates client OS/CPU/RAM."),
        ("POST", "/api/scan/local", "Scan the admin server machine (background thread)."),
        ("POST", "/api/scan/all", "Set scan_requested=True on all approved clients."),
        ("GET", "/api/health", "Lightweight health check (no DB)."),
        ("GET", "/api/admin-client", "Keeps the admin self-client online (dashboard poll)."),
        ("POST", "/api/supabase/register", "Registers the Vercel URL in the cloud registry (service-key auth)."),
    ]))
    E.append(h2("9.3 Client Management Endpoints"))
    E.append(endpoint_table([
        ("GET", "/api/clients", "List non-deleted clients (tenant-scoped)."),
        ("GET", "/api/clients/&lt;key&gt;/status", "Approval status for agent polling."),
        ("GET", "/api/clients/&lt;key&gt;", "Full detail + scan_changes diff between last two scans."),
        ("DELETE", "/api/clients/&lt;key&gt;", "Soft-delete a client."),
        ("POST", "/api/clients/delete-multiple", "Bulk soft-delete."),
        ("PUT", "/api/clients/&lt;key&gt;/manual", "Update manual fields."),
        ("GET/POST", "/api/clients/&lt;key&gt;/addons", "List / add addon devices."),
        ("DELETE", "/api/clients/&lt;key&gt;/addons/&lt;id&gt;", "Remove an addon device."),
        ("GET/PUT", "/api/clients/&lt;key&gt;/scan-config", "Read / update scan interval and enabled."),
        ("POST", "/api/clients/&lt;key&gt;/scan-now", "Trigger an immediate scan."),
        ("GET", "/api/clients/&lt;key&gt;/scan-results", "Latest scan result."),
        ("GET", "/api/scan/history", "Searchable/filterable scan history."),
        ("GET", "/api/admin/scan-changes", "Per-client scan diffs."),
        ("GET", "/api/activity-log", "Recent activity log."),
        ("GET/POST", "/api/groups", "List / create client groups."),
        ("DELETE", "/api/groups/&lt;id&gt;", "Delete a client group."),
    ]))
    E.append(h2("9.4 Settings and Admin Endpoints"))
    E.append(endpoint_table([
        ("GET/PUT", "/api/settings", "Global settings: auto_approve, stale_threshold_seconds, "
                                     "scan_all_interval, admin_client_key."),
        ("GET/PUT", "/api/settings/organization", "Organization profile."),
        ("GET/PUT", "/api/settings/security", "Security settings."),
        ("GET/PUT", "/api/settings/notifications", "Notification settings."),
        ("GET/POST/PUT", "/api/settings/connection", "Connection URL + token management."),
        ("GET/PUT", "/api/settings/dashboard", "Dashboard widget settings."),
        ("GET/POST", "/api/admin/users", "List / create admin users."),
        ("DELETE", "/api/admin/users/&lt;id&gt;", "Delete an admin user."),
        ("GET", "/api/admin/stats", "System statistics."),
    ]))
    E.append(h2("9.5 Authentication and Authorization"))
    E.append(h3("Five authentication mechanisms"))
    E.append(kv_table([
        ("Django sessions", "Primary for the admin panel. Login by username or email, account lockout, "
                            "remember-me (30-day) vs default 7-day sessions."),
        ("Signed cookie fallback", "A scanner_auth cookie (TimestampSigner, salt scanner-auth-cookie, "
                                   "30-day max age) restores the session on Vercel cold starts."),
        ("JWT (PyJWT)", "HS256, access 60 min / refresh 7 days, issuer system-scanner-pro. Endpoints "
                        "token/obtain, token/refresh, token/verify. Role derived from superuser flag."),
        ("API keys", "SHA-256 hashed key with rate limit, allowed IPs, expiry; header X-API-Key."),
        ("HMAC (agent)", "Agent&#8596;server messages signed with HMAC-SHA256 + timestamp; managed by the "
                         "monitoring module (section 10.16)."),
    ]))
    E.append(h3("RBAC permission classes"))
    E.append(field_table([
        ("ROLE_HIERARCHY", "dict", "super_admin=3, admin=2, viewer=1."),
        ("IsSuperAdmin", "class", "Superuser only."),
        ("IsAdmin", "class", "Admin role or above."),
        ("IsViewer", "class", "Any authenticated user."),
        ("IsAdminOrReadOnly", "class", "Writes require admin."),
        ("HasRole(role)", "class", "Requires a specific role."),
        ("CanManageDevices / Alerts / Schedules", "class", "Role-gated device, alert, and schedule management."),
        ("CanViewReports / CanGenerateReports", "class", "Role-gated report access."),
    ]))
    E.append(h2("9.6 Middleware"))
    E.append(kv_table([
        ("CookieAuthMiddleware", "Injects the user from a valid scanner_auth signed cookie when anonymous."),
        ("CompanyPrefixMiddleware", "Routes /&lt;user&gt;-&lt;company&gt;/ URL prefixes: resolves the prefix "
                                    "from the session/profile, strips it before dispatch, and redirects "
                                    "authenticated users to the prefixed URL."),
        ("SessionTimeoutMiddleware", "Idle timeout from Setting.session_timeout_minutes (default 120 min); "
                                     "redirects to /login/?timeout=1."),
        ("SecurityHeadersMiddleware", "Adds X-Content-Type-Options, X-Frame-Options DENY, X-XSS-Protection, "
                                      "and Referrer-Policy."),
        ("Whitenoise / CORS", "Serves static files and allows cross-origin API calls."),
    ]))
    E.append(h2("9.7 Company / Tenant Isolation"))
    E.extend(bullets([
        "get_user_company(request) gets or creates the profile and auto-creates a Company named after the "
        "username if unassigned.",
        "get_admin_owned_clients(request): superusers see their company's clients plus unowned; regular "
        "admins see their own clients plus unowned pending (so anyone can approve new devices).",
        "Every list view (clients, scans, activity, groups, locations, departments, employees, assets, "
        "assignments, org-audit, analytics, global search) is company-scoped.",
        "Settings, activity, audit, and login history all carry a company foreign key.",
    ]))
    E.append(h2("9.8 Key Algorithms"))
    E.append(h3("Change detection (diff_utils.compute_scan_diff)"))
    E.append(para(
        "Compares the last two ScanResult.scan_data dicts, ignoring metadata fields. Recursive dict diff, "
        "list diff keyed by name/model/serial/kb/device/mac/sid, and specialised peripheral and storage "
        "comparisons produce human-readable +, -, and arrow change lines. Exposed on the client detail "
        "page and /api/admin/scan-changes."))
    E.append(h3("Account lockout (auth_utils.check_account_lock)"))
    E.append(para(
        "Counts failed LoginAttempts in the last lock_duration_minutes (default 30) versus "
        "max_login_attempts (default 5) and reports the remaining lock time."))
    E.append(h3("Asset lifecycle state machine"))
    E.append(para(
        "Assets move through 13 states (Draft, Pending Approval, Approved, Purchased, Available, "
        "Assigned, Maintenance, Lost, Disposed, Archived, and others) with VALID_TRANSITIONS enforced on "
        "every status change; every transition writes an immutable AssetHistory entry."))
    E.append(h2("9.9 Management Commands (scanner_api)"))
    E.append(code_block(
        "python admin/manage.py clear_data       # wipe non-Django tables, recreate admin\n"
        "python admin/manage.py scan_local        # run a local scan of the admin host\n"
        "python admin/manage.py stale_checker     # mark stale clients offline (loop)\n"
        "python admin/manage.py createsuperuser   # create a superuser"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# 10. Monitoring Module
# ─────────────────────────────────────────────────────────────────────────────
def s10(E):
    E.append(h1("10. Monitoring Module"))
    E.append(para(
        "The monitoring app is where agents connect and where fleet intelligence lives. It provides the "
        "agent registration/heartbeat/inventory APIs, device management, WebSocket consumers, the event "
        "bus, scheduled scanning, health scoring, change detection, anomaly detection, the feature store, "
        "predictive analytics, and reports. It is mounted at /api/monitoring/ and its WebSocket routes "
        "at /ws/."))
    E.append(h2("10.1 Monitoring Data Models"))
    E.append(field_table([
        ("DeviceMonitoringInfo", "Model", "One row per client; monitoring_status, health_level/score, IP/MAC, "
                                          "OS info, agent_version, heartbeat counters, tags, notes."),
        ("HardwareInventory", "Model", "Immutable hardware component snapshot (cpu/ram/storage/gpu/motherboard/"
                                       "network) with an MD5 fingerprint and scan_id batch."),
        ("SoftwareInventory", "Model", "Software snapshot rows; is_present flips to False when a package is "
                                       "removed in a later scan."),
        ("DeviceHeartbeat", "Model", "One row per heartbeat: cpu/ram/disk pct, disk free/total, network, "
                                     "uptime, response time."),
        ("DeviceMetrics", "Model", "Hourly/daily rollups (avg/max/min cpu/ram/disk, health, uptime) for charts."),
        ("DeviceHistory", "Model", "Immutable per-device audit trail (categories: registration, status_change, "
                                   "hardware_change, software_change, health_change, security_event, "
                                   "alert_generated, admin_action, agent_update, remote_command)."),
        ("DeviceAlert", "Model", "Alert records with type, severity, status (active/acknowledged/resolved/"
                                 "dismissed), and details JSON."),
        ("AgentVersion", "Model", "Published agent releases (version, release notes, download URL, "
                                  "mandatory flag, file hash)."),
        ("AgentSecret", "Model", "HMAC credentials for an agent (agent_id unique, secret_key, "
                                 "device_fingerprint, is_active, last_used)."),
        ("ScheduledScan", "Model", "Recurring/one-time scan schedules (interval/daily/weekly/monthly/once) "
                                   "with targeting."),
        ("PendingScan", "Model", "Offline scan queue; agents pull pending scans on reconnect."),
        ("ScanScheduleLog", "Model", "Per-execution log of scheduled scans (triggered/completed/failed/"
                                     "skipped)."),
    ]))
    E.append(h2("10.2 Agent-Facing Endpoints"))
    E.append(endpoint_table([
        ("POST", "/api/monitoring/agent/register", "Register a monitoring agent; returns a secret_key. "
                                                   "Matches an existing Client by fingerprint, then "
                                                   "hostname, then client_key; creates one if needed."),
        ("POST", "/api/monitoring/agent/heartbeat", "HMAC-authenticated heartbeat (X-Agent-ID, X-Signature, "
                                                    "X-Timestamp); creates DeviceHeartbeat, computes health, "
                                                    "checks alerts."),
        ("POST", "/api/monitoring/agent/heartbeat-public", "Public heartbeat using only registration_key "
                                                           "(no HMAC); used by the standard client."),
        ("POST", "/api/monitoring/agent/inventory", "HMAC-authenticated full hardware + software inventory "
                                                    "snapshot; runs change detection."),
        ("GET", "/api/monitoring/agent/version-check", "Check for a newer agent version."),
        ("GET/POST", "/api/monitoring/agent/pending-scans", "Fetch queued scans; acknowledge executed/failed."),
    ]))
    E.append(h2("10.3 Device Management Endpoints"))
    E.append(endpoint_table([
        ("GET", "/api/monitoring/dashboard", "Fleet aggregates: status counts, health distribution, alerts, "
                                             "24h CPU/RAM/disk trends, 7-day health trend."),
        ("GET", "/api/monitoring/trends", "Configurable fleet trend series."),
        ("GET", "/api/monitoring/devices", "List devices with search/status/health/platform filters."),
        ("POST", "/api/monitoring/devices/bulk", "Bulk approve / block / maintenance / inactive."),
        ("GET/PUT", "/api/monitoring/devices/&lt;uuid&gt;", "Device detail / status update."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/approve", "Approve device (also approves the Client)."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/block", "Block device and deactivate all AgentSecrets."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/metrics", "Raw heartbeat data points."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/history", "Immutable device history."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/alerts", "Device alerts."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/hardware", "Hardware inventory history."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/software", "Present software list."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/heartbeats", "Heartbeat history."),
        ("GET", "/api/monitoring/alerts", "Fleet-wide alert list."),
        ("POST", "/api/monitoring/alerts/&lt;uuid&gt;/action", "Acknowledge / resolve / dismiss an alert."),
        ("GET/POST", "/api/monitoring/agent-versions", "List / publish agent versions."),
        ("GET/PUT", "/api/monitoring/settings/unauthorized-software", "Read / update the unauthorized "
                                                                      "software blocklist."),
    ]))
    E.append(h2("10.4 WebSocket Consumers"))
    E.append(h3("Agent channel: ws/agent/&lt;agent_id&gt;/"))
    E.append(para(
        "The agent connects and sends an auth message {type:'auth', agent_id, secret, signature, "
        "timestamp}. The consumer validates agent_id + secret_key against an active AgentSecret and "
        "requires the timestamp to be within 300 s (anti-replay). On success the agent is added to the "
        "channel group agent_&lt;agent_id&gt; and marked online. Inbound messages: heartbeat, "
        "scan_result, event, status_update, pong. Outbound messages: auth_success/auth_failed, command "
        "(scan_now/config_update), ping, heartbeat_ack."))
    E.append(h3("Dashboard channel: ws/dashboard/"))
    E.append(para(
        "Any open admin dashboard can connect (read-only if anonymous). The server pushes fleet events "
        "(device heartbeat, health changes, HW/SW changes, alerts, agent status) to the dashboard group "
        "in real time. Browsers can subscribe to a single device group to receive per-device updates."))
    E.append(h2("10.5 Event Bus and Subscribers"))
    E.append(para(
        "monitoring/event_bus.py defines an in-process pub/sub singleton and an EventType enum covering "
        "hardware, software, health, alerts, device lifecycle, agent version, heartbeat, and scan events. "
        "monitoring/subscribers.py registers default handlers that:"))
    E.extend(bullets([
        "Create/update DeviceAlerts and notify all admins on hardware/software/offline/deleted/version "
        "changes (severity-gated).",
        "Create in-app notifications for all hardware/software changes.",
        "Broadcast every event to the dashboard WebSocket group and to the device group.",
        "Write immutable DeviceHistory entries for each event category.",
    ]))
    E.append(note(
        "The event bus is the glue between the monitoring module and the dashboard: a change detected "
        "anywhere (agent inventory, scheduler, heartbeat) is published once and every subscriber reacts "
        "in order, so dashboards, alerts, history, and notifications all stay consistent."))
    E.append(h2("10.6 Health Scoring"))
    E.append(para(
        "calculate_health_score(heartbeat, software) computes a 0&#8211;100 score and a level "
        "(healthy &#8805;80, warning &#8805;50, critical below). Weights: CPU 25%, RAM 25%, disk 20%, "
        "connectivity 15%, software health 15%. CPU/RAM lose points above 70% and floor out beyond 85%; "
        "disk falls above 80% and floors at 95%; connectivity is 100 when the agent can reach the "
        "internet; software health is 100 when an antivirus product is present, 60 otherwise. A level "
        "change publishes HEALTH_LEVEL_CHANGED."))
    E.append(h2("10.7 Change Detection"))
    E.append(para(
        "monitoring/change_detection.py compares hardware inventory (by MD5 component fingerprints) and "
        "software snapshots. Hardware changes are added/removed/modified with per-component severity "
        "(storage is critical, motherboard/cpu warning, ram/gpu/network info). Software changes are "
        "added/removed/version_changed; names on the unauthorized list produce an unauthorized (warning) "
        "change, and a removed antivirus produces antivirus_removed (critical). Each change becomes an "
        "event-bus event and therefore an alert, notification, history entry, and dashboard broadcast."))
    E.append(h2("10.8 Alert Engine"))
    E.append(para(
        "monitoring/alerts.py runs heartbeat-based checks: high_cpu, high_ram, and low_disk (thresholds "
        "from Settings: alert_cpu_threshold 90, alert_ram_threshold 90, alert_disk_threshold 95, "
        "alert_disk_free_gb 5; disk becomes critical at 98% or under 2 GB free). check_offline_alerts "
        "creates device_offline alerts at 300/900/1800 seconds and resolves them when the device returns. "
        "Alerts have a lifecycle: active &#8594; acknowledged &#8594; resolved, or dismissed, tracked in "
        "DeviceAlert.status."))
    E.append(h2("10.9 Anomaly Detection"))
    E.append(kv_table([
        ("Threshold", "Static rules; confidence 0.95. CPU/RAM 85% warning / 95% critical; disk 90% warning / "
                      "98% critical; disk free 5 GB warning / 2 GB critical."),
        ("Z-score", "Requires 10+ history points; flags |z| &gt; 2.5; critical if z &gt; 4, warning if "
                    "z &gt; 3; confidence rises with z."),
        ("IQR", "Requires 20+ points; outliers beyond Q1&#8722;1.5&#215;IQR / Q3+1.5&#215;IQR; info severity."),
        ("Trend", "Requires 20+ points; flags rapid changes &gt;50% between the last 5 and last 20 "
                  "observations."),
    ]))
    E.append(h2("10.10 Feature Store"))
    E.append(para(
        "monitoring/feature_store.py maintains a per-device in-memory feature cache for future ML models. "
        "extract_features() builds performance features (resource pressure, high/low flags), resource "
        "features (cpu-ram correlation, disk-io pressure, uptime, needs_reboot), connectivity flags, "
        "software features (software count, antivirus presence, remote-access tools), hardware features, "
        "and temporal features (hour/day/weekend/business-hours, deltas and rates). get_feature_matrix() "
        "and export_for_training() produce training-ready matrices."))
    E.append(h2("10.11 Predictive Analytics"))
    E.append(kv_table([
        ("Disk-full time", "Linear regression on disk usage trend; hours_to_full = (100 &#8722; current)/slope. "
                           "URGENT under 24 h, schedule cleanup under 168 h, plan expansion under 720 h."),
        ("Failure risk", "Weighted 0&#8211;100 score from resource pressure (30), uptime (15), CPU volatility, "
                         "and declining health (25). Critical &gt;70, warning &gt;40."),
        ("Capacity needs", "Linear-regression forecast at 30/60/90 days; &gt;95% means add capacity, &gt;80% "
                           "means plan expansion."),
    ]))
    E.append(h2("10.12 Scheduled Scanning (APScheduler)"))
    E.append(para(
        "monitoring/scheduler.py wraps APScheduler. Every enabled ScheduledScan maps to a job. When a job "
        "fires it resolves its target clients (all approved, or a specific list, optionally filtered by "
        "platform), splits them into online and offline, and:"))
    E.extend(bullets([
        "<b>Online</b> &#8594; sends a live scan_now command to the agent_&lt;id&gt; WebSocket group via "
        "notify_agent(), and logs ScanScheduleLog(status='triggered').",
        "<b>Offline</b> &#8594; creates a PendingScan row and logs ScanScheduleLog(status='skipped'). The "
        "agent pulls its pending scans on reconnect via GET /api/monitoring/agent/pending-scans and "
        "acknowledges them.",
    ]))
    E.append(para(
        "Schedule CRUD is exposed under /api/monitoring/schedules (list/create/update/toggle/status/"
        "pending/history). On Vercel the scheduler does not run (no persistent process); external cron "
        "can call the schedule endpoints instead.", NOTE))
    E.append(h2("10.13 Security (HMAC + Rate Limiting)"))
    E.append(para(
        "monitoring/security.py provides generate_api_secret() (64 hex chars), compute_signature() "
        "(HMAC-SHA256 over the raw request body), verify_signature() with constant-time comparison, and "
        "verify_timestamp() (X-Timestamp within 300 s, anti-replay). authenticate_agent() resolves "
        "X-Agent-ID to an active AgentSecret and verifies the signature. A per-key in-memory RateLimiter "
        "(60 requests/minute for heartbeats) protects the endpoints. Blocking a device deactivates all "
        "of its AgentSecrets, so its HMAC identity is revoked immediately."))
    E.append(h2("10.14 Reports"))
    E.append(para(
        "monitoring/reports.py generates fleet, device, and alert reports. PDFs use ReportLab (A4, "
        "branded tables); CSV exports use the csv module. Endpoints under /api/monitoring/reports/ "
        "(section 21 covers report content in detail)."))


# ─────────────────────────────────────────────────────────────────────────────
# 11. Intelligence Module
# ─────────────────────────────────────────────────────────────────────────────
def s11(E):
    E.append(h1("11. Intelligence Module"))
    E.append(para(
        "The intelligence app is the cross-module insight layer. It unifies alerts from every module "
        "(asset, monitoring, maintenance, license, security, compliance, system), manages in-app "
        "notifications, writes an immutable audit trail, evaluates compliance, and provides a report "
        "engine with scheduled reports. It is mounted at /api/intelligence/."))
    E.append(h2("11.1 Data Models"))
    E.append(field_table([
        ("Alert", "Model", "Unified alert with module, severity (information/warning/critical/emergency), "
                           "category, status, escalation_level (0&#8211;3), dedup_hash, assigned_user, "
                           "resolved_time."),
        ("AlertHistory", "Model", "Immutable per-alert history of status/severity changes."),
        ("AlertRule", "Model", "User-defined rules (threshold_gt/lt/equals/contains) with suppress and "
                               "auto-resolve windows."),
        ("Notification", "Model", "In-app notification to a user; status unread/read/archived."),
        ("NotificationPreference", "Model", "Per-user gates: email/in-app toggles, per-severity and "
                                            "per-module flags, frequency, quiet hours."),
        ("Report", "Model", "Generated report (25 report types) stored as base64 with format, filters, "
                            "row count, status."),
        ("ScheduledReport", "Model", "Recurring report definition (daily/weekly/monthly/quarterly) with "
                                     "recipients and retention policy."),
        ("AuditLogEntry", "Model", "Immutable cross-module audit entry (module, action, object, old/new "
                                   "values, severity, description)."),
        ("ComplianceLog", "Model", "Compliance check results against frameworks (iso_27001/itil/soc2/"
                                   "internal/gdpr)."),
        ("DashboardAnalytics", "Model", "Periodic KPI snapshot for the dashboard."),
        ("RetentionPolicy", "Model", "Data retention per scope (alerts, notifications, reports, audit "
                                     "logs, compliance logs)."),
    ]))
    E.append(h2("11.2 Alert Management"))
    E.append(para(
        "intelligence/alerts.py creates alerts with a SHA-256 dedup hash so repeated conditions update "
        "the existing alert instead of duplicating it. Alerts can be acknowledged, resolved, dismissed, "
        "and assigned. escalate_alerts() raises severity levels by age (emergency &gt;1 h &#8594; level 3, "
        "critical &gt;4 h &#8594; level 2, warning &gt;24 h &#8594; level 1). run_alert_checks() generates "
        "alerts from business rules: expired/expiring warranties, overdue/due maintenance, "
        "expired/expiring/over-seat licenses, and stale clients."))
    E.append(h2("11.3 Notifications"))
    E.append(para(
        "intelligence/notifications.py gates every notification against the user's NotificationPreference "
        "(in-app toggle, severity, module, quiet hours). create_alert_notifications() notifies every "
        "active user for a new alert. Users mark notifications read/archived; the dashboard bell shows "
        "the unread count."))
    E.append(h2("11.4 Audit Logging"))
    E.append(para(
        "intelligence/audit.py is the central audit writer. It extracts the real client IP (X-Forwarded-"
        "For), browser user-agent, and device platform, and writes immutable AuditLogEntry rows. "
        "Convenience helpers cover login, logout, failed login, asset create/update/assign/delete, "
        "report download/generate, and settings changes."))
    E.append(h2("11.5 Report Engine"))
    E.append(para(
        "intelligence/reports.py implements nine report types: asset_inventory, asset_assignment, "
        "expiring_licenses, upcoming_maintenance, device_health, compliance_report, monthly_summary, "
        "software_inventory, and audit_report, in CSV, Excel, or PDF. Every generated report is "
        "persisted as a Report row; exports stream the stored base64 file."))
    E.append(h2("11.6 Key Endpoints"))
    E.append(endpoint_table([
        ("GET", "/api/intelligence/dashboard", "Analytics snapshot + alert/notification/audit summaries."),
        ("GET/POST", "/api/intelligence/alerts", "List / create alerts."),
        ("GET", "/api/intelligence/alerts/&lt;uuid&gt;", "Alert detail."),
        ("POST", "/api/intelligence/alerts/&lt;uuid&gt;/action", "Acknowledge / resolve / dismiss / assign."),
        ("GET", "/api/intelligence/alerts/&lt;uuid&gt;/history", "Alert history."),
        ("POST", "/api/intelligence/alerts/bulk", "Bulk alert actions."),
        ("POST", "/api/intelligence/alerts/run-checks", "Run the business-rule alert checks."),
        ("GET", "/api/intelligence/alerts/export", "Export alerts as CSV."),
        ("GET/POST", "/api/intelligence/alerts/rules", "List / create alert rules."),
        ("GET/PUT/DELETE", "/api/intelligence/alerts/rules/&lt;uuid&gt;", "Alert rule CRUD."),
        ("GET", "/api/intelligence/notifications", "User notifications + unread count."),
        ("POST", "/api/intelligence/notifications/mark-all-read", "Mark all read."),
        ("GET/PUT", "/api/intelligence/notifications/preferences", "Notification preferences."),
        ("POST", "/api/intelligence/notifications/&lt;uuid&gt;/action", "Read / archive."),
        ("GET/POST", "/api/intelligence/reports", "List / generate reports."),
        ("GET", "/api/intelligence/reports/&lt;uuid&gt;", "Report detail (logs download)."),
        ("GET", "/api/intelligence/reports/&lt;uuid&gt;/export", "Download stored report file."),
        ("GET/POST", "/api/intelligence/scheduled-reports", "List / create scheduled reports."),
        ("GET/PUT/DELETE", "/api/intelligence/scheduled-reports/&lt;uuid&gt;", "Scheduled report CRUD."),
        ("GET", "/api/intelligence/audit-logs", "Audit log list with filters."),
        ("GET", "/api/intelligence/audit-logs/export", "Export audit logs (max 5000 rows)."),
        ("GET/POST", "/api/intelligence/compliance", "Compliance log list / create."),
        ("GET", "/api/intelligence/compliance/dashboard", "Compliance rate by framework/status."),
        ("GET/POST", "/api/intelligence/retention-policies", "Retention policies."),
        ("GET/PUT", "/api/intelligence/settings", "Intelligence settings (escalation, retention)."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 12. Maintenance Module
# ─────────────────────────────────────────────────────────────────────────────
def s12(E):
    E.append(h1("12. Maintenance Module"))
    E.append(para(
        "The maintenance app manages the physical IT asset lifecycle: maintenance records, warranties, "
        "downtime, software licenses, license assignments, and compliance. It is mounted at "
        "/api/maintenance/."))
    E.append(h2("12.1 Data Models"))
    E.append(field_table([
        ("MaintenanceRecord", "Model", "A maintenance job: auto maintenance_id MNT######, type, status "
                                       "(Draft&#8594;...&#8594;Completed/Overdue), approval status, asset, "
                                       "department, vendor, technician, schedule dates, cost, priority, "
                                       "recurrence. is_overdue property."),
        ("MaintenanceHistory", "Model", "Immutable history of maintenance actions with JSON snapshots."),
        ("MaintenanceDocument", "Model", "Base64 documents attached to a maintenance record."),
        ("WarrantyRecord", "Model", "Warranty: auto WAR######, asset, provider, coverage, contract, "
                                    "support contacts, cost, computed_status (Active/Expiring Soon/Expired/...)."),
        ("DowntimeRecord", "Model", "Asset downtime windows with auto-computed duration and reason."),
        ("SoftwareLicense", "Model", "License: auto LIC######, type (Per User/Per Device/Subscription/OEM/...), "
                                     "status, encrypted + masked key, seats purchased/used, purchase/expiration "
                                     "dates, cost, department."),
        ("LicenseAssignment", "Model", "License &#8594; Asset/Employee/Department assignment; tracks active "
                                       "and removed assignments."),
        ("LicenseHistory", "Model", "Immutable license history."),
        ("ComplianceRecord", "Model", "Compliance findings (license_expiration, seat_overuse, "
                                      "unauthorized_software, missing_license, compliance_violation)."),
        ("MaintenanceAlert", "Model", "Maintenance/license/warranty alerts with severity and status."),
    ]))
    E.append(h2("12.2 Maintenance Lifecycle"))
    E.append(para(
        "Records start as Draft + Approval Pending. Approving moves them to Approved (or Cancelled). "
        "Status transitions are validated against a state map; entering In Progress auto-sets start_date; "
        "completing auto-sets completion_date and moves the linked asset back to Available. Completed "
        "records are immutable (no update/delete)."))
    E.append(h2("12.3 License Management"))
    E.append(para(
        "Licenses store the license key encrypted (license_key_encrypted) and display only a masked form "
        "(license_key_masked). Assigning a license to an asset/employee/department increments seats_used "
        "with a database atomic F() update; removing an assignment decrements it and is refused when the "
        "license is archived or seats are exhausted."))
    E.append(h2("12.4 Alerts"))
    E.append(para(
        "maintenance/alerts.py's check_and_generate_alerts() creates maintenance_overdue, "
        "maintenance_due, warranty_expiring/expired, license_expiration (7-day critical / 30-day warning "
        "/ 60-day info), license_expired, and license_seat_exhaustion alerts. It also flips warranty and "
        "license statuses to Expired when past due."))
    E.append(h2("12.5 Key Endpoints"))
    E.append(endpoint_table([
        ("GET/POST", "/api/maintenance/maintenance", "List / create maintenance records."),
        ("GET/PUT/DELETE", "/api/maintenance/maintenance/&lt;uuid&gt;", "Maintenance CRUD."),
        ("POST", "/api/maintenance/maintenance/&lt;uuid&gt;/status", "Transition maintenance status."),
        ("POST", "/api/maintenance/maintenance/&lt;uuid&gt;/approve", "Approve / reject maintenance."),
        ("POST", "/api/maintenance/maintenance/&lt;uuid&gt;/upload", "Attach a document."),
        ("GET", "/api/maintenance/maintenance/export", "Export maintenance CSV."),
        ("GET/POST", "/api/maintenance/warranties", "List / create warranties."),
        ("GET/DELETE", "/api/maintenance/warranties/&lt;uuid&gt;", "Warranty detail / delete."),
        ("GET/POST", "/api/maintenance/downtime", "List / create downtime."),
        ("POST", "/api/maintenance/downtime/&lt;uuid&gt;/end", "Close an open downtime window."),
        ("GET/POST", "/api/maintenance/licenses", "List / create licenses."),
        ("GET/PUT/DELETE", "/api/maintenance/licenses/&lt;uuid&gt;", "License CRUD."),
        ("POST", "/api/maintenance/licenses/&lt;uuid&gt;/archive", "Archive a license."),
        ("POST", "/api/maintenance/licenses/assign", "Assign a license."),
        ("POST", "/api/maintenance/licenses/assignments/&lt;uuid&gt;/remove", "Remove a license assignment."),
        ("GET", "/api/maintenance/licenses/export", "Export licenses CSV."),
        ("GET/POST", "/api/maintenance/compliance", "List / create compliance records."),
        ("POST", "/api/maintenance/compliance/&lt;uuid&gt;/action", "Acknowledge / resolve / dismiss."),
        ("GET", "/api/maintenance/alerts", "Maintenance alerts."),
        ("POST", "/api/maintenance/alerts/&lt;uuid&gt;/action", "Alert action."),
        ("POST", "/api/maintenance/alerts/check", "Run alert checks."),
        ("GET", "/api/maintenance/dashboard", "Maintenance KPIs and distributions."),
        ("GET", "/api/maintenance/analytics/cost-trend", "Monthly cost trend."),
        ("GET", "/api/maintenance/analytics/vendor-performance", "Vendor completion/quality metrics."),
        ("GET", "/api/maintenance/analytics/failure-rate", "Asset failure rates."),
        ("GET", "/api/maintenance/analytics/downtime", "Downtime analytics."),
        ("GET", "/api/maintenance/analytics/license-dashboard", "License KPIs."),
        ("GET", "/api/maintenance/analytics/license-utilization", "Per-license utilization."),
        ("GET", "/api/maintenance/analytics/license-cost", "License cost analysis."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 13. Organization & Asset Management
# ─────────────────────────────────────────────────────────────────────────────
def s13(E):
    E.append(h1("13. Organization and Asset Management"))
    E.append(para(
        "These modules live inside scanner_api and give the platform its IT-asset-management face. They "
        "connect employees and departments to scanned devices and to tracked assets."))
    E.append(h2("13.1 Locations"))
    E.append(endpoint_table([
        ("GET/POST", "/api/locations", "List / create locations."),
        ("GET/PUT", "/api/locations/&lt;uuid&gt;", "Location CRUD (Closed is read-only)."),
        ("POST", "/api/locations/&lt;uuid&gt;/delete", "Delete (blocked while assets are active)."),
        ("POST", "/api/locations/&lt;uuid&gt;/archive", "Archive a location."),
        ("GET", "/api/locations/&lt;uuid&gt;/dashboard", "Location dashboard."),
        ("GET/POST", "/api/locations/&lt;uuid&gt;/export", "Export locations CSV."),
    ]))
    E.append(h2("13.2 Departments"))
    E.append(para(
        "Departments auto-seed eight defaults per company. Employees and assets link to departments, so "
        "a department cannot be deleted while it still owns either."))
    E.append(endpoint_table([
        ("GET/POST", "/api/departments", "List / create departments."),
        ("GET/PUT", "/api/departments/&lt;uuid&gt;", "Department CRUD."),
        ("POST", "/api/departments/&lt;uuid&gt;/delete", "Delete (blocked with employees/assets)."),
        ("POST", "/api/departments/&lt;uuid&gt;/disable", "Disable a department."),
        ("GET", "/api/departments/&lt;uuid&gt;/dashboard", "Department dashboard."),
    ]))
    E.append(h2("13.3 Employees"))
    E.append(endpoint_table([
        ("GET/POST", "/api/employees", "List (search/dept/loc/status/has_assets) / create employees."),
        ("GET/PUT", "/api/employees/&lt;uuid&gt;", "Employee CRUD."),
        ("POST", "/api/employees/&lt;uuid&gt;/delete", "Delete (blocked with assignment history)."),
        ("POST", "/api/employees/&lt;uuid&gt;/deactivate", "Deactivate and auto-return assets."),
        ("GET", "/api/employees/&lt;uuid&gt;/assets", "Employee's assets."),
    ]))
    E.append(h2("13.4 Assignments"))
    E.append(endpoint_table([
        ("GET/POST", "/api/assignments", "List / create asset assignments (blocks double-assigning an "
                                         "asset)."),
        ("POST", "/api/assignments/&lt;uuid&gt;/return", "Return an assigned asset."),
        ("POST", "/api/assignments/bulk", "Bulk assignments."),
        ("GET", "/api/org/audit-logs", "Organization audit logs."),
        ("GET", "/api/org/stats", "Organization dashboard stats."),
    ]))
    E.append(h2("13.5 Asset Lifecycle"))
    E.append(para(
        "Assets start as Draft and flow through Pending Approval, Approved, Purchased, Available, and "
        "Assigned, with Maintenance, Lost, Disposed, and Archived states. Every transition is validated "
        "against the state machine and recorded in immutable AssetHistory. Assets can be assigned to "
        "employees, returned, transferred, retired, and disposed, and carry QR codes for physical "
        "scanning."))
    E.append(endpoint_table([
        ("GET/POST", "/api/assets", "List / create assets (filters incl. warranty expiring/expired)."),
        ("GET/PUT/DELETE", "/api/assets/&lt;uuid&gt;", "Asset CRUD."),
        ("POST", "/api/assets/&lt;uuid&gt;/status", "Validated status transition."),
        ("POST", "/api/assets/&lt;uuid&gt;/assign", "Assign to an employee."),
        ("POST", "/api/assets/&lt;uuid&gt;/return", "Return from assignment."),
        ("POST", "/api/assets/&lt;uuid&gt;/transfer", "Transfer asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/retire", "Retire asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/dispose", "Dispose asset."),
        ("GET", "/api/assets/&lt;uuid&gt;/history", "Immutable asset history."),
        ("GET", "/api/assets/&lt;uuid&gt;/qr", "QR code image."),
        ("GET", "/api/assets/dashboard", "Asset dashboard."),
        ("GET", "/api/assets/analytics", "Asset analytics."),
        ("GET/POST", "/api/assets/import", "CSV/XLSX import."),
        ("GET", "/api/assets/export", "Asset export."),
        ("GET", "/api/scan/&lt;qr_code&gt;", "QR lookup of an asset."),
    ]))
    E.append(h2("13.6 Cross-Module Insights"))
    E.append(endpoint_table([
        ("GET", "/api/executive-analytics", "KPIs across assets, monitoring, maintenance, licenses, and "
                                            "security plus recent activity."),
        ("GET", "/api/global-search", "Search across assets, employees, departments, locations, clients, "
                                      "licenses, and alerts."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 14. Client Agent in Detail
# ─────────────────────────────────────────────────────────────────────────────
def s14(E):
    E.append(h1("14. Client Agent in Detail"))
    E.append(para(
        "The client agent is a standalone Python process that runs on every managed machine. It is "
        "deliberately dependency-light (standard library plus websockets and watchdog) so it can be "
        "frozen into a single executable with PyInstaller."))
    E.append(h2("14.1 Startup Flow"))
    E.append(code_block(
        "1.  Crash-log bootstrap (client_crash.log records every import step)\n"
        "2.  main(): rescue mode? silent mode? -> autostart re-registration\n"
        "3.  Single-instance check (Windows named mutex)\n"
        "4.  Load or create registration key + fingerprint (client_key.json)\n"
        "5.  Resolve admin URL: env > CLI arg > cloud discovery > UDP > prompt\n"
        "6.  Reachability loop: GET /api/health; on failure rediscover\n"
        "7.  POST /api/register; wait for approval (poll /api/clients/<key>/status)\n"
        "8.  Run initial scan; POST /api/scan\n"
        "9.  Register monitoring identity -> AgentSecret (agent_id + secret)\n"
        "10. (Frozen Windows) spawn detached background copy; close terminal\n"
        "11. Start threads: heartbeat loop, watchdog, cloud discovery, UDP listener\n"
        "12. Start WebSocket client (if supported)\n"
        "13. Start event monitors + event dispatcher\n"
        "14. Enter scheduled scan loop (interval from server scan-config)"
    ))
    E.append(h2("14.2 HTTP Communicator"))
    E.append(kv_table([
        ("register", "POST /api/register with key, hostname, platform, version, fingerprint."),
        ("ping", "POST /api/ping; carries heartbeat; reads trigger_scan; flushes offline queue."),
        ("submit_scan", "POST /api/scan with full scan_data (120 s timeout)."),
        ("check_status", "GET /api/clients/&lt;key&gt;/status for approval polling."),
        ("fetch_latest_scan", "GET /api/clients/&lt;key&gt;/scan-results."),
        ("get_scan_config", "GET /api/clients/&lt;key&gt;/scan-config."),
        ("monitor_register", "POST /api/monitoring/agent/register -> secret_key."),
        ("monitor_heartbeat", "POST /api/monitoring/agent/heartbeat with HMAC headers."),
        ("monitor_heartbeat_public", "POST /api/monitoring/agent/heartbeat-public with registration_key only."),
        ("monitor_inventory", "POST /api/monitoring/agent/inventory with HMAC headers."),
        ("monitor_version_check", "GET /api/monitoring/agent/version-check."),
    ]))
    E.append(para(
        "Retries: connection errors, 5xx, and 429 are retried up to 3 times with exponential backoff "
        "plus jitter (base 1 s, max 30 s). 4xx are not retried. The in-memory offline queue (500-item "
        "cap) holds scan posts until the server is reachable again.", NOTE))
    E.append(h2("14.3 WebSocket Client"))
    E.append(para(
        "WebSocketClient connects to ws(s)://HOST/ws/agent/&lt;agent_id&gt;/ and authenticates with "
        "{type:'auth', agent_id, secret, signature, timestamp}. It auto-reconnects with exponential "
        "backoff (2 s up to 60 s), sends an application-level ping every 20 s, and permanently disables "
        "itself if the server answers the WebSocket upgrade with a plain HTTP response (Vercel "
        "detection), falling back to HTTP polling. Inbound commands: auth_success (replays pending "
        "commands), auth_failed, command (scan_now/config_update/ping), ping, heartbeat_ack."))
    E.append(h2("14.4 Hardware Fingerprint"))
    E.append(para(
        "generate_fingerprint() hashes motherboard serial, CPU id, first disk serial, and all MAC "
        "addresses (joined and sorted) plus machine architecture with SHA-256 and truncates to 16 hex "
        "characters. This stable identity survives IP/hostname changes and reinstalls, which is what "
        "makes fingerprint-based re-registration work."))
    E.append(h2("14.5 Scanner (Collected Data)"))
    E.append(field_table([
        ("Processor", "Snapshot", "Manufacturer, model, serial, cores, threads, speed, cache/architecture."),
        ("RAM", "Snapshot", "Manufacturer, capacity, serial, speed, form factor per module."),
        ("Storage", "Snapshot", "Disks (model, serial, size, interface) + partitions (filesystem, mount, free)."),
        ("Motherboard", "Snapshot", "Manufacturer, model, serial, BIOS version."),
        ("GPU", "Snapshot", "Name, vendor, driver, dedicated memory."),
        ("OS", "Snapshot", "Name, version, build, architecture, install details."),
        ("Network", "Snapshot", "Interfaces (name, MAC, IPv4, status)."),
        ("Peripherals", "Snapshot", "Keyboard, mouse, audio, webcam, printers, USB storage/other."),
        ("Software", "Snapshot", "Installed applications (name, version, publisher) - Windows."),
        ("Windows Updates", "Snapshot", "KB IDs and descriptions (Windows only)."),
        ("Antivirus", "Snapshot", "Antivirus products from SecurityCenter2 (Windows only)."),
        ("User Accounts", "Snapshot", "Local user accounts (Windows only)."),
    ]))
    E.append(h2("14.6 Metrics"))
    E.append(para(
        "collect_metrics() returns cpu_usage_pct, ram_usage_pct, disk_usage_pct, disk_free_gb, "
        "disk_total_gb, network_connected (probed via TCP to 8.8.8.8:53 and 1.1.1.1:53), and "
        "uptime_seconds, using WMI on Windows, /proc on Linux, and system commands on macOS."))
    E.append(h2("14.7 Event Monitors"))
    E.append(endpoint_table([
        ("USB", "5 s poll", "USB insertion/removal/status-change (WMI on Windows, lsusb on Linux, "
                            "system_profiler on macOS)."),
        ("Process", "10 s poll", "Process start/termination; flags suspicious names (mimikatz, psexec, "
                                 "netcat, meterpreter, ...) and processes running from temp folders."),
        ("Software", "60 s poll", "Software install/remove/version change; antivirus disabled and "
                                  "firewall disabled detection via SecurityCenter2 (Windows)."),
        ("File", "Real-time (watchdog)", "Critical file created/modified/deleted/moved on system paths; "
                                         "2 s debounce; extensions and filenames whitelist."),
    ], widths=[2.2 * cm, 3.2 * cm, PAGE_W - 2 * MARGIN - 5.4 * cm]))
    E.append(h2("14.8 Event Dispatcher and Offline Queue"))
    E.append(para(
        "EventDispatcher batches events (every 5 s or when 50 accumulate) and sends them over WebSocket "
        "first, then HMAC-signed HTTP, then public HTTP. If no transport is available it persists the "
        "batch to %APPDATA%\\SystemScannerPro\\offline_events\\batch_*.json and replays those files on "
        "the next start. The dispatcher reports sent/failed/disk-queued/replayed counters."))
    E.append(h2("14.9 Offline Resilience"))
    E.append(kv_table([
        ("Exponential backoff", "HTTP retries with jitter; heartbeat backoff 5 s doubling to 30 s."),
        ("Offline event queue", "Disk-persisted event batches replayed on reconnect/restart."),
        ("Heartbeat watchdog", "Restarts a crashed heartbeat thread (max 5 restarts, check every 10 s)."),
        ("Re-discovery", "On repeated failures the agent re-queries cloud discovery and UDP discovery and "
                         "switches to a reachable admin URL."),
        ("Passive UDP listener", "Continuously listens on port 45000 and adopts any ADMIN_HERE broadcast "
                                 "(unless the URL is manual)."),
        ("Vercel fallback", "WebSocket auto-disabled; everything continues over HTTP polling."),
    ]))
    E.append(h2("14.10 Background and Autostart Mode (Windows)"))
    E.append(para(
        "The packaged Windows agent can run hidden. On a manual launch it registers autostart (Run key "
        "plus a Startup-folder .vbs launcher), spawns a fully detached hidden copy (--rescue --silent) "
        "and closes the terminal. The hidden copy redirects output to client_agent.log, detaches its "
        "console, and runs the agent. A named mutex prevents duplicate instances, and closing the "
        "console window spawns a rescue copy so the agent stays online."))


# ─────────────────────────────────────────────────────────────────────────────
# 15. How Everything Connects (Scenarios)
# ─────────────────────────────────────────────────────────────────────────────
def s15(E):
    E.append(h1("15. How Everything Connects (End-to-End Scenarios)"))
    E.append(para(
        "This section is the map of the platform: concrete scenarios showing exactly which component "
        "calls which endpoint and which event fires next. Each scenario traces one business flow through "
        "all the modules described in sections 8&#8211;14."))
    E.append(h2("15.1 Onboarding a New Device"))
    E.append(code_block(
        "AGENT                 ADMIN SERVER\n"
        "  |  client_key.json created\n"
        "  |  admin URL resolved (arg/env/cloud/UDP)\n"
        "  |-- POST /api/register -------------> scanner_api.RegisterClientView\n"
        "  |                                        resolve key/fingerprint -> new Client (pending)\n"
        "  |                                        DeviceMonitoringInfo created (via monitor module)\n"
        "  |                                        event bus: DEVICE_REGISTERED\n"
        "  |                                        ActivityLog: register\n"
        "  |<-- approved: false\n"
        "  |-- POST /api/ping (loop, 30s) -----> PingClientView\n"
        "  |-- GET /api/clients/<key>/status --> approved?  (loop until admin acts)\n"
        "  |\n"
        "ADMIN clicks Approve on /api/approve or /api/monitoring/devices/<uuid>/approve\n"
        "  |                                        Client.approved=True, status=online\n"
        "  |                                        event bus: DEVICE_APPROVED\n"
        "  |                                        ActivityLog: approve\n"
        "  |                                        dashboard WebSocket broadcast\n"
        "  |-- POST /api/scan (initial scan) ---> ScanResult stored, change baseline set\n"
        "  |-- monitoring agent register -------> AgentSecret issued (agent_id + secret)\n"
        "  |-- WebSocket connect ws/agent/<id>/ -> HMAC auth -> agent_<id> group\n"
        "  |-- event monitors + dispatcher start\n"
        "DEVICE IS NOW AN ONLINE, MONITORED FLEET MEMBER"
    ))
    E.append(h2("15.2 Real-Time Scan Command"))
    E.append(code_block(
        "ADMIN (dashboard or API)            ADMIN SERVER                  AGENT\n"
        "  POST /api/clients/<key>/scan-now     sets scan_requested=True\n"
        "                                       sends WebSocket command:\n"
        "                                       notify_agent() -> group_send agent_<id>\n"
        "                                       AgentConsumer.send_command\n"
        "                                                     |-- {type:'command',\n"
        "                                                     |    command_type:'scan_now'}\n"
        "                                                     |<-- runs collect_all()\n"
        "                                                     |-- POST /api/scan\n"
        "                                                     |-- {type:'scan_result'}\n"
        "                                          ScanResult stored\n"
        "                                          event bus: scan_completed\n"
        "                                          dashboard broadcast (live update)\n"
        "  |<-- dashboard shows the fresh scan\n"
        "\n"
        "If the agent is offline: scan_requested stays set; on the next /api/ping the server returns\n"
        "trigger_scan:true and the agent runs the scan immediately (HTTP path)."
    ))
    E.append(h2("15.3 Scheduled Scan Dispatch"))
    E.append(code_block(
        "APScheduler job fires (monitoring/scheduler.py)\n"
        "  |-- resolve target clients (all approved, or selected, platform-filtered)\n"
        "  |\n"
        "  +-- ONLINE client ------------------> WebSocket command scan_now\n"
        "  |                                       ScanScheduleLog: triggered\n"
        "  |\n"
        "  `-- OFFLINE client -----------------> PendingScan created (offline queue)\n"
        "                                           ScanScheduleLog: skipped\n"
        "                                           broadcast schedule_executed to dashboard\n"
        "\n"
        "Later, the offline agent reconnects:\n"
        "  AGENT -- GET /api/monitoring/agent/pending-scans --> list\n"
        "  AGENT -- POST /api/scan (executes the scan)\n"
        "  AGENT -- POST /api/monitoring/agent/pending-scans {scan_id, status:'executed'}\n"
        "  SERVER -- PendingScan marked executed, ScanScheduleLog completed"
    ))
    E.append(h2("15.4 Event Detection Pipeline"))
    E.append(code_block(
        "Something changes on a machine (USB inserted, file modified, process started,\n"
        "software installed, antivirus disabled):\n"
        "\n"
        "AGENT\n"
        "  USB/File/Process/Software monitor detects the delta vs baseline\n"
        "    `-> on_event(event) -> EventDispatcher\n"
        "         batch (5s / 50 events)\n"
        "         send WebSocket {type:'event', event_type, severity, event_data}\n"
        "         (fallback: HMAC HTTP / public HTTP / disk queue)\n"
        "\n"
        "ADMIN SERVER (AgentConsumer._handle_event)\n"
        "  `-> DeviceHistory row (category security_event or status_change)\n"
        "  `-> DeviceAlert when severity is warning/critical\n"
        "  `-> broadcast device_event + new_alert to dashboards\n"
        "\n"
        "SERVER-SIDE INVENTORY PATH (agent inventory submission)\n"
        "  /api/monitoring/agent/inventory -> detect_hardware_changes / detect_software_changes\n"
        "    `-> event bus events (hw_component_*, sw_*)\n"
        "         |-> subscribers create DeviceAlerts + admin notifications\n"
        "         |-> broadcast_change -> dashboard WebSocket\n"
        "         `-> record DeviceHistory\n"
        "\n"
        "RESULT: the change is simultaneously a history entry, an alert, a notification,\n"
        "and a live dashboard update."
    ))
    E.append(h2("15.5 Alert Lifecycle"))
    E.append(code_block(
        "SOURCE                 MONITORING/INTELLIGENCE/MAINTENANCE        OPERATOR\n"
        "  heartbeat high CPU   alerts.py high_cpu -> DeviceAlert active\n"
        "  offline detection    check_offline_alerts -> device_offline\n"
        "  business rules       intelligence.run_alert_checks() -> unified Alert\n"
        "  maintenance rules    maintenance.check_and_generate_alerts() -> MaintenanceAlert\n"
        "  \n"
        "  all of these ALSO:\n"
        "    `-> create_alert_notifications() -> user Notification (preference-gated)\n"
        "    `-> dashboard WebSocket (live badge)\n"
        "\n"
        "OPERATOR ACTION\n"
        "  acknowledge -> status acknowledged, AlertHistory recorded\n"
        "  resolve      -> status resolved, resolved_at set\n"
        "  dismiss      -> status dismissed\n"
        "  assign       -> assigned_user set (intelligence alerts)\n"
        "\n"
        "ESCALATION (intelligence)\n"
        "  open alerts age past thresholds -> escalate_alerts() raises severity level"
    ))
    E.append(h2("15.6 Offline Client Recovery"))
    E.append(code_block(
        "1. Agent loses connectivity -> heartbeat fails, backoff doubles (5s..30s)\n"
        "2. Events keep arriving -> EventDispatcher persists batches to disk\n"
        "3. Server marks the client offline (stale threshold) -> DEVICE_OFFLINE event\n"
        "   -> device_offline alert + dashboard red dot\n"
        "4. After repeated failures the agent re-discovers:\n"
        "     cloud discovery -> UDP discovery -> reachable URL\n"
        "5. Agent reconnects, pings, flushes the offline queue (events replay)\n"
        "6. Agent pulls pending scheduled scans and executes them\n"
        "7. Server marks online -> DEVICE_ONLINE event -> alert resolved, green dot"
    ))
    E.append(h2("15.7 Change Detection and Notification"))
    E.append(code_block(
        "SCAN N (t=0)                        SCAN N+1 (t=3600s)\n"
        "  software: [A, B, C]                  software: [A, B, D]\n"
        "  hardware: [Disk SN-1]                hardware: [Disk SN-1, Disk SN-2]\n"
        "\n"
        "/api/scan stores ScanResult N+1\n"
        "  `-> scanner_api diff (last two scans) -> scan_changes on client detail\n"
        "\n"
        "/api/monitoring/agent/inventory (or heartbeat + software list)\n"
        "  `-> detect_software_changes: C removed (info), D added (info)\n"
        "  `-> detect_hardware_changes: Disk SN-2 added (critical storage change)\n"
        "  `-> event bus: sw_removed, sw_installed, hw_component_added\n"
        "  `-> DeviceAlert: sw_removed, hw_component_added + admin notifications\n"
        "  `-> DeviceHistory rows + dashboard broadcasts\n"
        "\n"
        "Unauthorized software? -> sw_unauthorized warning alert\n"
        "Antivirus removed?      -> sw_antivirus_removed CRITICAL alert"
    ))
    E.append(h2("15.8 Serverless (Vercel) Flow"))
    E.append(code_block(
        "CLIENT                       VERCEL (api/index.py)          SUPABASE\n"
        "  starts                          cold start:\n"
        "    |-- cloud discovery ---->     migrate, admin user, register\n"
        "    |                             server URL + token in registry\n"
        "    |<-- https://...vercel.app    \n"
        "    |-- POST /api/register ------> Django (serverless)\n"
        "    |-- POST /api/ping ----------> 30s polling (no WebSocket)\n"
        "    |-- heartbeat-public --------> DeviceHeartbeat\n"
        "    |-- version-check ----------->\n"
        "  WebSocket auto-disabled (HTTP rejection detected)\n"
        "  APScheduler/UDP unavailable -> schedules via external cron hitting\n"
        "  the /api/monitoring/schedules endpoints instead"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# 16. Security Architecture
# ─────────────────────────────────────────────────────────────────────────────
def s16(E):
    E.append(h1("16. Security Architecture"))
    E.append(h2("16.1 Authentication Layers"))
    E.append(kv_table([
        ("Admin panel (sessions)", "Login by username or email; account lockout after 5 failures in 30 min; "
                                   "remember-me 30-day vs default 7-day sessions; CSRF-exempt session "
                                   "authentication for DRF."),
        ("Signed cookie fallback", "scanner_auth cookie (TimestampSigner, 30-day max age, httpOnly, "
                                   "SameSite=Lax, Secure on Vercel) restores identity on cold starts."),
        ("JWT", "HS256 access (60 min) / refresh (7 days) token pairs, issuer system-scanner-pro; "
                "obtain/refresh/verify endpoints."),
        ("API keys", "SHA-256 hashed keys with rate limiting, optional IP allow-lists, and expiry; raw key "
                     "returned once at creation."),
        ("Agent HMAC", "Every agent HTTP endpoint verifies HMAC-SHA256 over the raw body with a "
                       "timestamp (300 s window) against an active AgentSecret."),
        ("Resilient backend", "Recovers the admin superuser if the user row is missing after a database "
                              "reset or cold start."),
    ]))
    E.append(h2("16.2 Authorization (RBAC)"))
    E.append(para(
        "Roles are super_admin, admin, and viewer. Permission classes gate device/alert/schedule "
        "management and report access. In practice most API views also enforce tenant scoping "
        "(company/owner) rather than role checks, so visibility is the primary authorization model."))
    E.append(h2("16.3 Agent Authentication Details"))
    E.append(code_block(
        "1. Agent registers -> server returns secret_key (AgentSecret row)\n"
        "2. Every authenticated request adds headers:\n"
        "     X-Agent-ID:  <agent_id>\n"
        "     X-Signature: HMAC-SHA256(secret_key, raw_body)\n"
        "     X-Timestamp: <unix float>\n"
        "3. Server: timestamp within 300s (replay protection)\n"
        "4. Server: active AgentSecret found by agent_id\n"
        "5. Server: constant-time HMAC comparison passes\n"
        "6. Rate limit (60/min per agent) applied\n"
        "\n"
        "Blocking a device deactivates all its AgentSecrets -> identity revoked instantly."
    ))
    E.append(h2("16.4 Tenant Isolation"))
    E.extend(bullets([
        "Every admin server uses its own database (SQLite locally; the cloud instance for Vercel).",
        "Clients, settings, groups, locations, departments, employees, and assets carry a company FK.",
        "List/detail views filter by company (superuser) or owner (regular admin).",
        "Unowned pending clients are visible to all admins so new devices can be approved.",
        "The UI URL prefix /&lt;user&gt;-&lt;company&gt;/ reinforces the boundary.",
    ]))
    E.append(h2("16.5 HTTP Hardening"))
    E.extend(bullets([
        "SecurityHeadersMiddleware: X-Content-Type-Options nosniff, X-Frame-Options DENY, X-XSS-Protection, "
        "Referrer-Policy strict-origin-when-cross-origin.",
        "SECURE_BROWSER_XSS_FILTER and SECURE_CONTENT_TYPE_NOSNIFF enabled.",
        "Secure cookies on Vercel; HTTPS redirects handled by the proxy.",
        "Agent secrets are 64-hex-char random values; connection tokens use secrets.token_hex(16).",
    ]))
    E.append(h2("16.6 Secrets Management"))
    E.append(para(
        "Secrets live in .env (DJANGO_SECRET_KEY, SUPABASE_SERVICE_KEY, etc.); .env is git-ignored. "
        "License keys are stored encrypted with a masked display. API keys are stored only as SHA-256 "
        "hashes. Report the following to your security team: the cloud-discovery client embeds a "
        "service-role JWT in client/discovery.py, and example credentials appear in repository files "
        "(.env.template, .env.vercel). Rotate these before production.", NOTE))
    E.append(h2("16.7 Auditing"))
    E.append(para(
        "Three audit layers: ActivityLog (admin actions), AuditLog/LoginHistory (authentication and "
        "security events), and DeviceHistory + AssetHistory (immutable device and asset trails). The "
        "intelligence app adds a unified immutable AuditLogEntry. All are company-scoped."))


# ─────────────────────────────────────────────────────────────────────────────
# 17. REST API Reference (complete)
# ─────────────────────────────────────────────────────────────────────────────
def s17(E):
    E.append(h1("17. REST API Reference (Complete)"))
    E.append(para(
        "All endpoints are relative to the admin base URL. Prefixes: /api/ (scanner_api), "
        "/api/monitoring/ (monitoring), /api/intelligence/ (intelligence), /api/maintenance/ "
        "(maintenance). WebSocket endpoints are covered in section 18."))
    E.append(h2("17.1 scanner_api: Registration, Communication, Scans"))
    E.append(endpoint_table([
        ("POST", "/api/register", "Register / refresh a client."),
        ("POST", "/api/approve", "Approve a single client."),
        ("POST", "/api/approve-multiple", "Bulk approve clients."),
        ("POST", "/api/ping", "Client heartbeat (online status, trigger_scan)."),
        ("GET", "/api/clients/&lt;key&gt;/status", "Approval status."),
        ("POST", "/api/scan", "Submit a scan result."),
        ("POST", "/api/scan/local", "Scan the admin server machine."),
        ("POST", "/api/scan/all", "Trigger scans on all approved clients."),
        ("GET", "/api/scan/history", "Scan history with filters."),
        ("GET", "/api/clients", "List non-deleted clients."),
        ("GET", "/api/clients/&lt;key&gt;", "Client detail + scan diff."),
        ("DELETE", "/api/clients/&lt;key&gt;", "Soft-delete client."),
        ("POST", "/api/clients/delete-multiple", "Bulk soft-delete."),
        ("PUT", "/api/clients/&lt;key&gt;/manual", "Update manual fields."),
        ("GET/POST", "/api/clients/&lt;key&gt;/addons", "List / add addon devices."),
        ("DELETE", "/api/clients/&lt;key&gt;/addons/&lt;id&gt;", "Remove an addon device."),
        ("GET/PUT", "/api/clients/&lt;key&gt;/scan-config", "Scan interval / enabled."),
        ("POST", "/api/clients/&lt;key&gt;/scan-now", "Trigger immediate scan."),
        ("GET", "/api/clients/&lt;key&gt;/scan-results", "Latest scan result."),
        ("GET", "/api/admin-client", "Admin self-client keep-alive."),
        ("GET", "/api/health", "Lightweight health check."),
        ("POST", "/api/supabase/register", "Register the server in the cloud registry."),
    ]))
    E.append(h2("17.2 scanner_api: Settings, Admin, Activity"))
    E.append(endpoint_table([
        ("GET/PUT", "/api/settings", "Global settings."),
        ("GET/PUT", "/api/settings/organization", "Organization profile."),
        ("GET/PUT", "/api/settings/security", "Security settings."),
        ("GET/PUT", "/api/settings/notifications", "Notification settings."),
        ("GET/POST/PUT", "/api/settings/connection", "Connection URL + token."),
        ("GET/PUT", "/api/settings/dashboard", "Dashboard widget settings."),
        ("GET/POST", "/api/admin/users", "List / create admin users."),
        ("DELETE", "/api/admin/users/&lt;id&gt;", "Delete admin user."),
        ("GET", "/api/admin/stats", "System statistics."),
        ("GET", "/api/admin/scan-changes", "Per-client scan diffs."),
        ("POST", "/api/admin/change-password", "Change password."),
        ("GET", "/api/activity-log", "Recent activity log."),
        ("GET/POST", "/api/groups", "List / create client groups."),
        ("DELETE", "/api/groups/&lt;id&gt;", "Delete a group."),
    ]))
    E.append(h2("17.3 scanner_api: Authentication"))
    E.append(endpoint_table([
        ("POST", "/api/auth/login", "Session login (username or email)."),
        ("POST", "/api/auth/logout", "Session logout."),
        ("GET", "/api/auth/me", "Current user profile."),
        ("GET/PUT", "/api/auth/profile", "Get / update profile."),
        ("POST", "/api/auth/change-password", "Change password."),
        ("POST", "/api/auth/upload-avatar", "Upload an avatar."),
        ("GET", "/api/auth/login-history", "Login history."),
        ("GET", "/api/auth/audit-logs", "Audit log trail."),
        ("GET", "/api/auth/active-sessions", "Active sessions."),
        ("POST", "/api/auth/token/obtain", "Obtain JWT access + refresh tokens."),
        ("POST", "/api/auth/token/refresh", "Refresh the access token."),
        ("POST", "/api/auth/token/verify", "Verify a token."),
        ("GET/POST", "/api/auth/api-keys", "List / create API keys."),
        ("DELETE", "/api/auth/api-keys/&lt;id&gt;", "Revoke an API key."),
    ]))
    E.append(h2("17.4 scanner_api: Organization"))
    E.append(endpoint_table([
        ("GET/POST", "/api/locations", "List / create locations."),
        ("GET/PUT", "/api/locations/&lt;uuid&gt;", "Location CRUD."),
        ("POST", "/api/locations/&lt;uuid&gt;/delete", "Delete a location."),
        ("POST", "/api/locations/&lt;uuid&gt;/archive", "Archive a location."),
        ("GET", "/api/locations/&lt;uuid&gt;/dashboard", "Location dashboard."),
        ("GET/POST", "/api/locations/&lt;uuid&gt;/export", "Location CSV export / import."),
        ("GET/POST", "/api/departments", "List / create departments."),
        ("GET/PUT", "/api/departments/&lt;uuid&gt;", "Department CRUD."),
        ("POST", "/api/departments/&lt;uuid&gt;/delete", "Delete a department."),
        ("POST", "/api/departments/&lt;uuid&gt;/disable", "Disable a department."),
        ("GET", "/api/departments/&lt;uuid&gt;/dashboard", "Department dashboard."),
        ("GET/POST", "/api/employees", "List / create employees."),
        ("GET/PUT", "/api/employees/&lt;uuid&gt;", "Employee CRUD."),
        ("POST", "/api/employees/&lt;uuid&gt;/delete", "Delete an employee."),
        ("POST", "/api/employees/&lt;uuid&gt;/deactivate", "Deactivate + auto-return assets."),
        ("GET", "/api/employees/&lt;uuid&gt;/assets", "Employee assets."),
        ("GET/POST", "/api/assignments", "List / create assignments."),
        ("POST", "/api/assignments/&lt;uuid&gt;/return", "Return an assignment."),
        ("POST", "/api/assignments/bulk", "Bulk assignments."),
        ("GET", "/api/org/audit-logs", "Organization audit logs."),
        ("GET", "/api/org/stats", "Organization stats."),
    ]))
    E.append(h2("17.5 scanner_api: Assets"))
    E.append(endpoint_table([
        ("GET/POST", "/api/assets", "List / create assets."),
        ("GET/PUT/DELETE", "/api/assets/&lt;uuid&gt;", "Asset CRUD."),
        ("POST", "/api/assets/&lt;uuid&gt;/status", "Status transition."),
        ("POST", "/api/assets/&lt;uuid&gt;/assign", "Assign asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/return", "Return asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/transfer", "Transfer asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/retire", "Retire asset."),
        ("POST", "/api/assets/&lt;uuid&gt;/dispose", "Dispose asset."),
        ("GET", "/api/assets/&lt;uuid&gt;/history", "Asset history."),
        ("GET", "/api/assets/&lt;uuid&gt;/qr", "Asset QR code."),
        ("GET", "/api/assets/dashboard", "Asset dashboard."),
        ("GET", "/api/assets/analytics", "Asset analytics."),
        ("GET/POST", "/api/assets/import", "CSV/XLSX import."),
        ("GET", "/api/assets/export", "Asset export."),
        ("POST", "/api/assets/bulk", "Bulk asset actions."),
        ("GET", "/api/scan/&lt;qr_code&gt;", "QR lookup."),
        ("GET", "/api/executive-analytics", "Cross-module KPIs."),
        ("GET", "/api/global-search", "Global search."),
    ]))
    E.append(h2("17.6 monitoring: Agent and Device"))
    E.append(endpoint_table([
        ("POST", "/api/monitoring/agent/register", "Agent registration (issues HMAC secret)."),
        ("POST", "/api/monitoring/agent/heartbeat", "HMAC heartbeat."),
        ("POST", "/api/monitoring/agent/heartbeat-public", "Public heartbeat."),
        ("POST", "/api/monitoring/agent/inventory", "Hardware/software inventory snapshot."),
        ("GET", "/api/monitoring/agent/version-check", "Agent version check."),
        ("GET/POST", "/api/monitoring/agent/pending-scans", "Pending scans for an agent."),
        ("GET", "/api/monitoring/dashboard", "Fleet dashboard aggregates."),
        ("GET", "/api/monitoring/trends", "Fleet trends."),
        ("GET", "/api/monitoring/devices", "List devices."),
        ("POST", "/api/monitoring/devices/bulk", "Bulk device actions."),
        ("GET/PUT", "/api/monitoring/devices/&lt;uuid&gt;", "Device detail / status."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/approve", "Approve device."),
        ("POST", "/api/monitoring/devices/&lt;uuid&gt;/block", "Block device."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/metrics", "Device metrics."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/history", "Device history."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/alerts", "Device alerts."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/hardware", "Hardware inventory."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/software", "Software inventory."),
        ("GET", "/api/monitoring/devices/&lt;uuid&gt;/heartbeats", "Heartbeat history."),
    ]))
    E.append(h2("17.7 monitoring: Alerts, Schedules, Reports"))
    E.append(endpoint_table([
        ("GET", "/api/monitoring/alerts", "Fleet alerts."),
        ("POST", "/api/monitoring/alerts/&lt;uuid&gt;/action", "Ack / resolve / dismiss."),
        ("GET/POST", "/api/monitoring/agent-versions", "Agent version catalog."),
        ("GET/PUT", "/api/monitoring/settings/unauthorized-software", "Unauthorized software list."),
        ("GET/POST", "/api/monitoring/schedules", "List / create schedules."),
        ("GET/PUT/DELETE", "/api/monitoring/schedules/&lt;uuid&gt;", "Schedule CRUD."),
        ("POST", "/api/monitoring/schedules/&lt;uuid&gt;/toggle", "Enable / disable."),
        ("GET", "/api/monitoring/schedules/&lt;uuid&gt;/history", "Schedule run history."),
        ("GET", "/api/monitoring/schedules/status", "Scheduler status."),
        ("GET/DELETE", "/api/monitoring/schedules/pending", "Pending scans."),
        ("GET", "/api/monitoring/reports/fleet/pdf", "Fleet PDF report."),
        ("GET", "/api/monitoring/reports/fleet/csv", "Fleet CSV export."),
        ("GET", "/api/monitoring/reports/device/&lt;uuid&gt;/pdf", "Device PDF report."),
        ("GET", "/api/monitoring/reports/device/&lt;uuid&gt;/csv", "Device CSV export."),
        ("GET", "/api/monitoring/reports/alerts/pdf", "Alerts PDF report."),
        ("GET", "/api/monitoring/reports/alerts/csv", "Alerts CSV export."),
    ]))
    E.append(h2("17.8 intelligence"))
    E.append(endpoint_table([
        ("GET", "/api/intelligence/dashboard", "Analytics dashboard."),
        ("GET/POST", "/api/intelligence/alerts", "List / create alerts."),
        ("GET", "/api/intelligence/alerts/&lt;uuid&gt;", "Alert detail."),
        ("POST", "/api/intelligence/alerts/&lt;uuid&gt;/action", "Ack / resolve / dismiss / assign."),
        ("GET", "/api/intelligence/alerts/&lt;uuid&gt;/history", "Alert history."),
        ("POST", "/api/intelligence/alerts/bulk", "Bulk actions."),
        ("POST", "/api/intelligence/alerts/run-checks", "Run alert checks."),
        ("GET", "/api/intelligence/alerts/export", "CSV export."),
        ("GET/POST", "/api/intelligence/alerts/rules", "Alert rules."),
        ("GET/PUT/DELETE", "/api/intelligence/alerts/rules/&lt;uuid&gt;", "Alert rule CRUD."),
        ("GET", "/api/intelligence/notifications", "Notifications."),
        ("POST", "/api/intelligence/notifications/mark-all-read", "Mark all read."),
        ("GET/PUT", "/api/intelligence/notifications/preferences", "Preferences."),
        ("POST", "/api/intelligence/notifications/&lt;uuid&gt;/action", "Read / archive."),
        ("GET/POST", "/api/intelligence/reports", "List / generate reports."),
        ("GET", "/api/intelligence/reports/&lt;uuid&gt;", "Report detail."),
        ("GET", "/api/intelligence/reports/&lt;uuid&gt;/export", "Download report."),
        ("GET/POST", "/api/intelligence/scheduled-reports", "Scheduled reports."),
        ("GET/PUT/DELETE", "/api/intelligence/scheduled-reports/&lt;uuid&gt;", "Scheduled report CRUD."),
        ("GET", "/api/intelligence/audit-logs", "Audit logs."),
        ("GET", "/api/intelligence/audit-logs/export", "Audit CSV export."),
        ("GET", "/api/intelligence/audit-logs/&lt;uuid&gt;", "Audit detail."),
        ("GET", "/api/intelligence/audit-logs/user/&lt;int&gt;", "User activity."),
        ("GET", "/api/intelligence/audit-logs/modules", "Module list."),
        ("GET", "/api/intelligence/audit-logs/actions", "Action list."),
        ("GET/POST", "/api/intelligence/compliance", "Compliance logs."),
        ("GET", "/api/intelligence/compliance/dashboard", "Compliance dashboard."),
        ("GET/PUT/DELETE", "/api/intelligence/compliance/&lt;uuid&gt;", "Compliance CRUD."),
        ("GET/POST", "/api/intelligence/retention-policies", "Retention policies."),
        ("GET/PUT", "/api/intelligence/settings", "Intelligence settings."),
    ]))
    E.append(h2("17.9 maintenance"))
    E.append(endpoint_table([
        ("GET/POST", "/api/maintenance/maintenance", "List / create maintenance."),
        ("GET/PUT/DELETE", "/api/maintenance/maintenance/&lt;uuid&gt;", "Maintenance CRUD."),
        ("POST", "/api/maintenance/maintenance/&lt;uuid&gt;/status", "Status transition."),
        ("POST", "/api/maintenance/maintenance/&lt;uuid&gt;/approve", "Approve / reject."),
        ("POST", "/api/maintenance/maintenance/&lt;uuid&gt;/upload", "Upload document."),
        ("GET", "/api/maintenance/maintenance/export", "CSV export."),
        ("GET/POST", "/api/maintenance/warranties", "List / create warranties."),
        ("GET/DELETE", "/api/maintenance/warranties/&lt;uuid&gt;", "Warranty detail."),
        ("GET/POST", "/api/maintenance/downtime", "List / create downtime."),
        ("POST", "/api/maintenance/downtime/&lt;uuid&gt;/end", "End downtime."),
        ("GET/POST", "/api/maintenance/licenses", "List / create licenses."),
        ("GET/PUT/DELETE", "/api/maintenance/licenses/&lt;uuid&gt;", "License CRUD."),
        ("POST", "/api/maintenance/licenses/&lt;uuid&gt;/archive", "Archive license."),
        ("POST", "/api/maintenance/licenses/assign", "Assign license."),
        ("POST", "/api/maintenance/licenses/assignments/&lt;uuid&gt;/remove", "Remove assignment."),
        ("GET", "/api/maintenance/licenses/export", "License CSV export."),
        ("GET/POST", "/api/maintenance/compliance", "Compliance records."),
        ("POST", "/api/maintenance/compliance/&lt;uuid&gt;/action", "Compliance action."),
        ("GET", "/api/maintenance/alerts", "Maintenance alerts."),
        ("POST", "/api/maintenance/alerts/&lt;uuid&gt;/action", "Alert action."),
        ("POST", "/api/maintenance/alerts/check", "Run alert checks."),
        ("GET", "/api/maintenance/dashboard", "Dashboard."),
        ("GET", "/api/maintenance/analytics/cost-trend", "Cost trend."),
        ("GET", "/api/maintenance/analytics/vendor-performance", "Vendor performance."),
        ("GET", "/api/maintenance/analytics/failure-rate", "Failure rates."),
        ("GET", "/api/maintenance/analytics/downtime", "Downtime analytics."),
        ("GET", "/api/maintenance/analytics/license-dashboard", "License dashboard."),
        ("GET", "/api/maintenance/analytics/license-utilization", "License utilization."),
        ("GET", "/api/maintenance/analytics/license-cost", "License cost."),
    ]))
    E.append(h2("17.10 System / Diagnostics"))
    E.append(endpoint_table([
        ("GET", "/__health/", "Health check (public)."),
        ("GET", "/__diag/", "Vercel DB/init diagnostics."),
        ("GET", "/download-client/", "Download the client installer with Content-SHA256."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 18. WebSocket Protocol
# ─────────────────────────────────────────────────────────────────────────────
def s18(E):
    E.append(h1("18. WebSocket Protocol"))
    E.append(para(
        "WebSockets are served by Channels via ASGI (monitoring/routing.py, django_admin/asgi.py). "
        "Routes: ws/agent/&lt;agent_id&gt;/ and ws/dashboard/."))
    E.append(h2("18.1 Dashboard Channel (browser)"))
    E.append(code_block(
        "CLIENT (browser)  -> ws(s)://HOST/ws/dashboard/\n"
        "SERVER sends     -> {type:'connected', message:'Dashboard connected...'}\n"
        "CLIENT ->        -> {type:'ping'}            SERVER -> {type:'pong'}\n"
        "CLIENT ->        -> {type:'subscribe_device', device_id}\n"
        "CLIENT ->        -> {type:'unsubscribe_device', device_id}\n"
        "\n"
        "SERVER PUSHES (group 'dashboard'):\n"
        "  {type:'dashboard.update',  data:{type:<event_type>, ...}}\n"
        "  {type:'dashboard.alert',   data:{...alert...}}\n"
        "  {type:'dashboard.agent_status', data:{agent_id, status}}\n"
        "  {type:'device.update',     data:{...}} (to device_<id> group)"
    ))
    E.append(h2("18.2 Agent Channel (agent)"))
    E.append(code_block(
        "AGENT connects  -> ws(s)://HOST/ws/agent/<agent_id>/\n"
        "SERVER sends    -> {type:'auth_required', message, agent_id}\n"
        "AGENT sends     -> {type:'auth', agent_id, secret, signature, timestamp}\n"
        "                    (timestamp within 300s; secret matches AgentSecret)\n"
        "SERVER sends    -> {type:'auth_success', server_time, pending_commands:[...]}\n"
        "   OR           -> {type:'auth_failed', message} then close 4003\n"
        "\n"
        "AGENT -> SERVER:\n"
        "  {type:'heartbeat', cpu, ram, disk, ...}     -> {type:'heartbeat_ack', health...}\n"
        "  {type:'scan_result', scan_type, scan_data}  -> {type:'scan_ack'}\n"
        "  {type:'event', event_type, severity, event_data}\n"
        "  {type:'status_update', monitoring_status}\n"
        "  {type:'pong'}\n"
        "\n"
        "SERVER -> AGENT (group 'agent_<agent_id>'):\n"
        "  {type:'command', command_type, command_id, payload}   # scan_now/config_update\n"
        "  {type:'ping', server_time}"
    ))
    E.append(h2("18.3 Command Reference"))
    E.append(endpoint_table([
        ("scan_now", "Admin requests an immediate scan. Agent runs collect_all() and submits via "
                     "POST /api/scan, then replies {type:'scan_result'}."),
        ("config_update", "Admin updates interval_seconds / enabled. Agent merges the new scan config."),
        ("ping", "Heartbeat keep-alive; agent replies pong."),
    ], widths=[3.0 * cm, PAGE_W - 2 * MARGIN - 3.0 * cm]))
    E.append(h2("18.4 Message Flow Guarantees"))
    E.extend(bullets([
        "Agent heartbeat messages flow both ways: WS is the live channel; the 30-second HTTP ping is "
        "the durable fallback.",
        "Pending commands are read from DeviceMonitoringInfo.notes (semicolon-delimited) and delivered "
        "in auth_success.",
        "Offline agents keep working over HTTP; when they reconnect, the pending command list is "
        "delivered immediately.",
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 19. Event Types & Bus
# ─────────────────────────────────────────────────────────────────────────────
def s19(E):
    E.append(h1("19. Event Types and the Event Bus"))
    E.append(para(
        "The event bus (monitoring/event_bus.py) is an in-process pub/sub singleton. It is the "
        "connective tissue of the monitoring module: every notable occurrence is published once, and "
        "subscribers turn it into alerts, notifications, history, and dashboard broadcasts. Event types:"))
    E.append(endpoint_table([
        ("hw_component_added / removed / modified", "Hardware inventory change", "Severity from component map "
                                                                                 "(storage critical)."),
        ("sw_installed / sw_removed / sw_version_changed", "Software change", "Info by default."),
        ("sw_unauthorized", "Blocklisted software found", "Warning."),
        ("sw_antivirus_removed", "Antivirus product removed", "Critical."),
        ("health_level_changed / health_score_updated", "Health recomputation", "Dashboard + history."),
        ("alert_created / acknowledged / resolved / dismissed", "Alert lifecycle", "Dashboard broadcast."),
        ("device_registered / approved / blocked / deleted / offline / online / status_changed",
         "Device lifecycle", "Alerts + history + dashboard."),
        ("agent_version_changed", "Agent updated", "Info alert + notification."),
        ("heartbeat_received", "Every heartbeat", "Metrics pipeline."),
        ("scan_completed / scan_scheduled", "Scan lifecycle", "Dashboard + history."),
    ], widths=[6.6 * cm, 4.6 * cm, PAGE_W - 2 * MARGIN - 11.2 * cm]))
    E.append(h2("19.1 How a Published Event Is Handled"))
    E.append(code_block(
        "publish(event)\n"
        "  `-> subscribers registered for that event_type\n"
        "  `-> wildcard subscriber (broadcasts to dashboard + device groups)\n"
        "  `-> alert-creation subscribers (severity-gated)\n"
        "  `-> notification subscriber (admin in-app notification)\n"
        "  `-> DeviceHistory writer (category from event prefix)\n"
        "  `-> recent-events ring buffer (queryable via get_recent_events)"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# 20. Database Schema Overview
# ─────────────────────────────────────────────────────────────────────────────
def s20(E):
    E.append(h1("20. Database Schema Overview"))
    E.append(para(
        "Each admin server owns its own database. Table prefixes: none (scanner_api tables like "
        "clients, scan_results), monitoring_, intelligence_, maintenance_."))
    E.append(h2("20.1 Table Families"))
    E.append(component_table([
        ("Identity & fleet", "companies, client_groups, clients, scan_results, addon_devices, "
                             "device_fingerprints."),
        ("Settings & audit", "settings, activity_logs, audit_logs, login_history, login_attempts, "
                             "administrator_profiles."),
        ("Organization", "locations, departments, employees, employee_asset_assignments, org_audit_logs."),
        ("Assets", "asset_categories, asset_vendors, assets, asset_assignments_v2, asset_transfers, "
                   "asset_history, asset_documents, api_keys."),
        ("Monitoring", "monitoring_device_info, monitoring_hardware_inventory, monitoring_software_inventory, "
                       "monitoring_device_heartbeat, monitoring_device_metrics, monitoring_device_history, "
                       "monitoring_device_alerts, monitoring_agent_versions, monitoring_agent_secrets."),
        ("Scheduling", "monitoring_scheduled_scans, monitoring_pending_scans, monitoring_scan_schedule_logs."),
        ("Intelligence", "intelligence_alerts, intelligence_alert_history, intelligence_alert_rules, "
                         "intelligence_notifications, intelligence_notification_preferences, "
                         "intelligence_reports, intelligence_scheduled_reports, intelligence_audit_logs, "
                         "intelligence_compliance_logs, intelligence_dashboard_analytics, "
                         "intelligence_retention_policies."),
        ("Maintenance", "maintenance_records, maintenance_history, maintenance_documents, warranty_records, "
                        "downtime_records, software_licenses, license_assignments, license_history, "
                        "compliance_records, maintenance_alerts."),
    ]))
    E.append(h2("20.2 Key Relationships"))
    E.extend(bullets([
        "Client &#8594; ScanResult (1:N); Client &#8594; AddonDevice (1:N); Client &#8594; "
        "DeviceMonitoringInfo (1:1); Client &#8594; DeviceHeartbeat / HardwareInventory / "
        "SoftwareInventory / DeviceAlert / DeviceHistory / AgentSecret / PendingScan (1:N).",
        "Company &#8594; Client, Setting, Location, Department, Employee, Asset (1:N) &#8212; the tenant "
        "backbone.",
        "Employee &#8594; Client (through EmployeeAssetAssignment); Asset &#8594; Employee (assigned_to); "
        "License &#8594; Asset/Employee/Department (through LicenseAssignment).",
        "DeviceHistory and AssetHistory are immutable: save() raises on update.",
    ]))
    E.append(h2("20.3 Database Location"))
    E.append(endpoint_table([
        ("Development", "admin/data/scanner.db", "SQLite next to the admin server."),
        ("Windows (packaged)", "%APPDATA%\\SystemScannerPro\\scanner.db", "Per-user app data."),
        ("Linux (packaged)", "~/.local/share/SystemScannerPro/scanner.db", "XDG data home."),
        ("macOS (packaged)", "~/Library/Application Support/SystemScannerPro/scanner.db", "App support."),
        ("Vercel", "PostgreSQL via DATABASE_URL", "Supabase pooler (port 6543)."),
    ], widths=[4.2 * cm, 6.4 * cm, PAGE_W - 2 * MARGIN - 10.6 * cm]))


# ─────────────────────────────────────────────────────────────────────────────
# 21. Reports & Exports
# ─────────────────────────────────────────────────────────────────────────────
def s21(E):
    E.append(h1("21. Reports and Exports"))
    E.append(h2("21.1 Monitoring Reports"))
    E.append(field_table([
        ("Fleet PDF", "generate_fleet_pdf()", "Fleet summary table (status counts, health) + per-device "
                                              "details."),
        ("Fleet CSV", "generate_fleet_csv()", "10-column fleet inventory export."),
        ("Device PDF", "generate_device_pdf(key)", "Device info + active alerts."),
        ("Device CSV", "generate_device_csv(key)", "90-day alert history for one device."),
        ("Alerts PDF", "generate_alerts_pdf(days=30)", "Alert history table."),
        ("Alerts CSV", "generate_alerts_csv(days=30)", "Alert history export."),
    ]))
    E.append(h2("21.2 Intelligence Report Engine"))
    E.append(para(
        "The intelligence engine generates nine report types in CSV, Excel, or PDF, persists each as a "
        "Report row, and lets users schedule recurring reports. Report types: asset_inventory, "
        "asset_assignment, expiring_licenses, upcoming_maintenance, device_health, compliance_report, "
        "monthly_summary, software_inventory, audit_report."))
    E.append(h2("21.3 Maintenance and License Exports"))
    E.append(para(
        "Maintenance records, licenses, locations, departments, employees, assets, alerts, and audit "
        "logs all have CSV export endpoints; assets additionally support CSV/XLSX import."))


# ─────────────────────────────────────────────────────────────────────────────
# 22. Background Tasks & Scheduling
# ─────────────────────────────────────────────────────────────────────────────
def s22(E):
    E.append(h1("22. Background Tasks and Scheduling"))
    E.append(component_table([
        ("Admin UDP discovery", "main.py start_discovery_listener/broadcaster: answers DISCOVER_ADMIN and "
                                "broadcasts ADMIN_HERE on UDP 45000."),
        ("Admin self-heartbeat", "main.py admin_client_heartbeat_loop: keeps the admin self-client online "
                                 "every 30 s."),
        ("Admin self-scan", "main.py admin_self_scan: one local scan on startup."),
        ("Cloud-registry refresh", "main.py cloud_discovery_refresh_loop: re-registers the public IP every "
                                   "300 s."),
        ("APScheduler", "monitoring/scheduler.py: interval/daily/weekly/monthly/once scheduled scans, "
                        "splitting targets into online (WebSocket) and offline (PendingScan)."),
        ("Heartbeat watchdog", "client/main.py HeartbeatWatchdog: restarts a dead heartbeat thread."),
        ("Client cloud discovery loop", "client/main.py cloud_discovery_loop: re-queries the registry every "
                                        "300 s."),
        ("Client UDP listener", "client/main.py listen_admin_broadcast: adopts ADMIN_HERE broadcasts."),
        ("Event dispatcher", "client/events/dispatcher.py: flushes batched events every 5 s."),
        ("Stale checker", "manage.py stale_checker: marks stale clients offline (loop, 30 s)."),
        ("Alert checkers", "manage.py alert_checker / health_checker / offline_detector; POST "
                           "alerts/check and alerts/run-checks."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# 23. Deployment Guide
# ─────────────────────────────────────────────────────────────────────────────
def s23(E):
    E.append(h1("23. Deployment Guide"))
    E.append(h2("23.1 Self-Hosted (Local / VPS)"))
    E.append(code_block(
        "# Install\n"
        "pip install -r requirements.txt\n"
        "\n"
        "# Start the admin server (binds 0.0.0.0, port 80)\n"
        "python admin/main.py\n"
        "\n"
        "# With a public domain and WebSocket support (ASGI via daphne):\n"
        "python admin/main.py --host 0.0.0.0 --port 80 --domain scanner.example.com --asgi\n"
        "\n"
        "# Agents connect with:\n"
        "python client/main.py https://scanner.example.com"
    ))
    E.append(h2("23.2 nginx Reverse Proxy with HTTPS"))
    E.append(code_block(
        "server { listen 80; server_name scanner.example.com; return 301 https://$host$request_uri; }\n"
        "server {\n"
        "    listen 443 ssl;\n"
        "    server_name scanner.example.com;\n"
        "    ssl_certificate /etc/letsencrypt/live/scanner.example.com/fullchain.pem;\n"
        "    ssl_certificate_key /etc/letsencrypt/live/scanner.example.com/privkey.pem;\n"
        "    location / {\n"
        "        proxy_pass http://127.0.0.1:80;\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        "    }\n"
        "    location /ws/ {\n"
        "        proxy_pass http://127.0.0.1:80;\n"
        "        proxy_http_version 1.1;\n"
        "        proxy_set_header Upgrade $http_upgrade;\n"
        "        proxy_set_header Connection \"upgrade\";\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_read_timeout 86400;\n"
        "    }\n"
        "}\n"
        "\n"
        "sudo certbot --nginx -d scanner.example.com"
    ))
    E.append(h2("23.3 Vercel Serverless"))
    E.append(para(
        "vercel.json routes everything to api/index.py (@vercel/python, maxDuration 30). The bootstrap "
        "sets DJANGO_SETTINGS_MODULE, migrates, creates the admin user, stores the admin URL in the "
        "cloud registry, and forces auto-approve off. Requirements: DATABASE_URL (Supabase PostgreSQL, "
        "pooler rewritten to port 6543), DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS."))
    E.append(code_block(
        "# Vercel environment variables\n"
        "DJANGO_SECRET_KEY      = <random>\n"
        "DJANGO_DEBUG           = False\n"
        "DJANGO_ALLOWED_HOSTS   = *\n"
        "DATABASE_URL           = postgresql://postgres:****@db.<proj>.supabase.co:5432/postgres\n"
        "SUPABASE_URL           = https://<proj>.supabase.co\n"
        "SUPABASE_SERVICE_KEY   = <service role key>\n"
        "\n"
        "# Vercel limitations (client auto-adapts)\n"
        "WebSocket   -> not supported; agents use HTTP polling\n"
        "UDP 45000   -> not supported; clients use cloud discovery / URL\n"
        "APScheduler -> not supported; use Vercel cron to call schedule endpoints\n"
        "SQLite      -> not supported; PostgreSQL required"
    ))
    E.append(h2("23.4 Cloud Discovery"))
    E.append(para(
        "The admin server registers itself in the Supabase server_registry table (setup_cloud_discovery"
        ".sql creates it with public read and service-role write policies). Clients query it during "
        "startup and every 300 s to follow the admin if it moves. A GitHub Actions workflow "
        "(supabase-register.yml) re-registers hourly as a safety net."))


# ─────────────────────────────────────────────────────────────────────────────
# 24. Building Executables
# ─────────────────────────────────────────────────────────────────────────────
def s24(E):
    E.append(h1("24. Building Executables"))
    E.append(para(
        "build_client.py builds the client (and admin) into single-file executables with PyInstaller. "
        "The script auto-installs PyInstaller, collects client data files into the bundle, and writes a "
        ".spec file to avoid command-line length limits."))
    E.append(code_block(
        "pip install pyinstaller\n"
        "python build_client.py          # builds client_scanner.exe\n"
        "\n"
        "# Output handling:\n"
        "# - dist/client_scanner.exe\n"
        "# - copied to admin/data/client_scanner.exe (downloadable from /download-client/)\n"
        "# - admin/data/client_scanner.zip (client_scanner.dat + run.bat + README)\n"
        "\n"
        "# Optional code signing via env vars:\n"
        "#   CODE_SIGN_PFX, CODE_SIGN_PASSWORD, CODE_SIGN_TIMESTAMP\n"
        "\n"
        "# Run the built client:\n"
        "client_scanner.exe http://192.168.1.100:80\n"
        "client_scanner.exe https://your-project.vercel.app"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# 25. Configuration Reference
# ─────────────────────────────────────────────────────────────────────────────
def s25(E):
    E.append(h1("25. Configuration Reference"))
    E.append(h2("25.1 Environment Variables"))
    E.append(field_table([
        ("DJANGO_SECRET_KEY", "string", "Django secret key (override the insecure default)."),
        ("DJANGO_DEBUG", "bool", "Debug mode."),
        ("DJANGO_ALLOWED_HOSTS", "csv", "Allowed hosts (* or comma list)."),
        ("DATABASE_URL", "url", "PostgreSQL connection (required on Vercel)."),
        ("DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT", "string", "PostgreSQL components."),
        ("DB_CONN_MAX_AGE", "int", "0 on Vercel, 10 on persistent servers."),
        ("SUPABASE_URL", "string", "Supabase project URL (cloud registry)."),
        ("SUPABASE_SERVICE_KEY", "string", "Service role key for registry writes."),
        ("VERCEL", "flag", "Set to 1 on Vercel (IS_VERCEL mode)."),
        ("ADMIN_SERVER_URL", "string", "Client-side override of the admin URL."),
    ]))
    E.append(h2("25.2 Important Setting Keys"))
    E.append(field_table([
        ("auto_approve", "bool", "Auto-approve new registrations."),
        ("stale_threshold_seconds", "int", "Default 120; offline cutoff."),
        ("scan_all_interval", "int", "Interval for scan-all."),
        ("admin_client_key", "string", "Admin self-client key."),
        ("admin_server_url / admin_connection_token", "string", "Connection settings."),
        ("session_timeout_minutes", "int", "Default 120."),
        ("alert_cpu_threshold / alert_ram_threshold", "int", "Default 90."),
        ("alert_disk_threshold / alert_disk_free_gb", "int", "Default 95 / 5."),
        ("unauthorized_software_list", "csv", "Software that triggers sw_unauthorized."),
        ("monitoring_warning_seconds / monitoring_offline_seconds / monitoring_critical_seconds",
         "int", "Offline alert tiers 300 / 900 / 1800."),
        ("alert_escalation_enabled, notification_retention_days, report_retention_days, "
         "audit_retention_days", "mixed", "Intelligence settings."),
    ]))
    E.append(h2("25.3 Client Configuration Files"))
    E.append(field_table([
        ("client_key.json", "registration_key + fingerprint", "Identity; do not delete unless re-registering."),
        ("client_config.json", "admin_url, scan_interval, auto_start, manual_url", "Connection and scan "
                                                                                   "settings."),
        ("client_agent.log / client_crash.log", "log files", "Runtime and startup diagnostics."),
    ]))
    E.append(h2("25.4 Admin CLI Options"))
    E.append(endpoint_table([
        ("--port PORT", "Server port", "Default 80."),
        ("--host HOST", "Bind address", "Prompted on first run."),
        ("--debug", "Debug mode", "Enables Django debug."),
        ("--username / --password", "Default admin", "admin / admin123."),
        ("--reset", "Re-ask bind IP", "Clears saved host."),
        ("--domain DOMAIN", "Public domain", "Registers https://&lt;domain&gt; for cloud discovery."),
        ("--asgi", "ASGI server", "Serve with daphne (WebSocket support)."),
    ], widths=[4.2 * cm, 4.0 * cm, PAGE_W - 2 * MARGIN - 8.2 * cm]))


# ─────────────────────────────────────────────────────────────────────────────
# 26. Operations & Administration
# ─────────────────────────────────────────────────────────────────────────────
def s26(E):
    E.append(h1("26. Operations and Administration"))
    E.append(h2("26.1 Management Commands"))
    E.append(code_block(
        "python admin/manage.py migrate            # apply DB migrations\n"
        "python admin/manage.py scan_local         # scan the admin machine\n"
        "python admin/manage.py scan_all           # trigger scans on all clients\n"
        "python admin/manage.py stale_checker      # mark stale clients offline\n"
        "python admin/manage.py alert_checker      # evaluate offline alerts\n"
        "python admin/manage.py health_checker     # recompute health scores\n"
        "python admin/manage.py offline_detector   # mark offline devices\n"
        "python admin/manage.py clear_data         # wipe data, recreate admin\n"
        "python admin/manage.py createsuperuser    # create a superuser\n"
        "python admin/manage.py changepassword     # change a user's password\n"
        "python admin/manage.py collectstatic      # collect static files"
    ))
    E.append(h2("26.2 Reset Procedures"))
    E.append(endpoint_table([
        ("Reset admin IP", "python admin/main.py --reset", "Re-prompts for the bind address."),
        ("Reset admin password", "Delete admin/data/scanner.db then re-run", "Recreates DB + default admin."),
        ("Reset client", "Delete client/client_key.json", "New key + fingerprint re-link on re-run."),
        ("Reset client URL", "Delete client_config.json", "Re-prompts for the admin URL."),
        ("Full factory reset", "Delete DB + client key/config files", "Brand-new state on both sides."),
    ], widths=[4.2 * cm, 6.6 * cm, PAGE_W - 2 * MARGIN - 10.8 * cm]))
    E.append(h2("26.3 Running as a Service"))
    E.append(code_block(
        "# Windows scheduled task\n"
        'schtasks /create /tn "SystemScanner" /tr "C:\\path\\client_scanner.exe http://SERVER" /sc onstart\n'
        "\n"
        "# Linux systemd\n"
        "# /etc/systemd/system/scanner-client.service\n"
        "[Unit]\n"
        "Description=System Scanner Client\n"
        "After=network.target\n"
        "[Service]\n"
        "ExecStart=/usr/bin/python3 /path/to/client/main.py http://SERVER\n"
        "Restart=always\n"
        "RestartSec=10\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
        "\n"
        "# macOS launchd (~/Library/LaunchAgents/com.scanner.client.plist)\n"
        "# RunAtLoad true, KeepAlive true"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# 27. Troubleshooting
# ─────────────────────────────────────────────────────────────────────────────
def s27(E):
    E.append(h1("27. Troubleshooting"))
    E.append(endpoint_table([
        ("Client cannot connect", "Verify the admin is running and reachable; allow TCP 80 and UDP 45000 "
                                  "through the firewall; bind 0.0.0.0; use the full http:// URL."),
        ("Client 'Connection failed'", "Admin offline, network issue, or URL missing the http(s) prefix."),
        ("WebSocket not connecting", "Check port 80 reachability; ensure /ws/ has proxy upgrade headers; "
                                     "on Vercel WebSocket is unsupported (HTTP fallback is normal)."),
        ("Client stays Pending", "Approve from the dashboard, or enable auto-approve in Settings."),
        ("No live updates", "The Live badge must be green on the monitoring page; the server must run ASGI "
                            "(daphne/uvicorn)."),
        ("Scheduler warning (no such table)", "Run python admin/manage.py migrate."),
        ("Events not sent", "Look for '[OK] 4 event monitors active' in the client log; if offline, events "
                            "are queued to disk and replay on reconnect."),
        ("Heartbeat errors", "Consecutive errors trigger cloud + UDP re-discovery after 5 failures."),
        ("Vercel 502 / cold start", "Cold starts may take 5-10 s; first request may time out."),
        ("Vercel DB connection refused", "Check DATABASE_URL, Supabase project state, and IP allow-list."),
        ("Cannot delete a device", "Soft delete only removes from dashboards; re-registration with the same "
                                   "key returns 403 until the row is purged."),
        ("Blocked device still pings", "Blocking deactivates AgentSecrets; the device is re-listed as "
                                       "pending, not online."),
    ], widths=[4.6 * cm, PAGE_W - 2 * MARGIN - 4.6 * cm]))


# ─────────────────────────────────────────────────────────────────────────────
# 28. Known Issues & Limitations
# ─────────────────────────────────────────────────────────────────────────────
def s28(E):
    E.append(h1("28. Known Issues and Limitations"))
    E.append(endpoint_table([
        ("run_alert_checks mismatch", "intelligence management command passes escalate_only=... but the "
                                      "function takes no arguments and returns a list; the API view calls "
                                      "it correctly."),
        ("Scheduled reports are CRUD-only", "ScheduledReport has no background executor; nothing computes "
                                            "next_run or runs reports on schedule."),
        ("Vercel limits", "No WebSocket, UDP, or APScheduler; sessions rely on signed cookies; SQLite is "
                          "ephemeral."),
        ("Version skew", "Client code reports VERSION 1.6.1 while the exe version resource is 3.0.0.0."),
        ("README drift", "References build/build.py, pyusb, psutil; the real builder is build_client.py "
                         "and the client uses websockets + watchdog + stdlib."),
        ("Path handling", "client_config.json may carry a URL path (e.g. /kailasam-shiv); the communicator "
                          "normalizes to scheme://netloc."),
        ("Embedded credentials", "Service-role JWT and example keys exist in repo files; rotate before "
                                 "production."),
        ("MaintenanceAlert actor", "acknowledge_alert/resolve_alert hardcode acknowledged_by='admin'."),
        ("License seat thresholds", "maintenance uses seats_used >= purchased_seats while intelligence uses "
                                    "> ; inconsistent."),
    ], widths=[5.2 * cm, PAGE_W - 2 * MARGIN - 5.2 * cm]))


# ─────────────────────────────────────────────────────────────────────────────
# 29. Appendix
# ─────────────────────────────────────────────────────────────────────────────
def s29(E):
    E.append(h1("29. Appendix"))
    E.append(h2("29.1 Device Status Indicators"))
    E.append(endpoint_table([
        ("Online", "Green dot", "Heartbeats received (every 30 s)."),
        ("Offline", "Red dot", "No heartbeat for over the stale threshold (120 s)."),
        ("Pending", "Yellow dot", "Registered but not yet approved."),
        ("Blocked", "Purple dot", "Blocked by admin; agent secrets deactivated."),
        ("Maintenance / Inactive", "Operator-set", "Administrative monitoring statuses."),
    ]))
    E.append(h2("29.2 Scan Data Collected"))
    E.append(field_table([
        ("Processor", "Snapshot", "Manufacturer, model, serial, cores, threads, speed, cache/architecture."),
        ("RAM", "Snapshot", "Per-module manufacturer, capacity, serial, speed, form factor."),
        ("Storage", "Snapshot", "Disks (model, serial, size, interface) + partitions (filesystem, mount)."),
        ("Motherboard", "Snapshot", "Manufacturer, model, serial, BIOS version."),
        ("GPU", "Snapshot", "Name, vendor, driver, dedicated memory."),
        ("OS", "Snapshot", "Name, version, build, architecture, install date."),
        ("Network", "Snapshot", "Interfaces (name, MAC, IPv4, status)."),
        ("Peripherals", "Snapshot", "Keyboard, mouse, audio, webcam, printers, USB devices."),
        ("Software", "Snapshot", "Installed apps (name, version, publisher)."),
        ("Windows Updates", "Snapshot", "KB IDs + descriptions (Windows only)."),
        ("Antivirus", "Snapshot", "AV products + firewall status (Windows only)."),
        ("User Accounts", "Snapshot", "Local user accounts (Windows only)."),
    ]))
    E.append(h2("29.3 Health Score Formula"))
    E.append(kv_table([
        ("CPU (25%)", "100 when &#8804;70%; linear fall to 50 at 85%; floor 10 beyond 85%."),
        ("RAM (25%)", "Same piecewise scoring as CPU."),
        ("Disk (20%)", "100 when &#8804;80%; linear fall to 30 at 95%; floor 0 beyond 95%."),
        ("Connectivity (15%)", "100 when connected; 0 when disconnected."),
        ("Software health (15%)", "100 with antivirus present; 60 otherwise; 80 when no software data."),
        ("Level", "&#8805;80 healthy; &#8805;50 warning; below critical."),
    ]))
    E.append(h2("29.4 Monitoring Thresholds"))
    E.append(endpoint_table([
        ("MONITORING_WARNING_SECONDS", "300", "First offline warning."),
        ("MONITORING_OFFLINE_SECONDS", "900", "Marked offline."),
        ("MONITORING_CRITICAL_SECONDS", "1800", "Critical offline alert."),
        ("Stale threshold (setting)", "120 s", "Client considered stale/offline."),
        ("Heartbeat interval", "30 s", "Agent ping cadence."),
        ("Anomaly z-threshold / iqr / lookback", "2.5 / 1.5 / 168 h", "Statistical detectors."),
    ], widths=[7.0 * cm, 2.6 * cm, PAGE_W - 2 * MARGIN - 9.6 * cm]))
    E.append(h2("29.5 Ports"))
    E.append(endpoint_table([
        ("80 / custom (TCP)", "HTTP + WebSocket", "Admin web + API + WS upgrade."),
        ("443 (TCP)", "HTTPS", "Production TLS."),
        ("45000 (UDP)", "Discovery", "ADMIN_HERE broadcasts / DISCOVER_ADMIN queries."),
    ], widths=[3.2 * cm, 4.2 * cm, PAGE_W - 2 * MARGIN - 7.4 * cm]))
    E.append(h2("29.6 Glossary"))
    E.append(kv_table([
        ("Agent", "Client-side process that scans, monitors, and reports to the admin server."),
        ("Client", "Server-side record of a machine (key, fingerprint, approval, status)."),
        ("Registration key", "8-char identity used by all HTTP calls; lives in client_key.json."),
        ("Hardware fingerprint", "SHA-256 of motherboard/CPU/disk/MAC identity; survives reinstalls."),
        ("DeviceMonitoringInfo", "Per-device monitoring state row in the monitoring module."),
        ("AgentSecret", "HMAC credential pair (agent_id + secret) for agent authentication."),
        ("Event bus", "In-process pub/sub that turns every notable occurrence into alerts, history, "
                      "notifications, and broadcasts."),
        ("PendingScan", "Offline scan queue; delivered to an agent when it reconnects."),
        ("Health score", "0-100 composite of CPU, RAM, disk, connectivity, and software health."),
        ("Soft delete", "Marking a row deleted=True instead of removing it, preserving history."),
        ("Company", "Tenant entity; isolates fleet data and settings."),
        ("Cloud registry", "Supabase server_registry table used for discovery."),
    ]))
    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=0.7, color=GRID))
    E.append(Spacer(1, 3))
    E.append(para(
        "This document was generated from the project source and configuration. The authoritative code "
        "lives in admin/ and client/. For the connection lifecycle see admin/scanner_api/views.py and "
        "client/communicator.py; for monitoring, WebSocket, scheduler, and AI see admin/monitoring/; for "
        "insights see admin/intelligence/ and admin/maintenance/.", SMALL))


# ─────────────────────────────────────────────────────────────────────────────
# 30. Deep-Dive: REST API Worked Examples
# ─────────────────────────────────────────────────────────────────────────────
def s30(E):
    E.append(h1("30. Deep-Dive: REST API Worked Examples"))
    E.append(para(
        "This section shows real request/response shapes for the most important endpoints. "
        "All bodies are JSON (Content-Type: application/json) unless stated otherwise. Agent "
        "HTTP endpoints are authenticated with HMAC-SHA256 over the raw body using headers "
        "X-Agent-ID, X-Signature, and X-Timestamp (max age 300 s), per admin/monitoring/security.py. "
        "Browser and API-key endpoints use session cookies, JWT, or API keys. Error responses "
        "are DRF JSON with a \"detail\" key."))
    E.append(h2("30.1 Session login"))
    E.append(code_block(
        'POST /api/auth/login  (no auth required)\n'
        '{\n'
        '  "username": "admin",\n'
        '  "password": "StrongPass!123",\n'
        '  "remember_me": true\n'
        '}\n'
        '\n'
        '200 OK  ->  {\n'
        '  "user": { "id": 1, "username": "admin", "email": "admin@example.com", "is_superuser": true },\n'
        '  "message": "Login successful"\n'
        '}\n'
        '401  ->  { "detail": "Invalid credentials", "attempts_remaining": 4 }\n'
        '403  ->  { "detail": "Account locked" }'))
    E.append(para(
        "A successful login writes an AuditLog (login_success), a LoginHistory row, records the "
        "IP and user agent, and issues the session cookie (scanner_auth, TimestampSigner, 30 days "
        "if remember_me). Failed logins write LoginAttempt rows and, past the lockout threshold, "
        "lock the account (see admin/scanner_api/auth_utils.py and validators.py)."))
    E.append(h2("30.2 JWT token endpoints"))
    E.append(code_block(
        'POST /api/auth/token/obtain\n'
        '{\n'
        '  "username": "admin",\n'
        '  "password": "StrongPass!123"\n'
        '}\n'
        '200 OK  ->  { "access": "eyJhbGciOiJIUzI1NiIs...", "refresh": "eyJhbGciOiJIUzI1NiIs..." }\n'
        '\n'
        'POST /api/auth/token/refresh\n'
        '{\n'
        '  "refresh": "eyJhbGciOiJIUzI1NiIs..."\n'
        '}\n'
        '200 OK  ->  { "access": "eyJhbGciOiJIUzI1NiIs..." }\n'
        '\n'
        'POST /api/auth/token/verify\n'
        '{\n'
        '  "token": "eyJhbGciOiJIUzI1NiIs..."\n'
        '}\n'
        '200 OK (valid)  |  401 (expired or invalid)'))
    E.append(para(
        "JWT settings (admin/django_admin/settings.py): HS256, access token 60 minutes, refresh "
        "token 7 days, issuer \"system-scanner-pro\", signed with the Django SECRET_KEY."))
    E.append(h2("30.3 API key management"))
    E.append(code_block(
        'GET  /api/auth/api-keys        ->  { "api_keys": [ { "id": 1, "name": "CI", "is_active": true,\n'
        '                                                    "created_at": "2026-08-14T09:00:00Z" } ] }\n'
        'POST /api/auth/api-keys\n'
        '{\n'
        '  "name": "automation-1"\n'
        '}\n'
        '201  ->  { "id": 2, "name": "automation-1", "key": "<plaintext shown once>", "is_active": true }\n'
        'DELETE /api/auth/api-keys/2   ->  204 No Content'))
    E.append(para(
        "Keys are generated with token_hex(32) and stored hashed (SHA-256) in the api_keys table "
        "(admin/scanner_api/api_key_auth.py). API-key requests are rate limited to 60 per minute."))
    E.append(h2("30.4 Client registration (core scanner_api)"))
    E.append(code_block(
        'POST /api/register   (no auth required)\n'
        '{\n'
        '  "hostname": "DESKTOP-AB12CD",\n'
        '  "ip_address": "192.168.1.50",\n'
        '  "mac_address": "AA:BB:CC:DD:EE:FF",\n'
        '  "os": "Windows 10 Pro",\n'
        '  "platform": "Windows",\n'
        '  "client_version": "1.6.1",\n'
        '  "username": "kailas",\n'
        '  "device_type": "desktop"\n'
        '}\n'
        '201 Created  ->  { "client_key": "Ab12cD34", "registered": true, "approved": false }\n'
        '409 Conflict ->  { "detail": "..." }   (duplicate key / fingerprint collision)'))
    E.append(para(
        "The agent calls this from client/communicator.py register(); the server keeps the same "
        "registration_key, refreshes the fingerprint, and resets status to pending so the admin "
        "can re-approve after a DB reset. Approval state is returned so the agent can wait for "
        "the admin (see client/main.py heartbeat_loop)."))
    E.append(h2("30.5 Monitoring agent registration (HMAC)"))
    E.append(code_block(
        'POST /api/monitoring/agent/register\n'
        'X-Agent-ID: <agent_uuid>\n'
        'X-Signature: <hmac-sha256-hex>\n'
        'X-Timestamp: 1723600000.123\n'
        '{\n'
        '  "hostname": "DESKTOP-AB12CD",\n'
        '  "os": "Windows 10 Pro",\n'
        '  "platform": "Windows",\n'
        '  "version": "1.6.1",\n'
        '  "architecture": "AMD64",\n'
        '  "cpu": "Intel Core i7-12700",\n'
        '  "memory": "32768 MB",\n'
        '  "hd": "1 TB SSD",\n'
        '  "ip_address": "192.168.1.50",\n'
        '  "mac_address": "AA:BB:CC:DD:EE:FF",\n'
        '  "username": "kailas"\n'
        '}\n'
        '200 OK  ->  { "agent_id": "<uuid>", "secret_key": "<64-char-hex>", "approved": false }'))
    E.append(para(
        "The signature is HMAC-SHA256(key = secret_key, message = raw request body) as a hex "
        "digest (admin/monitoring/security.py compute_signature). The agent stores the returned "
        "secret_key and uses it for every subsequent signed call. RateLimiter caps requests at "
        "60 per minute per key."))
    E.append(h2("30.6 Agent heartbeat (public variant used by the agent)"))
    E.append(code_block(
        'POST /api/monitoring/agent/heartbeat-public\n'
        '{\n'
        '  "registration_key": "Ab12cD34",\n'
        '  "cpu_usage_pct": 34.5,\n'
        '  "ram_usage_pct": 61.2,\n'
        '  "disk_usage_pct": 47.8,\n'
        '  "disk_free_gb": 512.3,\n'
        '  "disk_total_gb": 1000.0,\n'
        '  "network_connected": true,\n'
        '  "uptime_seconds": 482000,\n'
        '  "load_average": 0.8,\n'
        '  "agent_version": "1.6.1",\n'
        '  "hostname": "DESKTOP-AB12CD",\n'
        '  "current_user": "kailas"\n'
        '}\n'
        '200 OK  ->  { "status": "ok" }'))
    E.append(para(
        "The current agent sends heartbeats over this public HTTP endpoint every ~5 seconds "
        "(client/main.py heartbeat_loop -> monitor_heartbeat_public), which updates "
        "DeviceMonitoringInfo.last_heartbeat, computes the health score, runs check_and_create_alerts, "
        "and publishes health_level_changed / agent_version_changed events when values change."))
    E.append(h2("30.7 Scan submission and history"))
    E.append(code_block(
        'POST /api/scan\n'
        '{\n'
        '  "client_key": "Ab12cD34",\n'
        '  "scan_type": "scheduled",\n'
        '  "scan_data": { "hostname": "DESKTOP-AB12CD", "platform": "Windows", "cpu": "...", "ram": "..." }\n'
        '}\n'
        '201 Created  ->  { "status": "ok" }\n'
        '\n'
        'GET /api/scan/history?limit=50&offset=0\n'
        '200  ->  { "history": [ { "client_key": "Ab12cD34", "scan_type": "scheduled",\n'
        '                          "created_at": "2026-08-14T09:00:00Z", "changes": null } ],\n'
        '            "total": 123, "limit": 50, "offset": 0 }'))
    E.append(para(
        "Scan payloads are diffed against the previous scan with compute_scan_diff (admin/"
        "scanner_api/diff_utils.py) so the dashboard can highlight added/removed/changed hardware "
        "and software on the client detail page."))
    E.append(h2("30.8 Scheduled scan management"))
    E.append(code_block(
        'GET /api/monitoring/schedules?limit=50\n'
        '200  ->  { "schedules": [ { "id": "<uuid>", "name": "Daily full scan", "schedule_type": "daily",\n'
        '                            "time_of_day": "02:00:00", "scan_type": "full", "target_all": true,\n'
        '                            "enabled": true, "last_run": null, "next_run": "2026-08-15T02:00:00Z",\n'
        '                            "run_count": 0 } ], "total": 1 }\n'
        '\n'
        'POST /api/monitoring/schedules\n'
        '{\n'
        '  "name": "Nightly full scan",\n'
        '  "schedule_type": "daily",\n'
        '  "time_of_day": "02:00:00",\n'
        '  "scan_type": "full",\n'
        '  "target_all": true,\n'
        '  "enabled": true\n'
        '}\n'
        '201  ->  { "id": "<uuid>", "name": "Nightly full scan", ... }'))
    E.append(para(
        "Schedules are mirrored into the APScheduler jobs at runtime (admin/monitoring/scheduler.py). "
        "When a job fires, online agents receive a WS command scan_now; offline agents get a PendingScan "
        "row that they pick up over HTTP from /api/monitoring/agent/pending-scans (header "
        "X-Registration-Key or query param key) and acknowledge with POST + status executed."))
    E.append(h2("30.9 Maintenance record creation"))
    E.append(code_block(
        'POST /api/maintenance/maintenance\n'
        '{\n'
        '  "asset": "<uuid>",\n'
        '  "maintenance_type": "Preventive",\n'
        '  "priority": "High",\n'
        '  "scheduled_date": "2026-09-01",\n'
        '  "estimated_cost": "250.00",\n'
        '  "vendor_name": "Acme IT Services",\n'
        '  "description": "Quarterly cleaning and thermal repaste"\n'
        '}\n'
        '201 Created  ->  { "id": "<uuid>", "maintenance_id": "MNT000001", "status": "Draft",\n'
        '                   "approval_status": "Pending", "asset_name": "Laptop-01", ... }'))
    E.append(para(
        "Maintenance ids are auto-generated as MNT%06d in save(). Creating or updating a record "
        "writes MaintenanceHistory and runs maintenance.alerts.check_and_generate_alerts to detect "
        "due/overdue records."))
    E.append(h2("30.10 Intelligence alerts"))
    E.append(code_block(
        'GET /api/intelligence/alerts?severity=warning&status=open&page_size=50&page=1\n'
        '200  ->  { "alerts": [ { "id": "<uuid>", "title": "Disk usage above 90%", "module": "monitoring",\n'
        '                          "severity": "warning", "category": "monitoring", "status": "open",\n'
        '                          "escalation_level": 0, "age_hours": 3 } ], "total": 7, "page": 1 }\n'
        '\n'
        'POST /api/intelligence/alerts/<uuid>/action\n'
        '{\n'
        '  "action": "ack"\n'
        '}\n'
        '200  ->  { "status": "ok", "alert": { "...": "..." } }\n'
        'Actions: ack | resolve | escalate | dismiss'))
    E.append(para(
        "Alert creation deduplicates by SHA-256 dedup_hash with a suppression window (default 60 "
        "minutes), and escalation raises escalation_level over time (admin/intelligence/alerts.py). "
        "Resolving or dismissing an alert stamps resolved_time automatically."))
    E.append(h2("30.11 Report generation"))
    E.append(code_block(
        'POST /api/intelligence/reports/generate\n'
        '{\n'
        '  "report_type": "fleet_summary",\n'
        '  "format": "pdf",\n'
        '  "filters": { "status": "online", "platform": "Windows" }\n'
        '}\n'
        '200  ->  { "id": "<uuid>", "name": "...", "status": "completed", "file_size": 182340,\n'
        '           "generated_at": "2026-08-14T09:00:00Z" }'))
    E.append(para(
        "Fleet/device/alert PDFs are also downloadable directly from the monitoring module "
        "(/api/monitoring/reports/fleet/pdf, /reports/device/<uuid>/pdf, /reports/alerts/pdf) as "
        "application/pdf attachments built by admin/monitoring/reports.py."))


# ─────────────────────────────────────────────────────────────────────────────
# 31. Deep-Dive: WebSocket Protocol and Message Catalog
# ─────────────────────────────────────────────────────────────────────────────
def s31(E):
    E.append(h1("31. Deep-Dive: WebSocket Protocol and Message Catalog"))
    E.append(para(
        "Two Django-Channels sockets are exposed (admin/monitoring/routing.py). All frames are "
        "JSON text messages carrying a \"type\" key. The agent socket is authenticated with a "
        "secret-key lookup plus a timestamp freshness check; the dashboard socket relies on the "
        "session cookie and admits unauthenticated browsers in read-only mode."))
    E.append(kv_table([
        ("Agent socket", "ws/agent/&lt;agent_id&gt;/ - AgentConsumer. Used by the installed client agent."),
        ("Dashboard socket", "ws/dashboard/ - DashboardConsumer. Used by the browser dashboard."),
    ]))
    E.append(h2("31.1 Connection and auth handshake"))
    E.append(code_block(
        '1. Client opens ws(s)://HOST/ws/agent/<agent_id>/\n'
        '2. Server accepts and immediately sends:\n'
        '   { "type": "auth_required", "message": "...", "agent_id": "<agent_id>" }\n'
        '3. Client replies (client/communicator.py WebSocketClient._authenticate):\n'
        '   { "type": "auth", "agent_id": "<agent_id>",\n'
        '     "secret": "<agent_secret_key>", "timestamp": "1723600000.123" }\n'
        '4. Server validates agent_id match, non-empty secret, timestamp within 300 s,\n'
        '   then AgentSecret lookup (agent_id + secret_key + is_active=True).\n'
        '   Success ->  { "type": "auth_success", "message": "...",\n'
        '                "server_time": "...", "pending_commands": [] }\n'
        '   Failure ->  { "type": "auth_failed", "message": "Invalid credentials" }  + close 4003\n'
        '   Missing agent_id in path            -> close 4001'))
    E.append(para(
        "On auth success the server joins channel group agent_&lt;id&gt;, marks the device online "
        "(Client.status, DeviceMonitoringInfo.monitoring_status), broadcasts agent_status=online to "
        "the dashboard, and delivers any pending commands. If the WebSocket upgrade is rejected with "
        "a plain HTTP status (serverless/Vercel), the agent sets ws_unsupported and permanently falls "
        "back to HTTP polling for that process."))
    E.append(h2("31.2 Server-to-agent messages"))
    E.append(endpoint_table([
        ("auth_required", "ws accept", "Server demands authentication (first message after connect)."),
        ("auth_success", "valid auth", "Auth accepted; carries pending_commands that the client runs."),
        ("auth_failed", "bad auth", "Auth rejected; server closes with code 4003."),
        ("command", "scan job / admin", "Remote command: { command_type, command_id, payload }."),
        ("ping", "keepalive", "{ server_time }; client answers pong. Dormant - no active sender."),
        ("heartbeat_ack", "after heartbeat", "{ health_score, health_level, pending_commands, server_time }."),
        ("scan_ack", "after scan_result", "{ status: ok|error, message }."),
        ("error", "bad frame", "Invalid JSON, pre-auth message, or unknown type."),
    ]))
    E.append(code_block(
        'scan_now command sent by the scheduler for online agents:\n'
        '{ "type": "command", "command_type": "scan_now",\n'
        '  "command_id": "scan_Ab12cD34_1723600000",\n'
        '  "payload": { "scan_type": "full", "schedule_id": "<schedule-uuid>" } }\n'
        '\n'
        'Client reaction (client/main.py handle_ws_command):\n'
        '1. Runs collect_all() locally.\n'
        '2. Submits the scan via HTTP POST /api/scan.\n'
        '3. Replies { "type": "scan_result", "scan_type": "on_demand",\n'
        '            "scan_data": { "hostname": "...", "platform": "..." } }\n'
        '\n'
        'config_update: merges payload.interval_seconds / payload.enabled into the local\n'
        'scan config (designed; no active server sender today).\n'
        'ping command: client replies { "type": "pong" }.'))
    E.append(h2("31.3 Agent-to-server messages"))
    E.append(endpoint_table([
        ("auth", "handshake", "{ agent_id, secret, timestamp }. signature is read but not verified."),
        ("event", "event dispatcher", "{ event_type, severity, event_data }. Batched every 5 s / 50 max."),
        ("scan_result", "after scan_now", "{ scan_type, scan_data } stored as a ScanResult row."),
        ("pong", "reply to ping", "Keeps the server-side connection alive."),
        ("heartbeat", "agent heartbeat", "Full metrics heartbeat over WS (implemented, not used by agent)."),
        ("status_update", "status change", "{ status } updates DeviceMonitoringInfo.monitoring_status."),
    ]))
    E.append(code_block(
        'Event message as sent by client/events/dispatcher.py:\n'
        '{ "type": "event", "event_type": "usb_device_connected",\n'
        '  "severity": "warning",\n'
        '  "event_data": { "title": "USB device connected",\n'
        '                  "message": "SanDisk 3.2Gen1 attached",\n'
        '                  "device_id": "USB\\\\VID_0781&PID_5591\\\\...",\n'
        '                  "device_name": "SanDisk 3.2Gen1", "type": "storage",\n'
        '                  "serial": "AA0123456789", "vendor": "SanDisk" } }\n'
        '\n'
        'Server _store_event: writes DeviceHistory (category security_event for critical,\n'
        'status_change otherwise), and for warning/critical creates a DeviceAlert and\n'
        'broadcasts new_alert to the dashboard.'))
    E.append(h2("31.4 Dashboard broadcast messages"))
    E.append(endpoint_table([
        ("agent_status", "auth/disconnect", "{ agent_id, status: online|offline, timestamp }."),
        ("device_heartbeat", "WS heartbeat", "{ agent_id, health_score, health_level, cpu, ram, disk, timestamp }."),
        ("scan_completed", "WS scan_result", "{ agent_id, scan_type, timestamp }."),
        ("device_event", "WS event", "{ agent_id, event_type, severity, timestamp }."),
        ("device_status_update", "WS status_update", "{ agent_id, status, timestamp }."),
        ("new_alert", "warning/critical event", "{ agent_id, event_type, severity, details, timestamp }."),
        ("<event_type>", "event bus", "Every EventBus publication is forwarded to the dashboard group."),
    ]))
    E.append(para(
        "The event bus forwards every published event type to the dashboard with keys "
        "event_type, client_id, client_key, hostname, severity, title, description, data, timestamp, "
        "source (Event.to_dict in admin/monitoring/event_bus.py). Real published types include "
        "device_registered, agent_version_changed, health_level_changed, hw_component_added/removed/"
        "modified, sw_installed/sw_removed/sw_version_changed/sw_unauthorized/sw_antivirus_removed, "
        "device_status_changed, device_approved, device_blocked, and schedule_executed."))
    E.append(h2("31.5 Offline handling and recovery"))
    E.extend(bullets([
        "WS disconnect: AgentConsumer.disconnect marks monitoring_status=offline (only if it was online) and broadcasts agent_status=offline.",
        "Independent detector: the offline_detector management command flips stale devices to offline after stale_threshold_seconds (default 120 s) and creates a device_offline DeviceAlert.",
        "Queued events: while disconnected, agent events buffer in memory and are persisted to %APPDATA%/SystemScannerPro/offline_events/batch_*.json, replayed on the next dispatcher start.",
        "Pending scans: the scheduler creates PendingScan rows for offline agents; agents fetch and acknowledge them over HTTP.",
        "Reconnect: the agent reconnects with exponential backoff 2 s to 60 s, re-authenticating each time.",
    ]))
    E.append(note(
        "Accuracy notes: the agent currently sends heartbeats over HTTP, not WS, so heartbeat_ack/"
        "device_heartbeat are implemented but rarely fire. WS auth is a plain secret-key lookup plus "
        "timestamp check - the signature field is accepted but not verified. The pending_commands "
        "delivery path reads DeviceMonitoringInfo.notes, which nothing writes today, so it is dormant. "
        "The dashboard frontend listens for alert_created but the server only emits new_alert."))


# ─────────────────────────────────────────────────────────────────────────────
# 32. Deep-Dive: Database Schema Reference
# ─────────────────────────────────────────────────────────────────────────────
def s32(E):
    E.append(h1("32. Deep-Dive: Database Schema Reference"))
    E.append(para(
        "Every model is listed below with its full field set as defined in the models.py files. "
        "Unless noted, id is UUIDField(primary_key=True, default=uuid.uuid4, editable=False). All "
        "apps use BigAutoField as default_auto_field. The scanner_api app is the hub: the monitoring, "
        "intelligence, and maintenance apps all reference scanner_api tables (Client, Asset, Employee, "
        "Department, Location, Company) rather than duplicating them."))

    E.append(h2("32.1 scanner_api: core and organization"))
    E.append(h3("32.1.1 Company (companies)"))
    E.append(field_table([
        ("name", "CharField(255)", "Unique company name."),
        ("slug", "SlugField(128)", "Unique, blank; auto-slugified in save()."),
        ("created_at", "DateTimeField", "Auto-set on create."),
    ]))
    E.append(h3("32.1.2 ClientGroup (client_groups)"))
    E.append(field_table([
        ("name", "CharField(128)", "Group name."),
        ("description", "TextField", "Blank by default."),
        ("company", "FK Company", "CASCADE, null/blank, related_name=client_groups."),
        ("created_at", "DateTimeField", "Auto-set."),
    ]))
    E.append(h3("32.1.3 Client (clients) - central agent record"))
    E.append(field_table([
        ("registration_key", "CharField(64)", "Unique, indexed; agent identity."),
        ("hostname / platform", "CharField", "Machine name and OS family."),
        ("status", "CharField(32)", "pending / online / offline / etc.; default pending."),
        ("last_seen", "DateTimeField", "Null/blank."),
        ("approved", "BooleanField", "Default False."),
        ("owner", "FK auth.User", "SET_NULL, related_name=owned_clients."),
        ("company", "FK Company", "CASCADE, related_name=clients."),
        ("group", "FK ClientGroup", "SET_NULL, related_name=clients."),
        ("tags", "CharField(512)", "Comma tags, blank."),
        ("purchase_cost", "DecimalField(12,2)", "Null/blank."),
        ("purchase_date", "DateField", "Null/blank."),
        ("vendor_name / vendor_contact", "CharField", "Blank."),
        ("warranty_expiry", "DateField", "Null/blank."),
        ("notes", "TextField", "Blank."),
        ("scan_interval", "IntegerField", "Default 3600 s."),
        ("scan_enabled", "BooleanField", "Default True."),
        ("scan_requested", "BooleanField", "Default False."),
        ("last_ip", "CharField(64)", "Blank."),
        ("device_fingerprint", "CharField(64)", "Indexed, blank."),
        ("deleted", "BooleanField", "Soft delete flag."),
        ("client_version / os_version", "CharField", "Agent and OS version strings."),
        ("cpu_model / ram_info", "CharField", "Inventory summary strings."),
        ("created_at", "DateTimeField", "Auto-set."),
    ]))
    E.append(h3("32.1.4 ScanResult (scan_results)"))
    E.append(field_table([
        ("client", "FK Client", "CASCADE, null/blank, related_name=scans."),
        ("scan_type", "CharField(32)", "scheduled / full / quick / ...; default scheduled."),
        ("scan_data", "JSONField", "Full inventory JSON, default {}."),
        ("created_at", "DateTimeField", "Indexed with client (desc)."),
    ]))
    E.append(h3("32.1.5 AddonDevice (addon_devices)"))
    E.append(field_table([
        ("client", "FK Client", "CASCADE, related_name=addons."),
        ("name / description / serial_number", "Char/Text", "Device metadata."),
        ("purchase_cost", "DecimalField(12,2)", "Null/blank."),
        ("category", "CharField(128)", "Blank."),
        ("added_at", "DateTimeField", "Auto-set."),
    ]))
    E.append(h3("32.1.6 ActivityLog (activity_logs)"))
    E.append(field_table([
        ("action", "CharField(32)", "register/approve/scan/scan_request/delete/update/login/setting_change."),
        ("client", "FK Client", "SET_NULL, related_name=activity_logs."),
        ("company", "FK Company", "CASCADE, related_name=activity_logs."),
        ("details", "TextField", "Blank."),
        ("created_at", "DateTimeField", "Indexed desc."),
    ]))
    E.append(h3("32.1.7 Setting (settings)"))
    E.append(field_table([
        ("key", "CharField(255)", "Primary key (e.g. stale_threshold_seconds)."),
        ("value", "TextField", "Blank."),
        ("company", "FK Company", "CASCADE, null/blank, related_name=settings."),
    ]))
    E.append(h3("32.1.8 AdministratorProfile (administrator_profiles)"))
    E.append(field_table([
        ("user", "OneToOne auth.User", "CASCADE, related_name=admin_profile."),
        ("company", "FK Company", "CASCADE, related_name=admins."),
        ("phone_number / profile_picture_url", "Char/URL", "Optional profile data."),
        ("timezone / currency / date_format", "CharField", "Defaults UTC / USD / YYYY-MM-DD."),
        ("dashboard_default", "CharField(50)", "Default dashboard."),
        ("notification_email / notification_in_app", "BooleanField", "Default True."),
        ("notification_daily_summary", "BooleanField", "Default False."),
        ("password_changed_at", "DateTimeField", "Null/blank."),
        ("mfa_enabled / mfa_secret", "Bool / Char", "MFA support fields."),
        ("created_at / updated_at", "DateTimeField", "Auto timestamps."),
        ("constraint", "unique_together", "(company, user)."),
    ]))
    E.append(h3("32.1.9 AuditLog (audit_logs)"))
    E.append(field_table([
        ("user", "FK auth.User", "SET_NULL, no related_name."),
        ("company", "FK Company", "CASCADE, related_name=audit_logs."),
        ("event_type", "CharField(32)", "login_success/failure, logout, password_changed, profile_updated, settings_updated, account_locked/unlocked, session_created/expired, etc."),
        ("ip_address / user_agent", "GenericIP / Text", "Request context."),
        ("device_info", "JSONField", "Blank dict."),
        ("details", "TextField", "Blank."),
        ("success", "BooleanField", "Default True."),
        ("created_at", "DateTimeField", "Indexed."),
    ]))
    E.append(h3("32.1.10 LoginHistory / LoginAttempt / DeviceFingerprint"))
    E.append(field_table([
        ("LoginHistory", "login_time, logout_time, session_duration, ip_address, user_agent, browser, os, device_type, location, is_current", "Per-user login timeline (user FK SET_NULL, company FK)."),
        ("LoginAttempt", "identifier, ip_address, success, created_at", "Brute-force tracking, identifier indexed."),
        ("DeviceFingerprint", "user, fingerprint, device_name, browser, os, last_seen, trusted", "Trusted-device tokens (auto BigAutoField id)."),
    ]))

    E.append(h3("32.1.11 Location (locations)"))
    E.append(field_table([
        ("company", "FK Company", "CASCADE, related_name=locations."),
        ("office_name / building_name / floor / room_number", "CharField", "Physical address details."),
        ("address / city / state / country / postal_code", "Char/Text", "Country default USA."),
        ("contact_number / office_manager / timezone", "CharField", "Timezone default UTC."),
        ("status", "CharField(20)", "Active / Archived / Closed; default Active."),
        ("notes", "TextField", "Blank."),
        ("deleted", "BooleanField", "Soft delete."),
        ("created_at / updated_at", "DateTimeField", "Auto timestamps."),
        ("constraint", "unique_together", "(office_name, city)."),
    ]))
    E.append(h3("32.1.12 Department (departments)"))
    E.append(field_table([
        ("company", "FK Company", "CASCADE, related_name=departments."),
        ("name / code", "CharField", "Name + short code."),
        ("description / department_head / email / phone_number", "Char/Text", "Optional contact info."),
        ("location", "FK Location", "SET_NULL, related_name=departments."),
        ("budget", "DecimalField(14,2)", "Null/blank."),
        ("status", "CharField(20)", "Active / Disabled / Archived; default Active."),
        ("deleted", "BooleanField", "Soft delete."),
        ("created_at / updated_at", "DateTimeField", "Auto timestamps."),
    ]))
    E.append(h3("32.1.13 Employee (employees)"))
    E.append(field_table([
        ("company", "FK Company", "CASCADE, related_name=employees."),
        ("employee_code", "CharField(50)", "Unique per company."),
        ("full_name / email", "Char / Email", "Email unique per company."),
        ("phone_number", "CharField(20)", "Blank."),
        ("department", "FK Department", "PROTECT, related_name=employees."),
        ("designation / manager_name", "CharField", "Job info."),
        ("reports_to", "FK self", "SET_NULL, related_name=direct_reports."),
        ("location", "FK Location", "PROTECT, related_name=employees."),
        ("joining_date", "DateField", "Null/blank."),
        ("status", "CharField(20)", "Active/Inactive/Resigned/On Leave/Terminated/Retired; default Active."),
        ("profile_image", "TextField", "Base64, blank."),
        ("notes / deleted", "Text / Bool", "Notes and soft delete."),
        ("created_at / updated_at", "DateTimeField", "Auto timestamps."),
    ]))
    E.append(h3("32.1.14 EmployeeAssetAssignment (employee_asset_assignments)"))
    E.append(field_table([
        ("employee", "FK Employee", "PROTECT, related_name=asset_assignments."),
        ("client", "FK Client", "SET_NULL, related_name=employee_assignments."),
        ("assigned_at / returned_at", "DateTimeField", "Auto-set / null."),
        ("is_active", "BooleanField", "Default True."),
        ("assigned_by / notes", "Char / Text", "Actor and notes."),
    ]))
    E.append(h3("32.1.15 OrgAuditLog (org_audit_logs)"))
    E.append(field_table([
        ("company", "FK Company", "CASCADE, related_name=org_audit_logs."),
        ("entity_type", "CharField(20)", "employee / department / location."),
        ("entity_id / entity_name", "CharField", "Referenced entity."),
        ("action", "CharField(20)", "created/updated/deactivated/archived/disabled."),
        ("previous_value / new_value", "JSONField", "Change snapshots."),
        ("performed_by / ip_address / user_agent", "Char / IP / Text", "Audit context."),
        ("created_at", "DateTimeField", "Indexed."),
    ]))

    E.append(h3("32.1.16 Asset categories and vendors"))
    E.append(field_table([
        ("AssetCategory", "name, code, description, parent (self FK), icon, is_active", "Hierarchical asset taxonomy; parent SET_NULL related_name=children."),
        ("AssetVendor", "name, contact_person, email, phone, address, website, notes", "Vendor directory; company FK."),
    ]))

    E.append(h3("32.1.17 Asset (assets) - largest table"))
    E.append(field_table([
        ("company", "FK Company", "CASCADE, related_name=assets."),
        ("asset_id", "CharField(32)", "Unique; auto AST%06d in save()."),
        ("asset_name / asset_tag", "CharField", "asset_tag unique+indexed."),
        ("serial_number", "CharField(255)", "Unique, indexed."),
        ("qr_code / barcode", "UUIDField", "Both unique and indexed, default uuid4."),
        ("category", "FK AssetCategory", "SET_NULL, related_name=assets."),
        ("manufacturer / model_name / description / specifications", "Char/Text/JSON", "specifications is JSON dict."),
        ("image", "TextField", "Base64, blank."),
        ("purchase_date / purchase_cost / current_value / residual_value", "Date/Decimal", "Financial values."),
        ("depreciation_pct", "DecimalField(5,2)", "Default 0."),
        ("invoice_number / purchase_order_number", "CharField", "Procurement refs."),
        ("vendor", "FK AssetVendor", "SET_NULL, related_name=assets."),
        ("department / location", "FK", "SET_NULL, related_name=assets."),
        ("warranty_start / warranty_end / warranty_provider / amc_details", "Date/Char/Text", "Warranty info."),
        ("asset_status", "CharField(24)", "13 states Draft..Disposed; indexed, default Draft."),
        ("parent", "FK self", "SET_NULL, related_name=children (asset hierarchy)."),
        ("client", "FK Client", "SET_NULL, related_name=linked_assets."),
        ("is_insured / insurance_value / insurance_expiry", "Bool/Decimal/Date", "Insurance."),
        ("created_by / last_audit_date / tags / notes", "Char/Date/Text", "Meta info."),
        ("is_active / deleted", "BooleanField", "State flags."),
        ("assigned_to", "FK Employee", "SET_NULL, related_name=assigned_assets."),
        ("created_at / updated_at", "DateTimeField", "Auto timestamps."),
    ]))
    E.append(h3("32.1.18 AssetAssignment / AssetTransfer / AssetHistory / AssetDocument"))
    E.append(field_table([
        ("AssetAssignment", "asset (PROTECT), employee (PROTECT), department, location, assigned_at, expected_return_date, returned_at, is_active, assigned_by, notes", "Table asset_assignments_v2."),
        ("AssetTransfer", "asset (PROTECT), from/to employee/department/location, transfer_date, reason, transferred_by, notes", "Asset movement trail."),
        ("AssetHistory", "asset (PROTECT), action, timestamp, previous_value, new_value, performed_by, ip_address, user_agent, notes", "Immutable: save() raises when pk set; update() raises."),
        ("AssetDocument", "asset (PROTECT), name, file_data (base64), file_type, file_size, uploaded_by", "Attached documents."),
    ]))
    E.append(h3("32.1.19 ApiKey (api_keys)"))
    E.append(field_table([
        ("key", "CharField(64)", "Unique; plaintext shown once at creation."),
        ("key_hash", "CharField(128)", "SHA-256 stored hash, indexed."),
        ("name / user", "Char / FK User", "Label and owner (CASCADE, related_name=api_keys)."),
        ("is_active", "BooleanField", "Default True."),
        ("rate_limit", "IntegerField", "Requests/minute, default 60."),
        ("allowed_ips / expires_at / last_used", "Text / DateTime", "Optional restrictions."),
        ("created_at", "DateTimeField", "Auto-set."),
    ]))

    E.append(h2("32.2 monitoring: device intelligence"))
    E.append(h3("32.2.1 DeviceMonitoringInfo (monitoring_device_info)"))
    E.append(field_table([
        ("client", "OneToOne Client", "CASCADE, related_name=monitoring_info, indexed."),
        ("monitoring_status", "CharField(20)", "pending/approved/rejected/blocked/online/offline/inactive/maintenance/unknown; default pending."),
        ("health_level", "CharField(20)", "healthy/warning/critical/unknown; default unknown."),
        ("health_score", "IntegerField", "0-100."),
        ("ip_address / mac_address / public_ip", "IP / Char", "Network identity."),
        ("os_name / os_build / os_architecture", "CharField", "OS details."),
        ("agent_version / last_heartbeat / heartbeat_count", "Char/DateTime/Int", "Agent status."),
        ("device_type", "CharField(32)", "laptop/desktop/server/workstation/vm/cloud; default desktop."),
        ("department / location_name / current_user", "CharField", "Placement info."),
        ("tags / notes", "Char / Text", "Free-form."),
        ("created_at / updated_at", "DateTimeField", "Auto timestamps."),
    ]))
    E.append(h3("32.2.2 HardwareInventory / SoftwareInventory"))
    E.append(field_table([
        ("HardwareInventory", "client FK, component_type (cpu/ram/storage/gpu/motherboard/network), component_data JSON, fingerprint, scan_id, created_at", "Per-component hardware snapshots."),
        ("SoftwareInventory", "client FK, name (512, indexed), version, publisher, category (application/driver/update/browser/office/antivirus/service/other), raw_data JSON, scan_id, is_present, created_at", "Installed software entries with presence flag."),
    ]))
    E.append(h3("32.2.3 DeviceHeartbeat (monitoring_device_heartbeat)"))
    E.append(field_table([
        ("client", "FK Client", "CASCADE, related_name=monitoring_heartbeats."),
        ("cpu_usage_pct / ram_usage_pct / disk_usage_pct / disk_free_gb / disk_total_gb / load_average", "FloatField", "Metric readings, default 0."),
        ("network_connected", "BooleanField", "Default True."),
        ("uptime_seconds / scan_running / pending_commands", "Int/Bool/Int", "Status extras."),
        ("agent_version / ip_address", "Char / IP", "Context."),
        ("response_time_ms / created_at", "Int / DateTime", "Latency and timestamp."),
    ]))
    E.append(h3("32.2.4 DeviceMetrics (monitoring_device_metrics)"))
    E.append(field_table([
        ("client", "FK Client", "CASCADE, related_name=device_metrics."),
        ("period", "CharField(8)", "hourly / daily; default hourly."),
        ("avg/max/min_cpu_pct, avg/max/min_ram_pct, avg/max/min_disk_pct", "FloatField", "9 aggregates."),
        ("health_score / health_level", "Int / Char", "Rolled-up health."),
        ("uptime_pct / total_heartbeats / missed_heartbeats", "Float/Int", "Availability."),
        ("period_start / period_end", "DateTimeField", "Bucket window."),
    ]))
    E.append(h3("32.2.5 DeviceHistory (monitoring_device_history) - immutable"))
    E.append(field_table([
        ("client", "FK Client", "PROTECT, related_name=device_history."),
        ("category", "CharField(20)", "registration/status_change/hardware_change/software_change/health_change/security_event/alert_generated/admin_action/agent_update/remote_command."),
        ("event_type / description", "Char / Text", "Event name and text."),
        ("previous_value / new_value", "JSONField", "Change diff."),
        ("severity", "CharField(16)", "info/warning/critical; default info."),
        ("source", "CharField(64)", "system/agent/etc."),
        ("timestamp", "DateTimeField", "Auto-set; save() raises if pk set."),
    ]))
    E.append(h3("32.2.6 DeviceAlert (monitoring_device_alerts)"))
    E.append(field_table([
        ("client", "FK Client", "CASCADE, related_name=monitoring_alerts."),
        ("alert_type", "CharField(64)", "Indexed (e.g. device_offline)."),
        ("severity", "CharField(16)", "info/warning/critical; default warning."),
        ("status", "CharField(16)", "active/acknowledged/resolved/dismissed; default active."),
        ("title / message / details", "Char / Text / JSON", "Alert content."),
        ("acknowledged_by / acknowledged_at / resolved_at", "Char / DateTime", "Workflow stamps."),
    ]))
    E.append(h3("32.2.7 AgentVersion / AgentSecret"))
    E.append(field_table([
        ("AgentVersion", "version (unique), release_notes, download_url, is_mandatory, min_python_version (default 3.7), file_hash, is_active", "Version registry used by agent/version-check."),
        ("AgentSecret", "client FK, agent_id (unique), secret_key, device_fingerprint, is_active, last_used", "HMAC secrets issued at agent registration."),
    ]))
    E.append(h3("32.2.8 ScheduledScan / PendingScan / ScanScheduleLog"))
    E.append(field_table([
        ("ScheduledScan", "name, description, schedule_type (interval/daily/weekly/monthly/once), interval_seconds, cron_expression, time_of_day, day_of_week, day_of_month, target_all, target_clients (ManyToMany - the only M2M in the schema), target_platforms, scan_type, enabled, last_run, next_run, run_count", "Scan schedules mirrored into APScheduler."),
        ("PendingScan", "client FK, scheduled_scan FK, scan_type, priority, status (pending/sent/executed/failed/expired), sent_at, executed_at, error_message", "Offline-scan queue; immutable (save raises when pk set)."),
        ("ScanScheduleLog", "scheduled_scan FK, client FK, triggered_at, completed_at, status, changes_detected, alerts_generated, details", "Execution log per schedule+client."),
    ]))

    E.append(h2("32.3 intelligence: alerts, insights, audit"))
    E.append(h3("32.3.1 Alert (intelligence_alerts)"))
    E.append(field_table([
        ("title / description", "Char / Text", "Alert headline and detail."),
        ("module", "CharField(20)", "asset / monitoring / maintenance / license."),
        ("source_object_id / source_object_type", "CharField", "Generic source reference."),
        ("severity", "CharField(16)", "information/warning/critical/emergency; default warning."),
        ("category", "CharField(20)", "asset/monitoring/maintenance/license/security/compliance/system."),
        ("status", "CharField(16)", "open/acknowledged/resolved/dismissed; default open."),
        ("assigned_user", "CharField(128)", "Blank."),
        ("generated_time / resolved_time", "DateTimeField", "Auto / null until resolved."),
        ("escalation_level", "IntegerField", "0 by default."),
        ("dedup_hash", "CharField(64)", "SHA-256 dedupe key, indexed."),
        ("notification_sent", "BooleanField", "Default False."),
        ("resolution_notes", "TextField", "Blank."),
    ]))
    E.append(h3("32.3.2 AlertHistory / AlertRule"))
    E.append(field_table([
        ("AlertHistory", "alert FK, action, previous_status/new_status, previous_severity/new_severity, performed_by, notes, timestamp", "Immutable state-transition log per alert."),
        ("AlertRule", "name, description, module, category, severity, condition_type, condition_field, condition_value, suppress_duplicates, suppress_window_minutes (60), auto_resolve_minutes, is_active, created_by", "Rule-engine definitions for automated alerting."),
    ]))
    E.append(h3("32.3.3 Notification / NotificationPreference"))
    E.append(field_table([
        ("Notification", "user FK, title, message, severity, status (unread/read/archived), module, source_alert FK, source_url, created_time, read_time", "Per-user in-app notifications."),
        ("NotificationPreference", "user OneToOne, email_enabled, in_app_enabled, severity_* (4 flags), module_* (7 flags), frequency (instant/daily/weekly/never), quiet_hours_start/end", "Delivery preferences."),
    ]))
    E.append(h3("32.3.4 Report / ScheduledReport"))
    E.append(field_table([
        ("Report", "name, report_type (25 choices), format (pdf/excel/csv), filters JSON, generated_by, file_data (base64), file_size, row_count, status (pending/generating/completed/failed), error_message, generated_at, completed_at", "Generated report artifacts."),
        ("ScheduledReport", "name, report_type, format, frequency (daily/weekly/monthly/quarterly), filters, recipients, next_run, last_run, is_active, retention_policy (1_year/3_years/permanent)", "Recurring report config (CRUD today; no background executor)."),
    ]))
    E.append(h3("32.3.5 AuditLogEntry / ComplianceLog / DashboardAnalytics / RetentionPolicy"))
    E.append(field_table([
        ("AuditLogEntry", "user_id (plain int, no FK), username, timestamp, ip_address, browser_info, device_info, module (9 choices), action (21 choices), object_type, object_id, object_repr, old_value, new_value, severity, description", "Immutable security audit trail."),
        ("ComplianceLog", "framework (iso_27001/itil/soc2/internal/gdpr), control_id, control_name, status, severity, description, finding_details, asset FK, audited_by, audited_at, next_audit_date", "Compliance findings."),
        ("DashboardAnalytics", "9 counters (total_alerts, open_alerts, critical_alerts, notifications_today, reports_generated, security_violations, audit_events_today, compliance_violations, pending_notifications), snapshot_time", "Periodic KPI snapshots."),
        ("RetentionPolicy", "scope (unique: alerts/notifications/reports/audit_logs/compliance_logs), retention_period, is_active", "Per-scope retention settings."),
    ]))

    E.append(h2("32.4 maintenance: asset care, licenses, compliance"))
    E.append(h3("32.4.1 MaintenanceRecord (maintenance_records)"))
    E.append(field_table([
        ("maintenance_id", "CharField(32)", "Unique; auto MNT%06d."),
        ("asset", "FK Asset", "PROTECT, related_name=maintenance_records."),
        ("asset_category_name", "CharField(128)", "Copied from asset.category in save()."),
        ("maintenance_type", "CharField(20)", "Preventive/Corrective/Emergency/Inspection/Upgrade/Repair/Replacement/Calibration."),
        ("status", "CharField(24)", "Draft/Pending Approval/Approved/Scheduled/In Progress/Waiting Parts/Completed/Cancelled/Overdue."),
        ("approval_status", "CharField(16)", "Pending/Approved/Rejected."),
        ("vendor_name / vendor_contact / technician", "CharField", "Service provider."),
        ("description / notes", "TextField", "Details."),
        ("scheduled_date / start_date / completion_date / due_date", "DateField", "Timeline."),
        ("estimated_cost / actual_cost / downtime_hours", "DecimalField", "Costs and downtime."),
        ("priority", "CharField(16)", "Low/Medium/High/Critical; default Medium."),
        ("recurring / recurrence_interval_days / next_occurrence", "Bool/Int/Date", "Recurring maintenance."),
        ("created_by / approved_by", "CharField", "Actors."),
        ("department", "FK Department", "SET_NULL, related_name=maintenance_records."),
        ("deleted", "BooleanField", "Soft delete."),
    ]))
    E.append(h3("32.4.2 MaintenanceHistory / MaintenanceDocument"))
    E.append(field_table([
        ("MaintenanceHistory", "maintenance FK, action, description, previous_value, new_value, performed_by, ip_address, timestamp", "Immutable workflow log."),
        ("MaintenanceDocument", "maintenance FK, name, file_data (base64), file_type, file_size, uploaded_by", "Attached documents."),
    ]))
    E.append(h3("32.4.3 WarrantyRecord / DowntimeRecord"))
    E.append(field_table([
        ("WarrantyRecord", "warranty_id (auto WAR%06d), asset FK (PROTECT), warranty_start (required), warranty_end (required), warranty_provider (required), contract_number, amc_details, support contacts, coverage_type (Full/Parts/Labor/Limited), status (Active/Expiring Soon/Expired/Claimed/Archived), cost", "Warranty tracking."),
        ("DowntimeRecord", "asset FK (PROTECT), maintenance FK (SET_NULL), start_time, end_time, duration_hours (auto), reason (Maintenance/Repair/Failure/Upgrade/Power/Network/Other), description", "Downtime events."),
    ]))
    E.append(h3("32.4.4 SoftwareLicense / LicenseAssignment / LicenseHistory"))
    E.append(field_table([
        ("SoftwareLicense", "license_id (auto LIC%06d), software_name, vendor, product_edition, version, license_key_encrypted, license_key_masked, license_type (Per User/Per Device/Subscription/OEM/Enterprise/Volume/Trial/Open Source), purchased_seats, seats_used, purchase_date, expiration_date, renewal_date, cost, status (Draft/Active/Expiring Soon/Expired/Suspended/Archived), department FK, notes, deleted", "Software entitlement tracking."),
        ("LicenseAssignment", "license FK (PROTECT), assignable_type (Asset/Employee/Department), asset/employee/department FKs, assigned_date, removal_date, assigned_by, is_active", "Seat consumption."),
        ("LicenseHistory", "license FK, action, description, previous_value, new_value, performed_by, timestamp", "Immutable license log."),
    ]))
    E.append(h3("32.4.5 ComplianceRecord / MaintenanceAlert"))
    E.append(field_table([
        ("ComplianceRecord", "category (license_expiration/seat_overuse/unauthorized_software/missing_license/compliance_violation), severity, title, description, license FK, asset FK, details JSON, status (active/acknowledged/resolved/dismissed), acknowledged_by, resolved_at", "Compliance findings."),
        ("MaintenanceAlert", "Generated by maintenance/alerts.py from due/overdue maintenance, warranty, and license expiry rules.", "Alert queue for the maintenance module."),
    ]))
    E.append(h2("32.5 Relationship map"))
    E.append(component_table([
        ("Client (hub)", "Referenced by ScanResult, AddonDevice, ActivityLog, EmployeeAssetAssignment, Asset.client, DeviceMonitoringInfo, HardwareInventory, SoftwareInventory, DeviceHeartbeat, DeviceMetrics, DeviceHistory, DeviceAlert, AgentSecret, PendingScan, ScanScheduleLog, ScheduledScan.target_clients."),
        ("Asset", "Referenced by AssetAssignment, AssetTransfer, AssetHistory, AssetDocument, MaintenanceRecord, WarrantyRecord, DowntimeRecord, LicenseAssignment, ComplianceRecord, ComplianceLog."),
        ("Employee", "Referenced by EmployeeAssetAssignment, AssetAssignment, AssetTransfer, LicenseAssignment."),
        ("Company", "Tenant root for most scanner_api, monitoring, intelligence, and maintenance tables."),
        ("auth.User", "Owns AdministratorProfile, DeviceFingerprint, AuditLog, LoginHistory, LoginAttempt, ApiKey, Notification, NotificationPreference."),
        ("Department / Location", "Referenced by Employee, Asset, MaintenanceRecord, SoftwareLicense, LicenseAssignment, AssetTransfer."),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────────────
def build():
    doc = DocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.4 * cm, bottomMargin=1.3 * cm,
        title=f"System Scanner Pro v{VERSION} \u2014 Complete System Documentation",
        author="System Scanner Pro",
        subject="Complete system documentation",
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
    E.append(para("Table of Contents", H1))
    E.append(toc())
    E.append(PageBreak())

    s01(E)
    s02(E)
    s03(E)
    s04(E)
    s05(E)
    s06(E)
    s07(E)
    s08(E)
    s09(E)
    s10(E)
    s11(E)
    s12(E)
    s13(E)
    s14(E)
    s15(E)
    s16(E)
    s17(E)
    s18(E)
    s19(E)
    s20(E)
    s21(E)
    s22(E)
    s23(E)
    s24(E)
    s25(E)
    s26(E)
    s27(E)
    s28(E)
    s29(E)
    s30(E)
    s31(E)
    s32(E)

    doc.multiBuild(E)

    pages = doc.page
    return pages


if __name__ == "__main__":
    pages = build()
    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"OK: {OUTPUT}")
    print(f"Pages: {pages}  |  Size: {size_kb:.1f} KB")
