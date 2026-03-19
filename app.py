"""
LinkedIn Content Generator — Flask Web UI

A clean web interface that replaces the command-line workflow.
Start with: python app.py
"""

import os
import sys
import json
import base64
import webbrowser
import threading

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, Response,
)

# Import existing project modules
from dropbox_client import download_latest_file, list_files
from gemini_client import (
    generate_three_options, generate_freestyle_post,
    generate_post_image, upload_file,
)
from linkedin_client import post_to_linkedin
from post import save_options
import saved_posts

# ── Flask App Setup ───────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory storage for the current session's generated posts and images.
# This avoids needing a database — posts live here until saved or posted.
_session_posts = []       # list of {"theme": str, "text": str}
_session_images = []      # list of bytes | None
_freestyle_post = None    # {"theme": str, "text": str}
_freestyle_image = None   # bytes | None


def _save_image_to_disk(image_bytes, theme):
    """Save image bytes to a file for saved-posts persistence."""
    if not image_bytes:
        return None
    safe_name = theme.replace(" ", "_").replace('"', "").replace("'", "")[:30]
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".saved_images",
        f"{safe_name}_{id(image_bytes)}.png",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


def _load_image_from_disk(path):
    """Load image bytes from a saved file path."""
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


# ── Context Processor — inject saved_count into all templates ─────
@app.context_processor
def inject_saved_count():
    return {"saved_count": saved_posts.count()}


# ══════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard")


# ── Generate Flow ─────────────────────────────────────────────────

@app.route("/generate")
def generate():
    """Show generated posts if available, otherwise show the generate button."""
    options = []
    for i, post in enumerate(_session_posts):
        options.append({
            "theme": post["theme"],
            "text": post["text"],
            "has_image": _session_images[i] is not None if i < len(_session_images) else False,
        })
    return render_template(
        "generate.html",
        active_page="generate",
        options=options,
        post_result=session.pop("post_result", None),
    )


@app.route("/generate/run")
def generate_trigger():
    """Actually run the generation pipeline. Synchronous — blocks until done."""
    global _session_posts, _session_images

    try:
        # Step 1-2: Dropbox
        local_path, original_name = download_latest_file()

        # Step 3: Upload to Gemini
        uploaded_file = upload_file(local_path, original_name)

        # Step 4: Generate 3 posts
        options = generate_three_options(uploaded_file)

        # Step 5: Generate images
        images = []
        for theme, text in options:
            img = generate_post_image(text)
            images.append(img)

        # Save for the legacy post.py loader too
        save_options(options, images)

        # Store in memory for the web UI
        _session_posts = [{"theme": t, "text": txt} for t, txt in options]
        _session_images = images

        # Cleanup temp file
        os.unlink(local_path)

        flash("3 posts generated successfully.", "success")

    except Exception as e:
        flash(f"Generation failed: {e}", "error")

    return redirect(url_for("generate"))


# ── Freestyle Flow ────────────────────────────────────────────────

@app.route("/freestyle", methods=["GET", "POST"])
def freestyle():
    """Custom topic input and generation."""
    global _freestyle_post, _freestyle_image

    result = None
    topic = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        if topic:
            try:
                theme, text = generate_freestyle_post(topic)
                image = generate_post_image(text)

                _freestyle_post = {"theme": theme, "text": text}
                _freestyle_image = image

                result = {
                    "theme": theme,
                    "text": text,
                    "has_image": image is not None,
                }
                flash("Post generated.", "success")

            except Exception as e:
                flash(f"Generation failed: {e}", "error")
        else:
            flash("Please enter a topic.", "error")

    elif _freestyle_post:
        result = {
            "theme": _freestyle_post["theme"],
            "text": _freestyle_post["text"],
            "has_image": _freestyle_image is not None,
        }
        topic = _freestyle_post["theme"]

    return render_template(
        "freestyle.html",
        active_page="freestyle",
        result=result,
        topic=topic,
        post_result=session.pop("post_result", None),
    )


# ── Saved Posts ───────────────────────────────────────────────────

@app.route("/saved")
def saved():
    posts = saved_posts.get_saved_posts()
    return render_template(
        "saved.html",
        active_page="saved",
        posts=posts,
        post_result=session.pop("post_result", None),
    )


# ── Post Actions ──────────────────────────────────────────────────

@app.route("/post/<int:index>", methods=["POST"])
def post_now(index):
    """Post a generated/freestyle post to LinkedIn."""
    source = request.form.get("source", "session")

    try:
        if source == "session" and index < len(_session_posts):
            text = _session_posts[index]["text"]
            image = _session_images[index] if index < len(_session_images) else None
            post_id = post_to_linkedin(text, image)
            session["post_result"] = post_id
            flash("Posted to LinkedIn.", "success")
            return redirect(url_for("generate"))

        elif source == "freestyle" and _freestyle_post:
            text = _freestyle_post["text"]
            image = _freestyle_image
            post_id = post_to_linkedin(text, image)
            session["post_result"] = post_id
            flash("Posted to LinkedIn.", "success")
            return redirect(url_for("freestyle"))

    except Exception as e:
        flash(f"Failed to post: {e}", "error")

    return redirect(url_for("generate") if source == "session" else url_for("freestyle"))


@app.route("/post-saved/<int:index>", methods=["POST"])
def post_saved(index):
    """Post a saved post to LinkedIn."""
    posts = saved_posts.get_saved_posts()
    if index < len(posts):
        post = posts[index]
        image = _load_image_from_disk(post.get("image_path"))
        try:
            post_id = post_to_linkedin(post["text"], image)
            saved_posts.remove_post(index)
            session["post_result"] = post_id
            flash("Posted to LinkedIn and removed from saved.", "success")
        except Exception as e:
            flash(f"Failed to post: {e}", "error")
    else:
        flash("Post not found.", "error")

    return redirect(url_for("saved"))


@app.route("/save/<int:index>", methods=["POST"])
def save_post(index):
    """Save a generated/freestyle post for later."""
    source = request.form.get("source", "session")

    if source == "session" and index < len(_session_posts):
        post = _session_posts[index]
        image = _session_images[index] if index < len(_session_images) else None
        img_path = _save_image_to_disk(image, post["theme"])
        total = saved_posts.save_post(post["theme"], post["text"], img_path)
        flash(f"Saved. You now have {total} saved post(s).", "success")
        return redirect(url_for("generate"))

    elif source == "freestyle" and _freestyle_post:
        img_path = _save_image_to_disk(_freestyle_image, _freestyle_post["theme"])
        total = saved_posts.save_post(
            _freestyle_post["theme"], _freestyle_post["text"], img_path
        )
        flash(f"Saved. You now have {total} saved post(s).", "success")
        return redirect(url_for("freestyle"))

    flash("Nothing to save.", "error")
    return redirect(url_for("dashboard"))


@app.route("/schedule/<int:index>", methods=["POST"])
def schedule_post(index):
    """Set a schedule date for a saved post."""
    scheduled_for = request.form.get("scheduled_for", "")
    if scheduled_for:
        # Convert from HTML datetime-local format to our storage format
        scheduled_for = scheduled_for.replace("T", " ")

    posts = saved_posts.get_saved_posts()
    if index < len(posts):
        posts[index]["scheduled_for"] = scheduled_for if scheduled_for else None
        saved_posts._save_all(posts)
        if scheduled_for:
            flash(f"Post scheduled for {scheduled_for}.", "success")
        else:
            flash("Schedule cleared.", "info")
    else:
        flash("Post not found.", "error")

    return redirect(url_for("saved"))


@app.route("/delete/<int:index>", methods=["POST"])
def delete_post(index):
    """Delete a saved post."""
    saved_posts.remove_post(index)
    flash("Post deleted.", "success")
    return redirect(url_for("saved"))


@app.route("/edit-and-post", methods=["POST"])
def edit_and_post():
    """Post an edited version of a post."""
    source = request.form.get("source", "session")
    index = int(request.form.get("index", 0))
    text = request.form.get("text", "").strip()

    if not text:
        flash("Post text cannot be empty.", "error")
        return redirect(url_for("dashboard"))

    # Get the image from the appropriate source
    image = None
    if source == "session" and index < len(_session_images):
        image = _session_images[index]
    elif source == "freestyle":
        image = _freestyle_image
    elif source == "saved":
        posts = saved_posts.get_saved_posts()
        if index < len(posts):
            image = _load_image_from_disk(posts[index].get("image_path"))

    try:
        post_id = post_to_linkedin(text, image)
        session["post_result"] = post_id
        flash("Edited post published to LinkedIn.", "success")

        # If posted from saved, remove it
        if source == "saved":
            saved_posts.remove_post(index)
            return redirect(url_for("saved"))

    except Exception as e:
        flash(f"Failed to post: {e}", "error")

    if source == "freestyle":
        return redirect(url_for("freestyle"))
    elif source == "saved":
        return redirect(url_for("saved"))
    return redirect(url_for("generate"))


# ── Image Serving ─────────────────────────────────────────────────

@app.route("/image/<source>/<int:index>")
def serve_image(source, index):
    """Serve a generated image from memory."""
    image_bytes = None

    if source == "session" and index < len(_session_images):
        image_bytes = _session_images[index]
    elif source == "freestyle":
        image_bytes = _freestyle_image

    if image_bytes:
        return Response(image_bytes, mimetype="image/png")
    # Return a 1x1 transparent pixel as fallback
    return Response(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "nGNgYPgPAAEDAQAIicLsAAAABJRU5ErkJggg=="
        ),
        mimetype="image/png",
    )


@app.route("/saved-image/<int:index>")
def serve_saved_image(index):
    """Serve an image from a saved post."""
    posts = saved_posts.get_saved_posts()
    if index < len(posts):
        image_bytes = _load_image_from_disk(posts[index].get("image_path"))
        if image_bytes:
            return Response(image_bytes, mimetype="image/png")

    return Response(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "nGNgYPgPAAEDAQAIicLsAAAABJRU5ErkJggg=="
        ),
        mimetype="image/png",
    )


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = 5000

    # Auto-open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    print("=" * 55)
    print("  LinkedIn Content Generator — Web UI")
    print(f"  Running at: http://localhost:{port}")
    print("  Press Ctrl+C to stop")
    print("=" * 55)

    app.run(host="0.0.0.0", port=port, debug=False)
