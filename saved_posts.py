"""
Saved Posts Queue — Save posts you like for posting later.
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


def save_post(theme: str, text: str, image_path: str | None = None) -> int:
    """Save a post to the queue. Returns the total number of saved posts."""
    posts = _load_all()
    posts.append({
        "theme": theme,
        "text": text,
        "image_path": image_path,
        "saved_on": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
    })
    _save_all(posts)
    return len(posts)


def get_saved_posts() -> list[dict]:
    """Get all saved posts."""
    return _load_all()


def remove_post(index: int) -> None:
    """Remove a post from the queue by index (0-based)."""
    posts = _load_all()
    if 0 <= index < len(posts):
        posts.pop(index)
        _save_all(posts)


def count() -> int:
    """How many posts are saved."""
    return len(_load_all())
