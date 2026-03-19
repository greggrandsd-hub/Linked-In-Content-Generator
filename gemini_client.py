"""
Steps 3, 4, 5 of the workflow — Google Gemini AI integration.

3. Upload a file to Gemini.
4. Generate a LinkedIn post (text response) based on the file.
5. Generate an accompanying image for the post.
"""

import time

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, LINKEDIN_PERSONA


def get_gemini_client() -> genai.Client:
    """Return an authenticated Gemini client."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")
    return genai.Client(api_key=GEMINI_API_KEY)


def upload_file(local_path: str, display_name: str) -> types.File:
    """
    Upload a file to Gemini so it can be referenced in prompts.
    """
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


def generate_linkedin_post(uploaded_file: types.File) -> str:
    """
    Use Gemini to generate a LinkedIn post based on the uploaded content.
    """
    client = get_gemini_client()

    prompt = (
        f"{LINKEDIN_PERSONA}\n\n"
        "Based on the attached file, create an engaging LinkedIn post. "
        "The post should:\n"
        "- Start with a hook that grabs attention\n"
        "- Share a key insight or lesson from the content\n"
        "- Be authentic and conversational\n"
        "- End with a question or call-to-action to drive engagement\n"
        "- Include 3-5 relevant hashtags at the end\n\n"
        "Return ONLY the post text, nothing else."
    )

    print("[Gemini] Generating LinkedIn post text...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[uploaded_file, prompt],
    )

    post_text = response.text.strip()
    print(f"[Gemini] Post generated ({len(post_text)} chars)")
    return post_text


def generate_post_image(post_text: str) -> bytes | None:
    """
    Use Gemini to generate an image that complements the LinkedIn post.
    Returns the raw image bytes (PNG), or None if generation fails.
    """
    client = get_gemini_client()

    prompt = (
        "Generate a professional, clean, visually appealing image suitable "
        "for a LinkedIn post. The image should complement this post:\n\n"
        f"{post_text}\n\n"
        "Style: modern, professional, minimal text overlay, business-appropriate "
        "color palette. Do NOT include any text in the image."
    )

    print("[Gemini] Generating post image...")
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # Extract image from response
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            print("[Gemini] Image generated successfully")
            return part.inline_data.data

    print("[Gemini] Warning: No image was generated")
    return None
