# G Squared SEO / AEO / GEO Engine

A fully automated organic-visibility engine. Once switched on, it publishes one
keyword-targeted article **every day** in Greg's voice — optimized for Google
(SEO), featured snippets and voice search (AEO), and AI engines like ChatGPT,
Perplexity, and Google AI Overviews (GEO) — with **zero manual work**.

## What it does on every run

1. **Picks the next topic** from a queue of long-tail, question-intent keywords
   in the sales-leadership niche (`content/topic_queue.json`). When the queue
   runs low it asks Gemini to research and add 20 more — it never runs dry.
2. **Generates a 1,200–1,800 word article** in Greg's Staccato voice with:
   - keyword-optimized title, meta description, and slug (SEO)
   - a 40–60 word "Short Answer" box right under the headline — featured-snippet
     and AI-citation bait (AEO)
   - question-phrased headings and a real FAQ section (AEO)
   - statistics, quotable one-liners, and named-author attribution — the things
     generative engines actually cite (GEO)
3. **Rebuilds the static site** under `docs/`, including:
   - `sitemap.xml`, `robots.txt` (explicitly welcomes GPTBot, PerplexityBot,
     ClaudeBot, etc.), `llms.txt` (the site guide AI crawlers read), RSS feed
   - Article, FAQPage, and BreadcrumbList JSON-LD schema on every page
   - internal links between articles
4. **Drops a companion LinkedIn post** into the Saved queue in the web UI —
   every article automatically feeds the LinkedIn engine too.
5. **Emails Greg** the live link + the LinkedIn post.

## One-time setup (~10 minutes, then never again)

### 1. Add the Gemini key to GitHub

Repo → **Settings → Secrets and variables → Actions → New repository secret**

- `GEMINI_API_KEY` — required
- `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT` — optional, for the
  daily notification email

### 2. Turn on GitHub Pages

Repo → **Settings → Pages** → Source: **Deploy from a branch** →
Branch: **main**, folder: **/docs** → Save.

Your site goes live at
`https://greggrandsd-hub.github.io/Linked-In-Content-Generator/` immediately.

### 3. Put it on YOUR domain (do this — it's the whole point)

Two months of SEO equity lives at **theaisalesleader.com**, so the articles
should build that domain's authority, not github.io's. Serve the engine at
`insights.theaisalesleader.com`:

1. In your DNS provider (wherever theaisalesleader.com is registered), add a
   CNAME record: host `insights` → value `greggrandsd-hub.github.io`
2. Repo → **Settings → Pages → Custom domain** → enter
   `insights.theaisalesleader.com` → Save, and tick **Enforce HTTPS** once the
   certificate is issued (a few minutes)
3. Repo → **Settings → Secrets and variables → Actions → Variables** → add
   `SITE_BASE_URL` = `https://insights.theaisalesleader.com`

Every canonical URL, sitemap entry, schema block, and the CNAME file then
point at your domain automatically. Your existing site is untouched — the
subdomain lives alongside it, and every article links back to
theaisalesleader.com. (If your main site is WordPress and you'd rather have
articles land directly in its blog via the WordPress API, that's a small
add-on to the engine — say the word.)

### 4. That's it

The workflow in `.github/workflows/seo-engine.yml` runs every morning at
7:00 AM ET, publishes the article, commits it, and the site updates itself.
You can also trigger it manually: **Actions → SEO Engine → Run workflow**,
or click **Publish Next Article Now** in the web UI's SEO Engine tab.

### 5. Tell Google you exist (one time)

- Add the site to [Google Search Console](https://search.google.com/search-console)
  and submit `sitemap.xml`. Do the same in
  [Bing Webmaster Tools](https://www.bing.com/webmasters) (Bing powers ChatGPT
  search and Copilot).

## Running it locally instead

```bash
python seo_run.py                 # publish one article now
python seo_run.py --schedule      # run every 24h, forever
python seo_run.py --rebuild       # re-render the site from stored articles
```

## Honest expectations (read this, Greg)

- **Months 1–3:** Google is indexing. AI engines (ChatGPT, Perplexity) often
  cite fresh long-tail content *faster* than Google ranks it — expect AEO/GEO
  wins first. This is normal, not failure.
- **Months 3–6:** long-tail question keywords start ranking; impressions climb
  in Search Console. 30 articles compound in ways 2 articles can't.
- **Month 6+:** the library (180+ articles by then) becomes a moat.
- **What this engine deliberately does NOT do:** backlink exchanges like the
  ones ads promise ("88 backlinks, zero outreach"). Reciprocal link networks
  violate Google's spam policy and can get a site penalized — a real backlink
  strategy is podcast guesting, Vistage talks, and being quotable, which this
  content makes easier.

## Files

```
seo_engine/
  topics.py      keyword queue (seeded + Gemini auto-refill)
  generator.py   article generation (SEO + AEO + GEO structure)
  publisher.py   static site renderer (docs/) + sitemap/robots/llms.txt/RSS
  engine.py      orchestrator: generate → publish → repurpose → notify
seo_run.py       CLI entry point
content/         article JSON (source of truth) + topic queue state
docs/            the rendered website (what GitHub Pages serves)
.github/workflows/seo-engine.yml   the daily automation
```
