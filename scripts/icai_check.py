#!/usr/bin/env python3
"""ICAI wording check for website content and blog posts.

Flags words and patterns that conflict with the ICAI Code of Ethics and the
Guidelines on Advertisement and Websites (superlatives, fee mentions,
testimonials, client names, guarantees, solicitation, etc.).

Usage:  python scripts/icai_check.py               -> checks content/ and data/
        python scripts/icai_check.py FILE [FILE..]  -> checks given files
Exit code 1 if any HIGH finding exists (used to block a pull request).
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HIGH = [
    (r"\b(best|leading|top|premier|foremost|finest|no\.?\s*1|number one|most experienced|largest)\s+(firm|firms|ca|cas|chartered|accountants?|consultants?|advisors?|advisers?|tax|gst|audit|services?|team|professionals?|in\s+(agra|india|uttar|the\s+city))\b", "Superlative / comparative claim"),
    (r"\b(unmatched|unrivalled|unparalleled|second to none|one-stop)\b", "Superlative / comparative claim"),
    (r"\b(expert|experts|specialist|specialists|guru)\b", "Self-description as expert/specialist (ICAI: no specialty designations)"),
    (r"(?<!not )\bguarantee(d|s)?\b|\b100\s*%\s*(success|approval|refund)\b", "Guarantee of outcome"),
    (r"(₹|rs\.?|inr)\s?\d[\d,]*\s*(/-)?\s*(only|onwards|per\s+(filing|return|registration|engagement))", "Professional fee / price mention"),
    (r"\b(our|the firm'?s?|professional)\s+fees?\s+(is|are|start|starting|from)\b", "Professional fee mention"),
    (r"\b(free|complimentary)\s+(consultation|filing|registration|service|advice)\b", "Free service offer"),
    (r"\b(discount|offer|cashback|limited period|hurry)\b", "Promotional offer"),
    (r"\btestimonial|what our clients say|client reviews?|star rating|★", "Testimonial / review"),
    (r"\bwhy choose us\b|\bwhy us\b", "'Why choose us' promotion"),
    (r"\b(our clients include|clients like|trusted by|serving clients such as)\b", "Client name disclosure"),
    (r"\b(award|awarded|award-winning|ranked)\b|(?<!zero-)\brated\s+(as|among|by)\b", "Awards / rankings"),
    (r"\b(contact us now|call now|book now|act now|don'?t miss)\b", "Solicitation / call to action"),
    (r"\bsuccess rate\b", "Success-rate claim"),
]
MEDIUM = [
    (r"\b(hassle[- ]free|cheapest|affordable|lowest|quickest|fastest)\b", "Promotional adjective"),
    (r"\b(trusted|reliable|renowned|reputed)\b", "Subjective quality claim"),
    (r"\b(loan arrangement|we arrange loans|loan agent)\b", "Activity outside permitted scope"),
]
# Words that are fine in a technical sense (e.g. 'top layer' in RBI framework)
ALLOW = [r"top layer", r"upper layer", r"best-judg?ement", r"best judg?ement", r"stop the proceedings",
         r"top of", r"guarantee fund", r"credit guarantee", r"bank guarantee", r"guarantee cover", r"\bguarantee scheme",
         r"do(es)? not act as a loan agent", r"does not arrange or guarantee loans", r"not arrange or guarantee"]


def scan(path: Path):
    text = path.read_text(encoding="utf-8")
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        clean = low
        for a in ALLOW:
            clean = re.sub(a, " ", clean)
        for level, rules in (("HIGH", HIGH), ("MEDIUM", MEDIUM)):
            for pat, why in rules:
                m = re.search(pat, clean, re.I)
                if m:
                    out.append((level, path.relative_to(ROOT), i, why, line.strip()[:110]))
    return out


def main():
    files = [Path(f).resolve() for f in sys.argv[1:]] or \
        list((ROOT / "content").rglob("*.md")) + [f for f in (ROOT / "data").glob("*.json") if f.name != "updates.json"] + list((ROOT / "templates").glob("*.html"))
    findings = [f for p in files if p.exists() for f in scan(p)]
    for lvl, p, ln, why, ctx in findings:
        print(f"[{lvl}] {p}:{ln}  {why}\n        {ctx}")
    highs = sum(1 for f in findings if f[0] == "HIGH")
    print(f"\n{len(files)} files checked · {highs} high · {len(findings) - highs} medium")
    sys.exit(1 if highs else 0)


if __name__ == "__main__":
    main()
