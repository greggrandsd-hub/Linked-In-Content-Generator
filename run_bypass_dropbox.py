"""
Temporary bypass: Dropbox token expired.
Uses local reference content (LI_Post_Examples docx) as source material,
then runs Gemini + email steps normally.
"""
import sys
import os

# Ensure we can import project modules
sys.path.insert(0, os.path.dirname(__file__))

from gemini_client import generate_three_options, generate_post_image, _extract_text_from_docx
from email_client import send_three_options_email
from post import save_options


def run_pipeline():
    print("=" * 60)
    print("  LinkedIn Content Generator — 3 Options (Dropbox bypass)")
    print("=" * 60)

    # Use local reference docx instead of Dropbox
    local_ref = os.path.join(os.path.dirname(__file__), "LI_Post_Examples_For_Training_Model.docx")
    original_name = "LI_Post_Examples_For_Training_Model.docx"

    print(f"\n[Step 1/6] Using local reference file: {original_name}")
    print("[Step 2/6] Skipped (Dropbox token expired — using local file)")

    print("\n[Step 3/6] Extracting content from local file...")
    reference_text = _extract_text_from_docx(local_ref)
    print(f"  Extracted {len(reference_text)} characters")

    print("\n[Step 4/6] Generating 3 post options (different G Squared Truths)...")
    options = generate_three_options(reference_text)

    for i, (theme, text) in enumerate(options, 1):
        print(f"\n{'='*50}")
        print(f"  OPTION {i} — Theme: {theme}")
        print(f"{'='*50}")
        print(text)

    print("\n[Step 5/6] Generating images for each option...")
    images = []
    for i, (theme, text) in enumerate(options, 1):
        print(f"\n  Image {i}/3 ({theme})...")
        img = generate_post_image(text)
        images.append(img)

    save_options(options, images)

    print("\n[Step 6/6] Sending email with 3 options...")
    subject = f"Pick Your LinkedIn Post — {original_name} [Scheduled Run]"
    send_three_options_email(subject, options, images)

    print("\n" + "=" * 60)
    print("  Done. Check your inbox — pick 1, 2, or 3.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
