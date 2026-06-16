"""
Configuration module — all settings via environment variables.
Copy .env.example to .env and fill in your values.
"""
import os


class Config:
    # Telegram Bot Token — get from @BotFather
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "your_telegram_bot_token")

    # Ollama URL — use Windows host IP if running Ollama on Windows
    # Find IP: ip route | grep default | awk '{print $3}'
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")

    # n8n Webhook URLs — copy from n8n after importing the workflow
    # n8n → Workflow → Webhook node → Production URL
    N8N_SEND_WEBHOOK:  str = os.getenv("N8N_SEND_WEBHOOK",  "http://localhost:5678/webhook/send-application")
    N8N_DRAFT_WEBHOOK: str = os.getenv("N8N_DRAFT_WEBHOOK", "http://localhost:5678/webhook/draft-application")
    N8N_SHEETS_WEBHOOK: str = os.getenv("N8N_SHEETS_WEBHOOK", "http://localhost:5678/webhook/log-sheets")

    # CV PDF path inside the container
    CV_PDF_PATH: str = os.getenv("CV_PDF_PATH", "/app/assets/CV_2026.pdf")
