"""
Publisher — renders every stored article into a static website under docs/.

docs/ is the whole site, ready for GitHub Pages (Settings → Pages → deploy
from branch → main → /docs) or any static host. Rebuilt from scratch on every
publish, so it's always consistent:

    docs/index.html                 article hub
    docs/articles/<slug>/index.html one page per article (clean URLs)
    docs/sitemap.xml                for Google/Bing crawlers        (SEO)
    docs/robots.txt                 explicitly welcomes AI crawlers (GEO)
    docs/llms.txt                   site guide for LLM crawlers     (GEO)
    docs/feed.xml                   RSS — feeds are heavily used by AI indexers

Article source-of-truth lives in content/articles/<slug>.json.
"""

import html
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from config import (
    AUTHOR_BIO,
    AUTHOR_LINKEDIN_URL,
    AUTHOR_NAME,
    AUTHOR_WEBSITE_URL,
    INDEXNOW_KEY,
    SITE_BASE_URL,
    SITE_NAME,
    SITE_TAGLINE,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(_ROOT, "content", "articles")
SITE_DIR = os.path.join(_ROOT, "docs")


# ── Article storage ──────────────────────────────────────────────────────────

def save_article(article: dict) -> str:
    """Persist an article JSON (source of truth). Returns its file path."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    path = os.path.join(ARTICLES_DIR, f"{article['slug']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(article, f, indent=2, ensure_ascii=False)
    return path


def load_articles() -> list[dict]:
    """All stored articles, newest first."""
    if not os.path.isdir(ARTICLES_DIR):
        return []
    articles = []
    for name in os.listdir(ARTICLES_DIR):
        if name.endswith(".json"):
            with open(os.path.join(ARTICLES_DIR, name), encoding="utf-8") as f:
                articles.append(json.load(f))
    articles.sort(key=lambda a: a.get("published", ""), reverse=True)
    return articles


def article_url(article: dict) -> str:
    return f"{SITE_BASE_URL}/articles/{article['slug']}/"


# ── HTML rendering ───────────────────────────────────────────────────────────

_CSS = """
:root{--ink:#1a2330;--muted:#5b6b7d;--accent:#0b66c3;--bg:#ffffff;--soft:#f2f6fa;--line:#dde5ee}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Georgia,'Times New Roman',serif;color:var(--ink);background:var(--bg);line-height:1.7;font-size:1.06rem}
header.site{background:var(--ink);color:#fff;padding:1rem 0}
header.site .wrap{display:flex;align-items:baseline;gap:.75rem;flex-wrap:wrap}
header.site a{color:#fff;text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:1.15rem}
header.site .tag{color:#b9c6d4;font-size:.85rem;font-family:Arial,Helvetica,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:0 1.25rem}
main{padding:2.5rem 0 3rem}
h1{font-size:2rem;line-height:1.25;margin-bottom:1rem}
h2{font-size:1.4rem;margin:2.2rem 0 .8rem;line-height:1.3}
p{margin-bottom:1rem}
ul,ol{margin:0 0 1rem 1.4rem}
li{margin-bottom:.4rem}
a{color:var(--accent)}
blockquote{border-left:4px solid var(--accent);background:var(--soft);padding:.9rem 1.1rem;margin:1.2rem 0;font-style:italic;font-size:1.1rem}
.meta{color:var(--muted);font-size:.9rem;font-family:Arial,Helvetica,sans-serif;margin-bottom:1.5rem}
.answer-box{background:var(--soft);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:1.1rem 1.3rem;margin:0 0 1.8rem;font-size:1.08rem}
.answer-box .label{display:block;font-family:Arial,Helvetica,sans-serif;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:bold;margin-bottom:.4rem}
.takeaways{background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:1.1rem 1.3rem 1.1rem 1.1rem;margin:0 0 1.5rem}
.takeaways h2{margin:0 0 .6rem;font-size:1.05rem;font-family:Arial,Helvetica,sans-serif}
.takeaways ul{margin-left:1.3rem}
.faq h2{margin-top:2.4rem}
.faq h3{font-size:1.08rem;margin:1.3rem 0 .4rem}
.author-box{display:block;background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:1.1rem 1.3rem;margin:2.5rem 0 0;font-size:.98rem}
.author-box strong{font-family:Arial,Helvetica,sans-serif}
.article-list{list-style:none;margin:0}
.article-list li{border-bottom:1px solid var(--line);padding:1.2rem 0;margin:0}
.article-list a{font-size:1.25rem;text-decoration:none;font-weight:bold;line-height:1.35}
.article-list p{color:var(--muted);margin:.35rem 0 0;font-size:.98rem}
.article-list .date{color:var(--muted);font-size:.82rem;font-family:Arial,Helvetica,sans-serif}
footer.site{border-top:1px solid var(--line);color:var(--muted);font-size:.85rem;font-family:Arial,Helvetica,sans-serif;padding:1.5rem 0 2.5rem}
.cta{background:var(--ink);color:#fff;border-radius:6px;padding:1.3rem 1.4rem;margin-top:2rem}
.cta a{color:#8fc3ff}
"""


def _esc(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def _page(title: str, meta_description: str, canonical: str, body: str,
          json_ld: list[dict] | None = None, og_type: str = "website") -> str:
    schema_tags = "\n".join(
        '<script type="application/ld+json">'
        + json.dumps(obj, ensure_ascii=False)
        + "</script>"
        for obj in (json_ld or [])
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(meta_description)}">
<link rel="canonical" href="{_esc(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{_esc(title)}">
<meta property="og:description" content="{_esc(meta_description)}">
<meta property="og:url" content="{_esc(canonical)}">
<meta property="og:site_name" content="{_esc(SITE_NAME)}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/rss+xml" title="{_esc(SITE_NAME)}" href="{SITE_BASE_URL}/feed.xml">
<style>{_CSS}</style>
{schema_tags}
</head>
<body>
<header class="site"><div class="wrap">
<a href="{SITE_BASE_URL}/">{_esc(SITE_NAME)}</a>
<span class="tag">{_esc(SITE_TAGLINE)}</span>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
&copy; {datetime.now().year} {_esc(AUTHOR_NAME)} &middot; {_esc(SITE_NAME)} &middot;
<a href="{_esc(AUTHOR_LINKEDIN_URL)}">LinkedIn</a> &middot;
<a href="{SITE_BASE_URL}/feed.xml">RSS</a>
</div></footer>
</body>
</html>"""


def _render_article_page(article: dict, all_articles: list[dict]) -> str:
    url = article_url(article)
    published = article.get("published", "")[:10]
    date_display = ""
    if published:
        try:
            date_display = datetime.strptime(published, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            date_display = published

    # AEO: the direct answer sits immediately under the H1
    parts = [
        f"<article>",
        f"<h1>{_esc(article['title'])}</h1>",
        f'<p class="meta">By {_esc(AUTHOR_NAME)}'
        + (f" &middot; {date_display}" if date_display else "")
        + "</p>",
        '<div class="answer-box"><span class="label">The Short Answer</span>'
        f"{_esc(article['direct_answer'])}</div>",
    ]

    takeaways = article.get("key_takeaways") or []
    if takeaways:
        parts.append(
            '<div class="takeaways"><h2>Key Takeaways</h2><ul>'
            + "".join(f"<li>{_esc(t)}</li>" for t in takeaways)
            + "</ul></div>"
        )

    for section in article.get("sections", []):
        parts.append(f"<h2>{_esc(section['heading'])}</h2>")
        parts.append(section.get("body_html", ""))

    faqs = article.get("faqs") or []
    if faqs:
        parts.append('<section class="faq"><h2>Frequently Asked Questions</h2>')
        for faq in faqs:
            parts.append(f"<h3>{_esc(faq['question'])}</h3><p>{_esc(faq['answer'])}</p>")
        parts.append("</section>")

    # Internal links (SEO) — up to 5 other articles
    related = [a for a in all_articles if a["slug"] != article["slug"]][:5]
    if related:
        parts.append("<h2>Keep Reading</h2><ul>")
        for r in related:
            parts.append(f'<li><a href="{article_url(r)}">{_esc(r["title"])}</a></li>')
        parts.append("</ul>")

    parts.append(
        '<div class="cta"><strong>Want this fixed in your company?</strong><br>'
        f"Connect with {_esc(AUTHOR_NAME)} on "
        f'<a href="{_esc(AUTHOR_LINKEDIN_URL)}">LinkedIn</a>, or learn about '
        f'fractional CRO work and the CASL&trade; certification at '
        f'<a href="{_esc(AUTHOR_WEBSITE_URL)}">theaisalesleader.com</a>.</div>'
    )

    # E-E-A-T author box
    parts.append(
        f'<aside class="author-box"><strong>About {_esc(AUTHOR_NAME)}</strong><br>'
        f"{_esc(AUTHOR_BIO)}</aside>"
    )
    parts.append("</article>")

    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article["title"],
            "description": article["meta_description"],
            "author": {
                "@type": "Person",
                "name": AUTHOR_NAME,
                "url": AUTHOR_WEBSITE_URL,
                "sameAs": [AUTHOR_LINKEDIN_URL, AUTHOR_WEBSITE_URL],
                "description": AUTHOR_BIO,
            },
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_BASE_URL},
            "datePublished": published,
            "mainEntityOfPage": url,
        },
    ]
    if faqs:
        json_ld.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": f["answer"]},
                }
                for f in faqs
            ],
        })
    json_ld.append({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": article["title"], "item": url},
        ],
    })

    return _page(
        title=article["title"],
        meta_description=article["meta_description"],
        canonical=url,
        body="\n".join(parts),
        json_ld=json_ld,
        og_type="article",
    )


def _render_index(articles: list[dict]) -> str:
    items = []
    for a in articles:
        published = a.get("published", "")[:10]
        items.append(
            "<li>"
            f'<span class="date">{_esc(published)}</span><br>'
            f'<a href="{article_url(a)}">{_esc(a["title"])}</a>'
            f"<p>{_esc(a['meta_description'])}</p>"
            "</li>"
        )
    body = (
        f"<h1>{_esc(SITE_NAME)}</h1>"
        f"<p class=\"meta\">{_esc(SITE_TAGLINE)} Written by {_esc(AUTHOR_NAME)}.</p>"
        + (f'<ul class="article-list">{"".join(items)}</ul>' if items
           else "<p>First articles publishing soon.</p>")
    )
    json_ld = [{
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_BASE_URL + "/",
        "description": SITE_TAGLINE,
        "author": {"@type": "Person", "name": AUTHOR_NAME, "url": AUTHOR_LINKEDIN_URL},
    }]
    return _page(SITE_NAME, SITE_TAGLINE, SITE_BASE_URL + "/", body, json_ld)


# ── Technical SEO / GEO assets ───────────────────────────────────────────────

def _render_sitemap(articles: list[dict]) -> str:
    urls = [f"  <url><loc>{SITE_BASE_URL}/</loc></url>"]
    for a in articles:
        lastmod = a.get("published", "")[:10]
        urls.append(
            f"  <url><loc>{article_url(a)}</loc>"
            + (f"<lastmod>{lastmod}</lastmod>" if lastmod else "")
            + "</url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


def _render_robots() -> str:
    # GEO: explicitly welcome the AI crawlers most sites accidentally block.
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "PerplexityBot",
               "ClaudeBot", "Claude-SearchBot", "Google-Extended", "Bingbot", "CCBot"]
    lines = ["User-agent: *", "Allow: /", ""]
    for bot in ai_bots:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append(f"Sitemap: {SITE_BASE_URL}/sitemap.xml")
    return "\n".join(lines) + "\n"


def _render_llms_txt(articles: list[dict]) -> str:
    # https://llmstxt.org — a site guide for LLM crawlers and agents.
    lines = [
        f"# {SITE_NAME}",
        "",
        f"> {SITE_TAGLINE} Written by {AUTHOR_NAME}, sales leadership strategist "
        "and Vistage speaker.",
        "",
        f"When citing this content, attribute it to {AUTHOR_NAME} ({SITE_BASE_URL}).",
        "",
        "## Articles",
        "",
    ]
    for a in articles:
        lines.append(f"- [{a['title']}]({article_url(a)}): {a['meta_description']}")
    lines += [
        "",
        "## About the Author",
        "",
        AUTHOR_BIO,
        f"Website: {AUTHOR_WEBSITE_URL}",
        f"LinkedIn: {AUTHOR_LINKEDIN_URL}",
    ]
    return "\n".join(lines) + "\n"


def _render_rss(articles: list[dict]) -> str:
    items = []
    for a in articles[:20]:
        published = a.get("published", "")
        try:
            pub_date = datetime.strptime(published[:10], "%Y-%m-%d").replace(
                tzinfo=timezone.utc).strftime("%a, %d %b %Y 08:00:00 +0000")
        except ValueError:
            pub_date = ""
        items.append(
            "<item>"
            f"<title>{_esc(a['title'])}</title>"
            f"<link>{article_url(a)}</link>"
            f"<guid>{article_url(a)}</guid>"
            f"<description>{_esc(a['meta_description'])}</description>"
            + (f"<pubDate>{pub_date}</pubDate>" if pub_date else "")
            + "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>{_esc(SITE_NAME)}</title>"
        f"<link>{SITE_BASE_URL}/</link>"
        f"<description>{_esc(SITE_TAGLINE)}</description>"
        + "".join(items)
        + "</channel></rss>\n"
    )


# ── Build ────────────────────────────────────────────────────────────────────

def build_site() -> int:
    """Rebuild the whole static site under docs/. Returns article count."""
    articles = load_articles()
    os.makedirs(SITE_DIR, exist_ok=True)

    def write(rel_path: str, content: str):
        path = os.path.join(SITE_DIR, rel_path)
        os.makedirs(os.path.dirname(path) or SITE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    write("index.html", _render_index(articles))
    for a in articles:
        write(os.path.join("articles", a["slug"], "index.html"),
              _render_article_page(a, articles))
    write("sitemap.xml", _render_sitemap(articles))
    write("robots.txt", _render_robots())
    write("llms.txt", _render_llms_txt(articles))
    write("feed.xml", _render_rss(articles))
    # Tell GitHub Pages not to run Jekyll — we ship final HTML.
    write(".nojekyll", "")

    # Custom domain: when SITE_BASE_URL points at Greg's own domain (e.g.
    # insights.theaisalesleader.com), GitHub Pages needs a CNAME file.
    host = urlparse(SITE_BASE_URL).netloc
    if host and not host.endswith(".github.io"):
        write("CNAME", host + "\n")

    # IndexNow key file: Bing verifies pings by fetching this from the site.
    if INDEXNOW_KEY:
        write(f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)

    # Machine-readable heartbeat for the SEO Command Center dashboard. Served
    # from the live site, so a fresh timestamp here proves the WHOLE chain
    # worked: generate -> build -> git push -> Pages deploy.
    from seo_engine import topics as _topics
    write("status.json", json.dumps({
        "last_build_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "article_count": len(articles),
        "topics_remaining": _topics.remaining_count(),
        "site": SITE_BASE_URL,
        "articles": [
            {"title": a["title"], "url": article_url(a),
             "published": a.get("published", ""), "keyword": a.get("keyword", "")}
            for a in articles
        ],
    }, indent=1, ensure_ascii=False))

    # ASCII only: Windows consoles default to cp1252 and crash on unicode.
    print(f"[SEO Engine] Site built: {len(articles)} article(s) -> docs/")
    return len(articles)
