#!/usr/bin/env python3
"""Draft short plain-English summaries for new notifications and circulars.

Summaries are written to data/summaries.json and published automatically
under "Summary by CA. Kunal Darwani" if they pass the ICAI wording check.
Set the repository variable REQUIRE_SUMMARY_REVIEW=true to send them for review instead.
"""
import datetime as dt, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_util

ROOT = Path(__file__).resolve().parent.parent
UPD = ROOT / "data" / "updates.json"
SUM = ROOT / "data" / "summaries.json"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
MAX_PER_RUN = 15
OFFICIAL = ["incometaxindia.gov.in", "rbi.org.in", "sebi.gov.in", "gst.gov.in", "icai.org", "mca.gov.in",
            "cbic.gov.in", "taxinformation.cbic.gov.in", "egazette.gov.in", "pib.gov.in", "gstcouncil.gov.in"]

GUIDE = """Write for Indian business owners and finance teams. For each item give ONE summary of at most 35 words:
who is affected, what changes, and any date or action. Plain English, factual, no opinions.
ICAI rules: no self-promotion, no 'contact us', no superlatives, no fees, no guarantees.
If you cannot verify what the document says from the official source, return an empty string for that item."""


def main():
    if not claude_util.has_key():
        print("No AI key set – summaries skipped")
        return 0
    updates = json.loads(UPD.read_text(encoding="utf-8"))["items"]
    summaries = json.loads(SUM.read_text(encoding="utf-8")) if SUM.exists() else {}
    cutoff = (dt.datetime.now(IST).date() - dt.timedelta(days=5)).isoformat()
    todo = [u for u in updates if u["link"] not in summaries and u["date"] >= cutoff
            and (u["kind"] == "circular" or u["source"] in ("GST", "CBDT", "MCA", "CBIC"))][:MAX_PER_RUN]
    if not todo:
        print("Nothing new to summarise")
        return 0
    listing = "\n".join(f'{i + 1}. [{u["source"]}] {u["title"]} ({u["date"]}) {u["link"]}' for i, u in enumerate(todo))
    prompt = f"""{GUIDE}

Items (read each on the official website before summarising):
{listing}

Return ONLY a JSON array of strings, one per item, in the same order."""
    out = claude_util.ask_json(prompt, allowed_domains=OFFICIAL, max_searches=min(10, len(todo) + 2))
    added = 0
    for u, text in zip(todo, out if isinstance(out, list) else []):
        text = (text or "").strip()
        if text:
            summaries[u["link"]] = {"summary": text[:300], "date": dt.datetime.now(IST).date().isoformat()}
            added += 1
    SUM.write_text(json.dumps(summaries, indent=1, ensure_ascii=False), encoding="utf-8")
    review = ROOT / "automation" / "summaries_review.md"
    review.write_text("# Summaries for review\n\nMerging publishes these under *Summary by CA. Kunal Darwani*. "
                      "Edit `data/summaries.json` in this pull request to correct any text.\n\n" +
                      "\n".join(f"- **{u['title']}**\n  {summaries.get(u['link'], {}).get('summary', '(skipped)')}\n  {u['link']}"
                                for u in todo) + "\n", encoding="utf-8")
    print(f"Drafted {added} summaries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
