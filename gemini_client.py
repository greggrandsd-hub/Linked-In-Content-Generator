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


def generate_linkedin_post(
    uploaded_file: types.File | str,
    theme: tuple[str, str] | None = None,
) -> tuple[str, str]:
    """
    Generate a single LinkedIn post for a specific G Squared Truth theme.
    Returns (theme_name, post_text).
    """
    client = get_gemini_client()

    if theme is None:
        theme = random.choice(G_SQUARED_TRUTHS)

    theme_name, theme_description = theme

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
        f"founders, and revenue leaders.\n\n"
        "Use any relevant context from the reference material below to enrich "
        "the post, but the THEME must drive the post.\n\n"
        "STACCATO STYLE RULES (non-negotiable):\n"
        "- Hook must be under 10 words\n"
        "- One idea per line. Double space between every line.\n"
        "- Structure: Hook -> The Problem -> The Fix -> One clear question at the end\n"
        "- NO exclamation points. Ever.\n"
        "- NO AI words: delve, leverage, landscape, unlock, harness, elevate, foster, navigate, robust\n"
        "- Use em dashes (—) for dramatic pauses\n"
        "- Use analogies and metaphors to make points stick\n"
        "- Be direct, opinionated, confrontational — challenge bad behavior\n"
        "- Use emojis sparingly (1-2 max, only if they add real impact)\n"
        "- Include 3-5 relevant hashtags at the very end\n"
        "- Keep it under 1300 characters\n"
        "- Do NOT sound generic, corporate, or motivational-poster-ish\n\n"
        "Return ONLY the post text, nothing else."
    )

    # Build contents — if it's extracted text, include inline; if File, reference it
    if isinstance(uploaded_file, str):
        contents = [f"REFERENCE MATERIAL:\n\n{uploaded_file[:5000]}\n\n{prompt}"]
    else:
        contents = [uploaded_file, prompt]

    print(f'[Gemini] Generating post for theme: "{theme_name}"...')
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
    )

    post_text = response.text.strip()
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
    return (theme_name, post_text)


def generate_three_options(uploaded_file: types.File | str) -> list[tuple[str, str]]:
    """
    Generate 3 LinkedIn post options, each based on a different G Squared Truth.
    Returns list of (theme_name, post_text) tuples.
    """
    themes = pick_random_themes(3)
    options = []

    for i, theme in enumerate(themes, 1):
        print(f"\n--- Generating Option {i} of 3 ---")
        result = generate_linkedin_post(uploaded_file, theme=theme)
        options.append(result)
        # Small delay between calls to avoid rate limits
        if i < 3:
            time.sleep(2)

    return options


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
        "A striking overhead photo of a clean desk workspace with strategic elements — chess pieces, a whiteboard with diagrams, coffee, dramatic shadows",
        "A powerful wide-angle photo of a lone figure standing at a crossroads or fork in the road, metaphorical, dramatic sky, golden hour lighting",
        "A stylized 3D render of interconnected gears, arrows, and pathways forming a revenue machine, dark background with glowing blue and gold accents",
        "A photojournalistic shot of a coach drawing plays on a whiteboard, intense focus, locker room energy, black and white with selective color",
        "An aerial drone photo of a complex maze or labyrinth, symbolizing complexity vs. simplicity, crisp and high contrast",
        "A dramatic close-up of hands building something — blocks, a bridge, a structure — symbolizing process and construction, warm tones",
    ]
    chosen_style = random.choice(styles)

    prompt = (
        f"{chosen_style}. "
        f"The image should visually represent this concept: {post_text[:200]}. "
        "NO text, NO words, NO letters, NO logos in the image. "
        "High quality, LinkedIn-worthy, professional, eye-catching in a social feed."
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
