"""
LinkedIn Content Generator. Main Pipeline.

Pipeline:
  1. Local    -> Read reference content from Git Test Folder
  2. Gemini   -> Generate 5 LinkedIn post options across diverse categories
                 (mix of G Squared Truths + broader Idea Source pool)
  3. Gemini   -> Generate an image for each option
  4. Gmail    -> Email all 5 options for Greg's approval

No external dependencies (Dropbox removed). All source material is local.
"""

import os
import sys

from gemini_client import generate_five_options, generate_post_image, _extract_text_from_docx
from email_client import send_n_options_email
from post import save_options


# Bumped from 3 to 5 on 2026-05-28 per Greg's brief: posts were
# "stale, static, too narrow." 5 + broader Idea Source pool fixes that.
OPTIONS_PER_RUN = 5

# Images capped at 3 (Greg 2026-06-04): keep the 5 post options for variety, but only
# generate 3 images so a flaky image API can never be the bottleneck. Options beyond
# this ship text-only. Bump if you want more.
IMAGE_LIMIT = 3


def run_pipeline():
    """Execute the full content-generation pipeline."""

    print("=" * 60)
    print(f"  LinkedIn Content Generator. {OPTIONS_PER_RUN} Options")
    print("=" * 60)

    # -- Step 1: Load local reference content
    print("\n[Step 1/5] Loading local reference content...")
    local_ref = os.path.join(os.path.dirname(__file__), "LI_Post_Examples_For_Training_Model.docx")
    reference_text = _extract_text_from_docx(local_ref)
    print(f"  Loaded {len(reference_text)} characters from training examples")

    # -- Step 2: Generate N LinkedIn post options across diverse categories
    print(f"\n[Step 2/5] Generating {OPTIONS_PER_RUN} post options across diverse categories...")
    options = generate_five_options(reference_text)

    for i, (theme, text) in enumerate(options, 1):
        print(f"\n{'='*50}")
        print(f"  OPTION {i}. Theme: {theme}")
        print(f"{'='*50}")
        print(text)

    # -- Step 3: Generate images, capped at IMAGE_LIMIT. Extra options ship text-only.
    print(f"\n[Step 3/5] Generating up to {IMAGE_LIMIT} images...")
    images = []
    for i, (theme, text) in enumerate(options, 1):
        if i <= IMAGE_LIMIT:
            print(f"\n  Image {i}/{IMAGE_LIMIT} ({theme})...")
            images.append(generate_post_image(text))
        else:
            images.append(None)

    # -- Save options for easy posting later
    save_options(options, images)

    # -- Step 4: Email all N options
    print(f"\n[Step 4/5] Sending email with {OPTIONS_PER_RUN} options...")
    subject = "Pick Your LinkedIn Post. Scheduled Run"
    send_n_options_email(subject, options, images)

    pick_range = ", ".join(str(i) for i in range(1, OPTIONS_PER_RUN + 1))
    print("\n" + "=" * 60)
    print(f"  Done. Check your inbox. pick {pick_range}.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
