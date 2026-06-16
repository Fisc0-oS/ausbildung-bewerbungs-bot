# 🤖 Ausbildung Bewerbungs-Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-Local_LLM-5A6E6E?style=for-the-badge&logo=ollama&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/n8n-Automation-EA4B71?style=for-the-badge&logo=n8n&logoColor=white" />
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" />
</p>

<p align="center">
  Automated job application bot for German <strong>Ausbildung</strong> positions.<br/>
  Paste a job listing → get a personalized Anschreiben + CV PDF in ~30 seconds.<br/>
  <strong>100% self-hosted. Zero cloud costs. Runs on your home server.</strong>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Analysis** | Extracts company name, email, match score from any job listing |
| ✍️ **AI Cover Letter** | Generates personalized Anschreiben via local LLM (gemma2:9b) |
| 📄 **PDF Generation** | Creates professional Anschreiben + CV PDF with photo |
| ✅ **3-Button Flow** | Send / Draft / Skip — right from Telegram |
| 📧 **Gmail Integration** | Sends application directly via Gmail API |
| 📅 **Auto Follow-up** | Google Calendar reminder 14 days after applying |
| 📊 **Application Tracker** | Logs every application to Google Sheets |

---

## 🏗️ Architecture

```
Telegram (job listing text)
        │
        ▼
  Python Bot (bot.py)
        │
        ├──► Ollama gemma2:9b ──► Anschreiben (cover letter)
        ├──► Ollama gemma2:9b ──► Vacancy analysis (JSON)
        └──► ReportLab ──────────► PDF files
                │
                ▼
     Telegram: analysis + PDFs + buttons
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
     Send     Draft    Skip
       │        │
       ▼        ▼
    n8n Webhooks
       ├──► Gmail API
       ├──► Google Calendar
       └──► Google Sheets
```

---

## 🛠️ Tech Stack

- **[Python 3.12](https://python.org)** + [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- **[Ollama](https://ollama.ai)** — Local LLM inference (no API key required)
- **[n8n](https://n8n.io)** — Workflow automation (Gmail, Calendar, Sheets)
- **[ReportLab](https://reportlab.com)** — PDF generation
- **[Docker](https://docker.com)** + Docker Compose

---

## 🚀 Quick Start

### Prerequisites

- Docker + Docker Compose
- [Ollama](https://ollama.ai) with models pulled:
  ```bash
  ollama pull gemma2:9b
  ollama pull gemma2:2b
  ```
- [n8n](https://n8n.io) instance
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Cloud project with Gmail, Calendar and Sheets APIs enabled

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Fisc0-oS/Ausbildung-Bot.git
cd Ausbildung-Bot

# 2. Configure environment
cp .env.example .env
nano .env  # Add your tokens and URLs

# 3. Add your CV photo (optional)
cp your-photo.png assets/foto-CV.png

# 4. Import n8n workflow
# Go to n8n → Import → select n8n_webhooks_workflow.json
# Configure Google credentials and activate the workflow

# 5. Start the bot
docker compose up -d --build
docker logs ausbildung-bot -f
```

---

## ⚙️ Configuration

All settings are via environment variables. Copy `.env.example` to `.env`:

```env
# Telegram Bot Token
TELEGRAM_TOKEN=your_bot_token

# Ollama URL (Windows host IP if Ollama runs on Windows)
OLLAMA_URL=http://172.17.0.1:11434

# n8n Webhook URLs (copy from n8n after importing workflow)
N8N_SEND_WEBHOOK=https://your-n8n/webhook/send-application
N8N_DRAFT_WEBHOOK=https://your-n8n/webhook/draft-application
N8N_SHEETS_WEBHOOK=https://your-n8n/webhook/log-sheets
```

> **Note:** If Ollama runs on a Windows host, find the IP with:
> ```bash
> ip route | grep default | awk '{print $3}'
> ```

---

## 📱 Usage

1. Send `/start` to the bot
2. Paste any German job listing text
3. Wait ~30 seconds for analysis + cover letter generation
4. Review the vacancy analysis and PDF preview
5. Choose an action:
   - **✅ Send** — Gmail sends it with PDFs + Calendar reminder + Sheets log
   - **📝 Draft** — Saves to Gmail Drafts + Sheets log
   - **❌ Skip** — Discard

---

## 📁 Project Structure

```
Ausbildung-Bot/
├── bot.py                      # Telegram bot + LLM logic
├── pdf_generator.py            # PDF generation (Anschreiben + CV)
├── config.py                   # Environment variable configuration
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example                # Environment template
├── n8n_webhooks_workflow.json  # n8n workflow (Gmail + Calendar + Sheets)
├── assets/
│   └── foto-CV.png             # Your photo (not included in repo)
└── SETUP.md                    # Detailed setup guide
```

---

## 🔧 n8n Setup

1. Import `n8n_webhooks_workflow.json` into your n8n instance
2. Configure credentials:
   - **Gmail OAuth2** — for sending emails
   - **Google Calendar OAuth2** — for follow-up reminders
   - **Google Sheets Service Account** — for application tracking
3. Replace `YOUR_SPREADSHEET_ID` in all Sheets nodes
4. **Activate** the workflow

---

## 🤝 Related Projects

**[WhatsApp AI Bot](https://github.com/Fisc0-oS/Whatsapp-AI-bot)** — Restaurant reservation bot built with WAHA + n8n + Ollama, also fully self-hosted.

---

## 👤 Author

**Volodymyr Chipak**

[![Website](https://img.shields.io/badge/Website-v--chipak.de-1F4E79?style=flat-square&logo=googlechrome&logoColor=white)](https://v-chipak.de)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Volodymyr_Chipak-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/volodymyr-chipak-803b2628a/)
[![GitHub](https://img.shields.io/badge/GitHub-Fisc0--oS-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/Fisc0-oS)

---

## 📄 License

MIT License — feel free to use and adapt for your own job search automation.
