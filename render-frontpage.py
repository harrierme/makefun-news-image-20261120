#!/usr/bin/env python3
"""Render the one-page newspaper for Friday 20 November 2026.

Reads stories.md (the verified research list: 4 leads, 12 cards, 36
briefs, a DATE CHECK box and a footer) and draws a 1024x1024 front
page with Pillow. This script runs only on the build machine; the
grader never runs it. The graded entrypoint (main.ts) only copies the
entry.png this script produces into /output, so the two graded runs
are byte-identical.

Palette: cream paper, black ink, brick red for the masthead and tags,
navy for the markets strip. Serif bold for the masthead and headlines,
sans for labels and briefs. Every illustration is drawn here from
simple shapes; no photos and no outside files are used.
"""

import hashlib
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent
W, H = 1024, 1024
MARGIN = 14
CONTENT_W = W - 2 * MARGIN

PAPER = (247, 242, 231)
INK = (17, 17, 17)
RED = (158, 43, 37)
NAVY = (31, 58, 95)
TAN = (217, 201, 168)
TAN_DARK = (120, 100, 70)
GOLD = (176, 141, 58)
SKY = (70, 110, 150)
SKY_DARK = (24, 48, 80)
GREEN = (46, 110, 70)
GREY = (90, 90, 88)
FAINT = (150, 140, 120)

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def load_font(path, size):
    return ImageFont.truetype(path, size)


def wrap_text(draw, text, fnt, width):
    """Split text into lines that fit width (plain word wrap)."""
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, text, fnt, width, max_lines):
    """Wrap text; if it runs past max_lines, trim the tail with ..."""
    lines = wrap_text(draw, text, fnt, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines and draw.textlength(lines[-1] + " ...", font=fnt) > width:
            tail = lines[-1]
            if " " in tail:
                lines[-1] = tail.rsplit(" ", 1)[0]
            else:
                lines[-1] = tail[:-1]
        lines[-1] = lines[-1] + " ..."
    return lines


def truncate(draw, text, fnt, width):
    """Shorten one line to fit width, ending with ..."""
    if draw.textlength(text, font=fnt) <= width:
        return text
    while text and draw.textlength(text + " ...", font=fnt) > width:
        if " " in text:
            text = text.rsplit(" ", 1)[0]
        else:
            text = text[:-1]
    return text + " ..."


def draw_centered(draw, cx, y, text, fnt, fill):
    w = draw.textlength(text, font=fnt)
    draw.text((cx - w / 2, y), text, font=fnt, fill=fill)


def fit_size(draw, text, path, sizes, width):
    """Biggest font size from sizes whose text fits width."""
    for size in sizes:
        fnt = load_font(path, size)
        if draw.textlength(text, font=fnt) <= width:
            return fnt
    return load_font(path, sizes[-1])

# ---------------------------------------------------------------------------
# Parsing stories.md (the verified research list, kept as a data file)
# ---------------------------------------------------------------------------

PIN_RE = re.compile(r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)")
BRIEF_RE = re.compile(
    r"^(\d+)\.\s+([^:]+):\s+(.+?)\s+"
    r"\((CONFIRMED|REPORTED|CLAIM|OFFICIAL|FORECAST)\)\s*$"
)
DOT_RE = re.compile(r"[·•]")


def split_dot(text):
    return [part.strip() for part in DOT_RE.split(text)]


def parse_header(line):
    """Parse '5. MIDDLE EAST · GULF | CLAIM · Reuters' into fields."""
    m = re.match(r"^(\d+)\.\s+(.+)$", line)
    num = int(m.group(1))
    rest = m.group(2)
    left, _, right = rest.partition("|")
    parts = split_dot(left.strip())
    region = parts[0] if parts else ""
    field = parts[1] if len(parts) > 1 else ""
    label = ""
    source = ""
    right = right.strip()
    if right:
        rparts = split_dot(right)
        label = rparts[0] if rparts else ""
        source = rparts[1] if len(rparts) > 1 else ""
    return {"num": num, "region": region, "field": field,
            "label": label, "source": source}


def parse_items(lines):
    """Parse the LEAD / KARTU sections into story dicts."""
    items = []
    cur = None
    field = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            cur = parse_header(line)
            cur["headline"] = ""
            cur["summary"] = ""
            cur["lat"] = None
            cur["lon"] = None
            items.append(cur)
            field = None
            continue
        if cur is None:
            continue
        if line.startswith("Headline:"):
            cur["headline"] = line[len("Headline:"):].strip()
            field = "headline"
        elif line.startswith("Ringkasan:"):
            cur["summary"] = line[len("Ringkasan:"):].strip()
            field = "summary"
        elif "Pin:" in line:
            before, _, pinpart = line.partition("Pin:")
            before = before.strip()
            if before:
                if field == "summary" and cur["summary"]:
                    cur["summary"] += " " + before
                elif field == "headline":
                    cur["headline"] += " " + before
                else:
                    cur["summary"] = before
                    field = "summary"
            pm = PIN_RE.search("Pin:" + pinpart)
            if pm:
                cur["lat"] = float(pm.group(1))
                cur["lon"] = float(pm.group(2))
            field = None
        elif line.startswith("Pin"):
            pm = PIN_RE.search(line)
            if pm:
                cur["lat"] = float(pm.group(1))
                cur["lon"] = float(pm.group(2))
            field = None
        elif field == "summary":
            cur["summary"] += " " + line
        elif field == "headline":
            cur["headline"] += " " + line
        elif field is None:
            cur["summary"] = line
            field = "summary"
    return items


def parse_masthead(lines):
    out = {}
    last_key = None
    for raw in lines:
        line = raw.strip()
        if line.startswith("- "):
            body = line[2:]
            key, _, val = body.partition(": ")
            out[key.strip()] = val.strip()
            last_key = key.strip()
        elif line and last_key is not None:
            out[last_key] += " " + line
    return out


def mast_value(mast, prefix, default=""):
    for key, val in mast.items():
        if key.startswith(prefix):
            return val
    return default


def parse_datecheck(lines):
    excluded = []
    notyet = []
    mode = None
    for raw in lines:
        line = raw.strip()
        if line.startswith("Dibuang"):
            mode = "excluded"
        elif line.startswith("Belum"):
            mode = "notyet"
        elif line.startswith("- ") and mode:
            item = line[2:].strip()
            if mode == "excluded":
                excluded.append(item)
            else:
                notyet.append(item)
    return excluded, notyet


def parse_stories(path):
    text = Path(path).read_text(encoding="utf-8")
    sections = {}
    current = None
    for raw in text.splitlines():
        if raw.startswith("## "):
            current = raw[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(raw)

    def find(prefix):
        for name, lines in sections.items():
            if name.startswith(prefix):
                return lines
        return []

    mast = parse_masthead(find("Masthead"))
    leads = parse_items(find("LEAD"))
    cards = parse_items(find("KARTU"))
    briefs = []
    for raw in find("BRIEF"):
        m = BRIEF_RE.match(raw.strip())
        if m:
            briefs.append({"num": int(m.group(1)), "place": m.group(2).strip(),
                           "text": m.group(3).strip(), "label": m.group(4)})
    excluded, notyet = parse_datecheck(find("DATE CHECK"))
    footer = [line.strip() for line in find("FOOTER") if line.strip()]
    return {
        "kicker": mast_value(mast, "Kicker"),
        "date_line": mast_value(mast, "Headline tanggal"),
        "counts": mast_value(mast, "Hitungan"),
        "region_strip": mast_value(mast, "Strip region"),
        "numbers": mast_value(mast, "Strip angka"),
        "leads": leads,
        "cards": cards,
        "briefs": briefs,
        "excluded": excluded,
        "notyet": notyet,
        "footer": footer,
    }

# ---------------------------------------------------------------------------
# Drawn illustrations (all original shapes, no photos, no outside files)
# ---------------------------------------------------------------------------

def scene_skyline(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=SKY_DARK)
    for fx, fy in [(0.1, 0.15), (0.3, 0.08), (0.5, 0.2), (0.7, 0.1),
                   (0.85, 0.22), (0.2, 0.3), (0.6, 0.3)]:
        d.ellipse([x + fx * w - 1, y + fy * h - 1, x + fx * w + 1, y + fy * h + 1],
                  fill=(255, 255, 255))
    for fx, fw, fh in [(0.0, 0.18, 0.55), (0.2, 0.14, 0.75), (0.36, 0.16, 0.45),
                       (0.54, 0.14, 0.65), (0.7, 0.16, 0.5), (0.88, 0.12, 0.6)]:
        bx, bw, bh = x + fx * w, fw * w, fh * h
        d.rectangle([bx, y + h - bh, bx + bw, y + h], fill=INK)
        for wy in (0.25, 0.5, 0.75):
            for wx in (0.3, 0.65):
                d.rectangle([bx + wx * bw - 1, y + h - bh + wy * bh - 1,
                             bx + wx * bw + 1, y + h - bh + wy * bh + 1], fill=GOLD)
    for bx, tx, ty in [(0.15, 0.45, 0.18), (0.5, 0.7, 0.12), (0.8, 0.6, 0.25)]:
        d.line([x + bx * w, y + h, x + tx * w, y + ty * h], fill=RED, width=2)
        d.ellipse([x + tx * w - 3, y + ty * h - 3, x + tx * w + 3, y + ty * h + 3],
                  fill=(255, 255, 255))
        d.ellipse([x + tx * w - 5, y + ty * h - 5, x + tx * w + 5, y + ty * h + 5],
                  outline=RED, width=1)


def scene_bridge(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(232, 238, 242))
    d.rectangle([x, y + h * 0.68, x + w, y + h], fill=SKY)
    d.line([x, y + h * 0.55, x + w, y + h * 0.55], fill=INK, width=3)
    for tx in (0.25, 0.75):
        d.rectangle([x + tx * w - 2, y + h * 0.3, x + tx * w + 2, y + h * 0.55],
                    fill=INK)
        d.line([x + tx * w, y + h * 0.3, x + tx * w - w * 0.2, y + h * 0.55],
               fill=INK, width=1)
        d.line([x + tx * w, y + h * 0.3, x + tx * w + w * 0.2, y + h * 0.55],
               fill=INK, width=1)
    for i in range(7):
        px = x + w * (0.08 + i * 0.05)
        py = y + h * (0.5 - i * 0.045)
        d.ellipse([px - 1, py - 1, px + 1, py + 1], fill=INK)
    d.ellipse([x + w * 0.55, y + h * 0.42, x + w * 0.7, y + h * 0.54], fill=GREY)


def scene_flags(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    for i, col in enumerate((RED, NAVY, GOLD)):
        bx = x + w * (0.06 + i * 0.32)
        bw = w * 0.26
        d.rectangle([bx, y + h * 0.08, bx + bw, y + h * 0.55], fill=col)
        d.ellipse([bx + bw / 2 - 4, y + h * 0.22, bx + bw / 2 + 4, y + h * 0.22 + 8],
                  fill=(255, 255, 255))
    d.ellipse([x + w * 0.2, y + h * 0.72, x + w * 0.8, y + h * 0.86], fill=TAN_DARK)
    d.line([x + w * 0.2, y + h * 0.79, x + w * 0.8, y + h * 0.79], fill=INK, width=2)


def scene_market(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.line([x + w * 0.12, y + h * 0.12, x + w * 0.12, y + h * 0.88], fill=INK, width=1)
    d.line([x + w * 0.12, y + h * 0.88, x + w * 0.95, y + h * 0.88], fill=INK, width=1)
    pts = [(0.15, 0.25), (0.3, 0.35), (0.45, 0.3), (0.6, 0.5), (0.75, 0.62), (0.9, 0.8)]
    for (fx1, fy1), (fx2, fy2) in zip(pts, pts[1:]):
        d.line([x + fx1 * w, y + fy1 * h, x + fx2 * w, y + fy2 * h],
               fill=RED, width=3)
    for fx, fy in pts:
        d.ellipse([x + fx * w - 2, y + fy * h - 2, x + fx * w + 2, y + fy * h + 2],
                  fill=RED)


def scene_strait(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.rectangle([x, y + h * 0.45, x + w, y + h], fill=SKY)
    for wy in (0.55, 0.75, 0.92):
        d.arc([x + w * 0.05, y + h * wy, x + w * 0.45, y + h * wy + 12],
              200, 340, fill=(255, 255, 255), width=2)
        d.arc([x + w * 0.55, y + h * wy, x + w * 0.95, y + h * wy + 12],
              200, 340, fill=(255, 255, 255), width=2)
    d.polygon([(x + w * 0.2, y + h * 0.55), (x + w * 0.8, y + h * 0.55),
               (x + w * 0.72, y + h * 0.4), (x + w * 0.28, y + h * 0.4)], fill=INK)
    for i, col in enumerate((RED, NAVY, GOLD)):
        d.rectangle([x + w * (0.3 + i * 0.13), y + h * 0.28,
                     x + w * (0.4 + i * 0.13), y + h * 0.4], fill=col)
    d.polygon([(x, y), (x + w * 0.25, y), (x, y + h * 0.45)], fill=TAN)
    d.polygon([(x + w, y), (x + w * 0.75, y), (x + w, y + h * 0.45)], fill=TAN)


def scene_jets(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(232, 238, 242))
    for jx, jy, s in [(0.3, 0.35, 1.0), (0.62, 0.6, 0.8)]:
        cx, cy = x + jx * w, y + jy * h
        d.polygon([(cx - 14 * s, cy), (cx + 14 * s, cy - 4 * s),
                   (cx + 6 * s, cy + 5 * s)], fill=INK)
        d.line([cx - 14 * s, cy, cx - 34 * s, cy + 6 * s], fill=(255, 255, 255), width=2)
        d.line([cx - 14 * s, cy + 2, cx - 30 * s, cy + 12 * s], fill=GREY, width=1)


def scene_shield(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    cx = x + w / 2
    pts = [(cx - w * 0.28, y + h * 0.12), (cx + w * 0.28, y + h * 0.12),
           (cx + w * 0.28, y + h * 0.5), (cx, y + h * 0.88),
           (cx - w * 0.28, y + h * 0.5)]
    d.polygon(pts, fill=TAN, outline=NAVY, width=2)
    d.line([cx - w * 0.14, y + h * 0.45, cx - w * 0.02, y + h * 0.62,
            cx + w * 0.18, y + h * 0.3], fill=RED, width=3)


def scene_summit(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.polygon([(x + w * 0.12, y + h * 0.35), (x + w * 0.88, y + h * 0.35),
               (x + w * 0.5, y + h * 0.12)], fill=TAN_DARK)
    for i in range(4):
        bx = x + w * (0.18 + i * 0.18)
        d.rectangle([bx, y + h * 0.38, bx + w * 0.08, y + h * 0.78], fill=INK)
    d.rectangle([x + w * 0.1, y + h * 0.78, x + w * 0.9, y + h * 0.82], fill=INK)
    d.rectangle([x + w * 0.08, y + h * 0.84, x + w * 0.92, y + h * 0.88], fill=INK)


def scene_court(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.polygon([(x + w * 0.15, y + h * 0.3), (x + w * 0.85, y + h * 0.3),
               (x + w * 0.5, y + h * 0.1)], fill=TAN_DARK)
    for i in range(3):
        bx = x + w * (0.22 + i * 0.22)
        d.rectangle([bx, y + h * 0.33, bx + w * 0.08, y + h * 0.68], fill=INK)
    d.line([x + w * 0.5, y + h * 0.72, x + w * 0.5, y + h * 0.9], fill=INK, width=2)
    d.line([x + w * 0.3, y + h * 0.78, x + w * 0.7, y + h * 0.78], fill=INK, width=2)
    d.arc([x + w * 0.2, y + h * 0.78, x + w * 0.4, y + h * 0.9], 0, 180, fill=INK, width=2)
    d.arc([x + w * 0.6, y + h * 0.78, x + w * 0.8, y + h * 0.9], 0, 180, fill=INK, width=2)


def scene_ipo(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    for i, (fh, col) in enumerate([(0.3, NAVY), (0.5, GREEN), (0.72, GOLD)]):
        bx = x + w * (0.16 + i * 0.28)
        d.rectangle([bx, y + h * (0.88 - fh), bx + w * 0.18, y + h * 0.88], fill=col)
    d.line([x + w * 0.18, y + h * 0.3, x + w * 0.5, y + h * 0.18,
            x + w * 0.82, y + h * 0.08], fill=RED, width=3)
    d.polygon([(x + w * 0.82, y + h * 0.08), (x + w * 0.72, y + h * 0.08),
               (x + w * 0.82, y + h * 0.18)], fill=RED)


def scene_outage(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.rectangle([x + w * 0.14, y + h * 0.14, x + w * 0.86, y + h * 0.68],
                fill=INK)
    d.rectangle([x + w * 0.2, y + h * 0.2, x + w * 0.8, y + h * 0.62],
                fill=(232, 238, 242))
    d.line([x + w * 0.34, y + h * 0.28, x + w * 0.66, y + h * 0.54],
           fill=RED, width=3)
    d.line([x + w * 0.66, y + h * 0.28, x + w * 0.34, y + h * 0.54],
           fill=RED, width=3)
    d.line([x + w * 0.42, y + h * 0.68, x + w * 0.58, y + h * 0.68], fill=INK, width=3)
    d.line([x + w * 0.32, y + h * 0.82, x + w * 0.68, y + h * 0.82], fill=INK, width=3)


def scene_capitol(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.line([x + w * 0.5, y + h * 0.06, x + w * 0.5, y + h * 0.16], fill=INK, width=2)
    d.polygon([(x + w * 0.5, y + h * 0.06), (x + w * 0.66, y + h * 0.1),
               (x + w * 0.5, y + h * 0.14)], fill=RED)
    d.pieslice([x + w * 0.28, y + h * 0.14, x + w * 0.72, y + h * 0.58],
               180, 360, fill=NAVY)
    d.rectangle([x + w * 0.24, y + h * 0.56, x + w * 0.76, y + h * 0.78], fill=TAN_DARK)
    d.rectangle([x + w * 0.18, y + h * 0.78, x + w * 0.82, y + h * 0.84], fill=INK)
    d.rectangle([x + w * 0.14, y + h * 0.86, x + w * 0.86, y + h * 0.9], fill=INK)


def scene_embassy(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.rectangle([x + w * 0.16, y + h * 0.2, x + w * 0.84, y + h * 0.82], fill=TAN)
    for wy in (0.32, 0.5, 0.68):
        for wx in (0.28, 0.5, 0.72):
            d.rectangle([x + wx * w - 3, y + wy * h - 4, x + wx * w + 3, y + wy * h + 4],
                        fill=INK)
    d.line([x + w * 0.5, y + h * 0.08, x + w * 0.5, y + h * 0.2], fill=INK, width=2)
    d.polygon([(x + w * 0.5, y + h * 0.08), (x + w * 0.68, y + h * 0.12),
               (x + w * 0.5, y + h * 0.16)], fill=RED)
    d.line([x + w * 0.3, y + h * 0.2, x + w * 0.45, y + h * 0.45,
            x + w * 0.35, y + h * 0.6, x + w * 0.55, y + h * 0.82], fill=RED, width=2)


def scene_climate(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    cx, cy, r = x + w * 0.32, y + h * 0.3, min(w, h) * 0.16
    for ang in range(0, 360, 45):
        import math
        a = math.radians(ang)
        d.line([cx + (r + 2) * math.cos(a), cy + (r + 2) * math.sin(a),
                cx + (r + 8) * math.cos(a), cy + (r + 8) * math.sin(a)],
               fill=GOLD, width=2)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    d.ellipse([x + w * 0.55, y + h * 0.55, x + w * 0.92, y + h * 0.9], fill=GREEN)
    d.line([x + w * 0.55, y + h * 0.9, x + w * 0.92, y + h * 0.55], fill=INK, width=1)


def scene_tennis(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.rectangle([x + w * 0.1, y + h * 0.16, x + w * 0.9, y + h * 0.84], fill=GREEN)
    d.rectangle([x + w * 0.1, y + h * 0.16, x + w * 0.9, y + h * 0.84],
                outline=(255, 255, 255), width=2)
    d.line([x + w * 0.5, y + h * 0.16, x + w * 0.5, y + h * 0.84],
           fill=(255, 255, 255), width=1)
    d.line([x + w * 0.1, y + h * 0.5, x + w * 0.9, y + h * 0.5],
           fill=(255, 255, 255), width=2)
    d.ellipse([x + w * 0.68, y + h * 0.62, x + w * 0.68 + 10, y + h * 0.62 + 10],
              fill=GOLD, outline=INK, width=1)


def scene_cricket(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PAPER)
    d.rectangle([x, y + h * 0.78, x + w, y + h * 0.86], fill=TAN)
    for i in range(3):
        bx = x + w * (0.3 + i * 0.1)
        d.line([bx, y + h * 0.3, bx, y + h * 0.78], fill=GOLD, width=3)
    d.line([x + w * 0.3, y + h * 0.28, x + w * 0.5, y + h * 0.28], fill=GOLD, width=2)
    d.polygon([(x + w * 0.62, y + h * 0.2), (x + w * 0.72, y + h * 0.26),
               (x + w * 0.6, y + h * 0.62), (x + w * 0.52, y + h * 0.56)], fill=TAN_DARK)
    d.ellipse([x + w * 0.72, y + h * 0.68, x + w * 0.72 + 9, y + h * 0.68 + 9],
              fill=RED)


SCENES = {
    "skyline": scene_skyline, "bridge": scene_bridge, "flags": scene_flags,
    "market": scene_market, "strait": scene_strait, "jets": scene_jets,
    "shield": scene_shield, "summit": scene_summit, "court": scene_court,
    "ipo": scene_ipo, "outage": scene_outage, "capitol": scene_capitol,
    "embassy": scene_embassy, "climate": scene_climate,
    "tennis": scene_tennis, "cricket": scene_cricket,
}

LEAD_SCENES = {1: "skyline", 2: "bridge", 3: "flags", 4: "market"}
CARD_SCENES = {5: "strait", 6: "jets", 7: "shield", 8: "summit", 9: "court",
               10: "ipo", 11: "outage", 12: "capitol", 13: "embassy",
               14: "climate", 15: "tennis", 16: "cricket"}


def draw_scene(d, box, kind):
    x, y, w, h = box
    d.rectangle([x, y, x + w, y + h], outline=FAINT, width=1)
    SCENES[kind](d, x + 1, y + 1, w - 2, h - 2)


# ---------------------------------------------------------------------------
# Schematic world map with numbered pins
# ---------------------------------------------------------------------------

CONTINENTS = {
    "NA": [(-168, 66), (-150, 70), (-135, 69), (-125, 71), (-115, 68), (-105, 68),
           (-95, 69), (-88, 66), (-82, 66), (-78, 71), (-70, 62), (-60, 52),
           (-55, 47), (-62, 44), (-68, 42), (-74, 38), (-76, 35), (-80, 32),
           (-81, 26), (-85, 30), (-90, 21), (-95, 18), (-100, 16), (-105, 20),
           (-110, 23), (-115, 29), (-120, 34), (-124, 40), (-124, 48),
           (-130, 55), (-140, 60), (-155, 58), (-165, 60)],
    "SA": [(-79, 9), (-77, 8), (-75, 10), (-72, 12), (-68, 11), (-64, 10),
           (-60, 8), (-55, 6), (-52, 4), (-50, 0), (-45, -3), (-40, -5),
           (-35, -8), (-37, -13), (-39, -17), (-41, -22), (-46, -24),
           (-48, -28), (-52, -32), (-55, -35), (-58, -38), (-62, -41),
           (-65, -43), (-68, -47), (-70, -52), (-73, -53), (-72, -48),
           (-73, -40), (-72, -33), (-72, -25), (-75, -18), (-78, -10),
           (-80, -5), (-81, 0), (-80, 5)],
    "EU": [(-10, 36), (-9, 38), (-9, 43), (-4, 44), (-2, 47), (-4, 48),
           (-6, 49), (-3, 50), (0, 51), (2, 51), (4, 53), (6, 54), (8, 55),
           (8, 57), (10, 58), (12, 56), (10, 59), (6, 60), (6, 62), (8, 64),
           (12, 66), (15, 68), (18, 69), (22, 70), (26, 71), (30, 70),
           (32, 68), (35, 66), (38, 64), (40, 62), (42, 60), (40, 58),
           (38, 56), (35, 54), (32, 52), (30, 50), (28, 48), (28, 45),
           (26, 44), (24, 42), (23, 40), (22, 38), (20, 40), (18, 40),
           (16, 42), (14, 44), (12, 44), (10, 44), (8, 44), (6, 43),
           (3, 43), (0, 40), (-2, 37), (-5, 36), (-8, 37)],
    "AF": [(-17, 15), (-16, 20), (-15, 25), (-13, 28), (-10, 30), (-6, 33),
           (-3, 35), (0, 36), (5, 37), (10, 37), (12, 34), (15, 32),
           (18, 32), (22, 33), (25, 32), (28, 31), (30, 31), (32, 29),
           (33, 27), (34, 24), (35, 21), (36, 19), (38, 18), (39, 16),
           (40, 14), (42, 12), (44, 11), (46, 11), (48, 11), (50, 12),
           (51, 10), (49, 7), (47, 3), (44, 0), (42, -3), (40, -6),
           (39, -10), (38, -15), (36, -18), (35, -21), (34, -24),
           (33, -26), (32, -28), (30, -31), (28, -33), (25, -34),
           (22, -35), (19, -35), (17, -33), (15, -30), (13, -26),
           (12, -22), (12, -18), (11, -14), (10, -10), (9, -6), (9, -2),
           (9, 2), (8, 4), (5, 5), (0, 6), (-4, 5), (-8, 5), (-12, 7),
           (-15, 10), (-17, 13)],
    "AS": [(30, 70), (35, 69), (40, 68), (45, 68), (50, 69), (55, 69),
           (60, 70), (65, 70), (70, 71), (75, 72), (80, 73), (85, 74),
           (90, 75), (95, 76), (100, 77), (105, 77), (110, 76), (115, 74),
           (120, 73), (125, 72), (130, 71), (135, 71), (140, 72), (145, 71),
           (150, 70), (155, 69), (160, 68), (165, 67), (170, 67), (175, 66),
           (178, 65), (175, 63), (170, 60), (165, 60), (162, 56), (160, 53),
           (158, 50), (155, 48), (152, 45), (150, 42), (147, 40), (144, 38),
           (142, 36), (140, 33), (138, 30), (135, 28), (132, 26), (130, 24),
           (128, 22), (126, 20), (124, 18), (122, 16), (120, 14), (118, 12),
           (116, 10), (114, 8), (112, 6), (110, 4), (108, 2), (106, 4),
           (104, 6), (102, 8), (100, 10), (98, 12), (96, 14), (94, 16),
           (92, 18), (90, 20), (88, 22), (86, 20), (84, 19), (82, 17),
           (80, 15), (78, 13), (77, 10), (76, 8), (74, 10), (72, 14),
           (70, 18), (68, 22), (66, 24), (64, 25), (62, 25), (60, 25),
           (58, 26), (56, 27), (54, 26), (52, 25), (50, 26), (48, 28),
           (46, 30), (44, 31), (42, 33), (40, 35), (38, 37), (36, 38),
           (34, 40), (32, 41), (30, 42), (28, 44), (26, 45), (24, 45),
           (22, 44), (20, 43), (18, 44)],
    "AU": [(113, -22), (114, -26), (115, -31), (116, -35), (120, -34),
           (124, -33), (128, -32), (132, -32), (135, -35), (138, -35),
           (140, -38), (143, -39), (146, -39), (149, -37), (150, -34),
           (152, -31), (153, -28), (153, -25), (151, -22), (149, -20),
           (147, -19), (145, -17), (143, -14), (142, -11), (141, -12),
           (139, -14), (137, -12), (136, -15), (135, -14), (133, -12),
           (131, -12), (129, -13), (127, -14), (125, -15), (123, -17),
           (121, -19), (119, -20), (116, -21)],
}

LAT_TOP, LAT_BOT = 78.0, -58.0
PIN_OFFSETS = [(0, 0), (16, 0), (-16, 0), (0, 16), (0, -16), (16, 16),
               (-16, -16), (16, -16), (-16, 16), (24, 0), (0, 24),
               (-24, 0), (0, -24)]


def project(lon, lat, mx, my, mw, mh):
    x = mx + (lon + 180.0) / 360.0 * mw
    y = my + (LAT_TOP - lat) / (LAT_TOP - LAT_BOT) * mh
    return (x, y)


def draw_map(d, mx, my, mw, mh, items):
    d.rectangle([mx, my, mx + mw, my + mh], fill=(233, 236, 232),
                outline=INK, width=1)
    for poly in CONTINENTS.values():
        pts = [project(lon, lat, mx, my, mw, mh) for lon, lat in poly]
        d.polygon(pts, fill=TAN, outline=TAN_DARK)
    placed = []
    for item in items:
        if item["lat"] is None or item["lon"] is None:
            continue
        px, py = project(item["lon"], item["lat"], mx, my, mw, mh)
        ox, oy = 24, 0
        for dx, dy in PIN_OFFSETS:
            cx, cy = px + dx, py + dy
            if all((cx - qx) ** 2 + (cy - qy) ** 2 >= 17 ** 2
                   for qx, qy in placed):
                ox, oy = dx, dy
                break
        cx, cy = px + ox, py + oy
        if ox or oy:
            d.line([px, py, cx, cy], fill=INK, width=1)
            d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=RED)
        placed.append((cx, cy))
        r = 8
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED,
                  outline=(255, 255, 255), width=1)
        num = str(item["num"])
        fnt = load_font(SANS_B, 9)
        tw = d.textlength(num, font=fnt)
        d.text((cx - tw / 2, cy - 5.5), num, font=fnt, fill=(255, 255, 255))

# ---------------------------------------------------------------------------
# Layout: masthead, leads, cards, map + briefs, date check, footer
# ---------------------------------------------------------------------------

def tag_text(item):
    tag = item["region"] + " · " + item["field"] + " | " + item["label"]
    if item["source"]:
        tag += " · " + item["source"]
    return tag


def draw_badge(d, cx, cy, num, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
    fnt = load_font(SANS_B, 2 * r - 5)
    text = str(num)
    tw = d.textlength(text, font=fnt)
    d.text((cx - tw / 2, cy - r + 1.5), text, font=fnt, fill=(255, 255, 255))


def draw_masthead(d, data):
    kicker = data["kicker"].split("(")[0].strip()
    fnt_k = load_font(SANS_B, 13)
    draw_centered(d, W / 2, 16, kicker, fnt_k, RED)
    name = "THE WORLD IN ONE DAY"
    fnt_n = fit_size(d, name, SERIF_B, [48, 46, 44, 42], CONTENT_W)
    draw_centered(d, W / 2, 32, name, fnt_n, INK)
    d.line([MARGIN, 86, W - MARGIN, 86], fill=INK, width=2)
    fnt_c = load_font(SERIF_B, 17)
    draw_centered(d, W / 2, 92, data["counts"], fnt_c, RED)
    fnt_r = load_font(SANS, 11)
    draw_centered(d, W / 2, 112, data["region_strip"], fnt_r, INK)


def draw_numbers(d, data):
    d.line([MARGIN, 130, W - MARGIN, 130], fill=NAVY, width=2)
    label = "THE DAY IN NUMBERS"
    fnt_l = load_font(SANS_B, 11)
    d.text((MARGIN, 137), label, font=fnt_l, fill=NAVY)
    label_w = d.textlength(label + "  ", font=fnt_l)
    numbers = data["numbers"]
    fnt_n = fit_size(d, numbers, SERIF_B, [15, 14, 13, 12],
                     CONTENT_W - label_w)
    d.text((MARGIN + label_w, 136), numbers, font=fnt_n, fill=NAVY)
    d.line([MARGIN, 158, W - MARGIN, 158], fill=NAVY, width=2)


def lead_tag(d, item, fnt_t, width):
    full = tag_text(item)
    if d.textlength(full, font=fnt_t) <= width:
        return full
    return item["region"] + " · " + item["field"] + " | " + item["label"]


def draw_lead(d, item, x, y, w, h):
    draw_scene(d, (x, y, 138, h), LEAD_SCENES[item["num"]])
    tx = x + 146
    tw = w - 146
    draw_badge(d, tx + 9, y + 10, item["num"], 9)
    fnt_t = load_font(SANS_B, 10)
    tag = lead_tag(d, item, fnt_t, tw - 22)
    d.text((tx + 22, y + 4), tag, font=fnt_t, fill=RED)
    fnt_h = load_font(SERIF_B, 17)
    lines = fit_lines(d, item["headline"], fnt_h, tw, 2)
    hy = y + 22
    for line in lines:
        d.text((tx, hy), line, font=fnt_h, fill=INK)
        hy += 20
    fnt_s = load_font(SANS, 10)
    slines = fit_lines(d, item["summary"], fnt_s, tw, 3)
    sy = hy + 3
    for line in slines:
        d.text((tx, sy), line, font=fnt_s, fill=INK)
        sy += 13


def draw_leads(d, data):
    cell_w = (CONTENT_W - 10) // 2
    cell_h = 105
    for i, item in enumerate(data["leads"]):
        col = i % 2
        row = i // 2
        x = MARGIN + col * (cell_w + 10)
        y = 166 + row * (cell_h + 10)
        draw_lead(d, item, x, y, cell_w, cell_h)


def card_tag(d, item, fnt_t, width):
    region = item["region"]
    if region == "MIDDLE EAST":
        region = "MIDEAST"
    full = region + " · " + item["field"] + " | " + item["label"]
    if item["source"]:
        full += " · " + item["source"]
    if d.textlength(full, font=fnt_t) <= width:
        return full
    short = region + " · " + item["field"] + " | " + item["label"]
    return truncate(d, short, fnt_t, width)


def draw_card(d, item, x, y, w, h):
    draw_scene(d, (x, y, 56, h), CARD_SCENES[item["num"]])
    tx = x + 62
    tw = w - 62
    draw_badge(d, tx + 6, y + 7, item["num"], 6)
    fnt_t = load_font(SANS_B, 8)
    tag = card_tag(d, item, fnt_t, tw - 15)
    d.text((tx + 15, y + 4), tag, font=fnt_t, fill=RED)
    fnt_h = load_font(SERIF_B, 10)
    lines = fit_lines(d, item["summary"], fnt_h, tw, 5)
    hy = y + 18
    for line in lines:
        d.text((tx, hy), line, font=fnt_h, fill=INK)
        hy += 12


def draw_cards(d, data):
    cell_w = (CONTENT_W - 3 * 8) // 4
    cell_h = 80
    for i, item in enumerate(data["cards"]):
        col = i % 4
        row = i // 4
        x = MARGIN + col * (cell_w + 8)
        y = 394 + row * (cell_h + 8)
        draw_card(d, item, x, y, cell_w, cell_h)


def draw_map_briefs(d, data):
    fnt_h = load_font(SANS_B, 12)
    d.text((MARGIN, 658), "WHERE IT HAPPENED", font=fnt_h, fill=RED)
    d.text((430, 658), "ALSO ON FRIDAY 20 NOVEMBER", font=fnt_h, fill=RED)
    draw_map(d, MARGIN, 676, 400, 230, data["leads"] + data["cards"])
    col_w = 282
    row_h = 12.5
    fnt_n = load_font(SANS_B, 9)
    fnt_p = load_font(SANS_B, 9)
    fnt_t = load_font(SANS, 9)
    for i, brief in enumerate(data["briefs"]):
        col = i // 18
        row = i % 18
        bx = 430 + col * (col_w + 16)
        by = 676 + row * row_h
        num = str(brief["num"]) + ". "
        d.text((bx, by), num, font=fnt_n, fill=RED)
        nw = d.textlength(num, font=fnt_n)
        place = brief["place"] + ": "
        d.text((bx + nw, by), place, font=fnt_p, fill=INK)
        pw = d.textlength(place, font=fnt_p)
        rest = truncate(d, brief["text"], fnt_t, col_w - nw - pw)
        d.text((bx + nw + pw, by), rest, font=fnt_t, fill=INK)


def draw_datecheck(d, data):
    d.rectangle([MARGIN, 914, W - MARGIN, 970], fill=(250, 238, 234),
                outline=RED, width=1)
    fnt_t = load_font(SANS_B, 11)
    d.text((MARGIN + 8, 919), "DATE CHECK: STORIES WE LEFT OUT ON PURPOSE",
           font=fnt_t, fill=RED)
    fnt_b = load_font(SANS, 9)
    left = "LEFT OUT: " + " · ".join(
        item.split("(")[0].strip() for item in data["excluded"])
    right = "NOT YET: " + " · ".join(data["notyet"])
    y = 934
    for line in wrap_text(d, left, fnt_b, CONTENT_W - 16):
        d.text((MARGIN + 8, y), line, font=fnt_b, fill=INK)
        y += 11
    for line in wrap_text(d, right, fnt_b, CONTENT_W - 16):
        d.text((MARGIN + 8, y), line, font=fnt_b, fill=INK)
        y += 11


def draw_footer(d, data):
    fnt_s = load_font(SANS, 10)
    fnt_e = load_font(SERIF, 11)
    if len(data["footer"]) > 0:
        draw_centered(d, W / 2, 978, data["footer"][0], fnt_s, INK)
    if len(data["footer"]) > 1:
        draw_centered(d, W / 2, 992, data["footer"][1], fnt_e, INK)


def render(data):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=2)
    d.rectangle([6, 6, W - 7, H - 7], outline=INK, width=1)
    draw_masthead(d, data)
    draw_numbers(d, data)
    draw_leads(d, data)
    draw_cards(d, data)
    draw_map_briefs(d, data)
    draw_datecheck(d, data)
    draw_footer(d, data)
    return img


def main():
    data = parse_stories(REPO / "stories.md")
    counts = (len(data["leads"]), len(data["cards"]), len(data["briefs"]),
              len(data["excluded"]), len(data["notyet"]))
    print("parsed: leads=%d cards=%d briefs=%d excluded=%d notyet=%d" % counts)
    if counts != (4, 12, 36, 6, 2):
        raise SystemExit("unexpected story counts: %r" % (counts,))
    total = counts[0] + counts[1] + counts[2]
    print("total stories: %d" % total)
    img = render(data)
    out = REPO / "entry.png"
    img.save(out, format="PNG", optimize=True)
    raw = out.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    print("WROTE %s %d bytes sha256=%s" % (out, len(raw), digest))
    if len(raw) > 1048576:
        raise SystemExit("entry.png is over 1 MiB")
    if img.size != (1024, 1024):
        raise SystemExit("entry.png is not 1024x1024")


if __name__ == "__main__":
    main()
