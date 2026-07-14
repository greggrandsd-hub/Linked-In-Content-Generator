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


def _parse_json_response(text: str) -> dict:
    """Parse Gemini's JSON output, tolerating markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return json.loads(text.strip())


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
below) carries over: direct, opinionated, staccato lines, em dashes, analogies,
no corporate fluff, no AI words (delve, leverage, landscape, unlock, harness,
elevate, foster, navigate, robust). But this is an ARTICLE, so paragraphs can
be 2-4 sentences and total length must be 1,200-1,800 words.

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
    response = _call_with_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
    )

    article = _parse_json_response(response.text)

    # Fill in the metadata the publisher needs
    article["keyword"] = keyword
    article["slug"] = _slugify(article.get("title") or working_title)
    for field in ("title", "meta_description", "direct_answer", "sections", "faqs"):
        if not article.get(field):
            raise ValueError(f"Gemini response missing required field: {field}")

    word_count = sum(
        len(re.sub(r"<[^>]+>", " ", s.get("body_html", "")).split())
        for s in article["sections"]
    )
    print(f"[SEO Engine] Article generated: \"{article['title']}\" (~{word_count} words)")
    return article
