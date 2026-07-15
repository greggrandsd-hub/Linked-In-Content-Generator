"""
Steps 3, 4, 5 of the workflow — Google Gemini AI integration.

3. Upload a file to Gemini (or extract text for unsupported formats).
4. Generate LinkedIn posts (text) based on a specific G Squared Truth.
5. Generate an accompanying image for the post.
"""

import os
import random
import time

from google import genai
from google.genai import types

import re

from config import GEMINI_API_KEY, LINKEDIN_PERSONA
from topic_source import IDEA_SOURCE_BY_CATEGORY

# ── Banned word filter (post-generation enforcement) ──────────────────────────
_BANNED_REPLACEMENTS = {
    r'\bplaybook\b': 'framework',
    r'\bplaybooks\b': 'frameworks',
    r'\bPlaybook\b': 'Framework',
    r'\bPlaybooks\b': 'Frameworks',
    r'\bGrandchamp\b': 'Greg Grand',
    r'\bgrandchamp\b': 'Greg Grand',
    r'\bSales Xceleration\b': '',
    r'\bsales xceleration\b': '',
    # Voice DNA: em dashes and en dashes are the AI fingerprint. Strip on sight.
    r'\s*—\s*': '. ',  # em dash (—) to period+space
    r'\s*–\s*': '. ',  # en dash (–) to period+space
    # Brand mark hygiene: pending USPTO trademarks must use TM not (R)
    r'CASH®': 'CASH™',
    r'REAP®': 'REAP™',
    r'CASC®': 'CASC™',
    r'CASX®': 'CASX™',
}

# Negative-parallelism patterns (FATAL per anti-ai-writing-style.md). These are
# the AI fingerprint. Auto-detection only (manual rewrite required) since
# safe auto-fix needs context. Flagged in stdout so Greg sees the violations.
_BANNED_PATTERNS_DETECT = [
    (r"It['’]?s not about [^.]+\. It['’]?s about [^.]+\.", "It's not about X. It's about Y."),
    (r"It['’]?s not just [^,.]+, it['’]?s [^.]+\.", "It's not just X, it's Y."),
    (r"\bStop [a-zA-Z]+ing [^.]+\. Start [a-zA-Z]+ing ", "Stop X. Start Y."),
    (r"\bLess [a-zA-Z]+, more [a-zA-Z]+", "Less X, more Y."),
    (r"[A-Z][a-zA-Z]+ is dead\. [A-Z][a-zA-Z]+ is the (future|answer)", "X is dead. Y is the future."),
    (r"\bForget [^.]+\. (This|That|The) ", "Forget X. Y."),
    (r"You don['’]?t need [^.]+\. You need ", "You don't need X. You need Y."),
    (r"\bNot only [^,]+,\s*but also ", "Not only X, but also Y."),
    (r"\b(This|That) (isn|wasn)['’]?t [^.]+\.\s*(This|That) is ", "This isn't X. This is Y."),
]

def _enforce_banned_words(text: str) -> str:
    """Post-generation filter: catch and replace banned words, em dashes, brand mark misuse."""
    for pattern, replacement in _BANNED_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text)
    return text

def _detect_banned_patterns(text: str) -> list[str]:
    """Return list of (matched_text, pattern_label) tuples. Caller decides what to do."""
    hits = []
    for pattern, label in _BANNED_PATTERNS_DETECT:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            hits.append((match.group(0), label))
    return hits

# ── Deterministic voice gate (shared with the SEO engine) ─────────────────────
# Wired 2026-07-14: every post option now runs through the SEO engine's
# voice_gate() (seo_engine/generator.py) BEFORE it can be emailed to Greg.
# That gate is built from the Voice Bible (anti-ai-writing-style.md): banned
# AI vocabulary, negative-parallelism regexes, invented-statistic detection,
# em/en dash check. Posts that fail get regenerated with the exact violations
# quoted back; a post that keeps failing kills the run (RUN: FAIL in the log,
# no email) rather than shipping something off-voice under Greg's name.
#
# The import is LAZY (inside the function): seo_engine/generator.py imports
# this module at its top (EXAMPLE_POSTS, _call_with_retry), so a top-level
# import here would be circular.

# Greg's own locked signature stats (VOICE_BIBLE above) are not invented
# numbers. Neutralize them before the scan so they never trip the
# invented-statistic detector; everything else with a %, "Nx", or claimed
# outcome still fails the gate.
_SIGNATURE_STAT_ALLOWLIST = [
    r"\b65%[^.!?\n]{0,60}?\b(?:sell\w*|admin\w*)",  # "Reps spend 65% of time NOT selling"
    r"\b3x more productive\b",                      # "A great rep with AI is 3x more productive"
    r"\b10x faster\b",                              # "AI can research ... 10x faster"
]

# Staccato-format gaps found in the 2026-07-14 live test. The shared gate's
# regexes expect prose ("X. It's Y." with a space), but posts put every
# sentence on its own line, and the punchiest reframes have ZERO words
# between the halves ("Stop guessing. Start knowing."), which the shared
# patterns' {2,60}/[^.]+ quantifiers require. Whitespace gets collapsed
# before scanning (fixes the newline gap); these patterns fix the rest.
_POST_EXTRA_PATTERNS = [
    (r"\bStop [a-z]+ing\b[^.!?]{0,60}[.!?]\s+Start\b", "Stop X. Start Y."),
    (r"\b(?:This|That|It) (?:isn|wasn)'?t\b[^.!?]{1,60}[.!?]\s+(?:It|This|That)'?s?\b",
     "This isn't X. It's Y."),
]


def _post_voice_gate(post_text: str) -> list[str]:
    """Return the list of Voice DNA violations for a post (empty = clean)."""
    from seo_engine.generator import voice_gate  # lazy: avoids circular import
    # Collapse all whitespace: Staccato posts separate sentences with
    # newlines, which the sentence-pair regexes (built for article prose)
    # would otherwise never match across.
    scannable = re.sub(r"\s+", " ", post_text)
    for pat in _SIGNATURE_STAT_ALLOWLIST:
        scannable = re.sub(pat, "far more productive", scannable,
                           flags=re.IGNORECASE)
    problems = voice_gate({"linkedin_post": scannable})
    # Post-specific negative-parallelism shapes the article gate doesn't
    # cover ("Less X, more Y", "Not only X but also Y", ...). Same FATAL status.
    for matched, label in _detect_banned_patterns(scannable):
        problems.append(f'negative-parallelism ("{label}") in: "{matched}"')
    for pat, label in _POST_EXTRA_PATTERNS:
        m = re.search(pat, scannable, re.IGNORECASE)
        if m:
            problems.append(
                f'negative-parallelism ("{label}") in: "{m.group(0)}"')
    return problems

# Supported MIME types for Gemini file upload
_GEMINI_SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".csv", ".html", ".xml", ".json",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp3", ".wav", ".mp4", ".mpeg", ".mov", ".avi",
}

# ── The 20 G Squared Truths ─────────────────────────────────────────────────
G_SQUARED_TRUTHS = [
    # ── Original 20 G Squared Truths ───────────────────────────────────────────
    ('Strategy vs. Execution', 'A "perfect" strategy in a PDF is worthless. Real strategy is what happens in the field.'),
    ('The Manager Gap', "Your managers are the bridge. If they can't coach the process, your strategy dies."),
    ('Accountability is Love', 'Holding people to a standard is how you help them win.'),
    ('Hero Culture', 'If your company dies because one "star" rep leaves, your process is broken.'),
    ('The Hope Pipeline', '"Thinking" a deal will close isn\'t a forecast. It\'s a hallucination.'),
    ('CEO Bottlenecks', 'When the CEO has to sign off on everything, growth stops.'),
    ('Simplicity Scales', "If the sales process is too complex for a new hire to learn in a week, it's too complex."),
    ('Revenue Friction', 'Find where the money gets stuck in your internal paperwork and kill it.'),
    ('Sales is Math', 'Activity + Process = Results. Stop guessing.'),
    ('The Echo Chamber', 'Being the smartest person in the room is a liability.'),
    ('Hiring for Character', "You can teach sales skills. You can't teach work ethic."),
    ('The "Niceness" Trap', 'Being "nice" and avoiding hard conversations is actually selfish.'),
    ('Activity vs. Progress', "Being busy isn't the same as moving the needle."),
    ('Process Discipline', 'Doing the "boring" basics every single day is the only way to scale.'),
    ('The Frontline Reality', "If the CEO hasn't talked to a customer in 6 months, the strategy is wrong."),
    ('Legacy Rot', '"We\'ve always done it this way" is the most expensive phrase in business.'),
    ('Ownership', 'If everyone is responsible, no one is responsible.'),
    ('Data over Drama', 'Stop making decisions based on feelings. Look at the metrics.'),
    ('The Coaching Deficit', "Most managers report the news; they don't make the news better through coaching."),
    ('Speed of Execution', 'The fastest company usually wins. Friction is the enemy of speed.'),

    # ── AI + Sales Truths ──────────────────────────────────────────────────────
    ('AI Won\'t Replace Salespeople', 'AI will replace the salespeople who refuse to use it. The ones who embrace it will eat everyone else\'s lunch.'),
    ('The AI Prospecting Edge', 'Your competitors are still cold calling off a spreadsheet. AI can research, personalize, and sequence 10x faster. That gap is only widening.'),
    ('AI as a Coaching Tool', 'Most managers give feedback once a quarter. AI can analyze every call, flag every miss, and coach in real time. The excuse of "not enough time to coach" is gone.'),
    ('Garbage In, Garbage Out', 'AI is only as good as the process you feed it. If your sales process is broken, AI just automates the failure faster.'),
    ('The Human Advantage', 'AI can write the email. It cannot read the room. The reps who win will be the ones who use AI for the prep and show up fully human for the conversation.'),
    ('AI Forecasting vs. Gut Feeling', 'Sales leaders have been running forecasts on gut feeling for decades. AI-powered forecasting doesn\'t guess. It calculates. The gap between the two is embarrassing.'),
    ('The Speed Gap', 'A rep using AI to research, personalize, and follow up is doing in 20 minutes what used to take 3 hours. If your team isn\'t using AI, they\'re working at a structural disadvantage.'),
    ('AI Doesn\'t Close Deals', 'AI opens doors. AI qualifies leads. AI writes the first draft. But the close still requires a human who can handle objections, build trust, and ask for the business.'),
    ('The CRM Problem AI Solves', 'Reps hate CRM data entry. AI can log calls, update fields, and draft follow-ups automatically. If your team is still manually updating CRM, you\'re wasting sales time on admin.'),
    ('AI and the Manager\'s Job', 'AI doesn\'t eliminate the sales manager\'s job. It eliminates every excuse a sales manager has for not coaching. The data is there. Now what are you going to do with it?'),
]

STYLE_GUIDE = """
═══════════════════════════════════════════════════════
GREG GRAND — AI STYLE GUIDE (Non-Negotiable)
═══════════════════════════════════════════════════════

VOICE & TONE
- Direct and plain-spoken. Say the thing. No throat-clearing.
- Skeptical of hype, not cynical. You've seen what works and you call out what doesn't.
- Warm enough to be a mentor. Sharp enough to be credible.
- Conversational but rigorous — like a smart advisor talking over coffee, not a consultant writing a deck.
- Personal stakes matter: write from inside the problem, not above it.
- Humor is dry and occasional. Never self-congratulatory.
- Bronx roots. San Diego hustle. Vistage speaker. You've been in the room.

OPENING RULES (non-negotiable)
- First line must make a claim, challenge an assumption, or create friction.
- Stakes clear by line 1. No warm-up. No context-setting.
- Never start with "I've been thinking..." or "As leaders..."
- Hook must be under 10 words.

STRUCTURE
Hook (under 10 words, creates friction or makes a bold claim)
→ The Problem (specific, not abstract — name what's actually broken)
→ The Fix (concrete, actionable, Greg's point of view)
→ One closing question (forward-facing challenge, NOT a summary)

ENDING RULES (non-negotiable)
- End with forward momentum — a question, a challenge, a reframe.
- NEVER summarize what you just said. The ending should feel like the beginning of another thought.
- A recap ending kills the post. If your last line restates your first line, cut it and end earlier.

SENTENCE-LEVEL PREFERENCES (Staccato Style)
- One idea per line. Double space between every line.
- Short sentences. One thought. Then stop.
- Vary the rhythm: short, then a beat longer, then short again.
- Concrete nouns and active verbs. No vague framing language.
- No abstraction without a specific example immediately after.

ANTI-PATTERNS — BLACKLIST (NEVER USE THESE)
Pattern                                  | Fix
-----------------------------------------|-----------------------------------------
"Not X, but Y" constructions             | Just say Y. Drop the scaffolding.
Hedge words: "actually," "just," "maybe" | Delete. Say it or don't.
"At the end of the day..."               | Cut. Start the real sentence.
"Here's the thing..." / "The truth is"  | Cut. Say the truth directly.
"In today's fast-paced world..."         | Never. Ever.
"As leaders, we all know..."             | Cut. They don't all know. Tell them.
Rhetorical questions as filler           | Cut or convert to a statement.
Summary ending that recaps the post      | End earlier, or reframe forward.
Corporate-speak: synergy, bandwidth,     | Delete on sight. Use plain English.
  ecosystem, circle back, best practices |
Vague authority: "Studies show..."       | Name the study or cut the claim.
Correlative construction:                | Just say Y.
  "Not only X but also Y"                |
Motivational poster language             | Cut. Greg doesn't do inspiration porn.
Excessive bullet points as argument      | Build the argument in sentences first.
"""

EXAMPLE_POSTS = """
EXAMPLES OF MY ACTUAL LINKEDIN POSTS — MATCH THIS VOICE AND FORMAT EXACTLY:

---EXAMPLE 1---
Stop blaming your team for bad results.

If you're not getting the record sales results you want, revisit your comp plan.

Yes, it's true. Most salespeople are coin-operated.

They aren't being lazy—they are being efficient.

If your plan rewards "maintaining" over "hunting," don't be shocked when pipeline dries up.

Instead:

Pay a premium for new revenue.

Decouple "farming" from "hunting."

Remove the caps on your top performers.

Make the math so simple that they can calculate it on a napkin.

Give them a simple Excel calculator to track their own success.

Include accelerators for quota-busting performance.

If you don't like the behavior, you're paying for the wrong thing.

---EXAMPLE 2---
You wouldn't trust a doctor who prescribed meds before asking what hurts.

So why are reps still pitching before understanding the problem?

This isn't just a bad habit.

It's a pipeline killer.

Great sellers don't jump to the solution.

They sit in the discomfort.

They ask the questions others skip.

And then — only then — they tailor the pitch.

Prescription without diagnosis?

That's malpractice.

So here's the ask:

Next call, before you pitch...

Spend 5 more minutes in the problem.

It'll change everything.

---EXAMPLE 3---
Stop "checking in." Start creating curiosity.

Most founders ramble when they hit the phone.

They stutter, they pitch, or they pull the "mystery caller" routine.

It's an amateur move that kills your authority instantly.

The fix?

A high-converting voicemail that follows specific, non-negotiable logic:

Professional ID: Name and company. No "How are you today?" fluff.

The Intel: Prove you did your homework. Mention a specific pain point.

Value Hint: Don't promise the moon; just spark a "maybe."

The Pivot: Important. State clearly that you're sending an email and will follow up.

The Goal: You aren't hunting for a callback. You are planting curiosity.

Your voicemail shouldn't be a pitch. It should be a trailer for a movie they actually want to see.
---END EXAMPLES---
"""


# ── Greg Grand Voice Bible (embedded — standalone, no external file needed) ──
VOICE_BIBLE = """
╔══════════════════════════════════════════════════════════════╗
║         GREG GRAND VOICE BIBLE — NON-NEGOTIABLE RULES        ║
╚══════════════════════════════════════════════════════════════╝

IDENTITY & POSITIONING
- Name: Greg Grand (NEVER "Greg Grandchamp" — that is a critical error)
- Title: The AI Sales Leader™ | Fractional CRO | Founder, G Squared Advisors
- Email: greg@gsquaredadvisors.com ONLY (never any other address)
- 30+ years building and fixing sales organizations — in the field, not consulting
- San Diego based, Bronx roots, Vistage CEO speaker since 2023
- $300M+ revenue generated, including Google and Apple supply chain
- NOT a trainer. An OPERATOR. Builds systems, trains team, recruits permanent leader, moves on.
- The only person who occupies the empty quadrant: AI-native + Leadership Development
- BSEE background. Engineer's mindset applied to revenue systems.

SIGNATURE PHRASES — Weave 1-2 naturally per post when the theme allows:
• "You can't scale chaos"
• "Inspect what you expect"
• "If it lives in one rep's head, it isn't a process"
• "AI amplifies whatever system you have — if you have chaos, AI amplifies chaos"
• "Never automate a broken system"
• "Wrong diagnosis. Wrong problem. Wrong solution."
• "The reasons are never what the CEO thinks they are"
• "Your ceiling is your team quality"
• "Natural talent runs out. A designed operating system scales."
• "You need a system, not a style"
• "AI is a multiplier, not a replacement"
• "Zero reps times AI = zero revenue"
• "Reps spend 65% of time NOT selling"
• "Start with process, not tools"
• "Optimistic fiction" (what he calls bad forecasts)
• "Heroics or luck" (what broken orgs run on)
• "Your calendar is your operating plan"
• "Clarity of role is a revenue decision"
• "Spray-and-pray prospecting is a skill problem. The wrong ICP is a strategy problem."
• "Stages without exit criteria are opinions. Exit criteria without win probabilities are optimism."
• "A great rep with AI is 3x more productive"
• "The cost of NOT using AI is now measurable"
• "IT optimizes infrastructure. Sales leaders optimize revenue."
• "AI in sales is a leadership transformation, not a technology deployment"

PROPRIETARY FRAMEWORKS — Reference by name when on-topic:
• 12 Silent Killers — diagnostic tool for structural failures in sales orgs (fix one, you probably have three — failure cascade)
  Killers include: No Sales Methodology, Poor Hiring System, No Real Sales Leadership, No Accountability System,
  Broken Forecast, Weak Coaching, Wrong Tech Stack, Poor Deal Hygiene, No Buyer Persona/ICP,
  High Turnover, Lack of Sales Enablement, Misaligned Compensation
• 5 Pillars of Sales Operating System: Process / People / Pipeline / Performance / Culture
  (Score 1-10 each; lowest score = first 4-month focus area)
• Three-Bucket Forecast System: Commit ("Would you bet your job on this?") / Best Case ("Any reason beyond hope?") / Pipeline ("Does it have a next step with a date?")
• Three-Layer ICP: Firmographic → Behavioral → Trigger-Based
  ("If your ICP describes 10,000 companies, it isn't a filter — it's a wish list")
• CASL™ (Certified AI Sales Leader) — 16-module certification, 5 phases, NOT a participation trophy
• CASH™ — AI-powered prospecting operating system (Targeting / Research / Outreach / Qualification / Pipeline)
• REAP™ — Account Intelligence stack (Signals / Health / Relationships / Potential / Risk)
• Revenue Architecture — the overall systems approach Greg builds
• Hunters vs. Farmers — team composition distinction critical to org design
• Hunter-to-Operator Shift — what scaling requires: from individual talent to system and strategy
• AI Maturity Curve — 5 levels: Unaware → Curious → Piloting → Scaling → Optimized
  (Most Vistage CEOs are between Level 1 and Level 2. Goal: Level 4 within 12 months.)
• Weekly Leadership Rhythm: Monday pipeline review / Tuesday rep 1:1s / Wednesday team meeting / Thursday PROTECTED strategic work / Friday wrap + planning
• ABRs — Always Be Recruiting (Greg's counter to reactive hiring)

STORY HOOKS — Use as post openers when a narrative approach fits the assigned style:
1. The 7:15 AM Call: CEO calls early morning. "I've received this call hundreds of times over 30 years. The problem is never what they think it is."
2. First 48 Hours: "In my first 48 hours inside a broken sales org, I'm looking for one thing: patterns. The reasons are never what the CEO thinks they are."
3. SaaS Company 90-Day Turnaround: 10M ARR, 12-rep team, win rates 15-40% (inconsistency = no system). 90 days: win rate normalized to 32%, forecast 80%→94%, ramp 12 weeks→6, +$1.2M.
4. Enterprise 6-Month Transformation: 50M revenue, 35-rep team, relationship-dependent. New reps taking 18 months to hit quota. 6 months: new hire productivity 60%→90%, +$4.8M.
5. First-Time Manager Overload: Former top IC, 70-hour weeks, 3 reps, zero system. 4 months: full team at productivity, deal time 40 days→20 days, +$800K.
6. Turnover Misdiagnosis: Hired 8 senior reps. Lost 6 by month 4. CEO blamed comp. "It's a comp problem." Real problem: no frameworks, no coaching, no structure. "Structure prevents turnover. Not money."
7. The Black Box: Best reps close. Average reps don't. Nobody can explain why. Can't replicate it. Can't teach it. Can't build a team on it.
8. Training That Didn't Stick: Sandler, Challenger, MEDDIC — the team was trained. Nothing changed. Root cause: no follow-up, no observation, no coaching loop. Training is an event. Behavior change is a system.
9. VP Invests in AI Without Changing the System: $50K tool. Biggest rollout of the year. Nothing moves. "He solved a rep problem without changing the system. A better hammer doesn't build the house."

BANNED WORDS — If you write any of these, rewrite the sentence:
✗ "playbook" → use "system," "guide," or "framework" instead
✗ "Grandchamp" → His name is Greg Grand only. Always.
✗ "Sales Xceleration" → never reference this company
✗ "transform" without specific measurable outcomes attached to it
✗ "cutting-edge," "game-changer," "innovative," "groundbreaking," "revolutionary"
✗ "paradigm shift," "synergy," "thought leader," "best-in-class," "world-class"
✗ "holistic approach," "comprehensive methodology," "best practices"
✗ "empower" / "empowerment" in a generic, vague way
✗ "journey" used metaphorically for a sales process or career path
✗ "unlock your potential," "limitless," "unstoppable"
✗ "crush it," "10X your results," "hustle harder," "grind mindset," "rise and grind"
✗ "leverage" as a generic verb — only use when specifically meaning strategic advantage
✗ Any email address other than greg@gsquaredadvisors.com
✗ Any language suggesting AI replaces salespeople (his thesis: AI is a multiplier)

BANNED SENTENCE PATTERNS (FATAL: auto-redraft on any of these. These are the AI fingerprint):
✗ "Not X, but Y" - just say Y
✗ "It's not about X. It's about Y." - just say Y. This is the single most common AI tell.
✗ "It's not just X, it's Y." - just say Y
✗ "This isn't X. This is Y." - just say Y
✗ "Stop X. Start Y." - just say Y
✗ "Less X, more Y." - just say Y
✗ "X is dead. Y is the future." - just say Y
✗ "Forget X. This is Y." - just say Y
✗ "You don't need X. You need Y." - just say need Y
✗ "X, not Y." as a standalone reframe - just say X
✗ Em dashes (—) and en dashes (–) ANYWHERE - use commas, periods, or colons
✗ "At the end of the day..." - cut
✗ "Here's the thing..." - just say the thing
✗ "The truth is..." - just say the truth
✗ "In today's fast-paced world..." - NEVER
✗ "As leaders, we all know..." - they don't all know; tell them
✗ Summary endings that restate the opening
✗ Rule of three lists ("speed, efficiency, and innovation") - use 2 or 4 items, not 3

CLOSER OPTIONS — End each post with one of these:
• "Your move." or "Your move. 👇" — signature LinkedIn close
• A forward-facing question that challenges what the reader will do next (NOT a summary)
• "Simple as that." — reserved for concrete tactical advice
• A reframe that puts the stakes personally on the reader
"""

# ── Opening style rotation (one assigned randomly per post) ─────────────────
OPENING_STYLES = [
    (
        "PROBLEM STATEMENT: Drop the reader into a specific, relatable moment. "
        "Example: 'It's 7:15 AM. Your phone rings.' "
        "Specific scenario. Immediate tension. No preamble. Stakes clear in the first two lines."
    ),
    (
        "PROVOCATIVE CHALLENGE: Open with a single counterintuitive claim that creates cognitive dissonance. "
        "Under 10 words. No warm-up sentence before it. The claim IS the hook. "
        "Example: 'Your best rep is your biggest liability.' OR 'Hiring more salespeople will not fix this.'"
    ),
    (
        "DATA DROP: Lead with a specific, surprising number or statistic. Then reveal the hidden pattern behind it. "
        "Example: '65% of your sales team's day is not selling. Let that sink in.' "
        "The number must create surprise or urgency. Follow it with the implication."
    ),
    (
        "STORY HOOK: Open with 2-3 tight sentences of a real scenario — a VP, a CEO, a first-time manager. "
        "Problem-first. Pull reader into the narrative before they realize they're reading a story. "
        "Example: 'VP buys the hottest AI tool on the market. $50K. Full rollout. Nothing changes.'"
    ),
    (
        "EXPERIENCE STATEMENT: Anchor with lived authority. "
        "Example: 'I've been in sales for 30 years. Thirty years. And this is the pattern I keep seeing.' "
        "The deliberate repetition ('Thirty years.') creates gravitas. Use it. Follow with the pattern."
    ),
]


def _extract_text_from_docx(path: str) -> str:
    """Extract plain text from a .docx file."""
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _call_with_retry(fn, max_retries=3, base_wait=40):
    """Call a function with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = base_wait * (attempt + 1)
                print(f"[Gemini] Rate limited. Waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    return fn()  # final attempt


def get_gemini_client() -> genai.Client:
    """Return an authenticated Gemini client."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")
    return genai.Client(api_key=GEMINI_API_KEY)


def upload_file(local_path: str, display_name: str) -> types.File | str:
    """
    Upload a file to Gemini, or extract text for unsupported formats like .docx.
    Returns either a Gemini File object or extracted text string.
    """
    ext = os.path.splitext(local_path)[1].lower()

    # For unsupported formats, extract text locally
    if ext not in _GEMINI_SUPPORTED_EXTENSIONS:
        if ext in (".docx", ".doc"):
            print(f"[Gemini] Extracting text from {display_name} (docx not supported for upload)")
            text = _extract_text_from_docx(local_path)
            print(f"[Gemini] Extracted {len(text)} characters of text")
            return text
        else:
            # Try uploading anyway — might work for newer supported types
            pass

    client = get_gemini_client()
    print(f"[Gemini] Uploading file: {display_name}")

    uploaded = client.files.upload(
        file=local_path,
        config=types.UploadFileConfig(display_name=display_name),
    )

    # Wait for processing
    while uploaded.state == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    print(f"[Gemini] File ready: {uploaded.name}")
    return uploaded


def pick_random_themes(count: int = 3) -> list[tuple[str, str]]:
    """Pick N random, non-repeating themes from the G Squared Truths.

    Legacy picker. Kept for any caller that wants pure G Squared Truths.
    For the scheduled Tue/Thu run, use pick_diverse_themes() which adds
    the broader Idea Source pool and enforces category diversity.
    """
    return random.sample(G_SQUARED_TRUTHS, min(count, len(G_SQUARED_TRUTHS)))


def pick_diverse_themes(count: int = 5) -> list[tuple[str, str | None]]:
    """
    Pick N themes from BOTH the G Squared Truths AND the Idea Source pool,
    enforcing category diversity (no two themes from the same category).

    Returns list of (theme_name, theme_description_or_None) tuples.
    G Squared Truths come with a description (the Truth). Idea Source
    topics come with description=None. The Voice Bible carries the POV
    at generation time.

    Why diverse:
      Greg's brief was "stale, static, too narrow." A single random draw
      from a small pool repeats theme families. Drawing one topic per
      category breaks that pattern and forces variety in every run.
    """
    # Group everything by category.
    by_category: dict[str, list[tuple[str, str | None]]] = {}

    # G Squared Truths get their own category bucket so they get represented
    # but don't dominate. One slot per run from this bucket on average.
    by_category["Greg's G Squared Truths"] = [
        (name, desc) for name, desc in G_SQUARED_TRUTHS
    ]

    # Idea Source: each category is its own bucket.
    for category, topics in IDEA_SOURCE_BY_CATEGORY.items():
        by_category[category] = [(topic, None) for topic in topics]

    # If asked for more than we have categories, fall back to with-replacement
    # category sampling (still no two themes from same category within reason).
    available_categories = list(by_category.keys())
    if count > len(available_categories):
        chosen_categories = random.sample(available_categories, len(available_categories))
    else:
        chosen_categories = random.sample(available_categories, count)

    # Pick one theme from each chosen category.
    picks: list[tuple[str, str | None]] = []
    for category in chosen_categories:
        theme = random.choice(by_category[category])
        picks.append(theme)

    return picks


def generate_linkedin_post(
    uploaded_file: types.File | str,
    theme: tuple[str, str | None] | None = None,
) -> tuple[str, str]:
    """
    Generate a single LinkedIn post for a specific theme.

    Theme is a tuple of (theme_name, theme_description_or_None).
    - If theme_description is set (G Squared Truth), the post anchors on
      that specific Truth statement.
    - If theme_description is None (Idea Source topic), the post writes
      Greg's POV on the topic from scratch, using the Voice Bible as the
      sole POV source.

    Returns (theme_name, post_text).
    """
    client = get_gemini_client()

    if theme is None:
        # Default behavior: random G Squared Truth (legacy single-post path)
        theme = random.choice(G_SQUARED_TRUTHS)

    theme_name, theme_description = theme

    # Rotate opening style so posts never all start the same way
    opening_style = random.choice(OPENING_STYLES)

    # Theme block changes based on whether we have a pre-baked Truth statement
    # or just a topic to riff on.
    if theme_description:
        theme_block = (
            f"YOUR ASSIGNED THEME FOR THIS POST:\n"
            f'Theme: "{theme_name}"\n'
            f'Core Truth: "{theme_description}"\n\n'
            f"CRITICAL: This post MUST be about the theme above. '{theme_name}'.\n"
            f"The core idea is: {theme_description}\n"
            f"Do NOT write about generic LinkedIn advice or content tips.\n"
            f"Write about THIS specific G Squared Truth as it applies to sales teams, "
            f"founders, and revenue leaders.\n\n"
        )
    else:
        theme_block = (
            f"YOUR ASSIGNED TOPIC FOR THIS POST:\n"
            f'Topic: "{theme_name}"\n\n'
            f"CRITICAL: This post MUST be about the topic above. '{theme_name}'.\n"
            f"There is no pre-written 'core truth' for this topic. YOU must write\n"
            f"Greg's POV on it, using the VOICE BIBLE and signature phrases above\n"
            f"as your only source of Greg's perspective.\n"
            f"Do NOT write about generic LinkedIn advice or content tips.\n"
            f"Write a sharp, opinionated, experience-driven post about THIS topic\n"
            f"as it applies to sales teams, founders, and revenue leaders.\n"
            f"Anchor on a real failure mode or a specific tactical mistake Greg has\n"
            f"seen, then give the fix in Greg's voice.\n\n"
        )

    prompt = (
        f"{LINKEDIN_PERSONA}\n\n"
        f"{STYLE_GUIDE}\n\n"
        f"{VOICE_BIBLE}\n\n"
        f"{EXAMPLE_POSTS}\n\n"
        f"ASSIGNED OPENING STYLE FOR THIS POST:\n"
        f"{opening_style}\n"
        f"You MUST open using this style. Do not default to a generic hook.\n\n"
        f"{theme_block}"
        "VOICE INTEGRATION REQUIREMENTS:\n"
        "- Weave in 1-2 of Greg's signature phrases naturally (see VOICE BIBLE above) — do NOT force them all in\n"
        "- Reference one of Greg's proprietary frameworks by name if it fits the theme\n"
        "- Write from lived experience, not theory — 'I've seen this in dozens of organizations'\n"
        "- Close with 'Your move.' or a forward-facing challenge question — NEVER a summary\n\n"
        "IMPORTANT CONTENT DIRECTION: Greg is deeply focused on the intersection of "
        "AI and sales leadership right now. Where it fits naturally with the theme, "
        "connect it to how AI is changing sales — prospecting, coaching, forecasting, "
        "CRM, speed of execution. Don't force it, but if the theme touches process, "
        "data, speed, or execution, lean into the AI angle hard.\n\n"
        "ADDITIONAL NON-NEGOTIABLES:\n"
        "- NO exclamation points. Ever.\n"
        "- NO em dashes (—) or en dashes (–). EVER. This is Greg's #1 voice rule. They are the AI fingerprint. Use commas, periods, or colons instead.\n"
        "- NO AI banned vocabulary: delve, leverage, landscape, unlock, harness, holistic, robust, seamless, supercharge, transformative, paradigm, intricate, meticulous, pivotal, crucial, vibrant, cutting-edge, revolutionary, future-proof, scalable, foster, navigate, elevate, optimize, garner, accentuate, empower, redefine, breakthrough, streamline, frictionless, adaptive, effortless, data-driven, insightful, proactive, mission-critical, visionary, disruptive, intuitive, leading-edge, synergize, democratize, accelerate, dynamic, immersive, predictive, integrated, plug-and-play, turnkey, enduring, valuable, captivate, tapestry, realm, journey (metaphorical), trailblazing, pioneering, versatile, showcase, emphasize, highlight (verb).\n"
        "- NO negative-parallelism reframes (FATAL: single biggest AI tell). The banned constructions: 'It's not about X. It's about Y.', 'Not X. Y.', 'Stop X. Start Y.', 'X, not Y' as a standalone reframe, 'X is dead. Y is the future.', 'Less X, more Y.', 'Forget X. Y.', 'This isn't X. This is Y.' Just state what it IS. Delete the negation.\n"
        "- NO brand mark misuse. CASL is registered (™). CASH, REAP, CASC, CASX are PENDING with USPTO. Use ™ NOT ® on the pending marks. Better: write 'The AI Sales Leader certification suite' or 'our CASL program' and skip the symbol entirely.\n"
        "- Use analogies and metaphors to make points stick\n"
        "- Be direct, opinionated, confrontational. Challenge bad behavior.\n"
        "- Use emojis sparingly (1-2 max, only if they add real impact)\n"
        "- NO hashtags. Ever. Do not include any hashtags.\n"
        "- HARD LIMIT: Keep it under 700 characters (~130 words). Greg's actual LinkedIn posts run 125-140 words. The example posts above are the target length. Anything over 700 chars = REWRITE and trim. Tighter is better. Cut paragraphs, not substance.\n\n"
        "Return ONLY the post text, nothing else."
    )

    # Build contents — if it's extracted text, include inline; if File, reference it
    if isinstance(uploaded_file, str):
        contents = [f"REFERENCE MATERIAL:\n\n{uploaded_file[:5000]}\n\n{prompt}"]
    else:
        contents = [uploaded_file, prompt]

    print(f'[Gemini] Generating post for theme: "{theme_name}"...')

    # Quality loop (mirrors seo_engine.generator.generate_article): fresh
    # draft, then surgical repair passes quoting the exact violations, then
    # the SEO engine's deterministic autofix as a last resort. A post that
    # still fails raises, which fails the whole run loud (RUN: FAIL in the
    # log, no email) instead of putting an off-voice draft in Greg's inbox.
    current_contents = contents
    post_text = ""
    problems: list[str] = []
    for attempt in (1, 2, 3):
        response = _call_with_retry(
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=current_contents,
            )
        )
        post_text = _enforce_banned_words(response.text.strip())
        problems = _post_voice_gate(post_text)
        if not problems:
            break
        print(f"[Voice Gate] Attempt {attempt} for '{theme_name}' failed "
              f"({len(problems)} issue(s)): {'; '.join(p[:90] for p in problems[:4])}")
        if attempt == 3:
            break
        repair = (
            "\n\nHERE IS YOUR DRAFT, WHICH FAILED REVIEW:\n" + post_text
            + "\n\nFix ONLY these specific violations by rewriting the "
              "offending sentences. Keep the same theme, opening style, and "
              "everything else exactly as written. Return ONLY the corrected "
              "post text, nothing else:\n- "
            + "\n- ".join(p[:200] for p in problems[:10])
        )
        if isinstance(uploaded_file, str):
            current_contents = [contents[0] + repair]
        else:
            current_contents = [uploaded_file, contents[1] + repair]

    if problems:
        from seo_engine.generator import (_apply_synonym_fix,
                                          _fix_neg_parallelism,
                                          _strip_banned_dashes)
        post_text = _apply_synonym_fix(
            _fix_neg_parallelism(_strip_banned_dashes(post_text)))
        problems = _post_voice_gate(post_text)
    if problems:
        raise ValueError(
            f"Post option '{theme_name}' failed the voice gate after 3 "
            "attempts + autofix. Nothing off-voice ships under Greg's name. "
            "Violations: " + "; ".join(p[:120] for p in problems[:6])
        )

    print(f"[Gemini] Post generated ({len(post_text)} chars). Voice gate: PASS")
    return (theme_name, post_text)


def generate_n_options(
    uploaded_file: types.File | str,
    count: int,
    use_idea_source: bool = True,
) -> list[tuple[str, str]]:
    """
    Generate N LinkedIn post options.

    use_idea_source=True (default) draws from BOTH G Squared Truths and
    the broader Idea Source pool, enforcing category diversity. This is
    the path Greg's scheduled Tue/Thu run uses for variety.

    use_idea_source=False falls back to legacy behavior: pure G Squared
    Truths only, no category diversity guarantee.

    Returns list of (theme_name, post_text) tuples.
    """
    if use_idea_source:
        themes = pick_diverse_themes(count)
    else:
        themes = pick_random_themes(count)

    options = []
    for i, theme in enumerate(themes, 1):
        print(f"\n--- Generating Option {i} of {count} ---")
        result = generate_linkedin_post(uploaded_file, theme=theme)
        options.append(result)
        # Small delay between calls to avoid rate limits
        if i < count:
            time.sleep(2)

    return options


def generate_three_options(uploaded_file: types.File | str) -> list[tuple[str, str]]:
    """
    Generate 3 LinkedIn post options (legacy entry point).
    Kept so older callers and scripts still work.
    Routes through generate_n_options.
    """
    return generate_n_options(uploaded_file, count=3, use_idea_source=False)


def generate_five_options(uploaded_file: types.File | str) -> list[tuple[str, str]]:
    """
    Generate 5 LinkedIn post options across diverse categories.

    This is the Tue + Thu scheduled-run entry point. Pulls from the
    combined G Squared Truths + Idea Source pool, one theme per category,
    so the morning email gives Greg 5 visibly different angles to choose
    from.
    """
    return generate_n_options(uploaded_file, count=5, use_idea_source=True)


def generate_freestyle_post(user_topic: str) -> tuple[str, str]:
    """
    Generate a LinkedIn post about a custom topic (not from the 20 themes).
    Still uses Greg's Staccato voice and style rules.
    Returns (topic_label, post_text).
    """
    client = get_gemini_client()

    # Rotate opening style so posts never all start the same way
    opening_style = random.choice(OPENING_STYLES)

    prompt = (
        f"{LINKEDIN_PERSONA}\n\n"
        f"{STYLE_GUIDE}\n\n"
        f"{VOICE_BIBLE}\n\n"
        f"{EXAMPLE_POSTS}\n\n"
        f"ASSIGNED OPENING STYLE FOR THIS POST:\n"
        f"{opening_style}\n"
        f"You MUST open using this style. Do not default to a generic hook.\n\n"
        f"YOUR TOPIC FOR THIS POST:\n"
        f'The user wants to write about: "{user_topic}"\n\n'
        f"CRITICAL: This post MUST be about the topic above.\n"
        f"Write about it as Greg Grand would — through the lens of sales leadership, "
        f"revenue growth, and building teams. Make it a G Squared Truth even though "
        f"it's not one of the standard 20. Same voice, same fire, same format.\n\n"
        "VOICE INTEGRATION REQUIREMENTS:\n"
        "- Weave in 1-2 of Greg's signature phrases naturally (see VOICE BIBLE above) — do NOT force them all in\n"
        "- Reference one of Greg's proprietary frameworks by name if it fits the topic\n"
        "- Write from lived experience, not theory — 'I've seen this in dozens of organizations'\n"
        "- Close with 'Your move.' or a forward-facing challenge question — NEVER a summary\n\n"
        f"IMPORTANT CONTENT DIRECTION: Greg is deeply focused on the intersection of "
        f"AI and sales leadership right now. Where it fits naturally with the topic, "
        f"connect it to how AI is changing sales — prospecting, coaching, forecasting, "
        f"CRM, speed of execution. Don't force it, but lean into the AI angle where relevant.\n\n"
        "ADDITIONAL NON-NEGOTIABLES:\n"
        "- NO exclamation points. Ever.\n"
        "- NO em dashes (—) or en dashes (–). EVER. This is Greg's #1 voice rule. They are the AI fingerprint. Use commas, periods, or colons instead.\n"
        "- NO AI banned vocabulary: delve, leverage, landscape, unlock, harness, holistic, robust, seamless, supercharge, transformative, paradigm, intricate, meticulous, pivotal, crucial, vibrant, cutting-edge, revolutionary, future-proof, scalable, foster, navigate, elevate, optimize, garner, accentuate, empower, redefine, breakthrough, streamline, frictionless, adaptive, effortless, data-driven, insightful, proactive, mission-critical, visionary, disruptive, intuitive, leading-edge, synergize, democratize, accelerate, dynamic, immersive, predictive, integrated, plug-and-play, turnkey, enduring, valuable, captivate, tapestry, realm, journey (metaphorical), trailblazing, pioneering, versatile, showcase, emphasize, highlight (verb).\n"
        "- NO negative-parallelism reframes (FATAL: single biggest AI tell). The banned constructions: 'It's not about X. It's about Y.', 'Not X. Y.', 'Stop X. Start Y.', 'X, not Y' as a standalone reframe, 'X is dead. Y is the future.', 'Less X, more Y.', 'Forget X. Y.', 'This isn't X. This is Y.' Just state what it IS. Delete the negation.\n"
        "- NO brand mark misuse. CASL is registered (™). CASH, REAP, CASC, CASX are PENDING with USPTO. Use ™ NOT ® on the pending marks. Better: write 'The AI Sales Leader certification suite' or 'our CASL program' and skip the symbol entirely.\n"
        "- Use analogies and metaphors to make points stick\n"
        "- Be direct, opinionated, confrontational. Challenge bad behavior.\n"
        "- Use emojis sparingly (1-2 max, only if they add real impact)\n"
        "- NO hashtags. Ever. Do not include any hashtags.\n"
        "- HARD LIMIT: Keep it under 700 characters (~130 words). Greg's actual LinkedIn posts run 125-140 words. The example posts above are the target length. Anything over 700 chars = REWRITE and trim. Tighter is better. Cut paragraphs, not substance.\n\n"
        "Return ONLY the post text, nothing else."
    )

    print(f'[Gemini] Generating freestyle post about: "{user_topic}"...')
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
    )

    post_text = _enforce_banned_words(response.text.strip())
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
    violations = _detect_banned_patterns(post_text)
    if violations:
        print(f"[Voice DNA] {len(violations)} banned-pattern violation(s) detected in freestyle '{user_topic}':")
        for matched, label in violations:
            print(f"  - {label}: {matched!r}")
        print(f"[Voice DNA] Greg should rewrite the flagged sentences before posting.")
    return (user_topic, post_text)


def generate_post_image(post_text: str) -> bytes | None:
    """
    Use Imagen via Google GenAI to generate an image for the LinkedIn post.
    Returns the raw image bytes (PNG), or None if generation fails.
    """
    client = get_gemini_client()

    # Vary the image style each time for visual freshness
    import random
    styles = [
        "A dramatic cinematic photo of a high-stakes boardroom meeting with dramatic lighting, shallow depth of field, dark moody tones",
        "A bold editorial-style illustration with strong geometric shapes, contrasting colors like navy blue and burnt orange, modern and abstract",
        "A striking overhead photo of a clean desk workspace with chess pieces, coffee cup, and dramatic shadows — no screens or papers visible",
        "A powerful wide-angle photo of a lone figure standing at a crossroads or fork in the road, metaphorical, dramatic sky, golden hour lighting",
        "A stylized 3D render of interconnected gears and pathways forming a machine, dark background with glowing blue and gold accents, abstract",
        "A cinematic silhouette of a business leader looking out a floor-to-ceiling window at a city skyline, dramatic contrast, reflective mood",
        "An aerial drone photo of a complex maze or labyrinth, crisp and high contrast, abstract pattern",
        "A dramatic close-up of hands building with wooden blocks or stacking stones, symbolizing process and construction, warm cinematic tones",
        "A moody black-and-white photo of an empty conference table with a single spotlight, minimalist and powerful",
        "A vibrant abstract painting style image with bold brush strokes in navy, gold, and white, conveying energy and movement",
    ]
    chosen_style = random.choice(styles)

    # Strip hashtags and any text that might bleed into the image
    clean_concept = post_text[:200].split("#")[0].strip()

    prompt = (
        f"{chosen_style}. "
        f"Visually represent this concept: {clean_concept}. "
        "CRITICAL REQUIREMENT: The image must contain ABSOLUTELY ZERO text, "
        "ZERO words, ZERO letters, ZERO numbers, ZERO writing of any kind. "
        "No signs, no labels, no captions, no watermarks, no typography, "
        "no handwriting, no whiteboard writing, no screen text. "
        "Pure visual imagery only — shapes, people, objects, scenes. "
        "If there is a whiteboard or screen in the scene it must be blank. "
        "High quality, LinkedIn-worthy, professional, eye-catching."
    )

    print("[Gemini] Generating post image with Imagen...")
    try:
        # Images are a bonus, not the deliverable. Bound the retry budget hard so a
        # rate-limited or 503 Imagen can never run the job past the task's time limit
        # and get it killed before the email sends. Fixed 2026-06-04 (3->5 images on
        # 2026-05-28 + 40s retries blew past PT10M and killed every run since).
        response = _call_with_retry(
            lambda: client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                ),
            ),
            max_retries=2,
            base_wait=5,
        )

        if response.generated_images:
            print("[Gemini] Image generated successfully")
            return response.generated_images[0].image.image_bytes

    except Exception as e:
        print(f"[Gemini] Image generation failed: {e}")

    print("[Gemini] Warning: No image was generated")
    return None
