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

# ── SEO / AEO / GEO Engine ───────────────────────────────────────────────────
# Where the generated site will live. Default: this repo's GitHub Pages URL.
SITE_BASE_URL = (
    os.getenv("SITE_BASE_URL")
    or "https://greggrandsd-hub.github.io/Linked-In-Content-Generator"
).rstrip("/")
SITE_NAME = os.getenv("SITE_NAME", "G Squared Truths")
SITE_TAGLINE = os.getenv(
    "SITE_TAGLINE",
    "No-nonsense sales leadership answers for CEOs, founders, and revenue leaders.",
)
AUTHOR_NAME = os.getenv("AUTHOR_NAME", "Greg Grand")
AUTHOR_BIO = os.getenv(
    "AUTHOR_BIO",
    "Greg Grand is a sales leadership strategist and Vistage speaker who helps "
    "CEOs, founders, and revenue leaders build sales teams that scale on "
    "process, not heroics — the G Squared Truths framework.",
)
AUTHOR_LINKEDIN_URL = os.getenv("AUTHOR_LINKEDIN_URL", "https://www.linkedin.com/in/greggrand/")

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
