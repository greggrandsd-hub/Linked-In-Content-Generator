"""
Sales Leadership and Revenue Growth. Idea Source Document.

This is the broader topic pool that the LinkedIn Content Generator pulls
from, in addition to the G Squared Truths (Greg's specific opinions that
live in gemini_client.py).

Greg's brief for this file (2026-06-05):
  "Top 50 things I should be posting: 10 areas, five each. Bake it in so
  we have variety." This is the curated 50. Ten areas, five topics each,
  grounded in Greg's real frameworks, story hooks, and AI-first point of
  view. The picker enforces category diversity so no single run repeats
  an area.

Each topic is a standalone concept. Topics are grouped under a CATEGORY
so the picker can enforce category diversity (no two posts from the same
category in a single run, which kills repetition).

Rules:
  - One concept per line (no merged ideas)
  - Plain phrasing. The Voice Bible carries the tone.
  - No banned vocabulary, no em dashes, no negative-parallelism reframes.
  - "playbook" is banned. Use "system" / "framework" / "guide".
"""

# ── Idea Source by Category ─────────────────────────────────────────────────
# Structured as { "CATEGORY": [topic, topic, ...] }
# 10 areas, 5 topics each = 50. The picker pulls (category, topic) tuples
# and ensures category diversity. Add or remove topics here without touching
# anything else (per _BACKUPS/LOCKED-DAILY-TASKS.md, the sanctioned knob).

IDEA_SOURCE_BY_CATEGORY: dict[str, list[str]] = {
    "AI in Sales Execution": [
        "Why a rep using AI does three hours of prospecting in twenty minutes",
        "The CRM data-entry problem AI quietly solves",
        "What to pull from AI research before every first call",
        "Personalization at scale without sounding like a robot",
        "The structural disadvantage of a team still cold calling off a spreadsheet",
    ],
    "AI for Sales Leadership and Coaching": [
        "AI can analyze every call, so the no-time-to-coach excuse is gone",
        "Real-time coaching versus feedback once a quarter",
        "Spotting the deal about to slip before the rep does",
        "What AI forecasting catches that a gut-feel review misses",
        "The sales manager's real job after AI removes the busywork",
    ],
    "The 5 Pillars Operating System": [
        "Process: if it lives in one rep's head, it is not a process",
        "People: your ceiling is your team quality",
        "Pipeline: stages without exit criteria are just opinions",
        "Performance: inspect what you expect",
        "Psychology: why the same plan fires up one rep and breaks another",
    ],
    "The 12 Silent Killers": [
        "Fix one silent killer and you usually find three more",
        "The broken forecast that looks fine until quarter-end",
        "When a manager has a title but no real leadership system",
        "Misaligned comp: paying for the behavior you say you hate",
        "The wrong tech stack that automates a broken process faster",
    ],
    "Hiring, Onboarding, and Talent": [
        "Always Be Recruiting: the cure for panic hiring",
        "You can teach sales skills, you cannot teach work ethic",
        "Why an 18-month ramp is a system failure and how to cut it to six",
        "Why structure keeps reps longer than money does",
        "The scorecard that makes a bad hire obvious in week one",
    ],
    "Forecasting and Pipeline Discipline": [
        "What turns a hope into a real forecast",
        "The three-bucket forecast: would you bet your job on this deal?",
        "Every pipeline stage needs an exit criterion with a date",
        "Optimistic fiction: how good people produce bad forecasts",
        "The twenty-minute pipeline review that actually predicts the quarter",
    ],
    "Compensation and Incentive Design": [
        "Most salespeople are coin-operated, and that is not an insult",
        "Decouple hunting from farming in your comp plan",
        "Take the cap off your top performers",
        "Make the comp math simple enough to run on a napkin",
        "If you do not like the behavior, you are paying for the wrong thing",
    ],
    "CEO and Founder Lessons": [
        "The 7:15 AM call: the problem is never what the CEO thinks",
        "When the CEO signs off on everything, growth stops",
        "If the CEO has not talked to a customer in six months, the strategy is wrong",
        "When to stop selling it yourself and hire a real sales leader",
        "The founder-led sales trap and how to climb out of it",
    ],
    "The Hunter to Operator Shift": [
        "You cannot scale chaos, AI just amplifies it faster",
        "Natural talent runs out, a designed operating system scales",
        "The black box: your best reps close and nobody can explain why",
        "Going from my style to a system the next hire can run",
        "Never automate a broken system",
    ],
    "Contrarian Takes on the Industry": [
        "Training is an event, behavior change is a system",
        "A better hammer does not build the house: the $50K tool that changed nothing",
        "The salespeople AI actually replaces are the ones who refuse to use it",
        "AI opens the door, a human still closes",
        "Garbage in, garbage out: AI on a broken process just fails faster",
    ],
}


def all_idea_source_themes() -> list[tuple[str, str, str | None]]:
    """
    Return every Idea Source topic as a (category, theme_name, truth) tuple.

    The third slot is the optional "core truth". For Idea Source topics
    there isn't one (the Voice Bible carries Greg's POV at generation
    time), so it's always None. This shape matches the G_SQUARED_TRUTHS
    normalization in gemini_client.pick_diverse_themes.
    """
    out: list[tuple[str, str, str | None]] = []
    for category, topics in IDEA_SOURCE_BY_CATEGORY.items():
        for topic in topics:
            out.append((category, topic, None))
    return out


def category_count() -> int:
    return len(IDEA_SOURCE_BY_CATEGORY)


def total_topic_count() -> int:
    return sum(len(topics) for topics in IDEA_SOURCE_BY_CATEGORY.values())
