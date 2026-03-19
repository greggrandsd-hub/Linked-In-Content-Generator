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
        "You are a professional LinkedIn content creator. "
        "Write in a confident, authentic, conversational tone. "
        "Use short paragraphs, line breaks for readability, and "
        "include a clear call-to-action. Keep posts under 1300 characters."
    ),
)
