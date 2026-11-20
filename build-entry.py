#!/usr/bin/env python3
"""Build entry.png: a one-page newspaper front page summing up the world news
of Friday 20 November 2026.

Drawn from scratch with Pillow (local build tool only). The submitted program
is main.ts, which simply copies the finished entry.png to the output dir, so
the graded runs are byte-identical and need no network.

Stories (all reported on 20 Nov 2026, cross-checked across several news
round-ups of the day — OneTurn's 20 Nov day page, Morning Briefing #222,
Bangladesh Chronicle's 20 Nov briefing):
  LEAD. Houthi missile damages Riyadh's tallest tower — the Public
    Investment Fund tower in the financial district; Saudi air defences
    intercept a second missile and five drones.
  MARKETS. Nikkei -4.8%, S&P 500 -2% for a fifth straight session as
    AI-bubble fears spread; Anthropic closes +17% at ~$97 on its Nasdaq
    debut (offer $83, ticker ANT).
  UKRAINE. Russia's overnight strike on Kyiv; the EU will summon Moscow's
    envoy over damage to its embassy; the UK pledges 1,000+ drones (£260m).
  CULTURE. GTA 6 launch tops $2.3bn in sales — the biggest entertainment
    launch ever.
  Also today: the ICJ's Rohingya genocide ruling (9-6) reverberates; the
    IMF warns global public debt nears 100% of GDP; Italy fines Meta
    EUR 805m over Android photo access; an FAA ground stop strands 1.5m
    travellers; Kenya discharges its last Ebola patient; the US Senate
    rejects the Iran war-powers resolution 51-48.
"""

import math
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

PAPER = (250, 246, 236)
INK = (26, 26, 26)
NAVY = (16, 35, 61)
NAVY_MID = (28, 58, 96)
RED = (179, 39, 30)
RED_DARK = (140, 28, 22)
GOLD = (232, 197, 71)
GREY = (90, 88, 82)
GREY_LIGHT = (150, 146, 136)
CARD = (255, 255, 255)
BORDER = (200, 192, 172)
GREEN = (31, 122, 74)
TEAL = (14, 110, 110)
PURPLE = (96, 58, 120)
ORANGE = (198, 102, 16)

SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, xy, text, fnt, max_w, fill, spacing=4, max_lines=None):
    x, y = xy
    lines = wrap(draw, text, fnt, max_w)
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y


# ---------------------------------------------------------------- icons
def icon_chart_down(d, box, fg):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    # falling line with arrowhead
    pts = [(x0 + 2, y0 + h * 0.18), (x0 + w * 0.38, y0 + h * 0.42),
           (x0 + w * 0.58, y0 + h * 0.34), (x1 - 2, y0 + h * 0.82)]
    d.line(pts, fill=fg, width=4, joint="curve")
    ax, ay = x1 - 2, y0 + h * 0.82
    d.polygon([(ax, ay), (ax - 12, ay - 2), (ax - 2, ay - 12)], fill=fg)
    d.line([x0 + 2, y1 - 3, x1 - 2, y1 - 3], fill=fg, width=3)


def icon_rocket(d, box, fg):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    w, h = x1 - x0, y1 - y0
    # body
    d.polygon([(cx, y0 + 1), (cx + w * 0.28, y0 + h * 0.45),
               (cx + w * 0.28, y0 + h * 0.72), (cx, y0 + h * 0.62),
               (cx - w * 0.28, y0 + h * 0.72), (cx - w * 0.28, y0 + h * 0.45)],
              fill=fg)
    # window
    d.ellipse([cx - 5, y0 + h * 0.30, cx + 5, y0 + h * 0.44], fill=PAPER)
    # fins
    d.polygon([(cx - w * 0.28, y0 + h * 0.62), (cx - w * 0.46, y1 - 2),
               (cx - w * 0.14, y0 + h * 0.78)], fill=fg)
    d.polygon([(cx + w * 0.28, y0 + h * 0.62), (cx + w * 0.46, y1 - 2),
               (cx + w * 0.14, y0 + h * 0.78)], fill=fg)
    # flame
    d.polygon([(cx - 5, y0 + h * 0.72), (cx + 5, y0 + h * 0.72),
               (cx, y1 - 1)], fill=fg)


def icon_warning(d, box, fg):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    h = y1 - y0
    d.polygon([(cx, y0 + 1), (x1 - 1, y1 - 2), (x0 + 1, y1 - 2)],
              outline=fg, width=3)
    d.rectangle([cx - 2, y0 + h * 0.42, cx + 2, y0 + h * 0.66], fill=fg)
    d.ellipse([cx - 2, y0 + h * 0.74, cx + 2, y0 + h * 0.86], fill=fg)


def icon_star(d, box, fg):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    r_out, r_in = min(x1 - x0, y1 - y0) // 2 - 1, 0
    r_in = r_out * 0.42
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    d.polygon(pts, fill=fg)


ICONS = {
    "chart_down": icon_chart_down,
    "rocket": icon_rocket,
    "warning": icon_warning,
    "star": icon_star,
}

# ---------------------------------------------------------------- content
LEAD = {
    "kicker": "MIDDLE EAST  ·  RIYADH",
    "headline": "Houthi missile hits Riyadh's tallest tower",
    "summary": ("Blast damages the sovereign wealth fund tower in the "
                "financial district; Saudi defences intercept a second "
                "missile and five drones."),
}

MARKETS = [
    ("NIKKEI", "-4.8%", RED),
    ("S&P 500", "-2.0% · 5TH DAY DOWN", RED),
    ("ANTHROPIC", "+17% · $97 DEBUT", GREEN),
]

CARDS = [
    {
        "kicker": "MARKETS",
        "headline": "Asia leads a global sell-off",
        "summary": ("Japan's Nikkei drops 4.8% as AI-bubble fears spread; "
                    "Wall Street falls for a fifth straight session."),
        "icon": "chart_down",
        "color": RED,
    },
    {
        "kicker": "TECH",
        "headline": "Anthropic jumps 17% on debut",
        "summary": ("Shares close near $97, above the $83 offer, on the "
                    "Nasdaq under ticker ANT."),
        "icon": "rocket",
        "color": TEAL,
    },
    {
        "kicker": "UKRAINE",
        "headline": "Russia strikes Kyiv overnight",
        "summary": ("Blasts hit the capital; the EU will summon Moscow's "
                    "envoy over damage to its embassy in the attack."),
        "icon": "warning",
        "color": NAVY_MID,
    },
    {
        "kicker": "ENTERTAINMENT",
        "headline": "GTA 6 launch tops $2.3bn",
        "summary": ("Rockstar's sequel posts the biggest entertainment "
                    "launch ever, smashing sales records in its first days."),
        "icon": "star",
        "color": PURPLE,
    },
]

ALSO = [
    "ICJ's Rohingya genocide ruling reverberates",
    "IMF: global public debt nears 100% of GDP",
    "Italy fines Meta \u20ac805m over photo access",
    "FAA ground stop strands 1.5m travellers",
    "Kenya discharges its last Ebola patient",
    "US Senate rejects Iran war-powers bid, 51\u201348",
]

# ---------------------------------------------------------------- canvas
img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)

# --- breaking bar
d.rectangle([0, 0, W, 44], fill=RED)
d.ellipse([20, 15, 32, 27], fill=(255, 255, 255))
d.text((40, 10), "BREAKING NEWS", font=font(SANS_B, 22), fill=(255, 255, 255))
d.text((W - 20, 10), "FRIDAY, 20 NOVEMBER 2026",
       font=font(SANS_B, 22), fill=(255, 255, 255), anchor="ra")

# --- masthead
d.text((W // 2, 58), "THE WORLD IN ONE DAY",
       font=font(SERIF_B, 52), fill=NAVY, anchor="ma")
d.text((W // 2, 118), "ONE IMAGE  ·  EVERY STORY THAT MATTERED",
       font=font(SANS_B, 19), fill=GREY, anchor="ma")
d.rectangle([20, 148, W - 20, 152], fill=RED)
d.rectangle([20, 154, W - 20, 156], fill=NAVY)

# --- lead story card
lx, ly, lw, lh = 20, 170, 984, 260
d.rectangle([lx, ly, lx + lw, ly + lh], fill=CARD, outline=BORDER, width=2)
d.rectangle([lx, ly, lx + 8, ly + lh], fill=RED)

# lead illustration: night skyline panel with a missile streak
px0, py0, px1, py1 = lx + 22, ly + 20, lx + 352, ly + lh - 20
d.rectangle([px0, py0, px1, py1], fill=NAVY)
# stars
for sx, sy in [(px0 + 30, py0 + 22), (px0 + 120, py0 + 14), (px0 + 210, py0 + 30),
               (px0 + 280, py0 + 16), (px0 + 70, py0 + 55), (px0 + 250, py0 + 62)]:
    d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=GOLD)
# buildings (dark silhouettes with lit windows)
buildings = [(0, 150, 46, 220), (50, 110, 92, 220), (96, 170, 130, 220),
             (134, 70, 176, 220), (180, 130, 224, 220), (228, 95, 268, 220),
             (272, 160, 308, 220)]
for bx0, bh, bx1, by1 in buildings:
    x0b, x1b = px0 + bx0, px0 + bx1
    y1b = py1
    y0b = py1 - (220 - bh)
    d.rectangle([x0b, y0b, x1b, y1b], fill=(10, 24, 44))
    for wy in range(y0b + 12, y1b - 8, 18):
        for wx in range(x0b + 6, x1b - 6, 14):
            if (wx + wy) % 3 == 0:
                d.rectangle([wx, wy, wx + 4, wy + 5], fill=GOLD)
# tallest tower (twisted PIF tower): tapered, leaning slightly
tx0, tx1 = px0 + 134, px0 + 176
d.polygon([(tx0 + 6, py1 - 150), (tx1 - 6, py1 - 150),
           (tx1 - 14, py0 + 26), (tx0 + 14, py0 + 26)], fill=(24, 48, 84))
d.polygon([(tx0 + 14, py0 + 26), (tx1 - 14, py0 + 26),
           (tx1 - 18, py0 + 8), (tx0 + 18, py0 + 8)], fill=(36, 68, 110))
# missile streak: bright diagonal with glow + impact flash on the tower
d.line([px0 + 300, py0 + 30, px0 + 168, py0 + 96], fill=(255, 170, 60), width=5)
d.line([px0 + 300, py0 + 30, px0 + 168, py0 + 96], fill=(255, 240, 200), width=2)
d.ellipse([px0 + 152, py0 + 80, px0 + 184, py0 + 112], fill=(255, 200, 90))
d.ellipse([px0 + 160, py0 + 88, px0 + 176, py0 + 104], fill=(255, 255, 255))
# smoke puffs
for sx, sy, sr in [(px0 + 140, py0 + 78, 9), (px0 + 128, py0 + 66, 7),
                   (px0 + 196, py0 + 84, 8)]:
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(120, 120, 120))
d.text((px0 + 8, py1 - 26), "RIYADH, SAUDI ARABIA",
       font=font(SANS_B, 15), fill=(255, 255, 255))

# lead text
tx = lx + 392
d.text((tx, ly + 24), LEAD["kicker"], font=font(SANS_B, 21), fill=RED)
y = draw_wrapped(d, (tx, ly + 56), LEAD["headline"], font(SERIF_B, 42),
                 lw - 412, INK, spacing=2, max_lines=3)
draw_wrapped(d, (tx, y + 14), LEAD["summary"], font(SANS, 23),
             lw - 412, GREY, spacing=5, max_lines=3)

# --- markets strip
mx, my, mw, mh = 20, 442, 984, 60
d.rectangle([mx, my, mx + mw, my + mh], fill=NAVY)
seg_w = mw // 3
for i, (label, value, color) in enumerate(MARKETS):
    cx = mx + i * seg_w + seg_w // 2
    d.text((cx, my + 8), label, font=font(SANS_B, 17), fill=GOLD, anchor="ma")
    d.text((cx, my + 30), value, font=font(SANS_B, 24), fill=color if color != GREEN else (110, 220, 150), anchor="ma")
    if i:
        d.line([mx + i * seg_w, my + 10, mx + i * seg_w, my + mh - 10],
               fill=(60, 80, 110), width=2)

# --- story grid 2x2
CW, CH, GAP = 486, 180, 12
for i, s in enumerate(CARDS):
    row, col = divmod(i, 2)
    x = 20 + col * (CW + GAP)
    y0 = 514 + row * (CH + 12)
    d.rectangle([x, y0, x + CW, y0 + CH], fill=CARD, outline=BORDER, width=2)
    d.rectangle([x, y0, x + CW, y0 + 6], fill=s["color"])
    pad = 16
    ix, iy, ir = x + pad + 22, y0 + 16 + 22, 22
    d.ellipse([ix - ir, iy - ir, ix + ir, iy + ir], fill=s["color"])
    ICONS[s["icon"]](d, (ix - 15, iy - 15, ix + 15, iy + 15),
                     (255, 255, 255))
    d.text((x + pad + 54, y0 + 30), s["kicker"], font=font(SANS_B, 19),
           fill=s["color"])
    y = draw_wrapped(d, (x + pad, y0 + 66), s["headline"], font(SERIF_B, 27),
                     CW - 2 * pad, INK, spacing=2, max_lines=2)
    draw_wrapped(d, (x + pad, y + 8), s["summary"], font(SANS, 19),
                 CW - 2 * pad, GREY, spacing=4, max_lines=3)

# --- also today
ax, ay, aw, ah = 20, 898, 984, 102
d.rectangle([ax, ay, ax + aw, ay + ah], fill=(238, 232, 218), outline=BORDER, width=2)
d.text((ax + 16, ay + 10), "ALSO TODAY", font=font(SANS_B, 19), fill=RED)
col_w = (aw - 32) // 2
for i, item in enumerate(ALSO):
    col, row = divmod(i, 3)
    x = ax + 16 + col * col_w
    y = ay + 38 + row * 20
    d.ellipse([x, y + 5, x + 6, y + 11], fill=RED)
    d.text((x + 12, y), item, font=font(SANS, 17), fill=INK)

img.save(OUT)
print("saved", OUT, img.size)
