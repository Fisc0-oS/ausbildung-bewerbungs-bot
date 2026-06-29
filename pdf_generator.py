"""
PDF Generator FINAL — CV + Anschreiben, 1 сторінка, фото в рамці.
"""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
import re
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

from config import Config

BLUE       = colors.HexColor("#1F4E79")
LIGHT_BLUE = colors.HexColor("#2E75B6")
DARK_GRAY  = colors.HexColor("#2C2C2C")
MID_GRAY   = colors.HexColor("#666666")
LIGHT_BG   = colors.HexColor("#EEF4FB")
WHITE      = colors.white

PHOTO_PATH = Path(__file__).parent / "assets" / "foto-CV.png"


def s(name, **kw):
    d = dict(fontName="Helvetica", textColor=DARK_GRAY, fontSize=9, leading=13)
    d.update(kw)
    return ParagraphStyle(name, **d)

def hr(thickness=0.4, space_after=3):
    return HRFlowable(width="100%", thickness=thickness, color=LIGHT_BLUE, spaceAfter=space_after)

def sp(h=0.2):
    return Spacer(1, h*cm)

def blt(text, st):
    return Paragraph(f"▪  {text}", st)


# ── ANSCHREIBEN ───────────────────────────────────────────────────────────────

def generate_anschreiben_pdf(anschreiben_text: str, analysis: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.2*cm, bottomMargin=2.0*cm)

    s_name = s("N",  fontSize=15, fontName="Helvetica-Bold", textColor=BLUE, spaceAfter=4)
    s_sub  = s("Su", fontSize=9,  textColor=LIGHT_BLUE, spaceAfter=4)
    s_ct   = s("C",  fontSize=8,  textColor=MID_GRAY, spaceAfter=3)
    s_date = s("D",  fontSize=9,  textColor=MID_GRAY, spaceAfter=8)
    s_rec  = s("R",  fontSize=9.5, fontName="Helvetica-Bold", textColor=DARK_GRAY, spaceAfter=2)
    s_rec2 = s("R2", fontSize=9,  textColor=MID_GRAY, spaceAfter=8)
    s_subj = s("SB", fontSize=10.5, fontName="Helvetica-Bold", textColor=BLUE,
                spaceBefore=4, spaceAfter=8)
    s_body = s("B",  fontSize=10, leading=15, spaceAfter=7, alignment=TA_JUSTIFY)
    s_sign = s("SG", fontSize=9.5, spaceAfter=2)

    story = []

    # Шапка з фото
    txt_col = [
        Paragraph("YOUR_NAME", s_name),
        Paragraph("Bewerber – Fachinformatiker Systemintegration", s_sub),
        hr(thickness=1.2, space_after=5),
        Paragraph("YOUR_STREET  ·  YOUR_CITY  ·  YOUR_PHONE", s_ct),
        Paragraph(
            '<a href="mailto:your@email.com" color="#2E75B6">your@email.com</a>  ·  '
            '<a href="https://your-website.de" color="#2E75B6">your-website.de</a>  ·  '
            '<a href="https://github.com/YOUR_USERNAME" color="#2E75B6">github.com/YOUR_USERNAME</a>', s_ct),
    ]

    if PHOTO_PATH.exists():
        photo_img = RLImage(str(PHOTO_PATH), width=2.6*cm, height=3.2*cm)
        photo_cell = Table([[photo_img]], colWidths=[2.8*cm], rowHeights=[3.4*cm])
        photo_cell.setStyle(TableStyle([
            ("BOX",           (0,0), (-1,-1), 1.5, LIGHT_BLUE),
            ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BG),
            ("LEFTPADDING",   (0,0), (-1,-1), 3),
            ("RIGHTPADDING",  (0,0), (-1,-1), 3),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        content_width = A4[0] - 2.5*cm - 2.5*cm
        header = Table([[txt_col, photo_cell]],
                       colWidths=[content_width - 3.0*cm, 3.0*cm])
        header.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("ALIGN",         (1,0), (1,-1),  "RIGHT"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        story.append(header)
    else:
        for item in txt_col:
            story.append(item)

    story.append(sp(0.6))
    story.append(Paragraph(f"Hamburg, {datetime.now().strftime('%d. ') + ['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'][datetime.now().month-1] + datetime.now().strftime(' %Y')}", s_date))

    firma = analysis.get("firma", "")
    if firma and firma not in ("Unbekannt", ""):
        story.append(Paragraph(firma, s_rec))
        ort = analysis.get("ort", "")
        if ort:
            story.append(Paragraph(ort, s_rec2))

    stelle = analysis.get("stelle", "Fachinformatiker Systemintegration")
    story.append(Paragraph(f"Bewerbung als {stelle}", s_subj))
    story.append(hr(thickness=0.5, space_after=8))

    # Тіло листа
    skip = ["YOUR_CITY,", "YOUR_STREET", "YOUR_PHONE", "your@email",
            "v-chipak", "github", "YOUR_NAME", "Mit freundlichen"]
    # Robust paragraph split: try blank lines, then single newlines, then sentences
    _txt = anschreiben_text.strip()
    paras = [p.strip() for p in _txt.split("\n\n") if p.strip()]
    if len(paras) <= 1:
        paras = [p.strip() for p in _txt.split("\n") if p.strip()]
    if len(paras) <= 1:
        # No newlines at all — split into chunks of ~2 sentences
        sents = re.split(r"(?<=[.!?])\s+", _txt)
        paras = []
        for i in range(0, len(sents), 2):
            chunk = " ".join(sents[i:i+2]).strip()
            if chunk:
                paras.append(chunk)
    words = 0
    for para in paras:
        if any(k in para for k in skip):
            continue
        clean = para.replace("\n", " ").strip()
        if not clean:
            continue
        wc = len(clean.split())
        if words + wc > 255:
            rem = 255 - words
            if rem > 15:
                clean = " ".join(clean.split()[:rem]) + "."
            else:
                break
        story.append(Paragraph(clean, s_body))
        words += wc

    story.append(sp(0.6))
    story.append(Paragraph("Mit freundlichen Grüßen,", s_sign))
    story.append(sp(1.2))
    story.append(Paragraph("<b>YOUR_NAME</b>", s_sign))

    doc.build(story)
    return buf.getvalue()


# ── CV ────────────────────────────────────────────────────────────────────────

def generate_cv_pdf() -> bytes:
    return _cv()  # Завжди генеруємо свіжий CV


def _cv() -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.6*cm, rightMargin=1.6*cm,
        topMargin=1.8*cm, bottomMargin=1.0*cm)

    s_name = s("N",  fontSize=20, fontName="Helvetica-Bold", textColor=BLUE, leading=24, spaceAfter=4)
    s_sub  = s("Su", fontSize=10, textColor=LIGHT_BLUE, leading=14, spaceAfter=5)
    s_ct   = s("C",  fontSize=8,  textColor=MID_GRAY, leading=11, alignment=TA_CENTER, spaceAfter=0)
    s_sec  = s("Se", fontSize=8.5, fontName="Helvetica-Bold", textColor=BLUE, spaceBefore=5, spaceAfter=2)
    s_body = s("B",  fontSize=8, leading=11, spaceAfter=2)
    s_blt  = s("Bu", fontSize=7.5, textColor=MID_GRAY, leading=10, spaceAfter=1, leftIndent=8)
    s_proj = s("P",  fontSize=8.5, fontName="Helvetica-Bold", textColor=BLUE, spaceAfter=1, spaceBefore=4)
    s_tag  = s("T",  fontSize=7, textColor=MID_GRAY, leading=10, spaceAfter=2)
    s_sk   = s("SK", fontSize=7, fontName="Helvetica-Bold", textColor=BLUE)
    s_sv   = s("SV", fontSize=7, textColor=DARK_GRAY)

    # HEADER з фото
    name_block = [
        Paragraph("VOLODYMYR CHIPAK", s_name),
        Paragraph("Fachinformatiker Systemintegration  —  Bewerber ab 08/2026", s_sub),
        HRFlowable(width="100%", thickness=1.5, color=LIGHT_BLUE, spaceAfter=5),
        Paragraph(
            "Hamburg  ·  YOUR_PHONE  ·  "
            '<a href="mailto:your@email.com" color="#2E75B6">your@email.com</a>  ·  '
            '<a href="https://your-website.de" color="#2E75B6">your-website.de</a>  ·  '
            '<a href="https://github.com/YOUR_USERNAME" color="#2E75B6">github.com/YOUR_USERNAME</a>', s_ct),
    ]

    if PHOTO_PATH.exists():
        photo_img = RLImage(str(PHOTO_PATH), width=2.5*cm, height=3.2*cm)
        photo_cell = Table([[photo_img]], colWidths=[2.7*cm], rowHeights=[3.4*cm])
        photo_cell.setStyle(TableStyle([
            ("BOX",           (0,0), (-1,-1), 1.5, LIGHT_BLUE),
            ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BG),
            ("LEFTPADDING",   (0,0), (-1,-1), 3),
            ("RIGHTPADDING",  (0,0), (-1,-1), 3),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        content_width = A4[0] - 1.6*cm - 1.6*cm
        header = Table([[name_block, photo_cell]],
                       colWidths=[content_width - 2.9*cm, 2.9*cm])
        header.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("ALIGN",         (1,0), (1,-1),  "RIGHT"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
    else:
        header = Table([[name_block]], colWidths=[A4[0] - 3.2*cm])

    story = [header, sp(0.3)]

    # ЛІВА КОЛОНКА
    L = []
    L.append(Paragraph("TECHNISCHE PROJEKTE", s_sec))
    L.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))

    L.append(Paragraph("WhatsApp AI Bot — Fully Local", s_proj))
    L.append(Paragraph("WAHA · n8n · Ollama · Docker · CUDA · GTX 1080  |  01/2026–heute", s_tag))
    for t in ["Lokales KI-System ohne Cloud — 0€ laufende Kosten",
               "GPU-Inferenz 60+ tok/s, Intent-Detection EN/DE",
               "Open Source: github.com/YOUR_USERNAME"]:
        L.append(blt(t, s_blt))

    L.append(Paragraph("Telegram Ausbildungs-Bot", s_proj))
    L.append(Paragraph("Python · n8n · Ollama · ReportLab · Gmail API  |  06/2026", s_tag))
    for t in ["Automatische Anschreiben-Generierung via lokaler LLM",
               "PDF-Export + Gmail + Google Calendar + Sheets",
               "3-Button-Flow: Senden / Entwurf / Überspringen"]:
        L.append(blt(t, s_blt))

    L.append(Paragraph("Webserver your-website.de", s_proj))
    L.append(Paragraph("Ubuntu 24.04 · Apache · Cloudflare · Let's Encrypt  |  02–03/2026", s_tag))
    for t in ["SSL Labs Grade A+, TLS 1.3, 99,9% Uptime in 3 Wochen",
               "Dynamic DNS, IPv4/IPv6, Cloudflare Tunnel"]:
        L.append(blt(t, s_blt))

    L.append(Paragraph("PC-Systembau & Hardware (15+ Builds)", s_proj))
    L.append(Paragraph("2020–heute", s_tag))
    L.append(blt("RAM OC: CL18→CL14 (–23% Latenz), MemTest86/HWMonitor", s_blt))

    L.append(sp(0.2))
    L.append(Paragraph("BERUFSERFAHRUNG", s_sec))
    L.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))
    L.append(Paragraph("<b>Fachlagerist</b>  ·  MediaMarkt TechVillage Hamburg  |  10–12/2025", s_body))
    L.append(Paragraph("<b>Bundesfreiwilligendienst</b>  ·  Café Eins Hamburg  |  06/2024–09/2025", s_body))

    L.append(sp(0.2))
    L.append(Paragraph("BILDUNG", s_sec))
    L.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))
    L.append(Paragraph("IT-Selbststudium (Docker, n8n, Python, Linux, KI)  |  12/2025–03/2026", s_body))
    L.append(Paragraph("Deutschkurs B2  —  <b>aktuell in Bearbeitung</b>  |  seit 12/2025", s_body))
    L.append(Paragraph("Sprachzertifikat Deutsch B1  |  2024", s_body))
    L.append(Paragraph("Mittlerer Schulabschluss (MSA), Note 3,3  |  2025", s_body))

    # ПРАВА КОЛОНКА
    R = []
    R.append(Paragraph("KOMPETENZEN", s_sec))
    R.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))

    skills = [
        ("Container",  "Docker, Compose"),
        ("Automation", "n8n, Webhooks"),
        ("Lokale KI",  "Ollama, CUDA"),
        ("Python",     "Bot, API, PDF"),
        ("OS",         "Ubuntu 24.04, Bash"),
        ("Server",     "Apache, SSL/TLS"),
        ("Netzwerk",   "TCP/IP, DNS, UFW"),
        ("Cloud",      "Cloudflare, DDNS"),
        ("Virt.",      "VirtualBox, VMs"),
        ("Dev",        "Git, HTML, JS"),
    ]
    td = [[Paragraph(k, s_sk), Paragraph(v, s_sv)] for k, v in skills]
    t = Table(td, colWidths=[2.1*cm, 3.0*cm])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT_BG, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#CCDDEE")),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    R.append(t)

    R.append(sp(0.3))
    R.append(Paragraph("SPRACHEN", s_sec))
    R.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))
    for lang in ["UA  Ukrainisch  C2", "RU  Russisch  C1",
                 "DE  Deutsch  B1 (B2 aktuell)", "EN  Englisch  B2"]:
        R.append(Paragraph(lang, s_body))

    R.append(sp(0.3))
    R.append(Paragraph("NACHWEISE", s_sec))
    R.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))
    R.append(Paragraph("your-website.de", s_body))
    R.append(Paragraph("SSL Labs Grade A+", s_body))
    R.append(Paragraph("github.com/YOUR_USERNAME", s_body))

    R.append(sp(0.3))
    R.append(Paragraph("VERFÜGBARKEIT", s_sec))
    R.append(HRFlowable(width="100%", thickness=0.4, color=LIGHT_BLUE, spaceAfter=3))
    R.append(Paragraph("Start:  <b>08/2026</b>", s_body))
    R.append(Paragraph("Umzugsbereit:  <b>Ja</b>", s_body))
    R.append(Paragraph("Schichtbereit:  <b>Ja</b>", s_body))

    content_width = A4[0] - 1.6*cm - 1.6*cm
    main = Table([[L, R]], colWidths=[content_width * 0.685, content_width * 0.315])
    main.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LINEAFTER",     (0,0), (0,-1),  0.5, colors.HexColor("#CCDDEE")),
        ("RIGHTPADDING",  (0,0), (0,-1),  10),
        ("LEFTPADDING",   (1,0), (1,-1),  10),
    ]))
    story.append(main)

    story.append(sp(0.15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_BLUE, spaceAfter=2))
    story.append(Paragraph(
        f"Hamburg, {['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'][datetime.now().month-1] + datetime.now().strftime(' %Y')}  ·  YOUR_NAME",
        s("F", fontSize=7.5, textColor=MID_GRAY, alignment=TA_CENTER)))

    doc.build(story)
    return buf.getvalue()
