"""
G Squared SEO / AEO / GEO Engine.

Automated organic-visibility pipeline:

- SEO  (Search Engine Optimization)    — long-tail keyword articles, sitemap,
  clean semantic HTML, internal linking.
- AEO  (Answer Engine Optimization)    — answer-first paragraphs, question
  headings, FAQ blocks, FAQPage/Article JSON-LD schema.
- GEO  (Generative Engine Optimization) — statistics, quotable lines, clear
  entity/author attribution, llms.txt so AI engines can cite you.

Run it:
    python seo_run.py                # generate + publish the next article
    python seo_run.py --schedule     # run daily, forever
    (or let the GitHub Actions cron do it — see .github/workflows/seo-engine.yml)
"""
