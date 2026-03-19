"""
Saved Posts Queue — Save posts you like for posting later.
Supports scheduling posts for specific dates and times.
"""

import json
import os
from datetime import datetime

SAVED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".saved_posts.json")


def _load_all() -> list[dict]:
    """Load all saved posts."""
    if not os.path.exists(SAVED_FILE):
        return []
    with open(SAVED_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_all(posts: list[dict]) -> None:
    """Write all saved posts."""
    with open(SAVED_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def save_post(theme: str, text: str, image_path: str | None = None,
              scheduled_for: str | None = None) -> int:
    """Save a post to the queue. Returns the total number of saved posts."""
    posts = _load_all()
    posts.append({
        "theme": theme,
        "text": text,
        "image_path": image_path,
        "saved_on": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "scheduled_for": scheduled_for,
    })
    _save_all(posts)
    return len(posts)


def get_saved_posts() -> list[dict]:
    """Get all saved posts."""
    return _load_all()


def get_due_posts() -> list[tuple[int, dict]]:
    """Get posts that are scheduled and due now. Returns list of (index, post)."""
    posts = _load_all()
    now = datetime.now()
    due = []
    for i, p in enumerate(posts):
        sched = p.get("scheduled_for")
        if sched:
            try:
                sched_time = datetime.strptime(sched, "%Y-%m-%d %H:%M")
                if sched_time <= now:
                    due.append((i, p))
            except ValueError:
                pass
    return due


def remove_post(index: int) -> None:
    """Remove a post from the queue by index (0-based)."""
    posts = _load_all()
    if 0 <= index < len(posts):
        posts.pop(index)
        _save_all(posts)


def count() -> int:
    """How many posts are saved."""
    return len(_load_all())
