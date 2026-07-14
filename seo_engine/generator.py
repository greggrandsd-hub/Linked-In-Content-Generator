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
# forbids them, and this guarantees it even when the model slips.
def _strip_banned_dashes(value):
    if isinstance(value, str):
        value = value.replace(" — ", ": ").replace("—", ": ")
        return value.replace("–", "-")
    if isinstance(value, list):
        return [_strip_banned_dashes(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_banned_dashes(v) for k, v in value.items()}
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

You are {AUTHOR_NAME} — sales leadership strategist and Vistage speaker —
writing a long-form article for your website. Your LinkedIn voice (see examples
below) carries over: direct, opinionated, staccato lines, analogies,
no corporate fluff, no AI words (delve, leverage, landscape, unlock, harness,
elevate, foster, navigate, robust). But this is an ARTICLE, so paragraphs can
be 2-4 sentences and total length must be 1,200-1,800 words.

NON-NEGOTIABLE STYLE RULES:
- NEVER use an em dash or en dash anywhere. Use a colon or two sentences.
- NEVER use the word "playbook". Say "system", "framework", or "guide".
- NEVER use the pattern "It's not about X. It's about Y." or "Not X. Y."
- Never mention company sizes or team sizes.

{EXAMPLE_POSTS}

TARGET SEARCH KEYWORD: "{keyword}"
WORKING TITLE: "{working_title}"

This article must be optimized for three audiences simultaneously:

1. GOOGLE (SEO)
   - Keyword appears naturally in the title, first 100 words, and 2+ headings
   - 1,200-1,800 words of genuinely useful, specific advice
   - Scannable: short paragraphs, bullet lists, bold key phrases

2. ANSWER ENGINES (AEO — featured snippets, voice search)
   - direct_answer: a 40-60 word standalone answer to the keyword's question.
     Someone reading ONLY this must get the complete core answer.
   - Every section heading phrased as a question the reader would ask
   - 4 FAQs with 40-60 word standalone answers

3. GENERATIVE ENGINES (GEO — ChatGPT, Perplexity, Google AI Overviews)
   - Include 3+ concrete numbers/statistics (realistic, from your experience —
     phrase as "In my work with sales teams..." not fake citations)
   - Include 2+ short quotable one-liners (your signature punchy truths)
   - Define terms plainly so an AI can lift clean explanations

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

    # Length gate: Gemini sometimes undershoots the 1,200-word floor (article 2
    # came in at ~800). One retry with an explicit expansion demand.
    article = None
    for attempt in (1, 2):
        response = _call_with_retry(
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
            )
        )
        article = _strip_banned_dashes(_parse_json_response(response.text))
        word_count = sum(
            len(re.sub(r"<[^>]+>", " ", s.get("body_html", "")).split())
            for s in article.get("sections", [])
        )
        if word_count >= 1000:
            break
        if attempt == 1:
            print(f"[SEO Engine] Draft too short ({word_count} words), regenerating deeper...")
            prompt += (
                "\n\nIMPORTANT: your previous draft was too short. The article "
                "body MUST total at least 1,300 words across the sections. Go "
                "deeper on every section: add a concrete example, a step list, "
                "or a number from your experience to each one."
            )

    # Fill in the metadata the publisher needs
    article["keyword"] = keyword
    article["slug"] = _slugify(article.get("title") or working_title)
    for field in ("title", "meta_description", "direct_answer", "sections", "faqs"):
        if not article.get(field):
            raise ValueError(f"Gemini response missing required field: {field}")

    print(f"[SEO Engine] Article generated: \"{article['title']}\" (~{word_count} words)")
    return article
