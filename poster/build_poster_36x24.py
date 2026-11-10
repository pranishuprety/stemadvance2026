"""
36 x 24 in Fall Research Day 2026 poster.
Run from the project root:  python poster/build_poster_36x24.py
(Graphs come from analysis/poster_graphs.py.)
"""
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree
from PIL import Image

import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "poster/Fall_Research_Day_2026_Poster_36x24.pptx"
REPO = "github.com/pranishuprety/stemadvance2026"

FONT = "Segoe UI"
HEADER = RGBColor(0x8B, 0x00, 0x00)
BG = RGBColor(0xF3, 0xF4, 0xF6)
SLATE = RGBColor(0x1F, 0x29, 0x37)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER = RGBColor(0x9C, 0xA3, 0xAF)
TEXT = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x4B, 0x55, 0x63)
RED = RGBColor(0xA3, 0x11, 0x1A)
LIGHT = RGBColor(0xE5, 0xE7, 0xEB)

BODY = 29
BAR = 0.9
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(36), Inches(24)
slide = prs.slides.add_slide(prs.slide_layouts[6])


def rect(x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, lw=1.5):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(lw)
    s.shadow.inherit = False
    return s


def runs_from(t):
    parts = re.split(r"(\*\*.+?\*\*)", t)
    return [(p[2:-2], True) if p.startswith("**") else (p, False)
            for p in parts if p]


def fmt(r, size, bold=False, color=TEXT, italic=False):
    r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold
    r.font.italic = italic; r.font.color.rgb = color


def frame(obj, margin=0.03):
    tf = obj.text_frame; tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Inches(margin))
    return tf


def write(tf, items, size=BODY, gap=8, color=TEXT, align=PP_ALIGN.LEFT,
          bold_color=None, bold_all=False):
    """items: '- ' bullet, otherwise plain paragraph; **x** marks bold."""
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(gap)
        bullet = item.startswith("- ")
        for t, b in runs_from(item[2:] if bullet else item):
            r = p.add_run(); r.text = t
            fmt(r, size, b or bold_all, (bold_color or color) if b else color)
        if bullet:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(Inches(0.4))); pPr.set("indent", str(-Inches(0.34)))
            etree.SubElement(pPr, qn("a:buClr")).append(
                etree.fromstring(f'<a:srgbClr xmlns:a="http://schemas.openxmlformats.org/'
                                 f'drawingml/2006/main" val="{SLATE}"/>'))
            etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
            etree.SubElement(pPr, qn("a:buChar")).set("char", "■")
    return tf


def text(x, y, w, h, items, anchor=MSO_ANCHOR.TOP, **kw):
    tf = frame(slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)))
    tf.vertical_anchor = anchor
    return write(tf, items, **kw)


def label(shape, items, size, color=WHITE, align=PP_ALIGN.CENTER, margin=0.08,
          anchor=MSO_ANCHOR.MIDDLE, bold_all=True, gap=0):
    tf = frame(shape, margin); tf.vertical_anchor = anchor
    write(tf, items, size=size, color=color, align=align, bold_all=bold_all, gap=gap)


def panel(x, y, w, h, title):
    rect(x, y, w, h, WHITE, BORDER)
    bar = rect(x, y, w, BAR, SLATE)
    rect(x, y, 0.2, BAR, RED)
    label(bar, [title], 34, align=PP_ALIGN.LEFT, margin=0.4)
    return x + 0.3, y + BAR + 0.2, w - 0.6


def headline(x, y, w, msg, size=31, h=0.6):
    text(x, y, w, h, [msg], size=size, color=RED, bold_all=True, gap=0)


def caption(x, y, w, msg, size=21):
    text(x, y, w, 0.4, [msg], size=size, color=MUTED, align=PP_ALIGN.CENTER, gap=0)
    for r in slide.shapes[-1].text_frame.paragraphs[0].runs:
        r.font.italic = True


def picture(path, x, y, w=None, h=None):
    W, H = Image.open(path).size
    if w is None:
        w = h * W / H
    slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))
    return w * H / W


def arrow(x1, y1, x2, y2, color=SLATE, width=3.5, head=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(width)
    if head:
        ln = c.line._get_or_add_ln()
        e = etree.SubElement(ln, qn("a:tailEnd"))
        e.set("type", "triangle"); e.set("w", "med"); e.set("len", "med")


def stats(x, y, w, pairs, num_size=58, label_size=19):
    cw = w / len(pairs)
    for i, (num, lab, col) in enumerate(pairs):
        tf = frame(slide.shapes.add_textbox(Inches(x + i * cw), Inches(y),
                                            Inches(cw), Inches(1.6)))
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = num; fmt(r, num_size, True, col)
        p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = lab; fmt(r2, label_size, False, MUTED)



# ---------------- background and header ----------------
rect(0, 0, 36, 24, BG)
rect(0, 0, 36, 3.25, HEADER)
rect(0, 3.25, 36, 0.1, SLATE)
picture("poster/caldwell_logo.png", 0.7, 0.95, w=6.4)
tf = frame(slide.shapes.add_textbox(Inches(7.6), Inches(0.15), Inches(27.6),
                                    Inches(3.0)))
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
for i, (t, s, b, after) in enumerate([
        ("Quantifying and Forecasting the Impact of the 2025 U.S. Government "
         "Shutdown on New York–Metro Flight Delays", 56, True, 8),
        ("Pranish Uprety   |   Advisor: Dr. Sushil Poudel   |   "
         "Department of Computer Science, Caldwell University", 30, False, 0)]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.alignment = PP_ALIGN.CENTER; p.space_after = Pt(after)
    r = p.add_run(); r.text = t; fmt(r, s, b, WHITE)

M, G = 0.6, 0.45
LSIDE, SIDE = 6.6, 7.6
CENTER = 36 - 2 * M - 2 * G - LSIDE - SIDE
XL, XC, XR = M, M + LSIDE + G, M + LSIDE + G + CENTER + G
TOP, BOT = 3.8, 23.4

# ---------------- left column ----------------
h = 5.4
x, y, w = panel(XL, TOP, LSIDE, h, "Objective")
text(x, y - 0.05, w, 1.0, [
    "Measure how the 2025 shutdown affected New York–Metro air travel:"],
    size=25, gap=0, color=MUTED)
for i, v in enumerate(["**Quantify** the change in delays and cancellations",
                       "**Test** whether weather explains the change",
                       "**Forecast** delays from information known in advance"]):
    yy = y + 1.05 + i * 1.0
    num = rect(x, yy + 0.1, 0.58, 0.58, SLATE)
    label(num, [str(i + 1)], 24, margin=0)
    text(x + 0.8, yy, w - 0.8, 0.85, [v], size=25, gap=0, bold_color=TEXT,
         anchor=MSO_ANCHOR.MIDDLE)

y0 = TOP + h + G
h = BOT - y0
x, y, w = panel(XL, y0, LSIDE, h, "Background")
stats(x, y - 0.05, w, [("43", "shutdown days", RED), ("40", "airports cut", RED),
                       ("3", "airports studied", RED)], num_size=56, label_size=19)


def subhead(yy, t):
    text(x, yy, w, 0.5, [t.upper()], size=19, color=MUTED, bold_all=True, gap=0)
    rect(x, yy + 0.5, w, 0.03, BORDER)


yy = y + 1.75
subhead(yy, "What happened")
text(x, yy + 0.62, w, 1.6, [
    "- Longest U.S. shutdown on record",
    "- Air-traffic controllers worked **without pay**; staffing shortages grew",
], size=24, gap=5, bold_color=TEXT)

ty = yy + 3.4
rect(x + 0.2, ty, w - 0.4, 0.22, LIGHT)
rect(x + 0.2, ty, (w - 0.4) * 42 / 61, 0.22, RED)
for frac, day, what, above in [(0, "Oct 1", "Shutdown\nbegins", False),
                               (37 / 61, "Nov 7", "FAA cuts flights [3]", True),
                               (42 / 61, "Nov 12", "Shutdown\nends", False)]:
    cx = x + 0.2 + (w - 0.4) * frac
    rect(cx - 0.2, ty - 0.09, 0.4, 0.4, WHITE, RED, MSO_SHAPE.OVAL, lw=4)
    if above:
        text(cx - 1.8, ty - 0.95, 3.6, 0.8, [f"**{day}**", what], size=20, gap=0,
             color=MUTED, bold_color=TEXT, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.BOTTOM)
    else:
        bx = cx - 0.2 if frac == 0 else cx - 0.6
        text(bx, ty + 0.4, 2.0, 1.2, [f"**{day}**", what], size=20, gap=0,
             color=MUTED, bold_color=TEXT)

yy = ty + 1.7
subhead(yy, "Why it matters")
text(x, yy + 0.62, w, 2.6, [
    "- NY has the most congested U.S. airspace",
    "- Delay costs airlines **$100.76 per minute** [1]",
    "- Delays spread between airports [2]",
], size=24, gap=5, bold_color=TEXT)

gy = y0 + h - 1.75
gap_box = rect(x, gy, w, 1.45, LIGHT)
rect(x, gy, 0.12, 1.45, RED)
text(x + 0.3, gy, w - 0.45, 1.45, [
    "**Research gap:** no data-driven estimate of the shutdown's effect "
    "on New York–Metro flights"], size=22, gap=0, bold_color=TEXT,
    anchor=MSO_ANCHOR.MIDDLE)

# ---------------- center: methodology block diagram ----------------
MH = 7.35
x, y, w = panel(XC, TOP, CENTER, MH, "Methodology")


def block(bx, by, bw, bh, lines, fill=WHITE, line=SLATE, color=TEXT,
          sub_color=MUTED, size=26, sub=22, align=PP_ALIGN.CENTER,
          anchor=MSO_ANCHOR.MIDDLE):
    b = rect(bx, by, bw, bh, fill, line, lw=1.75)
    tf = frame(b, 0.12); tf.vertical_anchor = anchor
    for i, t in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = t
        fmt(r, size if i == 0 else sub, i == 0, color if i == 0 else sub_color)
    return b


A = 0.6
cols = [3.2, 3.6, 2.7, 4.3, 2.9]
cx_ = [x]
for c in cols[:-1]:
    cx_.append(cx_[-1] + c + A)
by, bh = y + 0.6, MH - BAR - 0.2 - 0.6 - 0.3
mid = by + bh / 2
for i, name in enumerate(["DATA", "PREPROCESSING", "PANEL", "ANALYSIS", "RESULT"]):
    text(cx_[i], y + 0.02, cols[i], 0.45, [f"{i + 1}   {name}"], size=20,
         color=MUTED, align=PP_ALIGN.CENTER, bold_all=True, gap=0)
    rect(cx_[i], y + 0.47, cols[i], 0.03, BORDER)

dh = (bh - 0.6) / 2
for i, lines in enumerate([["BTS On-Time", "310K flights", "8 airports"],
                           ["METAR Weather", "hourly reports", "wind, visibility"]]):
    dy = by + i * (dh + 0.6)
    block(cx_[0], dy, cols[0], dh, lines)
    arrow(cx_[0] + cols[0], dy + dh / 2, cx_[1] - 0.02, dy + dh / 2)

rect(cx_[1], by, cols[1], bh, WHITE, SLATE, lw=1.75)
text(cx_[1] + 0.15, by + 0.15, cols[1] - 0.3, bh - 0.3, [
    "- Keep EWR, JFK, LGA + 5 corridor airports",
    "- Remove cancelled flights",
    "- Average delay per airport-hour",
    "- Join hourly weather",
], size=23, gap=12, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)

arrow(cx_[1] + cols[1], mid, cx_[2] - 0.02, mid)
block(cx_[2], mid - 1.4, cols[2], 2.8,
      ["Airport-hour panel", "Oct–Nov", "2024 and 2025"],
      fill=SLATE, line=SLATE, color=WHITE, sub_color=RGBColor(0xD1, 0xD5, 0xDB))

ah, ag = (bh - 3 * 0.2) / 4, 0.2
bus = cx_[2] + cols[2] + A / 2
arrow(cx_[2] + cols[2], mid, bus, mid, head=False)
arrow(bus, by + ah / 2, bus, by + 3 * (ah + ag) + ah / 2, head=False)
steps = [("Significance", "Welch t-test, 2024 vs. 2025", "p < 0.001"),
         ("Extra cost", "3 baselines × $100.76/min", "≈ $41M"),
         ("Forecast", "calendar + schedule + flag", "R² up to 0.23"),
         ("Coupling", "lead–lag correlation", "r 0.19 → 0.55")]
for i, (name, how, out) in enumerate(steps):
    ay = by + i * (ah + ag)
    arrow(bus, ay + ah / 2, cx_[3] - 0.02, ay + ah / 2)
    block(cx_[3], ay, cols[3], ah, [name, how], size=26, sub=21,
          align=PP_ALIGN.LEFT)
    arrow(cx_[3] + cols[3], ay + ah / 2, cx_[4] - 0.02, ay + ah / 2)
    block(cx_[4], ay, cols[4], ah, [out], fill=LIGHT, line=BORDER, color=RED,
          size=27)

# ---------------- center: 2 x 2 results ----------------
CW = (CENTER - G) / 2
RY = TOP + MH + G
RH = (BOT - RY - G) / 2
cells = [
    ("Result 1: Delays Over Time", "analysis/poster_g_timeline.png",
     "Delays spiked during the shutdown",
     "Daily average departure delay, EWR + JFK + LGA"),
    ("Result 2: By Airport", "analysis/poster_g_airports.png",
     "JFK and LGA delays more than doubled",
     "JFK, LGA: p < 0.001 · EWR: p = 0.07 (n.s.)"),
    ("Result 3: Extra Delay Cost", "analysis/poster_g_cost.png",
     "≈ $41M extra, not explained by weather",
     "Cost at $100.76 per delay minute [1]"),
    ("Result 4: Forecast", "analysis/poster_g_forecast.png",
     "Our forecast beat the normal-year baseline",
     "R², forecast vs. baseline: EWR .23/.09 · JFK .12/−.01 · LGA .15/−.04"),
]
for k, (title, img, msg, cap) in enumerate(cells):
    cx = XC + (k % 2) * (CW + G)
    cy = RY + (k // 2) * (RH + G)
    x, y, w = panel(cx, cy, CW, RH, title)
    headline(x, y - 0.08, w, msg)
    fh_ = RH - BAR - 0.2 - 0.55 - 0.5
    iw = Image.open(img).size
    fw = min(w, fh_ * iw[0] / iw[1])
    picture(img, x + (w - fw) / 2, y + 0.5, w=fw)
    caption(x, cy + RH - 0.52, w, cap, size=20)

# ---------------- right column ----------------
h = 7.0
x, y, w = panel(XR, TOP, SIDE, h, "Result 5: Coupling")
headline(x, y - 0.08, w, "Under stress, Newark's delays moved with JFK and LGA",
         size=26, h=1.0)
fw = w
picture("analysis/poster_g_coupling.png", x + (w - fw) / 2, y + 0.95, w=fw)
caption(x, TOP + h - 0.52, w, "1-hour lagged correlation (does not imply causation)",
        size=20)

y0 = TOP + h + G
h = 5.7
x, y, w = panel(XR, y0, SIDE, h, "Conclusions")
text(x, y, w, h - BAR - 1.9, [
    "- **JFK +107%, LGA +149%**; EWR +27% not significant",
    "- **≈ $41M** extra cost, not from weather",
    "- Partly **predictable** from public data",
    "- Airports **more linked** under stress",
], size=27, gap=6, bold_color=RED)
rect(x, y0 + h - 1.7, w, 0.03, BORDER)
text(x, y0 + h - 1.6, w, 1.5, [
    "**Limits:** departures only; one prior year",
    "**Next:** targeted vs. blanket flight cuts",
], size=22, gap=4, color=MUTED, bold_color=TEXT)

y0 += h + G
h = 2.85
x, y, w = panel(XR, y0, SIDE, h, "References")
text(x, y - 0.12, w, h - BAR - 0.1, [
    "[1] Airlines for America, Delay Costs, 2025.",
    "[2] Fleurquin et al., Sci. Reports 3:1159, 2013.",
    "[3] FAA Emergency Order, Nov. 6, 2025.",
    "[4] BTS, On-Time Performance data.",
    "[5] Iowa Environmental Mesonet, ASOS/METAR.",
], size=18, gap=1, color=MUTED)

y0 += h + G
h = BOT - y0
rect(XR, y0, SIDE, h, SLATE)
rect(XR, y0, 0.2, h, RED)
qs = h - 0.5
rect(XR + 0.4, y0 + 0.25, qs, qs, WHITE)
picture("poster/repo_qr.png", XR + 0.45, y0 + 0.3, w=qs - 0.1)
tx = XR + 0.4 + qs + 0.3
text(tx, y0 + 0.2, XR + SIDE - tx - 0.15, qs + 0.1, [
    "**Research Repository**", "Code, data & figures", REPO,
], size=19, color=WHITE, bold_color=WHITE, gap=3, anchor=MSO_ANCHOR.MIDDLE)
tf = slide.shapes[-1].text_frame
tf.paragraphs[0].runs[0].font.size = Pt(27)
tf.paragraphs[2].runs[0].font.size = Pt(15)
tf.paragraphs[2].runs[0].font.color.rgb = RGBColor(0xD1, 0xD5, 0xDB)

prs.save(OUT)
print("saved", OUT)
