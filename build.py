#!/usr/bin/env python3
"""Static site builder for Kunal Darwani & Company, Chartered Accountants.

Usage:  python build.py            -> builds into ./dist
        python build.py --drafts   -> also renders posts marked `draft: true`

Content lives in:
  data/site.json          firm details and partners
  data/categories.json    service categories (display order)
  data/compliance.json    compliance calendar
  content/services/*.md   one file per service (front matter + body)
  content/blog/*.md       blog posts (front matter + body). `service:` links a post to a service page.
  content/pages/*.md      static pages (disclaimer, privacy, about)
"""
import json, re, shutil, sys, datetime as dt
from pathlib import Path
from xml.sax.saxutils import escape

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SHOW_DRAFTS = "--drafts" in sys.argv

MD = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])


def parse_md(path: Path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    MD.reset()
    html = MD.convert(body.strip())
    words = len(re.findall(r"\w+", body))
    meta.setdefault("slug", path.stem)
    meta["html"] = html
    meta["reading_minutes"] = max(1, round(words / 200))
    return meta


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def fmt_date(d):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    return d.strftime("%-d %B %Y")


def main():
    site = load_json("site.json")
    categories = load_json("categories.json")
    compliance = load_json("compliance.json")
    upd_path = ROOT / "data" / "updates.json"
    updates = json.loads(upd_path.read_text(encoding="utf-8")) if upd_path.exists() else {"items": []}
    sum_path = ROOT / "data" / "summaries.json"
    summaries = json.loads(sum_path.read_text(encoding="utf-8")) if sum_path.exists() else {}
    for u in updates["items"]:
        u["date_human"] = fmt_date(u["date"])
        u["summary"] = summaries.get(u["link"], {}).get("summary", "")
    upd_news = [u for u in updates["items"] if u["kind"] == "news"]
    upd_circ = [u for u in updates["items"] if u["kind"] == "circular"]

    services = [parse_md(p) for p in sorted((ROOT / "content/services").glob("*.md"))]
    services.sort(key=lambda s: (s.get("order", 999), s["title"]))
    svc_by_slug = {s["slug"]: s for s in services}

    posts = []
    for p in (ROOT / "content/blog").glob("*.md"):
        post = parse_md(p)
        if post.get("draft") and not SHOW_DRAFTS:
            continue
        d = post.get("date")
        post["date"] = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d))
        post["date_human"] = fmt_date(post["date"])
        posts.append(post)
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)

    for s in services:
        s["posts"] = [p for p in posts if p.get("service") == s["slug"]]
    for p in posts:
        p["service_obj"] = svc_by_slug.get(p.get("service"))

    cats = []
    for c in categories:
        c = dict(c)
        c["services"] = [s for s in services if s.get("category") == c["slug"]]
        cats.append(c)

    pages = {p.stem: parse_md(p) for p in (ROOT / "content/pages").glob("*.md")}

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.globals.update(site=site, categories=cats, year=dt.date.today().year,
                       build_date=dt.date.today().isoformat())

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "static", DIST / "static")

    urls = []

    def render(tpl, out, depth=0, **ctx):
        rel = "../" * depth
        html = env.get_template(tpl).render(rel=rel, **ctx)
        target = DIST / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        urls.append(out)

    render("updates.html", "updates.html", updates=updates, upd_news=upd_news, upd_circ=upd_circ,
           page_title="Latest News & Notifications", nav="updates")
    render("home.html", "index.html", services=services, posts=posts[:3],
           upd_news=upd_news[:6], upd_circ=upd_circ[:6], updates=updates,
           compliance=compliance, page_title=None, nav="home")
    render("services.html", "services/index.html", 1, page_title="Services", nav="services")
    for s in services:
        render("service.html", f"services/{s['slug']}.html", 1, s=s,
               page_title=s["title"], description=s.get("summary"), nav="services")
    render("blog.html", "blog/index.html", 1, posts=posts, page_title="Knowledge Centre", nav="blog")
    for p in posts:
        render("post.html", f"blog/{p['slug']}.html", 1, p=p, page_title=p["title"],
               description=p.get("summary"), nav="blog")
    render("partners.html", "partners.html", page_title="Partners", nav="partners")
    render("calendar.html", "compliance-calendar.html", compliance=compliance,
           page_title="Compliance Calendar", nav="calendar")
    render("contact.html", "contact.html", page_title="Contact", nav="contact")
    for slug, pg in pages.items():
        render("page.html", f"{slug}.html", pg=pg, page_title=pg["title"], nav=slug)

    # sitemap + RSS
    base = site["base_url"].rstrip("/")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{base}/{u.replace('index.html', '')}</loc></url>" for u in urls]
    sm.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

    items = "".join(
        f"<item><title>{escape(p['title'])}</title><link>{base}/blog/{p['slug']}.html</link>"
        f"<guid>{base}/blog/{p['slug']}.html</guid>"
        f"<pubDate>{p['date'].strftime('%a, %d %b %Y 00:00:00 +0530')}</pubDate>"
        f"<description>{escape(p.get('summary', ''))}</description></item>"
        for p in posts[:30])
    rss = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
           f"<title>{escape(site['firm_name'])} – Knowledge Centre</title><link>{base}/blog/</link>"
           f"<description>Tax, GST, company law and accounting updates</description>{items}</channel></rss>")
    (DIST / "blog" / "feed.xml").write_text(rss, encoding="utf-8")
    (DIST / "CNAME").write_text(site["domain"] + "\n")

    print(f"Built {len(urls)} pages: {len(services)} services, {len(posts)} posts -> {DIST}")


if __name__ == "__main__":
    main()
