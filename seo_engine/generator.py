"""
Article generator — turns one target keyword into a fully optimized article.

Every article is built to win in three places at once:

- SEO:  keyword in title/H1/slug/meta, 1,200-1,800 words, semantic headings.
- AEO:  a 40-60 word direct answer right under the H1 (featured-snippet and
        voice-assistant bait), question-phrased H2s, a real FAQ section.
- GEO:  concrete statistics, quotable one-liners, and named-expert attribution —
        the three things studies show generative engines actually cite.

Output is structured JSON so the publisher can render clean HTML + schema.
"""

import json
import re

from config import AUTHOR_NAME, LINKEDIN_PERSONA
from gemini_client import EXAMPLE_POSTS, get_gemini_client, _call_with_retry


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80].rstrip("-")


def _parse_json_response(text: str):
    """Parse the first JSON value in a model response, tolerating markdown
    fences and any prose before or after the JSON (Gemini sometimes appends
    trailing commentary, which json.loads rejects as "Extra data")."""
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("No JSON found in model response")
    value, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    return value


# Voice rule: em/en dashes are banned in everything Greg ships. The prompt
# forbids them; this backstop repairs any that slip through WITHOUT wrecking
# grammar. Paired dashes (a parenthetical: "data — news, financials — into")
# become commas; a lone dash becomes a colon.
def _fix_dashes_in_sentence(sentence: str) -> str:
    if sentence.count("—") >= 2:
        sentence = re.sub(r"\s*—\s*", ", ", sentence)
    else:
        sentence = re.sub(r"\s*—\s*", ": ", sentence)
    return sentence


def _strip_banned_dashes(value):
    if isinstance(value, str):
        if "—" in value:
            parts = re.split(r"(?<=[.!?])\s+", value)
            value = " ".join(_fix_dashes_in_sentence(p) for p in parts)
        return value.replace("–", "-")
    if isinstance(value, list):
        return [_strip_banned_dashes(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_banned_dashes(v) for k, v in value.items()}
    return value


# ── Deterministic voice gate ─────────────────────────────────────────────────
# Code-level enforcement of Greg's Voice DNA (anti-ai-writing-style.md) and the
# no-invented-numbers rule. Articles that fail get regenerated with feedback;
# an article that keeps failing kills the run. No fabricated stats ship under
# Greg's name, ever.

_BANNED_WORDS = [
    "delve", "realm", "harness", "unlock", "tapestry", "paradigm",
    "cutting-edge", "revolutionize", "intricate", "intricacies", "showcasing",
    "crucial", "pivotal", "meticulously", "vibrant", "unparalleled",
    "leverage", "synergy", "game-changer", "testament", "commendable",
    "meticulous", "groundbreaking", "foster", "showcase", "holistic",
    "garner", "accentuate", "pioneering", "trailblazing", "unleash",
    "transformative", "redefine", "seamless", "scalable", "robust",
    "empower", "streamline", "frictionless", "elevate", "effortless",
    "data-driven", "mission-critical", "visionary", "disruptive",
    "reimagine", "unprecedented", "leading-edge", "synergize", "democratize",
    "state-of-the-art", "immersive", "plug-and-play", "turnkey",
    "future-proof", "supercharge", "captivate", "playbook",
    "competitive landscape", "in today's", "let's dive", "dive in",
    "it's important to note", "it's worth noting", "at the end of the day",
    "furthermore", "moreover", "let that sink in", "studies show",
    "research shows", "actionable intelligence", "strategic advantage",
]

_NEG_PARALLELISM = [
    r"\bisn'?t (just )?(about )?[^.!?]{2,60}[.!?] (It|This|That)'?s?\b",
    # Uncontracted form the pattern above misses: "is not a people problem.
    # It is a process problem." (caught live 2026-07-16)
    r"\bis not (?:just )?(?:a |an |about )?[^.!?]{2,60}[.!?]\s+(?:It|This|That) is\b",
    r"\b(is )?[Nn]o?t (just )?about [^.!?]{2,60}[.!?]\s+(It|This|That)('s| is) about\b",
    r"\bYou don'?t need [^.!?]{2,60}[.!?] You need\b",
    r"\bForget [^.!?]{2,60}[.!?]",
    r"\bStop [a-z]+ing [^.!?]{2,60}[.!?] Start\b",
    r"\bThe question isn'?t\b",
    r"\b[A-Za-z ]{2,30} is dead[.!?]",
]

# Targets CLAIMED outcomes (the fabricated-credibility pattern), not advice
# math like "block 45 minutes" or "win back those 10 hours".
_FAKE_STAT = re.compile(
    r"\d+\s*(%|percent)"                                   # any percentage claim
    r"|\bby up to\b"                                       # "cut X by up to N"
    r"|\b\d+x\b"                                           # "3x your pipeline"
    r"|\b(I|we|my (clients|teams)|teams I work with)\b[^.!?]{0,80}\b(sav|cut|boost|increas|improv|reduc|grew|doubl)\w*[^.!?]{0,50}\b\d+\s*(minutes|hours|days|deals)",
    re.IGNORECASE,
)


def _article_text(article: dict) -> str:
    chunks = [article.get("title", ""), article.get("meta_description", ""),
              article.get("direct_answer", ""), article.get("linkedin_post", "")]
    chunks += article.get("key_takeaways", []) or []
    for s in article.get("sections", []) or []:
        chunks += [s.get("heading", ""), s.get("body_html", "")]
    for f in article.get("faqs", []) or []:
        chunks += [f.get("question", ""), f.get("answer", "")]
    return " ".join(re.sub(r"<[^>]+>", " ", c) for c in chunks if c)


def _sentence_with(text: str, idx: int) -> str:
    """The sentence around character position idx, for repair feedback."""
    start = max(text.rfind(".", 0, idx), text.rfind("?", 0, idx),
                text.rfind("!", 0, idx)) + 1
    end = len(text)
    for ch in ".?!":
        p = text.find(ch, idx)
        if p != -1:
            end = min(end, p + 1)
    return text[start:end].strip()


def voice_gate(article: dict) -> list:
    """Return the list of violations (empty = clean), each quoting the
    offending sentence so a repair pass can fix it surgically."""
    text = _article_text(article)
    low = text.lower()
    violations = []
    for w in _BANNED_WORDS:
        i = low.find(w)
        if i != -1:
            violations.append(
                f'banned word/phrase "{w}" in: "{_sentence_with(text, i)}"')
    for pat in _NEG_PARALLELISM:
        m = re.search(pat, text)
        if m:
            violations.append(
                f'negative-parallelism (state only the positive claim) in: '
                f'"{_sentence_with(text, m.start())}"')
    for m in _FAKE_STAT.finditer(text):
        violations.append(
            f'invented statistic/claim in: "{_sentence_with(text, m.start())}"')
    if "—" in text or "–" in text:
        violations.append("em/en dash present")
    return violations


# Last-resort deterministic swaps for stubborn single banned words. Same part
# of speech, so a word-level replace stays grammatical.
_SYNONYM_FIX = {
    "seamless": "smooth", "seamlessly": "smoothly", "crucial": "essential",
    "pivotal": "central", "foster": "build", "fosters": "builds",
    "elevate": "raise", "elevates": "raises", "redefine": "reshape",
    "redefines": "reshapes", "unprecedented": "rare", "leverage": "use",
    "leverages": "uses", "leveraging": "using", "robust": "solid",
    "empower": "equip", "empowers": "equips", "streamline": "simplify",
    "streamlines": "simplifies", "harness": "use", "unleash": "release",
    "transformative": "powerful", "holistic": "complete", "unlock": "open up",
    "supercharge": "boost", "effortless": "easy", "scalable": "repeatable",
    "frictionless": "smooth", "meticulous": "careful", "meticulously": "carefully",
}


# The Voice Bible's own fix for negative parallelism, applied literally:
# "delete everything before the positive claim." For the pair pattern
# "X isn't A. It's B." keep only "It's B." Standalone "Forget X." gets cut.
_NEG_PAIR = re.compile(
    r"(?:[A-Z][^.!?<>]{0,80}\bis(?:n'?t| not)\b[^.!?<>]{1,60}[.!?])\s*"
    r"((?:It|This|That)(?:'s| is)\b[^.!?]{1,120}[.!?])"
)
_FORGET = re.compile(r"\bForget [^.!?<>]{2,60}[.!?]\s*")


def _fix_neg_parallelism(value):
    if isinstance(value, str):
        value = _NEG_PAIR.sub(r"\1", value)
        return _FORGET.sub("", value)
    if isinstance(value, list):
        return [_fix_neg_parallelism(v) for v in value]
    if isinstance(value, dict):
        return {k: _fix_neg_parallelism(v) for k, v in value.items()}
    return value


def _apply_synonym_fix(value):
    if isinstance(value, str):
        for bad, good in _SYNONYM_FIX.items():
            value = re.sub(rf"\b{bad}\b", good, value)
            value = re.sub(rf"\b{bad.capitalize()}\b", good.capitalize(), value)
        return value
    if isinstance(value, list):
        return [_apply_synonym_fix(v) for v in value]
    if isinstance(value, dict):
        return {k: _apply_synonym_fix(v) for k, v in value.items()}
    return value


def generate_article(topic: dict) -> dict:
    """
    Generate a complete SEO/AEO/GEO-optimized article for a topic
    ({"keyword": ..., "title": ...}). Returns a structured article dict.
    """
    client = get_gemini_client()
    keyword = topic["keyword"]
    working_title = topic.get("title", keyword.title())

    prompt = f"""{LINKEDIN_PERSONA}

You are {AUTHOR_NAME}, sales leadership strategist and Vistage speaker,
writing a long-form article for your website. This is an ARTICLE, so paragraphs
can be 2-4 sentences and total length must be 1,200-1,800 words. Write like a
sharp human who happens to be typing.

VOICE DNA (hard rules, one violation fails the article):

1. NEVER invent statistics, percentages, or research results. No "60% of
   teams", no "cut research time by 45 minutes", no "in my work with clients,
   deal value increased 20%", no "studies show". ZERO fabricated numbers or
   outcomes. You may use numbers only two ways: (a) simple illustrative math
   the reader can check themselves ("a rep making 30 calls a week has 1,500
   conversations a year"), clearly framed as an example, or (b) plain counts
   in advice ("block 45 minutes", "ask these 5 questions"). Authority comes
   from specificity of PROCESS: exact steps, exact questions, exact meeting
   agendas. Never from claimed data.
2. NEVER use an em dash or en dash anywhere. Commas, periods, colons,
   parentheses.
3. Negative parallelism is FATAL. Never "It's not about X. It's about Y.",
   "Not X. Y.", "Forget X...", "You don't need X. You need Y.", "X is dead.",
   "The question isn't X...", or ANY sentence that negates one framing and
   then asserts a corrected one. Just state the positive claim.
4. Banned vocabulary (the AI fingerprint): delve, leverage, landscape,
   unlock, harness, elevate, foster, navigate, robust, seamless, streamline,
   empower, transformative, game-changer, cutting-edge, crucial, pivotal,
   holistic, scalable, optimize, supercharge, unleash, revolutionize,
   paradigm, synergy, tapestry, realm, actionable, strategic advantage,
   playbook (say "system" or "framework"), plus dead phrases: "In today's...",
   "It's important to note", "Let's dive in", "At the end of the day",
   "Furthermore", "Moreover", "That said".
5. No extended metaphors. No military, sniper, hunting, war, or sports
   metaphor systems running through the article. One light analogy maximum,
   then drop it.
6. No puffery ("a pivotal moment", "marking a significant shift"). No rule of
   three ("speed, efficiency, and innovation"). No meta commentary ("In this
   section we will..."). Use "is" and "has", never "serves as" or "represents".
7. Rhythm: vary sentence length. Short punchy lines mixed with longer ones.
   1-3 sentence paragraphs. Start sentences with And, But, So when natural.
   Contractions always. Direct address ("you"), active voice, first person
   where it's genuinely Greg's view.
8. Never mention company sizes or team sizes.
9. Section headings in sentence case, phrased as questions a real buyer asks.
10. Program facts, when a topic touches Greg's own offerings: the programs are
   CASL (Certified AI Sales Leader), CASH (Certified AI Sales Hunter), REAP,
   CASC, CASX, the Sales Leadership Forum, and Workshops. The Forum is a
   founding cohort now forming: NEVER claim existing members, member counts,
   or testimonials for anything. NEVER describe module-by-module curriculum
   details. NEVER state prices. Point readers to theaisalesleader.com.

VOICE BIBLE (the DOs — this is what makes the article sound like Greg and not
like any other sales writer; the rules above only remove AI tells, THIS adds
the voice):

A. You are an OPERATOR writing from the field. 30+ years walking into broken
   sales orgs and fixing them with systems. Write first-person lived
   experience: "I've seen this in dozens of organizations", "In my first 48
   hours inside a broken sales org, I look for patterns", "The reasons are
   never what the CEO thinks they are", "every CEO who calls me about this".
   At least 2 sections must carry a first-person operator observation.
B. Signature Greg lines. Work 2-3 of these in naturally where they genuinely
   fit (never force them, never stack them): "Here's the reality:",
   "Here's what I've seen:", "You can't scale chaos",
   "Never automate a broken system", "Start with process, not tools",
   "AI is a multiplier, not a replacement",
   "AI amplifies whatever system you have. If you have chaos, AI amplifies
   chaos.", "If it lives in one rep's head, it isn't a process",
   "Your ceiling is your team quality", "optimistic fiction" (bad forecasts),
   "heroics or luck" (what broken orgs run on),
   "Your calendar is your operating plan", "Simple as that." (tactical close).
C. Name Greg's own systems BY NAME when the topic touches them (this is his
   IP and his differentiation): the 5 P's (Process, People, Pipeline,
   Performance, Psychology), the 12 Silent Killers, the Three-Bucket Forecast
   and its three questions (Commit: "Would you bet your job on this closing
   this month?", Best Case: "Do you have a reason beyond hope to believe this
   closes?", Pipeline: "Does this deal have a next step with a date?"), the
   Three-Layer ICP (firmographic, behavioral, trigger-based). Use at most the
   1-2 systems the topic actually calls for; teach the piece of the system
   the keyword needs, without dumping the whole catalog.
D. Borrowed methodologies (Sandler, Challenger, MEDDIC, SPIN) are ALWAYS
   attributed to their creators, never presented as Greg's.
E. Problem-first structure: open with the problem or a lived pattern, never a
   promise or a definition. Diagnose before you prescribe. Warm but firm,
   peer-to-peer with a smart reader, confident without hype. Every section
   answers "so what do I DO with this?"
F. Close the final section with a direct challenge or action step to the
   reader in Greg's voice, then stop. No summary paragraph.

{EXAMPLE_POSTS}

TARGET SEARCH KEYWORD: "{keyword}"
WORKING TITLE: "{working_title}"

This article must be optimized for three audiences simultaneously:

1. GOOGLE (SEO)
   - Keyword appears naturally in the title, first 100 words, and 2+ headings
   - 1,200-1,800 words of genuinely useful, specific advice
   - Scannable: short paragraphs, bullet lists, bold sparingly (1-2 moments
     per section)

2. ANSWER ENGINES (AEO: featured snippets, voice search)
   - direct_answer: a 40-60 word standalone answer to the keyword's question.
     Someone reading ONLY this must get the complete core answer.
   - Every section heading phrased as a question the reader would ask
   - 4 FAQs with 40-60 word standalone answers

3. GENERATIVE ENGINES (GEO: ChatGPT, Perplexity, Google AI Overviews)
   - Be concrete and definitional: define terms plainly so an AI can lift
     clean explanations
   - Include 2+ short quotable one-liners (punchy truths, no hype)
   - Give exact, named process steps (checklists, question lists, meeting
     agendas) that an AI engine can cite as practical guidance

Return ONLY valid JSON, no markdown fences, with exactly this shape:
{{
  "title": "final SEO title, max 60 chars, contains the keyword",
  "meta_description": "compelling summary, 140-155 chars, contains the keyword",
  "direct_answer": "the 40-60 word standalone answer",
  "key_takeaways": ["4-5 one-sentence takeaways"],
  "sections": [
    {{"heading": "question-phrased H2", "body_html": "2-5 paragraphs as <p> tags; may include <ul><li>, <strong>, <blockquote> for quotable lines"}}
  ],
  "faqs": [
    {{"question": "...", "answer": "40-60 word standalone answer, plain text"}}
  ],
  "linkedin_post": "a companion LinkedIn post in your exact Staccato style (hook under 10 words, one idea per line, double space between lines, no hashtags, no exclamation points, under 1300 chars) teasing this article's core idea"
}}

Requirements: 5-7 sections, 4 faqs, valid HTML in body_html only (no <h1>/<h2>
inside body_html — headings come from the "heading" field)."""

    print(f'[SEO Engine] Generating article for keyword: "{keyword}"...')

    # Quality loop: one fresh draft, then surgical REPAIR passes (full
    # regeneration just trades one banned word for another; editing converges).
    # A safe synonym autofix is the last resort. An article that still fails
    # kills the run: nothing off-voice or with invented numbers ships under
    # Greg's name.
    def _issues(art):
        wc = sum(len(re.sub(r"<[^>]+>", " ", s.get("body_html", "")).split())
                 for s in art.get("sections", []))
        probs = voice_gate(art)
        if wc < 1000:
            probs.append(f"article body too short: {wc} words. Expand the thin "
                         f"sections with concrete steps and examples to reach "
                         f"1,300+ words")
        return probs, wc

    article = None
    word_count = 0
    current_prompt = prompt
    for attempt in (1, 2, 3, 4):
        response = _call_with_retry(
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[current_prompt],
            )
        )
        try:
            article = _strip_banned_dashes(_parse_json_response(response.text))
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[SEO Engine] Attempt {attempt}: response was not valid JSON ({e})")
            if attempt == 4:
                raise
            current_prompt = prompt + (
                "\n\nYOUR PREVIOUS RESPONSE WAS NOT VALID JSON. Return exactly "
                "ONE valid JSON object and nothing else. Escape every double "
                "quote inside string values as \\\" and do not use raw line "
                "breaks inside strings."
            )
            continue
        problems, word_count = _issues(article)
        if not problems:
            break
        print(f"[SEO Engine] Attempt {attempt} failed the voice gate "
              f"({len(problems)} issue(s)): {'; '.join(p[:90] for p in problems[:4])}")
        if attempt == 4:
            break
        # Repair mode: hand back the exact draft with the quoted violations.
        current_prompt = (
            prompt
            + "\n\nHERE IS YOUR DRAFT, WHICH FAILED REVIEW:\n"
            + json.dumps(article, ensure_ascii=False)
            + "\n\nFix ONLY these specific violations by rewriting the quoted "
              "sentences (and expanding thin sections if flagged short). Keep "
              "everything else exactly as written. Return the full corrected "
              "JSON object and nothing else:\n- "
            + "\n- ".join(problems[:12])
        )

    # Last resort: deterministic fixes (synonym swaps for stubborn banned
    # words, the Voice Bible's delete-the-negation cut for parallelisms),
    # then one final verdict.
    problems, word_count = _issues(article)
    if problems:
        article = _apply_synonym_fix(_fix_neg_parallelism(article))
        problems, word_count = _issues(article)
    if problems:
        raise ValueError(
            "Article failed the voice gate after 4 attempts + autofix: "
            + "; ".join(p[:120] for p in problems[:6])
        )

    # Fill in the metadata the publisher needs
    article["keyword"] = keyword
    article["slug"] = _slugify(article.get("title") or working_title)
    for field in ("title", "meta_description", "direct_answer", "sections", "faqs"):
        if not article.get(field):
            raise ValueError(f"Gemini response missing required field: {field}")

    print(f"[SEO Engine] Article generated: \"{article['title']}\" (~{word_count} words)")
    return article
