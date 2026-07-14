"""
Configuration loader — reads all secrets and settings from .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Dropbox ──────────────────────────────────────────────────────────────────
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN", "")
DROPBOX_FOLDER_PATH = os.getenv("DROPBOX_FOLDER_PATH", "/LinkedInContent")

# ── Google Gemini AI ─────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Gmail / SMTP ─────────────────────────────────────────────────────────────
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")  # where to send the draft

# ── LinkedIn API (for auto-posting) ──────────────────────────────────────────
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")

# ── Voice / Persona ──────────────────────────────────────────────────────────
LINKEDIN_PERSONA = os.getenv(
    "LINKEDIN_PERSONA",
    (
        "You are Greg Grand — The AI Sales Leader™. "
        "Fractional CRO, Founder of G Squared Advisors (San Diego), Vistage CEO speaker. "
        "30+ years building and fixing sales organizations. $300M+ revenue generated. "
        "You are an OPERATOR, not a trainer. You walk into broken sales orgs and build systems. "
        "Your LinkedIn voice is direct, no-BS, staccato, and experience-driven. "
        "You speak from the field, not the ivory tower. "
        "You diagnose before you prescribe. You build systems, not workarounds. "
        "Contact: greg@gsquaredadvisors.com"
    ),
)
