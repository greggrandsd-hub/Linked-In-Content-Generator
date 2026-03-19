"""
Easy LinkedIn Poster — Pick your favorite option and post it.

Just double-click "Post to LinkedIn.bat" on your Desktop, or run:
    python post.py
"""

import json
import os
import sys

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from linkedin_client import post_to_linkedin
from gemini_client import generate_post_image

LAST_RUN_FILE = os.path.join(os.path.dirname(__file__), ".last_run.json")


def save_options(options: list[tuple[str, str]], images: list[bytes | None]) -> None:
    """Save the last generated options so they can be posted later."""
    data = {
        "options": [{"theme": t, "text": txt} for t, txt in options],
    }
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Save images separately (binary)
    for i, img in enumerate(images):
        if img:
            img_path = os.path.join(os.path.dirname(__file__), f".last_image_{i+1}.png")
            with open(img_path, "wb") as f:
                f.write(img)


def load_options() -> tuple[list[dict], list[bytes | None]]:
    """Load the last generated options."""
    if not os.path.exists(LAST_RUN_FILE):
        print("\nNo saved options found.")
        print("Run the generator first (double-click 'Generate Posts.bat')")
        input("\nPress Enter to exit...")
        sys.exit(1)

    with open(LAST_RUN_FILE, encoding="utf-8") as f:
        data = json.load(f)

    images = []
    for i in range(len(data["options"])):
        img_path = os.path.join(os.path.dirname(__file__), f".last_image_{i+1}.png")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                images.append(f.read())
        else:
            images.append(None)

    return data["options"], images


def main():
    print("=" * 50)
    print("  Post to LinkedIn — Pick Your Favorite")
    print("=" * 50)

    options, images = load_options()

    # Show the options
    for i, opt in enumerate(options, 1):
        print(f"\n{'—'*50}")
        print(f"  OPTION {i}: {opt['theme']}")
        print(f"{'—'*50}")
        # Show first 3 lines as preview
        lines = [l for l in opt["text"].split("\n") if l.strip()]
        for line in lines[:4]:
            print(f"  {line}")
        if len(lines) > 4:
            print(f"  ... ({len(lines) - 4} more lines)")

    print(f"\n{'—'*50}")

    # Ask for choice
    while True:
        choice = input("\nWhich option to post? (1, 2, or 3 — or 'q' to quit): ").strip()
        if choice.lower() == "q":
            print("Cancelled. Nothing was posted.")
            input("\nPress Enter to exit...")
            return
        if choice in ("1", "2", "3"):
            idx = int(choice) - 1
            if idx < len(options):
                break
        print("Please enter 1, 2, or 3 (or 'q' to quit)")

    selected = options[idx]
    selected_image = images[idx] if idx < len(images) else None

    print(f"\nYou picked Option {choice}: {selected['theme']}")
    print("\nFull post:")
    print("—" * 50)
    print(selected["text"])
    print("—" * 50)

    confirm = input("\nPost this to LinkedIn? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled. Nothing was posted.")
        input("\nPress Enter to exit...")
        return

    # Post it
    try:
        post_id = post_to_linkedin(selected["text"], selected_image)
        print(f"\nPosted to LinkedIn successfully.")
        print(f"Post ID: {post_id}")
    except Exception as e:
        print(f"\nError posting: {e}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
