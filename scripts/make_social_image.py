#!/usr/bin/env python3
"""Make a 1080x1350 branded image card for a Knowledge Centre article (Instagram / social)."""
import datetime as dt
import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "automation" / "fonts"
SERIF = FONTS / "SourceSerif4[opsz,wght].ttf"
SANS = FONTS / "IBMPlexSans[wdth,wght].ttf"

W, H = 1080, 1350
NAVY_TOP, NAVY_BOT = (20, 52, 98), (11, 31, 60)
GOLD, GOLD_SOFT = (214, 168, 84), (176, 122, 28)
WHITE, MUTED = (255, 255, 255), (196, 210, 230)
PAD = 96

TOPIC = [("gst", "GST"), ("tds", "TDS"), ("income", "Income Tax"), ("tax-audit", "Income Tax"),
         ("itr", "Income Tax"), ("company", "Company Law"), ("llp", "LLP"), ("nidhi", "Company Law"),
         ("audit", "Audit"), ("msme", "MSME"), ("startup", "Startup"), ("fssai", "Licensing"),
         ("iec", "Licensing"), ("pf", "Payroll"), ("payroll", "Payroll"), ("accounting", "Accounting"),
         ("foreign", "Accounting")]


FONT_URLS = {
    SERIF: "https://raw.githubusercontent.com/google/fonts/main/ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf",
    SANS: "https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsans/IBMPlexSans%5Bwdth,wght%5D.ttf",
}


def ensure_fonts():
    import urllib.request
    FONTS.mkdir(parents=True, exist_ok=True)
    for path, url in FONT_URLS.items():
        if not path.exists():
            urllib.request.urlretrieve(url, path)


def font(path, size, weight):
    ensure_fonts()
    f = ImageFont.truetype(str(path), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:  # noqa: BLE001
        pass
    return f


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def card(meta, slug, out):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(NAVY_TOP, NAVY_BOT)))
    # soft gold arc, top-right
    d.ellipse([W - 330, -330, W + 330, 330], outline=(*GOLD_SOFT,), width=3)
    d.ellipse([W - 250, -250, W + 250, 250], outline=(60, 80, 112), width=2)

    # header
    small = font(SANS, 30, "SemiBold")
    d.text((PAD, PAD + 4), "KNOWLEDGE CENTRE", font=small, fill=GOLD)
    d.rectangle([PAD, PAD + 58, PAD + 90, PAD + 63], fill=GOLD)

    svc = str(meta.get("service", ""))
    topic = next((v for k, v in TOPIC if k in svc or k in slug), "Compliance")
    chip_f = font(SANS, 28, "Medium")
    tw = d.textlength(topic.upper(), font=chip_f)
    cy = PAD + 120
    d.rounded_rectangle([PAD, cy, PAD + tw + 44, cy + 54], radius=27, outline=GOLD, width=2)
    d.text((PAD + 22, cy + 9), topic.upper(), font=chip_f, fill=GOLD)

    # title + summary: largest title size that leaves room for the summary above the call-to-action
    title = str(meta.get("title", "")).strip()
    summ = str(meta.get("summary", "")).strip()
    sf = font(SANS, 36, "Regular")
    summ_lines = wrap(d, summ, sf, W - 2 * PAD)
    limit = H - PAD - 150 - 86 - 30          # top of the call-to-action line, minus a gap
    top = cy + 110
    for size in (84, 78, 72, 66, 60, 56, 52, 48):
        tf = font(SERIF, size, "SemiBold")
        lines = wrap(d, title, tf, W - 2 * PAD)
        lh = int(size * 1.18)
        room = (limit - (top + len(lines) * lh + 34)) // 52
        if len(lines) <= 5 and room >= min(len(summ_lines), 4):
            break
    y = top
    for ln in lines:
        d.text((PAD, y), ln, font=tf, fill=WHITE)
        y += lh
    y += 34
    show = summ_lines[: max(0, min(room, 5))]
    if show and len(show) < len(summ_lines):
        show[-1] = show[-1].rstrip(" ,.;:") + "…"
    for ln in show:
        d.text((PAD, y), ln, font=sf, fill=MUTED)
        y += 52

    # footer
    fy = H - PAD - 150
    cta_f = font(SANS, 32, "Medium")
    d.text((PAD, fy - 86), "Read the full article at kunaldarwani.com/blog", font=cta_f, fill=GOLD)
    d.rectangle([PAD, fy, W - PAD, fy + 2], fill=(70, 92, 126))
    d.text((PAD, fy + 32), "Kunal Darwani & Company", font=font(SERIF, 44, "SemiBold"), fill=WHITE)
    d.text((PAD, fy + 92), "Chartered Accountants  ·  Agra", font=font(SANS, 30, "Regular"), fill=MUTED)
    date = meta.get("date")
    try:
        ds = (date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date))).strftime("%-d %B %Y")
    except Exception:  # noqa: BLE001
        ds = ""
    rf = font(SANS, 30, "Medium")
    site = "kunaldarwani.com"
    d.text((W - PAD - d.textlength(site, font=rf), fy + 40), site, font=rf, fill=GOLD)
    if ds:
        df = font(SANS, 26, "Regular")
        d.text((W - PAD - d.textlength(ds, font=df), fy + 94), ds, font=df, fill=MUTED)

    img.save(out, "PNG", optimize=True)


def card_wide(meta, slug, out, w=1200, h=900):
    """Landscape card for Google Business Profile posts and link previews."""
    pad = 72
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(NAVY_TOP, NAVY_BOT)))
    d.ellipse([w - 300, -300, w + 300, 300], outline=GOLD_SOFT, width=3)
    d.ellipse([w - 225, -225, w + 225, 225], outline=(60, 80, 112), width=2)

    small = font(SANS, 26, "SemiBold")
    d.text((pad, pad), "KNOWLEDGE CENTRE", font=small, fill=GOLD)
    d.rectangle([pad, pad + 48, pad + 80, pad + 52], fill=GOLD)
    svc = str(meta.get("service", ""))
    topic = next((v for k, v in TOPIC if k in svc or k in slug), "Compliance")
    chip_f = font(SANS, 24, "Medium")
    x0 = pad + d.textlength("KNOWLEDGE CENTRE", font=small) + 28
    tw = d.textlength(topic.upper(), font=chip_f)
    d.rounded_rectangle([x0, pad - 8, x0 + tw + 36, pad + 38], radius=23, outline=GOLD, width=2)
    d.text((x0 + 18, pad - 1), topic.upper(), font=chip_f, fill=GOLD)

    title = str(meta.get("title", "")).strip()
    for size in (72, 66, 60, 56, 52, 48):
        tf = font(SERIF, size, "SemiBold")
        lines = wrap(d, title, tf, w - 2 * pad - 60)
        if len(lines) <= 3:
            break
    y = pad + 110
    for ln in lines[:4]:
        d.text((pad, y), ln, font=tf, fill=WHITE)
        y += int(size * 1.18)

    fy = h - pad - 110
    sf = font(SANS, 30, "Regular")
    y += 26
    room = max(0, (fy - 40 - y) // 44)
    for ln in wrap(d, str(meta.get("summary", "")).strip(), sf, w - 2 * pad)[: min(3, room)]:
        d.text((pad, y), ln, font=sf, fill=MUTED)
        y += 44

    d.rectangle([pad, fy, w - pad, fy + 2], fill=(70, 92, 126))
    d.text((pad, fy + 26), "Kunal Darwani & Company", font=font(SERIF, 38, "SemiBold"), fill=WHITE)
    d.text((pad, fy + 76), "Chartered Accountants  ·  Agra", font=font(SANS, 26, "Regular"), fill=MUTED)
    rf = font(SANS, 28, "Medium")
    site = "kunaldarwani.com"
    d.text((w - pad - d.textlength(site, font=rf), fy + 32), site, font=rf, fill=GOLD)
    date = meta.get("date")
    try:
        ds = (date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date))).strftime("%-d %B %Y")
        df = font(SANS, 24, "Regular")
        d.text((w - pad - d.textlength(ds, font=df), fy + 78), ds, font=df, fill=MUTED)
    except Exception:  # noqa: BLE001
        pass
    img.save(out, "PNG", optimize=True)


def front_matter(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return yaml.safe_load(m.group(1)) if m else {}


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    wide = len(sys.argv) > 3 and sys.argv[3] == "--wide"
    (card_wide if wide else card)(front_matter(src), Path(src).stem, out)
    print("wrote", out)
