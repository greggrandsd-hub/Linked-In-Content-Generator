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

from config import GEMINI_API_KEY, LINKEDIN_PERSONA

# Supported MIME types for Gemini file upload
_GEMINI_SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".csv", ".html", ".xml", ".json",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp3", ".wav", ".mp4", ".mpeg", ".mov", ".avi",
}

# ── The 20 AI Sales Leadership Program Themes ───────────────────────────────
AI_SALES_LEADERSHIP_THEMES = [
    ('AI Won\'t Replace Sales Leaders — It Exposes Weak Ones', 'Leaders who can\'t coach, think strategically, or build process will be replaced — not by AI, but by the leaders who use AI.'),
    ('The Gut-Check Problem', 'Most sales leaders make million-dollar decisions on gut feel. AI gives you the data to replace gut with certainty.'),
    ('Speed to Signal', 'Your competitors using AI get market signals weeks before you do. That lag costs pipeline, and it costs deals.'),
    ('The AI Adoption Gap', 'There are two kinds of sales leaders right now: those building AI-powered teams, and those about to be disrupted by them.'),
    ('AI as a Coaching Multiplier', 'One manager can\'t coach 12 reps deeply. AI can surface every call, flag every missed question, and score every conversation.'),
    ('Garbage In, Garbage Out', 'AI doesn\'t fix a broken sales process — it amplifies it. Get your fundamentals right before you layer in AI.'),
    ('The Human Edge', 'AI handles research, routing, and repetition. Humans handle trust, nuance, and judgment. Know which is which.'),
    ('Personalization at Scale', 'Your buyer expects you to know them before you call. AI makes this possible at scale. Ignoring it is leaving deals on the table.'),
    ('The CRM Graveyard', 'Most CRMs are where data goes to die. AI changes that — but only if your team actually uses the system.'),
    ('Fear vs. Curiosity', 'Sales leaders who fear AI spend their energy defending the past. Leaders who are curious about AI spend their energy building the future.'),
    ('AI is Not a Magic Wand', 'You still need a clear ICP, a repeatable process, and managers who coach. AI amplifies what you already have — nothing more.'),
    ('The Training Gap', 'You can\'t send your team into an AI-driven sales environment without training them. That\'s not a strategy — that\'s malpractice.'),
    ('Predictive Pipeline', 'The best sales leaders will soon know which deals will close before the rep does. That\'s not magic — it\'s AI-powered pattern recognition.'),
    ('The 70/30 Rule', 'AI handles 70% of the research, prep, and follow-up. Your rep uses that freed time to actually sell. That\'s the new playbook.'),
    ('Authenticity in the Age of AI', 'Buyers can smell AI-generated outreach from a mile away. Use AI for research and prep. Use humans for relationships and trust.'),
    ('Meeting Intelligence', 'Every sales call is a goldmine of competitive intelligence, coaching moments, and buying signals. AI mines it. Most leaders ignore it.'),
    ('The New Sales Stack', 'It\'s not about having the most tools — it\'s about having the right AI-powered workflow that your team actually uses consistently.'),
    ('Change or Be Changed', 'The sales playbook that worked in 2020 is obsolete. AI-native competitors are rewriting the rules. The question is who is writing yours.'),
    ('Forecasting Finally Works', 'AI-powered forecasting removes the wishful thinking from your pipeline review. Clean data in, accurate projections out — no more hallucinated pipelines.'),
    ('Leadership in the Age of AI', 'The best AI sales leaders aren\'t technologists. They are strategists who know how to amplify human talent with intelligent tools.'),
]

AI_PROGRAM_PERSONA = (
    "You are Greg Grand — a Vistage Speaker and sales leadership expert who runs "
    "The AI Sales Leadership Program at theaisalesleader.com. "
    "You help CEOs, founders, and sales leaders understand how to use AI to build "
    "faster, smarter revenue teams. "
    "Your content is direct, opinionated, and grounded in real sales leadership experience. "
    "You are not a tech evangelist — you are a results-driven sales leader who has seen "
    "what works and what doesn't when AI meets the sales floor."
)

AI_PROGRAM_CTA = "theaisalesleader.com"

# ── The 20 G Squared Truths ─────────────────────────────────────────────────
G_SQUARED_TRUTHS = [
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
]

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
    """Pick N random, non-repeating themes from the G Squared Truths."""
    return random.sample(G_SQUARED_TRUTHS, min(count, len(G_SQUARED_TRUTHS)))


_LENGTH_SPECS = {
    "short": (
        "LENGTH: SHORT (300-450 characters total)\n"
        "- Hook under 8 words — make it sting\n"
        "- 5-7 lines total. One idea per line. Every word earns its place.\n"
        "- Structure: Sharp hook → One brutal truth → One concrete action → One direct question\n"
        "- No filler, no setup, no warming up — hit hard and get out\n"
    ),
    "medium": (
        "LENGTH: MEDIUM (700-950 characters total)\n"
        "- Hook under 10 words\n"
        "- 12-16 lines total. One idea per line.\n"
        "- Structure: Hook → The Problem (2-3 lines) → The Fix (3-4 specific points) → Question\n"
        "- Room for one sharp analogy or real-world example\n"
        "- Enough depth to be useful, tight enough to hold attention\n"
    ),
    "long": (
        "LENGTH: LONG (1100-1400 characters total)\n"
        "- Hook under 10 words\n"
        "- 20-28 lines total. One idea per line.\n"
        "- Structure: Hook → Context/Story (2-3 lines) → The Problem (3-4 lines) → "
        "Detailed Solution with 4-6 numbered or bulleted steps → Challenge to the reader\n"
        "- Rich with specifics: name the behaviors, name the mistakes, name the fixes\n"
        "- Can include a mini-list (use dashes, not bullets) for the fix steps\n"
        "- End with a question that makes them think, not just agree\n"
    ),
}


def generate_linkedin_post(
    uploaded_file: types.File | str,
    theme: tuple[str, str] | None = None,
    length: str = "medium",
) -> tuple[str, str]:
    """
    Generate a single LinkedIn post for a specific G Squared Truth theme.
    length: 'short', 'medium', or 'long'
    Returns (theme_name, post_text).
    """
    client = get_gemini_client()

    if theme is None:
        theme = random.choice(G_SQUARED_TRUTHS)

    theme_name, theme_description = theme
    length_spec = _LENGTH_SPECS.get(length, _LENGTH_SPECS["medium"])

    prompt = (
        f"{LINKEDIN_PERSONA}\n\n"
        f"{EXAMPLE_POSTS}\n\n"
        f"YOUR ASSIGNED THEME FOR THIS POST:\n"
        f'Theme: "{theme_name}"\n'
        f'Core Truth: "{theme_description}"\n\n'
        f"CRITICAL: This post MUST be about the theme above — '{theme_name}'.\n"
        f"The core idea is: {theme_description}\n"
        f"Do NOT write about generic LinkedIn advice or content tips.\n"
        f"Write about THIS specific G Squared Truth as it applies to sales teams, "
        f"founders, and revenue leaders. Be specific — name the real behaviors, "
        f"the real mistakes, the real consequences. Give concrete examples.\n\n"
        "Use any relevant context from the reference material to enrich the post, "
        "but the THEME must drive it.\n\n"
        f"{length_spec}\n"
        "STACCATO STYLE RULES (non-negotiable):\n"
        "- One idea per line. Double space between every line.\n"
        "- NO exclamation points. Ever.\n"
        "- NO AI words: delve, leverage, landscape, unlock, harness, elevate, foster, navigate, robust\n"
        "- Use em dashes (—) for dramatic pauses\n"
        "- Use analogies and metaphors to make points stick\n"
        "- Be direct, opinionated, confrontational — challenge bad behavior\n"
        "- Use emojis sparingly (1-2 max, only if they add real impact)\n"
        "- NO hashtags. Ever. Do not include any hashtags.\n"
        "- Do NOT sound generic, corporate, or motivational-poster-ish\n\n"
        "Return ONLY the post text, nothing else."
    )

    # Build contents — if it's extracted text, include inline; if File, reference it
    if isinstance(uploaded_file, str):
        contents = [f"REFERENCE MATERIAL:\n\n{uploaded_file[:5000]}\n\n{prompt}"]
    else:
        contents = [uploaded_file, prompt]

    print(f'[Gemini] Generating {length} post for theme: "{theme_name}"...')
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
    )

    post_text = response.text.strip()
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
    return (theme_name, post_text)


def generate_three_options(uploaded_file: types.File | str) -> list[tuple[str, str, str]]:
    """
    Generate 3 LinkedIn post options — Short, Medium, Long — each on a different theme.
    Returns list of (theme_name, post_text, length_label) tuples.
    """
    themes = pick_random_themes(3)
    lengths = ["short", "medium", "long"]
    options = []

    for i, (theme, length) in enumerate(zip(themes, lengths), 1):
        print(f"\n--- Generating {length.upper()} Option {i} of 3 ---")
        theme_name, post_text = generate_linkedin_post(uploaded_file, theme=theme, length=length)
        options.append((theme_name, post_text, length))
        if i < 3:
            time.sleep(2)

    return options


def generate_freestyle_post(user_topic: str) -> tuple[str, str]:
    """
    Generate a LinkedIn post about a custom topic (not from the 20 themes).
    Still uses Greg's Staccato voice and style rules.
    Returns (topic_label, post_text).
    """
    client = get_gemini_client()

    prompt = (
        f"{LINKEDIN_PERSONA}\n\n"
        f"{EXAMPLE_POSTS}\n\n"
        f"YOUR TOPIC FOR THIS POST:\n"
        f'The user wants to write about: "{user_topic}"\n\n'
        f"CRITICAL: This post MUST be about the topic above.\n"
        f"Write about it as Greg Grand would — through the lens of sales leadership, "
        f"revenue growth, and building teams. Make it a G Squared Truth even though "
        f"it's not one of the standard 20. Same voice, same fire, same format.\n"
        f"Be specific — name the real behaviors, the real mistakes, the real consequences. "
        f"Give concrete examples. Don't stay at 30,000 feet.\n\n"
        f"{_LENGTH_SPECS['medium']}\n"
        "STACCATO STYLE RULES (non-negotiable):\n"
        "- One idea per line. Double space between every line.\n"
        "- Structure: Hook -> The Problem -> The Fix -> One clear question at the end\n"
        "- NO exclamation points. Ever.\n"
        "- NO AI words: delve, leverage, landscape, unlock, harness, elevate, foster, navigate, robust\n"
        "- Use em dashes (—) for dramatic pauses\n"
        "- Use analogies and metaphors to make points stick\n"
        "- Be direct, opinionated, confrontational — challenge bad behavior\n"
        "- Use emojis sparingly (1-2 max, only if they add real impact)\n"
        "- NO hashtags. Ever. Do not include any hashtags.\n"
        "- Do NOT sound generic, corporate, or motivational-poster-ish\n\n"
        "Return ONLY the post text, nothing else."
    )

    print(f'[Gemini] Generating freestyle post about: "{user_topic}"...')
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
    )

    post_text = response.text.strip()
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
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
        response = _call_with_retry(
            lambda: client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                ),
            )
        )

        if response.generated_images:
            print("[Gemini] Image generated successfully")
            return response.generated_images[0].image.image_bytes

    except Exception as e:
        print(f"[Gemini] Image generation failed: {e}")

    print("[Gemini] Warning: No image was generated")
    return None


# ── AI Sales Leadership Program Generation ──────────────────────────────────

def pick_random_ai_program_themes(count: int = 3) -> list[tuple[str, str]]:
    """Pick N random, non-repeating themes from the AI Sales Leadership themes."""
    return random.sample(AI_SALES_LEADERSHIP_THEMES, min(count, len(AI_SALES_LEADERSHIP_THEMES)))


def generate_ai_program_post(
    theme: tuple[str, str] | None = None,
    length: str = "medium",
) -> tuple[str, str]:
    """
    Generate a single LinkedIn post for the AI Sales Leadership Program.
    length: 'short', 'medium', or 'long'
    Returns (theme_name, post_text).
    """
    client = get_gemini_client()

    if theme is None:
        theme = random.choice(AI_SALES_LEADERSHIP_THEMES)

    theme_name, theme_description = theme
    length_spec = _LENGTH_SPECS.get(length, _LENGTH_SPECS["medium"])

    prompt = (
        f"{AI_PROGRAM_PERSONA}\n\n"
        f"{EXAMPLE_POSTS}\n\n"
        f"YOUR ASSIGNED THEME FOR THIS POST:\n"
        f'Theme: "{theme_name}"\n'
        f'Core Truth: "{theme_description}"\n\n'
        f"CRITICAL: This post MUST be about the theme above — '{theme_name}'.\n"
        f"The core idea is: {theme_description}\n"
        f"This is content for The AI Sales Leadership Program. "
        f"Write through the lens of AI meeting the sales floor — what it means for "
        f"sales leaders, their teams, their pipeline, and their competitive position. "
        f"Be specific — name the real behaviors, the real mistakes, the real consequences. "
        f"Give concrete examples of what good and bad looks like in practice.\n\n"
        f"OPTIONAL CTA: You may (not required every post) end with a soft reference to "
        f"{AI_PROGRAM_CTA} — only if it fits naturally. Never force it.\n\n"
        f"{length_spec}\n"
        "STACCATO STYLE RULES (non-negotiable):\n"
        "- One idea per line. Double space between every line.\n"
        "- NO exclamation points. Ever.\n"
        "- NO AI words: delve, leverage, landscape, unlock, harness, elevate, foster, navigate, robust\n"
        "- Use em dashes (—) for dramatic pauses\n"
        "- Use analogies and metaphors to make points stick\n"
        "- Be direct, opinionated, confrontational — challenge bad behavior\n"
        "- Use emojis sparingly (1-2 max, only if they add real impact)\n"
        "- NO hashtags. Ever. Do not include any hashtags.\n"
        "- Do NOT sound generic, corporate, or motivational-poster-ish\n\n"
        "Return ONLY the post text, nothing else."
    )

    print(f'[Gemini] Generating {length} AI Program post for theme: "{theme_name}"...')
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
    )

    post_text = response.text.strip()
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
    return (theme_name, post_text)


def generate_three_ai_program_options() -> list[tuple[str, str, str]]:
    """
    Generate 3 LinkedIn post options for the AI Sales Leadership Program —
    Short, Medium, Long — each on a different theme.
    Returns list of (theme_name, post_text, length_label) tuples.
    """
    themes = pick_random_ai_program_themes(3)
    lengths = ["short", "medium", "long"]
    options = []

    for i, (theme, length) in enumerate(zip(themes, lengths), 1):
        print(f"\n--- Generating AI Program {length.upper()} Option {i} of 3 ---")
        theme_name, post_text = generate_ai_program_post(theme=theme, length=length)
        options.append((theme_name, post_text, length))
        if i < 3:
            time.sleep(2)

    return options
