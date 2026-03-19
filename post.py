"""
Easy LinkedIn Poster — Save/load options for the posting flow.
Used by both main.py (to save) and run.py (to load and post).
"""

import json
import os

LAST_RUN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_run.json")


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
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f".last_image_{i+1}.png")
            with open(img_path, "wb") as f:
                f.write(img)


def load_options() -> tuple[list[dict], list[bytes | None]]:
    """Load the last generated options."""
    with open(LAST_RUN_FILE, encoding="utf-8") as f:
        data = json.load(f)

    images = []
    for i in range(len(data["options"])):
        img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f".last_image_{i+1}.png")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                images.append(f.read())
        else:
            images.append(None)

    return data["options"], images
