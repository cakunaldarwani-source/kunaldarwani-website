# kunaldarwani.com – Kunal Darwani & Company, Chartered Accountants

A static website with 33 service pages, a Knowledge Centre (blog), a compliance calendar and an ICAI wording check. AI-drafted articles arrive twice a week as pull requests for partner review.

## Folder map

| Path | What it holds |
|---|---|
| `data/site.json` | Firm name, address, phone, email, partner profiles. |
| `data/compliance.json` | Due dates shown on the home page and calendar page |
| `content/services/*.md` | One file per service. The front matter holds the scope, documents and laws; the body holds the description |
| `content/blog/*.md` | Articles. `service:` links an article to a service page, and the newest linked article is shown in full there |
| `content/pages/*.md` | The Firm, Disclaimer, Privacy policy |
| `templates/`, `static/` | HTML templates, CSS, JS |
| `scripts/icai_check.py` | Flags superlatives, fees, testimonials, guarantees and similar wording |
| `scripts/draft_post.py` | Drafts a new article with Claude (used by the AI workflow) |
| `automation/BLOG_WRITER_GUIDE.md` | ICAI and accuracy rules given to the AI writer |

## Build locally

```bash
pip install -r requirements.txt
python scripts/icai_check.py   # must show 0 high
python build.py                # output in ./dist
python -m http.server -d dist  # preview at http://localhost:8000
```

## One-time setup (GitHub Pages + custom domain)

1. Create a **private** GitHub repository (e.g. `kunaldarwani-website`) and push this folder to the `main` branch.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Settings → Pages → Custom domain:** `www.kunaldarwani.com`, then tick *Enforce HTTPS* once the certificate is issued.
4. At your domain registrar, add:
   - `CNAME` record: `www` → `<your-github-username>.github.io`
   - `A` records for the bare domain `kunaldarwani.com`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`

## AI blog routine (twice weekly, publishes automatically)

1. **Free option (default):** create a Google Gemini key at aistudio.google.com → *Get API key* (no billing needed). Save it as the repository secret `GEMINI_API_KEY` (**Settings → Secrets and variables → Actions → New repository secret**).
2. **Paid option:** an Anthropic key from console.anthropic.com, saved as `ANTHROPIC_API_KEY`. If both keys are present, Gemini is used unless the variable `AI_PROVIDER` is `anthropic`.
3. Optional variables: `GEMINI_MODEL` or `CLAUDE_MODEL` to pick a specific model.
4. **Settings → Actions → General → Workflow permissions:** select *Read and write* and tick *Allow GitHub Actions to create and approve pull requests*.

Every **Tuesday and Friday at 09:15 IST**, the workflow researches the latest updates (or picks the service with the oldest article), writes an article and runs these checks:

- the ICAI wording check (no superlatives, fees, testimonials, solicitation)
- official sources cited
- at least 500 words
- the site builds

**If every check passes, the article is published immediately with no approval needed.** If any check fails, the article is held back as a pull request titled *"Blog held for review"*, and GitHub emails you.

To go back to reviewing every article, add a repository variable `REQUIRE_BLOG_REVIEW` = `true`.

## ICAI compliance – what has been built in

- No firm logo or monogram: the firm name is in plain text only
- No fees, offers, testimonials, client names, awards, rankings or "why choose us"
- No superlatives or specialty labels ("expert", "best", "leading")
- Partner photos: passport-style only. Add them under `static/img/` and set `photo` in `site.json`. Initials are shown until then
- A disclaimer gate on first visit, plus a full Disclaimer page
- External links only to ICAI and government portals, with no links to commercial organisations
- Audit and attestation pages are factual and educational
- Articles and summaries pass automated ICAI wording checks and cite official sources, and the Disclaimer discloses the use of AI tools
- Intimate the website address to ICAI as its guidelines require (see the notes in the delivery message)

## Daily news & notifications (11:00 AM IST)

`.github/workflows/daily-updates.yml` runs every day at **11:00 AM IST**. It runs `scripts/fetch_updates.py`, which pulls new items from official sources only:

| Source | Section |
|---|---|
| Income Tax Department – notifications, circulars (RSS) | Notifications & Circulars |
| RBI – notifications (RSS) | Notifications & Circulars |
| SEBI – circulars and master circulars (RSS) | Notifications & Circulars |
| Income Tax Department, RBI and SEBI press releases | Latest News |
| GST portal – news and advisories | Latest News |
| ICAI – announcements | Latest News |
| MCA – notifications, general circulars, press releases | Both sections |
| CBIC – GST/customs notifications, circulars, press releases | Both sections |

**MCA and CBIC** publish no feed, and their websites refuse automated requests from servers outside India. Their new documents are therefore found with AI web search, **limited to official domains** (mca.gov.in, cbic.gov.in, taxinformation.cbic.gov.in, egazette.gov.in, pib.gov.in). Any link outside those domains is discarded. This needs the AI key secret (`GEMINI_API_KEY` or `ANTHROPIC_API_KEY`), the same one used for the blog.

### Summaries by CA. Kunal Darwani (reviewed)

After each daily fetch, `scripts/summarize_updates.py` writes a summary of up to 35 words for each new notification: who is affected, what changes, and any due date. Summaries that pass the ICAI wording check are **published automatically**, labelled *Summary by CA. Kunal Darwani*. To review them before publishing instead, set the repository variable `REQUIRE_SUMMARY_REVIEW` to `true`.

New items are saved to `data/updates.json` (the last 90 days are kept). They are shown on the home page and on `updates.html`, and the site is redeployed automatically. Every item links to the original document. If one source is down, the others still update. To run it on demand: **Actions → Daily news & notifications → Run workflow**. No setup is needed beyond the GitHub Pages steps above.

To add or remove a source, edit the `SOURCES` list at the top of `scripts/fetch_updates.py`.

## Updating the compliance calendar

Edit `data/compliance.json`. Past dates hide themselves automatically on the home page and are dimmed on the calendar page.
