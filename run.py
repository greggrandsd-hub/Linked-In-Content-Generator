"""
LinkedIn Content Generator — All-in-One

Double-click "LinkedIn Content Generator.bat" on your Desktop.
Generate posts, save your favorites, edit, and post — all in one place.
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
from gemini_client import generate_three_options, generate_post_image, upload_file
from email_client import send_three_options_email
from post import save_options, load_options
from linkedin_client import post_to_linkedin
import saved_posts


def open_in_notepad(text: str) -> str:
    """Open text in Notepad for editing. Returns the edited text."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="linkedin_post_",
        delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()

    print("\n  Notepad is opening with your post.")
    print("  Edit it however you want, then SAVE and CLOSE Notepad.")
    print("  Waiting...")

    subprocess.call(["notepad.exe", tmp.name])

    with open(tmp.name, "r", encoding="utf-8") as f:
        edited = f.read().strip()

    os.unlink(tmp.name)
    return edited


def save_image_for_later(image_bytes: bytes | None, theme: str) -> str | None:
    """Save image bytes to a file for later posting. Returns the file path."""
    if not image_bytes:
        return None
    safe_name = theme.replace(" ", "_").replace('"', "").replace("'", "")[:30]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".saved_images", f"{safe_name}_{id(image_bytes)}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


def load_image(path: str | None) -> bytes | None:
    """Load image bytes from a saved file path."""
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


def show_main_menu():
    """Show the main menu and return choice."""
    saved_count = saved_posts.count()
    saved_label = f"  2. Post a saved favorite ({saved_count} saved)" if saved_count else "  2. Post a saved favorite (none yet)"

    print()
    print("=" * 55)
    print("   LinkedIn Content Generator - G Squared Truths")
    print("=" * 55)
    print()
    print("  1. Generate 3 new posts")
    print(saved_label)
    print("  3. Quit")
    print()

    while True:
        choice = input("  What do you want to do? (1, 2, or 3): ").strip()
        if choice in ("1", "2", "3"):
            return choice
        print("  Just type 1, 2, or 3")


def handle_generate():
    """Generate 3 new posts, let user save/post them."""
    print("\n  Pulling your latest content from Dropbox...")
    files = list_files()
    local_path, original_name = download_latest_file()

    print(f"  Processing: {original_name}")
    uploaded_file = upload_file(local_path, original_name)

    print("\n  Generating 3 post options (different themes)...\n")
    options = generate_three_options(uploaded_file)

    print("\n  Creating images for each option...")
    images = []
    for i, (theme, text) in enumerate(options, 1):
        print(f"    Image {i}/3...")
        img = generate_post_image(text)
        images.append(img)

    # Save for the post.py loader
    save_options(options, images)

    # Send email
    print("\n  Emailing options to you...")
    subject = f"Pick Your LinkedIn Post - {original_name}"
    send_three_options_email(subject, options, images)

    # Cleanup temp file
    os.unlink(local_path)

    # Show all 3
    print("\n")
    print("=" * 55)
    print("   YOUR 3 OPTIONS")
    print("=" * 55)

    for i, (theme, text) in enumerate(options, 1):
        print(f"\n---------------------------------------------------")
        print(f"   OPTION {i}: {theme}")
        print(f"---------------------------------------------------")
        print()
        print(text)

    print(f"\n---------------------------------------------------")
    print("\n  Options also sent to your email with images.")

    # Let user act on each option
    while True:
        print()
        print("  What next?")
        print("    Type 1, 2, or 3 to POST that option now")
        print("    Type s1, s2, or s3 to SAVE one for later")
        print("    Type 'done' when finished")
        print()
        action = input("  Your choice: ").strip().lower()

        if action == "done":
            print("\n  All set.")
            return

        # Save for later
        if action in ("s1", "s2", "s3"):
            idx = int(action[1]) - 1
            if idx < len(options):
                theme, text = options[idx]
                img_path = save_image_for_later(images[idx], theme)
                total = saved_posts.save_post(theme, text, img_path)
                print(f"\n  Saved Option {idx+1} ({theme}) for later. You now have {total} saved post(s).")
            continue

        # Post now
        if action in ("1", "2", "3"):
            idx = int(action) - 1
            if idx < len(options):
                theme, text = options[idx]
                image = images[idx]
                post_flow(theme, text, image)
            continue

        print("  Type 1/2/3 to post, s1/s2/s3 to save, or 'done'")


def handle_saved():
    """Show saved posts and let user pick one to post."""
    posts = saved_posts.get_saved_posts()

    if not posts:
        print("\n  No saved posts yet. Generate some first.")
        return

    print("\n")
    print("=" * 55)
    print(f"   YOUR SAVED POSTS ({len(posts)} total)")
    print("=" * 55)

    for i, p in enumerate(posts, 1):
        print(f"\n---------------------------------------------------")
        print(f"   #{i}: {p['theme']}  (saved {p['saved_on']})")
        print(f"---------------------------------------------------")
        print()
        print(p["text"])

    print(f"\n---------------------------------------------------")

    while True:
        print()
        print(f"  Type a number (1-{len(posts)}) to POST it")
        print(f"  Type d1, d2, etc. to DELETE one")
        print(f"  Type 'back' to go back")
        print()
        action = input("  Your choice: ").strip().lower()

        if action == "back":
            return

        # Delete
        if action.startswith("d") and action[1:].isdigit():
            idx = int(action[1:]) - 1
            if 0 <= idx < len(posts):
                removed = posts[idx]
                saved_posts.remove_post(idx)
                posts = saved_posts.get_saved_posts()
                print(f"\n  Deleted '{removed['theme']}'. {len(posts)} saved post(s) remaining.")
                if not posts:
                    print("  No more saved posts.")
                    return
            continue

        # Post
        if action.isdigit():
            idx = int(action) - 1
            if 0 <= idx < len(posts):
                p = posts[idx]
                image = load_image(p.get("image_path"))
                posted = post_flow(p["theme"], p["text"], image)
                if posted:
                    saved_posts.remove_post(idx)
                    posts = saved_posts.get_saved_posts()
                    print(f"  Removed from saved queue. {len(posts)} post(s) remaining.")
                    if not posts:
                        return
            continue

        print(f"  Type a number (1-{len(posts)}), d1/d2/etc., or 'back'")


def post_flow(theme: str, text: str, image: bytes | None) -> bool:
    """Edit and post a single post. Returns True if posted."""
    print(f"\n  Selected: {theme}")

    edit_choice = input("\n  Want to edit it before posting? (y/n): ").strip().lower()
    if edit_choice == "y":
        text = open_in_notepad(text)
        print("\n  Got your edits.")

    confirm = input("\n  Post this to LinkedIn right now? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Skipped.")
        return False

    try:
        post_id = post_to_linkedin(text, image)
        print()
        print("  =============================================")
        print("   POSTED TO LINKEDIN")
        print("  =============================================")
        print(f"  Theme: {theme}")
        print(f"  Post ID: {post_id}")
        print("  Check your LinkedIn profile -- it's live.")
        return True
    except Exception as e:
        print(f"\n  Error posting: {e}")
        print("  The post is in your email -- you can copy/paste it manually.")
        return False


def run():
    while True:
        choice = show_main_menu()

        if choice == "1":
            handle_generate()
        elif choice == "2":
            handle_saved()
        elif choice == "3":
            print("\n  See you next time.\n")
            return


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
