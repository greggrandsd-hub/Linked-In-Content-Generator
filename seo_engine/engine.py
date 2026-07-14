"""
Engine orchestrator — one call runs the whole SEO/AEO/GEO cycle:

    1. Pull the next keyword from the topic queue (auto-refills via Gemini)
    2. Generate a fully optimized article in Greg's voice
    3. Save it and rebuild the static site (docs/)
    4. Drop the companion LinkedIn post into the Saved queue
    5. Email Greg the article link + LinkedIn post (best-effort)

Designed to be idempotent and safe to run unattended (cron / GitHub Actions).
"""

from datetime import datetime

import saved_posts
from seo_engine import publisher, topics


def run_cycle(notify: bool = True) -> dict:
    """Generate and publish the next article. Returns the article dict."""
    from seo_engine import generator  # lazy — needs google-genai installed

    topic = topics.next_topic()
    print(f"[SEO Engine] Next topic: {topic['keyword']}")

    article = generator.generate_article(topic)
    article["published"] = datetime.now().strftime("%Y-%m-%d")

    publisher.save_article(article)
    publisher.build_site()
    topics.mark_used(topic["keyword"])

    url = publisher.article_url(article)
    print(f"[SEO Engine] Published: {url}")

    # Repurposing loop — the article's companion post lands in the Saved tab.
    linkedin_post = (article.get("linkedin_post") or "").strip()
    if linkedin_post:
        try:
            saved_posts.save_post(f"SEO: {article['title']}", linkedin_post)
            print("[SEO Engine] Companion LinkedIn post added to Saved queue")
        except Exception as e:
            print(f"[SEO Engine] Could not save companion post: {e}")

    _ping_indexnow([url, f"{publisher.SITE_BASE_URL}/"])

    if notify:
        _notify(article, url, linkedin_post)

    return article


def _ping_indexnow(urls: list) -> None:
    """Tell Bing (which feeds ChatGPT search and Copilot) about new/updated
    pages the moment they publish. Best-effort; never fails the run. Bing
    fetches on its own schedule, so pinging just before the Pages deploy
    finishes is fine."""
    try:
        import requests
        from urllib.parse import urlparse
        from config import INDEXNOW_KEY, SITE_BASE_URL

        if not INDEXNOW_KEY:
            return
        host = urlparse(SITE_BASE_URL).netloc
        r = requests.post(
            "https://api.indexnow.org/indexnow",
            json={"host": host, "key": INDEXNOW_KEY,
                  "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
                  "urlList": urls},
            timeout=15,
        )
        print(f"[SEO Engine] IndexNow ping sent ({r.status_code}) for {len(urls)} URL(s)")
    except Exception as e:
        print(f"[SEO Engine] IndexNow ping skipped: {e}")


def _notify(article: dict, url: str, linkedin_post: str) -> None:
    """Email the day's article link + companion post. Never fails the run."""
    try:
        from email_client import send_email

        body = (
            f"New article published by the SEO/AEO/GEO engine:\n\n"
            f"{article['title']}\n{url}\n\n"
            f"Target keyword: {article['keyword']}\n\n"
            f"--- Companion LinkedIn post (also in your Saved queue) ---\n\n"
            f"{linkedin_post or '(none generated)'}"
        )
        send_email(subject=f"SEO Engine published: {article['title']}", post_text=body)
        print("[SEO Engine] Notification email sent")
    except Exception as e:
        print(f"[SEO Engine] Notification email skipped: {e}")


def status() -> dict:
    """Snapshot for the dashboard: published articles + queue state."""
    articles = publisher.load_articles()
    return {
        "articles": articles,
        "article_count": len(articles),
        "topics_remaining": topics.remaining_count(),
        "queue": topics.get_queue(),
        "latest_url": publisher.article_url(articles[0]) if articles else None,
    }
