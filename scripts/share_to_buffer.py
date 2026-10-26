#!/usr/bin/env python3
"""Share newly published Knowledge Centre articles to LinkedIn and Google Business Profile via the Buffer API.

Runs in GitHub Actions (see .github/workflows/social-share.yml), so it needs neither
Kunal's computer nor an open browser. The Buffer API key is read from the
BUFFER_API_KEY repository secret and is never printed.

Usage:
  python scripts/share_to_buffer.py --files content/blog/a.md [...]   # share these articles
  python scripts/share_to_buffer.py --check                           # list channels only (no posting)
  python scripts/share_to_buffer.py --files ... --dry-run             # show post text, do not post
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml

API = "https://api.buffer.com"
SITE = "https://www.kunaldarwani.com"
MAX_LEN = 1200  # Buffer enforces ~1,248 characters for LinkedIn

HASHTAGS = {
    "gst": "#GST #GSTIndia #IndirectTax",
    "income": "#IncomeTax #ITR #DirectTax",
    "tds": "#TDS #IncomeTax",
    "tax-audit": "#TaxAudit #IncomeTax",
    "company": "#CompanyLaw #MCA #ROC",
    "llp": "#LLP #MCA",
    "audit": "#Audit #Assurance",
    "msme": "#MSME #Udyam",
    "startup": "#Startup #StartupIndia",
    "fssai": "#FSSAI",
    "pf": "#EPFO #ESIC #Payroll",
    "payroll": "#Payroll #EPFO",
    "accounting": "#Accounting #Bookkeeping",
    "foreign": "#Outsourcing #Accounting",
    "nidhi": "#NidhiCompany #CompanyLaw",
    "iec": "#IEC #DGFT",
}


def gql(query, variables=None):
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        sys.exit("BUFFER_API_KEY secret is not set.")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "kunaldarwani-website-actions",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            if data.get("errors"):
                raise RuntimeError(json.dumps(data["errors"])[:600])
            return data["data"]
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                raise
            print(f"  retrying after error: {e}")
            time.sleep(10 * (attempt + 1))


def channels():
    orgs = gql("query { account { organizations { id name } } }")["account"]["organizations"]
    out = []
    for o in orgs:
        q = "query($id: OrganizationId!) { channels(input: {organizationId: $id}) { id name service } }"
        for c in gql(q, {"id": o["id"]})["channels"]:
            out.append(c)
    return out


def input_fields(type_name):
    q = 'query($n: String!) { __type(name: $n) { name kind inputFields { name type { name kind ofType { name kind } } } enumValues { name } } }'
    return gql(q, {"n": type_name})["__type"]


def front_matter(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def build_text(path, meta):
    slug = Path(path).stem
    url = f"{SITE}/blog/{slug}.html"
    social = (meta.get("social") or "").strip()
    if social:
        text = social if url in social else f"{social}\n\nFull article:\n{url}"
    else:
        lines = [meta.get("title", "").strip(), "", (meta.get("summary") or "").strip()]
        faqs = [f.get("q", "").strip() for f in (meta.get("faq") or []) if f.get("q")][:3]
        if faqs:
            lines += ["", "Questions answered in the article:"] + [f"• {q}" for q in faqs]
        lines += ["", "Full article:", url]
        svc = str(meta.get("service", ""))
        tags = next((v for k, v in HASHTAGS.items() if k in svc), "#Compliance #India")
        lines += ["", tags]
        text = "\n".join(lines)
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1].rsplit("\n", 1)[0]
    return text, url


def share(path, chans, dry_run):
    meta = front_matter(path)
    if meta.get("social_share") is False:
        print(f"Skipping {path} (social_share: false)")
        return True
    text, url = build_text(path, meta)
    print(f"\n=== {path}\n{text}\n")
    if dry_run:
        return True
    ok = True
    mutation = """
mutation($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id } }
    ... on MutationError { message }
  }
}"""
    for c in chans:
        inp = {"text": text, "channelId": c["id"], "schedulingType": "automatic", "mode": "shareNow"}
        if c["service"] in ("googlebusiness", "google_business", "google"):
            inp["metadata"] = {"google": {"type": "whats_new", "button": "learn_more", "link": url}}
        try:
            res = gql(mutation, {"input": inp})["createPost"]
        except Exception as e:  # noqa: BLE001
            # Google metadata shape may differ – retry once with text only (link stays in the text).
            if "metadata" in inp:
                print(f"  {c['service']}: metadata rejected ({e}); retrying without button")
                inp.pop("metadata")
                res = gql(mutation, {"input": inp})["createPost"]
            else:
                raise
        if res.get("message"):
            ok = False
            print(f"  FAILED {c['service']} ({c['name']}): {res['message']}")
        else:
            print(f"  posted to {c['service']} ({c['name']}): post id {res['post']['id']}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.check:
        for c in channels():
            print(f"channel: {c['service']} | {c['name']} | {c['id']}")
        for t in ("CreatePostInput", "PostInputMetaData", "ShareMode", "SchedulingType"):
            try:
                print(json.dumps(input_fields(t)))
            except Exception as e:  # noqa: BLE001
                print(f"{t}: {e}")
        for t in ("PostInputMetaData",):
            info = input_fields(t) or {}
            for f in info.get("inputFields") or []:
                if "google" in f["name"].lower() or "linkedin" in f["name"].lower():
                    tn = f["type"]["name"] or (f["type"].get("ofType") or {}).get("name")
                    print(json.dumps(input_fields(tn)))
        return

    files = [f for f in a.files if f.startswith("content/blog/") and f.endswith(".md") and Path(f).exists()]
    if not files:
        print("No new articles to share.")
        return
    wanted = ("linkedin", "googlebusiness", "google_business", "google")
    chans = [c for c in channels() if c["service"] in wanted] if not a.dry_run else []
    if not a.dry_run and not chans:
        sys.exit("No LinkedIn / Google Business channels found in Buffer.")
    results = [share(f, chans, a.dry_run) for f in files]
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
