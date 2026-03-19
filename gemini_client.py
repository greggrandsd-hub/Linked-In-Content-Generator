"""
Steps 3, 4, 5 of the workflow — Google Gemini AI integration.

3. Upload a file to Gemini (or extract text for unsupported formats).
4. Generate a LinkedIn post (text response) based on the file.
5. Generate an accompanying image for the post.
"""

import os
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


def generate_linkedin_post(uploaded_file: types.File | str) -> str:
    """
    Use Gemini to generate a LinkedIn post based on the uploaded content.
    Accepts either a Gemini File object or extracted text string.
    """
    client = get_gemini_client()

    # The 20 G Squared Truths theme bank
    themes = """
THE 20 G SQUARED TRUTHS (use these as the backbone of every post):
1. Strategy vs. Execution: A "perfect" strategy in a PDF is worthless. Real strategy is what happens in the field.
2. The Manager Gap: Your managers are the bridge. If they can't coach the process, your strategy dies.
3. Accountability is Love: Holding people to a standard is how you help them win.
4. Hero Culture: If your company dies because one "star" rep leaves, your process is broken.
5. The Hope Pipeline: "Thinking" a deal will close isn't a forecast. It's a hallucination.
6. CEO Bottlenecks: When the CEO has to sign off on everything, growth stops.
7. Simplicity Scales: If the sales process is too complex for a new hire to learn in a week, it's too complex.
8. Revenue Friction: Find where the money gets stuck in your internal paperwork and kill it.
9. Sales is Math: Activity + Process = Results. Stop guessing.
10. The Echo Chamber: Being the smartest person in the room is a liability.
11. Hiring for Character: You can teach sales skills. You can't teach work ethic.
12. The "Niceness" Trap: Being "nice" and avoiding hard conversations is actually selfish.
13. Activity vs. Progress: Being busy isn't the same as moving the needle.
14. Process Discipline: Doing the "boring" basics every single day is the only way to scale.
15. The Frontline Reality: If the CEO hasn't talked to a customer in 6 months, the strategy is wrong.
16. Legacy Rot: "We've always done it this way" is the most expensive phrase in business.
17. Ownership: If everyone is responsible, no one is responsible.
18. Data over Drama: Stop making decisions based on feelings. Look at the metrics.
19. The Coaching Deficit: Most managers report the news; they don't make the news better through coaching.
20. Speed of Execution: The fastest company usually wins. Friction is the enemy of speed.
"""

    example_posts = """
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

    prompt = (
        f"{LINKEDIN_PERSONA}\n\n"
        f"{themes}\n\n"
        f"{example_posts}\n\n"
        "Based on the attached file, create an engaging LinkedIn post.\n\n"
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
        "- Do NOT sound generic, corporate, or motivational-poster-ish\n"
        "- Connect the post to one of the 20 G Squared Truths themes above\n\n"
        "Return ONLY the post text, nothing else."
    )

    # Build contents — if it's extracted text, include inline; if File, reference it
    if isinstance(uploaded_file, str):
        contents = [f"SOURCE CONTENT FROM FILE:\n\n{uploaded_file}\n\n{prompt}"]
    else:
        contents = [uploaded_file, prompt]

    print("[Gemini] Generating LinkedIn post text...")
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
    )

    post_text = response.text.strip()
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
    return post_text


def generate_post_image(post_text: str) -> bytes | None:
    """
    Use Imagen via Google GenAI to generate an image for the LinkedIn post.
    Returns the raw image bytes (PNG), or None if generation fails.
    """
    client = get_gemini_client()

    prompt = (
        "A professional, clean, visually striking image for a LinkedIn post about: "
        f"{post_text[:300]}. "
        "Style: modern, bold, business-appropriate color palette with blues and whites. "
        "Abstract or conceptual — no text, no people's faces, no logos. "
        "Think: clean infographic style, geometric shapes, professional atmosphere."
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
