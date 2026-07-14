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
# Where the generated site will live. Target: insights.theaisalesleader.com
# (a subdomain of Greg's real site, so every article builds HIS domain's
# authority). Until that DNS record exists, it serves from GitHub Pages —
# flip it by setting the SITE_BASE_URL repository variable / env var.
SITE_BASE_URL = (
    os.getenv("SITE_BASE_URL")
    or "https://greggrandsd-hub.github.io/Linked-In-Content-Generator"
).rstrip("/")
SITE_NAME = os.getenv("SITE_NAME", "The AI Sales Leader — Insights")
SITE_TAGLINE = os.getenv(
    "SITE_TAGLINE",
    "Straight answers on sales leadership, revenue growth, and AI-powered "
    "sales teams — from Greg Grand.",
)
AUTHOR_NAME = os.getenv("AUTHOR_NAME", "Greg Grand")
AUTHOR_BIO = os.getenv(
    "AUTHOR_BIO",
    "Greg Grand is the founder of G Squared Advisors and The AI Sales Leader™. "
    "A Vistage speaker and fractional CRO with 30 years in enterprise sales at "
    "Google, Apple, and Celestica, he certifies sales leaders to run AI-powered "
    "teams (CASL™) and helps CEOs build revenue engines that scale on process, "
    "not heroics. More at theaisalesleader.com.",
)
AUTHOR_LINKEDIN_URL = os.getenv("AUTHOR_LINKEDIN_URL", "https://www.linkedin.com/in/greggrand/")
AUTHOR_WEBSITE_URL = os.getenv("AUTHOR_WEBSITE_URL", "https://theaisalesleader.com")

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
