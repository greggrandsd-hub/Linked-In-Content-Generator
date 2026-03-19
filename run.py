"""
LinkedIn Content Generator — All-in-One

Double-click "LinkedIn Content Generator.bat" on your Desktop.
It generates 3 posts, shows them to you, and lets you edit + post your pick.
One click. One flow. Done.
"""

import os
import sys
import tempfile
import subprocess

# Fix Windows console encoding for special characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dropbox_client import download_latest_file, list_files
from gemini_client import generate_three_options, upload_file
from email_client import send_three_options_email
from post import save_options, load_options
from linkedin_client import post_to_linkedin


def open_in_notepad(text: str) -> str:
    """
    Open text in Notepad for editing. Returns the edited text.
    This is the easiest way to edit on Windows — no command line needed.
    """
    # Write to a temp file
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="linkedin_post_",
        delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()

    print("\n  Notepad is opening with your post.")
    print("  Edit it however you want, then SAVE and CLOSE Notepad.")
    print("  Waiting...")

    # Open Notepad and wait for it to close
    subprocess.call(["notepad.exe", tmp.name])

    # Read back the edited text
    with open(tmp.name, "r", encoding="utf-8") as f:
        edited = f.read().strip()

    os.unlink(tmp.name)
    return edited


def run():
    print()
    print("=" * 55)
    print("   LinkedIn Content Generator - G Squared Truths")
    print("=" * 55)

    # -- STEP 1: Generate -----------------------------------
    print("\n  Pulling your latest content from Dropbox...")
    files = list_files()
    local_path, original_name = download_latest_file()

    print(f"  Processing: {original_name}")
    uploaded_file = upload_file(local_path, original_name)

    print("\n  Generating 3 post options (different themes)...\n")
    options = generate_three_options(uploaded_file)

    # Skip image generation — posts speak for themselves
    images = [None, None, None]

    # Save for later use
    save_options(options, images)

    # Send email
    print("\n  Emailing options to you...")
    subject = f"Pick Your LinkedIn Post - {original_name}"
    send_three_options_email(subject, options, images)

    # Cleanup temp file
    os.unlink(local_path)

    # -- STEP 2: Show Options ------------------------------
    print("\n")
    print("=" * 55)
    print("   YOUR 3 OPTIONS - Pick one to post")
    print("=" * 55)

    for i, (theme, text) in enumerate(options, 1):
        print(f"\n---------------------------------------------------")
        print(f"   OPTION {i}: {theme}")
        print(f"---------------------------------------------------")
        print()
        print(text)

    # -- STEP 3: Pick, Edit & Post -------------------------
    print(f"\n---------------------------------------------------")
    print("\n  Options also sent to your email with images.")

    while True:
        print()
        choice = input("  Pick one to post (1, 2, or 3) -- or 'q' to skip: ").strip()

        if choice.lower() == "q":
            print("\n  No problem. Posts saved -- check your email to review.\n")
            input("  Press Enter to close...")
            return

        if choice in ("1", "2", "3"):
            idx = int(choice) - 1
            if idx < len(options):
                break

        print("  Just type 1, 2, or 3 (or 'q' to skip for now)")

    selected_theme, selected_text = options[idx]
    selected_image = images[idx] if idx < len(images) else None

    print(f"\n  You picked Option {choice}: {selected_theme}")

    # -- Ask if they want to edit --------------------------
    print()
    edit_choice = input("  Want to edit it before posting? (y/n): ").strip().lower()

    if edit_choice == "y":
        selected_text = open_in_notepad(selected_text)
        print("\n  Got it. Here's your edited post:")
        print("  ---------------------------------------------------")
        print(f"  {selected_text[:100]}...")
        print("  ---------------------------------------------------")

    # -- Confirm and post ----------------------------------
    print()
    confirm = input("  Post this to LinkedIn right now? (y/n): ").strip().lower()

    if confirm != "y":
        print("\n  No worries. Posts saved -- review in your email and come back anytime.\n")
        input("  Press Enter to close...")
        return

    # -- Post it -------------------------------------------
    print()
    try:
        post_id = post_to_linkedin(selected_text, selected_image)
        print()
        print("=" * 55)
        print("   POSTED TO LINKEDIN")
        print("=" * 55)
        print(f"\n  Theme: {selected_theme}")
        print(f"  Post ID: {post_id}")
        print("\n  Check your LinkedIn profile -- it's live.\n")
    except Exception as e:
        print(f"\n  Error posting: {e}")
        print("  The post is saved in your email -- you can copy/paste it manually.\n")

    input("  Press Enter to close...")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\n  ERROR: {e}")
        try:
            input("\n  Press Enter to close...")
        except EOFError:
            pass
        sys.exit(1)
