"""
Ausbildung Bewerbungs-Bot
Automated job application generator for German Ausbildung positions.

Author: github.com/Fisc0-oS
"""

import logging
import os
import json
import re
import requests
import tempfile
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from pdf_generator import generate_anschreiben_pdf, generate_cv_pdf
from config import Config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory session storage
pending_applications: dict = {}


# ── OLLAMA ────────────────────────────────────────────────────────────────────

def ollama_generate(prompt: str, model: str = "gemma2:9b", max_tokens: int = 1200) -> str:
    """Send a prompt to local Ollama instance and return the response."""
    try:
        resp = requests.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": max_tokens}
            },
            timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return ""


def analyze_vacancy(vacancy_text: str) -> dict:
    """Extract structured data from job listing using local LLM."""
    prompt = f"""Read this job listing and return a JSON object.
Return ONLY the JSON, nothing else.

Job listing:
{vacancy_text[:2000]}

Example output:
{{
  "firma": "Example GmbH",
  "stelle": "Fachinformatiker Systemintegration",
  "ort": "Hamburg",
  "start": "01.09.2026",
  "email": "jobs@example.de",
  "match_score": 85,
  "match_begruendung": "Good match with IT skills",
  "top_anforderungen": ["Network administration", "IT systems", "Problem solving"],
  "fehlende_skills": ["None"],
  "empfehlung": "BEWERBEN"
}}

JSON for this job listing:"""

    raw = ollama_generate(prompt, model="gemma2:9b", max_tokens=600)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            # Sanitize placeholder values
            bad = ["exakter", "Firmenname", "Platzhalter", "Stadt aus", "Datum wenn"]
            for key in ["firma", "stelle", "ort", "email"]:
                val = data.get(key, "")
                if any(w in str(val) for w in bad):
                    data[key] = "" if key == "email" else "Unknown"
            data["match_score"] = int(data.get("match_score") or 75)
            data["top_anforderungen"] = data.get("top_anforderungen") or ["IT Systems", "Networking", "Problem Solving"]
            data["fehlende_skills"] = data.get("fehlende_skills") or ["None"]
            data["empfehlung"] = data.get("empfehlung") or "BEWERBEN"
            return data
    except Exception as e:
        logger.error(f"JSON parse error: {e}\nRaw: {raw[:300]}")

    return _manual_extract(vacancy_text)


def _manual_extract(text: str) -> dict:
    """Fallback: extract key fields using regex."""
    email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""

    firma = "Unknown"
    firma_match = re.search(r'([A-Z][^\n.]{2,50}(?:GmbH|AG|KG|SE|GbR|e\.V\.)[\s\w&.-]*)', text)
    if firma_match:
        firma = firma_match.group(0).strip()

    ort = "Hamburg"
    ort_match = re.search(r'\b(\d{5})\s+([A-ZÄÖÜ][a-zäöü]+)', text)
    if ort_match:
        ort = ort_match.group(2)

    start = "n/a"
    if "September" in text:
        start = "01.09.2026"

    return {
        "firma": firma,
        "stelle": "Fachinformatiker Systemintegration",
        "ort": ort,
        "start": start,
        "email": email,
        "match_score": 75,
        "match_begruendung": "Good match with IT skills",
        "top_anforderungen": ["IT Systems", "Networking", "Problem Solving"],
        "fehlende_skills": ["None"],
        "empfehlung": "BEWERBEN"
    }


def generate_anschreiben(vacancy_text: str, firma: str, stelle: str) -> str:
    """Generate a personalized cover letter using local LLM."""
    firma_display = firma if firma not in ("Unknown", "") else "your company"

    prompt = f"""Write a job application cover letter in German (B2 level).

STYLE GUIDELINES:
- Sound natural and personal, not like a template
- Short, clear sentences (max 20-25 words each)
- Active voice, not passive
- Describe concrete situations instead of listing technologies
- Show enthusiasm without exaggerating
- Sound like a young person who speaks German well as a second language (B2)

APPLICANT:
- Lives in Hamburg, Germany
- Ukrainian, learning German for years, currently in B2 course
- Built a WhatsApp bot that manages restaurant reservations
  (runs completely locally on home server, no cloud)
- Built a Telegram bot that automatically generates job applications
- Runs own website with excellent security rating
- Skills: Linux, Docker, Networking, Server administration, Python
- Available from August 2026, willing to relocate

POSITION at {firma_display}:
{stelle}

Requirements:
{vacancy_text[:800]}

STRUCTURE (follow exactly):
Paragraph 1 (3-4 sentences): Why this position is interesting — be specific about the role
Paragraph 2 (4-5 sentences): Describe one concrete project (WhatsApp Bot OR website) — what was built and what was learned
Paragraph 3 (3-4 sentences): Connect experience to the job requirements
Paragraph 4 (2-3 sentences): Mention B2 course, motivation and closing

STRICT RULES:
1. Start DIRECTLY with: Sehr geehrte Damen und Herren,
2. NO date, NO address, NO subject line in the text
3. NO markdown (no **, no [], no *)
4. End with: Mit freundlichen Grüßen,
5. Maximum 200 words
6. No technology lists — tell a story

Write the cover letter now:"""

    return ollama_generate(prompt, model="gemma2:9b", max_tokens=800)


def clean_anschreiben(text: str) -> str:
    """Remove markdown and unwanted elements from generated text."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'#{1,3}\s+', '', text)

    match = re.search(r'Sehr geehrte', text)
    if match:
        text = text[match.start():]

    text = re.sub(r'\n\s*[A-Z][a-z]+ [A-Z][a-z]+\s*$', '', text, flags=re.MULTILINE)

    if "Mit freundlichen Grüßen" not in text:
        text += "\n\nMit freundlichen Grüßen,"

    return text.strip()


# ── INTEGRATIONS ──────────────────────────────────────────────────────────────

def log_to_sheets(data: dict, status: str):
    """Log application to Google Sheets via n8n webhook."""
    if not Config.N8N_SHEETS_WEBHOOK:
        return
    try:
        requests.post(Config.N8N_SHEETS_WEBHOOK, json={
            "datum": datetime.now().strftime("%Y-%m-%d"),
            "firma": data.get("firma", ""),
            "stelle": data.get("stelle", ""),
            "ort": data.get("ort", ""),
            "start": data.get("start", ""),
            "email": data.get("email", ""),
            "status": status,
            "match_score": data.get("match_score", ""),
            "keywords": ", ".join(data.get("top_anforderungen", [])),
            "follow_up": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        }, timeout=10)
    except Exception as e:
        logger.error(f"Sheets webhook error: {e}")


def send_gmail(data: dict, anschreiben_pdf: bytes, cv_pdf: bytes, draft: bool = False):
    """Send application email or save as draft via n8n webhook."""
    webhook = Config.N8N_DRAFT_WEBHOOK if draft else Config.N8N_SEND_WEBHOOK
    if not webhook:
        return False
    try:
        import base64
        resp = requests.post(webhook, json={
            "to_email": data.get("email", ""),
            "firma": data.get("firma", ""),
            "stelle": data.get("stelle", ""),
            "anschreiben_text": data.get("anschreiben", ""),
            "anschreiben_pdf_b64": base64.b64encode(anschreiben_pdf).decode(),
            "cv_pdf_b64": base64.b64encode(cv_pdf).decode(),
            "draft": draft
        }, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        return False


# ── TELEGRAM HANDLERS ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Ausbildung Application Bot*\n\n"
        "Send me a job listing text and I will:\n"
        "• Analyze the position\n"
        "• Generate a personalized Anschreiben\n"
        "• Create PDF files (cover letter + CV)\n\n"
        "📋 Paste job listing here ↓",
        parse_mode="Markdown"
    )


async def handle_vacancy_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vacancy_text = update.message.text

    if len(vacancy_text) < 50:
        await update.message.reply_text("⚠️ Text too short. Please paste the full job listing.")
        return

    processing_msg = await update.message.reply_text(
        "⏳ *Analyzing vacancy...*\n\n🔍 Step 1/3: Reading requirements...",
        parse_mode="Markdown"
    )

    # Step 1: Analyze vacancy
    analysis = analyze_vacancy(vacancy_text)

    firma_display = analysis['firma'] if analysis['firma'] not in ('Unknown', '') else '?'
    await processing_msg.edit_text(
        f"⏳ *Analyzing vacancy...*\n\n"
        f"✅ Step 1/3: Found — *{firma_display}*\n"
        f"✍️ Step 2/3: Generating Anschreiben...",
        parse_mode="Markdown"
    )

    # Step 2: Generate cover letter
    anschreiben_raw = generate_anschreiben(vacancy_text, analysis["firma"], analysis["stelle"])
    if not anschreiben_raw:
        await processing_msg.edit_text("❌ Generation failed. Check if Ollama is running.")
        return

    anschreiben = clean_anschreiben(anschreiben_raw)

    await processing_msg.edit_text(
        f"⏳ *Analyzing vacancy...*\n\n"
        f"✅ Step 1/3: Found — *{firma_display}*\n"
        f"✅ Step 2/3: Anschreiben ready\n"
        f"📄 Step 3/3: Generating PDFs...",
        parse_mode="Markdown"
    )

    # Step 3: Generate PDFs
    try:
        anschreiben_pdf = generate_anschreiben_pdf(anschreiben, analysis)
        cv_pdf = generate_cv_pdf()
    except Exception as e:
        logger.error(f"PDF error: {e}")
        await processing_msg.edit_text(f"❌ PDF generation error: {e}")
        return

    pending_applications[chat_id] = {
        **analysis,
        "anschreiben": anschreiben,
        "anschreiben_pdf": anschreiben_pdf,
        "cv_pdf": cv_pdf,
    }

    await processing_msg.delete()

    # Build analysis message
    score = int(analysis.get("match_score") or 75)
    score_emoji = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
    rec_emoji = "✅" if (analysis.get("empfehlung") or "BEWERBEN") == "BEWERBEN" else "⚠️"
    anforderungen = "\n".join(f"  • {r}" for r in (analysis.get("top_anforderungen") or []))
    fehlende = "\n".join(f"  • {s}" for s in (analysis.get("fehlende_skills") or ["None"]))
    def esc(t):
        return str(t).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
    anforderungen = esc(anforderungen)
    fehlende = esc(fehlende)
    preview = anschreiben[:280].replace("*", "").replace("_", "").replace("`", "")

    firma_line = f"🏢 *Firma:* {esc(analysis['firma'])}\n" if analysis.get('firma') and analysis['firma'] not in ('Unknown', '') else ""
    ort_line = f"📍 *Ort:* {esc(analysis['ort'])}\n" if analysis.get('ort') and analysis['ort'] not in ('Unknown', '') else ""
    email_line = f"✉️ *Email:* {analysis['email']}\n" if analysis.get('email') else ""

    analysis_text = (
        f"📊 *VACANCY ANALYSIS*\n"
        f"{'─' * 30}\n"
        f"{firma_line}"
        f"💼 *Position:* {esc(analysis.get('stelle', '-'))}\n"
        f"{ort_line}"
        f"📅 *Start:* {esc(analysis.get('start', 'n/a'))}\n"
        f"{email_line}\n"
        f"{score_emoji} *Match Score:* {score}/100\n"
        f"_{esc(analysis.get('match_begruendung', ''))}_\n\n"
        f"🎯 *Top Requirements:*\n{anforderungen}\n\n"
        f"❓ *Missing Skills:*\n{fehlende}\n\n"
        f"{rec_emoji} *Recommendation:* {esc(analysis.get('empfehlung', 'BEWERBEN'))}\n"
        f"{'─' * 30}\n"
        f"📝 *Preview:*\n_{preview}..._"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Send", callback_data=f"send_{chat_id}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"skip_{chat_id}"),
        ],
        [
            InlineKeyboardButton("📝 Draft", callback_data=f"draft_{chat_id}"),
        ]
    ])

    await update.message.reply_text(
        analysis_text,
        reply_markup=keyboard
    )

    # Send PDF files
    firma_clean = re.sub(r'[^\w-]', '_', str(analysis.get('firma') or 'Company'))[:25]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(anschreiben_pdf)
        ans_path = f.name

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(cv_pdf)
        cv_path = f.name

    await update.message.reply_document(
        document=open(ans_path, "rb"),
        filename=f"Anschreiben_{firma_clean}.pdf",
        caption="📄 Cover Letter (Anschreiben)"
    )
    await update.message.reply_document(
        document=open(cv_path, "rb"),
        filename="CV_2026.pdf",
        caption="📄 Curriculum Vitae"
    )

    os.unlink(ans_path)
    os.unlink(cv_path)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    parts = query.data.rsplit("_", 1)
    action = parts[0]
    chat_id = int(parts[1])

    data = pending_applications.get(chat_id)
    if not data:
        await query.edit_message_text("⚠️ Session expired. Please send the job listing again.")
        return

    if action == "skip":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ *Skipped.*", parse_mode="Markdown")
        pending_applications.pop(chat_id, None)

    elif action == "send":
        await query.edit_message_reply_markup(reply_markup=None)
        status_msg = await query.message.reply_text("📤 Sending application...")
        success = send_gmail(data, data["anschreiben_pdf"], data["cv_pdf"], draft=False)
        log_to_sheets(data, "Sent ✅")
        if success:
            await status_msg.edit_text(
                f"✅ Application sent!\n\n"
                f"🏢 {data.get('firma', '-')}\n"
                f"✉️ {data.get('email', '-')}\n"
                f"📅 Follow-up reminder: +14 days\n"
                f"📊 Logged to Google Sheets"
            )
        else:
            await status_msg.edit_text(
                "⚠️ n8n webhook did not respond.\n"
                "PDFs are in the chat — you can send them manually."
            )
        pending_applications.pop(chat_id, None)

    elif action == "draft":
        await query.edit_message_reply_markup(reply_markup=None)
        status_msg = await query.message.reply_text("📝 Saving draft...")
        success = send_gmail(data, data["anschreiben_pdf"], data["cv_pdf"], draft=True)
        log_to_sheets(data, "Draft 📝")
        if success:
            await status_msg.edit_text(
                f"📝 Draft saved!\n\n"
                f"✉️ Check Gmail Drafts\n"
                f"📊 Logged to Google Sheets"
            )
        else:
            await status_msg.edit_text(
                "⚠️ n8n webhook did not respond.\n"
                "PDFs are in the chat."
            )
        pending_applications.pop(chat_id, None)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vacancy_text))
    logger.info("🤖 Ausbildung Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
