"""
LinkedIn Content Generator — Main Pipeline

Mirrors the Make.com automation workflow:
  1. Dropbox  → List files in folder
  2. Dropbox  → Download the latest file
  3. Gemini   → Upload file to Gemini
  4. Gemini   → Generate a LinkedIn post (text)
  5. Gemini   → Generate an accompanying image
  6. Gmail    → Email the post + image to you
"""

import os
import sys

from dropbox_client import download_latest_file, list_files
from gemini_client import generate_linkedin_post, generate_post_image, upload_file
from email_client import send_email


def run_pipeline():
    """Execute the full content-generation pipeline."""

    print("=" * 60)
    print("  LinkedIn Content Generator")
    print("=" * 60)

    # ── Step 1: List files in Dropbox folder ─────────────────────────────
    print("\n[Step 1/6] Listing files in Dropbox folder...")
    files = list_files()
    print(f"  Found {len(files)} file(s):")
    for f in files[:5]:
        print(f"    - {f.name}  ({f.server_modified})")
    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more")

    # ── Step 2: Download the latest file ─────────────────────────────────
    print("\n[Step 2/6] Downloading latest file...")
    local_path, original_name = download_latest_file()
    print(f"  Saved to: {local_path}")

    # ── Step 3: Upload file to Gemini ────────────────────────────────────
    print("\n[Step 3/6] Uploading file to Gemini AI...")
    uploaded_file = upload_file(local_path, original_name)

    # ── Step 4: Generate LinkedIn post text ──────────────────────────────
    print("\n[Step 4/6] Generating LinkedIn post...")
    post_text = generate_linkedin_post(uploaded_file)
    print("\n--- Generated Post ---")
    print(post_text)
    print("--- End of Post ---\n")

    # ── Step 5: Generate accompanying image ──────────────────────────────
    print("[Step 5/6] Generating post image...")
    image_bytes = generate_post_image(post_text)

    # ── Step 6: Send via Gmail ───────────────────────────────────────────
    print("\n[Step 6/6] Sending email...")
    subject = f"LinkedIn Post Draft — {original_name}"
    send_email(subject, post_text, image_bytes)

    # ── Cleanup ──────────────────────────────────────────────────────────
    os.unlink(local_path)
    print("\n" + "=" * 60)
    print("  Pipeline complete! Check your inbox.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
