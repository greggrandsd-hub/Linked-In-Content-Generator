# LinkedIn Content Generator

Automatically generates LinkedIn posts **in your voice** from files you drop into Dropbox — powered by Google Gemini AI — and emails the ready-to-publish draft to your inbox.

## How It Works

This tool replicates an automated Make.com workflow in a standalone Python app:

| Step | Service | What It Does |
|------|---------|-------------|
| 1 | **Dropbox** | Lists all files in your content folder |
| 2 | **Dropbox** | Downloads the most recent file |
| 3 | **Google Gemini AI** | Uploads the file for analysis |
| 4 | **Google Gemini AI** | Generates a LinkedIn post based on the file content |
| 5 | **Google Gemini AI** | Creates an accompanying image for the post |
| 6 | **Gmail** | Emails the post text + image to you |

You simply drop a file (article, PDF, notes, etc.) into your Dropbox folder, and the tool does the rest.

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up your API keys

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Then edit `.env` with your actual keys (see **API Setup** below).

### 3. Run it

**One-time run:**
```bash
python main.py
```

**Scheduled (runs automatically every 24 hours):**
```bash
python scheduler.py
```

**Custom schedule (e.g., every 12 hours):**
```bash
python scheduler.py --hours 12
```

---

## API Setup

### Dropbox
1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click **Create app** → choose **Scoped access** → **Full Dropbox**
3. Under **Permissions**, enable `files.metadata.read` and `files.content.read`
4. Under **OAuth 2**, click **Generate access token**
5. Paste the token into your `.env` as `DROPBOX_ACCESS_TOKEN`
6. Create a folder in Dropbox (default: `/LinkedInContent`) and drop your content files there

### Google Gemini AI
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Paste it into your `.env` as `GEMINI_API_KEY`

### Gmail
1. Enable [2-Step Verification](https://myaccount.google.com/security) on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Create a new app password (select "Mail" and your device)
4. Paste the 16-character password into your `.env` as `GMAIL_APP_PASSWORD`

---

## Customize Your Voice

Edit the `LINKEDIN_PERSONA` in your `.env` file to control how Gemini writes your posts:

```
LINKEDIN_PERSONA=You are writing LinkedIn posts for Jane Smith, a VP of Engineering
who is passionate about developer experience and team culture. Write in a warm,
direct, and slightly witty voice. Use short paragraphs and line breaks.
```

The more specific you are, the more the posts will sound like you.

---

## Project Structure

```
Linked-In-Content-Generator/
├── main.py              # Full pipeline — run this
├── scheduler.py         # Optional: run on a recurring schedule
├── config.py            # Loads settings from .env
├── dropbox_client.py    # Dropbox file listing & download
├── gemini_client.py     # Gemini text & image generation
├── email_client.py      # Gmail email sending
├── requirements.txt     # Python dependencies
├── .env.example         # Template for your secrets
└── .gitignore
```

---

## What Kind of Files Can I Drop In?

Anything Gemini can read — PDFs, text files, Word docs, images, slides, etc. The tool will upload the file and ask Gemini to create a LinkedIn post inspired by its content.

**Ideas for content source files:**
- Conference talk notes or slides
- Blog post drafts
- Industry articles or reports
- Meeting notes with key takeaways
- Screenshots of interesting data or trends

---

## License

MIT
