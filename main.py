"""
LinkedIn Content Generator — Main Pipeline

Mirrors the Make.com automation workflow:
  1. Dropbox  -> List files in folder
  2. Dropbox  -> Download the latest file
  3. Gemini   -> Upload / extract file content
  4. Gemini   -> Generate 3 LinkedIn post options (each a different G Squared Truth)
  5. Gemini   -> Generate an image for each option
  6. Gmail    -> Email all 3 options for your approval
"""

import os
import sys

from dropbox_client import download_latest_file, list_files
from gemini_client import generate_three_options, generate_post_image, upload_file
from email_client import send_three_options_email


def run_pipeline():
    """Execute the full content-generation pipeline."""

    print("=" * 60)
    print("  LinkedIn Content Generator — 3 Options")
    print("=" * 60)

    # -- Step 1: List files in Dropbox folder
    print("\n[Step 1/6] Listing files in Dropbox folder...")
    files = list_files()
    print(f"  Found {len(files)} file(s):")
    for f in files[:5]:
        print(f"    - {f.name}  ({f.server_modified})")

    # -- Step 2: Download the latest file
    print("\n[Step 2/6] Downloading latest file...")
    local_path, original_name = download_latest_file()
    print(f"  Saved to: {local_path}")

    # -- Step 3: Upload / extract file content
    print("\n[Step 3/6] Processing file for Gemini AI...")
    uploaded_file = upload_file(local_path, original_name)

    # -- Step 4: Generate 3 LinkedIn post options (each a different theme)
    print("\n[Step 4/6] Generating 3 post options (different G Squared Truths)...")
    options = generate_three_options(uploaded_file)

    for i, (theme, text) in enumerate(options, 1):
        print(f"\n{'='*50}")
        print(f"  OPTION {i} — Theme: {theme}")
        print(f"{'='*50}")
        print(text)

    # -- Step 5: Generate an image for each option
    print("\n[Step 5/6] Generating images for each option...")
    images = []
    for i, (theme, text) in enumerate(options, 1):
        print(f"\n  Image {i}/3 ({theme})...")
        img = generate_post_image(text)
        images.append(img)

    # -- Step 6: Email all 3 options
    print("\n[Step 6/6] Sending email with 3 options...")
    subject = f"Pick Your LinkedIn Post — {original_name}"
    send_three_options_email(subject, options, images)

    # -- Cleanup
    os.unlink(local_path)
    print("\n" + "=" * 60)
    print("  Done. Check your inbox — pick 1, 2, or 3.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
