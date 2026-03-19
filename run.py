"""
LinkedIn Content Generator — All-in-One

Double-click "LinkedIn Content Generator.bat" on your Desktop.
Generate posts, save your favorites, schedule them, and post — all in one place.
"""

import os
import sys
import tempfile
import subprocess
from datetime import datetime, timedelta

# Fix Windows console encoding for special characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dropbox_client import download_latest_file, list_files
from gemini_client import generate_three_options, generate_post_image, upload_file
from email_client import send_three_options_email
from post import save_options
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
    """Save image bytes to a file for later posting."""
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


def ask_yes_no(question: str) -> bool:
    """Simple yes/no question."""
    while True:
        answer = input(f"  {question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Just type y or n")


def ask_schedule() -> str | None:
    """Ask when to schedule a post. Returns datetime string or None."""
    print()
    print("  When do you want to post it?")
    print()
    print("    1. Tomorrow morning (8am)")
    print("    2. This Thursday")
    print("    3. This Friday")
    print("    4. Next Monday")
    print("    5. Next Tuesday")
    print("    6. Next Wednesday")
    print("    7. Pick a specific date")
    print()

    while True:
        choice = input("  Pick a number (1-7): ").strip()
        now = datetime.now()

        if choice == "1":
            dt = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0)
            break
        elif choice == "2":
            days_ahead = (3 - now.weekday()) % 7 or 7
            dt = (now + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0)
            break
        elif choice == "3":
            days_ahead = (4 - now.weekday()) % 7 or 7
            dt = (now + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0)
            break
        elif choice == "4":
            days_ahead = (0 - now.weekday()) % 7 or 7
            dt = (now + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0)
            break
        elif choice == "5":
            days_ahead = (1 - now.weekday()) % 7 or 7
            dt = (now + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0)
            break
        elif choice == "6":
            days_ahead = (2 - now.weekday()) % 7 or 7
            dt = (now + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0)
            break
        elif choice == "7":
            print()
            date_str = input("  Type the date (example: March 25): ").strip()
            time_str = input("  What time? (example: 8am, 12pm, 3pm): ").strip()

            # Parse the date
            try:
                # Try common formats
                year = now.year
                for fmt in ["%B %d", "%b %d", "%m/%d", "%m-%d"]:
                    try:
                        parsed = datetime.strptime(date_str, fmt).replace(year=year)
                        break
                    except ValueError:
                        continue
                else:
                    print("  Couldn't understand that date. Try like: March 25 or 3/25")
                    continue

                # Parse time
                time_str = time_str.lower().replace(" ", "")
                for fmt in ["%I%p", "%I:%M%p", "%H:%M"]:
                    try:
                        parsed_time = datetime.strptime(time_str, fmt)
                        parsed = parsed.replace(hour=parsed_time.hour, minute=parsed_time.minute)
                        break
                    except ValueError:
                        continue
                else:
                    parsed = parsed.replace(hour=8, minute=0)
                    print(f"  Couldn't read the time -- defaulting to 8am")

                dt = parsed
                break
            except Exception:
                print("  Couldn't understand that. Try again.")
                continue
        else:
            print("  Just type a number 1-7")
            continue

    scheduled = dt.strftime("%Y-%m-%d %H:%M")
    friendly = dt.strftime("%A, %B %d at %I:%M %p")
    print(f"\n  Scheduled for: {friendly}")
    return scheduled


def show_main_menu():
    """Show the main menu and return choice."""
    saved_count = saved_posts.count()

    print()
    print("=" * 55)
    print("   LinkedIn Content Generator - G Squared Truths")
    print("=" * 55)
    print()
    print("  1. Generate 3 new posts")
    if saved_count:
        print(f"  2. View saved posts ({saved_count} saved)")
    else:
        print("  2. View saved posts (none yet)")
    print("  3. Quit")
    print()

    while True:
        choice = input("  What do you want to do? (1, 2, or 3): ").strip()
        if choice in ("1", "2", "3"):
            return choice
        print("  Just type 1, 2, or 3")


def handle_generate():
    """Generate 3 new posts, walk user through each one."""
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

    # Walk through each option one at a time
    print("\n")
    print("=" * 55)
    print("   YOUR 3 OPTIONS")
    print("=" * 55)

    for i, (theme, text) in enumerate(options, 1):
        print(f"\n---------------------------------------------------")
        print(f"   OPTION {i} of 3: {theme}")
        print(f"---------------------------------------------------")
        print()
        print(text)
        print()
        print(f"---------------------------------------------------")
        print(f"  What do you want to do with Option {i}?")
        print()

        if ask_yes_no("Post it now?"):
            post_flow(theme, text, images[i-1])
        elif ask_yes_no("Save it for later?"):
            if ask_yes_no("Schedule it for a specific day?"):
                schedule = ask_schedule()
            else:
                schedule = None
            img_path = save_image_for_later(images[i-1], theme)
            total = saved_posts.save_post(theme, text, img_path, schedule)
            if schedule:
                print(f"\n  Saved and scheduled. You now have {total} saved post(s).")
            else:
                print(f"\n  Saved for later. You now have {total} saved post(s).")
        else:
            print(f"\n  Skipped Option {i}.")

    print("\n  All done. Options also sent to your email with images.")


def handle_saved():
    """Show saved posts and walk user through them."""
    posts = saved_posts.get_saved_posts()

    if not posts:
        print("\n  No saved posts yet. Generate some first.")
        return

    print("\n")
    print("=" * 55)
    print(f"   YOUR SAVED POSTS ({len(posts)} total)")
    print("=" * 55)

    # Walk through each one
    i = 0
    while i < len(posts):
        p = posts[i]
        sched = p.get("scheduled_for")
        if sched:
            try:
                sched_friendly = datetime.strptime(sched, "%Y-%m-%d %H:%M").strftime("%A, %B %d at %I:%M %p")
                sched_label = f"  SCHEDULED: {sched_friendly}"
            except ValueError:
                sched_label = f"  SCHEDULED: {sched}"
        else:
            sched_label = "  Not scheduled"

        print(f"\n---------------------------------------------------")
        print(f"   Post {i+1} of {len(posts)}: {p['theme']}")
        print(f"   Saved: {p['saved_on']}")
        print(f"  {sched_label}")
        print(f"---------------------------------------------------")
        print()
        print(p["text"])
        print()
        print(f"---------------------------------------------------")

        if ask_yes_no("Post this one now?"):
            image = load_image(p.get("image_path"))
            posted = post_flow(p["theme"], p["text"], image)
            if posted:
                saved_posts.remove_post(i)
                posts = saved_posts.get_saved_posts()
                print(f"  Removed from saved. {len(posts)} post(s) remaining.")
                # Don't increment i since list shifted
                continue
        elif ask_yes_no("Delete this one?"):
            saved_posts.remove_post(i)
            posts = saved_posts.get_saved_posts()
            print(f"  Deleted. {len(posts)} post(s) remaining.")
            continue

        i += 1

        if i < len(posts):
            if not ask_yes_no("See the next saved post?"):
                break

    print("\n  Back to main menu.")


def post_flow(theme: str, text: str, image: bytes | None) -> bool:
    """Edit and post a single post. Returns True if posted."""
    if ask_yes_no("Want to edit it first?"):
        text = open_in_notepad(text)
        print("\n  Got your edits.")

    if not ask_yes_no("Post to LinkedIn right now?"):
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


def check_scheduled_posts():
    """Check if any scheduled posts are due and offer to post them."""
    due = saved_posts.get_due_posts()
    if not due:
        return

    print()
    print(f"  ** You have {len(due)} scheduled post(s) ready to go **")

    for idx, p in due:
        print(f"\n---------------------------------------------------")
        print(f"   SCHEDULED POST: {p['theme']}")
        print(f"   Was scheduled for: {p.get('scheduled_for', 'now')}")
        print(f"---------------------------------------------------")
        print()
        # Show preview
        lines = [l for l in p["text"].split("\n") if l.strip()]
        for line in lines[:5]:
            print(f"  {line}")
        if len(lines) > 5:
            print(f"  ... ({len(lines)-5} more lines)")
        print()

        if ask_yes_no("Post this now?"):
            image = load_image(p.get("image_path"))
            posted = post_flow(p["theme"], p["text"], image)
            if posted:
                saved_posts.remove_post(idx)


def run():
    # Check for any due scheduled posts first
    check_scheduled_posts()

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
