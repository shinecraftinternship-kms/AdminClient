import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics import renderPDF


BLUE = HexColor("#1a73e8")
DARK_BLUE = HexColor("#0d47a1")
LIGHT_BLUE = HexColor("#e3f2fd")
GREEN = HexColor("#2e7d32")
LIGHT_GREEN = HexColor("#e8f5e9")
ORANGE = HexColor("#e65100")
LIGHT_ORANGE = HexColor("#fff3e0")
RED = HexColor("#c62828")
LIGHT_RED = HexColor("#ffebee")
GRAY = HexColor("#616161")
LIGHT_GRAY = HexColor("#f5f5f5")
DARK_GRAY = HexColor("#424242")
BLACK = HexColor("#212121")

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Admin_Client_Connection_Guide.pdf")


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=white,
        alignment=TA_CENTER,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        fontName="Helvetica",
        fontSize=14,
        leading=18,
        textColor=HexColor("#bbdefb"),
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=24,
        textColor=DARK_BLUE,
        spaceBefore=20,
        spaceAfter=10,
        borderPadding=(0, 0, 4, 0),
    ))
    styles.add(ParagraphStyle(
        name="SubSection",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=BLUE,
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="StepTitle",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=white,
        spaceBefore=10,
        spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=BLACK,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BulletText",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=BLACK,
        leftIndent=20,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="CommandText",
        fontName="Courier",
        fontSize=10,
        leading=14,
        textColor=DARK_GRAY,
        backColor=LIGHT_GRAY,
        borderPadding=6,
        leftIndent=10,
        rightIndent=10,
        spaceAfter=6,
        spaceBefore=4,
    ))
    styles.add(ParagraphStyle(
        name="NoteText",
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        textColor=GRAY,
        leftIndent=15,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=white,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=BLACK,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=GRAY,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SmallBold",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=15,
        textColor=BLACK,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ArchitectureLabel",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=DARK_BLUE,
        alignment=TA_CENTER,
    ))
    return styles


def cover_page(styles):
    elements = []
    elements.append(Spacer(1, 1.5 * inch))

    cover_data = [[""]]
    cover_inner = []
    cover_inner.append(Spacer(1, 0.6 * inch))
    cover_inner.append(Paragraph("System Scanner Pro v3.0", styles["CoverTitle"]))
    cover_inner.append(Spacer(1, 0.15 * inch))
    cover_inner.append(Paragraph("Admin-Client Connection Guide", styles["CoverSubtitle"]))
    cover_inner.append(Spacer(1, 0.1 * inch))
    cover_inner.append(Paragraph("Step-by-Step Setup &amp; Configuration", styles["CoverSubtitle"]))
    cover_inner.append(Spacer(1, 0.4 * inch))
    cover_inner.append(Paragraph("AI-Powered Distributed Endpoint Monitoring", styles["CoverSubtitle"]))
    cover_inner.append(Spacer(1, 0.6 * inch))

    t = Table([[cover_inner]], colWidths=[6 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("BOX", (0, 0), (-1, -1), 2, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 1.2 * inch))

    info_data = [
        [Paragraph("<b>Document Version:</b>", styles["TableCell"]),
         Paragraph("2.0", styles["TableCell"])],
        [Paragraph("<b>Application Version:</b>", styles["TableCell"]),
         Paragraph("System Scanner Pro v3.0", styles["TableCell"])],
        [Paragraph("<b>Technology Stack:</b>", styles["TableCell"]),
         Paragraph("Django 5.x + DRF + Django Channels + Python 3.10+", styles["TableCell"])],
        [Paragraph("<b>Communication:</b>", styles["TableCell"]),
         Paragraph("HTTP REST + WebSocket + Cloud Discovery (Supabase) + UDP", styles["TableCell"])],
    ]
    info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#90caf9")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(PageBreak())
    return elements


def section_divider(title, styles):
    data = [[Paragraph(title, styles["SectionHeader"])]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("LINEBELOW", (0, 0), (-1, -1), 2, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def step_box(step_num, title, content_elements, styles, color=BLUE, bg=LIGHT_BLUE):
    header_data = [[
        Paragraph(f"Step {step_num}: {title}", styles["StepTitle"]),
    ]]
    header_table = Table(header_data, colWidths=[6.3 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))

    body_data = [[content_elements]]
    body_table = Table(body_data, colWidths=[6.3 * inch])
    body_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, color),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    combined = [[header_table], [body_table]]
    outer = Table(combined, colWidths=[6.5 * inch])
    outer.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return outer


def note_box(text, styles, bg=LIGHT_ORANGE, border=ORANGE):
    data = [[Paragraph(text, styles["NoteText"])]]
    t = Table(data, colWidths=[6.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.5, border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def info_box(text, styles, bg=LIGHT_GREEN, border=GREEN):
    data = [[Paragraph(text, styles["BodyText2"])]]
    t = Table(data, colWidths=[6.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.5, border),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def build_pdf():
    styles = build_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )
    elements = []

    # --- COVER PAGE ---
    elements.extend(cover_page(styles))

    # --- TABLE OF CONTENTS ---
    elements.append(section_divider("Table of Contents", styles))
    elements.append(Spacer(1, 0.15 * inch))
    toc_items = [
        "1. Architecture Overview",
        "2. Cloud Discovery Setup (Supabase)",
        "3. Prerequisites &amp; Requirements",
        "4. Install Dependencies",
        "5. Configure Environment",
        "6. Start the Admin Server",
        "7. Start the Client Agent",
        "8. Approve the Client",
        "9. Verify Connection",
        "10. Connection Methods Reference",
        "11. Troubleshooting",
        "12. Port Reference",
    ]
    for item in toc_items:
        elements.append(Paragraph(item, styles["BodyText2"]))
    elements.append(PageBreak())

    # --- SECTION 1: ARCHITECTURE OVERVIEW ---
    elements.append(section_divider("1. Architecture Overview", styles))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(
        "System Scanner Pro uses a <b>distributed client-server architecture</b>. "
        "The admin server (Django) runs on a central machine and serves a web dashboard, "
        "REST API, and WebSocket endpoint. Client agents run on each monitored machine, "
        "connecting to the admin server via HTTP and WebSocket.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 0.1 * inch))

    arch_data = [
        [Paragraph("<b>Component</b>", styles["TableHeader"]),
         Paragraph("<b>Technology</b>", styles["TableHeader"]),
         Paragraph("<b>Purpose</b>", styles["TableHeader"])],
        [Paragraph("Admin Server", styles["TableCell"]),
         Paragraph("Django 5.x + DRF", styles["TableCell"]),
         Paragraph("Web dashboard, REST API, data storage", styles["TableCell"])],
        [Paragraph("WebSocket Layer", styles["TableCell"]),
         Paragraph("Django Channels", styles["TableCell"]),
         Paragraph("Real-time bidirectional communication", styles["TableCell"])],
        [Paragraph("Client Agent", styles["TableCell"]),
         Paragraph("Python (stdlib + websockets)", styles["TableCell"]),
         Paragraph("Hardware scanning, event monitoring", styles["TableCell"])],
        [Paragraph("Cloud Discovery", styles["TableCell"]),
         Paragraph("Supabase REST API", styles["TableCell"]),
         Paragraph("Admin IP registry for cross-network client discovery", styles["TableCell"])],
        [Paragraph("Auto-Discovery", styles["TableCell"]),
         Paragraph("UDP broadcast (port 45000)", styles["TableCell"]),
         Paragraph("LAN-only fallback for same-network discovery", styles["TableCell"])],
        [Paragraph("Database", styles["TableCell"]),
         Paragraph("SQLite (default) / PostgreSQL", styles["TableCell"]),
         Paragraph("Client data, scan results, alerts", styles["TableCell"])],
    ]
    arch_table = Table(arch_data, colWidths=[1.5 * inch, 2 * inch, 3 * inch])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(arch_table)
    elements.append(Spacer(1, 0.15 * inch))

    elements.append(Paragraph("<b>Communication Flow:</b>", styles["SmallBold"]))
    flow_items = [
        "Admin detects public IP and registers it in Supabase cloud registry on startup",
        "Admin re-registers IP every 5 minutes to handle IP changes",
        "Client queries Supabase to find admin's current IP (works across any network)",
        "Fallback: client tries cached URL, then UDP broadcast (LAN), then manual prompt",
        "Client registers via HTTP POST to admin REST API",
        "Admin approves the client from the dashboard",
        "Client starts heartbeat (HTTP) + WebSocket connection",
        "Real-time events flow: USB, File, Process, Software changes",
    ]
    for item in flow_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(PageBreak())

    # --- SECTION 2: CLOUD DISCOVERY SETUP ---
    elements.append(section_divider("2. Cloud Discovery Setup (Supabase)", styles))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(
        "Cloud discovery allows clients to find the admin server <b>across any network</b>, "
        "even when the admin's IP address changes. The admin registers its public IP in a "
        "Supabase table, and clients query that table on startup and periodically.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("<b>How it works:</b>", styles["SmallBold"]))
    how_items = [
        "1. Admin detects its public IP via external service (ipify.org)",
        "2. Admin writes IP to Supabase table <font face='Courier' size='9'>server_registry</font>",
        "3. Admin re-registers every 5 minutes (handles IP changes)",
        "4. Client queries Supabase on startup to find admin URL",
        "5. Client re-checks Supabase every 5 minutes for IP changes",
        "6. If Supabase is unavailable, falls back to cached URL then UDP",
    ]
    for item in how_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("2.1", "Create Supabase Table", Paragraph(
        "Go to your Supabase project dashboard &#8594; SQL Editor and run the SQL from "
        "<font face='Courier' size='10'>setup_cloud_discovery.sql</font>:",
        styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    sql_lines = [
        "CREATE TABLE server_registry (",
        "  id          TEXT PRIMARY KEY DEFAULT 'admin',",
        "  ip_address  TEXT NOT NULL,",
        "  port        INTEGER DEFAULT 80,",
        "  protocol    TEXT DEFAULT 'http',",
        "  is_active   BOOLEAN DEFAULT true,",
        "  updated_at  TIMESTAMPTZ DEFAULT now()",
        ");",
        "",
        "-- Enable RLS with public read, service-role write",
        "ALTER TABLE server_registry ENABLE ROW LEVEL SECURITY;",
    ]
    for line in sql_lines:
        elements.append(Paragraph(line, styles["CommandText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("2.2", "Configure Supabase Credentials", Paragraph(
        "Ensure the <font face='Courier' size='10'>.env</font> file has your Supabase credentials:",
        styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    env_lines = [
        "SUPABASE_URL=\"https://your-project.supabase.co\"",
        "SUPABASE_SERVICE_KEY=\"your-service-role-key\"",
    ]
    for line in env_lines:
        elements.append(Paragraph(line, styles["CommandText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("2.3", "Admin Auto-Registers on Startup", Paragraph(
        "When the admin server starts, it automatically detects its public IP and registers "
        "it in Supabase. No manual configuration needed. The registration refreshes every "
        "5 minutes to handle IP changes.",
        styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("2.4", "Client Auto-Discovers on Startup", Paragraph(
        "When the client starts, it queries Supabase to find the admin's current IP. "
        "If found, it uses that URL. If not (Supabase down), it falls back to cached URL, "
        "then UDP broadcast, then manual prompt. The client also re-checks Supabase every "
        "5 minutes for IP changes.",
        styles["BodyText2"]
    ), styles, color=ORANGE, bg=LIGHT_ORANGE))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph("<b>Discovery Fallback Chain:</b>", styles["SmallBold"]))
    fallback_items = [
        "1. Cloud discovery (Supabase) - works across any network",
        "2. Cached URL (client_config.json) - from previous successful connection",
        "3. UDP broadcast (port 45000) - LAN only",
        "4. Manual URL prompt - last resort",
    ]
    for item in fallback_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(PageBreak())

    # --- SECTION 3: PREREQUISITES ---
    elements.append(section_divider("3. Prerequisites &amp; Requirements", styles))
    elements.append(Spacer(1, 0.1 * inch))

    prereq_data = [
        [Paragraph("<b>Requirement</b>", styles["TableHeader"]),
         Paragraph("<b>Details</b>", styles["TableHeader"])],
        [Paragraph("Python", styles["TableCell"]),
         Paragraph("Version 3.10 or higher", styles["TableCell"])],
        [Paragraph("pip", styles["TableCell"]),
         Paragraph("Python package manager (included with Python 3.4+)", styles["TableCell"])],
        [Paragraph("Operating System", styles["TableCell"]),
         Paragraph("Windows 7/10/11, Linux, or macOS", styles["TableCell"])],
        [Paragraph("Network", styles["TableCell"]),
         Paragraph("Admin and client machines must be on the same network (or have routing between them)", styles["TableCell"])],
        [Paragraph("Ports", styles["TableCell"]),
         Paragraph("TCP 80 (or custom port) for admin, UDP 45000 for auto-discovery", styles["TableCell"])],
        [Paragraph("Admin Privileges", styles["TableCell"]),
         Paragraph("Port 80 requires elevated privileges; use port 8080 as alternative", styles["TableCell"])],
        [Paragraph("Disk Space", styles["TableCell"]),
         Paragraph("~50 MB for application + scan data", styles["TableCell"])],
    ]
    prereq_table = Table(prereq_data, colWidths=[1.8 * inch, 4.7 * inch])
    prereq_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(prereq_table)

    elements.append(PageBreak())

    # --- SECTION 4: INSTALL DEPENDENCIES ---
    elements.append(section_divider("4. Install Dependencies", styles))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("3.1", "Open a Terminal / Command Prompt", Paragraph(
        "Navigate to the project directory:", styles["BodyText2"]
    ), styles))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(
        'cd "C:\\new intern project\\system_scanner_pro\\admin-client"',
        styles["CommandText"]
    ))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("3.2", "Install Python Packages", Paragraph(
        "Install all required packages from requirements.txt:", styles["BodyText2"]
    ), styles))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("pip install -r requirements.txt", styles["CommandText"]))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("<b>Key packages installed:</b>", styles["SmallBold"]))
    pkg_items = [
        "django, djangorestframework, channels, daphne (admin server)",
        "apscheduler (scheduled scanning)",
        "PyJWT (authentication tokens)",
        "websockets, watchdog (client agent)",
        "reportlab (PDF report generation)",
    ]
    for item in pkg_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(Spacer(1, 0.1 * inch))
    elements.append(note_box(
        "<b>Note:</b> If you get permission errors, try: pip install --user -r requirements.txt",
        styles
    ))

    elements.append(PageBreak())

    # --- SECTION 5: CONFIGURE ENVIRONMENT ---
    elements.append(section_divider("5. Configure Environment", styles))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("5.1", "Environment File (.env)", Paragraph(
        "The <font face='Courier' size='10'>.env</font> file in the project root contains Django settings. "
        "The defaults work for local development:", styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))
    env_lines = [
        "DJANGO_SECRET_KEY=\"django-insecure-change-me-in-production-abc123\"",
        "DJANGO_DEBUG=True",
        "DJANGO_ALLOWED_HOSTS=\"*\"",
        "",
        "# Supabase (Cloud Discovery)",
        "SUPABASE_URL=\"https://your-project.supabase.co\"",
        "SUPABASE_SERVICE_KEY=\"your-service-role-key\"",
    ]
    for line in env_lines:
        elements.append(Paragraph(line, styles["CommandText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("5.2", "Admin Server Configuration", Paragraph(
        "The admin server reads <font face='Courier' size='10'>admin/admin_config.json</font> for bind address. "
        "Default is <font face='Courier' size='10'>0.0.0.0</font> (all interfaces).", styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("5.3", "Client Configuration", Paragraph(
        "The client reads <font face='Courier' size='10'>client_config.json</font>. "
        "The <font face='Courier' size='10'>admin_url</font> field is set automatically via cloud discovery.", styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    config_data = [
        [Paragraph("<b>Field</b>", styles["TableHeader"]),
         Paragraph("<b>Default</b>", styles["TableHeader"]),
         Paragraph("<b>Description</b>", styles["TableHeader"])],
        [Paragraph("admin_url", styles["TableCell"]),
         Paragraph('"" (empty)', styles["TableCell"]),
         Paragraph("URL of the admin server (set on first run)", styles["TableCell"])],
        [Paragraph("scan_interval", styles["TableCell"]),
         Paragraph("3600", styles["TableCell"]),
         Paragraph("Seconds between automatic scans (1 hour)", styles["TableCell"])],
        [Paragraph("auto_start", styles["TableCell"]),
         Paragraph("true", styles["TableCell"]),
         Paragraph("Start scanning automatically on client boot", styles["TableCell"])],
    ]
    config_table = Table(config_data, colWidths=[1.5 * inch, 1.3 * inch, 3.7 * inch])
    config_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(config_table)

    elements.append(PageBreak())

    # --- SECTION 6: START ADMIN SERVER ---
    elements.append(section_divider("6. Start the Admin Server", styles))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("6.1", "Run the Admin Server", Paragraph(
        "Execute the following command from the project root:", styles["BodyText2"]
    ), styles, color=DARK_BLUE, bg=LIGHT_BLUE))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("python admin/main.py", styles["CommandText"]))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("<b>Alternative options:</b>", styles["SmallBold"]))
    alt_items = [
        "Custom port: python admin/main.py --port 8080",
        "Specific host: python admin/main.py --host 192.168.1.100",
        "Reset IP config: python admin/main.py --reset",
        "Change default credentials: python admin/main.py --username myadmin --password mypass",
    ]
    for item in alt_items:
        elements.append(Paragraph(f"&#8226; <font face='Courier' size='9.5'>{item}</font>", styles["BulletText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("6.2", "First-Run Setup Prompts", Paragraph(
        "On first run, the server will:", styles["BodyText2"]
    ), styles, color=DARK_BLUE, bg=LIGHT_BLUE))
    elements.append(Spacer(1, 0.1 * inch))

    first_run_items = [
        "<b>Database migration</b> - Creates SQLite database at admin/data/scanner.db",
        "<b>Admin user creation</b> - Creates default superuser: admin / admin123",
        "<b>IP address prompt</b> - Enter 0.0.0.0 (all interfaces) or a specific IP",
        "<b>Cloud discovery registration</b> - Detects public IP and registers in Supabase",
        "<b>UDP discovery start</b> - Begins broadcasting on port 45000",
        "<b>Django server start</b> - Serves on the configured host:port",
    ]
    for item in first_run_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("6.3", "Expected Console Output", Paragraph(
        "You should see output similar to:", styles["BodyText2"]
    ), styles, color=DARK_BLUE, bg=LIGHT_BLUE))
    elements.append(Spacer(1, 0.1 * inch))

    console_output = [
        "=======================================================",
        "  System Scanner Pro Admin Panel v2.1",
        "  (Django + DRF + Bootstrap 5)",
        "=======================================================",
        "",
        "  Using saved IP: 0.0.0.0",
        "  Running database migrations...",
        "  Admin user created: admin / admin123",
        "  Admin client key: <key-string>",
        "",
        "  Dashboard: http://0.0.0.0:80",
        "  Login:     http://0.0.0.0:80/login/",
        "",
        "  UDP discovery active on port 45000 (listen + broadcast)",
        "  [OK] Registered with cloud discovery: http://1.2.3.4:80",
        "  Cloud discovery refresh every 300s",
    ]
    for line in console_output:
        elements.append(Paragraph(line, styles["CommandText"]))

    elements.append(Spacer(1, 0.1 * inch))
    elements.append(step_box("6.4", "Open the Dashboard", Paragraph(
        "Open your web browser and navigate to <b>http://localhost</b> (or http://&lt;server-ip&gt;). "
        "Log in with <b>admin</b> / <b>admin123</b>.", styles["BodyText2"]
    ), styles, color=DARK_BLUE, bg=LIGHT_BLUE))

    elements.append(PageBreak())

    # --- SECTION 7: START CLIENT ---
    elements.append(section_divider("7. Start the Client Agent", styles))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph(
        "The client agent can run on the <b>same machine</b> as the admin server (for testing) "
        "or on <b>any other machine</b> on the same network.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("7.1", "Run the Client Agent", Paragraph(
        "Open a new terminal and navigate to the project root, then:", styles["BodyText2"]
    ), styles, color=ORANGE, bg=LIGHT_ORANGE))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("python client/main.py", styles["CommandText"]))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("7.2", "First-Run Configuration", Paragraph(
        "On first run, the client will:", styles["BodyText2"]
    ), styles, color=ORANGE, bg=LIGHT_ORANGE))
    elements.append(Spacer(1, 0.1 * inch))

    client_first_run = [
        "<b>Generate registration key</b> - Unique key saved to client_key.json",
        "<b>Generate hardware fingerprint</b> - Device identity saved to client_key.json",
        "<b>Cloud discovery</b> - Query Supabase for admin's current IP address",
        "<b>Fallback chain</b> - Try cached URL, UDP broadcast, then manual prompt",
    ]
    for item in client_first_run:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("<b>Admin URL resolution (automatic):</b>", styles["SmallBold"]))
    url_items = [
        "1. Cloud discovery via Supabase (works across any network)",
        "2. Cached URL from previous session (client_config.json)",
        "3. UDP broadcast detection (LAN only)",
        "4. Manual URL prompt (last resort)",
    ]
    for item in url_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("7.3", "Registration Process", Paragraph(
        "The client will automatically:", styles["BodyText2"]
    ), styles, color=ORANGE, bg=LIGHT_ORANGE))
    elements.append(Spacer(1, 0.1 * inch))

    reg_items = [
        "1. Send registration request to admin server",
        "2. Wait for admin approval (polls every 5 seconds)",
        "3. Once approved, perform initial hardware scan",
        "4. Submit scan results to admin server",
        "5. Start heartbeat loop (every 30 seconds)",
        "6. Connect WebSocket for real-time commands",
        "7. Start event monitors (USB, File, Process, Software)",
    ]
    for item in reg_items:
        elements.append(Paragraph(item, styles["BulletText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(step_box("7.4", "Expected Console Output", Paragraph(
        "You should see output similar to:", styles["BodyText2"]
    ), styles, color=ORANGE, bg=LIGHT_ORANGE))
    elements.append(Spacer(1, 0.1 * inch))

    client_console = [
        "=======================================================",
        "  System Scanner Pro Client v1.0.0",
        "=======================================================",
        "",
        "  Your Registration Key: <key>",
        "  Device Fingerprint:    <fingerprint>",
        "",
        "  Admin Server:  http://localhost:80",
        "  Connecting to admin server...",
        "  [WAITING] Registration sent. Waiting for admin approval...",
        "  [OK] Admin approved registration.",
        "",
        "  Performing initial scan...",
        "  [OK] Initial scan submitted successfully!",
        "  Starting communication channels...",
        "  [OK] Heartbeat watchdog started",
        "  Connecting WebSocket for real-time communication...",
        "  WebSocket client started (auto-reconnect enabled)",
        "",
        "  [OK] 4 event monitors active",
    ]
    for line in client_console:
        elements.append(Paragraph(line, styles["CommandText"]))

    elements.append(PageBreak())

    # --- SECTION 8: APPROVE CLIENT ---
    elements.append(section_divider("8. Approve the Client", styles))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("8.1", "Open the Admin Dashboard", Paragraph(
        "In your web browser, go to <b>http://localhost</b> and log in with <b>admin</b> / <b>admin123</b>.",
        styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("8.2", "Navigate to Clients Page", Paragraph(
        "Click on <b>Clients</b> or <b>Dashboard</b> in the navigation menu. "
        "You will see the pending client listed with a \"Pending\" status badge.",
        styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(step_box("8.3", "Approve the Client", Paragraph(
        "Click on the client entry and click the <b>Approve</b> button, "
        "or use the bulk action checkbox to approve multiple clients at once. "
        "Once approved, the client will automatically detect the status change and proceed.",
        styles["BodyText2"]
    ), styles, color=GREEN, bg=LIGHT_GREEN))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(info_box(
        "<b>Tip:</b> The client polls the admin server every 5 seconds to check its approval status. "
        "After approval, it immediately performs an initial scan and begins normal operation.",
        styles
    ))

    elements.append(PageBreak())

    # --- SECTION 9: VERIFY CONNECTION ---
    elements.append(section_divider("9. Verify Connection", styles))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph(
        "After approval, verify that everything is working correctly:", styles["BodyText2"]
    ))
    elements.append(Spacer(1, 0.1 * inch))

    verify_items = [
        ("<b>Dashboard</b>", "The client should appear in the admin dashboard with a green \"Online\" status badge."),
        ("<b>Scan Data</b>", "Click on the client to view its hardware scan results (CPU, RAM, GPU, storage, OS)."),
        ("<b>Heartbeat</b>", "The \"Last Seen\" timestamp should update every ~30 seconds."),
        ("<b>WebSocket</b>", "Real-time updates should appear without page refresh (device changes, alerts)."),
        ("<b>Event Monitors</b>", "USB insertion/removal, process changes, and software changes should appear in the monitoring page."),
        ("<b>Scheduled Scan</b>", "The client performs scans at the configured interval (default: 1 hour)."),
    ]
    for title, desc in verify_items:
        elements.append(Paragraph(f"&#8226; {title} - {desc}", styles["BulletText"]))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(note_box(
        "<b>Note:</b> The first scan takes a few seconds. Subsequent scans are faster. "
        "You can trigger an on-demand scan from the admin dashboard using the \"Scan Now\" button.",
        styles
    ))

    elements.append(PageBreak())

    # --- SECTION 10: CONNECTION METHODS ---
    elements.append(section_divider("10. Connection Methods Reference", styles))
    elements.append(Spacer(1, 0.1 * inch))

    conn_data = [
        [Paragraph("<b>Method</b>", styles["TableHeader"]),
         Paragraph("<b>Protocol</b>", styles["TableHeader"]),
         Paragraph("<b>Direction</b>", styles["TableHeader"]),
         Paragraph("<b>Purpose</b>", styles["TableHeader"])],
        [Paragraph("Cloud Discovery", styles["TableCell"]),
         Paragraph("HTTPS", styles["TableCell"]),
         Paragraph("Client &#8594; Supabase", styles["TableCell"]),
         Paragraph("Find admin IP across any network (primary method)", styles["TableCell"])],
        [Paragraph("UDP Auto-Discovery", styles["TableCell"]),
         Paragraph("UDP", styles["TableCell"]),
         Paragraph("Bidirectional", styles["TableCell"]),
         Paragraph("LAN-only fallback for same-network discovery", styles["TableCell"])],
        [Paragraph("Registration", styles["TableCell"]),
         Paragraph("HTTP POST", styles["TableCell"]),
         Paragraph("Client &#8594; Admin", styles["TableCell"]),
         Paragraph("Client registers with admin server", styles["TableCell"])],
        [Paragraph("Status Check", styles["TableCell"]),
         Paragraph("HTTP GET", styles["TableCell"]),
         Paragraph("Client &#8594; Admin", styles["TableCell"]),
         Paragraph("Client polls for approval status", styles["TableCell"])],
        [Paragraph("Heartbeat", styles["TableCell"]),
         Paragraph("HTTP POST", styles["TableCell"]),
         Paragraph("Client &#8594; Admin", styles["TableCell"]),
         Paragraph("Periodic keep-alive (every 30s)", styles["TableCell"])],
        [Paragraph("Scan Submission", styles["TableCell"]),
         Paragraph("HTTP POST", styles["TableCell"]),
         Paragraph("Client &#8594; Admin", styles["TableCell"]),
         Paragraph("Upload hardware scan results", styles["TableCell"])],
        [Paragraph("WebSocket", styles["TableCell"]),
         Paragraph("WS/WSS", styles["TableCell"]),
         Paragraph("Bidirectional", styles["TableCell"]),
         Paragraph("Real-time commands, events, alerts", styles["TableCell"])],
        [Paragraph("Dashboard", styles["TableCell"]),
         Paragraph("HTTP", styles["TableCell"]),
         Paragraph("Browser &#8594; Admin", styles["TableCell"]),
         Paragraph("Web UI for monitoring and management", styles["TableCell"])],
        [Paragraph("REST API", styles["TableCell"]),
         Paragraph("HTTP", styles["TableCell"]),
         Paragraph("Any &#8594; Admin", styles["TableCell"]),
         Paragraph("Programmatic access with JWT/API key auth", styles["TableCell"])],
    ]
    conn_table = Table(conn_data, colWidths=[1.3 * inch, 1.1 * inch, 1.4 * inch, 2.7 * inch])
    conn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(conn_table)

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph("<b>Resilience Features:</b>", styles["SmallBold"]))
    resilience_items = [
        "Cloud discovery - admin IP auto-registered in Supabase, refreshed every 5 minutes",
        "Client re-checks Supabase every 5 minutes for admin IP changes",
        "Exponential backoff on HTTP failures (5s &#8594; 10s &#8594; 20s &#8594; 30s max)",
        "Offline event queue - events saved to disk when disconnected, replayed on reconnect",
        "WebSocket auto-reconnect with exponential backoff",
        "Heartbeat watchdog thread restarts heartbeat if it crashes",
        "Cloud &#8594; cached &#8594; UDP &#8594; manual fallback chain for discovery",
    ]
    for item in resilience_items:
        elements.append(Paragraph(f"&#8226; {item}", styles["BulletText"]))

    elements.append(PageBreak())

    # --- SECTION 11: TROUBLESHOOTING ---
    elements.append(section_divider("11. Troubleshooting", styles))
    elements.append(Spacer(1, 0.1 * inch))

    trouble_data = [
        [Paragraph("<b>Problem</b>", styles["TableHeader"]),
         Paragraph("<b>Cause</b>", styles["TableHeader"]),
         Paragraph("<b>Solution</b>", styles["TableHeader"])],
        [Paragraph("Cloud discovery fails", styles["TableCell"]),
         Paragraph("Supabase table missing or credentials wrong", styles["TableCell"]),
         Paragraph("Run setup_cloud_discovery.sql in Supabase SQL Editor; check .env credentials", styles["TableCell"])],
        [Paragraph("Admin IP not updating", styles["TableCell"]),
         Paragraph("Public IP detection failed", styles["TableCell"]),
         Paragraph("Check internet connectivity; admin logs show detection errors", styles["TableCell"])],
        [Paragraph("Port 80 permission error", styles["TableCell"]),
         Paragraph("Port 80 requires admin/root privileges", styles["TableCell"]),
         Paragraph("Use --port 8080 or run as administrator", styles["TableCell"])],
        [Paragraph("Client cannot reach admin", styles["TableCell"]),
         Paragraph("Firewall or network isolation", styles["TableCell"]),
         Paragraph("Ensure ports 80 and 45000 are open, or use --port with a high port", styles["TableCell"])],
        [Paragraph("Client stuck on \"Waiting for approval\"", styles["TableCell"]),
         Paragraph("Admin has not approved the client", styles["TableCell"]),
         Paragraph("Open admin dashboard and approve the pending client", styles["TableCell"])],
        [Paragraph("No scan data appearing", styles["TableCell"]),
         Paragraph("Scan interval not elapsed or scan failed", styles["TableCell"]),
         Paragraph("Click \"Scan Now\" on the dashboard to trigger manual scan", styles["TableCell"])],
        [Paragraph("WebSocket not connecting", styles["TableCell"]),
         Paragraph("Monitoring agent registration failed", styles["TableCell"]),
         Paragraph("Check admin server logs; restart both admin and client", styles["TableCell"])],
        [Paragraph("UDP auto-discovery not working", styles["TableCell"]),
         Paragraph("Multicast/broadcast blocked by network", styles["TableCell"]),
         Paragraph("Enter admin URL manually on client first run", styles["TableCell"])],
        [Paragraph("Database errors", styles["TableCell"]),
         Paragraph("Corrupted or missing SQLite database", styles["TableCell"]),
         Paragraph("Delete admin/data/scanner.db and restart admin server", styles["TableCell"])],
    ]
    trouble_table = Table(trouble_data, colWidths=[2 * inch, 2 * inch, 2.5 * inch])
    trouble_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_RED]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#ef9a9a")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(trouble_table)

    elements.append(PageBreak())

    # --- SECTION 12: PORT REFERENCE ---
    elements.append(section_divider("12. Port Reference", styles))
    elements.append(Spacer(1, 0.1 * inch))

    port_data = [
        [Paragraph("<b>Port</b>", styles["TableHeader"]),
         Paragraph("<b>Protocol</b>", styles["TableHeader"]),
         Paragraph("<b>Service</b>", styles["TableHeader"]),
         Paragraph("<b>Direction</b>", styles["TableHeader"])],
        [Paragraph("80", styles["TableCell"]),
         Paragraph("TCP", styles["TableCell"]),
         Paragraph("Django web server (dashboard + API + WebSocket)", styles["TableCell"]),
         Paragraph("Inbound (from clients and browsers)", styles["TableCell"])],
        [Paragraph("45000", styles["TableCell"]),
         Paragraph("UDP", styles["TableCell"]),
         Paragraph("Auto-discovery broadcast/listener", styles["TableCell"]),
         Paragraph("Bidirectional (broadcast + receive)", styles["TableCell"])],
        [Paragraph("8080", styles["TableCell"]),
         Paragraph("TCP", styles["TableCell"]),
         Paragraph("Alternative admin port (if configured)", styles["TableCell"]),
         Paragraph("Inbound (from clients and browsers)", styles["TableCell"])],
    ]
    port_table = Table(port_data, colWidths=[0.8 * inch, 1 * inch, 3 * inch, 1.7 * inch])
    port_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(port_table)

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(
        "This guide was generated for <b>System Scanner Pro v3.0</b>. "
        "For additional documentation, see the README.md file in the project root.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # --- BUILD ---
    doc.build(elements)
    print(f"PDF generated successfully: {OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")


if __name__ == "__main__":
    build_pdf()
