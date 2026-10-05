#!/usr/bin/env python3
"""Write a new Knowledge Centre article with AI and save it to content/blog/.

Run by .github/workflows/ai-blog.yml twice a week; published automatically if it
passes the ICAI wording and quality checks.

Env:
  GEMINI_API_KEY      free Google Gemini key (preferred), or
  ANTHROPIC_API_KEY   paid Anthropic key
  TOPIC_HINT          optional, e.g. "GST Council meeting outcome" to steer the topic
"""
import datetime as dt, json, os, re, sys, time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_util

ROOT = Path(__file__).resolve().parent.parent


def front_matter(path):
    t = path.read_text(encoding="utf-8")
    return yaml.safe_load(t.split("---", 2)[1]) if t.startswith("---") else {}


def pick_service(services, posts):
    """Service whose most recent article is oldest gets the next turn."""
    latest = {}
    for p in posts:
        s, d = p.get("service"), str(p.get("date"))
        if s and d > latest.get(s, ""):
            latest[s] = d
    return min(services, key=lambda s: latest.get(s["slug"], "0000"))


LABELS = ("TITLE", "SUMMARY", "SERVICE", "SLUG", "SOURCES", "REVIEW_NOTES", "BODY")


def parse_reply(text):
    """Parse the labelled reply. Falls back to JSON if the model sent JSON anyway."""
    text = re.sub(r"^```[a-z]*\s*|```\s*$", "", text.strip())
    if text.lstrip().startswith("{"):
        return claude_util._parse_json(text)
    parts, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^\**(%s)\**\s*:\s*(.*)$" % "|".join(LABELS), line.strip()) if current != "BODY" else None
        if m:
            current = m.group(1)
            parts[current] = [m.group(2)] if m.group(2) else []
        elif current:
            parts[current].append(line)
    get = lambda k: "\n".join(parts.get(k, [])).strip()
    data = {
        "title": get("TITLE").strip("*# "), "summary": get("SUMMARY"), "service": get("SERVICE").strip("` "),
        "slug": get("SLUG").strip("` "), "body_markdown": get("BODY"),
        "sources": [u for u in re.findall(r"https?://[^\s<>)\]]+", get("SOURCES"))],
        "review_notes": [l.lstrip("-* ").strip() for l in get("REVIEW_NOTES").splitlines() if l.strip()],
    }
    if not data["title"] or len(data["body_markdown"].split()) < 200:
        raise ValueError("Reply did not contain a complete article")
    if not data["slug"]:
        data["slug"] = "-".join(re.findall(r"[a-z0-9]+", data["title"].lower())[:8])
    return data


def main():
    today = dt.date.today()
    services = [dict(front_matter(p), slug=p.stem) for p in sorted((ROOT / "content/services").glob("*.md"))]
    posts = [front_matter(p) for p in (ROOT / "content/blog").glob("*.md")]
    svc = pick_service(services, posts)
    guide = (ROOT / "automation/BLOG_WRITER_GUIDE.md").read_text(encoding="utf-8")
    recent_titles = "\n".join(f"- {p.get('title')}" for p in sorted(posts, key=lambda p: str(p.get('date')), reverse=True)[:40])
    hint = os.environ.get("TOPIC_HINT", "").strip()
    upd_file = ROOT / "data" / "updates.json"
    recent_updates = ""
    if upd_file.exists():
        items = json.loads(upd_file.read_text(encoding="utf-8")).get("items", [])[:25]
        recent_updates = "\n".join(f"- [{i['source']}] {i['date']}: {i['title']} ({i['link']})" for i in items)

    task = f"""Today is {today.isoformat()}.

Write one new article for the firm's Knowledge Centre.

Step 1 – Research: search the web for regulatory developments in India from the last 21 days
(CBDT, CBIC/GST Council, MCA, RBI, ICAI, EPFO, DGFT). Prefer official sources.
{"Topic steer from the partner: " + hint if hint else ""}

Latest official items already collected by the website (good candidates for a topic):
{recent_updates or "(none)"}

Step 2 – Choose the topic:
- If there is a significant recent development, write about it and set `service` to the closest slug from the list.
- Otherwise write a practical, evergreen article for the service "{svc['title']}" (slug: {svc['slug']}), on an angle not
  already covered by the existing titles below.

Valid service slugs: {", ".join(s['slug'] for s in services)}

Existing titles (do not duplicate):
{recent_titles}

Follow this guide strictly:
{guide}

Reply in EXACTLY this layout (plain text, no JSON, no code fences):
TITLE: <title>
SUMMARY: <max 30 words>
SERVICE: <one slug from the list>
SLUG: <lowercase-hyphenated, max 8 words>
SOURCES:
<one official URL per line>
REVIEW_NOTES:
<one point per line that the reviewing partner should verify>
BODY:
<the full article in Markdown, no H1, at least 700 words>"""

    data = None
    for attempt in range(2):
        try:
            data = parse_reply(claude_util.ask_text(task, max_searches=8, max_tokens=12000))
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}", flush=True)
            if attempt == 0:
                time.sleep(120)
    if data is None:
        raise SystemExit("AI service unavailable today - no article written. It will try again at the next scheduled run.")

    slug = re.sub(r"[^a-z0-9-]+", "-", data["slug"].lower()).strip("-")
    fm = {
        "title": data["title"],
        "date": today.isoformat(),
        "service": data["service"] if data["service"] in {s["slug"] for s in services} else svc["slug"],
        "author": data.get("author", "CA. Kunal Darwani"),
        "summary": data["summary"],
        "ai_drafted": True,
    }
    body = data["body_markdown"].strip()
    if data.get("sources"):
        body += "\n\n**Sources:** " + " · ".join(f"<{u}>" for u in data["sources"])
    out = ROOT / "content/blog" / f"{slug}.md"
    out.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body + "\n", encoding="utf-8")

    notes = ROOT / "automation" / "last_review_notes.md"
    notes.write_text(f"# Review notes for {out.name}\n\n" + "\n".join(f"- {n}" for n in data.get("review_notes", [])) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"post={out.relative_to(ROOT)}\ntitle={data['title']}\n")


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Write a new Knowledge Centre article with AI and save it to content/blog/.

Run by .github/workflows/ai-blog.yml twice a week; published automatically if it
passes the ICAI wording and quality checks.

Env:
  GEMINI_API_KEY      free Google Gemini key (preferred), or
  ANTHROPIC_API_KEY   paid Anthropic key
  TOPIC_HINT          optional, e.g. "GST Council meeting outcome" to steer the topic
"""
import datetime as dt, json, os, re, sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_util

ROOT = Path(__file__).resolve().parent.parent


def front_matter(path):
    t = path.read_text(encoding="utf-8")
    return yaml.safe_load(t.split("---", 2)[1]) if t.startswith("---") else {}


def pick_service(services, posts):
    """Service whose most recent article is oldest gets the next turn."""
    latest = {}
    for p in posts:
        s, d = p.get("service"), str(p.get("date"))
        if s and d > latest.get(s, ""):
            latest[s] = d
    return min(services, key=lambda s: latest.get(s["slug"], "0000"))


def main():
    today = dt.date.today()
    services = [dict(front_matter(p), slug=p.stem) for p in sorted((ROOT / "content/services").glob("*.md"))]
    posts = [front_matter(p) for p in (ROOT / "content/blog").glob("*.md")]
    svc = pick_service(services, posts)
    guide = (ROOT / "automation/BLOG_WRITER_GUIDE.md").read_text(encoding="utf-8")
    recent_titles = "\n".join(f"- {p.get('title')}" for p in sorted(posts, key=lambda p: str(p.get('date')), reverse=True)[:40])
    hint = os.environ.get("TOPIC_HINT", "").strip()
    upd_file = ROOT / "data" / "updates.json"
    recent_updates = ""
    if upd_file.exists():
        items = json.loads(upd_file.read_text(encoding="utf-8")).get("items", [])[:25]
        recent_updates = "\n".join(f"- [{i['source']}] {i['date']}: {i['title']} ({i['link']})" for i in items)

    task = f"""Today is {today.isoformat()}.

Write one new article for the firm's Knowledge Centre.

Step 1 – Research: search the web for regulatory developments in India from the last 21 days
(CBDT, CBIC/GST Council, MCA, RBI, ICAI, EPFO, DGFT). Prefer official sources.
{"Topic steer from the partner: " + hint if hint else ""}

Latest official items already collected by the website (good candidates for a topic):
{recent_updates or "(none)"}

Step 2 – Choose the topic:
- If there is a significant recent development, write about it and set `service` to the closest slug from the list.
- Otherwise write a practical, evergreen article for the service "{svc['title']}" (slug: {svc['slug']}), on an angle not
  already covered by the existing titles below.

Valid service slugs: {", ".join(s['slug'] for s in services)}

Existing titles (do not duplicate):
{recent_titles}

Follow this guide strictly:
{guide}

Return ONLY a JSON object, no code fences, with keys:
  "title", "summary" (max 30 words), "service" (slug), "author",
  "slug" (lowercase-hyphenated, max 8 words), "body_markdown" (article body, no H1),
  "sources" (list of URLs used), "review_notes" (points the reviewing partner should verify)."""

    data = claude_util.ask_json(task, max_searches=8, max_tokens=12000)

    slug = re.sub(r"[^a-z0-9-]+", "-", data["slug"].lower()).strip("-")
    fm = {
        "title": data["title"],
        "date": today.isoformat(),
        "service": data["service"] if data["service"] in {s["slug"] for s in services} else svc["slug"],
        "author": data.get("author", "CA. Kunal Darwani"),
        "summary": data["summary"],
        "ai_drafted": True,
    }
    body = data["body_markdown"].strip()
    if data.get("sources"):
        body += "\n\n**Sources:** " + " · ".join(f"<{u}>" for u in data["sources"])
    out = ROOT / "content/blog" / f"{slug}.md"
    out.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body + "\n", encoding="utf-8")

    notes = ROOT / "automation" / "last_review_notes.md"
    notes.write_text(f"# Review notes for {out.name}\n\n" + "\n".join(f"- {n}" for n in data.get("review_notes", [])) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"post={out.relative_to(ROOT)}\ntitle={data['title']}\n")


if __name__ == "__main__":
    sys.exit(main())
