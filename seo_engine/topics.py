"""
Topic engine — the keyword-targeted content queue.

A new domain can't win head terms like "sales training" — but it CAN win
long-tail, question-shaped searches that the big players ignore. Those same
questions are exactly what people type into ChatGPT and Perplexity, which is
what makes them AEO/GEO gold.

The queue ships pre-seeded with long-tail question keywords in Greg's niche.
When it runs low, the engine asks Gemini to research and append more, so it
never runs dry. State lives in content/topic_queue.json.
"""

import json
import os

_CONTENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content"
)
QUEUE_FILE = os.path.join(_CONTENT_DIR, "topic_queue.json")

# Refill the queue via Gemini when fewer than this many topics remain unused.
REFILL_THRESHOLD = 5
REFILL_BATCH_SIZE = 20

# ── Seed topics ──────────────────────────────────────────────────────────────
# Long-tail, question-intent keywords a new site can actually rank for,
# mapped loosely to the 20 G Squared Truths. Each becomes one article.
SEED_TOPICS = [
    {"keyword": "why is my sales team not hitting quota", "title": "Why Is My Sales Team Not Hitting Quota? The 5 Real Reasons"},
    {"keyword": "how to fix an inaccurate sales forecast", "title": "How to Fix an Inaccurate Sales Forecast (Stop Forecasting Hope)"},
    {"keyword": "how to hold salespeople accountable without micromanaging", "title": "How to Hold Salespeople Accountable Without Micromanaging"},
    {"keyword": "what to do when your best salesperson leaves", "title": "What to Do When Your Best Salesperson Leaves (Hero Culture Is the Real Problem)"},
    {"keyword": "why do sales strategies fail in execution", "title": "Why Do Sales Strategies Fail in Execution? The Manager Gap"},
    {"keyword": "how to build a sales process for a small company", "title": "How to Build a Sales Process for a Small Company (Simple Enough to Learn in a Week)"},
    {"keyword": "sales compensation plan mistakes", "title": "7 Sales Compensation Plan Mistakes That Kill Pipeline"},
    {"keyword": "how should a CEO stop being the bottleneck in sales", "title": "How a CEO Stops Being the Bottleneck in Their Own Sales Process"},
    {"keyword": "sales activity metrics vs results", "title": "Sales Activity Metrics vs. Results: What to Actually Measure"},
    {"keyword": "how to coach sales managers to coach reps", "title": "How to Coach Sales Managers Who Only Report the News"},
    {"keyword": "signs of a broken sales pipeline", "title": "8 Signs of a Broken Sales Pipeline (and How to Fix Each One)"},
    {"keyword": "how to run a sales pipeline review meeting", "title": "How to Run a Pipeline Review Meeting That Isn't a Fiction Reading"},
    {"keyword": "hiring salespeople for character vs experience", "title": "Hiring Salespeople: Character vs. Experience — Which Wins?"},
    {"keyword": "why being nice is hurting your sales team", "title": "The Niceness Trap: Why Avoiding Hard Conversations Is Selfish"},
    {"keyword": "how often should a CEO talk to customers", "title": "How Often Should a CEO Talk to Customers? (More Than You Do)"},
    {"keyword": "how to simplify a complex sales process", "title": "How to Simplify a Sales Process That's Choking Your Growth"},
    {"keyword": "what is revenue friction and how to remove it", "title": "What Is Revenue Friction? Find Where Money Gets Stuck and Kill It"},
    {"keyword": "how to make sales predictable with math", "title": "Sales Is Math: How to Make Revenue Predictable"},
    {"keyword": "why we've always done it this way is expensive", "title": "\"We've Always Done It This Way\" — the Most Expensive Phrase in Business"},
    {"keyword": "how to create ownership on a sales team", "title": "If Everyone Is Responsible, No One Is: Creating Real Ownership in Sales"},
    {"keyword": "data driven sales management for small business", "title": "Data Over Drama: Data-Driven Sales Management for Small Business"},
    {"keyword": "how to speed up sales execution", "title": "Speed of Execution: Why the Fastest Company Usually Wins"},
    {"keyword": "how to stop salespeople from pitching too early", "title": "How to Stop Your Reps From Pitching Before They Diagnose"},
    {"keyword": "how to leave a sales voicemail that gets callbacks", "title": "The High-Converting Sales Voicemail: Plant Curiosity, Don't Pitch"},
    {"keyword": "sales quota setting for small business", "title": "How to Set Sales Quotas for a Small Business (Napkin-Simple Math)"},
    {"keyword": "difference between hunting and farming in sales", "title": "Hunting vs. Farming in Sales: Why You Must Decouple Them"},
    {"keyword": "how to reduce ramp time for new sales hires", "title": "How to Cut New Sales Hire Ramp Time in Half"},
    {"keyword": "should you cap sales commissions", "title": "Should You Cap Sales Commissions? No — Here's the Math"},
    {"keyword": "how to tell if a deal will actually close", "title": "How to Tell if a Deal Will Actually Close (a Forecast Is Not a Feeling)"},
    {"keyword": "sales team accountability framework", "title": "A Simple Sales Accountability Framework (Accountability Is Love)"},
    {"keyword": "why sales managers fail in their first year", "title": "Why New Sales Managers Fail in Year One — the Coaching Deficit"},
    {"keyword": "how many touches does it take to book a meeting", "title": "How Many Touches to Book a Meeting? Activity + Process = Results"},
    {"keyword": "ceo guide to fixing underperforming sales team", "title": "The CEO's Guide to Fixing an Underperforming Sales Team"},
    {"keyword": "how to get honest feedback as a CEO", "title": "The Echo Chamber: How CEOs Get Honest Feedback Before It's Too Late"},
    {"keyword": "boring basics of sales that actually scale", "title": "Process Discipline: The Boring Basics That Actually Scale Revenue"},
    {"keyword": "how to stop being busy and start moving the needle in sales", "title": "Busy Isn't Progress: How Sales Teams Confuse Motion With Movement"},
]


def _load_queue() -> list[dict]:
    if not os.path.exists(QUEUE_FILE):
        return [dict(t, used=False) for t in SEED_TOPICS]
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_queue(queue: list[dict]) -> None:
    os.makedirs(_CONTENT_DIR, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def remaining_count() -> int:
    """How many unused topics are left in the queue."""
    return sum(1 for t in _load_queue() if not t.get("used"))


def get_queue() -> list[dict]:
    """Full queue (used and unused), for the dashboard."""
    return _load_queue()


def next_topic() -> dict:
    """
    Return the next unused topic, refilling via Gemini if the queue is low.
    Does NOT mark it used — call mark_used(keyword) after a successful publish.
    """
    queue = _load_queue()

    unused = [t for t in queue if not t.get("used")]
    if len(unused) <= REFILL_THRESHOLD:
        try:
            queue = _refill(queue)
            unused = [t for t in queue if not t.get("used")]
        except Exception as e:
            print(f"[Topics] Queue refill failed (will keep using seeds): {e}")

    if not unused:
        raise RuntimeError("Topic queue is empty and refill failed.")

    _save_queue(queue)
    return unused[0]


def mark_used(keyword: str) -> None:
    """Mark a topic as used after its article has been published."""
    queue = _load_queue()
    for t in queue:
        if t["keyword"] == keyword:
            t["used"] = True
    _save_queue(queue)


def _refill(queue: list[dict]) -> list[dict]:
    """Ask Gemini for a fresh batch of long-tail question keywords."""
    from gemini_client import get_gemini_client, _call_with_retry

    existing = ", ".join(t["keyword"] for t in queue)
    prompt = (
        "You are an SEO strategist for a sales-leadership expert whose audience "
        "is CEOs, founders, and revenue leaders of small and mid-size companies. "
        f"Generate {REFILL_BATCH_SIZE} NEW long-tail, question-intent search keywords "
        "this audience types into Google, ChatGPT, or Perplexity — problems about "
        "sales teams, forecasting, pipeline, comp plans, sales managers, hiring "
        "reps, accountability, and scaling revenue.\n\n"
        "Rules:\n"
        "- Long-tail (5+ words), low-competition, specific problems\n"
        "- Question or how-to phrasing preferred\n"
        f"- Must NOT duplicate any of these existing keywords: {existing}\n\n"
        'Return ONLY a JSON array like: [{"keyword": "...", "title": "..."}] '
        "where title is a compelling, keyword-containing article headline."
    )

    client = get_gemini_client()
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    new_topics = json.loads(text.strip())

    existing_keywords = {t["keyword"].lower() for t in queue}
    added = 0
    for t in new_topics:
        if isinstance(t, dict) and t.get("keyword") and t.get("title"):
            if t["keyword"].lower() not in existing_keywords:
                queue.append({"keyword": t["keyword"], "title": t["title"], "used": False})
                added += 1

    print(f"[Topics] Refilled queue with {added} new topics from Gemini")
    return queue
