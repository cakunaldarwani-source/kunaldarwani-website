#!/usr/bin/env python3
"""Fetch the latest notifications, circulars and news from official sources.

Runs daily at 11:00 AM IST via .github/workflows/daily-updates.yml and merges new
items into data/updates.json, which build.py renders on the home page and on
/updates.html. Every item links to the original document on the official site.

Sources (all official / regulator websites):
  Income Tax Department – notifications, circulars, press releases (RSS)
  Reserve Bank of India – notifications, press releases (RSS)
  SEBI – circulars and press releases (RSS, filtered)
  GST Network portal – news & advisories (JSON used by gst.gov.in)
  ICAI – announcements (HTML)
  MCA and CBIC – their websites publish no feed and block automated
  requests, so new items are located with Claude's web search restricted to
  the official domains (mca.gov.in, cbic.gov.in, taxinformation.cbic.gov.in,
  egazette.gov.in, pib.gov.in). Only links on those domains are accepted.
  Needs the ANTHROPIC_API_KEY secret; skipped without it.

A source that fails is skipped; the others still update.
"""
import datetime as dt, email.utils, html, json, re, sys
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_util

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "updates.json"
KEEP_DAYS = 90
MAX_ITEMS = 400
UA = {"User-Agent": "Mozilla/5.0 (compatible; KDCo-UpdatesBot/1.0; +https://www.kunaldarwani.com)"}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# kind: "circular" -> Latest Notifications & Circulars ; "news" -> Latest News
SOURCES = [
    {"name": "CBDT", "kind": "circular", "type": "rss", "label": "Income Tax Notification",
     "url": "https://www.incometaxindia.gov.in/notification-rss-feed/-/asset_publisher/bxhj/rss"},
    {"name": "CBDT", "kind": "circular", "type": "rss", "label": "Income Tax Circular",
     "url": "https://www.incometaxindia.gov.in/circular-rss-feed/-/asset_publisher/bxhj/rss"},
    {"name": "CBDT", "kind": "news", "type": "rss", "label": "Income Tax Press Release",
     "url": "https://www.incometaxindia.gov.in/press-release-rss-feed/-/asset_publisher/bxhj/rss"},
    {"name": "RBI", "kind": "circular", "type": "rss", "label": "RBI Notification",
     "url": "https://www.rbi.org.in/notifications_rss.xml"},
    {"name": "RBI", "kind": "news", "type": "rss", "label": "RBI Press Release",
     "url": "https://www.rbi.org.in/pressreleases_rss.xml",
     "exclude": r"money market operations|auction|weekly statistical|treasury bill|result of|cut-off|"
                r"lending facility|reserve money|state government securities|government stock|"
                r"variable rate repo|variable rate reverse repo|\bsdl\b|overnight|imposes monetary penalty|"
                r"cancels the certificate|directions under section 35a|appoints|payment of interest"},
    {"name": "SEBI", "kind": "circular", "type": "rss", "label": "SEBI Circular",
     "url": "https://www.sebi.gov.in/sebirss.xml", "include_link": r"/legal/(circulars|master-circulars)/"},
    {"name": "SEBI", "kind": "news", "type": "rss", "label": "SEBI Press Release",
     "url": "https://www.sebi.gov.in/sebirss.xml", "include_link": r"/media-and-notifications/press-releases/"},
    {"name": "GST", "kind": "news", "type": "gstn", "label": "GST Portal Advisory",
     "url": "https://www.gst.gov.in/fomessage/newsupdates"},
    {"name": "ICAI", "kind": "news", "type": "icai", "label": "ICAI Announcement",
     "url": "https://www.icai.org/category/announcements"},
    {"name": "MCA", "type": "ai_search", "label": "MCA",
     "authority": "the Ministry of Corporate Affairs (MCA), Government of India",
     "what": "notifications (including amendments to Companies Act rules and LLP rules), general circulars, "
             "orders and press releases",
     "domains": ["mca.gov.in", "egazette.gov.in", "pib.gov.in"]},
    {"name": "CBIC", "type": "ai_search", "label": "CBIC",
     "authority": "the Central Board of Indirect Taxes and Customs (CBIC) and the GST Council",
     "what": "GST notifications (Central Tax, Central Tax (Rate), Integrated Tax), GST circulars, "
             "customs and excise notifications and circulars, instructions and press releases",
     "domains": ["cbic.gov.in", "taxinformation.cbic.gov.in", "cbic-gst.gov.in", "gstcouncil.gov.in",
                 "egazette.gov.in", "pib.gov.in"]},
]


def clean_title(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    t = re.sub(r"\[\s*F\.?\s*No\.?[^\]]*\]", "", t, flags=re.I)        # file numbers
    t = re.sub(r"/\s*S\.?O\.?\s*\d+\s*\(E\)", "", t, flags=re.I)       # gazette S.O. numbers
    t = re.sub(r"/\s*G\.?S\.?R\.?\s*\d+\s*\(E\)", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -–/:")
    return (t[:177] + "…") if len(t) > 180 else t


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
        return d.astimezone(IST).date() if d.tzinfo else d.date()
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
                "%d %b, %Y %z", "%d %b, %Y", "%d %B %Y", "%a, %d %b %Y", "%A, %B %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s)
    if m:
        try:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
    return None


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=40, **kw)
    r.raise_for_status()
    return r


def parse_rss(xml_text):
    """RSS 2.0 or Atom -> list of (title, link, date)."""
    xml_text = re.sub(r"^\s*<\?xml[^>]*\?>", "", xml_text.lstrip("﻿"))
    root = ET.fromstring(xml_text)
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        f = {c.tag.split("}")[-1]: c for c in it}
        title = (f["title"].text or "") if "title" in f else ""
        link = ""
        if "link" in f:
            link = (f["link"].text or f["link"].get("href") or "").strip()
        if not link and "guid" in f:
            link = (f["guid"].text or "").strip()
        date = None
        for k in ("pubDate", "date", "published", "updated"):
            if k in f and f[k].text:
                date = parse_date(f[k].text)
                if date:
                    break
        out.append((title, link, date))
    return out


def fetch_rss(src):
    items = []
    for title, link, date in parse_rss(get(src["url"]).text):
        if src.get("include_link") and not re.search(src["include_link"], link):
            continue
        if src.get("exclude") and re.search(src["exclude"], title, re.I):
            continue
        items.append((title, link, date))
    return items


def fetch_gstn(src):
    data = get(src["url"]).json().get("data", [])
    items = []
    for d in data:
        link = d.get("linkURl") if str(d.get("IsExternal", "")).lower() in ("true", "y", "1") and d.get("linkURl") \
            else f"https://www.gst.gov.in/newsandupdates/read/{d.get('id')}"
        items.append((d.get("title", ""), link, parse_date(d.get("date", ""))))
    return items


def fetch_icai(src):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(get(src["url"]).text, "html.parser")
    items, seen = [], set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if len(text) < 20:
            continue
        block = a.find_parent(["li", "tr", "div"]) or a
        m = re.search(r"\(?(\d{2}-\d{2}-\d{4})\)?", block.get_text(" ", strip=True))
        if not m:
            continue
        href = requests.compat.urljoin(src["url"], a["href"])
        if href in seen:
            continue
        seen.add(href)
        items.append((re.sub(r"\s*-?\s*\(?\d{2}-\d{2}-\d{4}\)?\s*$", "", text), href, parse_date(m[1])))
        if len(items) >= 25:
            break
    return items


def fetch_ai_search(src):
    """Locate new MCA/CBIC documents via web search limited to official domains."""
    if not claude_util.has_key():
        raise RuntimeError("No AI key (GEMINI_API_KEY or ANTHROPIC_API_KEY) – skipped")
    today = dt.datetime.now(IST).date()
    prompt = f"""Today is {today.isoformat()} (India).
List {src['what']} issued by {src['authority']} on or after {(today - dt.timedelta(days=7)).isoformat()}.
Search only the official websites. Include an item only if you found its page or PDF on an official website.
Copy each title as the authority wrote it (number, date and subject), with no commentary.
Return ONLY a JSON array (empty if nothing found). Each element:
{{"title": "...", "date": "YYYY-MM-DD", "link": "https://...", "type": "notification" | "circular" | "order" | "press release"}}"""
    data = claude_util.ask_json(prompt, allowed_domains=src["domains"], max_searches=6)
    items = []
    for d in data if isinstance(data, list) else []:
        link = str(d.get("link", ""))
        host = re.sub(r"^https?://", "", link).split("/")[0].lower()
        if not any(host == dom or host.endswith("." + dom) for dom in src["domains"]):
            continue  # never accept non-official links
        typ = str(d.get("type", "notification")).lower()
        kind = "news" if "press" in typ else "circular"
        label = f"{src['name']} {typ.title()}"
        items.append((d.get("title", ""), link, parse_date(str(d.get("date", ""))), kind, label))
    return items


FETCHERS = {"rss": fetch_rss, "gstn": fetch_gstn, "icai": fetch_icai, "ai_search": fetch_ai_search}


def main():
    today = dt.datetime.now(IST).date()
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    by_link = {i["link"]: i for i in existing.get("items", [])}
    report = []
    for src in SOURCES:
        try:
            got = FETCHERS[src["type"]](src)
            new = 0
            for row in got:
                title, link, date = row[:3]
                kind = row[3] if len(row) > 3 else src["kind"]
                label = row[4] if len(row) > 4 else src["label"]
                title = clean_title(title)
                if not title or not link.startswith("http"):
                    continue
                if link not in by_link:
                    new += 1
                by_link[link] = {
                    "title": title, "link": link,
                    "date": (date or today).isoformat(),
                    "source": src["name"], "label": label, "kind": kind,
                    "first_seen": by_link.get(link, {}).get("first_seen", today.isoformat()),
                }
            report.append(f"OK    {src['label']:<26} {len(got):>3} items, {new} new")
        except Exception as e:  # keep going with other sources
            report.append(f"FAIL  {src['label']:<26} {type(e).__name__}: {str(e)[:90]}")

    cutoff = (today - dt.timedelta(days=KEEP_DAYS)).isoformat()
    items = [i for i in by_link.values() if i["date"] >= cutoff and i["date"] <= (today + dt.timedelta(days=1)).isoformat()]
    items.sort(key=lambda i: (i["date"], i["first_seen"]), reverse=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
                               "items": items[:MAX_ITEMS]}, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(report))
    print(f"Saved {min(len(items), MAX_ITEMS)} items -> {OUT.relative_to(ROOT)}")
    # fail the run only if every source failed
    Path(ROOT / "automation").mkdir(exist_ok=True)
    (ROOT / "automation" / "last_fetch_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 1 if all(r.startswith("FAIL") for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
