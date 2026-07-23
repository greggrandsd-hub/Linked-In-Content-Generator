"""
Offline test suite for the rewired LinkedIn voice gate (2026-07-23).

Runs with NO API calls: exercises _post_voice_gate, _enforce_banned_words,
and the prompt constants directly. Run from this folder:

    python test_voice_gate_offline.py

Every check maps to the 2026-07-23 rewire ruling: New Voice Bible July 2026
(master) blended with the Apify post-performance analysis. The three PASS
fixtures are Greg's real verified winners and must stay gate-clean forever:
if a future gate change fails them, the gate is wrong, not the posts.
"""

import re
import sys

import config
from gemini_client import (EXAMPLE_POSTS, GREG_SPOKEN_VOICE,
                           NEW_VOICE_BIBLE_LIVE_INSTRUCTION, OPENING_STYLES,
                           STYLE_GUIDE, VOICE_BIBLE, _enforce_banned_words,
                           _post_voice_gate)

EXAMPLE_VISTAGE = """A week of Vistage AI Masterclass sessions in Seattle. First time running my new workshop format: teach it, show it live, then the business owners build it themselves with AI before they leave the room.

More fun than I have had presenting in years. For a long time I sat up there as the talking head for three hours. This time the room did the work, and the aha moments kept coming.

Here's what I saw: every room already has one leader quietly ahead on AI. Sometimes the rest of the room found that out the same day. There was a great variety in AI experience, but we all came together that day to learn, pressure-test, and come out with some amazing results.

Thank you, Carla Corkern and Jess Hickey, for putting me in front of your groups. Sharp members, honest questions, zero spectators.

The gap between companies putting AI to work in sales and companies waiting is getting expensive. The CEOs in those rooms aren't waiting.

If you chair a Vistage group and want this workshop in your room, let's talk."""

EXAMPLE_DOG = """This was too funny not to share and a good reminder to check your tech. We have a golden retriever that loves to interrupt meetings. Most dog owners know this one well.

When I opened Zoom for my next call, which didn't happen due to a reschedule, I was talking to my dog about taking him for a walk later, among other things, like telling him to please stop licking the floor.

When I closed Zoom, I got this transcript. The message (besides what I thought was hilarious) is that if you have your AI Companions on and forget, it is still listening."""

EXAMPLE_CADENCE = """Is your team confusing CADENCE with SKILL?

The biggest mistake I see in cold outbound is mistaking activity for effectiveness. A perfect cadence is useless if the message is generic and self-serving.

Stop hounding people with commercial reminders.

Instead of: "Following up on my last email..."

Try this: Lead with a specific, observed insight about their business or industry. Show them you did your homework.

Focus: The goal of the first few touches is discovery and curiosity, not a meeting. As a good friend of mine says.."Prospecting is only about sorting." Thanks, Brian Jackson for that golden nugget.

Cold outbound is a skill that requires research, personalization, and storytelling.

Time to coach the skill, not just implement the software and count metrics.

If you are sending hundreds of emails and getting silence, revisit your approach, slow down, personalize, and do your research. Be different."""

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {name}" + (f"  <- {detail}" if not condition and detail else ""))


def has(problems, needle):
    return any(needle in p for p in problems)


def main():
    # ── 1-3: the three real winner examples must be gate-clean ────────────
    for label, text in (("example vistage (real-moment winner)", EXAMPLE_VISTAGE),
                        ("example dog (human artifact winner)", EXAMPLE_DOG)):
        problems = _post_voice_gate(text)
        check(f"{label} passes clean", problems == [], "; ".join(problems[:4]))

    # The cadence post is a real past winner but is written in the banned
    # broetry format, so it must NOT pass and is no longer a training example.
    check("cadence post (broetry, disavowed format) correctly fails",
          has(_post_voice_gate(EXAMPLE_CADENCE), "broetry"))

    # ── 4-9: each new deterministic check fires on the injected violation ──
    problems = _post_voice_gate(EXAMPLE_DOG.replace("meetings.", "meetings; every time."))
    check("semicolon fails", has(problems, "semicolon"))

    problems = _post_voice_gate(EXAMPLE_DOG + "\n\nYour move. 👇")
    check("emoji fails", has(problems, "emoji"))

    problems = _post_voice_gate(EXAMPLE_DOG + "\n\n#SalesLeadership")
    check("hashtag fails", has(problems, "hashtag"))

    problems = _post_voice_gate(EXAMPLE_DOG.replace("well.", "well!"))
    check("exclamation fails", has(problems, "exclamation"))

    stack = "\n\n".join(["Your pipeline is lying.", "Your forecast is fiction.",
                         "Your reps know it.", "Your board will too."])
    problems = _post_voice_gate(EXAMPLE_DOG + "\n\n" + stack)
    check("staccato stack of 4 one-liners fails", has(problems, "staccato stack"))

    bullets = "\n".join(["• Keep the weekly pipeline review on the calendar",
                         "• Ask for evidence, never opinion, on every commit",
                         "• Coach one skill per rep per month",
                         "• Inspect the same five numbers every Friday"])
    problems = _post_voice_gate(EXAMPLE_DOG + "\n\n" + bullets)
    check("bullet list does NOT trip staccato check",
          not has(problems, "staccato stack"), "; ".join(problems[:4]))

    # ── 10-11: word band ──────────────────────────────────────────────────
    short_text = " ".join(EXAMPLE_DOG.split()[:50])
    problems = _post_voice_gate(short_text)
    check("under 95 words fails", has(problems, "too short"))

    problems = _post_voice_gate(EXAMPLE_VISTAGE + "\n\n" + EXAMPLE_DOG)
    check("over 200 words fails", has(problems, "too long"))

    # ── 12: em dash autofix strips before the gate ────────────────────────
    dashed = EXAMPLE_DOG.replace("to check your tech", "to check your tech — every time")
    cleaned = _enforce_banned_words(dashed)
    check("em dash stripped by autofix", "—" not in cleaned)
    check("stripped text passes gate", _post_voice_gate(cleaned) == [],
          "; ".join(_post_voice_gate(cleaned)[:4]))

    # ── 13-14: negative parallelism still fatal ───────────────────────────
    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nIt's not about speed. It's about systems.")
    check("negative parallelism fails", len(problems) > 0)

    problems = _post_voice_gate(EXAMPLE_DOG + "\n\nStop guessing. Start knowing.")
    check("Stop X. Start Y. fails", len(problems) > 0)

    # ── 14b: comma-joined negative parallelism (live gate gap 2026-07-23) ─
    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nThis isn't a rep problem, it's a leadership failure to establish a system.")
    check("comma-form negative parallelism fails (shipped option 2 sentence)",
          has(problems, "comma form"))

    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nThat is not a process, it is a wish.")
    check("uncontracted comma-form negative parallelism fails",
          has(problems, "comma form"))

    # ── 15: signature stat allowlist survives ─────────────────────────────
    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nA great rep with AI is 3x more productive.")
    check("signature stat 3x allowlisted", not has(problems, "3x"),
          "; ".join(problems[:4]))

    # ── 16-21: constants hygiene ──────────────────────────────────────────
    check("STYLE_GUIDE has no Staccato mandate",
          "Staccato Style" not in STYLE_GUIDE and "One idea per line. Double space" not in STYLE_GUIDE)
    check("STYLE_GUIDE declares the format dead", "Staccato format is DEAD" in STYLE_GUIDE)
    check("VOICE_BIBLE 5th P is Psychology",
          "Performance / Psychology" in VOICE_BIBLE and "Performance / Culture" not in VOICE_BIBLE)
    # STYLE_GUIDE is allowed to contain the phrase once: as its own ban line.
    check("'Let that sink in' appears only as a ban, never as an example",
          all("Let that sink in" not in s for s in
              [VOICE_BIBLE, EXAMPLE_POSTS] + [s for s in OPENING_STYLES])
          and STYLE_GUIDE.count("Let that sink in") == 1
          and "Banned. Never." in STYLE_GUIDE)
    check("no emoji closer in VOICE_BIBLE", "👇" not in VOICE_BIBLE)
    check("EXAMPLE_POSTS carries the Vistage winner",
          "Vistage AI Masterclass" in EXAMPLE_POSTS)

    # ── 22: live persona (env override) is de-staccatoed ──────────────────
    check("LINKEDIN_PERSONA has no Staccato instruction",
          "staccato" not in config.LINKEDIN_PERSONA.lower())
    check("LINKEDIN_PERSONA carries the New Voice Bible",
          "New Voice Bible" in config.LINKEDIN_PERSONA)

    # ── Round-2 anti-pastiche checks (Greg: "the last gmail is still shit") ─
    OPTION1_SHIPPED = """A CEO in San Diego invested $50,000 in a new AI sales prospecting tool. His team went all-in, generating a flood of new leads and activities. Six months later, revenue hadn't moved an inch.

He couldn't grasp why the investment flopped. You simply can't scale chaos.

AI amplifies whatever system you have. If that system is broken, AI amplifies brokenness. His reps were just doing more of the wrong things, faster.

Before pouring AI on a problem, leaders must inspect their sales operating system. This means defining each of the 5 Pillars: Process, People, Pipeline, Performance, and Psychology. Start with process, not tools.

Without clear stages and exit criteria, or a disciplined coaching rhythm, any AI tool becomes just another shiny object speeding up an inefficient process.

Where are you starting the hard work of diagnosing your operating system before adding more AI?"""
    problems = _post_voice_gate(OPTION1_SHIPPED)
    check("shipped option 1 (the 'still shit' post) now fails on stuffing",
          has(problems, "signature-phrase stuffing"))
    check("shipped option 1 fails on missing first person",
          has(problems, "first-person"))
    check("shipped option 1 fails on case-study opener",
          has(problems, "case-study opener"))

    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nYou can't scale chaos. Inspect what you expect.")
    check("two signature phrases fails", has(problems, "stuffing"))

    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nAI amplifies whatever system you have. If you have chaos, AI amplifies chaos.")
    check("ONE full amplifier phrase does NOT count as stuffing",
          not has(problems, "stuffing"), "; ".join(problems[:3]))

    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nLeaders react to that 65% by chasing more tools.")
    check("bare reference back to the 65% signature stat is allowlisted",
          not has(problems, "invented statistic"), "; ".join(problems[:3]))

    problems = _post_voice_gate(
        "A VP of Sales rolled out a new tool last quarter.\n\n" + EXAMPLE_DOG)
    check("third-person character opener fails", has(problems, "case-study opener"))

    # ── Broetry paragraph structure (Greg 2026-07-23 night) ──────────────
    GOLD_721 = """A week of Vistage AI Masterclass sessions in Seattle. First time running my new workshop format: teach it, show it live, then the business owners build it themselves with AI before they leave the room.

More fun than I have had presenting in years. For a long time I sat up there as the talking head for three hours. This time the room did the work, and the aha moments kept coming.

Here is what I saw: every room already has one leader quietly ahead on AI. Sometimes the rest of the room found that out the same day. There was a great variety in AI experience, but we all came together that day to learn, pressure-test, and come out with some amazing results.

Thank you, Carla Corkern and Jess Hickey, for putting me in front of your groups. Sharp members, honest questions, zero spectators.

The gap between companies putting AI to work in sales and companies waiting is getting expensive. The CEOs in those rooms are not waiting.

If you chair a Vistage group and want this workshop in your room, let us talk."""
    check("Greg's real gold 7/21 post PASSES the broetry check",
          not has(_post_voice_gate(GOLD_721), "broetry"),
          "; ".join(_post_voice_gate(GOLD_721)[:3]))

    BROETRY = """For years I gave the same three-hour talk. Stand up, teach, watch the heads nod, sit down.

Last week in Seattle I threw that format out.

The new way: I teach one AI play, I show it live, then the business owners build it themselves before they leave the room. They do the work, I coach.

I haven't had that much fun presenting in years. A CEO who builds it themselves remembers it. One who watched me run a demo forgets it by Friday.

Every room already had one owner quietly ahead on AI. Half the time the rest of the group found out that same day.

Thank you Carla Corkern and Jess Hickey for the rooms. Sharp members, honest questions, zero spectators.

The gap between owners using AI in sales and owners still thinking about it widens every week. The ones in these rooms stopped thinking about it.

If you chair a Vistage group and want this in your room, let us talk."""
    check("the fragment version Greg rejected FAILS the broetry check",
          has(_post_voice_gate(BROETRY), "broetry"))

    GOOD_PARA = """For years I gave the same three-hour talk. Stand up, teach, watch the heads nod, sit down. Last week in Seattle I threw that format out. Now I teach one AI play, show it live, and the business owners build it themselves before they leave the room. They do the work, I coach.

I haven't had that much fun presenting in years. A CEO who builds it themselves remembers it. The one who watched me run a demo forgets it by Friday. And every room already had one owner quietly ahead on AI, though half the time the rest of the group only found that out the same day.

Thank you Carla Corkern and Jess Hickey for putting me in front of your groups. Sharp members, honest questions, zero spectators.

The gap between owners using AI in sales and owners still thinking about it widens every week, and the ones in these rooms have stopped thinking about it. If you chair a Vistage group and want this in your room, let us talk."""
    check("the grouped-paragraph rewrite PASSES the broetry check",
          not has(_post_voice_gate(GOOD_PARA), "broetry"),
          "; ".join(_post_voice_gate(GOOD_PARA)[:3]))

    # ── New Voice Bible Part 17 is the verbatim governing header ──────────
    check("Part 17 live instruction present verbatim",
          "recognizably like Greg and can survive contact" in NEW_VOICE_BIBLE_LIVE_INSTRUCTION
          and "apply the red-flag card and the only-you test" in NEW_VOICE_BIBLE_LIVE_INSTRUCTION)

    # ── Spoken-voice corpus wired in (2026-07-23 evening) ─────────────────
    check("spoken corpus carries verified excerpts",
          all(s in GREG_SPOKEN_VOICE for s in
              ["show up and throw up salespeople", "dirty socks",
               "I still get chills", "no, you're a sales guy"]))
    check("spoken corpus has no invented-stat joke or dashes",
          "64.3" not in GREG_SPOKEN_VOICE
          and chr(8212) not in GREG_SPOKEN_VOICE
          and chr(8211) not in GREG_SPOKEN_VOICE)
    check("spoken corpus keeps the written bans explicit",
          "written bans still apply" in GREG_SPOKEN_VOICE)

    # ── New gate checks: company size, markdown residue, announced emotion ─
    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nThat saved 400 hours for a mid-sized team.")
    check("company-size mention fails", has(problems, "company-size"))

    problems = _post_voice_gate(
        EXAMPLE_DOG.replace("this transcript", "this *exact* transcript"))
    check("markdown residue fails", has(problems, "markdown residue"))

    problems = _post_voice_gate(
        EXAMPLE_DOG + "\n\nMy irritation? Leaders who skip the basics.")
    check("announced irritation fails", has(problems, "announced irritation"))

    # ── Drop-not-kill resilience + batch variety (offline, stubbed) ───────
    import gemini_client as gc
    real_gen = gc.generate_linkedin_post
    calls = {"n": 0, "avoid_seen": []}

    def one_bad(uploaded_file, theme=None, avoid_notes=""):
        calls["n"] += 1
        calls["avoid_seen"].append(avoid_notes)
        if calls["n"] == 2:
            raise ValueError("stub: option failed gate")
        if calls["n"] == 1:
            return (theme[0] if theme else "t",
                    "stub post that got back 400 hours of selling")
        return (theme[0] if theme else "t", "stub post text")

    try:
        gc.time.sleep = lambda s: None
        gc.generate_linkedin_post = one_bad
        got = gc.generate_n_options("ref", 5)
        check("one failed option is dropped, survivors ship", len(got) == 4,
              f"got {len(got)}")
        check("batch variety: later options told to avoid used markers",
              any("400 hours" in a for a in calls["avoid_seen"][1:]),
              str(calls["avoid_seen"]))

        gc.generate_linkedin_post = lambda u, theme=None, avoid_notes="": (
            (_ for _ in ()).throw(ValueError("stub: all fail")))
        try:
            gc.generate_n_options("ref", 3)
            check("all options failing raises", False, "no exception raised")
        except ValueError:
            check("all options failing raises", True)
    finally:
        gc.generate_linkedin_post = real_gen

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{passed}/{total} tests passed")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
