"""Generate the System Scanner Pro client installation guide for macOS & Linux.

Run from the project root:
    python docs/generate_install_guide_pdf.py

Requires: pip install reportlab
Output: docs/Client_Install_Guide_macOS_Linux.pdf
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    PageTemplate,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "Client_Install_Guide_macOS_Linux.pdf")
GENERATED = datetime.now().strftime("%B %d, %Y")
VERSION = "1.7.0"

BRAND = colors.HexColor("#0f2b46")
ACCENT = colors.HexColor("#1d6fb8")
LIGHT = colors.HexColor("#eef4fb")
CODE_BG = colors.HexColor("#101820")
CODE_FG = colors.HexColor("#d6e4f0")

styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=22, textColor=BRAND, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=14, textColor=BRAND, spaceBefore=14, spaceAfter=6)
STEP = ParagraphStyle("STEP", parent=styles["Heading3"], fontName="Helvetica-Bold",
                      fontSize=11.5, textColor=ACCENT, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontName="Helvetica",
                      fontSize=10, leading=14, spaceAfter=6)
SMALL = ParagraphStyle("SMALL", parent=styles["BodyText"], fontName="Helvetica",
                       fontSize=8.5, leading=12, textColor=colors.HexColor("#555555"))
CENTER = ParagraphStyle("CENTER", parent=styles["BodyText"], alignment=TA_CENTER)

CODE = ParagraphStyle("CODE", parent=styles["Code"], fontName="Courier",
                      fontSize=9, leading=13, textColor=CODE_FG,
                      backColor=CODE_BG, borderPadding=(6, 8, 6, 8), spaceAfter=8)


def cmd(text):
    return Preformatted(text, CODE)


def note(title, text):
    t = Table(
        [[Paragraph(f"<b>{title}</b> {text}", BODY)]],
        colWidths=[16.5 * cm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def steps_table(rows):
    data = [[Paragraph(f"<b>{n}</b>", CENTER), Paragraph(txt, BODY)] for n, txt in rows]
    t = Table(data, colWidths=[1 * cm, 15.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#dde6ef")),
    ]))
    return t


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, A4[1] - 0.9 * cm, A4[0], 0.9 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.white)
    canvas.drawRightString(A4[0] - 1 * cm, A4[1] - 0.62 * cm,
                           f"System Scanner Pro {VERSION} — Install Guide")
    canvas.setFillColor(BRAND)
    canvas.rect(0, 0, A4[0], 0.7 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 0.25 * cm, f"Generated {GENERATED}")
    canvas.restoreState()


story = []

# ── Cover ────────────────────────────────────────────────────────────────
story.append(Spacer(1, 3.2 * cm))
story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
story.append(Spacer(1, 0.6 * cm))
story.append(Paragraph("Installing the System Scanner Client<br/>on macOS &amp; Linux", H1))
story.append(Paragraph(
    f"Version {VERSION} · Generated {GENERATED} · Applies to Intel and Apple-silicon Macs "
    "and mainstream Linux distributions (Ubuntu, Debian, Fedora, Arch).", SMALL))
story.append(Spacer(1, 0.4 * cm))
story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
story.append(Spacer(1, 1.2 * cm))

story.append(Paragraph(
    "The client is a single self-contained native binary — no Python installation is "
    "required on the target machine. Each operating system gets its own build:", BODY))
story.append(steps_table([
    ("Windows", "<b>client_scanner.exe</b> — served automatically when you open the download link on Windows."),
    ("Linux", "<b>system-scanner_1.7.0_amd64.deb</b> — native Debian/Ubuntu package, installs with one command. "
              "Other distros can grab <b>client_scanner-linux.zip</b>."),
    ("macOS", "<b>client_scanner-macos.zip</b> — contains a proper <b>System Scanner.app</b> bundle."),
]))
story.append(note("How downloads work:",
                  "Open your admin panel and click <b>Download Client</b>. The panel detects your "
                  "operating system automatically and serves the right file. You can force a specific "
                  "build with /download-client/?os=linux or /download-client/?os=macos."))

story.append(PageBreak())

# ── Part A: macOS ────────────────────────────────────────────────────────
story.append(Paragraph("Part A — macOS Installation (step by step)", H1))
story.append(steps_table([
    ("Step 1", "<b>Download.</b> In your browser, go to your admin panel URL and click "
               "<b>Download Client</b>. Safari/Chrome on a Mac receives <b>client_scanner-macos.zip</b> "
               "automatically."),
    ("Step 2", "<b>Unzip it.</b> Double-click the ZIP in Finder — a <b>System Scanner.app</b> appears — "
               "or run:"),
]))
story.append(cmd("cd ~/Downloads\nunzip client_scanner-macos.zip\ncd system-scanner-macos"))
story.append(steps_table([
    ("Step 3", "<b>Allow the app to run (Gatekeeper).</b> Because the app is not notarised with an "
               "Apple Developer certificate, macOS may block first launch. Remove the quarantine flag:"),
]))
story.append(cmd('xattr -dr com.apple.quarantine "System Scanner.app"'))
story.append(note("If System Settings blocked it anyway:",
                  "Go to <b>System Settings → Privacy &amp; Security</b>, scroll to the Security section "
                  "and click <b>Allow Anyway</b> next to the blocked app message, then relaunch."))
story.append(steps_table([
    ("Step 4", "<b>Start the client (first run from Terminal).</b> The console prints your Registration "
               "Key, so start it once via Terminal to see it. Double-clicking the .app also works "
               "(it runs in the background; output goes to the system log):"),
]))
story.append(cmd('"System Scanner.app/Contents/MacOS/client_scanner-macos"\n# after approval you can simply:\nopen "System Scanner.app"'))
story.append(steps_table([
    ("Step 5", "<b>Register and wait for approval.</b> The console prints a Registration Key "
               "(e.g. <b>A1B2C3D4</b>) and shows “Waiting for admin approval…”. Open the admin dashboard, "
               "find your Mac under <b>Pending</b>, and click <b>Approve</b>. The client turns green "
               "(Online) within one scan interval."),
]))

story.append(Paragraph("Optional — start automatically at login (macOS)", H2))
story.append(Paragraph("Create a LaunchAgent so the scanner starts whenever you log in:", BODY))
story.append(cmd("mkdir -p ~/Library/LaunchAgents\ncat > ~/Library/LaunchAgents/com.systemscanner.client.plist << 'EOF'\n"
                 "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                 "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\"\n"
                 "  \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
                 "<plist version=\"1.0\"><dict>\n"
                 "  <key>Label</key><string>com.systemscanner.client</string>\n"
                 "  <key>ProgramArguments</key>\n"
                 "  <array><string>/Users/YOU/system-scanner-macos/System Scanner.app/Contents/MacOS/client_scanner-macos</string></array>\n"
                 "  <key>RunAtLoad</key><true/>\n"
                 "  <key>KeepAlive</key><true/>\n"
                 "</dict></plist>\nEOF\n"
                 "launchctl load ~/Library/LaunchAgents/com.systemscanner.client.plist"))

story.append(PageBreak())

# ── Part B: Linux ────────────────────────────────────────────────────────
story.append(Paragraph("Part B — Linux Installation (step by step)", H1))
story.append(steps_table([
    ("Step 1", "<b>Download.</b> From the admin panel click <b>Download Client</b> — Linux browsers get "
               "the <b>system-scanner_1.7.0_amd64.deb</b> package (Debian/Ubuntu). Fetch it directly with wget:"),
]))
story.append(cmd("# replace YOUR-PANEL with your admin server URL\n"
                 "wget 'https://YOUR-PANEL/download-client/?os=linux' -O system-scanner_1.7.0_amd64.deb"))
story.append(steps_table([
    ("Step 2", "<b>Install the package.</b> This installs the binary to <b>/usr/local/bin/system-scanner</b>:"),
]))
story.append(cmd("sudo dpkg -i ./system-scanner_1.7.0_amd64.deb\n# if a dependency error appears:\nsudo apt -f install"))
story.append(note("Not on Debian/Ubuntu?",
                  "Fedora, Arch, etc. can download the portable zip instead: "
                  "<font face='Courier'>https://YOUR-PANEL/download-client/?os=linux&amp;format=zip</font>, "
                  "then unzip and run <font face='Courier'>chmod +x client_scanner-linux &amp;&amp; ./client_scanner-linux</font>."))
story.append(steps_table([
    ("Step 3", "<b>Run it:</b>"),
]))
story.append(cmd("sudo system-scanner"))
story.append(steps_table([
    ("Step 4", "<b>Get approved.</b> Note the Registration Key printed in the terminal. On the admin "
               "dashboard your machine appears with a yellow <b>Pending</b> dot — click <b>Approve</b>. "
               "Heartbeats and scans begin immediately after approval."),
    ("Step 5", "<b>Verify connectivity.</b> If nothing appears on the dashboard, confirm the panel is "
               "reachable from the machine:"),
]))
story.append(cmd("curl -I https://YOUR-PANEL/api/health   # expect HTTP 200"))

story.append(Paragraph("Optional — run as a background service (Linux)", H2))
story.append(Paragraph("Install as a systemd service so it survives reboots and runs headless:", BODY))
story.append(cmd("sudo tee /etc/systemd/system/system-scanner.service > /dev/null << 'EOF'\n"
                 "[Unit]\nDescription=System Scanner Pro Client\nAfter=network-online.target\nWants=network-online.target\n\n"
                 "[Service]\nExecStart=/usr/local/bin/system-scanner\nRestart=always\nRestartSec=10\nUser=root\n\n"
                 "[Install]\nWantedBy=multi-user.target\nEOF\n"
                 "sudo systemctl daemon-reload\nsudo systemctl enable --now system-scanner\njournalctl -u system-scanner -f"))

# ── Troubleshooting ──────────────────────────────────────────────────────
story.append(Paragraph("Troubleshooting", H1))
tbl = Table([
    [Paragraph("<b>Symptom</b>", BODY), Paragraph("<b>Cause &amp; fix</b>", BODY)],
    [Paragraph("“Permission denied” on Linux/macOS", BODY),
     Paragraph("Binary not executable — run <font face='Courier'>chmod +x client_scanner-*</font>.", BODY)],
    [Paragraph("“App can’t be opened” on macOS", BODY),
     Paragraph("Gatekeeper quarantine — run <font face='Courier'>xattr -dr com.apple.quarantine \"System Scanner.app\"</font>, "
               "or use System Settings → Privacy &amp; Security → Allow Anyway.", BODY)],
    [Paragraph("dpkg reports missing dependencies", BODY),
     Paragraph("Run <font face='Courier'>sudo apt -f install</font> to fix up, then retry. Or use the "
               "portable zip: <font face='Courier'>/download-client/?os=linux&amp;format=zip</font>.", BODY)],
    [Paragraph("Client stuck at “Pending”", BODY),
     Paragraph("An admin must approve it from the dashboard, or the device re-registers each poll. "
               "Approve once — approval persists by registration key.", BODY)],
    [Paragraph("Client never appears on dashboard", BODY),
     Paragraph("Wrong panel URL configured, or outbound HTTPS blocked. Check "
               "<font face='Courier'>curl -I https://YOUR-PANEL/api/health</font> returns 200.", BODY)],
    [Paragraph("“cannot execute binary file”", BODY),
     Paragraph("You downloaded the build for a different OS — re-download from the panel so it matches yours.", BODY)],
], colWidths=[5.5 * cm, 11 * cm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d7e6")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 7),
]))
story.append(tbl)

story.append(Spacer(1, 0.5 * cm))
story.append(note("Good to know:",
                  "All builds talk to the same admin panel over HTTPS with automatic WebSocket→HTTP "
                  "fallback, so no firewall rules beyond outbound 443 are needed. Deleting a device from "
                  "the dashboard only soft-hides it; re-registration with the same key restores history."))

# ── Build ────────────────────────────────────────────────────────────────
doc = BaseDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=1.6 * cm, rightMargin=1.6 * cm,
    topMargin=1.6 * cm, bottomMargin=1.4 * cm,
    title="System Scanner Pro — macOS & Linux Install Guide",
    author="System Scanner Pro",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=page_decor)])
doc.build(story)
print(f"PDF written: {OUTPUT}")
