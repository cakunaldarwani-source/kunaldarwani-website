#!/usr/bin/env python3
"""Publish the next queued Knowledge Centre article.

Queued articles live in content/queue/ as NN-<slug>.md (NN = order).
This script takes the first file in name order, sets its `date` to today
(IST), writes it to content/blog/<slug>.md and removes it from the queue.

Usage:  python scripts/publish_queue.py          -> publish next article
        python scripts/publish_queue.py --list   -> show the queue only
Writes `published`, `file`, `slug` and `title` to $GITHUB_OUTPUT when set.
"""
import datetime as dt
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content" / "queue"
BLOG = ROOT / "content" / "blog"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"{k}={v}")
        if path:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"{k}={v}\n")


def main():
    queued = sorted(QUEUE.glob("*.md")) if QUEUE.exists() else []
    if "--list" in sys.argv:
        for q in queued:
            print(q.name)
        print(f"{len(queued)} article(s) in queue")
        return
    if not queued:
        print("Queue is empty - nothing to publish.")
        output(published="false")
        return

    src = queued[0]
    slug = re.sub(r"^\d+-", "", src.stem)
    dest = BLOG / f"{slug}.md"
    if dest.exists():
        sys.exit(f"{dest} already exists - rename the queued file.")

    text = src.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"{src.name}: front matter not found")
    meta = yaml.safe_load(m.group(1))
    today = dt.datetime.now(IST).date().isoformat()
    new_fm = re.sub(r"(?m)^date:.*$", f"date: '{today}'", m.group(1), count=1)
    if "date:" not in new_fm:
        new_fm = f"date: '{today}'\n" + new_fm
    dest.write_text(f"---\n{new_fm}\n---\n" + text[m.end():], encoding="utf-8")
    src.unlink()

    print(f"Published {src.name} -> content/blog/{slug}.md dated {today}")
    print(f"{len(queued) - 1} article(s) left in queue")
    output(published="true", file=f"content/blog/{slug}.md", slug=slug,
           title=str(meta.get("title", slug)).replace("\n", " "))


if __name__ == "__main__":
    main()
