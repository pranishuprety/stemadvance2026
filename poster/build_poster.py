"""
Rebuilds the Fall Research Day 2026 poster on the original Caldwell template:
keeps the header, logo, title and authors, and lays out cleaner content.
Run from the project root:  python poster/build_poster.py
"""
import glob
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

SRC = glob.glob(r"C:\Users\ASUS\Downloads\Copy of Fall Research Day 2026*.pptx")[0]
OUT = "poster/Fall_Research_Day_2026_Poster_Clean.pptx"
FONT = "Roboto"
DARK = RGBColor(0x1F, 0x29, 0x37)
TEXT = RGBColor(0x11, 0x18, 0x27)
BORDER = RGBColor(0x9C, 0xA3, 0xAF)
LIGHT = RGBColor(0xF3, 0xF4, 0xF6)
RED = RGBColor(0xC0, 0x39, 0x2B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BODY = 7.5

KEEP = {"84", "85", "86", "118", "119", "120", "185"}  # header, bg, title, authors, logo

prs = Presentation(SRC)
slide = prs.slides[0]
for sh in list(slide.shapes):
    if sh.name.split(";")[1] not in KEEP:
        sh._element.getparent().remove(sh._element)


def runs_from(text):
    """'**bold** rest' -> [(text, bold)]"""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, False) for p in parts if p]


def style_run(r, size, bold=False, color=TEXT, italic=False):
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color


def set_bullet(p, kind, level=0):
    pPr = p._p.get_or_add_pPr()
    mar = 0.13 + 0.14 * level
    pPr.set("marL", str(Inches(mar)))
    pPr.set("indent", str(-Inches(0.11)))
    if kind == "num":
        el = etree.SubElement(pPr, qn("a:buAutoNum"))
        el.set("type", "arabicPeriod")
    else:
        el = etree.SubElement(pPr, qn("a:buChar"))
        el.set("char", "•" if level == 0 else "–")


def textbox(x, y, w, h, items, size=BODY, gap=2.5, align=PP_ALIGN.LEFT):
    """items: str ('- ' bullet, '1. ' numbered, '  - ' sub-bullet) or plain text."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Inches(0.02))
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(gap)
        kind, level, text = None, 0, item
        if item.startswith("  - "):
            kind, level, text = "dot", 1, item[4:]
        elif item.startswith("- "):
            kind, text = "dot", item[2:]
        elif re.match(r"\d\. ", item):
            kind, text = "num", item[3:]
        for t, b in runs_from(text):
            r = p.add_run()
            r.text = t
            style_run(r, size, bold=b)
        if kind:
            set_bullet(p, kind, level)
    return tb


def panel(x, y, w, h, title):
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                 Inches(w), Inches(h))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = BORDER; box.line.width = Pt(0.75)
    box.shadow.inherit = False
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                 Inches(w), Inches(0.24))
    bar.fill.solid(); bar.fill.fore_color.rgb = DARK
    bar.line.fill.background(); bar.shadow.inherit = False
    tf = bar.text_frame
    tf.margin_left = Inches(0.08); tf.margin_top = tf.margin_bottom = Inches(0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    r = tf.paragraphs[0].add_run(); r.text = title
    style_run(r, 9.5, bold=True, color=WHITE)
    return x + 0.08, y + 0.30, w - 0.16


def caption(x, y, w, text):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.16))
    tf = tb.text_frame; tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Inches(0.0))
    p = tf.paragraphs[0]
    for t, b in runs_from(text):
        r = p.add_run(); r.text = t
        style_run(r, 6.5, bold=b, color=RGBColor(0x37, 0x41, 0x51))


def table(x, y, w, rows, col_w, bold_cells=(), size=6.5, row_h=0.17):
    gf = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y),
                                Inches(w), Inches(row_h * len(rows)))
    tbl = gf.table
    tbl.first_row = True
    tbl.horz_banding = False
    total = sum(col_w)
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(w * cw / total)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = DARK if i == 0 else (WHITE if i % 2 else LIGHT)
            c.margin_left = c.margin_right = Inches(0.03)
            c.margin_top = c.margin_bottom = Inches(0.01)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = c.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run(); r.text = val
            style_run(r, size, bold=(i == 0 or (i, j) in bold_cells),
                      color=WHITE if i == 0 else TEXT)
    return gf


def flow_box(x, y, w, h, text):
    b = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                               Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = RGBColor(0xF9, 0xFA, 0xFB)
    b.line.color.rgb = RGBColor(0xD1, 0xD5, 0xDB); b.line.width = Pt(0.75)
    b.shadow.inherit = False
    tf = b.text_frame; tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Inches(0.02))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text
    style_run(r, 6.5, bold=True)


def arrow(x, y, sym="→"):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(0.18), Inches(0.2))
    tf = tb.text_frame
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Inches(0))
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = sym
    style_run(r, 9, bold=True, color=RED)


TOP, BOTTOM = 1.22, 7.40
C1, W1 = 0.12, 3.90
C2, W2 = 4.12, 5.00
C3, W3 = 9.22, 4.00

# ---------------- Column 1 ----------------
x, y, w = panel(C1, TOP, W1, 1.32, "Research Questions")
textbox(x, y, w, 1.0, [
    "- **Measure:** How much did delays and cancellations rise at EWR, JFK and "
    "LGA during the 43-day 2025 federal shutdown?",
    "- **Explain:** Does the rise remain after accounting for weather?",
    "- **Forecast:** Could it have been predicted using only information "
    "known in advance?",
], size=8.2)

x, y, w = panel(C1, 2.62, W1, 2.22, "Background")
textbox(x, y, w, 1.9, [
    "- Each minute of delay costs U.S. airlines about **$100.76** (2024) [1].",
    "- Airports share aircraft, crews and airspace, so delays spread from one "
    "airport to others [2].",
    "- **2025 shutdown (Oct 1 to Nov 12):** air-traffic controllers worked "
    "unpaid; on Nov 7 the FAA began cutting flights at 40 airports [4].",
    "- A national study estimated about 1M extra delay hours (~$66M) [3].",
    "- Most delay models predict delays from past data; few measure the local "
    "impact of a specific real-world event.",
], size=8.2)

x, y, w = panel(C1, 4.92, W1, 2.48, "Data")
textbox(x, y, w, 1.65, [
    "- **Flights:** BTS on-time records [5], 8 Northeast airports",
    "  - Oct–Nov 2024 (normal): 160,383 flights",
    "  - Oct–Nov 2025 (shutdown): 149,426 flights",
    "  - Jan 2023 (NOTAM outage): 75,574 flights",
    "- **Weather:** hourly METAR wind, visibility and rain for EWR, JFK, LGA",
    "- **Panel:** average departure delay per airport per hour; cancelled "
    "flights analyzed separately",
], size=8.2, gap=1.5)
fy = 6.78
bw, aw = 0.80, 0.16
fx = x + 0.02
flow_box(fx, fy, bw, 0.36, "BTS flight records")
arrow(fx + bw, fy + 0.08, "+")
flow_box(fx + bw + aw, fy, bw, 0.36, "METAR weather")
arrow(fx + 2 * bw + aw, fy + 0.08)
flow_box(fx + 2 * bw + 2 * aw, fy, bw, 0.36, "Airport-hour panel")
arrow(fx + 3 * bw + 2 * aw, fy + 0.08)
flow_box(fx + 3 * bw + 3 * aw, fy, bw, 0.36, "4 analyses (Methods)")
caption(x, 7.18, w, "**Figure 1.** Data pipeline.")

# ---------------- Column 2 ----------------
x, y, w = panel(C2, TOP, W2, 1.70, "Methods")
textbox(x, y, w, 1.4, [
    "1. **Significance:** compare daily average delay, 2024 vs. 2025 (Welch "
    "t-test, bootstrap 95% CI).",
    "2. **Excess delay and cost:** three separate baselines (last year; an ML "
    "model of normal operations; the same model plus weather). Excess minutes "
    "× $100.76.",
    "3. **Forecast test:** the model sees only hour, weekday, scheduled flights "
    "and a shutdown flag (no past delays). Trained on Oct–Nov 2024 + Oct 2025, "
    "tested on unseen Nov 2025 against a normal-year average.",
    "4. **Airport coupling:** correlation between Newark's delay and JFK/LGA "
    "delay one hour later, in normal vs. disrupted periods.",
], size=7.8)

x, y, w = panel(C2, 3.00, W2, 4.40, "Results")
img_w = w
slide.shapes.add_picture("analysis/poster_fig_daily.png", Inches(x), Inches(y),
                         width=Inches(img_w))
img_h = img_w * 3.6 / 10
caption(x, y + img_h + 0.01, w,
        "**Figure 2.** Daily average departure delay, EWR + JFK + LGA combined.")
ty = y + img_h + 0.24
caption(x, ty, w, "**Table 1.** Delay (operated flights) and cancellations, "
        "Oct–Nov 2024 vs. 2025.")
table(x, ty + 0.17, w, [
    ["Airport", "Avg delay 2024", "Avg delay 2025", "Change", "p-value",
     "Cancelled after FAA order"],
    ["EWR", "13.2 min", "16.8 min", "+27%", "0.069 (n.s.)", "0.37% → 4.85%"],
    ["JFK", "7.6 min", "15.7 min", "+107%", "1.4×10⁻⁵", "0.01% → 3.34%"],
    ["LGA", "7.9 min", "19.8 min", "+149%", "7.3×10⁻⁶", "0.11% → 4.28%"],
], col_w=[0.7, 1, 1, 0.75, 1.0, 1.55], bold_cells={(2, 3), (3, 3)})
ty2 = ty + 0.17 + 4 * 0.17 + 0.10
caption(x, ty2, w, "**Table 2.** Excess delay attributed to the shutdown "
        "(Oct–Nov 2025, all three airports).")
table(x, ty2 + 0.17, w, [
    ["Baseline", "Excess delay (min)", "Cost at $100.76/min"],
    ["Prior year (2024)", "401,999", "$40.5M"],
    ["ML model of normal operations", "409,455", "$41.3M"],
    ["ML model + weather", "420,837", "$42.4M"],
], col_w=[2.2, 1.2, 1.2])

# ---------------- Column 3 ----------------
x, y, w = panel(C3, TOP, W3, 3.58, "Results (cont.)")
fig_w = 3.0
slide.shapes.add_picture("analysis/poster_fig_cost.png",
                         Inches(x + (w - fig_w) / 2), Inches(y),
                         width=Inches(fig_w))
fh = fig_w * 3.6 / 6.4
caption(x, y + fh + 0.01, w, "**Figure 3.** Delay cost by airport "
        "(prior-year baseline). Total excess ≈ $40.5M.")
ty = y + fh + 0.24
caption(x, ty, w, "**Table 3.** Forecast of unseen Nov 2025 (hourly). "
        "Higher R² and lower MAE are better.")
table(x, ty + 0.17, w, [
    ["Airport", "R² forecast", "R² normal-year", "MAE forecast",
     "MAE normal-year"],
    ["EWR", "0.23", "0.09", "12.4", "12.9"],
    ["JFK", "0.12", "−0.01", "9.5", "9.3"],
    ["LGA", "0.15", "−0.04", "15.2", "15.7"],
], col_w=[0.7, 1, 1.15, 1, 1.15],
    bold_cells={(1, 1), (2, 1), (3, 1), (1, 3), (3, 3), (2, 4)})
textbox(x, ty + 0.17 + 4 * 0.17 + 0.06, w, 0.4, [
    "- **Coupling:** Newark → JFK one-hour correlation: r = 0.19 in normal "
    "2024 vs. 0.55 in the shutdown and 0.57 in the Jan 2023 outage "
    "(correlation, not cause).",
], size=7)

x, y, w = panel(C3, 4.88, W3, 1.58, "Conclusions & Future Work")
textbox(x, y, w, 1.25, [
    "- Delays rose **+107% at JFK** and **+149% at LGA** (significant); "
    "EWR's +27% was not significant.",
    "- About **$41M** in excess airline delay cost; adding weather did not "
    "reduce the estimate.",
    "- A forecast using only advance information beat the normal-year baseline "
    "at all 3 airports, but accuracy is modest (R² 0.12–0.23).",
    "- **Limits:** departures only; one prior year as baseline; airline cost "
    "only, not passenger time.",
    "- **Next:** a network model to compare targeted vs. blanket flight cuts.",
], size=7, gap=1.5)

x, y, w = panel(C3, 6.54, W3, 0.86, "References")
textbox(x, y - 0.03, w, 0.6, [
    "[1] Airlines for America, “U.S. Passenger Carrier Delay Costs,” 2025.",
    "[2] P. Fleurquin et al., “Systemic delay propagation in the US airport "
    "network,” Sci. Rep., vol. 3, p. 1159, 2013.",
    "[3] R. T.-N. Wong, “The Value of Government Services: Evidence from Flight "
    "Delays During the 2025 Shutdown,” Richmond Fed Econ. Brief 25-45, 2025.",
    "[4] FAA, “Emergency Order Establishing Operating Limitations on the Use "
    "of Navigable Airspace,” Nov. 6, 2025.",
    "[5] BTS, “Reporting Carrier On-Time Performance (1987–present),” U.S. DOT.",
], size=5.3, gap=0)

prs.save(OUT)
print("saved", OUT)
