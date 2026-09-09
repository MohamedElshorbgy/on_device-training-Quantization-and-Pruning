"""
Machine Learning & Deep Learning - The Complete Guide (Beginner to Expert)
=========================================================================
Generates a single, detailed, self-contained PDF textbook.

Usage:
    pip install reportlab
    python gen_ml_dl_guide_pdf.py

Output:
    Machine_Learning_and_Deep_Learning_Complete_Guide.pdf
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, ListFlowable, ListItem,
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "Machine_Learning_and_Deep_Learning_Complete_Guide.pdf")

# Running headers/footers - overridable when this engine is reused for another
# document (see gen_rigl_implementation_pdf.py).
HEADER_TEXT = "Machine Learning & Deep Learning - The Complete Guide"
FOOTER_TEXT = "Beginner to Expert"

PAGE_W, PAGE_H = A4
MARGIN_L = MARGIN_R = 20 * mm
MARGIN_T = 18 * mm
MARGIN_B = 18 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R          # ~170 mm

# ---------------------------------------------------------------- palette ----
C_DARK    = colors.HexColor("#1a3a5c")
C_MID     = colors.HexColor("#2962a8")
C_LIGHT   = colors.HexColor("#ddeeff")
C_ACCENT  = colors.HexColor("#00695c")
C_CODE_BG = colors.HexColor("#f5f6f8")
C_CODE_BD = colors.HexColor("#c8ccd4")
C_GREEN_BG, C_GREEN_BD   = colors.HexColor("#e8f5e9"), colors.HexColor("#2e7d32")
C_ORANGE_BG, C_ORANGE_BD = colors.HexColor("#fff3e0"), colors.HexColor("#e65100")
C_PURPLE_BG, C_PURPLE_BD = colors.HexColor("#f3e5f5"), colors.HexColor("#7b1fa2")
C_TEAL_BG, C_TEAL_BD     = colors.HexColor("#e0f7fa"), colors.HexColor("#00695c")
C_YELLOW_BG, C_YELLOW_BD = colors.HexColor("#fffde7"), colors.HexColor("#f57f17")
C_RED_BG, C_RED_BD       = colors.HexColor("#ffebee"), colors.HexColor("#c62828")
C_BLUE_BG, C_BLUE_BD     = colors.HexColor("#e3f2fd"), colors.HexColor("#1565c0")
C_GREY    = colors.HexColor("#555555")
C_LGREY   = colors.HexColor("#eceff1")

BOX_KINDS = {
    "key":     (C_BLUE_BG,   C_BLUE_BD,   "KEY IDEA"),
    "math":    (C_PURPLE_BG, C_PURPLE_BD, "MATH"),
    "tip":     (C_GREEN_BG,  C_GREEN_BD,  "PRACTICAL TIP"),
    "warn":    (C_RED_BG,    C_RED_BD,    "PITFALL"),
    "note":    (C_YELLOW_BG, C_YELLOW_BD, "NOTE"),
    "intuit":  (C_TEAL_BG,   C_TEAL_BD,   "INTUITION"),
    "expert":  (C_ORANGE_BG, C_ORANGE_BD, "EXPERT CORNER"),
}

# ----------------------------------------------------------------- styles ----
def _ps(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)

S_TITLE    = _ps("TITLE", fontSize=30, leading=36, textColor=C_DARK,
                 alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=10)
S_SUBTITLE = _ps("SUBTITLE", fontSize=14, leading=19, textColor=C_MID,
                 alignment=TA_CENTER, spaceAfter=6)
S_PARTNUM  = _ps("PARTNUM", fontSize=13, leading=17, textColor=colors.white,
                 alignment=TA_CENTER, fontName="Helvetica-Bold")
S_PARTTTL  = _ps("PARTTTL", fontSize=24, leading=30, textColor=colors.white,
                 alignment=TA_CENTER, fontName="Helvetica-Bold")
S_H1       = _ps("H1", fontSize=16, leading=20, textColor=colors.white,
                 fontName="Helvetica-Bold")
S_H2       = _ps("H2", fontSize=13, leading=17, textColor=C_DARK,
                 fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
S_H3       = _ps("H3", fontSize=11, leading=15, textColor=C_MID,
                 fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
S_BODY     = _ps("BODY", fontSize=9.6, leading=13.6, alignment=TA_JUSTIFY,
                 spaceAfter=5)
S_BULLET   = _ps("BULLET", fontSize=9.4, leading=13.0, alignment=TA_LEFT,
                 spaceAfter=1.5)
S_CODE     = _ps("CODE", fontSize=8.0, leading=10.6, fontName="Courier",
                 spaceAfter=0, textColor=colors.HexColor("#102030"))
S_EQ       = _ps("EQ", fontSize=9.0, leading=13.0, fontName="Courier-Bold",
                 alignment=TA_CENTER, textColor=C_DARK)
S_BOXT     = _ps("BOXT", fontSize=8.2, leading=10.5, fontName="Helvetica-Bold",
                 textColor=colors.white)
S_BOXB     = _ps("BOXB", fontSize=9.2, leading=12.8, alignment=TA_JUSTIFY)
S_TH       = _ps("TH", fontSize=8.6, leading=11, fontName="Helvetica-Bold",
                 textColor=colors.white)
S_TD       = _ps("TD", fontSize=8.4, leading=11)
S_TDB      = _ps("TDB", fontSize=8.4, leading=11, fontName="Helvetica-Bold")
S_CAP      = _ps("CAP", fontSize=8.2, leading=11, textColor=C_GREY,
                 alignment=TA_CENTER, spaceBefore=2, spaceAfter=6)
S_TOC1     = _ps("TOC1", fontSize=10.5, leading=15, fontName="Helvetica-Bold",
                 textColor=C_DARK, spaceBefore=5)
S_TOC2     = _ps("TOC2", fontSize=9.4, leading=13, textColor=C_MID, leftIndent=10)
S_TOC3     = _ps("TOC3", fontSize=8.8, leading=11.5, textColor=C_GREY, leftIndent=22)

# ------------------------------------------------------------- xml escape ----
def xe(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def mk(s):
    """Escape, then re-enable a tiny inline markup set:
       **bold**  __italic__  `code`  ^{sup}  _{sub}"""
    s = xe(s)
    out, i = [], 0
    while i < len(s):
        if s.startswith("**", i):
            j = s.find("**", i + 2)
            if j < 0:
                out.append(s[i:]); break
            out.append("<b>" + s[i + 2:j] + "</b>"); i = j + 2
        elif s.startswith("__", i):
            j = s.find("__", i + 2)
            if j < 0:
                out.append(s[i:]); break
            out.append("<i>" + s[i + 2:j] + "</i>"); i = j + 2
        elif s[i] == "`":
            j = s.find("`", i + 1)
            if j < 0:
                out.append(s[i:]); break
            out.append('<font face="Courier" size="8.8" color="#7b1fa2">'
                       + s[i + 1:j] + "</font>"); i = j + 1
        elif s.startswith("^{", i):
            j = s.find("}", i + 2)
            if j < 0:
                out.append(s[i:]); break
            out.append("<super>" + s[i + 2:j] + "</super>"); i = j + 1
        elif s.startswith("_{", i):
            j = s.find("}", i + 2)
            if j < 0:
                out.append(s[i:]); break
            out.append("<sub>" + s[i + 2:j] + "</sub>"); i = j + 1
        else:
            out.append(s[i]); i += 1
    return "".join(out)

# ------------------------------------------------------------------ story ----
STORY = []
_counters = {"part": 0, "chap": 0, "sec": 0}

def add(*fl):
    for f in fl:
        STORY.append(f)

def pb():
    add(PageBreak())

def sp(h=4):
    add(Spacer(1, h))

# --------------------------------------------------------------- builders ----
def part(title, blurb="", numbered=True):
    if numbered:
        _counters["part"] += 1
        label = "PART %s" % _roman(_counters["part"])
    else:
        label = "APPENDICES"
    rows = [[Paragraph(label, S_PARTNUM)], [Paragraph(mk(title), S_PARTTTL)]]
    if blurb:
        rows.append([Paragraph(mk(blurb),
                     _ps("pb", fontSize=10, leading=14, textColor=colors.white,
                         alignment=TA_CENTER))])
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, 0), 26),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 26),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
    ]))
    t._toc = (0, ("%s - %s" % (label, title)) if numbered else title.upper())
    add(PageBreak(), Spacer(1, 55 * mm), t, PageBreak())

def _roman(n):
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s; n -= v
    return out

def chapter(title, newpage=True):
    _counters["chap"] += 1
    _counters["sec"] = 0
    n = _counters["chap"]
    txt = "%d.  %s" % (n, title)
    t = Table([[Paragraph(mk(txt), S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    t._toc = (1, txt)
    if newpage:
        add(PageBreak())
    add(t, Spacer(1, 7))
    return n

def h2(title):
    _counters["sec"] += 1
    txt = "%d.%d  %s" % (_counters["chap"], _counters["sec"], title)
    p = Paragraph(mk(txt), S_H2)
    p._toc = (2, txt)
    add(p, HRFlowable(width="100%", thickness=0.6, color=C_LIGHT,
                      spaceBefore=0, spaceAfter=4))

def h3(title):
    add(Paragraph(mk(title), S_H3))

def p(text):
    add(Paragraph(mk(text), S_BODY))

def bul(items, ordered=False, tight=False):
    lf = ListFlowable(
        [ListItem(Paragraph(mk(it), S_BULLET), leftIndent=16) for it in items],
        bulletType="1" if ordered else "bullet",
        bulletFontSize=9 if ordered else 10,
        bulletColor=C_MID, start="1" if ordered else "•",
        leftIndent=14, bulletOffsetY=-1,
        spaceBefore=1, spaceAfter=5 if not tight else 2,
    )
    add(lf)

def code(lines, caption=None, lang=None):
    if isinstance(lines, str):
        lines = lines.split("\n")
    paras = []
    for ln in lines:
        ln = ln.rstrip("\n")
        esc = xe(ln).replace(" ", "&nbsp;")
        stripped = ln.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            esc = '<font color="#2e7d32"><i>%s</i></font>' % esc
        paras.append(Paragraph(esc if esc else "&nbsp;", S_CODE))
    t = Table([[pp] for pp in paras], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.7, C_CODE_BD),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, C_MID),
    ]))
    tail = Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 6)
    if len(paras) <= 18:
        add(KeepTogether([Spacer(1, 3), t, tail]))
    else:
        add(Spacer(1, 3), t, tail)

def eq(lines, caption=None):
    if isinstance(lines, str):
        lines = [lines]
    rows = [[Paragraph(xe(l).replace(" ", "&nbsp;"), S_EQ)] for l in lines]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f4fb")),
        ("BOX", (0, 0), (-1, -1), 0.7, C_PURPLE_BD),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    items = [Spacer(1, 3), t]
    items.append(Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 6))
    add(KeepTogether(items))

def box(kind, title, body):
    bg, bd, default = BOX_KINDS[kind]
    head = title or default
    if isinstance(body, str):
        body = [body]
    inner = [Paragraph(head.upper(), S_BOXT)]
    rows = [[Table([[Paragraph(head.upper(), S_BOXT)]], colWidths=[CONTENT_W - 4],
                   style=TableStyle([
                       ("BACKGROUND", (0, 0), (-1, -1), bd),
                       ("LEFTPADDING", (0, 0), (-1, -1), 7),
                       ("TOPPADDING", (0, 0), (-1, -1), 3),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))]]
    body_fl = [Paragraph(mk(b), S_BOXB) for b in body]
    rows.append([body_fl])
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 1), (-1, 1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, bd),
        ("LEFTPADDING", (0, 1), (-1, 1), 8),
        ("RIGHTPADDING", (0, 1), (-1, 1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
        ("LEFTPADDING", (0, 0), (-1, 0), 0),
        ("RIGHTPADDING", (0, 0), (-1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, 0), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
    ]))
    add(Spacer(1, 3), KeepTogether([t]), Spacer(1, 6))

def tbl(header, rows, widths=None, caption=None, bold_first=False):
    ncol = len(header)
    if widths is None:
        widths = [CONTENT_W / ncol] * ncol
    else:
        tot = float(sum(widths))
        widths = [CONTENT_W * w / tot for w in widths]
    data = [[Paragraph(mk(h), S_TH) for h in header]]
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            st = S_TDB if (bold_first and i == 0) else S_TD
            cells.append(Paragraph(mk(c), st))
        data.append(cells)
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_MID),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0bec5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f4f7fa")))
    t.setStyle(TableStyle(style))
    add(Spacer(1, 3), t)
    add(Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 7))

def diagram(lines, caption=None):
    """Monospace ASCII figure on a light card."""
    rows = [[Paragraph(xe(l).replace(" ", "&nbsp;") or "&nbsp;",
                       _ps("dg", fontSize=7.6, leading=9.8, fontName="Courier",
                           textColor=C_DARK))] for l in lines]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f7fb")),
        ("BOX", (0, 0), (-1, -1), 0.7, C_MID),
        ("TOPPADDING", (0, 0), (-1, -1), 0.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    items = [Spacer(1, 4), t,
             Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 7)]
    add(KeepTogether(items))

def _checkbox():
    """An empty square drawn with a border - independent of font glyphs."""
    b = Table([[""]], colWidths=[3.1 * mm], rowHeights=[3.1 * mm])
    b.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, C_MID)]))
    return b


def checklist(title, items):
    rows = []
    for it in items:
        rows.append([_checkbox(), Paragraph(mk(it), S_BULLET)])
    t = Table(rows, colWidths=[7 * mm, CONTENT_W - 7 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (0, -1), 2.6),      # align box with the text
        ("TOPPADDING", (1, 0), (1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    add(Paragraph(mk(title), S_H3), t, Spacer(1, 6))

# ----------------------------------------------------------- doc template ----
class Book(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, pagesize=A4,
                                 leftMargin=MARGIN_L, rightMargin=MARGIN_R,
                                 topMargin=MARGIN_T, bottomMargin=MARGIN_B, **kw)
        frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W,
                      PAGE_H - MARGIN_T - MARGIN_B, id="body")
        self.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                            onPage=_decorate)])
        self.current_chapter = ""
        self._outline_base = None      # level of the first outline entry

    def afterFlowable(self, flowable):
        toc = getattr(flowable, "_toc", None)
        if toc:
            level, text = toc
            key = "toc%d" % id(flowable)
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (level, text, self.page, key))
            if level <= 1:
                # Normalise so the first entry is always outline level 0 - a
                # document without part dividers starts at chapter level.
                if self._outline_base is None:
                    self._outline_base = level
                lvl = max(0, level - self._outline_base)
                self.canv.addOutlineEntry(text[:90], key, level=lvl,
                                          closed=(lvl == 0))

def _decorate(canvas, doc):
    canvas.saveState()
    # header rule
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.8)
    canvas.line(MARGIN_L, PAGE_H - MARGIN_T + 6, PAGE_W - MARGIN_R,
                PAGE_H - MARGIN_T + 6)
    canvas.setFont("Helvetica", 7.4)
    canvas.setFillColor(C_GREY)
    canvas.drawString(MARGIN_L, PAGE_H - MARGIN_T + 9, HEADER_TEXT)
    # footer
    canvas.setStrokeColor(C_LIGHT)
    canvas.line(MARGIN_L, MARGIN_B - 8, PAGE_W - MARGIN_R, MARGIN_B - 8)
    canvas.setFont("Helvetica", 7.4)
    canvas.drawString(MARGIN_L, MARGIN_B - 16, FOOTER_TEXT)
    canvas.setFont("Helvetica-Bold", 8.4)
    canvas.setFillColor(C_DARK)
    canvas.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 16, str(doc.page))
    canvas.restoreState()


# =============================================================================
#                               FRONT MATTER
# =============================================================================
def front_matter():
    add(Spacer(1, 38 * mm))
    add(Paragraph("Machine Learning<br/>&amp; Deep Learning", S_TITLE))
    add(Spacer(1, 4))
    add(HRFlowable(width="55%", thickness=2, color=C_MID, spaceAfter=10,
                   hAlign="CENTER"))
    add(Paragraph("The Complete Guide - From Beginner to Expert", S_SUBTITLE))
    add(Spacer(1, 6))
    add(Paragraph("Foundations &#183; Classical ML &#183; Deep Learning &#183; "
                  "Transformers &#183; Generative Models &#183; "
                  "Quantization &amp; Pruning &#183; On-Device Training &#183; "
                  "Reinforcement Learning &#183; Time Series &#183; "
                  "Recommenders &#183; Vision &#183; NLP &#183; Speech &#183; "
                  "Distributed Systems &#183; Causal Inference &#183; "
                  "MLOps", S_SUBTITLE))
    add(Spacer(1, 20 * mm))
    rows = [
        ["Contents", "46 chapters in 6 parts, plus 3 appendices"],
        ["Level", "Absolute beginner to research practitioner"],
        ["Style", "Intuition first, then the mathematics, then working code"],
        ["Worked examples", "Every core algorithm is computed by hand on real "
         "numbers you can verify with a calculator"],
        ["Code", "Python / NumPy / PyTorch (framework-agnostic where possible)"],
    ]
    t = Table([[Paragraph(mk(a), S_TDB), Paragraph(mk(b), S_TD)] for a, b in rows],
              colWidths=[45 * mm, CONTENT_W - 45 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LGREY),
        ("BOX", (0, 0), (-1, -1), 0.8, C_MID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    add(t)
    pb()

    # ---- How to use this book -----------------------------------------------
    t = Table([[Paragraph("How To Use This Book", S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    add(t, Spacer(1, 8))
    p("This book is written to be read front to back by someone who has never "
      "trained a model, and to be used as a reference by someone who trains them "
      "for a living. Every chapter follows the same three-beat rhythm: first the "
      "**intuition** in plain language, then the **mathematics** written out "
      "step by step with no skipped algebra, then **code** that you can run.")
    p("Nothing is assumed beyond high-school algebra. Everything else - vectors, "
      "matrices, derivatives, probability - is built up in Chapter 2 and used "
      "consistently afterwards.")

    h3("The six parts")
    tbl(["Part", "Chapters", "What you get out of it"],
        [["I - Foundations", "1-4",
          "Vocabulary, the mathematics you actually need, what 'learning' means "
          "formally, and how to prepare data."],
         ["II - Classical ML", "5-13",
          "Linear and logistic regression, trees, SVMs, boosting, clustering, "
          "PCA, and how to measure a model honestly. Still the right answer for "
          "most tabular problems."],
         ["III - Deep Learning Core", "14-20",
          "Neurons, backpropagation derived by hand, activations, optimizers, "
          "normalization, regularization, and a practical debugging playbook."],
         ["IV - Architectures", "21-27",
          "CNNs, RNN/LSTM, attention and Transformers, LLMs, VAEs/GANs/diffusion, "
          "graph networks, and self-supervised learning."],
         ["V - Expert Topics", "28-35",
          "Quantization, pruning and sparsity, distillation, on-device and "
          "federated training, reinforcement learning, uncertainty and "
          "robustness, MLOps, and how to do research."],
         ["VI - Domains, Theory and Systems", "36-46",
          "Why generalization works at all, probabilistic modelling, "
          "forecasting, recommenders, detection and segmentation, NLP and "
          "retrieval, speech and multimodal models, GPUs and distributed "
          "training, causal inference and A/B testing, privacy and security, "
          "and a complete thirteen-stage project walkthrough."]],
        widths=[22, 14, 64], bold_first=True)

    h3("Reading paths")
    bul([
        "**Complete beginner (about 6 months, part-time):** Chapters 1 -> 2 -> 3 -> 4 "
        "-> 5 -> 6 -> 13 -> 9 -> 11, then Part III in order. Do the exercises at "
        "the end of every chapter before moving on.",
        "**Starting a real project today:** read Chapter 46 first - it is the "
        "thirteen-stage procedure end to end - and follow its references back "
        "into the chapters as each stage needs them.",
        "**Programmer who wants deep learning fast:** skim 1-3, read 4, then jump "
        "to 14-20, then pick the architecture chapter that matches your data "
        "(21 and 40 for images, 22-23 for sequences, 26 for graphs, 38 for time "
        "series).",
        "**Practitioner shipping to devices:** Part III as refresher, then 28-31 "
        "(quantization, pruning, distillation, on-device training), 43 "
        "(hardware and memory arithmetic), 34 (MLOps) and 46 (the full project "
        "walkthrough).",
        "**Working on a specific domain:** go straight to its chapter and read "
        "backwards - 38 time series, 39 recommenders, 40 vision beyond "
        "classification, 41 NLP and retrieval, 42 speech and multimodal.",
        "**Training or serving large models:** 23-24, then 43 (memory, "
        "parallelism, MFU, serving) and 36 (scaling laws).",
        "**Deciding rather than predicting:** 45 (causal inference and A/B "
        "testing) with 13 (evaluation) - the pair that prevents the most "
        "expensive mistakes in industry.",
        "**Interview preparation:** 3, 5, 6, 13, 15, 17, 21, 23, 36, plus the "
        "glossary in Appendix B.",
    ])

    h3("Conventions used throughout")
    tbl(["Symbol / style", "Meaning"],
        [["`x`, `y`", "Scalars in italics in the maths; monospace in the code."],
         ["**x** (bold)", "A vector; by default a column vector of shape (d, 1)."],
         ["**X** (bold capital)", "A matrix; the design matrix has shape (n, d): "
          "n rows = samples, d columns = features."],
         ["theta, w, b", "Learnable parameters: generic parameters, weights, bias."],
         ["L, J", "Per-sample loss L, and full objective / cost J averaged over data."],
         ["eta (or lr)", "Learning rate."],
         ["Coloured boxes", "KEY IDEA = the one thing to remember. MATH = a "
          "derivation. INTUITION = the mental picture. PRACTICAL TIP = what to "
          "actually do. PITFALL = a mistake people really make. EXPERT CORNER = "
          "depth you can skip on a first read."]],
        widths=[26, 74], bold_first=True)
    h3("Worked examples")
    p("Explanations are cheap; arithmetic is not. Wherever an algorithm has a "
      "core computation, this book performs it on real numbers and shows every "
      "intermediate value, so you can check the claim rather than accept it. "
      "Among them: least squares solved by hand on five houses; a gradient-"
      "descent trace step by step; a logistic regression trained on four points; "
      "an exhaustive decision-tree split search; three rounds of gradient "
      "boosting on six numbers; k-means and PCA computed in full; every "
      "classification metric derived from one confusion matrix; a complete "
      "forward and backward pass through a small network with a numerical "
      "gradient check; one Adam update; convolution and receptive-field "
      "arithmetic; attention computed on three tokens; and eight weights "
      "quantized to INT8 with the exact error.")
    box("tip", "Learn by rebuilding",
        "Every algorithm in Parts II and III is presented so that you can "
        "reimplement it in NumPy in under 100 lines. Do that at least once for "
        "linear regression, logistic regression, a decision tree, and a two-layer "
        "network trained with your own backpropagation. Nothing else produces the "
        "same level of understanding - libraries hide exactly the parts that "
        "matter.")
    pb()

    # ---- TOC ----------------------------------------------------------------
    t = Table([[Paragraph("Table of Contents", S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    add(t, Spacer(1, 8))
    toc = TableOfContents()
    toc.levelStyles = [S_TOC1, S_TOC2, S_TOC3]
    add(toc)


# =============================================================================
#                        PART I - FOUNDATIONS
# =============================================================================
def part1():
    part("Foundations",
         "What learning from data means, the mathematics behind it, and how to "
         "set up a problem so that the answer is trustworthy.")

    # ---------------------------------------------------------------- Ch 1 ---
    chapter("What Machine Learning Really Is", newpage=False)
    p("A traditional program is a list of rules written by a person. You want to "
      "detect spam, so you write: __if the subject contains 'FREE MONEY', mark it "
      "as spam__. That works until the spammers write 'F R E E M0NEY'. You add "
      "another rule. They adapt again. After two years you have 4,000 brittle "
      "rules and no one understands them.")
    p("Machine learning inverts the arrow. Instead of writing the rules, you "
      "collect **examples** - 50,000 emails, each labelled spam or not-spam - and "
      "you write a program that **searches for the rules by itself**. The output "
      "of that search is a **model**: a function with numbers inside it that "
      "turns an input into a prediction.")

    diagram([
        "  CLASSICAL PROGRAMMING                    MACHINE LEARNING",
        "  ---------------------                    ----------------",
        "                                                             ",
        "   data  ---+                               data    ---+     ",
        "            |--> [ program ] --> answers               |--> [ LEARNING ] --> program",
        "   rules ---+                               answers ---+      (the model)  ",
        "                                                             ",
        "   Humans supply the rules.                 Humans supply the answers;",
        "                                            the machine writes the rules.",
    ], "Figure 1.1 - The defining inversion of machine learning.")

    box("key", "The one-sentence definition",
        "Machine learning is the practice of fitting a parameterised function to "
        "data by minimising a measure of error, in the hope that the fitted "
        "function also works on data it has never seen. Everything else in this "
        "book - trees, transformers, diffusion models - is a choice about the "
        "shape of that function and the way you search for its parameters.")

    h2("A worked micro-example before any theory")
    p("Suppose you have five houses and you want to predict price from size.")
    tbl(["Size (m^2)", "50", "70", "90", "110", "130"],
        [["Price (k EUR)", "150", "195", "260", "300", "355"]],
        widths=[24, 15, 15, 15, 15, 16], bold_first=True)
    p("You guess the relationship is a straight line, `price = w * size + b`. "
      "The pair `(w, b)` are the **parameters**. Learning here means: try many "
      "values of `w` and `b`, and keep the pair whose predictions are closest to "
      "the five real prices. 'Closest' has to be defined numerically - that "
      "definition is the **loss function**. The usual choice is mean squared "
      "error:")
    eq("J(w, b) = (1/n) * SUM_i ( w * size_i + b - price_i )^2")
    p("For this data the best fit is roughly `w = 2.55`, `b = 20`. That model now "
      "predicts a 100 m^2 house at about 275k. You never wrote the rule "
      "'each square metre costs 2,550 EUR' - the data implied it and the "
      "optimiser found it. That is the entire idea, and every later chapter is a "
      "richer version of this loop:")
    diagram([
        "   +-------------+     +------------------+     +---------------+",
        "   |  DATA       | --> |  MODEL f(x; th)  | --> |  PREDICTION   |",
        "   +-------------+     +------------------+     +---------------+",
        "                             ^                          |",
        "                             |                          v",
        "                       +------------+           +----------------+",
        "                       | OPTIMISER  | <-------- |  LOSS  J(th)   |",
        "                       +------------+  gradient +----------------+",
    ], "Figure 1.2 - The universal training loop: predict, score, adjust, repeat.")

    h2("The vocabulary, defined once and used forever")
    tbl(["Term", "Meaning", "In the house example"],
        [["Sample / instance", "One row of data, one thing you make a prediction about.",
          "One house."],
         ["Feature", "One measured input variable. d features per sample.",
          "Size in m^2."],
         ["Feature vector x", "All features of one sample stacked together.", "[50]"],
         ["Label / target y", "The correct answer you want to predict.", "150k"],
         ["Design matrix X", "All samples stacked: shape (n, d).", "5 x 1 matrix"],
         ["Model f(x; th)", "The parameterised function producing predictions.",
          "w*x + b"],
         ["Parameters th", "Numbers learned from data.", "w and b"],
         ["Hyperparameters", "Numbers you choose before training, not learned from "
          "the training loss.", "Learning rate, degree of polynomial"],
         ["Loss L", "Error on one sample.", "(pred - price)^2"],
         ["Cost / objective J", "Average loss over a dataset, plus any penalties.",
          "MSE over 5 houses"],
         ["Training", "Searching parameter space to minimise J.", "Fitting w, b"],
         ["Inference", "Running the trained model on new inputs.",
          "Pricing a new listing"],
         ["Generalisation", "Accuracy on data not used for training.",
          "Pricing houses you never saw"]],
        widths=[19, 49, 32], bold_first=True)

    h2("The four learning paradigms")
    h3("1. Supervised learning - you have the answers")
    p("Every training sample carries a label. The model learns a mapping "
      "`x -> y`. Two sub-types dominate:")
    bul([
        "**Regression:** y is a continuous number. Price, temperature, remaining "
        "battery life, time-to-failure. Measured with MSE, MAE, R^2.",
        "**Classification:** y is one of K discrete classes. Spam / not spam, "
        "which of 1,000 objects is in this photo, which of 5 activities a "
        "wearable sensor is recording. Measured with accuracy, precision, recall, "
        "F1, AUC.",
    ])
    p("Supervised learning is by far the most reliable paradigm, and also the "
      "most expensive: someone has to produce the labels. A rule of thumb from "
      "industry is that 60-80% of the effort on a real supervised project is "
      "spent obtaining, cleaning and auditing labels, not on modelling.")

    h3("2. Unsupervised learning - structure without answers")
    p("Only `x` is available. The goal is to find structure: **clusters** of "
      "similar samples (k-means, GMM), a **low-dimensional** description (PCA, "
      "autoencoders), a **density** model of where data lives (which also gives "
      "you anomaly detection), or **associations** between items.")

    h3("3. Self-supervised learning - the answers hide in the data")
    p("Take unlabelled data and invent a task whose label is part of the data "
      "itself: hide a word and predict it, hide a patch of an image and "
      "reconstruct it, ask whether two augmented crops came from the same photo. "
      "This is how every modern large model - GPT-class language models, CLIP, "
      "DINO, wav2vec - is pretrained. It is technically supervised learning with "
      "free labels, and it is the single biggest reason deep learning scaled: it "
      "removed the labelling bottleneck. Chapter 27 covers it in depth.")

    h3("4. Reinforcement learning - learning from consequences")
    p("An **agent** takes **actions** in an **environment**, receives a scalar "
      "**reward**, and must learn a **policy** that maximises cumulative reward. "
      "There is no labelled correct action, only delayed and noisy feedback, and "
      "the agent's own behaviour determines the data it sees. Robotics, game "
      "playing, and the alignment stage of large language models (RLHF) all live "
      "here. Chapter 32.")

    box("intuit", "Which paradigm is my problem?",
        "Ask what you can actually collect. If you can collect input-output "
        "pairs, use supervised learning - it is the most sample-efficient and the "
        "easiest to evaluate. If you can collect only inputs, use self-supervised "
        "pretraining and then fine-tune on the few labels you can afford. Use "
        "reinforcement learning only when the decision changes the future data "
        "(control, sequential decisions); otherwise it makes an easy problem "
        "hard.")

    h2("Where deep learning fits")
    p("**Deep learning** is not a separate field from machine learning; it is the "
      "subset in which the model is a neural network with many layers, and in "
      "which the **features are learned rather than designed**. That is the whole "
      "distinction, and it is a big one:")
    diagram([
        "  CLASSICAL ML PIPELINE",
        "    raw data -> [ hand-designed features ] -> [ learned classifier ] -> y",
        "                 ^ engineered by a human expert over months",
        "",
        "  DEEP LEARNING PIPELINE",
        "    raw data -> [ layer1 -> layer2 -> ... -> layerN -> classifier ] -> y",
        "                 ^ every stage learned jointly from the same loss",
    ], "Figure 1.3 - Feature engineering versus representation learning.")
    p("In a convolutional network trained on photographs, the first layer ends up "
      "detecting edges, the next combines edges into corners and textures, the "
      "next into object parts, and the last into whole objects. Nobody programmed "
      "that hierarchy; it is what minimising the classification loss produces. "
      "This is called **representation learning**, and it is why deep learning "
      "wins on images, audio, text and video, where useful features are hard for "
      "humans to write down.")

    box("warn", "Deep learning is not always the answer",
        "On small or medium tabular datasets - the most common kind of data in "
        "industry - gradient-boosted trees (Chapter 11) usually beat neural "
        "networks, train in seconds instead of hours, need almost no tuning, and "
        "are easier to explain to a regulator. Reach for deep learning when the "
        "input is perceptual (pixels, waveforms, tokens), when you have a lot of "
        "data, or when you can start from a pretrained model.")

    h2("The taxonomy at a glance")
    tbl(["Paradigm", "Input", "Typical models", "Typical use"],
        [["Supervised - regression", "x, y in R",
          "Linear/ridge, gradient boosting, MLP", "Price, demand, RUL"],
         ["Supervised - classification", "x, y in {1..K}",
          "Logistic regression, trees, CNN, Transformer", "Spam, diagnosis, vision"],
         ["Unsupervised - clustering", "x only", "k-means, GMM, DBSCAN, HDBSCAN",
          "Segmentation, grouping"],
         ["Unsupervised - dim. reduction", "x only", "PCA, t-SNE, UMAP, autoencoder",
          "Visualisation, compression"],
         ["Unsupervised - density", "x only", "GMM, normalising flow, diffusion",
          "Anomaly detection, generation"],
         ["Self-supervised", "x + invented task", "BERT/GPT objectives, SimCLR, MAE",
          "Pretraining foundation models"],
         ["Reinforcement", "state, action, reward", "DQN, PPO, SAC, AlphaZero",
          "Control, games, RLHF"]],
        widths=[24, 19, 32, 25], bold_first=True)

    h2("A first end-to-end program")
    p("Here is a complete, honest supervised-learning workflow in 25 lines. Read "
      "it now even if the details are unfamiliar; every line is explained in the "
      "next three chapters.")
    code([
        "import numpy as np",
        "from sklearn.datasets import load_breast_cancer",
        "from sklearn.model_selection import train_test_split, cross_val_score",
        "from sklearn.pipeline import make_pipeline",
        "from sklearn.preprocessing import StandardScaler",
        "from sklearn.linear_model import LogisticRegression",
        "from sklearn.metrics import classification_report, roc_auc_score",
        "",
        "X, y = load_breast_cancer(return_X_y=True)      # 569 samples, 30 features",
        "",
        "# 1. Hold out a test set FIRST and do not look at it again until the end.",
        "X_tr, X_te, y_tr, y_te = train_test_split(",
        "        X, y, test_size=0.2, stratify=y, random_state=0)",
        "",
        "# 2. Scaling belongs INSIDE the pipeline so it is refit on each CV fold.",
        "model = make_pipeline(StandardScaler(),",
        "                      LogisticRegression(max_iter=5000, C=1.0))",
        "",
        "# 3. Estimate generalisation using cross-validation on the training set.",
        "cv = cross_val_score(model, X_tr, y_tr, cv=5, scoring='roc_auc')",
        "print(f'CV AUC: {cv.mean():.3f} +/- {cv.std():.3f}')",
        "",
        "# 4. Refit on all training data, then evaluate ONCE on the test set.",
        "model.fit(X_tr, y_tr)",
        "proba = model.predict_proba(X_te)[:, 1]",
        "print('test AUC:', round(roc_auc_score(y_te, proba), 3))",
        "print(classification_report(y_te, (proba > 0.5).astype(int)))",
    ], "Listing 1.1 - The shape of every honest supervised experiment.")
    p("Four habits in that listing separate practitioners from beginners: the "
      "test set is split off **before** anything else happens; preprocessing is "
      "inside the pipeline so it cannot leak information across folds; the model "
      "is selected using cross-validation, not the test set; and the test set is "
      "touched exactly once.")

    ex_ch1()

    h2("What can go wrong (a preview of Chapter 3)")
    bul([
        "**Overfitting:** the model memorises the training data, including its "
        "noise, and fails on new data. The classic symptom is 99% training "
        "accuracy and 62% test accuracy.",
        "**Underfitting:** the model is too simple to capture the pattern - a "
        "straight line through a curved relationship. Both training and test error "
        "are high.",
        "**Data leakage:** information about the answer sneaks into the features. "
        "Scaling before splitting, using a future value as a feature, or having "
        "the same patient in both train and test all inflate your score and "
        "produce a model that fails in production.",
        "**Distribution shift:** the world changes after you train. Prices move, "
        "sensors drift, users behave differently. A model is a photograph of the "
        "past.",
        "**Optimising the wrong metric:** 99% accuracy on a dataset where 99% of "
        "samples are negative means your model learned to say 'no'.",
    ])

    h3("Exercises")
    bul([
        "Fit `price = w*size + b` on the five houses above by hand: compute J for "
        "(w, b) = (2.0, 50), (2.55, 20), (3.0, 0) and say which is best.",
        "For each of these, name the paradigm and the metric you would use: "
        "predicting tomorrow's electricity demand; grouping customers with no "
        "labels; teaching a drone to land; filling in masked words in Wikipedia.",
        "Run Listing 1.1. Then deliberately break it by scaling `X` before the "
        "split and observe how much the test AUC changes - this is leakage in "
        "miniature.",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 2 ---
    chapter("The Mathematical Toolkit You Actually Need")
    p("You do not need a mathematics degree. You need fluency with four things: "
      "**linear algebra** (how data and parameters are stored and multiplied), "
      "**calculus** (how a loss changes when a parameter moves), **probability** "
      "(how to talk about uncertainty and where loss functions come from), and "
      "**optimisation** (how to move parameters downhill). This chapter builds "
      "all four from scratch, with machine-learning meaning attached to every "
      "object.")

    ex_ch2_notation()

    h2("Linear algebra: the language of data")
    h3("Scalars, vectors, matrices, tensors")
    tbl(["Object", "Notation", "Shape", "In ML"],
        [["Scalar", "x", "()", "A learning rate, a single loss value"],
         ["Vector", "x (bold)", "(d,)", "One sample's features; one layer's biases"],
         ["Matrix", "X (bold cap)", "(n, d)", "A batch of n samples; a weight matrix"],
         ["3-tensor", "T", "(N, H, W)", "A batch of greyscale images"],
         ["4-tensor", "T", "(N, C, H, W)", "A batch of colour images in PyTorch order"]],
        widths=[16, 18, 20, 46], bold_first=True)
    p("A **tensor** in deep-learning software is simply an n-dimensional array "
      "with an attached gradient machinery. The word carries no physics meaning "
      "here. What matters in practice is **shape discipline**: most bugs in deep "
      "learning are shape bugs, and the fastest debugging habit you can build is "
      "printing `tensor.shape` at every step.")

    h3("The three products you must never confuse")
    eq(["Dot product      a . b  = SUM_i a_i b_i                -> a scalar",
        "Matrix-vector    (A x)_i = SUM_j A_ij x_j             -> a vector",
        "Elementwise      (a * b)_i = a_i b_i                  -> same shape"])
    p("Matrix multiplication `C = A B` with A of shape (m, k) and B of shape "
      "(k, n) gives C of shape (m, n), where `C_ij = SUM_k A_ik B_kj`. The inner "
      "dimensions must match; the outer ones survive. Reading that rule as "
      "__(m, k) x (k, n) -> (m, n)__ and checking it mentally before every line "
      "you write will save you hours.")
    box("key", "A neural network layer is one matrix multiply",
        "A fully connected layer computing z = W x + b for a single sample "
        "becomes Z = X W^T + b for a whole batch, where X is (n, d) and W is "
        "(units, d). The reason GPUs transformed this field is that this single "
        "operation - dense matrix multiplication - is exactly what they do "
        "thousands of times faster than a CPU.")
    p("Useful identities you will meet again in the backpropagation chapter:")
    eq(["(A B)^T = B^T A^T",
        "(A B) C = A (B C)                 (associative)",
        "A (B + C) = A B + A C             (distributive)",
        "A B != B A                        (NOT commutative)"])

    h3("Norms - how big is this vector?")
    eq(["L1 norm     ||x||_1 = SUM_i |x_i|            -> promotes sparsity",
        "L2 norm     ||x||_2 = sqrt( SUM_i x_i^2 )    -> ordinary length",
        "L-inf norm  ||x||_inf = max_i |x_i|          -> worst single component"])
    p("L2 is the default: it is smooth, differentiable everywhere, and gives "
      "Euclidean distance `||a - b||_2`. L1 is not differentiable at zero, and "
      "that corner is precisely why L1 regularisation drives coefficients exactly "
      "to zero (Chapter 7). L-infinity appears in adversarial robustness, where "
      "an attacker may perturb every pixel by at most epsilon (Chapter 33).")

    h3("Geometry: angles, projections, similarity")
    eq("a . b = ||a|| ||b|| cos(theta)      =>      cos_sim(a, b) = (a . b) / (||a|| ||b||)")
    p("Cosine similarity ignores magnitude and compares direction only; it is the "
      "standard way to compare embeddings, and it is the numerator inside "
      "attention (Chapter 23) and inside every vector database. Two vectors are "
      "**orthogonal** when their dot product is zero - they share no information "
      "in the linear sense.")

    h3("Matrix decompositions that carry real meaning")
    bul([
        "**Eigendecomposition** `A = Q L Q^-1`: for a symmetric matrix, Q is "
        "orthogonal and L diagonal. Eigenvectors are directions the matrix only "
        "stretches; eigenvalues are the stretch factors. The eigenvalues of the "
        "**Hessian** of your loss describe the curvature of the optimisation "
        "landscape, and their ratio (the **condition number**) predicts how badly "
        "plain gradient descent will zig-zag.",
        "**Singular value decomposition** `A = U S V^T`: exists for every matrix. "
        "Keeping only the top k singular values gives the best possible rank-k "
        "approximation (Eckart-Young theorem). This one fact powers PCA "
        "(Chapter 12), latent semantic analysis, recommender systems, and LoRA "
        "fine-tuning of large models (Chapter 24).",
        "**Rank**: the number of linearly independent directions a matrix "
        "actually uses. Low-rank structure is what makes compression possible; "
        "'low-rank adaptation' means updating a big weight matrix with a product "
        "of two thin ones.",
    ])
    code([
        "import numpy as np",
        "A = np.random.randn(200, 50)",
        "U, s, Vt = np.linalg.svd(A, full_matrices=False)",
        "k = 10",
        "A_k = (U[:, :k] * s[:k]) @ Vt[:k]          # best rank-10 approximation",
        "err = np.linalg.norm(A - A_k) / np.linalg.norm(A)",
        "print(k, 'components keep', round(100*(1-err), 1), '% of the energy')",
        "# Storage: 200*50 = 10,000 numbers  ->  (200+50)*10 = 2,500 numbers",
    ], "Listing 2.1 - Low-rank approximation: the mathematical core of PCA and LoRA.")

    h2("Calculus: how the loss reacts to a parameter")
    h3("Derivative, partial derivative, gradient")
    p("The derivative `df/dx` is the rate of change of f at a point: move x by a "
      "tiny amount h and f moves by about `h * df/dx`. With many inputs, the "
      "**partial derivative** `dJ/dw_i` measures the effect of one parameter with "
      "all others frozen. Collecting all partials gives the **gradient**:")
    eq("grad J(w) = [ dJ/dw_1 , dJ/dw_2 , ... , dJ/dw_d ]")
    box("intuit", "The gradient is the uphill direction",
        "Stand on a hillside in fog. The gradient points in the direction of "
        "steepest ascent, and its length says how steep. To minimise a loss you "
        "therefore step in the direction of the NEGATIVE gradient. That single "
        "sentence is the whole of gradient descent, and by extension most of "
        "modern machine learning.")

    h3("The chain rule - the engine of deep learning")
    p("If `y = f(u)` and `u = g(x)`, then `dy/dx = (dy/du) * (du/dx)`. For a "
      "network that computes a composition of L layers, the derivative of the "
      "loss with respect to an early weight is a product of L local derivatives. "
      "Backpropagation (Chapter 15) is nothing more than an efficient, "
      "right-to-left evaluation of that product, reusing shared subexpressions.")
    eq(["J = L(a_L),   a_L = f_L(a_L-1),  ... ,  a_1 = f_1(x)",
        "",
        "dJ/dW_k = dJ/da_L * da_L/da_L-1 * ... * da_k+1/da_k * da_k/dW_k"])
    p("Two immediate consequences, both central to Part III: if the local factors "
      "are consistently smaller than 1, the product shrinks exponentially with "
      "depth (**vanishing gradients**); if consistently larger than 1, it explodes "
      "(**exploding gradients**). Residual connections, careful initialisation and "
      "normalisation layers all exist to keep that product near 1.")

    h3("Jacobians, Hessians and what curvature buys you")
    bul([
        "**Jacobian** J: the matrix of all first partials of a vector-valued "
        "function, shape (outputs, inputs). Automatic differentiation never builds "
        "it explicitly; it computes Jacobian-vector products instead, which is why "
        "backprop costs about the same as a forward pass.",
        "**Hessian** H: the matrix of second partials, shape (d, d). Positive "
        "definite H means a local minimum; mixed signs mean a saddle point. In "
        "high dimensions saddles vastly outnumber local minima, which is the "
        "modern explanation of why gradient descent works so well on "
        "non-convex networks.",
        "**Second-order methods** (Newton, L-BFGS, K-FAC) use curvature to choose "
        "the step size per direction. They converge in fewer iterations but cost "
        "O(d^2) or O(d^3) per step; with d in the billions they are impractical, "
        "which is why Adam - a cheap diagonal approximation - dominates.",
    ])

    h2("Probability: reasoning under uncertainty")
    h3("The rules")
    eq(["Sum rule          P(A) = SUM_B P(A, B)",
        "Product rule      P(A, B) = P(A | B) P(B)",
        "Bayes rule        P(H | D) = P(D | H) P(H) / P(D)",
        "Independence      P(A, B) = P(A) P(B)"])
    p("Bayes' rule is how you turn a **likelihood** (how probable is this data if "
      "the hypothesis holds) into a **posterior** (how probable is the hypothesis "
      "given the data). Read it as: __posterior is proportional to likelihood "
      "times prior__.")
    box("math", "The classic medical-test calculation",
        "A disease affects 1 in 1,000 people. A test has 99% sensitivity and 99% "
        "specificity. You test positive - what is the probability you are ill? "
        "P(D)=0.001, P(+|D)=0.99, P(+|not D)=0.01. Then "
        "P(+) = 0.99*0.001 + 0.01*0.999 = 0.01098, so "
        "P(D|+) = 0.00099 / 0.01098 = 9.0%. Ninety-one percent of positives are "
        "false. This is the same arithmetic as precision on an imbalanced "
        "classification problem (Chapter 13) - and the same reason a 99%-accurate "
        "fraud detector can be useless.")

    h3("Distributions you will meet")
    tbl(["Distribution", "Support", "Parameters", "Where it appears in ML"],
        [["Bernoulli", "{0,1}", "p", "Binary labels; the output of a sigmoid"],
         ["Categorical", "{1..K}", "p_1..p_K", "Multiclass labels; softmax output"],
         ["Binomial", "0..n", "n, p", "Counts of successes; A/B tests"],
         ["Gaussian", "R", "mu, sigma^2", "Noise models, weight init, VAEs, diffusion"],
         ["Laplace", "R", "mu, b", "The prior behind L1 regularisation"],
         ["Poisson", "0,1,2..", "lambda", "Event counts; click and arrival models"],
         ["Exponential", "R+", "lambda", "Waiting times, survival analysis"],
         ["Uniform", "[a,b]", "a, b", "Random search, dropout masks, init ranges"],
         ["Beta / Dirichlet", "simplex", "alpha", "Priors over probabilities; topic models"]],
        widths=[18, 12, 16, 54], bold_first=True)

    h3("Expectation, variance, covariance")
    eq(["E[X] = SUM_x x P(x)                       (mean)",
        "Var[X] = E[(X - E[X])^2] = E[X^2] - E[X]^2",
        "Cov[X, Y] = E[(X - E X)(Y - E Y)]",
        "Corr[X, Y] = Cov[X, Y] / (sd(X) sd(Y))    in [-1, 1]"])
    p("Linearity of expectation, `E[aX + bY] = aE[X] + bE[Y]`, holds even when X "
      "and Y are dependent, and it is used constantly - for instance to show that "
      "a minibatch gradient is an unbiased estimate of the full-dataset gradient, "
      "which is the entire justification for stochastic gradient descent.")

    h3("Maximum likelihood: where loss functions come from")
    p("Assume your data was generated by a model with parameters theta. The "
      "**likelihood** is the probability of the observed data under that model. "
      "Maximum-likelihood estimation picks theta to maximise it; equivalently it "
      "minimises the negative log-likelihood, because logs turn products into "
      "sums and are monotone:")
    eq(["theta_MLE = argmax_theta PROD_i p(y_i | x_i; theta)",
        "          = argmin_theta  -SUM_i log p(y_i | x_i; theta)"])
    box("key", "Two derivations you should be able to do from memory",
        "Assume Gaussian noise, y = f(x) + eps with eps ~ N(0, sigma^2). The "
        "negative log-likelihood becomes SUM (y_i - f(x_i))^2 / (2 sigma^2) plus a "
        "constant - that is MEAN SQUARED ERROR. Assume a Bernoulli label with "
        "p = sigmoid(z). The negative log-likelihood becomes "
        "-SUM [ y log p + (1-y) log(1-p) ] - that is CROSS-ENTROPY. Loss "
        "functions are not arbitrary; each one encodes an assumption about the "
        "noise in your labels.")

    h3("Information theory in one page")
    eq(["Entropy            H(p) = -SUM_x p(x) log p(x)",
        "Cross-entropy      H(p, q) = -SUM_x p(x) log q(x)",
        "KL divergence      KL(p || q) = SUM_x p(x) log( p(x)/q(x) ) >= 0",
        "Relationship       H(p, q) = H(p) + KL(p || q)"])
    p("Entropy measures average surprise, in bits if the log is base 2. "
      "Cross-entropy measures the cost of encoding data from p using a code built "
      "for q. Since H(p) is fixed by the data, **minimising cross-entropy is "
      "exactly minimising KL divergence** between the true label distribution and "
      "your model - which is why it is the default classification loss. KL is not "
      "symmetric, and that asymmetry is the difference between mode-seeking and "
      "mode-covering behaviour in variational inference and GAN training "
      "(Chapter 25).")

    ex_ch2_examples()

    h2("Optimisation: moving downhill")
    h3("Gradient descent, stated precisely")
    eq(["repeat:   theta <- theta - eta * grad J(theta)"])
    p("Convergence depends on the learning rate eta. For a convex quadratic with "
      "largest Hessian eigenvalue L, gradient descent converges only if "
      "`eta < 2/L`. Too small and you crawl; too large and you oscillate or "
      "diverge. This one hyperparameter is still, in 2020s practice, the most "
      "important knob in deep learning.")
    diagram([
        "  eta too small        eta about right        eta too large",
        "    \\                     \\                      \\    /\\",
        "     \\_                    \\_                     \\  /  \\   /",
        "      \\__                    \\__                   \\/    \\ /",
        "       ...  (crawls)            \\_. (converges)            V  (diverges)",
    ], "Figure 2.1 - The effect of the learning rate on the same loss surface.")

    h3("Batch, stochastic and mini-batch")
    tbl(["Variant", "Gradient uses", "Cost per step", "Behaviour"],
        [["Batch GD", "all n samples", "O(n)", "Smooth, exact, far too slow for large n"],
         ["SGD", "1 sample", "O(1)", "Very noisy, can escape shallow minima"],
         ["Mini-batch", "B samples (32-8192)", "O(B)",
          "The universal default: parallel-friendly and stable"]],
        widths=[16, 22, 16, 46], bold_first=True)
    p("Mini-batching wins for a hardware reason as much as a statistical one: a "
      "GPU computes a 256-sample batch in barely more wall-clock time than a "
      "single sample, because the bottleneck is memory movement, not arithmetic.")

    h3("Convexity, and why non-convexity is survivable")
    p("A function is **convex** if the line segment between any two points on the "
      "graph lies above the graph; then any local minimum is global. Linear "
      "regression, ridge, logistic regression and linear SVMs are convex - you "
      "can trust the optimum. Neural networks are decidedly non-convex, yet "
      "gradient descent finds excellent solutions. The current understanding: in "
      "very high dimensions, most critical points are saddles rather than poor "
      "local minima, and over-parameterised networks have wide, connected basins "
      "of good solutions.")

    h3("Constrained optimisation and Lagrange multipliers")
    p("To minimise f(x) subject to g(x) = 0, form `L(x, lam) = f(x) + lam g(x)` "
      "and set all partial derivatives to zero. This machinery yields the dual "
      "formulation of SVMs (Chapter 10), the eigenvalue problem in PCA "
      "(Chapter 12), and the equivalence between constrained-norm and "
      "penalised-norm regularisation (Chapter 7).")

    box("expert", "Numerical care that saves real experiments",
        "Never compute `log(softmax(z))` directly - subtract max(z) first and use "
        "the log-sum-exp trick, or call `log_softmax`. Never compute "
        "`log(sigmoid(z))` - use `logsigmoid` or a loss that takes raw logits "
        "(`BCEWithLogitsLoss`). Float32 has about 7 decimal digits of precision "
        "and float16 about 3, with a maximum of 65,504 - which is why mixed "
        "precision training needs loss scaling (Chapter 20). Catastrophic "
        "cancellation when subtracting nearly equal numbers is the source of most "
        "mysterious NaNs.")

    h3("Exercises")
    bul([
        "Show that for f(w) = ||Xw - y||^2 the gradient is 2 X^T (Xw - y). Do it "
        "componentwise first, then in matrix form.",
        "Derive cross-entropy from the Bernoulli likelihood, then differentiate it "
        "with respect to the logit z where p = sigmoid(z). You should get the "
        "famously clean result p - y.",
        "Compute the condition number of [[1, 0], [0, 100]] and sketch what "
        "gradient descent does on the quadratic it defines.",
        "Implement log-sum-exp in NumPy and compare it against a naive "
        "implementation on the input [1000, 1001, 1002].",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 3 ---
    chapter("The Learning Problem: Generalization, Bias and Variance")
    p("Training error is easy to drive to zero - store the training set in a "
      "lookup table. The entire difficulty of machine learning is **test** error. "
      "This chapter gives you the formal statement of that difficulty and the "
      "practical tools for managing it. If you read only one chapter of Part I, "
      "read this one; nearly every real-world failure traces back to something "
      "here.")

    h2("The formal setup")
    p("Assume samples (x, y) are drawn independently from an unknown distribution "
      "D. The quantity you care about is the **risk**, the expected loss on a "
      "fresh sample:")
    eq(["R(f)      = E_(x,y)~D [ L(f(x), y) ]          <- what you want",
        "R_emp(f)  = (1/n) SUM_i L(f(x_i), y_i)        <- what you can measure"])
    p("You minimise R_emp and hope R is close to it. The gap `R - R_emp` is the "
      "**generalisation gap**. Statistical learning theory bounds it, roughly, by "
      "a term that grows with the capacity of your model class and shrinks with "
      "the square root of the number of samples:")
    eq("R(f) <= R_emp(f) + O( sqrt( capacity / n ) )")
    p("The classical capacity measures are **VC dimension** (the largest set of "
      "points the class can label in all possible ways) and **Rademacher "
      "complexity** (how well the class can fit pure noise). These bounds are "
      "loose for deep networks - a ResNet can memorise random labels, so its VC "
      "dimension is enormous, yet it still generalises. Explaining that is an "
      "active research area (implicit regularisation of SGD, flat minima, "
      "margin-based and compression-based bounds). The bounds are still worth "
      "knowing because their **shape** is right: more capacity hurts, more data "
      "helps, and the trade-off is what you tune.")

    h2("Overfitting and underfitting, seen on a curve")
    diagram([
        "  error",
        "    ^",
        "    |  \\                                   /  test error",
        "    |   \\                                /",
        "    |    \\                            _/",
        "    |     \\__                     __/",
        "    |        \\____           ___/                <-- sweet spot at the",
        "    |             \\_________/                         minimum of test error",
        "    |               \\",
        "    |                 \\________________  training error",
        "    +-------------------------------------------> model capacity",
        "       UNDERFIT            OK                OVERFIT",
        "     high bias                            high variance",
    ], "Figure 3.1 - The classical capacity/error picture.")
    tbl(["Symptom", "Diagnosis", "What to do"],
        [["Train error high, test error high (similar)", "Underfitting / high bias",
          "Bigger model, more features, train longer, reduce regularisation, "
          "check the learning rate"],
         ["Train error low, test error much higher", "Overfitting / high variance",
          "More data, augmentation, stronger regularisation, smaller model, early "
          "stopping, ensembling"],
         ["Train error low, test low, production bad", "Distribution shift or leakage",
          "Audit the features for leakage, re-split by time or group, monitor "
          "drift, retrain regularly"],
         ["Test error lower than train error", "Usually a bug, or dropout/augmentation "
          "active only at train time", "Verify the split; check eval() mode"]],
        widths=[27, 21, 52], bold_first=True)

    h2("The bias-variance decomposition, derived")
    p("For squared loss and a target `y = f*(x) + eps` with `E[eps] = 0` and "
      "`Var[eps] = sigma^2`, consider the prediction `f_hat(x)` produced by "
      "training on a random dataset. Taking the expectation over datasets:")
    eq(["E[ (y - f_hat(x))^2 ]  =  ( E[f_hat(x)] - f*(x) )^2      <- BIAS^2",
        "                        +  E[ (f_hat(x) - E[f_hat(x)])^2 ] <- VARIANCE",
        "                        +  sigma^2                          <- IRREDUCIBLE"])
    box("math", "Where each term comes from",
        "Add and subtract the average prediction E[f_hat(x)] inside the square, "
        "expand, and observe that the cross term vanishes because "
        "E[f_hat - E f_hat] = 0. Noise eps is independent of the model, so it "
        "separates out. Bias is systematic error - the model class cannot "
        "represent the truth. Variance is sensitivity to which particular "
        "training set you happened to draw. Irreducible noise is the floor: no "
        "model, however large, can go below sigma^2.")
    bul([
        "**High bias, low variance:** linear regression on a curved relationship; "
        "a depth-2 decision tree; heavy L2 regularisation.",
        "**Low bias, high variance:** a fully grown decision tree; 1-nearest "
        "neighbour; a huge network trained without regularisation on a small "
        "dataset.",
        "**Bagging** (Chapter 11) attacks variance by averaging many high-variance "
        "models. **Boosting** attacks bias by adding many high-bias models in "
        "sequence. Knowing which one you need is the point of the decomposition.",
    ])

    box("expert", "Double descent - the modern amendment",
        "Push capacity past the point where the model exactly interpolates the "
        "training data and test error often falls AGAIN, sometimes below its "
        "classical minimum. The test-error curve is therefore not U-shaped but "
        "U-then-down. This is observed for random-feature models, boosting and "
        "deep networks, and it is why 'the model is too big, it will overfit' is "
        "no longer sound advice for neural networks. In the over-parameterised "
        "regime the useful lever is not smaller capacity but better implicit and "
        "explicit regularisation.")

    h2("Splitting data honestly")
    h3("Train / validation / test")
    tbl(["Split", "Typical size", "Used for", "How often you may look"],
        [["Training", "60-80%", "Fitting parameters", "Continuously"],
         ["Validation", "10-20%", "Choosing hyperparameters, early stopping, model "
          "selection", "Many times - it is being consumed"],
         ["Test", "10-20%", "One final unbiased estimate", "Once. Genuinely once."]],
        widths=[14, 14, 42, 30], bold_first=True)
    box("warn", "The validation set decays with use",
        "Every hyperparameter choice made on the validation set leaks a little "
        "information into your model. After a hundred experiments, validation "
        "performance is optimistic - you have partially fitted the validation "
        "set through your own decisions. This is why a untouched test set exists, "
        "and why leaderboards eventually go stale. If you must run hundreds of "
        "experiments, refresh the validation split or hold back a second test "
        "set.")

    h3("Cross-validation")
    diagram([
        "  5-fold cross-validation (shaded = validation fold)",
        "    fold 1:  [VVVV][    ][    ][    ][    ]",
        "    fold 2:  [    ][VVVV][    ][    ][    ]",
        "    fold 3:  [    ][    ][VVVV][    ][    ]",
        "    fold 4:  [    ][    ][    ][VVVV][    ]",
        "    fold 5:  [    ][    ][    ][    ][VVVV]",
        "    score = mean of the five validation scores  (+/- std)",
    ], "Figure 3.2 - k-fold cross-validation uses every sample for both roles.")
    bul([
        "**k-fold (k = 5 or 10):** the default. Cost is k trainings.",
        "**Stratified k-fold:** preserves class proportions in every fold - always "
        "use it for classification, especially when classes are imbalanced.",
        "**Leave-one-out:** k = n. Nearly unbiased but high variance and very "
        "expensive; useful only for tiny datasets.",
        "**Group k-fold:** keeps all samples from one patient, user or device in "
        "the same fold. Without it, a model can recognise the individual instead "
        "of the condition.",
        "**Time-series split:** train on the past, validate on the future, never "
        "shuffle. Rolling or expanding windows only.",
        "**Nested CV:** an inner loop selects hyperparameters, an outer loop "
        "estimates performance. This is the statistically correct way to report a "
        "number when you also tuned - and it is what reviewers ask for.",
    ])
    code([
        "from sklearn.model_selection import (StratifiedKFold, GroupKFold,",
        "                                     TimeSeriesSplit, cross_val_score)",
        "",
        "# classification, keeps class balance in each fold",
        "cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)",
        "",
        "# one subject must never appear in both train and validation",
        "cv = GroupKFold(n_splits=5)          # pass groups=subject_ids to the split",
        "",
        "# temporal data: fold i trains on [0..t_i] and validates on (t_i..t_i+1]",
        "cv = TimeSeriesSplit(n_splits=5)",
        "",
        "scores = cross_val_score(model, X, y, cv=cv, scoring='f1_macro')",
        "print(scores.mean(), '+/-', scores.std())",
    ], "Listing 3.1 - Choosing the splitter that matches your data's structure.")

    h2("Data leakage: the silent score inflator")
    p("Leakage is any situation where information that will not be available at "
      "prediction time influences training. It is the single most common reason a "
      "model that scored 0.97 offline scores 0.61 in production.")
    tbl(["Leak", "How it happens", "Fix"],
        [["Preprocessing leak", "Scaler, imputer or feature selector fitted on the "
          "whole dataset before splitting", "Fit inside a Pipeline, on training "
          "folds only"],
         ["Target leak", "A feature computed from the label, e.g. "
          "`total_paid` when predicting default", "Audit every feature: could I "
          "compute it at prediction time?"],
         ["Temporal leak", "Training on rows from after the prediction timestamp",
          "Split by time; build features with explicit as-of joins"],
         ["Group leak", "The same patient, user or device in train and test",
          "GroupKFold, or split by entity"],
         ["Duplicate leak", "Near-duplicate rows or images across splits",
          "Deduplicate, including perceptual near-duplicates"],
         ["Tuning leak", "Feature selection or hyperparameter search done before "
          "the split", "Everything data-dependent goes inside the CV loop"]],
        widths=[19, 45, 36], bold_first=True)

    h2("Learning curves: the diagnostic you should always plot")
    p("Plot training and validation error against the number of training samples. "
      "The shape tells you what to buy next:")
    tbl(["Shape", "Interpretation", "Action"],
        [["Both curves high and converged", "High bias; more data will not help",
          "Increase capacity or improve features"],
         ["Wide gap, validation still falling", "High variance; more data will help",
          "Collect or synthesise data; augment; regularise"],
         ["Validation rises after a point", "Overfitting with training duration",
          "Early stopping; stronger regularisation"],
         ["Both curves noisy", "Batch too small, learning rate too high, or the "
          "validation set is too small", "Enlarge the validation set; average over "
          "seeds"]],
        widths=[24, 38, 38], bold_first=True)

    ex_ch3()

    h2("No free lunch, and what it means for you")
    p("The **No Free Lunch theorem** says that averaged over all possible "
      "problems, every learning algorithm performs identically. That sounds "
      "nihilistic; it is not. Real problems are not drawn uniformly from all "
      "possible problems - they have structure: smoothness, locality, "
      "compositionality, translation invariance. An algorithm wins when its "
      "**inductive bias** matches the structure of your data. Convolutions "
      "encode locality and translation invariance; recurrence encodes sequential "
      "order; attention encodes 'any position may matter'; trees encode axis-"
      "aligned thresholds; L1 encodes 'few features matter'. Choosing a model is "
      "choosing an assumption.")

    h3("Exercises")
    bul([
        "Simulate the bias-variance decomposition: fit polynomials of degree "
        "1, 3, 9 to 30 noisy samples of sin(x), repeat over 200 resampled "
        "datasets, and plot bias^2, variance and total error against degree.",
        "Take any tabular dataset and deliberately introduce a target leak; "
        "measure the inflated CV score, then remove it and measure the honest one.",
        "Explain in two sentences why 10-fold CV on a dataset with 20 patients "
        "and 2,000 sensor windows is likely to overstate accuracy dramatically.",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 4 ---
    chapter("Data: Collection, Cleaning, Features and Splits")
    p("Models are interchangeable; data is not. Two teams using the same "
      "architecture but different data pipelines routinely differ by more than "
      "the gap between architectures. This chapter is the least glamorous and the "
      "highest-leverage in Part I.")

    h2("Types of data and what they demand")
    tbl(["Type", "Examples", "Preferred models", "Preprocessing"],
        [["Tabular numeric", "Sensor readings, prices", "GBDT, linear, MLP",
          "Scale for linear/NN; trees need nothing"],
         ["Tabular categorical", "Country, device type", "GBDT (native), NN with "
          "embeddings", "One-hot (low cardinality), target/embedding (high)"],
         ["Text", "Reviews, logs", "Transformers, TF-IDF + linear",
          "Tokenisation, subwords, truncation"],
         ["Images", "Photos, X-rays", "CNN, ViT", "Resize, normalise, augment"],
         ["Audio", "Speech, machine sound", "CNN on spectrogram, Conformer",
          "STFT / mel spectrogram, per-channel norm"],
         ["Time series", "IMU, ECG, demand", "GBDT on windows, 1D-CNN, LSTM",
          "Windowing, resampling, detrending"],
         ["Graphs", "Molecules, social", "GNN", "Adjacency, node features"]],
        widths=[16, 20, 30, 34], bold_first=True)

    h2("Cleaning: missing values, outliers, duplicates")
    h3("Missing data")
    bul([
        "**MCAR** (missing completely at random): dropping rows is unbiased but "
        "wasteful.",
        "**MAR** (missing at random given observed features): impute using the "
        "other features - iterative/MICE imputation, or k-NN imputation.",
        "**MNAR** (missing not at random): the fact of being missing carries "
        "information - always add a binary `was_missing` indicator column, because "
        "'income not stated' is itself predictive.",
    ])
    code([
        "from sklearn.pipeline import Pipeline",
        "from sklearn.compose import ColumnTransformer",
        "from sklearn.impute import SimpleImputer",
        "from sklearn.preprocessing import StandardScaler, OneHotEncoder",
        "",
        "num = Pipeline([('imp', SimpleImputer(strategy='median', add_indicator=True)),",
        "                ('sc',  StandardScaler())])",
        "cat = Pipeline([('imp', SimpleImputer(strategy='most_frequent')),",
        "                ('oh',  OneHotEncoder(handle_unknown='ignore',",
        "                                      min_frequency=10))])",
        "",
        "pre = ColumnTransformer([('num', num, numeric_cols),",
        "                         ('cat', cat, categorical_cols)])",
        "# pre is now a fit-on-train-only object; put it first in your model pipeline",
    ], "Listing 4.1 - Leak-proof preprocessing with ColumnTransformer.")

    h3("Outliers")
    p("Decide whether an extreme value is an **error** (a heart rate of 900 bpm) "
      "or a **rare truth** (a genuine 10x sale). Errors get removed or corrected; "
      "rare truths must stay, because they are often exactly what you are trying "
      "to detect. Detection tools: z-score for roughly Gaussian data, IQR fences "
      "for skewed data, isolation forest or local outlier factor for "
      "multivariate structure. Robust alternatives - median instead of mean, "
      "`RobustScaler`, Huber loss - are usually better than deletion.")

    h2("Scaling and transformation")
    tbl(["Transform", "Formula", "Use when"],
        [["Standardisation", "(x - mu) / sigma", "Default for linear models, SVM, "
          "PCA, neural nets"],
         ["Min-max", "(x - min) / (max - min)", "Bounded inputs, image pixels, "
          "when you need [0, 1]"],
         ["Robust", "(x - median) / IQR", "Heavy outliers present"],
         ["Log1p", "log(1 + x)", "Right-skewed positive quantities: counts, prices"],
         ["Box-Cox / Yeo-Johnson", "power transform", "Make a variable "
          "approximately Gaussian"],
         ["Quantile / rank", "map to uniform or normal", "Very non-linear "
          "distributions; robust to outliers"]],
        widths=[22, 26, 52], bold_first=True)
    box("warn", "Fit on train, apply to test - always",
        "`scaler.fit_transform(X_train)` then `scaler.transform(X_test)`. "
        "Calling fit on the test set - or on the full dataset before splitting - "
        "is leakage. Inside cross-validation the scaler must be refit on each "
        "training fold, which is exactly what a Pipeline does for you and what "
        "hand-rolled code usually gets wrong.")

    h2("Encoding categorical variables")
    bul([
        "**One-hot:** safe, interpretable, explodes with cardinality. Cap rare "
        "levels with `min_frequency`.",
        "**Ordinal:** only when the categories genuinely have an order (small < "
        "medium < large). Using it for unordered categories injects a false "
        "ranking that linear models will happily believe.",
        "**Target / mean encoding:** replace a category with the mean target for "
        "that category. Powerful for high cardinality, and a leakage magnet - it "
        "must be computed out-of-fold, with smoothing towards the global mean.",
        "**Hashing:** fixed-width, streaming-friendly, collisions are usually "
        "tolerable.",
        "**Learned embeddings:** map each level to a trainable dense vector. The "
        "standard approach inside neural networks, and how recommender systems "
        "represent millions of item IDs.",
    ])

    h2("Feature engineering that pays")
    bul([
        "**Domain ratios and differences:** debt/income, price per square metre, "
        "acceleration magnitude sqrt(ax^2+ay^2+az^2). Almost always beat raw "
        "columns.",
        "**Time features:** hour, day of week, is-holiday, and crucially cyclic "
        "encodings sin(2 pi h/24), cos(2 pi h/24) so that 23:00 is close to 01:00.",
        "**Lags and rolling windows** for time series: value at t-1, t-7; rolling "
        "mean, std, min, max, slope. Compute strictly with past data.",
        "**Aggregations across entities:** per-user mean, count, recency. This is "
        "where most of the signal lives in behavioural data.",
        "**Interactions:** explicit products x_i * x_j for linear models; trees "
        "and networks find them on their own.",
        "**Text:** TF-IDF n-grams for a strong cheap baseline; sentence embeddings "
        "when semantics matter.",
    ])
    box("tip", "Feature work versus model work",
        "On tabular problems, a day spent on features usually beats a week spent "
        "on architectures. On perceptual problems (images, audio, text), the "
        "reverse holds - the network learns better features than you can write, "
        "so spend the day on data quality, augmentation, and a better pretrained "
        "backbone instead.")

    h2("Class imbalance")
    p("When 1 in 500 transactions is fraud, accuracy is meaningless and most "
      "losses are dominated by the majority class. Options, roughly in order of "
      "what to try first:")
    bul([
        "Use the right metric: precision-recall AUC, F-beta, recall at fixed "
        "precision. Never accuracy.",
        "Class weights in the loss (`class_weight='balanced'`, "
        "`pos_weight` in PyTorch) - cheap and usually sufficient.",
        "Threshold tuning on the validation set: train normally, then choose the "
        "decision threshold that maximises your business metric. This is "
        "underused and often the single biggest win.",
        "Resampling: random undersampling of the majority, or SMOTE-style "
        "synthetic oversampling of the minority - only ever applied to the "
        "training fold, never to validation or test.",
        "Focal loss for extreme imbalance in detection tasks (Chapter 21).",
        "Reframe as anomaly detection if positives are both rare and diverse.",
    ])

    h2("Data augmentation")
    tbl(["Domain", "Standard augmentations", "Advanced"],
        [["Images", "Flip, crop, rotate, colour jitter, blur",
          "RandAugment, Mixup, CutMix, CutOut, copy-paste"],
         ["Audio", "Time shift, noise, gain, speed",
          "SpecAugment (mask time and frequency bands)"],
         ["Text", "Synonym swap, back-translation, dropout of tokens",
          "LLM paraphrase, EDA, span corruption"],
         ["Time series / IMU", "Jitter, scaling, time warping, window slicing",
          "Rotation of the sensor frame, magnitude warping, mixup"],
         ["Tabular", "Gaussian noise on numeric columns", "SMOTE, CTGAN, "
          "feature dropout"]],
        widths=[18, 42, 40], bold_first=True)
    box("key", "Augmentation encodes an invariance",
        "Every augmentation is a statement: 'the label does not change under this "
        "transformation'. Horizontal flip is right for cats and wrong for road "
        "signs with text; rotation is right for satellite images and wrong for "
        "handwritten digits (6 and 9). Choose augmentations that are true "
        "invariances of your task, and you are injecting free domain knowledge; "
        "choose false ones and you are injecting label noise.")

    ex_ch4()

    h2("Dataset documentation and ethics")
    bul([
        "Record provenance, collection dates, licences, consent, and known "
        "population gaps - a datasheet for the dataset.",
        "Check subgroup balance and measure performance per subgroup, not only "
        "in aggregate. A model can be 95% accurate overall and 60% accurate for "
        "one group.",
        "Remove or protect personal data; prefer aggregation, hashing, or "
        "on-device processing (Chapter 31) when the data is sensitive.",
        "Version datasets with the same rigour as code: a result you cannot "
        "reproduce because 'the data changed' is not a result.",
    ])

    h3("Exercises")
    bul([
        "Build a ColumnTransformer for a mixed dataset and confirm, by fitting on "
        "a subset, that no statistic of the test rows influences the transform.",
        "Take an imbalanced dataset, plot the precision-recall curve, and find "
        "the threshold that maximises recall subject to precision above 0.8.",
        "For a wearable-sensor dataset, list five window-level features you would "
        "compute and state, for each, why it is physically meaningful.",
    ], ordered=True)


# =============================================================================
#                        PART II - CLASSICAL MACHINE LEARNING
# =============================================================================
def part2():
    part("Classical Machine Learning",
         "The algorithms that still win on tabular data, and the ideas that every "
         "deep model inherits: linear models, trees, kernels, ensembles, "
         "clustering and honest evaluation.")

    # ---------------------------------------------------------------- Ch 5 ---
    chapter("Linear Regression, Derived Completely", newpage=False)
    p("Linear regression is worth studying far beyond its own usefulness: it is "
      "the smallest model in which every concept - parameters, loss, gradients, "
      "closed-form solutions, regularisation, and the geometry of fitting - "
      "appears in a form you can fully verify by hand.")

    h2("The model")
    eq(["y_hat = w_1 x_1 + w_2 x_2 + ... + w_d x_d + b   =   w . x + b",
        "",
        "with a bias column of ones:   y_hat = X w,   X in R^(n x (d+1))"])
    p("Folding the bias into the weight vector by appending a constant 1 feature "
      "keeps every formula below clean. The assumption embedded in this model is "
      "that the effect of each feature is additive and constant - one extra "
      "square metre adds the same amount of money whether the house is small or "
      "large. When that is false, you either transform features (log, splines, "
      "interactions) or move to a non-linear model.")

    h2("The loss and where it comes from")
    eq(["J(w) = (1/n) ||X w - y||^2 = (1/n) SUM_i (x_i . w - y_i)^2"])
    p("As shown in Chapter 2, squared error is the negative log-likelihood under "
      "Gaussian noise. That also tells you when it is the wrong choice: squared "
      "error punishes a single large error as much as many small ones, so "
      "outliers dominate the fit. Robust alternatives:")
    tbl(["Loss", "Formula", "Behaviour"],
        [["MSE", "(1/n) SUM (y - y_hat)^2", "Smooth; heavily influenced by outliers"],
         ["MAE", "(1/n) SUM |y - y_hat|", "Robust; estimates the median; not "
          "differentiable at 0"],
         ["Huber", "quadratic within delta, linear beyond", "Robust and smooth - "
          "usually the best default when outliers exist"],
         ["Quantile / pinball", "asymmetric absolute error", "Predicts a chosen "
          "quantile; the basis of prediction intervals"],
         ["Log-cosh", "log cosh(y - y_hat)", "Smooth approximation of Huber"]],
        widths=[16, 32, 52], bold_first=True)

    h2("Solution 1: the normal equations (closed form)")
    box("math", "Full derivation",
        "Write J(w) = (1/n)(Xw - y)^T (Xw - y) = (1/n)( w^T X^T X w - 2 w^T X^T y "
        "+ y^T y ). Differentiate with the matrix rules d(w^T A w)/dw = 2Aw for "
        "symmetric A, and d(w^T c)/dw = c. This gives grad J = (2/n)( X^T X w - "
        "X^T y ). Setting the gradient to zero gives the NORMAL EQUATIONS "
        "X^T X w = X^T y, whose solution is w = (X^T X)^-1 X^T y whenever X^T X "
        "is invertible.")
    eq("w* = (X^T X)^(-1) X^T y")
    p("Geometrically, `X w` ranges over the column space of X, and the best "
      "approximation to y in that subspace is its orthogonal projection - which "
      "is exactly what the normal equations state: the residual `Xw - y` is "
      "orthogonal to every column of X.")
    bul([
        "Cost is O(n d^2 + d^3): fine for d in the hundreds, hopeless for d in "
        "the millions.",
        "`X^T X` is singular when features are perfectly collinear or when d > n. "
        "Never invert it explicitly - use `numpy.linalg.lstsq` or a QR/SVD-based "
        "solver, which handle rank deficiency gracefully.",
        "Ridge regression fixes singularity outright: `w = (X^T X + lam I)^-1 X^T y` "
        "is always invertible for lam > 0 (Chapter 7).",
    ])

    h2("Solution 2: gradient descent (the scalable way)")
    eq(["grad J(w) = (2/n) X^T (X w - y)",
        "w <- w - eta * grad J(w)"])
    code([
        "import numpy as np",
        "",
        "def fit_linear_gd(X, y, lr=0.05, epochs=500, batch=64, seed=0):",
        "    rng = np.random.default_rng(seed)",
        "    n, d = X.shape",
        "    Xb = np.hstack([X, np.ones((n, 1))])          # bias trick",
        "    w = np.zeros(d + 1)",
        "    hist = []",
        "    for ep in range(epochs):",
        "        idx = rng.permutation(n)",
        "        for s in range(0, n, batch):",
        "            b = idx[s:s + batch]",
        "            resid = Xb[b] @ w - y[b]",
        "            grad = 2.0 / len(b) * Xb[b].T @ resid",
        "            w -= lr * grad",
        "        hist.append(np.mean((Xb @ w - y) ** 2))",
        "    return w, hist",
        "",
        "# Sanity check against the closed form on standardised data:",
        "# w_closed = np.linalg.lstsq(Xb, y, rcond=None)[0]",
    ], "Listing 5.1 - Mini-batch gradient descent for linear regression, 15 lines.")
    box("warn", "Feature scaling is not optional for gradient descent",
        "If one feature ranges over [0, 1] and another over [0, 100000], the loss "
        "surface is a long thin valley: the learning rate that is stable for the "
        "steep direction is far too small for the flat one, and training crawls. "
        "Standardise. The closed form does not care about scaling; gradient "
        "descent cares enormously.")

    h2("Interpreting and validating a linear model")
    h3("Coefficients")
    p("With standardised features, `w_j` is the expected change in y for a "
      "one-standard-deviation increase in feature j, **holding the other features "
      "fixed**. That last clause is where interpretations usually go wrong: with "
      "correlated features, the coefficients split the shared effect arbitrarily "
      "and can even flip sign. Check the **variance inflation factor**; a VIF "
      "above 5-10 signals multicollinearity, and ridge regularisation or dropping "
      "redundant features is the cure.")
    h3("Goodness of fit")
    eq(["R^2      = 1 - SS_res / SS_tot",
        "adj R^2  = 1 - (1 - R^2)(n - 1)/(n - d - 1)",
        "RMSE     = sqrt( (1/n) SUM (y - y_hat)^2 )     (same units as y)",
        "MAPE     = (100/n) SUM |y - y_hat| / |y|       (beware y near 0)"])
    p("R^2 always increases when you add features, which is why adjusted R^2 "
      "exists. Report RMSE or MAE alongside it - stakeholders understand 'the "
      "prediction is off by 12,000 EUR on average' far better than 'R^2 is 0.83'.")
    h3("Residual diagnostics")
    bul([
        "Residuals versus fitted values should look like a formless cloud. A "
        "funnel shape means **heteroscedasticity** - consider modelling log(y) or "
        "using weighted least squares.",
        "A curve in the residuals means a missing non-linearity - add a "
        "polynomial term, a spline, or switch to a tree model.",
        "A Q-Q plot far from the diagonal means non-Gaussian errors; prediction "
        "intervals from ordinary least squares will be wrong.",
        "Autocorrelated residuals in time series mean the model missed temporal "
        "structure; add lags.",
    ])

    h2("Polynomial and basis-function regression")
    p("Linear regression is linear **in the parameters**, not in the inputs. "
      "Replacing x by a basis expansion phi(x) keeps every formula above intact "
      "while fitting curves:")
    eq("y_hat = w_0 + w_1 phi_1(x) + ... + w_m phi_m(x)")
    bul([
        "Polynomials: simple, but high degrees oscillate wildly near the edges "
        "(Runge's phenomenon).",
        "Splines: piecewise polynomials with continuity constraints - far better "
        "behaved than a single high-degree polynomial and the standard choice in "
        "statistics.",
        "Radial basis functions: exp(-gamma ||x - c||^2) around chosen centres; "
        "this is the bridge to kernel methods in Chapter 10.",
    ])
    box("key", "The first appearance of the capacity dial",
        "Degree 1 underfits a curve; degree 15 on 20 points passes through every "
        "point and is useless between them. The degree is a hyperparameter, "
        "chosen on validation data, and it is the simplest possible instance of "
        "the bias-variance trade-off from Chapter 3.")

    ex_ch5()

    h2("From least squares to probability")
    p("Ordinary least squares gives a point prediction. Two upgrades are worth "
      "knowing:")
    bul([
        "**Bayesian linear regression** places a Gaussian prior on w and returns a "
        "posterior distribution rather than a point, giving calibrated predictive "
        "intervals that widen where data is sparse. With a Gaussian prior of "
        "variance tau^2 the posterior mean is exactly the ridge solution - "
        "regularisation is a prior in disguise.",
        "**Generalised linear models** keep the linear predictor `eta = w.x` and "
        "pass it through a link function: identity for regression, logit for "
        "binary classification (next chapter), log for Poisson counts. Same "
        "machinery, different noise assumption.",
    ])

    h3("Exercises")
    bul([
        "Implement the normal equations and compare against `lstsq` on a matrix "
        "with two perfectly correlated columns. Explain the failure.",
        "Fit polynomial degrees 1..15 on 25 noisy points from a cubic, plot train "
        "and validation RMSE, and identify the sweet spot.",
        "Derive the ridge solution by adding lam ||w||^2 to J and repeating the "
        "matrix derivation above.",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 6 ---
    chapter("Logistic and Softmax Regression")
    p("Despite the name, logistic regression is a **classifier**. It is the "
      "workhorse baseline for binary problems, the last layer of almost every "
      "neural classifier, and the cleanest place to learn cross-entropy and the "
      "logit view of probability.")

    h2("From linear score to probability")
    p("A linear model produces an unbounded score `z = w.x + b`, called the "
      "**logit**. The **sigmoid** squashes it into (0, 1):")
    eq(["sigma(z) = 1 / (1 + exp(-z))",
        "sigma'(z) = sigma(z) (1 - sigma(z))",
        "logit(p) = log( p / (1 - p) )      <- inverse of sigmoid"])
    diagram([
        "   1.0 |                          _______________",
        "       |                     ____/",
        "       |                 __/",
        "   0.5 |----------------/------------------------  sigma(0) = 0.5",
        "       |            __/",
        "       |      _____/",
        "   0.0 |_____/________________________________",
        "        -6    -4    -2     0     2     4     6      z",
    ], "Figure 6.1 - The logistic function: linear in the middle, saturating at the ends.")
    p("The saturation is important twice over: it keeps probabilities in range, "
      "and it causes **vanishing gradients** when |z| is large, because sigma' "
      "approaches zero. That is why sigmoid is no longer used as a hidden "
      "activation in deep networks (Chapter 16), only as an output.")

    h2("The loss: binary cross-entropy")
    box("math", "Derivation and the clean gradient",
        "Model P(y=1|x) = p = sigma(z). The Bernoulli likelihood of one sample is "
        "p^y (1-p)^(1-y). Taking the negative log gives "
        "L = -[ y log p + (1-y) log(1-p) ]. Now differentiate with respect to the "
        "LOGIT: dL/dp = -(y/p) + (1-y)/(1-p), and dp/dz = p(1-p). Multiplying, "
        "everything cancels: dL/dz = p - y. Therefore dL/dw = (p - y) x. The "
        "gradient is (prediction minus truth) times the input - identical in form "
        "to linear regression, and the reason cross-entropy pairs so well with "
        "sigmoid: the saturating derivative in the activation is cancelled by the "
        "logarithm in the loss.")
    eq(["J(w) = -(1/n) SUM_i [ y_i log p_i + (1 - y_i) log(1 - p_i) ]",
        "grad J = (1/n) X^T (p - y)"])
    box("warn", "Never square-error a classifier",
        "Using MSE with a sigmoid output multiplies the loss gradient by "
        "sigma'(z), which is near zero exactly when the model is confidently "
        "wrong - so the worst mistakes produce the smallest updates and learning "
        "stalls. Cross-entropy removes that factor. Also: always feed raw logits "
        "to `BCEWithLogitsLoss` / `CrossEntropyLoss` rather than applying sigmoid "
        "or softmax yourself, so the library can use the numerically stable "
        "formulation.")

    h2("Multiclass: softmax regression")
    eq(["z = W x + b,      z in R^K",
        "softmax(z)_k = exp(z_k) / SUM_j exp(z_j)",
        "L = -SUM_k y_k log softmax(z)_k = -log softmax(z)_[true class]",
        "dL/dz = softmax(z) - y      (one-hot y)"])
    p("Softmax is the natural generalisation of sigmoid to K classes, and the "
      "gradient keeps the same beautiful form. Two practical notes: softmax is "
      "shift-invariant, `softmax(z + c) = softmax(z)`, which is what makes the "
      "max-subtraction trick safe; and the outputs are coupled - raising one "
      "logit lowers every other probability. For **multi-label** problems, where "
      "several classes can be true at once, use K independent sigmoids instead.")
    code([
        "import numpy as np",
        "",
        "def softmax(Z):                       # Z: (n, K) logits",
        "    Z = Z - Z.max(axis=1, keepdims=True)      # numerical stability",
        "    E = np.exp(Z)",
        "    return E / E.sum(axis=1, keepdims=True)",
        "",
        "def fit_softmax(X, Y1h, lr=0.1, epochs=200, l2=1e-4):",
        "    n, d = X.shape; K = Y1h.shape[1]",
        "    W = np.zeros((d, K)); b = np.zeros(K)",
        "    for _ in range(epochs):",
        "        P = softmax(X @ W + b)",
        "        G = (P - Y1h) / n                     # dL/dz, the whole trick",
        "        W -= lr * (X.T @ G + l2 * W)",
        "        b -= lr * G.sum(axis=0)",
        "    return W, b",
    ], "Listing 6.1 - Softmax regression in NumPy; this is also the output layer of "
       "every classification network in Part III.")

    h2("Decision boundary, odds, and interpretation")
    p("The boundary is the set where `p = 0.5`, i.e. `w.x + b = 0` - a hyperplane. "
      "Logistic regression can therefore only separate classes linearly; curved "
      "boundaries require feature expansion or a non-linear model. Its "
      "interpretability comes from odds:")
    eq(["log( p / (1-p) ) = w.x + b",
        "exp(w_j) = odds ratio: the multiplicative change in odds per unit of x_j"])
    p("A coefficient of 0.7 on 'smoker' means the odds of the outcome are "
      "exp(0.7) = 2.0 times higher for smokers, all else equal. This direct "
      "reading is why logistic regression remains the standard model in medicine, "
      "credit scoring and any regulated setting.")

    ex_ch6()

    h2("Practical matters")
    bul([
        "**Regularisation is on by default** in scikit-learn (`C` is the inverse "
        "of the penalty strength). With separable data and no penalty, weights "
        "diverge to infinity - the likelihood keeps improving as the margin grows.",
        "**Solvers:** `lbfgs` for small dense problems, `saga` for large sparse "
        "ones or L1/elastic-net penalties, `liblinear` for small L1 problems.",
        "**Class imbalance:** `class_weight='balanced'` reweights the loss; then "
        "tune the decision threshold on validation data rather than accepting 0.5.",
        "**Calibration:** logistic regression is usually well calibrated out of "
        "the box, which is exactly why Platt scaling - fitting a logistic "
        "regression on another model's scores - is the standard calibration "
        "method (Chapter 13).",
        "**Multiclass strategies:** true multinomial softmax is preferred; "
        "one-vs-rest trains K binary models and is a reasonable fallback for "
        "models that cannot do multinomial natively.",
    ])

    h3("Exercises")
    bul([
        "Derive dL/dz = p - y for softmax by differentiating log-sum-exp. Watch "
        "the two cases k = true class and k != true class.",
        "Train logistic regression on a linearly separable 2-D dataset with the "
        "penalty switched off and plot the norm of w against iterations.",
        "Fit a logistic model on an imbalanced dataset, then sweep the threshold "
        "from 0 to 1 and plot precision and recall against it.",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 7 ---
    chapter("Regularization and Model Selection")
    p("Regularisation is any modification to a learning algorithm intended to "
      "reduce test error but not training error. It is how you buy generalisation "
      "when you cannot buy more data.")

    h2("Penalty-based regularisation")
    eq(["Ridge  (L2):    J = MSE + lam * SUM_j w_j^2",
        "Lasso  (L1):    J = MSE + lam * SUM_j |w_j|",
        "Elastic net:    J = MSE + lam * ( a * SUM |w_j| + (1-a) * SUM w_j^2 )"])
    tbl(["Property", "Ridge (L2)", "Lasso (L1)"],
        [["Effect on coefficients", "Shrinks all towards zero, none exactly zero",
          "Drives many exactly to zero"],
         ["Feature selection", "No", "Yes - built in"],
         ["Correlated features", "Splits weight evenly among them",
          "Arbitrarily picks one, drops the rest"],
         ["Solution", "Closed form: (X^T X + lam I)^-1 X^T y",
          "No closed form; coordinate descent or proximal methods"],
         ["Bayesian reading", "Gaussian prior on w", "Laplace prior on w"],
         ["When to prefer", "Many small effects, multicollinearity",
          "You believe few features matter and want a sparse model"]],
        widths=[24, 38, 38], bold_first=True)
    box("math", "Why L1 produces exact zeros",
        "Think of the constrained form: minimise MSE subject to ||w||_1 <= t. The "
        "L1 ball is a diamond with corners ON the axes; the elliptical contours of "
        "the MSE touch it, in general, at a corner - and a corner has one or more "
        "coordinates exactly zero. The L2 ball is round, has no corners, and the "
        "contact point almost never lies on an axis. Equivalently: the "
        "subgradient of |w| is a constant +/-1 all the way to zero, so shrinkage "
        "does not weaken as w gets small, whereas the L2 gradient 2w fades away.")
    diagram([
        "        L2 (ridge)                      L1 (lasso)",
        "        w2                              w2",
        "        |    ,--.                       |     /\\",
        "        |   /    \\   .-- MSE contours   |    /  \\   .-- MSE contours",
        "        |  (  o   )                     |   <    >",
        "        |   \\    /                      |    \\  /",
        "     ---+----`--'------ w1           ---+-----\\/------- w1",
        "        contact off-axis                 contact AT a corner => w1 = 0",
    ], "Figure 7.1 - The geometry that makes lasso a feature selector.")

    h2("Other forms of regularisation")
    bul([
        "**Early stopping:** stop when validation loss stops improving. For linear "
        "models trained by gradient descent this is provably similar to L2.",
        "**Data augmentation:** more effective than any penalty when you can "
        "define true invariances (Chapter 4).",
        "**Noise injection:** adding Gaussian noise to inputs is equivalent to L2 "
        "on the weights for linear models; adding it to weights or activations "
        "flattens the minima found.",
        "**Dropout, label smoothing, weight decay, stochastic depth:** the "
        "deep-learning-specific toolkit, Chapter 19.",
        "**Ensembling:** averaging independently trained models reduces variance "
        "directly, Chapter 11.",
        "**Parameter sharing:** convolution is a hard constraint that the same "
        "weights apply everywhere - one of the strongest regularisers in "
        "existence, and it is architectural rather than a penalty.",
    ])

    h2("Choosing hyperparameters")
    tbl(["Method", "How it works", "When to use"],
        [["Grid search", "Exhaustive over a discrete grid",
          "Few hyperparameters (<= 3), cheap models"],
         ["Random search", "Sample from distributions for a fixed budget",
          "The right default: better than grid when only a few dimensions matter"],
         ["Bayesian optimisation", "Fit a surrogate model of the objective, "
          "sample where improvement is expected (Optuna, scikit-optimize)",
          "Expensive training runs, many hyperparameters"],
         ["Hyperband / ASHA", "Start many configs, kill the weak ones early",
          "Deep learning, where a bad config is obvious after 2 epochs"],
         ["Population-based training", "Evolve a population, copy and perturb "
          "winners", "Long RL and large-model runs with schedules"]],
        widths=[20, 46, 34], bold_first=True)
    box("tip", "Search in log space, and search the right things",
        "Learning rate, regularisation strength and layer widths should be "
        "sampled log-uniformly (1e-5 to 1e-1), not uniformly. Random search "
        "beats grid search because performance usually depends strongly on one or "
        "two hyperparameters and weakly on the rest - random search gives you many "
        "distinct values of the important one, grid search wastes the budget "
        "repeating them.")
    code([
        "import numpy as np, optuna",
        "from sklearn.model_selection import cross_val_score, StratifiedKFold",
        "from sklearn.ensemble import HistGradientBoostingClassifier",
        "",
        "def objective(trial):",
        "    params = dict(",
        "        learning_rate = trial.suggest_float('lr', 1e-3, 3e-1, log=True),",
        "        max_leaf_nodes= trial.suggest_int('leaves', 8, 256, log=True),",
        "        min_samples_leaf = trial.suggest_int('min_leaf', 5, 200, log=True),",
        "        l2_regularization= trial.suggest_float('l2', 1e-8, 10.0, log=True),",
        "        max_iter = 500)",
        "    model = HistGradientBoostingClassifier(early_stopping=True, **params)",
        "    cv = StratifiedKFold(5, shuffle=True, random_state=0)",
        "    return cross_val_score(model, X, y, cv=cv, scoring='roc_auc').mean()",
        "",
        "study = optuna.create_study(direction='maximize')",
        "study.optimize(objective, n_trials=60, n_jobs=4)",
        "print(study.best_params, round(study.best_value, 4))",
    ], "Listing 7.1 - Bayesian hyperparameter search with correct log-scale ranges.")

    h2("Model selection criteria without a validation set")
    eq(["AIC = 2k - 2 log L         (prediction-oriented)",
        "BIC = k log n - 2 log L    (penalises complexity harder; consistent)",
        "MDL: choose the model that compresses data + model description best"])
    p("These are useful when data is too scarce to hold out, and in classical "
      "statistics generally. In modern practice, cross-validation is preferred "
      "because it makes no distributional assumptions - but AIC/BIC remain the "
      "standard in time-series order selection and in fields where models are "
      "fitted by maximum likelihood.")

    h2("A disciplined selection protocol")
    checklist("Before you report a number", [
        "The test set was split off before any exploration and touched once.",
        "Every data-dependent step (imputation, scaling, selection, encoding) "
        "lives inside the cross-validation loop.",
        "Hyperparameters were chosen on validation folds, not on the test set.",
        "Results are averaged over at least 3-5 random seeds, and you report the "
        "spread, not only the mean.",
        "You compare against a trivial baseline (majority class, mean predictor, "
        "last-value-carried-forward) and a simple strong baseline (ridge or "
        "gradient boosting).",
        "The difference you are claiming is larger than the seed-to-seed noise.",
    ])

    h3("Exercises")
    bul([
        "Plot the lasso regularisation path (coefficients versus lam) on a "
        "dataset with 20 features, 5 of which are informative.",
        "Compare grid search and random search on the same budget of 50 trials "
        "for a model with 4 hyperparameters, one of which is irrelevant.",
        "Show empirically that ridge with lam -> 0 recovers ordinary least "
        "squares, and that lam -> infinity drives predictions to the mean.",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 8 ---
    chapter("Instance-Based and Probabilistic Models")
    h2("k-Nearest Neighbours")
    p("k-NN does no training at all. To predict, it finds the k closest training "
      "samples and takes a majority vote (classification) or an average "
      "(regression). It is the purest form of **non-parametric** learning: the "
      "training data __is__ the model.")
    eq(["y_hat(x) = majority{ y_i : x_i in N_k(x) }        (classification)",
        "y_hat(x) = (1/k) SUM_(i in N_k(x)) y_i            (regression)"])
    tbl(["Aspect", "Detail"],
        [["Hyperparameters", "k, distance metric, weighting (uniform or 1/d)"],
         ["k small", "Low bias, high variance; k = 1 fits training data perfectly "
          "and is very sensitive to noise"],
         ["k large", "High bias, low variance; k = n predicts the global mean"],
         ["Distance", "Euclidean by default; Manhattan for high dimensions; "
          "cosine for embeddings and text; Hamming for binary"],
         ["Cost", "O(1) to train, O(n d) per query - the opposite profile of most "
          "models. KD-trees and ball-trees help in low dimensions; HNSW and IVF "
          "indexes are what production vector search actually uses"],
         ["Must-do", "Scale the features. An unscaled feature with a large range "
          "silently dominates the distance"]],
        widths=[22, 78], bold_first=True)
    box("warn", "The curse of dimensionality, concretely",
        "In high dimensions, all pairwise distances concentrate: the ratio "
        "(farthest - nearest)/nearest tends to zero as d grows. With d = 100 "
        "roughly uniform features, 'nearest neighbour' stops meaning anything. "
        "Also, to keep the same density you need exponentially more samples: "
        "covering [0,1]^d at resolution 0.1 requires 10^d points. k-NN is "
        "excellent for d up to about 10-20 with enough data, and unreliable far "
        "beyond that unless you first reduce dimensionality or use a learned "
        "embedding.")
    p("k-NN is still deeply relevant: retrieval-augmented generation, "
      "recommendation, deduplication, few-shot classification with foundation-"
      "model embeddings, and face recognition are all approximate nearest "
      "neighbour search over learned vectors. The lesson is that k-NN works "
      "wonderfully **once the representation is good** - which is exactly what "
      "deep learning provides.")

    h2("Naive Bayes")
    p("A generative classifier built directly on Bayes' rule, with one strong "
      "simplifying assumption: features are conditionally independent given the "
      "class.")
    eq(["P(y | x) proportional to P(y) PROD_j P(x_j | y)",
        "y_hat = argmax_y [ log P(y) + SUM_j log P(x_j | y) ]"])
    bul([
        "**Gaussian NB:** each P(x_j | y) is a normal distribution - continuous "
        "features.",
        "**Multinomial NB:** counts - the classic text classifier over bag-of-"
        "words.",
        "**Bernoulli NB:** binary presence/absence features.",
        "**Laplace (add-one) smoothing** is mandatory: a single unseen "
        "word-class pair would otherwise make the whole product zero.",
    ])
    p("The independence assumption is almost always false, yet Naive Bayes often "
      "classifies well, because it only needs the __argmax__ to be right, not the "
      "probabilities. Its probability estimates, however, are badly calibrated - "
      "typically pushed towards 0 or 1. Use it as a fast baseline on text, as a "
      "component in streaming systems, or when you have very little data; do not "
      "trust its confidence values without calibration.")
    code([
        "from sklearn.feature_extraction.text import TfidfVectorizer",
        "from sklearn.naive_bayes import MultinomialNB",
        "from sklearn.pipeline import make_pipeline",
        "",
        "clf = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2,",
        "                                    sublinear_tf=True),",
        "                    MultinomialNB(alpha=0.3))       # alpha = smoothing",
        "clf.fit(train_texts, train_labels)",
        "# Trains on 100k documents in about a second and is a genuinely strong",
        "# baseline that any transformer should be required to beat.",
    ], "Listing 8.1 - The five-second text-classification baseline.")

    h2("Linear and quadratic discriminant analysis")
    p("LDA models each class as a Gaussian with a **shared** covariance matrix; "
      "the resulting decision boundary is linear. QDA gives each class its own "
      "covariance and yields quadratic boundaries at the cost of many more "
      "parameters. LDA doubles as a supervised dimensionality reduction method: "
      "it projects onto at most K-1 directions that maximise between-class "
      "scatter relative to within-class scatter - a useful contrast with PCA, "
      "which ignores labels entirely (Chapter 12).")

    h3("Exercises")
    bul([
        "Plot k-NN test accuracy against k from 1 to 50 and mark the "
        "bias-variance regimes on the curve.",
        "Demonstrate distance concentration: sample 1,000 points uniformly in "
        "[0,1]^d for d = 2, 10, 100, 1000 and plot the ratio of maximum to "
        "minimum pairwise distance.",
        "Compare Multinomial Naive Bayes and logistic regression on a text "
        "dataset of 1,000 documents and again on 100,000 - explain the crossover.",
    ], ordered=True)


    # ---------------------------------------------------------------- Ch 9 ---
    chapter("Decision Trees")
    p("A decision tree asks a sequence of yes/no questions about the features "
      "until it reaches a leaf that holds a prediction. It is the only major "
      "model whose reasoning a non-technical stakeholder can read directly - and "
      "it is the building block of the ensembles in Chapter 11, which are still "
      "the best general-purpose tabular models available.")
    diagram([
        "                       [ age < 45 ? ]",
        "                       /            \\",
        "                    yes              no",
        "                    /                  \\",
        "        [ income < 30k ? ]         [ smoker ? ]",
        "          /         \\                /       \\",
        "        yes          no            yes        no",
        "        /              \\            /           \\",
        "   pred = 0.12     pred = 0.34   pred = 0.71   pred = 0.28",
    ], "Figure 9.1 - A depth-2 tree partitions feature space into axis-aligned boxes.")

    h2("How a split is chosen")
    p("At each node the algorithm considers every feature and every candidate "
      "threshold, and picks the split that most reduces an impurity measure. "
      "Cost is O(n d log n) per level with sorted features.")
    eq(["Gini      G = 1 - SUM_k p_k^2",
        "Entropy   H = -SUM_k p_k log2 p_k",
        "Gain      IG = Impurity(parent) - SUM_child (n_child/n_parent) * Impurity(child)",
        "Regression: MSE reduction, i.e. variance reduction"])
    box("math", "A concrete split calculation",
        "A node has 100 samples: 60 positive, 40 negative. Gini = 1 - (0.6^2 + "
        "0.4^2) = 0.48. A candidate split gives child A with 50 samples (45 pos, "
        "5 neg, Gini = 1 - 0.9^2 - 0.1^2 = 0.18) and child B with 50 samples "
        "(15 pos, 35 neg, Gini = 1 - 0.3^2 - 0.7^2 = 0.42). Weighted child "
        "impurity = 0.5*0.18 + 0.5*0.42 = 0.30, so the gain is 0.18. The split "
        "with the largest gain across all features and thresholds wins.")
    p("Gini and entropy almost always select the same splits; Gini is marginally "
      "cheaper (no logarithm) and is the default in most libraries. Neither is "
      "worth tuning.")

    h2("Controlling growth")
    p("An unconstrained tree grows until every leaf is pure - it memorises the "
      "training set and has near-zero bias and enormous variance. Control it "
      "with:")
    tbl(["Hyperparameter", "Effect", "Sensible start"],
        [["max_depth", "Hard cap on tree depth", "3-10 for a single tree"],
         ["min_samples_leaf", "Minimum samples in a leaf; the most effective "
          "single knob", "1-5% of n"],
         ["min_samples_split", "Minimum samples required to split a node", "20+"],
         ["max_features", "Features considered per split - the source of diversity "
          "in random forests", "sqrt(d) for classification"],
         ["ccp_alpha", "Cost-complexity (post-)pruning strength", "Tune by CV"],
         ["max_leaf_nodes", "Best-first growth with a leaf budget", "31-255 in "
          "boosting"]],
        widths=[22, 52, 26], bold_first=True)
    p("**Cost-complexity pruning** grows a large tree, then removes the subtree "
      "whose removal costs the least error per removed leaf, using "
      "`R_alpha(T) = R(T) + alpha |leaves(T)|`. Sweeping alpha produces a nested "
      "sequence of trees; cross-validation picks one. Post-pruning generally "
      "beats early stopping, because a weak split can enable a strong one "
      "beneath it.")

    h2("Strengths, weaknesses, and the properties that matter downstream")
    tbl(["Strengths", "Weaknesses"],
        [["No scaling or normalisation needed", "High variance: a small data "
          "change can restructure the whole tree"],
         ["Handles mixed numeric and categorical data", "Axis-aligned splits only; "
          "a diagonal boundary needs a staircase of splits"],
         ["Captures interactions and non-linearities automatically",
          "Cannot extrapolate beyond the training range - predictions are constant "
          "outside it"],
         ["Robust to outliers in the inputs", "Biased towards features with many "
          "distinct values when using naive impurity gain"],
         ["Missing values handled natively in modern implementations",
          "A single tree rarely competitive alone - use ensembles"]],
        widths=[50, 50])
    box("key", "Why trees dominate tabular data",
        "Real tabular features are heterogeneous - different units, skewed "
        "distributions, irrelevant columns, non-smooth relationships with "
        "thresholds ('approve if credit score above 700'). Trees are invariant to "
        "monotone transformations of each feature, ignore irrelevant features "
        "cheaply, and model thresholds exactly. Neural networks have to learn all "
        "of that from data, which is why they need more of it to reach the same "
        "point on tabular problems.")

    ex_ch9()

    h2("Feature importance - and how it misleads")
    bul([
        "**Impurity-based (Gini) importance:** free, but biased towards "
        "high-cardinality and continuous features, and computed on training data. "
        "Treat it as a rough hint only.",
        "**Permutation importance:** shuffle one column on held-out data and "
        "measure the drop in score. Model-agnostic and much more trustworthy; "
        "but correlated features share credit and can both appear unimportant.",
        "**SHAP values:** a game-theoretic attribution with strong consistency "
        "guarantees, with an exact fast algorithm for trees (TreeSHAP). The "
        "current standard for explaining tabular models, both globally and per "
        "prediction (Chapter 33).",
    ])
    code([
        "from sklearn.inspection import permutation_importance",
        "r = permutation_importance(model, X_val, y_val, n_repeats=20,",
        "                           scoring='roc_auc', random_state=0)",
        "order = r.importances_mean.argsort()[::-1]",
        "for i in order[:10]:",
        "    print(f'{feature_names[i]:30s} {r.importances_mean[i]:.4f}'",
        "          f' +/- {r.importances_std[i]:.4f}')",
    ], "Listing 9.1 - Permutation importance measured on validation data.")

    h3("Exercises")
    bul([
        "Implement CART for classification in NumPy: recursive best-split search "
        "with Gini, plus max_depth and min_samples_leaf. 80 lines is enough.",
        "Fit an unpruned tree and a pruned one on the same data and compare "
        "training/test accuracy and the number of leaves.",
        "Show that a decision tree cannot represent y = (x1 > x2) compactly, and "
        "explain what feature you would add to fix it.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 10 ---
    chapter("Support Vector Machines and Kernels")
    p("SVMs were the state of the art before deep learning, and they remain the "
      "best explanation of two ideas that keep reappearing: **margin** as a "
      "principled notion of confidence, and the **kernel trick** as a way to work "
      "in a high-dimensional space without ever visiting it.")

    h2("Maximum margin classification")
    p("Among the infinitely many hyperplanes that separate two classes, the SVM "
      "chooses the one whose distance to the nearest point of either class - the "
      "**margin** - is largest. A large margin is a robustness statement: the "
      "boundary can tolerate perturbation before misclassifying anything.")
    diagram([
        "        o   o          |<-- margin -->|",
        "     o    o    o    ---+----------+---+---",
        "        o    o        SV|          |  |SV",
        "  ------------------- boundary ----+----------------",
        "                        |          |",
        "                     x  |  x     x |     x   x",
        "                      SV|          |",
        "   Only the support vectors (SV) touch the margin and define the boundary.",
    ], "Figure 10.1 - The maximum-margin hyperplane and its support vectors.")
    eq(["minimise   (1/2)||w||^2",
        "subject to y_i (w . x_i + b) >= 1   for all i           (hard margin)",
        "",
        "geometric margin = 2 / ||w||       -> maximising margin = minimising ||w||"])
    p("Real data is rarely separable, so slack variables xi_i allow violations, "
      "penalised by C:")
    eq(["minimise (1/2)||w||^2 + C SUM_i xi_i,   y_i(w.x_i + b) >= 1 - xi_i,  xi_i >= 0",
        "",
        "equivalently   min  (1/2)||w||^2 + C SUM_i max(0, 1 - y_i f(x_i))"])
    p("That second form shows the SVM is just a linear model with **hinge loss** "
      "and L2 regularisation. Large C means little regularisation (fit the "
      "training data hard); small C means a wide, soft margin. C is the "
      "hyperparameter that matters most.")

    h2("The dual problem and the kernel trick")
    box("math", "Why the dual matters",
        "Introducing Lagrange multipliers alpha_i for the margin constraints and "
        "eliminating w and b gives the dual: maximise SUM alpha_i - (1/2) SUM_ij "
        "alpha_i alpha_j y_i y_j (x_i . x_j), subject to 0 <= alpha_i <= C and SUM "
        "alpha_i y_i = 0. The data appears ONLY through inner products x_i . x_j. "
        "So if you replace that inner product with any function K(x_i, x_j) that "
        "equals an inner product in some (possibly infinite-dimensional) feature "
        "space, you get a non-linear classifier at no extra representational "
        "cost. Also, alpha_i is non-zero only for support vectors - the solution "
        "is sparse in the training set.")
    eq(["f(x) = SUM_i alpha_i y_i K(x_i, x) + b"])
    tbl(["Kernel", "K(a, b)", "Character"],
        [["Linear", "a . b", "Text, very high-dimensional sparse data"],
         ["Polynomial", "(gamma a.b + r)^p", "Explicit interactions up to degree p"],
         ["RBF / Gaussian", "exp(-gamma ||a - b||^2)", "The default; infinite-"
          "dimensional feature space, local influence"],
         ["Sigmoid", "tanh(gamma a.b + r)", "Rarely used; not always a valid kernel"],
         ["String / graph kernels", "domain-specific", "Structured inputs without "
          "vectorisation"]],
        widths=[20, 30, 50], bold_first=True)
    p("A valid kernel must produce a positive semi-definite Gram matrix "
      "(Mercer's condition). For the RBF kernel, gamma sets the radius of "
      "influence of each support vector: large gamma means very local, wiggly "
      "boundaries and overfitting; small gamma approaches a linear model. Tune "
      "**C and gamma jointly on a log grid** - they interact strongly.")

    h2("Practical guidance")
    bul([
        "**Always scale features.** RBF distances are meaningless otherwise.",
        "Training cost is between O(n^2) and O(n^3): SVMs are excellent up to "
        "roughly 10^4-10^5 samples and impractical beyond. For large n use "
        "`LinearSVC`, SGD with hinge loss, or random-feature approximations "
        "(Nystroem, Random Fourier Features) which approximate the kernel map "
        "explicitly and restore linear cost.",
        "**SVR** (support vector regression) uses an epsilon-insensitive tube: "
        "errors smaller than epsilon cost nothing, which yields sparse, robust "
        "regression.",
        "**One-class SVM** learns the support of a distribution and is a classical "
        "anomaly detector.",
        "SVMs output distances, not probabilities. `probability=True` fits Platt "
        "scaling internally, which requires an extra internal cross-validation - "
        "it is slow and often better done explicitly (Chapter 13).",
    ])
    box("expert", "Hinge loss versus cross-entropy",
        "Hinge loss is exactly zero once a point is correctly classified with "
        "margin at least 1, so well-classified points stop contributing - hence "
        "sparsity in the support vectors. Cross-entropy never reaches zero and "
        "keeps pushing confident points further, which is why logistic models "
        "produce calibrated probabilities while SVMs produce good boundaries. "
        "Choose by what you need: a decision or a probability.")

    h3("Exercises")
    bul([
        "On a 2-D toy dataset, plot the RBF-SVM decision boundary for gamma in "
        "{0.01, 0.1, 1, 10} and C in {0.1, 1, 100}. Identify overfitting visually.",
        "Verify the dual sparsity claim: count support vectors as C decreases.",
        "Approximate an RBF kernel with `Nystroem` plus `LinearSVC` and compare "
        "accuracy and training time against the exact `SVC` on 20,000 samples.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 11 ---
    chapter("Ensembles: Bagging, Random Forests and Boosting")
    p("An ensemble combines many models into one predictor that is better than "
      "any member. There are two fundamentally different recipes, and the "
      "bias-variance decomposition of Chapter 3 tells you exactly what each one "
      "is for.")
    tbl(["Family", "Members are", "Trained", "Attacks", "Examples"],
        [["Bagging", "Strong, low-bias, high-variance", "In parallel, independently",
          "Variance", "Random forest, extra trees"],
         ["Boosting", "Weak, high-bias", "Sequentially, each fixing the last",
          "Bias (and variance, via shrinkage)", "AdaBoost, GBM, XGBoost, LightGBM"],
         ["Stacking", "Diverse model types", "Level-0 in parallel, level-1 on "
          "out-of-fold predictions", "Both", "Any blend + a meta-learner"]],
        widths=[14, 22, 26, 20, 18], bold_first=True)

    h2("Why averaging works")
    box("math", "The variance reduction formula",
        "Average M models each with variance s^2 and pairwise correlation rho. "
        "The variance of the average is rho*s^2 + (1 - rho) s^2 / M. As M grows "
        "the second term vanishes, but the first does not: the floor is set by how "
        "CORRELATED the members are. This single formula explains the entire "
        "design of random forests - every mechanism in them exists to lower rho.")

    h2("Bagging and random forests")
    bul([
        "**Bootstrap sample:** draw n samples with replacement; about 63.2% of the "
        "rows appear, the rest are **out-of-bag** and give a free validation "
        "estimate.",
        "**Feature subsampling at each split** (`max_features = sqrt(d)` for "
        "classification, `d/3` for regression) is what separates a random forest "
        "from plain bagged trees; it decorrelates the trees strongly.",
        "**Extra trees** go further: thresholds are drawn at random rather than "
        "optimised. Higher bias, much lower variance and much faster.",
        "Trees are grown deep and unpruned - variance is handled by the average, "
        "not by pruning each member.",
        "More trees never hurt accuracy, only time; 300-1,000 is typical, and the "
        "curve flattens.",
    ])
    p("Random forests are the best 'no-thought' baseline in existence: they need "
      "no scaling, tolerate irrelevant features, rarely overfit catastrophically, "
      "and their default hyperparameters are usually within a few percent of "
      "tuned performance.")

    h2("Boosting, from AdaBoost to gradient boosting")
    h3("AdaBoost, the original idea")
    p("Train a weak learner; increase the weights of the samples it got wrong; "
      "train the next learner on the reweighted data; repeat; combine with "
      "weights based on each learner's accuracy. AdaBoost was later shown to be "
      "gradient descent on the **exponential loss** in function space - which "
      "opened the door to the general framework.")
    h3("Gradient boosting, stated properly")
    p("Build an additive model `F_M(x) = SUM_m nu * h_m(x)`. At each stage, fit "
      "the next weak learner to the **negative gradient of the loss with respect "
      "to the current predictions** - the pseudo-residuals:")
    eq(["r_im = - [ dL(y_i, F(x_i)) / dF(x_i) ]_(F = F_(m-1))",
        "h_m  = argmin_h SUM_i ( r_im - h(x_i) )^2        (fit a tree to residuals)",
        "F_m  = F_(m-1) + nu * gamma_m * h_m              (nu = learning rate)"])
    p("With squared loss the pseudo-residuals are the ordinary residuals, which "
      "is the intuition most people learn first: each new tree predicts what the "
      "current ensemble is still getting wrong. Because the recipe only needs a "
      "gradient, the same algorithm works for logistic loss, Poisson loss, "
      "quantile loss, ranking losses and custom business losses.")
    box("key", "Shrinkage and the number of trees trade off",
        "The learning rate nu (shrinkage) and the number of trees M are coupled: "
        "halving nu roughly doubles the M you need. Small nu (0.01-0.1) with many "
        "trees and early stopping on a validation set generalises better than "
        "large nu with few trees. This pair, plus tree depth, is 80% of gradient "
        "boosting tuning.")

    h2("Modern implementations")
    tbl(["Library", "Distinctive ideas", "Best for"],
        [["XGBoost", "Second-order (Newton) boosting with an explicit "
          "regularisation term, sparsity-aware split finding, weighted quantile "
          "sketch", "Strong all-rounder, huge ecosystem"],
         ["LightGBM", "Histogram binning, leaf-wise growth, GOSS sampling, EFB "
          "feature bundling", "Very large datasets; usually the fastest"],
         ["CatBoost", "Ordered boosting to remove target leakage, native "
          "categorical handling with ordered target statistics, oblivious trees",
          "Many categorical features; least tuning needed"],
         ["scikit-learn HistGBDT", "LightGBM-style histograms in scikit-learn",
          "Zero extra dependencies"]],
        widths=[16, 54, 30], bold_first=True)
    code([
        "import lightgbm as lgb",
        "",
        "params = dict(objective='binary', metric='auc',",
        "              learning_rate=0.03,      # small + many rounds + early stop",
        "              num_leaves=63,           # capacity; 2^depth is the cap",
        "              min_data_in_leaf=50,     # main overfitting control",
        "              feature_fraction=0.8,    # column subsampling per tree",
        "              bagging_fraction=0.8, bagging_freq=1,   # row subsampling",
        "              lambda_l2=1.0, verbose=-1)",
        "",
        "dtr = lgb.Dataset(X_tr, y_tr)",
        "dva = lgb.Dataset(X_va, y_va, reference=dtr)",
        "model = lgb.train(params, dtr, num_boost_round=5000,",
        "                  valid_sets=[dva],",
        "                  callbacks=[lgb.early_stopping(200),",
        "                             lgb.log_evaluation(200)])",
        "print('best iteration:', model.best_iteration)",
    ], "Listing 11.1 - A gradient-boosting configuration that is hard to beat on "
       "tabular data.")

    ex_ch11()

    h2("Stacking and blending")
    p("Train diverse level-0 models (a GBDT, a linear model, a k-NN, a small "
      "neural net), collect their **out-of-fold** predictions as new features, and "
      "train a simple level-1 model - usually regularised logistic or linear "
      "regression - on those. The out-of-fold requirement is absolute: using "
      "in-fold predictions leaks and produces a meta-model that trusts an "
      "overfitted base model.")
    box("tip", "Practical ensembling that is worth the complexity",
        "In order of value per unit of effort: (1) average several seeds of the "
        "same model - almost free, reliably worth a few tenths of a percent; "
        "(2) average a GBDT with a neural network - their errors are genuinely "
        "different; (3) full stacking with a meta-learner. In production, weigh "
        "the gain against the latency and maintenance cost of running five "
        "models.")

    h3("Exercises")
    bul([
        "Implement gradient boosting with depth-2 trees and squared loss in 60 "
        "lines, and verify that its predictions approach the target as M grows.",
        "Show the effect of `max_features` on random forest accuracy and on the "
        "average correlation between tree predictions.",
        "Take a tuned LightGBM model and add a small MLP to a simple average. "
        "Measure whether the blend beats both members, and check the correlation "
        "of their errors to explain why.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 12 ---
    chapter("Unsupervised Learning and Dimensionality Reduction")
    h2("Clustering")
    h3("k-means")
    p("Partition n points into k clusters minimising within-cluster squared "
      "distance. Lloyd's algorithm alternates two steps until assignments stop "
      "changing:")
    eq(["Assign:  c_i = argmin_k ||x_i - mu_k||^2",
        "Update:  mu_k = mean of the points assigned to cluster k",
        "Objective (inertia):  J = SUM_i ||x_i - mu_c_i||^2"])
    bul([
        "Each step never increases J, so the algorithm converges - to a **local** "
        "optimum that depends on initialisation. Use **k-means++** seeding and "
        "several restarts.",
        "Assumes clusters are roughly spherical, similar in size and density; it "
        "fails on elongated or nested shapes.",
        "Choosing k: the **elbow** of the inertia curve, the **silhouette score** "
        "(the more reliable of the two), gap statistic, or a downstream metric if "
        "the clusters feed another system.",
        "Scale features first; k-means is Euclidean and unit-sensitive. "
        "MiniBatchKMeans scales to millions of points.",
    ])
    h3("Gaussian mixture models and EM")
    p("A GMM is the soft, probabilistic generalisation: data is assumed drawn "
      "from a mixture of K Gaussians, each with its own mean, covariance and "
      "weight. **Expectation-Maximisation** alternates computing the posterior "
      "responsibility of each component for each point (E-step) with re-fitting "
      "the components weighted by those responsibilities (M-step). Each iteration "
      "provably does not decrease the likelihood.")
    eq(["E-step:  gamma_ik = pi_k N(x_i | mu_k, S_k) / SUM_j pi_j N(x_i | mu_j, S_j)",
        "M-step:  mu_k = SUM_i gamma_ik x_i / SUM_i gamma_ik   (and similarly S_k, pi_k)"])
    p("GMMs give soft assignments, elliptical clusters, a proper likelihood (so "
      "BIC can select K), and a density model usable for anomaly detection. "
      "k-means is the limiting case with spherical, equal, vanishing-variance "
      "components.")
    h3("Density and hierarchical methods")
    bul([
        "**DBSCAN:** clusters are dense regions separated by sparse ones. Finds "
        "arbitrary shapes, labels outliers as noise, needs no k - but needs eps "
        "and min_samples, and struggles with varying density.",
        "**HDBSCAN:** builds a hierarchy over eps and extracts the most stable "
        "clusters. The best modern default for exploratory clustering.",
        "**Agglomerative:** merge the closest pair repeatedly; the dendrogram "
        "shows structure at every scale. Linkage choice (ward, average, complete) "
        "changes the results substantially.",
        "**Spectral clustering:** cluster the eigenvectors of a similarity graph "
        "Laplacian - excellent for manifold-shaped data, O(n^3) without "
        "approximation.",
    ])
    box("warn", "Clustering always returns clusters",
        "Every algorithm partitions whatever you give it, including pure noise. "
        "Before believing a clustering: check stability across seeds and "
        "subsamples, check that silhouette is meaningfully above zero, and, most "
        "importantly, validate against something external - a downstream metric or "
        "a domain expert's reading of the clusters.")

    h2("Dimensionality reduction")
    h3("PCA, derived")
    p("PCA finds the orthogonal directions of maximum variance. Centre X, then "
      "either eigendecompose the covariance `C = X^T X / (n-1)` or - better "
      "numerically - take the SVD of X directly.")
    eq(["X = U S V^T   =>   principal directions are the columns of V",
        "explained variance ratio of component j = s_j^2 / SUM_k s_k^2",
        "projection to k dims:  Z = X V_k         reconstruction: X_hat = Z V_k^T"])
    box("math", "Two equivalent characterisations",
        "Maximising projected variance and minimising squared reconstruction "
        "error give the SAME subspace. That equivalence is why PCA is "
        "simultaneously a compression method and a de-noising method, and why a "
        "linear autoencoder with squared loss learns exactly the PCA subspace "
        "(Chapter 25).")
    bul([
        "**Scale first** unless all features share units - otherwise the "
        "largest-variance unit dominates.",
        "Choose k by cumulative explained variance (90-99%) or by an elbow in the "
        "scree plot.",
        "PCA is linear and unsupervised: it may discard exactly the low-variance "
        "direction that carries your label. Check downstream, not just variance.",
        "**Whitening** rescales components to unit variance - useful before some "
        "downstream models, harmful when it amplifies noise directions.",
        "Variants: randomised/truncated SVD for large matrices, kernel PCA for "
        "non-linear structure, sparse PCA for interpretable loadings, incremental "
        "PCA for streaming.",
    ])
    h3("Manifold learning: t-SNE and UMAP")
    tbl(["Aspect", "t-SNE", "UMAP"],
        [["Objective", "Match pairwise neighbour probabilities with KL divergence",
          "Match fuzzy topological structure with cross-entropy"],
         ["Speed", "Slow, O(n log n) with Barnes-Hut", "Much faster; scales to "
          "millions"],
         ["Global structure", "Poorly preserved - inter-cluster distances are "
          "not meaningful", "Better preserved, still not metric"],
         ["Key knob", "perplexity (5-50)", "n_neighbors, min_dist"],
         ["New points", "No natural transform", "Has a transform method"]],
        widths=[18, 41, 41], bold_first=True)
    box("warn", "How to misread a t-SNE plot",
        "Cluster sizes carry no meaning. Distances between clusters carry almost "
        "no meaning. Random seeds change the picture. Different perplexities can "
        "invent or dissolve clusters. Use these plots to generate hypotheses and "
        "to sanity-check embeddings - never as evidence for a claim about "
        "geometry, and never to choose k for clustering.")
    h3("Other reductions worth knowing")
    bul([
        "**LDA** (supervised, K-1 dimensions, maximises class separation).",
        "**NMF** for non-negative data: parts-based, interpretable topics.",
        "**Autoencoders** for non-linear compression, and **VAEs** for a "
        "probabilistic latent space (Chapter 25).",
        "**Random projection**: the Johnson-Lindenstrauss lemma guarantees that a "
        "random linear map into O(log n / eps^2) dimensions preserves pairwise "
        "distances to within eps. Astonishingly cheap and useful for very "
        "high-dimensional sparse data.",
    ])

    ex_ch12()

    h2("Anomaly detection")
    tbl(["Method", "Idea", "Notes"],
        [["Z-score / IQR", "Univariate thresholds", "Trivial baseline; ignores "
          "correlations"],
         ["Mahalanobis distance", "Distance under the covariance", "Assumes one "
          "Gaussian blob"],
         ["Isolation Forest", "Random splits isolate outliers in fewer steps",
          "Fast, few assumptions - a strong default"],
         ["Local Outlier Factor", "Compares local density to neighbours' density",
          "Catches local anomalies a global method misses"],
         ["One-class SVM", "Learns a boundary around the data", "Sensitive to nu "
          "and gamma"],
         ["Autoencoder reconstruction error", "Anomalies reconstruct badly",
          "Good for images and signals; needs clean training data"]],
        widths=[24, 40, 36], bold_first=True)

    h3("Exercises")
    bul([
        "Implement k-means and k-means++ initialisation; compare final inertia "
        "over 50 random restarts of each.",
        "Run PCA on a face or digit dataset and display the first 16 components "
        "as images; then reconstruct with k = 5, 20, 100 and compare.",
        "Cluster the same dataset with k-means, GMM, DBSCAN and HDBSCAN and "
        "compare silhouette scores and the number of points labelled noise.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 13 ---
    chapter("Evaluation: Metrics, Calibration and Imbalance")
    p("A model is only as good as the number you use to judge it. Choosing that "
      "number is a modelling decision at least as important as choosing the "
      "architecture, and it is where most projects quietly fail.")

    h2("Classification: the confusion matrix and everything derived from it")
    diagram([
        "                          PREDICTED",
        "                     positive     negative",
        "                 +------------+------------+",
        "   A   positive  |     TP     |     FN     |   <- recall = TP/(TP+FN)",
        "   C             +------------+------------+",
        "   T   negative  |     FP     |     TN     |   <- specificity = TN/(TN+FP)",
        "   U             +------------+------------+",
        "   A                    ^",
        "   L              precision = TP/(TP+FP)",
    ], "Figure 13.1 - Every classification metric is a ratio taken from this table.")
    tbl(["Metric", "Formula", "Optimise it when"],
        [["Accuracy", "(TP+TN)/n", "Classes are balanced and errors cost the same"],
         ["Precision", "TP/(TP+FP)", "False alarms are expensive (spam filter, "
          "arrest, expensive follow-up)"],
         ["Recall / sensitivity", "TP/(TP+FN)", "Misses are expensive (cancer "
          "screening, fraud, safety)"],
         ["F1", "2PR/(P+R)", "You need a single number balancing the two"],
         ["F-beta", "(1+b^2)PR/(b^2 P + R)", "You can state how much more recall "
          "matters than precision"],
         ["Specificity", "TN/(TN+FP)", "The true-negative rate matters explicitly"],
         ["Balanced accuracy", "(recall + specificity)/2", "Imbalanced data, "
           "single number"],
         ["MCC", "correlation of predictions and truth", "Imbalanced data; the "
          "most informative single scalar"],
         ["Cohen kappa", "agreement above chance", "Comparing against annotator "
          "agreement"]],
        widths=[20, 26, 54], bold_first=True)

    h2("Threshold-free metrics: ROC and PR curves")
    bul([
        "**ROC curve:** true positive rate against false positive rate as the "
        "threshold sweeps. **AUC-ROC** is the probability that a random positive "
        "scores above a random negative. It is invariant to class balance - which "
        "is a strength when comparing across datasets and a serious weakness when "
        "positives are rare, because a huge number of false positives barely "
        "moves FPR.",
        "**Precision-recall curve:** precision against recall. **AUC-PR** (or "
        "average precision) is the right summary under heavy imbalance, because "
        "its baseline is the positive rate itself, not 0.5.",
        "**Rule:** with a positive rate below roughly 10%, report PR-AUC. Report "
        "ROC-AUC too if you like, but do not make decisions with it.",
    ])
    box("math", "Why AUC-ROC flatters a rare-event model",
        "Take 1,000,000 negatives and 1,000 positives. A model that flags 20,000 "
        "negatives as positive has FPR = 2%, which looks excellent on an ROC "
        "curve. But if it also catches 800 positives, precision is "
        "800/20,800 = 3.8% - 96% of the alerts are wrong, and the operations team "
        "will abandon the system in a week. The PR curve shows this immediately; "
        "the ROC curve hides it.")

    h2("Choosing the operating threshold")
    p("Training produces scores; the threshold is a **separate decision** that "
      "should be made with the costs of the application in hand. If a false "
      "negative costs C_FN and a false positive costs C_FP, the expected-cost-"
      "minimising threshold on a calibrated probability is:")
    eq("t* = C_FP / (C_FP + C_FN)")
    p("So if a miss is nine times more expensive than a false alarm, threshold at "
      "0.1, not 0.5. Choose the threshold on validation data, never on test, and "
      "re-check it after any retraining, because score distributions drift.")

    h2("Regression metrics")
    tbl(["Metric", "Formula", "Character"],
        [["MSE / RMSE", "mean of squared errors (root)", "Penalises large errors "
          "hard; RMSE is in the units of y"],
         ["MAE", "mean absolute error", "Robust; the median-optimal predictor"],
         ["MAPE", "mean of |err|/|y| in percent", "Interpretable, explodes near "
          "y = 0, asymmetric"],
         ["sMAPE / WAPE", "scaled variants", "Fixes some MAPE pathologies"],
         ["R^2", "1 - SS_res/SS_tot", "Relative to predicting the mean; can be "
          "negative"],
         ["Pinball loss", "asymmetric absolute", "Evaluates quantile forecasts"],
         ["MASE", "error relative to a naive forecast", "Time series: is the model "
          "beating last-value-carried-forward?"]],
        widths=[16, 30, 54], bold_first=True)

    h2("Probability calibration")
    p("A model is **calibrated** when among all samples it scores 0.7, about 70% "
      "are truly positive. Ranking quality (AUC) and calibration are independent: "
      "a model can rank perfectly and still be systematically overconfident. If "
      "the score feeds a threshold rule, an expected-cost calculation, or a human "
      "decision, calibration is not optional.")
    bul([
        "**Diagnose** with a reliability diagram (predicted probability against "
        "observed frequency in bins) and summarise with **expected calibration "
        "error (ECE)** or Brier score.",
        "**Platt scaling:** fit a 1-D logistic regression on the scores. Few "
        "parameters, works well with little validation data, assumes a sigmoidal "
        "distortion.",
        "**Isotonic regression:** fit a monotone step function. More flexible, "
        "needs more data (about 1,000+ validation samples), can overfit.",
        "**Temperature scaling:** divide the logits by a single learned scalar T. "
        "The standard fix for modern neural networks, which are famously "
        "overconfident; it preserves accuracy exactly since it is monotone.",
        "Fit calibration on a **held-out** set, never on the training data.",
    ])
    code([
        "import torch, torch.nn.functional as F",
        "",
        "def fit_temperature(logits, labels, iters=200):",
        "    # logits: (n, K) from a frozen trained model on a VALIDATION set",
        "    logT = torch.zeros(1, requires_grad=True)",
        "    opt = torch.optim.LBFGS([logT], lr=0.1, max_iter=iters)",
        "    def closure():",
        "        opt.zero_grad()",
        "        loss = F.cross_entropy(logits / logT.exp(), labels)",
        "        loss.backward()",
        "        return loss",
        "    opt.step(closure)",
        "    return logT.exp().item()      # T > 1 softens an overconfident model",
    ], "Listing 13.1 - Temperature scaling: one parameter, large calibration gains.")

    ex_ch13()

    h2("Statistical significance and reporting")
    bul([
        "Report mean and standard deviation over at least 3-5 seeds. A single "
        "run is an anecdote.",
        "Use bootstrap confidence intervals on the test set: resample it with "
        "replacement 1,000 times and take the 2.5th and 97.5th percentiles of the "
        "metric.",
        "For paired model comparison on the same test set use McNemar's test "
        "(classification) or a paired bootstrap; for multiple datasets use the "
        "Wilcoxon signed-rank test.",
        "Correct for multiple comparisons when you test many models "
        "(Bonferroni is crude but honest).",
        "Always report the trivial baseline. 'We reached 94% accuracy' means "
        "nothing if the majority class is 93%.",
    ])
    box("warn", "Goodhart's law in machine learning",
        "When a measure becomes a target, it ceases to be a good measure. A model "
        "tuned relentlessly against one offline metric will find the shortcuts "
        "that metric permits - background artefacts in X-rays, timestamp leakage "
        "in fraud data, annotation quirks in benchmarks. Defend with: multiple "
        "metrics, slice-based evaluation across subgroups, a hand-audited error "
        "sample every cycle, and an online test before you believe anything.")

    h2("Slice-based evaluation")
    p("Aggregate metrics hide the failures that matter. Always evaluate per "
      "slice: by class, by subgroup (age, sex, device, region, language), by "
      "difficulty, by data source, and by time period. A useful discipline is to "
      "define the slices **before** training and to treat a large per-slice drop "
      "as a release blocker, exactly like a failing test.")

    h3("Exercises")
    bul([
        "Construct a dataset with a 1% positive rate and a model with ROC-AUC "
        "0.95; compute its precision at the 0.5 threshold and explain the gap.",
        "Draw a reliability diagram for a random forest and for a neural network "
        "on the same data; apply isotonic regression and temperature scaling "
        "respectively and re-draw.",
        "Compute a bootstrap 95% confidence interval for the F1 of your best "
        "model and decide whether it is genuinely better than the runner-up.",
    ], ordered=True)


# =============================================================================
#                        PART III - DEEP LEARNING CORE
# =============================================================================
def part3():
    part("Deep Learning Core",
         "Neurons, backpropagation derived by hand, activations, optimisers, "
         "normalisation, regularisation, and a practical playbook for making "
         "training actually work.")

    # --------------------------------------------------------------- Ch 14 ---
    chapter("From a Single Neuron to a Multilayer Network", newpage=False)
    h2("The artificial neuron")
    eq(["z = w . x + b          (a linear score - identical to Chapter 5)",
        "a = phi(z)             (a non-linearity)"])
    p("That is the entire unit. Its power comes from two things: stacking many of "
      "them in a layer, and stacking layers. Without the non-linearity phi, "
      "stacking is pointless - the composition of linear maps is a linear map, so "
      "a 50-layer linear network has exactly the expressive power of one linear "
      "layer. **The non-linearity is what makes depth mean anything.**")
    diagram([
        "     x1 --w1--\\",
        "     x2 --w2---+--> [ sum ] --z--> [ phi ] --a-->",
        "     x3 --w3--/        ^",
        "                       |",
        "                       b",
        "",
        "  A LAYER of m such units, for a batch of n samples:",
        "     Z = X W^T + b      X:(n,d)  W:(m,d)  b:(m,)  Z:(n,m)",
        "     A = phi(Z)",
    ], "Figure 14.1 - A neuron, and the matrix form that a GPU actually executes.")

    h2("The multilayer perceptron")
    eq(["a^(0) = x",
        "z^(l) = W^(l) a^(l-1) + b^(l)",
        "a^(l) = phi( z^(l) )                for l = 1 .. L-1",
        "y_hat = output_activation( z^(L) )"])
    tbl(["Task", "Output units", "Output activation", "Loss"],
        [["Regression", "1", "none (identity)", "MSE / Huber"],
         ["Binary classification", "1", "sigmoid (or none + BCEWithLogits)",
          "Binary cross-entropy"],
         ["Multiclass (one label)", "K", "softmax (or none + CrossEntropyLoss)",
          "Categorical cross-entropy"],
         ["Multi-label", "K", "K independent sigmoids", "Sum of binary "
          "cross-entropies"],
         ["Count", "1", "exp / softplus", "Poisson NLL"],
         ["Quantiles", "Q", "none", "Pinball loss per quantile"]],
        widths=[24, 14, 33, 29], bold_first=True)

    h2("The universal approximation theorem, honestly stated")
    box("key", "What it does and does not promise",
        "A feedforward network with ONE hidden layer and a non-polynomial "
        "activation can approximate any continuous function on a compact set to "
        "arbitrary accuracy, given ENOUGH hidden units. What the theorem does NOT "
        "say: how many units (it can be exponential in the input dimension), that "
        "gradient descent will find those weights, or that the result will "
        "generalise. It establishes that depth is not required for "
        "expressiveness - and practice establishes that depth is required for "
        "EFFICIENCY.")
    p("Depth buys exponential efficiency for compositional functions. A function "
      "built from repeated composition - edges to shapes to parts to objects, "
      "characters to words to phrases to meaning - is represented by a deep "
      "network with a number of units linear in depth, and may need "
      "exponentially many units in a shallow one. Real perceptual data is "
      "compositional, which is why depth wins in practice.")

    h2("Counting parameters and cost")
    eq(["Params of a dense layer: m * d + m       (weights + biases)",
        "MLP 784 -> 256 -> 128 -> 10:",
        "  784*256+256 = 200,960",
        "  256*128+128 =  32,896",
        "  128*10 +10  =   1,290      TOTAL = 235,146 parameters",
        "Memory in float32 = 235,146 * 4 B = 0.94 MB (weights only)"])
    p("Training memory is far larger than the weights: you also store activations "
      "for the backward pass (batch size times all layer outputs), gradients (one "
      "per parameter), and optimiser state (two more per parameter for Adam). A "
      "useful rule for Adam in float32: **about 16 bytes per parameter** before "
      "activations. This arithmetic is the entry point to Part V, where reducing "
      "it is the whole game.")

    h2("Your first network, twice")
    code([
        "import torch, torch.nn as nn",
        "",
        "model = nn.Sequential(",
        "    nn.Flatten(),",
        "    nn.Linear(784, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.2),",
        "    nn.Linear(256, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.2),",
        "    nn.Linear(128, 10),                    # raw logits, no softmax here",
        ")",
        "",
        "opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)",
        "lossf = nn.CrossEntropyLoss(label_smoothing=0.05)",
        "sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3,",
        "                                            total_steps=epochs*len(train_dl))",
        "",
        "for epoch in range(epochs):",
        "    model.train()",
        "    for xb, yb in train_dl:",
        "        xb, yb = xb.to(dev), yb.to(dev)",
        "        opt.zero_grad(set_to_none=True)",
        "        loss = lossf(model(xb), yb)",
        "        loss.backward()",
        "        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)",
        "        opt.step(); sched.step()",
        "    model.eval()",
        "    with torch.no_grad():",
        "        acc = sum((model(x.to(dev)).argmax(1).cpu() == y).sum().item()",
        "                  for x, y in val_dl) / len(val_dl.dataset)",
        "    print(epoch, round(acc, 4))",
    ], "Listing 14.1 - A complete, modern training loop. Every ingredient - "
       "BatchNorm, dropout, AdamW, warmup schedule, gradient clipping, "
       "label smoothing - is explained in Chapters 16-20.")
    box("tip", "train() and eval() are not decoration",
        "Dropout must be off and BatchNorm must use running statistics at "
        "evaluation time. Forgetting `model.eval()` is the single most common "
        "PyTorch bug and produces mysteriously poor, noisy validation numbers. "
        "Equally, forgetting `torch.no_grad()` at evaluation wastes memory "
        "building a graph you never use.")

    h3("Exercises")
    bul([
        "Prove that a network with identity activations and L layers computes a "
        "single linear map, and give the resulting weight matrix.",
        "Count the parameters and estimate the Adam training memory of an MLP "
        "1024-1024-1024-10.",
        "Train the network above on MNIST or Fashion-MNIST; then remove all "
        "non-linearities and compare - the gap is the value of depth.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 15 ---
    chapter("Backpropagation, Derived and Implemented")
    p("Backpropagation is reverse-mode automatic differentiation applied to a "
      "neural network. It is not a learning algorithm - gradient descent is - but "
      "it is what makes gradient descent affordable: the cost of computing "
      "gradients for **all** parameters is about the same as one forward pass, "
      "regardless of how many parameters there are.")

    h2("The four equations")
    p("Define the error signal at layer l as `delta^(l) = dJ / dz^(l)`. Then:")
    eq(["(1)  delta^(L)   = grad_a J  *  phi'( z^(L) )          [output layer]",
        "(2)  delta^(l)   = ( W^(l+1)^T delta^(l+1) ) * phi'( z^(l) )   [recursion]",
        "(3)  dJ/dW^(l)   = delta^(l) ( a^(l-1) )^T",
        "(4)  dJ/db^(l)   = delta^(l)",
        "",
        "     ( * denotes elementwise multiplication )"])
    box("math", "Deriving equation (2), the only step that matters",
        "z^(l+1) = W^(l+1) a^(l) + b^(l+1) and a^(l) = phi(z^(l)). By the chain "
        "rule, dJ/dz^(l)_j = SUM_k (dJ/dz^(l+1)_k)(dz^(l+1)_k/da^(l)_j)"
        "(da^(l)_j/dz^(l)_j) = SUM_k delta^(l+1)_k W^(l+1)_kj phi'(z^(l)_j). "
        "Collecting over j gives exactly (W^(l+1)^T delta^(l+1)) * phi'(z^(l)). "
        "Notice what this says: the error is propagated backwards through the "
        "TRANSPOSE of the same weight matrix used in the forward pass, and it is "
        "gated by the local derivative of the activation.")
    diagram([
        "  FORWARD    x --> [W1] --> z1 --> phi --> a1 --> [W2] --> z2 --> loss",
        "                                                                   |",
        "  BACKWARD       dW1 <-- d1 <-- *phi' <-- W2^T d2 <----------- d2 <-+",
        "",
        "  Each layer needs, from the forward pass: its input a^(l-1) and z^(l).",
        "  That is why activations are stored - and why training memory scales",
        "  with batch size times depth.",
    ], "Figure 15.1 - Forward stores activations; backward consumes them.")

    h2("Why reverse mode, and what it costs")
    tbl(["Mode", "Cost", "Efficient when"],
        [["Forward-mode AD", "One pass per INPUT variable",
          "Few inputs, many outputs"],
         ["Reverse-mode AD (backprop)", "One pass per OUTPUT variable",
          "Many inputs, one output - exactly the ML case: millions of parameters, "
          "one scalar loss"],
         ["Numerical differences", "Two evaluations per parameter",
          "Never for training; only for checking a hand-written gradient"]],
        widths=[24, 30, 46], bold_first=True)

    h2("A complete NumPy implementation")
    code([
        "import numpy as np",
        "",
        "def init(sizes, rng):",
        "    # He initialisation, correct for ReLU (Chapter 16)",
        "    return [ (rng.normal(0, np.sqrt(2.0/a), (b, a)), np.zeros(b))",
        "             for a, b in zip(sizes[:-1], sizes[1:]) ]",
        "",
        "def forward(params, X):",
        "    cache = [X]",
        "    A = X",
        "    for i, (W, b) in enumerate(params):",
        "        Z = A @ W.T + b",
        "        A = Z if i == len(params) - 1 else np.maximum(0.0, Z)   # ReLU",
        "        cache.append((Z, A))",
        "    return A, cache                       # A = logits at the last layer",
        "",
        "def softmax_xent(logits, Y1h):",
        "    Z = logits - logits.max(1, keepdims=True)",
        "    P = np.exp(Z); P /= P.sum(1, keepdims=True)",
        "    n = len(Y1h)",
        "    loss = -np.sum(Y1h * np.log(P + 1e-12)) / n",
        "    return loss, (P - Y1h) / n            # dL/dlogits: the clean form",
        "",
        "def backward(params, cache, dZ):",
        "    grads = [None] * len(params)",
        "    for l in reversed(range(len(params))):",
        "        A_prev = cache[0] if l == 0 else cache[l][1]",
        "        dW = dZ.T @ A_prev                # eq. (3)",
        "        db = dZ.sum(axis=0)               # eq. (4)",
        "        grads[l] = (dW, db)",
        "        if l > 0:",
        "            dA = dZ @ params[l][0]        # W^T delta",
        "            dZ = dA * (cache[l][0] > 0)   # * phi'(z), ReLU derivative",
        "    return grads",
        "",
        "def sgd_step(params, grads, lr):",
        "    return [ (W - lr*dW, b - lr*db)",
        "             for (W, b), (dW, db) in zip(params, grads) ]",
    ], "Listing 15.1 - Backpropagation for an MLP in 35 lines. Write this once "
       "from scratch and deep learning stops being magic.")

    h2("Gradient checking")
    p("Before trusting a hand-written gradient, compare it against a central "
      "finite difference. Use double precision, a step of about 1e-5, and the "
      "relative error criterion below; anything under 1e-7 is right, above 1e-4 "
      "is a bug.")
    eq(["numeric = ( J(theta + eps) - J(theta - eps) ) / (2 eps)",
        "rel_err = |numeric - analytic| / max( |numeric| , |analytic| , 1e-8 )"])
    box("warn", "Check gradients with dropout and batch norm disabled",
        "Any source of randomness or batch-dependence makes J(theta + eps) and "
        "J(theta - eps) evaluate different functions, and the check fails for "
        "reasons that have nothing to do with your derivation. Fix the seed, turn "
        "off dropout, use eval-mode normalisation, and check on a small batch.")

    ex_ch15()

    h2("Vanishing and exploding gradients")
    p("Equation (2) is a repeated matrix product. Over L layers the error signal "
      "is multiplied by L factors of the form `W^T` and `phi'`. If the typical "
      "singular value of that product is below 1, the gradient decays "
      "exponentially with depth; above 1 and it explodes.")
    tbl(["Problem", "Symptom", "Remedies"],
        [["Vanishing", "Early layers barely change; loss plateaus early; deep net "
          "does no better than a shallow one",
          "ReLU-family activations, He/Glorot init, residual connections, "
          "normalisation layers, LSTM/GRU gates for sequences"],
         ["Exploding", "Loss becomes NaN or oscillates violently; gradient norms "
          "in the thousands",
          "Gradient clipping (norm 1.0 is a good default), lower learning rate, "
          "normalisation, careful init, gradient accumulation instead of huge "
          "steps"]],
        widths=[13, 39, 48], bold_first=True)
    box("key", "Residual connections in one line of intuition",
        "If a block computes y = x + F(x), then dy/dx = I + dF/dx. The identity "
        "term guarantees that gradient flows to earlier layers even when dF/dx is "
        "tiny. That is why ResNets made 100+ layer networks trainable, and it is "
        "why essentially every modern architecture, Transformers included, is "
        "built out of residual blocks.")

    h2("Automatic differentiation in practice")
    bul([
        "Frameworks build a **computation graph** during the forward pass "
        "(dynamic in PyTorch, traced/compiled in JAX and TF), then walk it "
        "backwards applying each operation's vector-Jacobian product.",
        "**Gradient accumulation:** call backward on several small batches before "
        "stepping, to simulate a large batch on limited memory. Remember to scale "
        "the loss by 1/accumulation_steps.",
        "**Gradient checkpointing:** discard activations during the forward pass "
        "and recompute them during the backward pass - trades roughly 30% extra "
        "compute for a large memory saving, and is what makes very deep or very "
        "long-context models fit.",
        "**detach() / stop_gradient** cuts the graph: essential for target "
        "networks in RL, teacher outputs in distillation, and any quantity you "
        "want treated as a constant.",
        "The **straight-through estimator** replaces a non-differentiable step "
        "(rounding, sign, top-k) with the identity in the backward pass. It is "
        "the trick that makes quantization-aware training possible (Chapter 28).",
    ])

    h3("Exercises")
    bul([
        "Implement Listing 15.1, train it on MNIST to above 97% test accuracy, "
        "and verify every gradient against finite differences first.",
        "Replace ReLU with sigmoid in a 10-layer network and plot the norm of "
        "dJ/dW per layer. Then add residual connections and re-plot.",
        "Derive the backward pass of a batch-normalisation layer. It is the most "
        "instructive non-trivial derivation in deep learning.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 16 ---
    chapter("Activations, Initialization and Loss Functions")
    h2("Activation functions")
    tbl(["Name", "Definition", "Range", "Notes"],
        [["Sigmoid", "1/(1+e^-z)", "(0,1)", "Output layer for binary tasks only. "
          "Saturates; not zero-centred"],
         ["Tanh", "(e^z-e^-z)/(e^z+e^-z)", "(-1,1)", "Zero-centred sigmoid; still "
          "saturates. Used inside LSTM gates"],
         ["ReLU", "max(0, z)", "[0,inf)", "The default for 20 years of CNNs: "
          "cheap, no saturation for z>0. Can die"],
         ["Leaky ReLU", "max(0.01z, z)", "R", "Fixes dying ReLU with a small "
          "negative slope"],
         ["PReLU", "max(az, z), a learned", "R", "Leaky with a learned slope"],
         ["ELU", "z if z>0 else a(e^z-1)", "(-a,inf)", "Smooth, mean activations "
          "near zero, costlier"],
         ["GELU", "z * Phi(z)", "R", "Smooth, probabilistic gating. Standard in "
          "Transformers"],
         ["SiLU / Swish", "z * sigmoid(z)", "R", "Smooth, often slightly better "
          "than ReLU in vision"],
         ["Mish", "z * tanh(softplus(z))", "R", "Smooth alternative, more compute"],
         ["Softplus", "log(1+e^z)", "(0,inf)", "Smooth ReLU; used to output "
          "positive parameters"],
         ["GLU / SwiGLU", "(Wx) * sigma(Vx)", "R", "Gated variants; SwiGLU is the "
          "standard feedforward in modern LLMs"],
         ["Softmax", "e^z_k / SUM e^z_j", "simplex", "Output layer for multiclass"]],
        widths=[14, 24, 12, 50], bold_first=True)
    box("warn", "The dying ReLU problem",
        "If a unit's pre-activation is negative for every sample, its gradient is "
        "exactly zero forever and the unit is dead. This usually follows a "
        "learning rate that was too high early in training, and can silently kill "
        "30-50% of a layer. Diagnose by counting units with zero activation over "
        "a validation batch; fix with a lower learning rate, He initialisation, "
        "Leaky ReLU or GELU, and normalisation layers.")
    box("tip", "What to actually use",
        "Hidden layers of a convnet or MLP: ReLU, or GELU/SiLU if you want the "
        "last half percent. Transformers: GELU or SwiGLU. LSTM gates: keep "
        "sigmoid and tanh - the gates need bounded outputs. Output layer: chosen "
        "by the task, per the table in Chapter 14. Do not spend a week tuning "
        "activations; spend it on data.")

    h2("Weight initialisation")
    p("Initialisation controls the scale of activations and gradients at step "
      "zero. Get it wrong and signals vanish or explode before learning begins. "
      "The principle is to keep the variance of activations roughly constant "
      "across layers.")
    eq(["Xavier/Glorot (tanh, sigmoid, linear):",
        "   Var(W) = 2 / (fan_in + fan_out)",
        "He/Kaiming (ReLU family) - accounts for half the outputs being zeroed:",
        "   Var(W) = 2 / fan_in",
        "LeCun (SELU):   Var(W) = 1 / fan_in",
        "Orthogonal:     W = an orthogonal matrix, good for RNNs and deep stacks"])
    bul([
        "**Never initialise all weights to zero** - every unit in a layer would "
        "compute the same thing and receive the same gradient forever. Symmetry "
        "must be broken randomly.",
        "**Biases** start at zero (a small positive value such as 0.01 was once "
        "recommended for ReLU; it makes little difference in practice).",
        "**Residual branches** are often initialised so the block starts as an "
        "identity (zero-init the last layer of each block, or use LayerScale). "
        "This lets very deep networks train stably from step one.",
        "Modern transformer stacks scale initialisation by 1/sqrt(2L) on residual "
        "projections to keep the variance of the residual stream bounded with "
        "depth.",
    ])

    h2("Loss functions, and what each one assumes")
    tbl(["Loss", "Task", "Assumption / behaviour"],
        [["MSE", "Regression", "Gaussian noise; punishes outliers heavily"],
         ["MAE", "Regression", "Laplace noise; estimates the conditional median"],
         ["Huber / smooth L1", "Regression, detection", "Quadratic near zero, "
          "linear far away - robust and smooth"],
         ["Cross-entropy", "Classification", "Correct probabilistic loss; pairs "
          "with softmax/sigmoid"],
         ["Focal loss", "Detection, heavy imbalance", "Down-weights easy examples "
          "by (1-p)^gamma"],
         ["Label-smoothed CE", "Classification", "Targets 1-eps instead of 1; "
          "reduces overconfidence and improves calibration"],
         ["KL divergence", "Distillation, VAE", "Matches a full distribution "
          "rather than a label"],
         ["Contrastive / InfoNCE", "Self-supervision, retrieval", "Pull positives "
          "together, push negatives apart"],
         ["Triplet loss", "Metric learning", "Anchor closer to positive than to "
          "negative by a margin"],
         ["Dice / IoU loss", "Segmentation", "Directly optimises overlap; robust "
          "to class imbalance in masks"],
         ["CTC", "Speech, handwriting", "Aligns unsegmented sequences"],
         ["Pinball", "Quantile regression", "Asymmetric; yields prediction "
          "intervals"]],
        widths=[19, 22, 59], bold_first=True)
    eq(["Focal loss:   FL(p_t) = -alpha (1 - p_t)^gamma log(p_t),   gamma ~ 2",
        "Label smoothing: y_smooth = (1 - eps) y_onehot + eps / K,  eps ~ 0.1"])
    box("expert", "Multi-task loss weighting",
        "When you sum several losses, their scales decide the effective learning "
        "rate of each task. Options: normalise each loss by a running estimate of "
        "its magnitude; use uncertainty weighting, which learns a per-task "
        "log-variance s_i and optimises SUM ( L_i / (2 exp(s_i)) + s_i / 2 ); or "
        "use gradient-based balancing such as GradNorm. Fixed hand-tuned weights "
        "work but become a maintenance burden as tasks are added.")

    h3("Exercises")
    bul([
        "Plot ReLU, GELU, SiLU and their derivatives on [-5, 5] and explain the "
        "smoothness argument in terms of the gradient at zero.",
        "Initialise a 20-layer ReLU MLP with Var(W)=1/fan_in, 2/fan_in and "
        "4/fan_in, and plot the standard deviation of activations per layer at "
        "initialisation.",
        "Train a classifier with and without label smoothing eps=0.1 and compare "
        "accuracy, expected calibration error, and the histogram of maximum "
        "softmax probabilities.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 17 ---
    chapter("Optimization Algorithms and Learning-Rate Schedules")
    p("Everything in this chapter is a variation on one line: `theta <- theta - "
      "eta * (something derived from the gradient)`. The variations differ in how "
      "they estimate direction and how they set an effective per-parameter step "
      "size.")

    h2("The algorithms, in the order they were invented")
    h3("SGD")
    eq("theta <- theta - eta * g,        g = gradient on the current mini-batch")
    h3("Momentum and Nesterov")
    eq(["v <- beta v + g              theta <- theta - eta v          (momentum)",
        "Nesterov: evaluate the gradient at the look-ahead point theta - eta beta v"])
    p("Momentum accumulates a velocity in directions of consistent gradient and "
      "cancels oscillation across a narrow valley. With beta = 0.9 the effective "
      "step is about 1/(1-beta) = 10 times larger along a consistent direction. "
      "It is not a nicety: SGD with momentum, well tuned, still produces the best "
      "final accuracy on many vision benchmarks.")
    h3("Adaptive methods")
    eq(["AdaGrad:  s <- s + g^2,          theta <- theta - eta g / (sqrt(s) + e)",
        "RMSProp:  s <- rho s + (1-rho) g^2,   theta <- theta - eta g/(sqrt(s)+e)",
        "",
        "Adam:  m <- b1 m + (1-b1) g            (first moment)",
        "       v <- b2 v + (1-b2) g^2          (second moment)",
        "       m_hat = m/(1-b1^t),  v_hat = v/(1-b2^t)     (bias correction)",
        "       theta <- theta - eta * m_hat / ( sqrt(v_hat) + eps )"])
    p("AdaGrad's accumulated sum only grows, so the effective learning rate decays "
      "monotonically to zero - fine for convex sparse problems, fatal for long "
      "deep-learning runs. RMSProp replaces the sum with an exponential moving "
      "average, fixing that. Adam adds momentum and bias correction, and it is "
      "the default for a good reason: it works without tuning on an enormous "
      "range of problems.")
    box("key", "AdamW: decoupled weight decay",
        "Adding lambda*||w||^2 to the loss is NOT the same as decaying weights "
        "when the optimiser rescales the gradient per parameter - the penalty "
        "gets divided by sqrt(v) too, so parameters with large gradients are "
        "barely regularised. AdamW decouples it: theta <- theta - eta(m_hat/"
        "(sqrt(v_hat)+eps) + lambda*theta). This one change reliably improves "
        "generalisation, and AdamW is now the default for Transformers and "
        "essentially all large-model training.")
    tbl(["Optimiser", "Typical LR", "When to choose it"],
        [["SGD + momentum 0.9", "0.1 with cosine decay (batch 256)",
          "CNNs on vision benchmarks; best final accuracy with a good schedule"],
         ["Adam / AdamW", "1e-3 (small nets), 1e-4 to 3e-4 (Transformers)",
          "Default for NLP, Transformers, GANs, RL, anything sparse or "
          "ill-conditioned"],
         ["RMSProp", "1e-3", "RNNs, some RL algorithms"],
         ["LAMB / LARS", "layer-wise scaled", "Very large batch training "
          "(32k+) where plain scaling diverges"],
         ["Lion", "3-10x smaller than Adam", "Memory-lean alternative: sign-based "
          "update, one state tensor instead of two"],
         ["Shampoo / K-FAC / Sophia", "problem-specific", "Second-order-ish "
          "methods; strong on large-scale pretraining, more complex"],
         ["L-BFGS", "line search", "Small full-batch deterministic problems only"]],
        widths=[18, 26, 56], bold_first=True)

    h2("Learning-rate schedules")
    p("The learning rate should usually be large early (fast progress, escaping "
      "poor regions) and small late (fine convergence). The schedule matters at "
      "least as much as the optimiser.")
    tbl(["Schedule", "Shape", "Use"],
        [["Step decay", "x0.1 at fixed epochs", "Classic ResNet recipes"],
         ["Cosine annealing", "smooth decay to ~0 over the run",
          "The modern default; often with restarts (SGDR)"],
         ["Linear warmup + decay", "rise for k steps, then decay",
          "Mandatory for Transformers and large batches"],
         ["OneCycle", "up then down, momentum inversely",
          "Fast convergence in few epochs; strong for fine-tuning"],
         ["Exponential", "eta * gamma^epoch", "Simple, needs tuning of gamma"],
         ["ReduceLROnPlateau", "cut when validation stalls",
          "Robust when you cannot predict run length"],
         ["Constant", "flat", "Debugging, or very short fine-tunes"]],
        widths=[22, 32, 46], bold_first=True)
    box("math", "Why warmup is needed",
        "At initialisation Adam's second-moment estimate v is based on very few "
        "samples, so its variance is huge and early steps can be wildly "
        "mis-scaled; simultaneously, in a deep residual stack the output "
        "distribution is far from its trained state, so early large steps do "
        "lasting damage. A linear warmup over 1-10k steps (or 1-5% of training) "
        "lets both stabilise. The larger the batch and the deeper the model, the "
        "more warmup you need.")

    h2("Batch size, learning rate, and their interaction")
    bul([
        "**Linear scaling rule:** multiply the batch size by k and multiply the "
        "learning rate by k, with warmup. Holds well up to batch sizes of a few "
        "thousand, then breaks down.",
        "**Square-root scaling** is sometimes better for Adam, since Adam already "
        "normalises by gradient magnitude.",
        "Small batches inject gradient noise, which acts as a regulariser and "
        "often improves generalisation; very large batches converge to sharper "
        "minima unless compensated with warmup, LARS/LAMB and more epochs.",
        "Batch size is chosen mostly by hardware: the largest that fits, rounded "
        "to a multiple of 8 (or 64) so tensor cores are used efficiently.",
        "**Gradient accumulation** simulates a larger batch on small memory; "
        "**gradient checkpointing** frees memory to enlarge the real batch.",
    ])

    h2("Finding the learning rate")
    code([
        "# LR range test (Smith): sweep the LR exponentially over one epoch and",
        "# plot loss against LR. Pick roughly one order of magnitude below the",
        "# point of steepest descent - NOT the minimum, which is already unstable.",
        "lrs, losses = [], []",
        "lr = 1e-7",
        "for xb, yb in train_dl:",
        "    for g in opt.param_groups: g['lr'] = lr",
        "    opt.zero_grad(set_to_none=True)",
        "    loss = lossf(model(xb.to(dev)), yb.to(dev))",
        "    loss.backward(); opt.step()",
        "    lrs.append(lr); losses.append(loss.item())",
        "    lr *= 1.1",
        "    if loss.item() > 4 * min(losses): break      # diverged; stop",
    ], "Listing 17.1 - The learning-rate range test: five minutes that saves days.")

    ex_ch17()

    h2("Gradient clipping and stability")
    eq(["if ||g|| > c :   g <- c * g / ||g||        (clip by global norm)"])
    p("Clip by **global norm** (across all parameters), not per-parameter, so the "
      "update direction is preserved. c = 1.0 is a standard default for "
      "Transformers and RNNs. If you must clip constantly, your learning rate is "
      "too high or your data contains pathological samples - clipping is a "
      "seatbelt, not a steering wheel.")

    box("expert", "Sharpness, flatness and SAM",
        "Solutions in flat regions of the loss surface tend to generalise better "
        "than those in sharp ones, because a flat minimum is robust to the shift "
        "between the training and test distributions. Sharpness-Aware "
        "Minimisation (SAM) makes this explicit: it takes an ascent step to the "
        "worst point within a small neighbourhood, computes the gradient THERE, "
        "and applies it at the original point. It roughly doubles the cost per "
        "step and reliably buys a point or two of accuracy on vision benchmarks.")

    h3("Exercises")
    bul([
        "Implement SGD, momentum, RMSProp and Adam in 20 lines each and race them "
        "on the Rosenbrock function, plotting the trajectories.",
        "Run the LR range test on a small CNN and compare the picked LR against a "
        "manual sweep of 5 values.",
        "Train the same model with cosine decay, step decay and a constant LR to "
        "the same number of epochs and compare final accuracy.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 18 ---
    chapter("Normalization Layers")
    p("Normalisation layers rescale intermediate activations so that each layer "
      "sees inputs with a stable distribution. They made deep networks trainable "
      "at practical learning rates, and every modern architecture contains one "
      "variety or another.")

    h2("Batch normalisation")
    eq(["mu_B    = (1/m) SUM_i x_i                    (per channel, over the batch)",
        "var_B   = (1/m) SUM_i (x_i - mu_B)^2",
        "x_hat_i = (x_i - mu_B) / sqrt(var_B + eps)",
        "y_i     = gamma * x_hat_i + beta            (learned scale and shift)"])
    p("gamma and beta preserve expressiveness - the layer can undo the "
      "normalisation if that is what the loss prefers. At inference time the "
      "batch statistics are replaced by **running averages** collected during "
      "training, which is exactly what `model.eval()` switches on.")
    tbl(["Benefit", "Mechanism"],
        [["Higher learning rates are stable", "Rescaling makes the loss surface "
          "smoother and bounds the effect of a large step"],
         ["Reduced sensitivity to initialisation", "The layer re-centres and "
          "re-scales whatever arrives"],
         ["A mild regularising effect", "Each sample's normalisation depends on "
          "the random batch it landed in - noise that acts like dropout"],
         ["Faster convergence", "Typically 2-5x fewer epochs on deep convnets"]],
        widths=[36, 64], bold_first=True)
    box("warn", "Batch norm's failure modes",
        "(1) Small batches: with batch size 2-8 the statistics are noisy and "
        "performance collapses - a real problem for detection and segmentation, "
        "where images are large. (2) Train/test mismatch: running statistics "
        "differ from batch statistics, causing a gap that appears only at "
        "evaluation. (3) Sequence models: statistics vary with position and "
        "padding. (4) Distributed training needs SyncBatchNorm to pool statistics "
        "across GPUs. (5) It leaks information between samples in a batch, which "
        "breaks some privacy and contrastive setups.")

    h2("The alternatives, and how they differ")
    diagram([
        "  Tensor (N, C, H, W). Shaded = the elements averaged together.",
        "",
        "  BatchNorm    : normalise over (N, H, W)  for each channel C",
        "  LayerNorm    : normalise over (C, H, W)  for each sample N",
        "  InstanceNorm : normalise over (H, W)     for each (N, C)",
        "  GroupNorm    : normalise over (C/g, H, W) for each sample and group",
        "  RMSNorm      : LayerNorm without mean subtraction; divide by RMS only",
    ], "Figure 18.1 - The normalisation family differs only in which axes are pooled.")
    tbl(["Layer", "Depends on batch?", "Standard use"],
        [["BatchNorm", "Yes", "CNNs with batch >= 32"],
         ["LayerNorm", "No", "Transformers, RNNs, any variable-length input"],
         ["RMSNorm", "No", "Modern LLMs - cheaper than LayerNorm, equally "
          "effective"],
         ["GroupNorm", "No", "Detection/segmentation with small batches (g = 32 "
          "is a good default)"],
         ["InstanceNorm", "No", "Style transfer, image generation"],
         ["Weight norm / spectral norm", "No", "Reparameterise or constrain the "
          "weights themselves; spectral norm stabilises GAN discriminators"]],
        widths=[24, 20, 56], bold_first=True)

    h2("Placement: pre-norm versus post-norm")
    eq(["Post-norm (original Transformer):  x <- Norm( x + Sublayer(x) )",
        "Pre-norm  (modern default):        x <- x + Sublayer( Norm(x) )"])
    p("Pre-norm keeps a clean identity path through the whole stack, so gradients "
      "reach the first layer without passing through a normalisation, and deep "
      "models train without a delicate warmup. Post-norm can reach slightly "
      "better final quality but is much harder to train deep. Every large "
      "language model of the last few years uses pre-norm (usually pre-RMSNorm).")
    box("expert", "What normalisation is actually doing",
        "The original 'internal covariate shift' explanation has not held up well "
        "under scrutiny. The better-supported account is that normalisation "
        "reparameterises the loss surface so that it is smoother (bounded "
        "Lipschitz constant of the gradient), which permits larger stable steps. "
        "A second effect is scale invariance: with a normalisation layer "
        "downstream, scaling a weight matrix by c leaves the output unchanged, so "
        "weight decay acts on the effective learning rate rather than on the "
        "function - which is why weight decay and normalisation interact in ways "
        "that surprise people.")

    h3("Exercises")
    bul([
        "Train a 20-layer MLP with and without BatchNorm at learning rates "
        "0.001, 0.01, 0.1 and tabulate which combinations converge.",
        "Replace BatchNorm with GroupNorm in a small CNN and compare accuracy at "
        "batch sizes 64, 8 and 2.",
        "Derive the BatchNorm backward pass and verify it numerically.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 19 ---
    chapter("Regularization for Deep Networks")
    p("Deep networks can memorise random labels, so they can certainly memorise "
      "your training set. Regularisation is how you push them towards solutions "
      "that generalise. The techniques below are cumulative - a strong recipe "
      "uses several at once.")

    h2("Dropout")
    p("During training, zero each unit independently with probability p and scale "
      "the survivors by 1/(1-p) so the expected activation is unchanged (inverted "
      "dropout). At evaluation, nothing is dropped.")
    bul([
        "**Why it works:** it prevents co-adaptation - no unit can rely on a "
        "specific partner being present - and it approximates an ensemble of "
        "exponentially many sub-networks that share weights.",
        "**Typical values:** 0.5 for wide fully connected layers, 0.1-0.3 in "
        "Transformers, and often 0 in convnets with BatchNorm, where the "
        "normalisation already supplies noise. **Spatial dropout** (drop whole "
        "channels) is the correct variant for convolutions.",
        "**Variants:** DropConnect drops weights instead of units; DropPath / "
        "stochastic depth drops entire residual blocks and is standard in modern "
        "vision transformers; DropBlock drops contiguous regions of a feature map.",
        "**Interaction warning:** dropout before BatchNorm changes the variance "
        "the normalisation sees, producing a train/test discrepancy. Put dropout "
        "after the normalisation, or omit one of the two.",
    ])

    h2("Weight decay")
    p("Weight decay shrinks weights towards zero each step. As Chapter 17 "
      "explained, use the **decoupled** form (AdamW). Two practical details are "
      "usually ignored and matter:")
    bul([
        "**Do not decay biases or normalisation parameters.** Decaying gamma and "
        "beta fights the normalisation layer and costs accuracy. Build two "
        "parameter groups.",
        "Typical values: 1e-4 for convnets with SGD, 0.01-0.1 for Transformers "
        "with AdamW. It interacts with the learning rate and the schedule; tune "
        "them together.",
    ])
    code([
        "decay, no_decay = [], []",
        "for name, param in model.named_parameters():",
        "    if not param.requires_grad:",
        "        continue",
        "    if param.ndim <= 1 or name.endswith('.bias') or 'norm' in name.lower():",
        "        no_decay.append(param)          # biases, LayerNorm/BatchNorm terms",
        "    else:",
        "        decay.append(param)             # weight matrices and conv kernels",
        "",
        "opt = torch.optim.AdamW([",
        "    {'params': decay,    'weight_decay': 0.05},",
        "    {'params': no_decay, 'weight_decay': 0.0},",
        "], lr=3e-4, betas=(0.9, 0.95))",
    ], "Listing 19.1 - Correct parameter grouping for weight decay.")

    h2("Early stopping")
    p("Monitor a validation metric, keep the best checkpoint, and stop when it "
      "has not improved for `patience` evaluations. Two rules: stop on the metric "
      "you actually care about, not on the training loss; and restore the best "
      "weights rather than keeping the last ones. Patience of 5-20 evaluations is "
      "typical; with a cosine schedule it is often better to train the full "
      "schedule and simply keep the best checkpoint.")

    h2("Augmentation and label-level regularisers")
    tbl(["Technique", "What it does", "Effect"],
        [["Mixup", "Train on convex combinations of two samples AND their labels",
          "Smoother decision boundaries, better calibration"],
         ["CutMix", "Paste a patch of one image into another; mix labels by area",
          "Strong for classification; forces use of the whole object"],
         ["CutOut / random erasing", "Blank a random rectangle",
          "Robustness to occlusion"],
         ["RandAugment / TrivialAugment", "Sample augmentation ops randomly with "
          "one or two hyperparameters", "Near-AutoAugment quality without the "
          "search cost"],
         ["Label smoothing", "Targets 1-eps instead of 1", "Less overconfidence, "
          "better calibration"],
         ["Noisy student / self-training", "Pseudo-label unlabelled data, train a "
          "larger student with noise", "Large gains when unlabelled data is "
          "plentiful"]],
        widths=[22, 42, 36], bold_first=True)
    eq(["Mixup:   x_mix = lam x_i + (1-lam) x_j,   y_mix = lam y_i + (1-lam) y_j",
        "         lam ~ Beta(alpha, alpha),  alpha in [0.1, 0.4] typically"])

    h2("Ensembling for deep networks")
    bul([
        "**Independent seeds:** train the same architecture 3-5 times and average "
        "the softmax outputs. Reliably the largest easy gain, and it also gives a "
        "usable uncertainty estimate (deep ensembles, Chapter 33).",
        "**Snapshot ensembles:** use a cyclic learning rate and save a checkpoint "
        "at each minimum; you get an ensemble for the price of one run.",
        "**Stochastic Weight Averaging (SWA):** average the WEIGHTS of "
        "checkpoints from the late phase of training with a constant or cyclic "
        "learning rate. Costs one model at inference, finds flatter minima, and "
        "is essentially free. Remember to recompute BatchNorm statistics "
        "afterwards.",
        "**Exponential moving average (EMA)** of weights: keep a shadow copy "
        "updated as `ema <- d*ema + (1-d)*w` with d around 0.999 and evaluate "
        "with it. Standard practice in diffusion models and semi-supervised "
        "learning.",
    ])

    h2("A regularisation recipe by data size")
    tbl(["Situation", "Recipe"],
        [["Small data (<10k), pretrained backbone available",
          "Freeze most layers, strong augmentation, dropout 0.3-0.5, weight decay, "
          "early stopping, 5-seed ensemble"],
         ["Medium data (10k-1M)", "Full fine-tune or train from scratch, "
          "RandAugment + Mixup, label smoothing 0.1, cosine schedule, EMA"],
         ["Large data (>10M)", "Weak augmentation, little or no dropout, weight "
          "decay, large batch with warmup - the data is the regulariser"],
         ["Noisy labels", "Label smoothing, symmetric or generalised cross-entropy, "
          "co-teaching, early stopping (networks fit clean data first)"]],
        widths=[26, 74], bold_first=True)

    h3("Exercises")
    bul([
        "Train a CNN on 5,000 CIFAR images with no regularisation, then add "
        "augmentation, then Mixup, then an ensemble; report the accuracy after "
        "each addition.",
        "Show that inverted dropout preserves the expected activation, and "
        "measure the variance it introduces.",
        "Implement SWA over the last 25% of training and compare against the best "
        "single checkpoint.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 20 ---
    chapter("Training in Practice: A Debugging Playbook")
    p("Most of the time lost in deep learning is lost to bugs that produce a "
      "plausible-looking but wrong result. This chapter is the ordered checklist "
      "that finds them.")

    h2("Start correctly")
    checklist("The first hour of any new model", [
        "Overfit a single batch of 8 samples to near-zero loss. If you cannot, "
        "the bug is in the model, loss or data pipeline - not in the "
        "hyperparameters. This is the single most valuable test in deep learning.",
        "Verify the loss at initialisation: for K balanced classes it should be "
        "about log(K) - 2.30 for 10 classes. A wildly different value means the "
        "output layer or the loss is wrong.",
        "Print shapes at every stage, once, and check them against what you "
        "intended.",
        "Visualise a batch after augmentation, with its labels. Half of all data "
        "bugs are visible immediately - wrong channel order, labels off by one, "
        "normalisation applied twice.",
        "Check the label mapping in both directions, and confirm that class "
        "indices in the loss match the ones in your evaluation code.",
        "Fix all seeds and record them; log the git commit, the config, and the "
        "data version.",
    ])

    h2("Symptom-to-cause table")
    tbl(["Symptom", "Likely causes", "What to try"],
        [["Loss is NaN", "Learning rate too high; log(0); division by zero; "
          "fp16 overflow; bad input values",
          "Lower LR; use logits-based losses; add eps; enable loss scaling; assert "
          "finite inputs"],
         ["Loss does not move", "LR too low; zero_grad missing; frozen "
          "parameters; dead ReLUs; broken data pipeline",
          "LR range test; check requires_grad; check gradient norms per layer"],
         ["Train loss falls, validation does not", "Overfitting, or a "
          "train/validation mismatch",
          "More regularisation and data; verify that both use identical "
          "preprocessing"],
         ["Validation better than training", "Dropout/augmentation active only in "
          "training (often normal), or leakage",
          "Compare at eval mode on the same data; audit the split"],
         ["Metrics good offline, bad in production", "Leakage, distribution "
          "shift, or skew between training and serving features",
          "Audit features; re-split by time; log serving inputs and compare "
          "distributions"],
         ["Results change wildly between runs", "Seed sensitivity, too-small "
          "validation set, unstable LR",
          "Average over seeds; enlarge validation; lower LR; add warmup"],
         ["GPU out of memory", "Batch too large; activations retained; memory "
          "leak from keeping loss tensors",
          "Reduce batch; use AMP and checkpointing; store `loss.item()`, not the "
          "tensor"],
         ["Training is slow", "Data loading is the bottleneck; small batch; "
          "unfused ops; CPU-GPU sync per step",
          "More workers + pin_memory; profile; AMP; torch.compile; avoid `.item()` "
          "inside the loop"]],
        widths=[22, 38, 40], bold_first=True)

    h2("Instrumentation worth having from day one")
    bul([
        "Log the training loss, the validation metric, the learning rate, the "
        "gradient global norm, and the weight norm - all against step, not epoch.",
        "Log per-layer gradient norms occasionally; a layer with a norm 1000x "
        "different from its neighbours is a bug.",
        "Log a few predictions and their inputs every N steps; looking at the data "
        "is diagnostic in a way that scalars are not.",
        "Track throughput (samples/second) and GPU utilisation. Under 80% "
        "utilisation almost always means the data pipeline, not the model.",
        "Use an experiment tracker (MLflow, Weights & Biases, TensorBoard, or a "
        "CSV plus a config file) so that a result from three weeks ago can be "
        "reproduced.",
    ])

    h2("Mixed precision and throughput")
    code([
        "scaler = torch.amp.GradScaler('cuda')",
        "for xb, yb in train_dl:",
        "    opt.zero_grad(set_to_none=True)",
        "    with torch.amp.autocast('cuda', dtype=torch.bfloat16):",
        "        loss = lossf(model(xb), yb)          # matmuls run in low precision",
        "    scaler.scale(loss).backward()            # loss scaling avoids fp16",
        "    scaler.unscale_(opt)                     # underflow in the gradients",
        "    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)",
        "    scaler.step(opt); scaler.update()",
    ], "Listing 20.1 - Automatic mixed precision: roughly 2x faster and half the "
       "activation memory. bfloat16 has fp32's exponent range and usually needs "
       "no loss scaling; fp16 does.")
    tbl(["Lever", "Typical speedup", "Cost"],
        [["Mixed precision (bf16/fp16)", "1.5-3x", "Rare numerical issues"],
         ["torch.compile / graph capture", "1.1-2x", "Compile time, occasional "
          "graph breaks"],
         ["Larger batch + scaled LR", "up to linear", "Memory; needs warmup"],
         ["Better data pipeline (workers, prefetch, webdataset)", "often 2x+",
          "Engineering time"],
         ["Gradient checkpointing", "0.7x speed", "Enables much larger models"],
         ["Multi-GPU DDP", "near-linear", "Communication; code complexity"],
         ["FSDP / ZeRO sharding", "enables huge models", "Communication overhead"]],
        widths=[36, 22, 42], bold_first=True)

    h2("Reproducibility")
    bul([
        "Seed Python, NumPy and the framework; set `torch.use_deterministic_"
        "algorithms(True)` when you need bit-exactness, and accept the slowdown.",
        "Pin library versions and record the CUDA/cuDNN version - kernel changes "
        "alter results.",
        "Version the data, not just the code. A hash of the dataset belongs in "
        "the run log.",
        "Save the full config with every checkpoint. A checkpoint whose "
        "hyperparameters are unknown is close to worthless.",
        "Accept that exact reproducibility across hardware is often impossible; "
        "aim instead for statistical reproducibility over seeds.",
    ])

    h3("Exercises")
    bul([
        "Deliberately introduce four bugs (missing zero_grad, wrong label order, "
        "missing eval mode, unnormalised inputs) and practise finding each from "
        "the loss curve alone.",
        "Profile a training step and determine whether you are data-bound or "
        "compute-bound.",
        "Reproduce one of your earlier results from its config and checkpoint "
        "only. If you cannot, fix your logging before doing anything else.",
    ], ordered=True)


# =============================================================================
#                        PART IV - ARCHITECTURES
# =============================================================================
def part4():
    part("Architectures",
         "Convolutional networks, recurrent networks, attention and Transformers, "
         "large language models, generative models, graph networks and "
         "self-supervised learning.")

    # --------------------------------------------------------------- Ch 21 ---
    chapter("Convolutional Neural Networks", newpage=False)
    p("A dense layer connecting a 224x224x3 image to 1,000 hidden units needs 150 "
      "million weights, treats neighbouring pixels as unrelated, and has to "
      "relearn every pattern separately at every position. Convolution fixes all "
      "three problems with two structural assumptions: **locality** (nearby "
      "pixels are related) and **translation equivariance** (a cat is a cat "
      "wherever it appears).")

    h2("The convolution operation")
    eq(["y[i, j] = SUM_c SUM_u SUM_v  w[c, u, v] * x[c, i + u, j + v]  +  b",
        "",
        "Output size:  O = floor( (I + 2P - K) / S ) + 1",
        "   I input size, K kernel, P padding, S stride",
        "Params of a conv layer: K*K*C_in*C_out + C_out",
        "FLOPs (multiply-adds): K*K*C_in*C_out*H_out*W_out"])
    diagram([
        "   input 5x5            kernel 3x3        output 3x3  (stride 1, no pad)",
        "   +--+--+--+--+--+      +--+--+--+        +--+--+--+",
        "   | a| b| c| .| .|      | 1| 0|-1|        | y| .| .|",
        "   +--+--+--+--+--+      +--+--+--+        +--+--+--+",
        "   | d| e| f| .| .|  *   | 1| 0|-1|   =    | .| .| .|",
        "   +--+--+--+--+--+      +--+--+--+        +--+--+--+",
        "   | g| h| i| .| .|      | 1| 0|-1|        | .| .| .|",
        "   +--+--+--+--+--+      +--+--+--+        +--+--+--+",
        "   y = a+d+g - (c+f+i)   <- this kernel detects vertical edges",
    ], "Figure 21.1 - A 3x3 convolution slides one small weight matrix over the "
       "whole input: parameter sharing in action.")
    box("key", "Three properties, one at a time",
        "SPARSE CONNECTIVITY: each output depends on a small patch, so cost is "
        "linear in image size instead of quadratic. PARAMETER SHARING: the same "
        "kernel is applied everywhere, so a feature learned in one corner "
        "transfers to all others - a massive reduction in parameters and a "
        "powerful regulariser. EQUIVARIANCE: shift the input and the feature map "
        "shifts identically; adding pooling or global average pooling converts "
        "equivariance into approximate INVARIANCE, which is what classification "
        "wants.")

    h2("The standard building blocks")
    tbl(["Layer", "What it does", "Typical use"],
        [["Conv 3x3", "The workhorse; two stacked 3x3 have the receptive field of "
          "one 5x5 with fewer parameters and more non-linearity", "Everywhere"],
         ["Conv 1x1", "Mixes channels only; changes depth cheaply",
          "Bottlenecks, projections, channel attention"],
         ["Stride 2 conv", "Downsamples while learning", "Modern replacement for "
          "pooling"],
         ["Max pool 2x2", "Downsamples by taking the maximum", "Classic; adds "
          "small translation invariance"],
         ["Global average pool", "Averages each channel to one number",
          "Replaces the huge final dense layer"],
         ["Transposed conv", "Learned upsampling", "Segmentation decoders, "
          "generators"],
         ["Dilated conv", "Inserts gaps in the kernel to enlarge the receptive "
          "field without cost", "Segmentation, audio (WaveNet)"],
         ["Depthwise separable", "Depthwise spatial conv + pointwise 1x1; about "
          "8-9x fewer FLOPs than a dense 3x3", "MobileNet and every efficient "
          "on-device model"]],
        widths=[18, 52, 30], bold_first=True)
    eq(["Standard 3x3 conv:      3*3*C_in*C_out    multiply-adds per position",
        "Depthwise separable:    3*3*C_in + C_in*C_out",
        "Ratio ~ 1/C_out + 1/9   ->  about 8-9x cheaper for C_out = 256"])

    h2("Receptive field - the quantity to reason about")
    eq(["RF_out = RF_in + (K - 1) * PROD(previous strides)"])
    p("A stack of ten 3x3 convolutions with stride 1 has a receptive field of "
      "21 pixels; if a decision needs context wider than that, the architecture "
      "cannot make it, no matter how much data you have. Downsampling, dilation "
      "and attention are the three ways to grow the receptive field quickly, and "
      "the choice among them defines much of modern architecture design.")

    ex_ch21()

    h2("A short history worth knowing")
    tbl(["Model", "Year", "Contribution"],
        [["LeNet-5", "1998", "Conv + pool + dense; digits; the template"],
         ["AlexNet", "2012", "ReLU, dropout, GPUs, augmentation; won ImageNet by a "
          "huge margin and started the era"],
         ["VGG", "2014", "Uniform 3x3 stacks; showed depth matters; very heavy"],
         ["GoogLeNet / Inception", "2014", "Multi-scale branches; 1x1 bottlenecks"],
         ["ResNet", "2015", "Residual connections; 152 layers trainable; the "
          "single most influential idea in the list"],
         ["DenseNet", "2016", "Concatenate all previous feature maps"],
         ["MobileNet / ShuffleNet", "2017", "Depthwise separable convolutions for "
          "phones"],
         ["EfficientNet", "2019", "Compound scaling of depth, width and resolution "
          "together"],
         ["ConvNeXt", "2022", "A convnet modernised with Transformer-era training "
          "recipes; matches ViT"]],
        widths=[22, 10, 68], bold_first=True)
    eq(["Residual block:   y = x + F(x)      (identity path + learned residual)",
        "Bottleneck block: 1x1 reduce -> 3x3 -> 1x1 expand, all with a skip"])

    h2("Beyond classification")
    bul([
        "**Object detection:** two-stage (Faster R-CNN: propose regions, then "
        "classify) versus one-stage (YOLO, SSD, RetinaNet with focal loss). "
        "Metrics: mAP at IoU thresholds. DETR reframes detection as set "
        "prediction with a Transformer and removes anchors and NMS.",
        "**Semantic segmentation:** per-pixel classification. U-Net's "
        "encoder-decoder with skip connections is still the standard in medical "
        "imaging; DeepLab adds dilated convolutions and multi-scale pooling.",
        "**Instance and panoptic segmentation:** Mask R-CNN adds a mask head to "
        "detection; panoptic unifies things and stuff.",
        "**Video:** 3D convolutions, two-stream (RGB + optical flow), or "
        "factorised (2+1)D convolutions; increasingly video Transformers.",
        "**Non-image uses:** 1D convolutions over time series and audio, and over "
        "text characters; convolution is about locality, not about pixels.",
    ])

    h2("Transfer learning - the default workflow for vision")
    code([
        "import torch, torchvision as tv, torch.nn as nn",
        "",
        "m = tv.models.resnet50(weights=tv.models.ResNet50_Weights.IMAGENET1K_V2)",
        "for p in m.parameters():",
        "    p.requires_grad = False              # stage 1: freeze the backbone",
        "m.fc = nn.Linear(m.fc.in_features, NUM_CLASSES)   # new head, trainable",
        "",
        "# stage 1: train the head only, LR ~1e-3, a few epochs",
        "# stage 2: unfreeze the last block(s) and fine-tune with a small LR",
        "for p in m.layer4.parameters():",
        "    p.requires_grad = True",
        "opt = torch.optim.AdamW([",
        "    {'params': m.layer4.parameters(), 'lr': 1e-4},   # discriminative LRs:",
        "    {'params': m.fc.parameters(),     'lr': 1e-3},   # deeper = smaller LR",
        "], weight_decay=1e-4)",
    ], "Listing 21.1 - Two-stage fine-tuning with discriminative learning rates.")
    box("tip", "How much to fine-tune",
        "Small dataset and similar domain: train the head only. Small dataset, "
        "different domain: fine-tune the last block or two with a small learning "
        "rate. Large dataset: fine-tune everything, still with a lower learning "
        "rate for early layers. Always keep the preprocessing (resize, mean/std "
        "normalisation) identical to what the backbone was pretrained with - "
        "this is a surprisingly common silent failure.")

    h3("Exercises")
    bul([
        "Compute the receptive field, parameter count and FLOPs of a 5-layer CNN "
        "by hand, then verify with a profiler.",
        "Implement a residual block and train a 20-layer plain CNN and a 20-layer "
        "ResNet on CIFAR-10; compare convergence.",
        "Replace every 3x3 convolution in a small CNN with a depthwise separable "
        "block; report the accuracy, parameter and latency changes.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 22 ---
    chapter("Sequence Models: RNN, LSTM and GRU")
    p("Sequences - text, speech, sensor streams, prices - have order and "
      "variable length. A recurrent network processes them one step at a time, "
      "carrying a hidden state that summarises everything seen so far.")
    eq(["h_t = tanh( W_hh h_(t-1) + W_xh x_t + b )",
        "y_t = W_hy h_t + b_y"])
    p("The same weights are used at every timestep - parameter sharing across "
      "time, exactly analogous to a convolution's sharing across space. Training "
      "uses **backpropagation through time**: unroll the network over the "
      "sequence and apply ordinary backpropagation, usually truncated to a window "
      "of a few hundred steps to bound memory.")

    h2("Why plain RNNs fail on long sequences")
    p("The gradient over T steps contains a factor `PROD_t (W_hh^T diag(tanh'))`. "
      "A repeated matrix product either vanishes or explodes exponentially in T. "
      "Exploding is easy to fix with clipping; vanishing is the hard one, and it "
      "means the network cannot connect an event at step 5 to a consequence at "
      "step 500.")

    h2("LSTM: a cell state with gates")
    eq(["f_t = sigma( W_f [h_(t-1), x_t] + b_f )        forget gate",
        "i_t = sigma( W_i [h_(t-1), x_t] + b_i )        input gate",
        "g_t = tanh ( W_g [h_(t-1), x_t] + b_g )        candidate",
        "o_t = sigma( W_o [h_(t-1), x_t] + b_o )        output gate",
        "c_t = f_t * c_(t-1) + i_t * g_t                CELL STATE (additive!)",
        "h_t = o_t * tanh(c_t)"])
    box("key", "The one line that matters",
        "c_t = f_t * c_(t-1) + i_t * g_t. The cell state is updated ADDITIVELY, "
        "not by a matrix multiplication, so the gradient path along c is a "
        "product of forget gates rather than of weight matrices. If the forget "
        "gate stays near 1, information and gradient flow for hundreds of steps. "
        "This is the same trick as a residual connection, invented for time.")
    p("**GRU** merges the forget and input gates into one update gate and drops "
      "the separate cell state: about 25% fewer parameters, usually "
      "indistinguishable in accuracy, and slightly faster. Try both; there is no "
      "reliable winner.")
    bul([
        "Initialise the **forget-gate bias to 1** so the cell remembers by "
        "default - a small change that historically made LSTMs much easier to "
        "train.",
        "**Bidirectional** RNNs run one pass in each direction and concatenate; "
        "only usable when the whole sequence is available (not for streaming or "
        "generation).",
        "Stack 2-4 layers; deeper recurrent stacks rarely help without residual "
        "connections between layers.",
        "**Variational (locked) dropout** applies the same mask at every timestep; "
        "ordinary per-step dropout destroys the recurrent signal.",
        "Pack padded sequences (`pack_padded_sequence`) so the network never "
        "consumes padding tokens.",
    ])

    h2("Sequence-to-sequence and the birth of attention")
    p("An encoder RNN compresses the input into a single fixed vector; a decoder "
      "RNN generates the output from it. The bottleneck is obvious: one vector "
      "cannot hold a 50-word sentence. Attention (Bahdanau, 2014) let the decoder "
      "look back at **all** encoder states, weighting them per output step:")
    eq(["score(s_t, h_i) -> alpha_ti = softmax_i(score)",
        "context c_t = SUM_i alpha_ti h_i",
        "decoder consumes [s_t ; c_t]"])
    p("This removed the bottleneck, gave interpretable alignments, and led "
      "directly to the conclusion of the next chapter: if attention is doing the "
      "work, the recurrence can be dropped entirely.")

    h2("When to still use an RNN in the 2020s")
    bul([
        "Streaming and low-latency inference with strict memory limits - an LSTM "
        "has O(1) state per step, while a Transformer's KV cache grows with "
        "length.",
        "Small on-device models over sensor streams, where a two-layer GRU of "
        "50k parameters is enough and a Transformer is not affordable.",
        "Very long sequences where quadratic attention is prohibitive - though "
        "**state-space models** (S4, Mamba) are now the stronger option: they "
        "keep the recurrent O(1) inference state while training in parallel like "
        "a convolution, and are competitive with Transformers on long-context "
        "tasks.",
        "Otherwise, for text and most sequence modelling, the default is a "
        "Transformer.",
    ])

    h3("Exercises")
    bul([
        "Implement an LSTM cell from the equations above and check it against "
        "`nn.LSTMCell`.",
        "Train a plain RNN, an LSTM and a GRU on the copy task (repeat a sequence "
        "after a delay of T steps) for T = 10, 50, 200 and plot accuracy against T.",
        "Add Bahdanau attention to a small seq2seq translation model and "
        "visualise the alignment matrix.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 23 ---
    chapter("Attention and the Transformer")
    p("The Transformer replaced recurrence with attention entirely. Its advantage "
      "is not only accuracy: every position is processed in parallel during "
      "training, so the architecture scales with hardware in a way RNNs never "
      "could. Understanding this chapter thoroughly is the highest-value "
      "investment in modern deep learning.")

    h2("Scaled dot-product attention")
    eq(["Attention(Q, K, V) = softmax( Q K^T / sqrt(d_k) ) V",
        "",
        "Q = X W_Q   (n, d_k)      queries: what am I looking for?",
        "K = X W_K   (n, d_k)      keys:    what do I contain?",
        "V = X W_V   (n, d_v)      values:  what do I pass on?"])
    box("intuit", "The database analogy",
        "Each token emits a QUERY describing what it needs, and every token "
        "offers a KEY describing what it has. The dot product query-dot-key "
        "scores the match; softmax turns the scores into weights that sum to one; "
        "the output is the weighted average of the VALUES. Unlike a hash lookup, "
        "the match is soft - every token contributes something, in proportion to "
        "relevance.")
    box("math", "Why divide by sqrt(d_k)",
        "If the components of q and k are independent with zero mean and unit "
        "variance, then q.k has variance d_k. With d_k = 64 the logits have a "
        "standard deviation of 8, and softmax of such large values is nearly "
        "one-hot with vanishing gradients. Dividing by sqrt(d_k) restores unit "
        "variance and keeps the softmax in its responsive range.")

    h2("Multi-head attention")
    eq(["head_i = Attention(X W_Q^i, X W_K^i, X W_V^i),   i = 1..h",
        "MHA(X) = Concat(head_1, ..., head_h) W_O",
        "typically d_k = d_v = d_model / h"])
    p("Splitting the representation into h heads lets the layer attend to "
      "different relationships at once - one head tracking syntactic dependency, "
      "another coreference, another position. The total compute is the same as "
      "one head of full width, so it is free capacity in the useful sense.")
    diagram([
        "   x --> LayerNorm --> Multi-Head Attention --+--> (+) -->",
        "   |                                          |    ^",
        "   +------------------------------------------|----+  residual",
        "                                              |",
        "   --> LayerNorm --> FeedForward (d -> 4d -> d) --> (+) -->",
        "   |                                                 ^",
        "   +-------------------------------------------------+  residual",
        "",
        "   One pre-norm Transformer block. Stack N of these.",
    ], "Figure 23.1 - The block: attention mixes across tokens, the feedforward "
       "mixes across channels, residuals carry the signal.")

    h2("The other components")
    bul([
        "**Position-wise feedforward:** two linear layers with a non-linearity, "
        "usually expanding by 4x. It holds most of the parameters and, on current "
        "evidence, most of the model's factual knowledge. Modern LLMs use SwiGLU "
        "here, which needs three matrices at roughly 2/3 the width.",
        "**Residual connections and normalisation** around every sublayer "
        "(pre-norm; see Chapter 18).",
        "**Causal masking** in decoders: set the scores for future positions to "
        "-inf before the softmax so a token can never see its own future. This "
        "single mask is what makes parallel training of an autoregressive model "
        "possible.",
        "**Cross-attention** in encoder-decoder models: queries come from the "
        "decoder, keys and values from the encoder.",
    ])

    h2("Positional information")
    p("Attention is permutation-equivariant - shuffle the tokens and the outputs "
      "shuffle with them. Order must be injected explicitly.")
    tbl(["Scheme", "How", "Properties"],
        [["Sinusoidal (original)", "Add fixed sin/cos of varying frequency",
          "No parameters; some extrapolation to longer sequences"],
         ["Learned absolute", "A trainable embedding per position",
          "Simple; cannot exceed the trained length"],
         ["Relative (T5, Shaw)", "Bias the attention logits by the distance i-j",
          "Generalises across lengths; used in encoder models"],
         ["RoPE (rotary)", "Rotate q and k by an angle proportional to position",
          "Relative by construction, extrapolates well, the de facto standard in "
          "modern LLMs; extendable by frequency scaling (YaRN, NTK)"],
         ["ALiBi", "Add a linear distance penalty to attention logits",
          "Very simple, strong length extrapolation"]],
        widths=[20, 38, 42], bold_first=True)

    h2("Complexity and the efficiency ladder")
    eq(["Time:   O(n^2 d)      Memory (naive):  O(n^2)",
        "n = sequence length, d = model dimension"])
    p("Quadratic cost in sequence length is the Transformer's defining "
      "limitation, and a decade of work exists to soften it:")
    tbl(["Technique", "Idea", "Status"],
        [["FlashAttention", "Tile the computation in SRAM; never materialise the "
          "n x n matrix. Exact, IO-aware", "Universal in practice; the first "
          "thing to enable"],
         ["Multi-query / grouped-query attention", "Share K and V across heads",
          "Shrinks the KV cache 8-64x; standard in modern LLMs"],
         ["Sliding window / local attention", "Attend within a window only",
          "Mistral-style; combine with a few global tokens"],
         ["Sparse patterns (Longformer, BigBird)", "Local + global + random",
          "Long documents"],
         ["Linear attention (Performer, Linformer)", "Kernel or low-rank "
          "approximation of softmax", "O(n); some quality loss"],
         ["State-space models (S4, Mamba)", "Structured recurrence, parallel "
          "training, O(1) inference state", "Strong for very long context"],
         ["KV cache quantisation / paging", "Store the cache in 8 or 4 bits, in "
          "pages", "The main memory lever at serving time"]],
        widths=[26, 42, 32], bold_first=True)

    h2("Implementing attention")
    code([
        "import torch, torch.nn as nn, torch.nn.functional as F",
        "",
        "class MultiHeadSelfAttention(nn.Module):",
        "    def __init__(self, d_model, n_heads, causal=True, p=0.0):",
        "        super().__init__()",
        "        assert d_model % n_heads == 0",
        "        self.h, self.dk = n_heads, d_model // n_heads",
        "        self.qkv  = nn.Linear(d_model, 3 * d_model, bias=False)",
        "        self.proj = nn.Linear(d_model, d_model, bias=False)",
        "        self.causal, self.p = causal, p",
        "",
        "    def forward(self, x):                       # x: (B, T, D)",
        "        B, T, D = x.shape",
        "        q, k, v = self.qkv(x).split(D, dim=2)",
        "        # (B, T, D) -> (B, heads, T, dk)",
        "        q = q.view(B, T, self.h, self.dk).transpose(1, 2)",
        "        k = k.view(B, T, self.h, self.dk).transpose(1, 2)",
        "        v = v.view(B, T, self.h, self.dk).transpose(1, 2)",
        "        # FlashAttention kernel: exact, memory-efficient, fused",
        "        y = F.scaled_dot_product_attention(",
        "                q, k, v, is_causal=self.causal,",
        "                dropout_p=self.p if self.training else 0.0)",
        "        y = y.transpose(1, 2).contiguous().view(B, T, D)",
        "        return self.proj(y)",
        "",
        "# The explicit form, for understanding only:",
        "#   att = (q @ k.transpose(-2,-1)) / self.dk**0.5",
        "#   att = att.masked_fill(mask == 0, float('-inf')).softmax(-1)",
        "#   y   = att @ v",
    ], "Listing 23.1 - Multi-head self-attention. The commented lines are the "
       "equations; the live code is what you should actually run.")

    ex_ch23()

    h2("The three architectural families")
    tbl(["Family", "Masking", "Trained by", "Examples", "Best at"],
        [["Encoder-only", "Bidirectional", "Masked token prediction",
          "BERT, RoBERTa, DeBERTa, ViT", "Classification, retrieval, embeddings"],
         ["Decoder-only", "Causal", "Next-token prediction",
          "GPT family, Llama, Mistral", "Generation, few-shot, chat - the "
          "dominant design"],
         ["Encoder-decoder", "Both", "Span corruption / seq2seq",
          "T5, BART, Whisper", "Translation, summarisation, speech"]],
        widths=[16, 14, 22, 24, 24], bold_first=True)

    h2("Transformers outside text")
    bul([
        "**Vision Transformer (ViT):** split the image into 16x16 patches, embed "
        "each as a token, add positional embeddings, run a standard encoder. "
        "Needs large data or strong augmentation and distillation (DeiT) because "
        "it lacks the convolutional inductive bias - which is also why it "
        "eventually surpasses convnets given enough data.",
        "**Swin Transformer:** hierarchical windows with shifting - reintroduces "
        "locality and multi-scale structure for detection and segmentation.",
        "**Audio:** Whisper (encoder-decoder over log-mel spectrograms), "
        "Conformer (convolution + attention).",
        "**Multimodal:** CLIP aligns image and text encoders with a contrastive "
        "loss; modern vision-language models feed image patch embeddings into an "
        "LLM's token stream.",
        "**Time series and sensor data:** patch-based Transformers (PatchTST) are "
        "now competitive with classical methods, though strong linear baselines "
        "remain surprisingly hard to beat.",
    ])

    h3("Exercises")
    bul([
        "Implement attention with explicit einsum and verify it matches "
        "`scaled_dot_product_attention` to 1e-5.",
        "Remove the sqrt(d_k) scaling and plot the entropy of the attention "
        "weights during the first 200 steps.",
        "Train a 4-layer character-level decoder-only Transformer on a small text "
        "corpus and sample from it. This is the single best exercise in this book.",
        "Visualise attention maps for a trained model and check whether any head "
        "has a recognisable role.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 24 ---
    chapter("Large Language Models")
    p("An LLM is a decoder-only Transformer trained to predict the next token on "
      "a very large text corpus, then adapted to follow instructions. Everything "
      "surprising about them - in-context learning, reasoning, code generation - "
      "emerges from that one objective at scale.")

    h2("Tokenization")
    bul([
        "**Byte-pair encoding (BPE)** and its variants (WordPiece, Unigram, "
        "SentencePiece) build a vocabulary by repeatedly merging the most "
        "frequent adjacent pair, producing subword units. Common words become one "
        "token; rare words split into pieces; nothing is ever out-of-vocabulary.",
        "Typical vocabularies are 32k-256k tokens. English averages roughly "
        "0.75 words per token; code and non-Latin scripts are considerably less "
        "efficient, which is a real cost and fairness issue.",
        "Tokenisation explains several famous failure modes: character counting, "
        "arithmetic on long numbers, and reversal tasks are hard because the model "
        "never sees characters.",
        "Byte-level fallbacks guarantee coverage of any input; some recent work "
        "removes tokenisation entirely in favour of byte or patch-level models.",
    ])

    h2("Pretraining")
    eq(["Objective:  maximise SUM_t log P(x_t | x_<t ; theta)",
        "Loss:       cross-entropy;   Perplexity = exp(cross-entropy)"])
    tbl(["Ingredient", "Current practice"],
        [["Data", "Trillions of tokens: filtered web crawl, code, books, "
          "scientific text. Quality filtering, deduplication and decontamination "
          "matter more than raw volume"],
         ["Architecture", "Decoder-only, pre-RMSNorm, RoPE, SwiGLU feedforward, "
          "grouped-query attention, no biases"],
         ["Optimiser", "AdamW, beta2 about 0.95, cosine decay with warmup, "
          "gradient clipping at 1.0, weight decay 0.1"],
         ["Parallelism", "Data + tensor + pipeline + sequence parallelism; ZeRO/"
          "FSDP sharding of optimiser state"],
         ["Precision", "bf16 compute with fp32 master weights; selective "
          "activation checkpointing"],
         ["Context", "4k-1M tokens, usually extended after the main run by "
          "adjusting RoPE frequencies and training on long documents"]],
        widths=[18, 82], bold_first=True)
    box("key", "Scaling laws",
        "Loss falls as a smooth power law in parameters N, data D and compute C - "
        "L(N) = (Nc/N)^a + irreducible. The Chinchilla result showed that for a "
        "fixed compute budget the optimum is roughly 20 tokens per parameter, and "
        "that most earlier models were badly undertrained on data rather than too "
        "small. In practice, inference cost now dominates for deployed models, so "
        "the industry deliberately overtrains smaller models far past Chinchilla "
        "optimality - a 7B model trained on 10-15T tokens is cheaper to serve "
        "forever than a 30B model trained to the same loss.")

    h2("Post-training: from predictor to assistant")
    bul([
        "**Supervised fine-tuning (SFT):** train on curated instruction-response "
        "pairs. A few thousand high-quality examples change behaviour "
        "dramatically; quality dominates quantity.",
        "**RLHF:** collect human preference comparisons, fit a reward model, then "
        "optimise the policy with PPO against that reward plus a KL penalty to "
        "stay near the SFT model. Powerful and operationally complex.",
        "**DPO and friends:** skip the explicit reward model - a closed-form loss "
        "on preference pairs directly optimises the same objective. Much simpler, "
        "now the common choice; variants include IPO, KTO, ORPO and SimPO.",
        "**RLAIF / Constitutional AI:** use model-generated critiques and "
        "preferences against a written set of principles, reducing the human "
        "labelling burden.",
        "**Reasoning training:** reinforcement learning on verifiable outcomes "
        "(maths, code tests) trains models to produce long chains of thought "
        "before answering, trading inference compute for accuracy.",
    ])

    h2("Parameter-efficient fine-tuning")
    eq(["LoRA:   W' = W + (alpha/r) B A,   A in R^(r x d),  B in R^(d x r),  r << d",
        "Train A and B only; W stays frozen. Merge B A into W at deployment for",
        "zero added latency."])
    tbl(["Method", "Trainable share", "Notes"],
        [["Full fine-tune", "100%", "Best quality, needs ~16 bytes/param of "
          "optimiser + gradient memory"],
         ["LoRA", "0.1-1%", "The default; r = 8-64, applied to attention and "
          "often MLP projections"],
         ["QLoRA", "0.1-1%", "Base model quantised to 4-bit NF4, LoRA adapters in "
          "bf16 - fine-tunes a 70B model on a single 48 GB GPU"],
         ["DoRA / rsLoRA", "0.1-1%", "Refinements on the LoRA parameterisation"],
         ["Prefix / prompt tuning", "<0.1%", "Learn virtual tokens; weaker but "
          "extremely light"],
         ["Adapters", "1-5%", "Small bottleneck modules inserted per layer; add "
          "inference latency unless merged"]],
        widths=[22, 18, 60], bold_first=True)

    h2("Inference: what actually costs money")
    bul([
        "Generation is **memory-bandwidth bound**, not compute bound: each token "
        "requires reading all weights. This is why quantization (Chapter 28) "
        "speeds up generation almost proportionally to the bit width.",
        "**KV cache** size = 2 * layers * heads_kv * head_dim * seq_len * "
        "batch * bytes. For long contexts it exceeds the weights themselves; "
        "grouped-query attention, paged attention (vLLM) and cache quantisation "
        "are the standard mitigations.",
        "**Speculative decoding:** a small draft model proposes k tokens, the "
        "large model verifies them in one forward pass - a 2-3x speedup with "
        "identical output distribution.",
        "**Batching** (continuous/in-flight batching) is what makes serving "
        "economical: it converts a bandwidth-bound workload into a "
        "compute-bound one.",
        "**Sampling controls:** temperature, top-k, top-p (nucleus), repetition "
        "and presence penalties. Temperature 0 is deterministic-greedy; higher "
        "temperature increases diversity and error rate together.",
    ])

    ex_ch24()

    h2("Using LLMs well")
    bul([
        "**Prompting:** state the role, the task, the constraints, and the output "
        "format explicitly; give 2-5 examples for a format-sensitive task; ask "
        "for reasoning before the answer when the task needs it; request "
        "structured output (JSON schema) when a program will parse it.",
        "**Retrieval-augmented generation (RAG):** chunk documents, embed them, "
        "retrieve the top-k by vector similarity (plus keyword search - hybrid "
        "retrieval beats either alone), rerank, and put the evidence in the "
        "prompt with citations. This is the standard way to give a model private, "
        "current, verifiable knowledge without training.",
        "**Tool use / agents:** let the model call functions - search, a "
        "calculator, a database, code execution - and loop on the results. "
        "Reliability comes from constraining the action space and validating "
        "every result, not from longer prompts.",
        "**Evaluation:** build a fixed test set of real inputs with expected "
        "properties; use exact checks where possible, an LLM judge with a rubric "
        "where not, and always keep a human-reviewed sample. Track regressions "
        "like any other software test.",
    ])
    box("warn", "The failure modes to design around",
        "Hallucination (confident fabrication) - mitigate with retrieval, "
        "citations and abstention instructions. Prompt injection - never let "
        "untrusted text carry authority; separate data from instructions and "
        "constrain tools. Context-length degradation - relevant facts placed in "
        "the middle of a long context are recalled least well. Non-determinism - "
        "even at temperature 0, batching and kernel choice can change outputs. "
        "Data contamination - benchmark scores may reflect memorised test sets.")

    h3("Exercises")
    bul([
        "Compute the KV-cache size for a 7B model (32 layers, 32 heads, head_dim "
        "128) at 8k context in fp16, and again with 8 KV heads (GQA).",
        "Fine-tune a small open model with LoRA on 500 instruction pairs and "
        "measure the change on a held-out set you wrote yourself.",
        "Build a minimal RAG pipeline over 200 of your own documents; measure "
        "answer accuracy with and without retrieval.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 25 ---
    chapter("Generative Models: Autoencoders, VAEs, GANs and Diffusion")
    p("A discriminative model learns P(y|x). A generative model learns P(x), or "
      "P(x|condition), and can therefore produce new samples. The families below "
      "differ in how they make the intractable business of modelling a "
      "high-dimensional distribution tractable.")

    h2("Autoencoders")
    eq(["z = Encoder(x)      x_hat = Decoder(z)      L = ||x - x_hat||^2"])
    p("A bottleneck forces a compressed representation. A linear autoencoder with "
      "squared loss recovers the PCA subspace exactly; non-linear ones learn "
      "curved manifolds. Variants: **denoising** (reconstruct a clean input from "
      "a corrupted one - the ancestor of both BERT and diffusion), **sparse** "
      "(penalise activations), **contractive** (penalise the Jacobian). Plain "
      "autoencoders are useful for compression, denoising and anomaly detection, "
      "but their latent space has holes - sampling a random z usually decodes to "
      "nonsense.")

    h2("Variational autoencoders")
    p("A VAE makes the latent space a proper probability distribution. The "
      "encoder outputs a mean and log-variance; a sample is drawn; the decoder "
      "reconstructs. The loss is the **evidence lower bound**:")
    eq(["ELBO = E_q(z|x)[ log p(x|z) ]  -  KL( q(z|x) || p(z) )",
        "       \\_____ reconstruction _____/   \\____ regulariser ____/",
        "",
        "Reparameterisation: z = mu + sigma * eps,  eps ~ N(0, I)"])
    box("math", "Why the reparameterisation trick is necessary",
        "You cannot backpropagate through 'sample from N(mu, sigma)' because the "
        "sampling node has no derivative with respect to mu and sigma. Writing "
        "z = mu + sigma * eps moves the randomness into eps, which carries no "
        "parameters, leaving a deterministic differentiable path to mu and sigma. "
        "This trick is the reason VAEs train with ordinary gradient descent, and "
        "it reappears throughout probabilistic deep learning.")
    bul([
        "**Posterior collapse:** with a powerful decoder the KL term can drive "
        "q(z|x) to the prior and the latent is ignored. Fix with KL annealing, "
        "free bits, or a weaker decoder.",
        "**beta-VAE** scales the KL term to trade reconstruction quality against "
        "disentangled, interpretable latents.",
        "**VQ-VAE** replaces the continuous latent with a discrete codebook; it "
        "underpins modern image and audio tokenisers, which is how images enter "
        "and leave a Transformer.",
        "VAE samples tend to be blurry because the Gaussian likelihood averages "
        "over plausible reconstructions.",
    ])

    h2("Generative adversarial networks")
    eq(["min_G max_D  E_x[ log D(x) ] + E_z[ log(1 - D(G(z))) ]"])
    p("A generator turns noise into samples; a discriminator tries to tell real "
      "from fake; they train against each other. At the theoretical optimum the "
      "generator matches the data distribution and the discriminator is at chance "
      "everywhere. GANs produce the sharpest images of any family per unit of "
      "inference compute, and they are notoriously unstable to train.")
    tbl(["Problem", "Cause", "Standard fixes"],
        [["Mode collapse", "The generator finds a few outputs that fool D and "
          "stops exploring", "Minibatch discrimination, unrolled GAN, WGAN-GP, "
          "diverse conditioning"],
         ["Vanishing generator gradient", "D wins too easily",
          "Non-saturating loss, WGAN with Lipschitz constraint, weaker D"],
         ["Training oscillation", "It is a two-player game, not a minimisation",
          "Two time-scale update rule (different LRs), spectral normalisation, EMA "
          "of generator weights"],
         ["No usable likelihood", "Implicit model", "Evaluate with FID/KID and "
          "human study; do not expect a density"]],
        widths=[22, 34, 44], bold_first=True)
    p("Landmarks: DCGAN (convolutional recipe), WGAN-GP (Wasserstein distance "
      "with a gradient penalty), Pix2Pix and CycleGAN (paired and unpaired "
      "translation), StyleGAN (style-based generator, still the reference for "
      "face synthesis), and SRGAN for super-resolution.")

    h2("Diffusion models")
    p("Diffusion is now the dominant family for images, audio and video. The idea "
      "is disarmingly simple: destroy data with noise in small steps, then learn "
      "to reverse each step.")
    eq(["Forward:  q(x_t | x_(t-1)) = N( sqrt(1-b_t) x_(t-1), b_t I )",
        "Closed form:  x_t = sqrt(a_bar_t) x_0 + sqrt(1 - a_bar_t) * eps",
        "Training loss (DDPM):   L = E || eps - eps_theta(x_t, t) ||^2",
        "i.e. a network that predicts the noise that was added."])
    diagram([
        "   x0 --noise--> x1 --noise--> ... --noise--> xT ~ N(0, I)      FORWARD",
        "   x0 <--denoise-- x1 <--denoise-- ... <--denoise-- xT          REVERSE",
        "        ^ the network eps_theta(x_t, t) predicts the noise at each step",
    ], "Figure 25.1 - Diffusion: a fixed corruption process and a learned reversal.")
    bul([
        "**Architecture:** a U-Net with residual blocks, self-attention at low "
        "resolutions, and a timestep embedding; increasingly a Transformer (DiT) "
        "instead.",
        "**Latent diffusion** runs the process in the latent space of a VAE "
        "rather than in pixels - roughly a 48x reduction in compute, and the "
        "reason Stable Diffusion runs on consumer hardware.",
        "**Conditioning:** cross-attention on text embeddings; "
        "**classifier-free guidance** trains with and without the condition and "
        "extrapolates at sampling time, `eps = eps_uncond + w(eps_cond - "
        "eps_uncond)`, trading diversity for prompt fidelity.",
        "**Samplers:** DDPM needs hundreds of steps; DDIM, DPM-Solver++ and flow "
        "matching reduce this to 10-50. Distillation (progressive, consistency, "
        "adversarial) reaches 1-4 steps.",
        "**Flow matching / rectified flow** reframes the same idea as learning a "
        "velocity field along straight paths between noise and data - simpler "
        "objective, fewer steps, and the current direction of the field.",
    ])
    box("key", "Why diffusion beat GANs",
        "Diffusion replaces one impossibly hard problem - map noise to a complex "
        "distribution in a single shot, judged by an adversary - with a thousand "
        "easy, stable regression problems. The training signal is a plain "
        "mean-squared error, so there is no minimax game, no mode collapse, and "
        "scaling behaves predictably. The cost is inference: many network "
        "evaluations per sample, which is exactly what step-distillation research "
        "attacks.")

    h2("The other families, briefly")
    tbl(["Family", "Mechanism", "Trade-off"],
        [["Autoregressive (PixelCNN, LLMs)", "Factorise P(x) into a product of "
          "conditionals", "Exact likelihood, best quality on text; slow "
          "sequential sampling"],
         ["Normalising flows", "Invertible transforms with tractable Jacobians",
          "Exact likelihood and fast sampling; architecturally constrained"],
         ["Energy-based models", "Learn an unnormalised energy",
          "Very flexible; sampling requires MCMC"],
         ["Consistency models", "Learn a direct map from any noise level to data",
          "One-to-few step sampling; distilled from diffusion"]],
        widths=[24, 34, 42], bold_first=True)

    h2("Evaluating generative models")
    bul([
        "**FID** compares the mean and covariance of Inception features between "
        "real and generated sets - lower is better, but it is sensitive to sample "
        "count and preprocessing, and it rewards matching the training "
        "distribution rather than quality per se.",
        "**Precision/recall for generative models** separates fidelity from "
        "coverage - useful when FID hides mode dropping.",
        "**CLIP score** measures prompt adherence for text-to-image.",
        "**Human evaluation** remains the ground truth; report it with proper "
        "sample sizes and blinding.",
        "For likelihood-based models, report bits-per-dimension; never compare it "
        "against a GAN, which has none.",
    ])

    h3("Exercises")
    bul([
        "Train an autoencoder and a VAE on MNIST; interpolate between two latent "
        "codes in each and compare the decoded paths.",
        "Implement DDPM training on 32x32 images in under 150 lines and sample "
        "with both DDPM and DDIM; compare step counts for equal quality.",
        "Train a small DCGAN and deliberately induce mode collapse by making the "
        "discriminator too strong; then fix it.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 26 ---
    chapter("Graph Neural Networks")
    p("Molecules, road networks, social graphs, program dependency graphs and "
      "meshes are not grids or sequences. A GNN generalises convolution to "
      "arbitrary graphs by passing messages along edges.")

    h2("Message passing")
    eq(["m_v^(k)  = AGGREGATE( { M(h_u^(k-1), h_v^(k-1), e_uv) : u in N(v) } )",
        "h_v^(k)  = UPDATE( h_v^(k-1), m_v^(k) )",
        "",
        "AGGREGATE must be permutation-invariant: sum, mean, max, or attention."])
    tbl(["Model", "Aggregation", "Character"],
        [["GCN", "Normalised mean: D^-1/2 A D^-1/2 H W",
          "Simple, strong baseline, spectral motivation"],
         ["GraphSAGE", "Mean/LSTM/max over a sampled neighbourhood",
          "Scales to large graphs by sampling; inductive"],
         ["GAT", "Attention-weighted neighbours",
          "Learns which neighbours matter; multi-head"],
         ["GIN", "Sum with an MLP", "Provably as expressive as the "
          "Weisfeiler-Lehman test - the most expressive of the simple "
          "message-passing schemes"],
         ["MPNN / SchNet / DimeNet", "Physics-aware messages with distances and "
          "angles", "Molecular property prediction, force fields"],
         ["Graph Transformer", "Full attention plus structural encodings",
          "Avoids over-squashing; needs positional encodings for graphs"]],
        widths=[22, 34, 44], bold_first=True)

    h2("Tasks and readouts")
    bul([
        "**Node classification:** predict a label per node (fraud in a "
        "transaction graph, role in a social network). Often transductive.",
        "**Link prediction:** score whether an edge exists - recommendation, "
        "knowledge-graph completion.",
        "**Graph classification/regression:** pool node embeddings into one "
        "vector (sum, mean, max, or a learned pooling) and predict - molecular "
        "property prediction is the canonical case.",
        "**Generation:** produce new graphs, e.g. candidate molecules, often with "
        "diffusion over adjacency and node features.",
    ])

    h2("The characteristic problems")
    tbl(["Problem", "Description", "Mitigation"],
        [["Over-smoothing", "After many layers all node embeddings converge to "
          "the same vector", "2-4 layers; residual/jumping-knowledge connections; "
          "PairNorm; initial-residual (GCNII)"],
         ["Over-squashing", "Information from an exponentially growing "
          "neighbourhood is compressed into a fixed vector",
          "Graph rewiring, virtual global nodes, graph Transformers"],
         ["Scalability", "Neighbourhood explosion when sampling k hops",
          "Neighbour sampling (GraphSAGE), cluster-based batching (Cluster-GCN), "
          "historical embeddings"],
         ["Expressiveness limit", "Message passing cannot distinguish some "
          "non-isomorphic graphs (1-WL bound)",
          "Add structural or positional features, subgraph counts, or higher-order "
          "schemes"],
         ["Heterophily", "Connected nodes often have DIFFERENT labels, breaking "
          "the smoothing assumption", "Separate self and neighbour "
          "transformations; signed or higher-order aggregation"]],
        widths=[18, 42, 40], bold_first=True)
    box("tip", "Before reaching for a GNN",
        "Test a strong tabular baseline with hand-made graph features - degree, "
        "neighbour label counts, PageRank, triangle counts, embeddings from "
        "node2vec - fed to gradient boosting. On many industrial graph problems "
        "this matches or beats a GNN at a fraction of the engineering cost. Use a "
        "GNN when the relational structure is genuinely the signal and the "
        "features alone are weak.")

    h3("Exercises")
    bul([
        "Implement a 2-layer GCN in raw PyTorch using a sparse adjacency matrix "
        "and train it on Cora.",
        "Demonstrate over-smoothing: plot the average pairwise cosine similarity "
        "of node embeddings against the number of layers, 1 to 12.",
        "Compare a GNN against gradient boosting on hand-crafted graph features "
        "for the same node-classification task.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 27 ---
    chapter("Self-Supervised and Transfer Learning")
    p("Labels are expensive; raw data is not. Self-supervised learning invents a "
      "supervised task out of unlabelled data, learns a representation from it, "
      "and transfers that representation to the task you actually care about with "
      "a fraction of the labels.")

    h2("Pretext tasks by modality")
    tbl(["Modality", "Objective", "Representative methods"],
        [["Text", "Predict the next token; predict masked tokens; corrupt and "
          "reconstruct spans", "GPT, BERT, T5, ELECTRA"],
         ["Images - contrastive", "Two augmented views of the same image should "
          "match; different images should not", "SimCLR, MoCo, CLIP (image-text)"],
         ["Images - non-contrastive", "Match views without negatives, avoiding "
          "collapse by architecture", "BYOL, SimSiam, DINO, DINOv2"],
         ["Images - generative", "Mask 75% of patches and reconstruct",
          "MAE, BEiT, SimMIM"],
         ["Audio", "Contrastive prediction of masked latent speech units",
          "wav2vec 2.0, HuBERT, BEATs"],
         ["Video", "Predict future frames, ordering, or masked spatio-temporal "
          "patches", "VideoMAE, V-JEPA"],
         ["Time series / sensors", "Masked reconstruction, contrastive over "
          "augmented windows", "TS2Vec, TF-C, PatchTST pretraining"],
         ["Graphs", "Mask node or edge attributes; contrast subgraphs",
          "GraphMAE, GRACE"]],
        widths=[18, 42, 40], bold_first=True)

    h2("Contrastive learning in detail")
    eq(["InfoNCE:  L = -log [ exp(sim(z_i, z_j)/tau) /",
        "                     SUM_k exp(sim(z_i, z_k)/tau) ]",
        "sim = cosine similarity, tau = temperature (0.05-0.2)"])
    bul([
        "**Augmentation is the whole design.** The representation becomes "
        "invariant to exactly the transformations you apply. For SimCLR, random "
        "crop plus colour jitter is essential - without colour jitter the network "
        "solves the task by matching colour histograms.",
        "**Negatives matter:** large batches (4k+) or a momentum-updated queue "
        "(MoCo) provide enough negatives; otherwise the loss is too easy.",
        "**Collapse** - all embeddings identical - is the failure mode. "
        "Contrastive methods avoid it with negatives; BYOL/SimSiam with a "
        "predictor head plus a stop-gradient; DINO with centring and sharpening; "
        "Barlow Twins and VICReg with explicit decorrelation terms.",
        "**Projection head:** contrast in the space AFTER a small MLP, but "
        "transfer the representation from BEFORE it - the head discards "
        "information useful downstream.",
    ])

    h2("Transfer learning strategies")
    tbl(["Scenario", "Strategy"],
        [["Target task similar, few labels", "Freeze the backbone, train a linear "
          "probe. Fast, and a strong evaluation of representation quality"],
         ["Target similar, moderate labels", "Fine-tune the last blocks with "
          "discriminative learning rates"],
         ["Target different, many labels", "Fine-tune everything, low LR, longer "
          "warmup; consider re-initialising the last block"],
         ["Very few labels (<100/class)", "Few-shot with a frozen foundation "
          "model plus k-NN or a prototype classifier; or LoRA on a large "
          "pretrained model"],
         ["Domain shift only", "Continue self-supervised pretraining on unlabelled "
          "target-domain data first (domain-adaptive pretraining), then fine-tune"]],
        widths=[28, 72], bold_first=True)
    box("warn", "Catastrophic forgetting",
        "Fine-tuning on a narrow task overwrites general capability. Mitigations: "
        "lower learning rates, freezing lower layers, replaying a sample of the "
        "original data, elastic weight consolidation (penalise movement of "
        "parameters important to the old task), or keeping the base model frozen "
        "and training adapters/LoRA so the original weights are never touched at "
        "all - which is also why adapter-based deployment is operationally "
        "attractive.")

    h2("Semi-supervised learning")
    bul([
        "**Pseudo-labelling:** predict on unlabelled data, keep confident "
        "predictions as labels, retrain. Simple and effective; guard against "
        "confirmation bias with a high threshold and strong augmentation.",
        "**Consistency regularisation:** the prediction should not change under "
        "augmentation - the core of FixMatch, which combines a weak-augmentation "
        "pseudo-label with a strong-augmentation consistency loss and remains a "
        "very strong baseline.",
        "**Mean teacher:** an EMA of the student's weights produces the targets, "
        "which stabilises training.",
        "**Noisy student:** iteratively train a larger student on pseudo-labels "
        "with noise (dropout, augmentation), then make it the teacher.",
    ])

    h3("Exercises")
    bul([
        "Train SimCLR on an unlabelled subset of CIFAR-10, then compare a linear "
        "probe on 1%, 10% and 100% of the labels against training from scratch.",
        "Ablate the augmentations in a contrastive setup one at a time and report "
        "linear-probe accuracy - this reproduces the key finding of the SimCLR "
        "paper.",
        "Take a pretrained sensor or audio encoder and evaluate a k-NN classifier "
        "on its frozen embeddings with 5 labelled examples per class.",
    ], ordered=True)


# =============================================================================
#                        PART V - EXPERT TOPICS
# =============================================================================
def part5():
    part("Expert Topics",
         "Making models small and fast, training them on the device itself, "
         "learning from interaction, trusting the output, and shipping the whole "
         "thing to production.")

    # --------------------------------------------------------------- Ch 28 ---
    chapter("Efficient Deep Learning I: Quantization", newpage=False)
    p("Quantization stores and computes with fewer bits. It is the single "
      "highest-leverage efficiency technique available: 8-bit integers cut memory "
      "by 4x against float32 and, on hardware with integer units, raise "
      "throughput by 2-4x, usually for well under one point of accuracy.")

    h2("Why it works and why it pays")
    bul([
        "Trained networks are heavily over-parameterised and their weights "
        "cluster in a narrow range; the mapping from weights to function is much "
        "less precise than float32 suggests.",
        "Inference for large models is **memory-bandwidth bound**. Fewer bits per "
        "weight means proportionally fewer bytes moved, so latency falls close to "
        "linearly with bit width even when the arithmetic is unchanged.",
        "Integer arithmetic units are smaller and far more energy-efficient than "
        "floating-point ones: an int8 multiply-accumulate costs roughly an order "
        "of magnitude less energy than an fp32 one, which is decisive on battery "
        "power.",
        "Microcontrollers frequently have no floating-point unit at all - int8 is "
        "not an optimisation there, it is the only option.",
    ])
    tbl(["Format", "Bits", "Memory for 7B params", "Typical use"],
        [["FP32", "32", "28 GB", "Training master weights, reference accuracy"],
         ["TF32 / FP16 / BF16", "19 / 16 / 16", "14 GB", "Training compute; BF16 "
          "has FP32's exponent range"],
         ["FP8 (E4M3 / E5M2)", "8", "7 GB", "Training and inference on recent "
          "accelerators"],
         ["INT8", "8", "7 GB", "The standard deployment format; excellent hardware "
          "support"],
         ["INT4 / NF4", "4", "3.5 GB", "LLM weight-only quantization; NF4 is "
          "information-theoretically matched to a normal distribution"],
         ["INT2 / ternary / binary", "2 / 1.58 / 1", "<= 1.75 GB", "Research and "
          "extreme edge; needs quantization-aware training from scratch"]],
        widths=[22, 16, 24, 38], bold_first=True)

    h2("The mathematics of affine quantization")
    eq(["Quantize:    q = clamp( round( r / s ) + z ,  q_min , q_max )",
        "Dequantize:  r_hat = s * ( q - z )",
        "",
        "s = (r_max - r_min) / (q_max - q_min)          scale (a float)",
        "z = q_min - round( r_min / s )                 zero-point (an integer)"])
    p("**Symmetric** quantization forces z = 0 and uses a range centred on zero: "
      "`s = max|r| / (2^(b-1) - 1)`. It makes the arithmetic cheaper (no "
      "cross-terms with the zero-point) and is the right choice for weights, "
      "which are roughly zero-centred. **Asymmetric** quantization keeps z and "
      "uses the full range; it is the right choice for activations after ReLU, "
      "which are non-negative and would waste half the codes under a symmetric "
      "scheme.")
    box("math", "Where the zero-point comes from, and why it must be exact",
        "Real zero must map to an exact integer, because padding, masking and "
        "ReLU all produce exact zeros and any error there shows up as a "
        "systematic bias across the whole tensor. Solving r = 0 in "
        "r = s(q - z) gives q = z, so the zero-point is precisely the integer "
        "code that represents 0.0. This is why the rounding in the definition of "
        "z is not optional.")
    eq(["Integer matmul with symmetric weights and asymmetric activations:",
        "",
        "  r_y = SUM_i r_w[i] r_x[i]",
        "      = s_w s_x * SUM_i q_w[i] ( q_x[i] - z_x )",
        "      = s_w s_x * ( SUM_i q_w[i] q_x[i]  -  z_x SUM_i q_w[i] )",
        "                    \\___ int32 accumulation ___/   \\_ precomputed _/"])
    p("The whole inner loop is integer multiply-accumulate into an int32 "
      "accumulator; the float scale is applied once at the end, usually as a "
      "fixed-point multiply-and-shift so that no floating-point unit is needed "
      "anywhere.")

    h2("Granularity and what it costs")
    tbl(["Granularity", "One scale per", "Accuracy", "Overhead"],
        [["Per-tensor", "Whole weight tensor", "Lowest", "Negligible; fastest"],
         ["Per-channel (per-output)", "Output channel / row", "Much better - the "
          "standard for weights", "One scale per channel"],
         ["Per-group (e.g. 128)", "Block of weights within a row", "Best for "
          "INT4 LLM weights", "Scales stored per group; still cheap"],
         ["Per-token (activations)", "Row of the activation matrix", "Handles "
          "varying dynamic range across tokens", "Computed on the fly"]],
        widths=[24, 28, 30, 18], bold_first=True)
    box("key", "Per-channel weight quantization is nearly free accuracy",
        "Different output channels of a convolution or linear layer often have "
        "weight ranges that differ by 10-100x. A single per-tensor scale is then "
        "set by the widest channel and crushes all the others into a handful of "
        "codes. Per-channel scales fix this at the cost of one float per channel, "
        "and they are supported by essentially all inference runtimes. Use them "
        "by default.")

    h2("Post-training quantization (PTQ)")
    p("PTQ quantizes a trained model without retraining. It needs only a small "
      "**calibration set** - typically 100-1,000 unlabelled samples - to estimate "
      "activation ranges.")
    bul([
        "**Dynamic quantization:** weights are quantized offline, activation "
        "ranges computed at runtime per batch. Trivial to apply, no calibration "
        "data, good for LSTMs and Transformer linear layers where the memory of "
        "the weights dominates.",
        "**Static quantization:** activation ranges are calibrated offline and "
        "baked in, so the entire graph runs in integer arithmetic. Faster; needs "
        "representative calibration data.",
        "**Calibration methods:** min-max (simple, outlier-sensitive), percentile "
        "(clip at 99.9%), entropy/KL (TensorRT's default, minimises information "
        "loss), and MSE-optimal search over clipping thresholds.",
        "**Cross-layer equalisation:** exploit the positive homogeneity of ReLU "
        "to rescale consecutive layers so their per-channel ranges match, "
        "improving per-tensor quantization for free.",
        "**Bias correction:** quantization introduces a systematic shift in the "
        "mean activation; measure it on the calibration set and fold the "
        "correction into the bias.",
        "**AdaRound:** learn, per weight, whether to round up or down by "
        "minimising the layer output error rather than the weight error. Reliably "
        "recovers most of the INT4 gap without labels.",
        "**GPTQ / AWQ / SmoothQuant** for LLMs: GPTQ solves a layerwise "
        "second-order reconstruction problem column by column; AWQ scales "
        "salient channels identified by activation magnitude before quantizing; "
        "SmoothQuant migrates activation outliers into the weights so both become "
        "quantizable.",
    ])

    h2("Quantization-aware training (QAT)")
    p("QAT simulates quantization during training so the network learns weights "
      "that are robust to it. Fake-quantize nodes round and clamp in the forward "
      "pass while the backward pass uses the straight-through estimator.")
    eq(["Forward:   x_q = s * ( clamp( round(x/s) + z, q_min, q_max ) - z )",
        "Backward:  dL/dx = dL/dx_q * 1[ q_min <= round(x/s)+z <= q_max ]",
        "           (identity inside the range, zero outside - the STE)"])
    code([
        "import torch, torch.nn as nn",
        "from torch.ao.quantization import QConfig, prepare_qat, convert",
        "from torch.ao.quantization.observer import (MovingAverageMinMaxObserver,",
        "                                            MovingAveragePerChannelMinMaxObserver)",
        "",
        "qconfig = QConfig(",
        "    activation=MovingAverageMinMaxObserver.with_args(",
        "        dtype=torch.quint8, qscheme=torch.per_tensor_affine),",
        "    weight=MovingAveragePerChannelMinMaxObserver.with_args(",
        "        dtype=torch.qint8, qscheme=torch.per_channel_symmetric))",
        "",
        "model.train()",
        "model.qconfig = qconfig",
        "model_prepared = prepare_qat(model.eval(), inplace=False).train()",
        "",
        "# Fine-tune for a few epochs at ~1/10 of the original learning rate.",
        "# Freeze the observers near the end so the ranges stop moving:",
        "#   model_prepared.apply(torch.ao.quantization.disable_observer)",
        "#   model_prepared.apply(nn.intrinsic.qat.freeze_bn_stats)",
        "",
        "model_int8 = convert(model_prepared.eval(), inplace=False)",
    ], "Listing 28.1 - Quantization-aware training in PyTorch. QAT typically "
       "recovers most of the INT8 gap and is often the only way to reach INT4.")
    tbl(["", "PTQ", "QAT"],
        [["Data needed", "100-1,000 unlabelled samples", "The training set and a "
          "training loop"],
         ["Time", "Minutes", "Hours to days (a fraction of full training)"],
         ["INT8 accuracy loss", "Typically <1% on CNNs; larger on compact models",
          "Usually within noise of the float model"],
         ["INT4 accuracy", "Needs GPTQ/AWQ-class methods; noticeable loss",
          "The reliable route"],
         ["When to use", "Always try first", "When PTQ is not good enough, or "
          "below 8 bits"]],
        widths=[20, 40, 40], bold_first=True)

    ex_ch28()

    h2("What breaks, and how to fix it")
    tbl(["Failure", "Cause", "Remedy"],
        [["Large drop on a depthwise-separable model", "Depthwise layers have "
          "very different per-channel ranges", "Per-channel weights; QAT; "
          "cross-layer equalisation"],
         ["LLM collapses below 8 bits", "A few activation channels have outliers "
          "100x larger than the rest", "SmoothQuant, AWQ, keeping outlier "
          "channels in fp16 (LLM.int8), group-wise scales"],
         ["Accuracy fine offline, poor on device", "The runtime fuses or reorders "
          "ops differently, or uses different rounding",
          "Evaluate with the actual runtime, not the simulation"],
         ["BatchNorm statistics wrong after quantization", "BN folded into the "
          "conv with float statistics that no longer match",
          "Fold BN before calibration; freeze BN statistics during QAT"],
         ["Softmax/LayerNorm degrade", "Narrow dynamic range in normalisation",
          "Keep sensitive layers in higher precision - mixed precision by "
          "sensitivity"]],
        widths=[24, 36, 40], bold_first=True)
    box("expert", "Sensitivity analysis: the workflow that actually finds the "
        "right configuration",
        "Quantize one layer at a time, keeping everything else in float, and "
        "record the accuracy drop. This produces a sensitivity ranking, usually "
        "showing that the first layer, the last layer and a handful of "
        "normalisation-adjacent layers account for most of the damage. Keep "
        "those in 8 or 16 bits and push the rest to 4. Automating this - solving "
        "for a bit-width assignment under a size or latency budget - is the core "
        "of mixed-precision quantization methods such as HAWQ, which use "
        "Hessian traces as the sensitivity proxy.")

    h2("Reporting quantization results honestly")
    checklist("A complete quantization report", [
        "Baseline float accuracy on the same evaluation code and data.",
        "Bit widths per tensor type (weights, activations, accumulator), and "
        "the granularity used for each.",
        "Which layers, if any, were kept in higher precision.",
        "Calibration set size and selection method.",
        "Measured model size on disk and peak RAM at inference, not just the "
        "theoretical figure.",
        "Latency and energy measured ON THE TARGET DEVICE with the target "
        "runtime, over many runs, reporting median and tail.",
        "Accuracy per class or per slice - quantization damage is often "
        "concentrated in rare classes.",
    ])

    h3("Exercises")
    bul([
        "Implement affine quantize/dequantize in NumPy and measure the "
        "reconstruction error of a trained weight tensor at 8, 6, 4 and 2 bits, "
        "per-tensor versus per-channel.",
        "Apply dynamic and static PTQ to the same CNN and compare accuracy, size "
        "and latency; then run QAT and compare again.",
        "Take a small Transformer, plot the per-channel maximum activation "
        "magnitude for each layer, and identify the outlier channels that make "
        "naive INT8 fail.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 29 ---
    chapter("Efficient Deep Learning II: Pruning and Sparsity")
    p("Pruning removes parameters, channels or whole blocks from a network. "
      "Trained networks are massively redundant - 80-95% of the weights in a "
      "typical over-parameterised model can be removed with careful procedure and "
      "little or no accuracy loss. The difficulty is not deciding what to remove; "
      "it is turning removal into actual speed.")

    h2("Structured versus unstructured")
    diagram([
        "  UNSTRUCTURED                    STRUCTURED (channel)",
        "   W = [ 0  a  0  b ]              W = [ a  b  0  0 ]",
        "       [ c  0  0  d ]                  [ c  d  0  0 ]",
        "       [ 0  e  f  0 ]                  [ e  f  0  0 ]",
        "   scattered zeros                 whole columns removed",
        "   90% sparse, same runtime        25% smaller AND 25% faster",
        "   unless the kernel exploits it   on any hardware",
    ], "Figure 29.1 - Sparsity that a matrix multiply can exploit versus sparsity "
       "that it cannot.")
    tbl(["Type", "Granularity", "Compression", "Real speedup"],
        [["Unstructured", "Individual weights", "Very high (90-99%)",
          "Only with sparse kernels or a sparse accelerator; often none on a "
          "dense GPU"],
         ["Semi-structured (2:4)", "2 non-zeros in every group of 4",
          "2x on weights", "Yes - up to about 1.5-2x on NVIDIA Ampere and later "
          "sparse tensor cores"],
         ["Channel / filter", "Whole output channels", "Moderate (30-70%)",
          "Yes, on all hardware - the network is simply smaller"],
         ["Block / head", "Attention heads, FFN blocks, layers",
          "Coarse", "Yes; the cleanest option for Transformers"],
         ["Layer dropping", "Entire residual blocks", "Coarse", "Yes; large "
          "latency wins, larger accuracy risk"]],
        widths=[20, 24, 20, 36], bold_first=True)
    box("key", "Choose the granularity your hardware can cash in",
        "The most common mistake in pruning is reporting '95% sparsity' with no "
        "latency change. If your deployment target is a dense CPU or GPU kernel, "
        "prune channels or heads. If it is an Ampere-class GPU, use 2:4 "
        "semi-structured sparsity. Use unstructured pruning only when your "
        "runtime has genuine sparse kernels, or when you care about model SIZE "
        "(compressed storage, over-the-air update) rather than speed.")

    h2("What to prune: saliency criteria")
    tbl(["Criterion", "Score", "Comment"],
        [["Magnitude", "|w|", "The strongest simple baseline; still competitive "
          "with everything else"],
         ["L1/L2 norm of a filter", "||W_c||", "The channel analogue of magnitude"],
         ["Gradient-based (SNIP)", "|w * dL/dw|", "Estimates the loss change from "
          "removal; works at initialisation"],
         ["Taylor / first-order", "|w * g| summed over a batch", "Standard for "
          "structured channel pruning"],
         ["Second-order (OBD/OBS, SparseGPT)", "H-weighted importance",
          "Theoretically better; SparseGPT makes it tractable for LLMs"],
         ["Activation-based (APoZ)", "Fraction of zero activations", "Cheap "
          "channel criterion for ReLU networks"],
         ["Wanda (LLMs)", "|w| * ||activation||", "Extremely cheap, no "
          "retraining, strong for one-shot LLM pruning"],
         ["Learned gates", "L0 / Gumbel gates trained jointly", "Optimises "
          "structure and weights together; more complex"]],
        widths=[26, 24, 50], bold_first=True)

    h2("When to prune: the four schedules")
    bul([
        "**One-shot after training:** train, prune, fine-tune. Simple and often "
        "sufficient up to moderate sparsity.",
        "**Iterative magnitude pruning:** repeat (prune a little, fine-tune) many "
        "times. Consistently the best accuracy at high sparsity, and the most "
        "expensive.",
        "**Gradual sparsity during training** (Zhu-Gupta): raise the sparsity "
        "from 0 to the target with a cubic schedule between step t0 and tn. "
        "Trains once, reaches high sparsity, and is the standard production "
        "recipe.",
        "**Sparse from the start / dynamic sparse training:** RigL, SET and "
        "similar methods keep a fixed sparsity budget throughout, periodically "
        "dropping the smallest weights and regrowing new connections where "
        "gradients are largest. They never require a dense model in memory, which "
        "is the property that makes them relevant to on-device training "
        "(Chapter 31).",
    ])
    eq(["Zhu-Gupta cubic schedule:",
        "s_t = s_f + (s_0 - s_f) * ( 1 - (t - t_0)/(n dt) )^3",
        "",
        "RigL step: drop the |w|-smallest fraction f of active weights,",
        "           grow the same number where |dL/dw| is largest,",
        "           f decayed cosine-wise over training."])
    box("expert", "Why regrowth by gradient magnitude is the right rule",
        "A weight that is currently zero has no effect on the loss, but its "
        "GRADIENT still says how much the loss would change if it became "
        "non-zero. RigL uses exactly that signal to decide where to spend its "
        "sparsity budget next, which is why it beats static random or magnitude-"
        "only sparsity at the same parameter count. The cost is one dense "
        "gradient computation at each update step - cheap if done every few "
        "hundred steps, and the reason the update interval is a key "
        "hyperparameter.")

    h2("The lottery ticket hypothesis")
    p("A randomly initialised dense network contains a sparse subnetwork - a "
      "'winning ticket' - that, when trained **from the original "
      "initialisation**, matches the full network's accuracy. The practical "
      "recipe that demonstrates it is iterative magnitude pruning with weight "
      "rewinding (reset the surviving weights to their values at initialisation, "
      "or at an early step, rather than keeping the trained values).")
    bul([
        "It reframes pruning as **finding a good architecture and "
        "initialisation**, not merely as removing fat.",
        "For large models, rewinding to an early step (a few percent into "
        "training) works where rewinding to step 0 does not.",
        "It does not yet give a cheap way to find the ticket without training the "
        "dense model first, which limits its direct practical use - but it "
        "motivates sparse-training methods that try to.",
    ])

    h2("Pruning in practice")
    code([
        "import torch, torch.nn.utils.prune as prune",
        "",
        "# --- global unstructured magnitude pruning across all conv/linear layers",
        "params = [(m, 'weight') for m in model.modules()",
        "          if isinstance(m, (torch.nn.Conv2d, torch.nn.Linear))]",
        "prune.global_unstructured(params, pruning_method=prune.L1Unstructured,",
        "                          amount=0.8)          # 80% of weights zeroed",
        "",
        "# --- structured: remove whole output channels by L2 norm",
        "for m in model.modules():",
        "    if isinstance(m, torch.nn.Conv2d):",
        "        prune.ln_structured(m, name='weight', amount=0.3, n=2, dim=0)",
        "",
        "# --- fine-tune here with a small learning rate (masks stay applied) ---",
        "",
        "for m, n in params:",
        "    prune.remove(m, n)      # bake the mask into the weights, drop the mask",
        "",
        "# NOTE: prune.remove leaves a DENSE tensor containing zeros. To gain",
        "# speed you must either export to a sparse format your runtime supports,",
        "# or physically rebuild the network with smaller layers (structured).",
    ], "Listing 29.1 - Pruning in PyTorch, including the caveat that most "
       "tutorials omit.")
    checklist("Pruning workflow that produces a deployable model", [
        "Establish the dense baseline accuracy and latency on the target device.",
        "Choose the granularity that your runtime can exploit.",
        "Decide global versus per-layer sparsity. Global allocates the budget "
        "automatically but can wipe out a small sensitive layer - always exclude "
        "the first and last layers.",
        "Use a gradual schedule with fine-tuning rather than one-shot, if you can "
        "afford the training time.",
        "After pruning, physically rebuild or export the compact model, then "
        "re-measure latency and memory on the device.",
        "Re-check per-class and per-slice accuracy: pruning damage concentrates "
        "in rare classes.",
        "Consider combining with quantization - prune first, then quantize, then "
        "fine-tune once more.",
    ])

    ex_ch29()

    h2("Sparsity in large language models")
    bul([
        "**SparseGPT** and **Wanda** prune LLMs in one shot to 50-60% "
        "unstructured or 2:4 sparsity using a small calibration set and no "
        "retraining.",
        "**Structured LLM pruning** (LLM-Pruner, Sheared-Llama) removes attention "
        "heads, FFN channels or layers and then continues pretraining briefly to "
        "recover - this is what produces genuinely smaller, faster models.",
        "**Mixture-of-experts** is conditional sparsity by design: only k of N "
        "expert FFNs run per token, so parameter count and compute decouple. It "
        "is the dominant way large models buy capacity without buying latency, at "
        "the cost of memory and routing complexity.",
        "**Activation sparsity:** ReLU-family models have naturally sparse "
        "activations that can be exploited to skip computation at inference "
        "(deja-vu-style predictors), and it is a reason some recent models "
        "deliberately reintroduce ReLU.",
    ])

    h2("Combining compression techniques")
    tbl(["Order", "Rationale"],
        [["Distill -> prune -> quantize -> fine-tune", "Distillation defines a "
          "smaller architecture first; pruning trims what remains; quantization "
          "is applied last because it is the least forgiving; a final short "
          "fine-tune (or QAT) recovers the residual loss"],
         ["Prune and quantize jointly", "Better in principle - the two interact - "
          "but harder to tune and to debug"],
         ["Quantize before pruning", "Generally worse: pruning decisions made on "
          "quantized weights are noisier"]],
        widths=[34, 66], bold_first=True)
    eq(["Compound compression example (typical, MobileNet-class model):",
        "  dense fp32        14.0 MB   100.0%   baseline accuracy",
        "  + 50% channels     7.2 MB    51.4%   -0.6 pt",
        "  + INT8             1.9 MB    13.6%   -0.9 pt",
        "  + distillation     1.9 MB    13.6%   -0.3 pt  (recovered by teacher)"])

    h3("Exercises")
    bul([
        "Prune a trained CNN to 50%, 80%, 90%, 95% and 99% with global magnitude "
        "pruning and plot accuracy against sparsity, with and without "
        "fine-tuning.",
        "Implement RigL's drop-and-grow step and compare against static sparse "
        "training at the same parameter budget.",
        "Structurally prune 30% of channels, rebuild the network with the smaller "
        "layers, and measure the actual latency change on your target device. "
        "Compare with the latency change from unstructured pruning at the same "
        "parameter count.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 30 ---
    chapter("Efficient Deep Learning III: Distillation, NAS and Efficient Design")
    h2("Knowledge distillation")
    p("A small **student** is trained to imitate a large **teacher**. The "
      "teacher's full output distribution carries much more information than a "
      "one-hot label - the relative probabilities of the wrong classes encode "
      "which categories resemble each other, the 'dark knowledge'.")
    eq(["L = (1 - a) * CE( y_true, student ) ",
        "  + a * T^2 * KL( softmax(z_T / T) || softmax(z_S / T) )",
        "",
        "T = temperature (2-10);  the T^2 factor keeps gradient magnitudes",
        "comparable between the two terms."])
    tbl(["Variant", "What is matched", "Notes"],
        [["Response / logit KD", "Output distribution", "The classic; simple and "
          "strong"],
         ["Feature / hint KD", "Intermediate activations (FitNets)", "Needs a "
          "projection when widths differ"],
         ["Attention transfer", "Attention maps", "Effective for CNNs and "
          "Transformers"],
         ["Relational KD", "Pairwise distances between samples in feature space",
          "Transfers structure rather than points"],
         ["Self-distillation", "The model teaches itself (deeper layers teach "
          "shallower, or an EMA teacher)", "Improves accuracy with no larger "
          "teacher"],
         ["Sequence-level KD", "Teacher-generated outputs used as training data",
          "The standard way to make small LLMs; effectively synthetic data"],
         ["Born-again networks", "Student identical in size to the teacher",
          "Often beats the teacher - evidence that the soft targets themselves "
          "are the benefit"]],
        widths=[22, 38, 40], bold_first=True)
    box("tip", "Distillation is the most reliable compression method",
        "Unlike pruning and quantization, distillation lets you choose the "
        "student architecture freely - so you can pick one that is fast on your "
        "actual hardware rather than one that is merely smaller. It also composes "
        "with everything else: distil into a pruned, quantized student and use "
        "the teacher's soft targets during quantization-aware fine-tuning.")

    h2("Efficient architecture design")
    bul([
        "**Depthwise separable convolutions** (MobileNet) - 8-9x fewer FLOPs per "
        "3x3 layer.",
        "**Inverted residuals with linear bottlenecks** (MobileNetV2) - expand, "
        "depthwise, project, with the skip on the narrow tensors to keep memory "
        "traffic low.",
        "**Squeeze-and-excitation** - cheap channel attention, consistently worth "
        "its small cost.",
        "**Group convolution and channel shuffle** (ShuffleNet) - reduce cost "
        "while preserving cross-channel mixing.",
        "**Compound scaling** (EfficientNet) - scale depth, width and resolution "
        "together rather than one at a time.",
        "**Hardware-aware design:** FLOPs are a poor proxy for latency. Memory "
        "access, kernel support, and degree of parallelism often dominate; a "
        "model with fewer FLOPs can easily be slower. Measure on the device.",
    ])

    h2("Neural architecture search")
    tbl(["Approach", "Mechanism", "Cost"],
        [["Reinforcement learning (NASNet)", "A controller proposes "
          "architectures, reward = validation accuracy", "Thousands of GPU-days; "
          "historical"],
         ["Evolutionary", "Mutate and select architectures", "High but "
          "parallelisable"],
         ["Differentiable (DARTS)", "Relax the discrete choice into a weighted "
          "mixture and optimise with gradients", "A few GPU-days; can collapse to "
          "trivial operations"],
         ["One-shot / supernet (Once-for-All)", "Train one weight-sharing "
          "supernet, then extract sub-networks per device", "Train once, deploy "
          "many - the practical modern approach"],
         ["Zero-cost proxies", "Score architectures at initialisation from "
          "gradient or Jacobian statistics", "Minutes; noisy but useful for "
          "filtering"]],
        widths=[26, 44, 30], bold_first=True)
    box("warn", "NAS is rarely the right first move",
        "A well-tuned existing architecture with good training recipes beats a "
        "poorly executed NAS almost every time, and NAS results frequently fail "
        "to transfer across datasets and hardware. Reach for it when you have a "
        "hard, fixed hardware constraint, a stable task, and enough compute to do "
        "it properly - typically hardware-aware supernet search against a "
        "measured latency table.")

    h2("Choosing a compression strategy")
    tbl(["Constraint", "First move", "Then"],
        [["Model too large for flash/RAM", "INT8 quantization (4x)",
          "Structured pruning, then INT4 with QAT"],
         ["Latency too high", "Structured pruning + a hardware-friendly "
          "architecture", "Quantization; operator fusion; a better runtime"],
         ["Energy budget", "Quantization (integer arithmetic)",
          "Reduce input resolution/sampling rate; early-exit networks"],
         ["Accuracy must not drop", "Distillation into a compact student",
          "QAT rather than PTQ; keep sensitive layers at higher precision"],
         ["Many target devices", "Once-for-All supernet", "Extract a sub-network "
          "per device from measured latency"]],
        widths=[24, 38, 38], bold_first=True)

    h3("Exercises")
    bul([
        "Distil a ResNet-50 teacher into a ResNet-18 student and compare against "
        "training the student from scratch, sweeping T and alpha.",
        "Measure FLOPs and on-device latency for MobileNetV2, EfficientNet-B0 and "
        "ResNet-18 and show that the FLOPs ranking does not match the latency "
        "ranking.",
        "Build a small supernet with three width options per layer and extract "
        "two sub-networks meeting different latency budgets.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 31 ---
    chapter("On-Device and Federated Training")
    p("Inference on the edge is now routine. **Training** on the edge is the "
      "harder and more interesting problem: it lets a model personalise to its "
      "user, adapt to sensor drift, and improve without any data ever leaving the "
      "device.")

    h2("Why train on the device at all")
    bul([
        "**Privacy:** raw sensor data, keystrokes, audio and health signals never "
        "leave the hardware. This is often a legal requirement, not a preference.",
        "**Personalisation:** a gesture, gait or keyboard model tuned to one "
        "person beats a global model by a wide margin.",
        "**Adaptation:** sensors age, mounting positions change, environments "
        "shift. A model that can fine-tune locally survives drift that would "
        "otherwise require a recall or an update campaign.",
        "**Connectivity and cost:** no round trip, no bandwidth bill, no cloud "
        "inference cost, and it works offline.",
    ])

    h2("The resource wall")
    eq(["Inference memory  ~  weights + one layer's activations",
        "Training memory   ~  weights + gradients + optimiser state",
        "                     + ALL activations kept for the backward pass",
        "",
        "Adam, fp32:  weights 4B + grad 4B + m 4B + v 4B = 16 B / parameter",
        "A 1M-parameter model therefore needs ~16 MB before activations -",
        "more than the total SRAM of most microcontrollers."])
    tbl(["Class of device", "RAM", "Compute", "What is feasible"],
        [["Cloud GPU", "40-80 GB", "100+ TFLOPs", "Anything"],
         ["Phone / SoC NPU", "4-16 GB", "1-10 TOPS", "Full fine-tuning of small "
          "models; LoRA on medium ones"],
         ["Embedded Linux (Pi-class)", "0.5-8 GB", "10-100 GFLOPs",
          "Fine-tuning small CNNs; sparse or partial updates"],
         ["MCU (Cortex-M)", "256 KB - 1 MB SRAM", "~100 MFLOPs",
          "Last-layer or sparse-subset updates only; int8 arithmetic"]],
        widths=[24, 20, 18, 38], bold_first=True)

    h2("Techniques that make on-device training possible")
    tbl(["Technique", "What it saves", "Cost / caveat"],
        [["Freeze most layers, train the head", "Activations and gradients for "
          "frozen layers", "Limited adaptation capacity"],
         ["Bias-only / BitFit updates", "Gradients and optimiser state (biases "
          "are <1% of parameters)", "Surprisingly effective for domain shift"],
         ["LoRA / adapters", "Optimiser state and gradient memory",
          "Still needs backward through the frozen layers"],
         ["Sparse updates (a subset of channels/layers)", "Both memory and "
          "compute, tunably", "Needs a rule for choosing the subset - this is "
          "where RigL-style criteria are used"],
         ["Quantized training (int8/fp8 forward and backward)", "Memory "
          "bandwidth and energy", "Needs stochastic rounding and careful scaling "
          "to avoid gradient underflow"],
         ["Gradient checkpointing", "Activation memory (the dominant term)",
          "About 30% extra compute"],
         ["Small batch + gradient accumulation", "Peak activation memory",
          "More steps; noisier BatchNorm - prefer GroupNorm"],
         ["SGD or Lion instead of Adam", "8 bytes/parameter of optimiser state",
          "May need more careful learning-rate tuning"],
         ["Forward-only / zeroth-order methods", "The entire backward pass",
          "Much slower convergence; viable for tiny adaptation"]],
        widths=[26, 34, 40], bold_first=True)
    box("key", "Activations, not weights, are the binding constraint",
        "For a small model, the weights may be a few hundred kilobytes while the "
        "activations retained for backpropagation are several megabytes, because "
        "they scale with batch size, spatial resolution and depth. The first "
        "three things to try are therefore: batch size 1 with accumulation, "
        "gradient checkpointing, and freezing the early layers - which removes "
        "their stored activations entirely.")
    code([
        "# Update only the last block and all bias terms - a strong, cheap",
        "# on-device personalisation recipe.",
        "for name, p in model.named_parameters():",
        "    p.requires_grad = name.endswith('.bias') or name.startswith('layer4')",
        "",
        "trainable = [p for p in model.parameters() if p.requires_grad]",
        "print('trainable:', sum(p.numel() for p in trainable),",
        "      'of', sum(p.numel() for p in model.parameters()))",
        "",
        "opt = torch.optim.SGD(trainable, lr=1e-3, momentum=0.9)   # 4 B/param state",
        "",
        "# Halve activation memory again at ~30% compute cost:",
        "model.layer4 = torch.utils.checkpoint.checkpoint_wrapper(model.layer4)",
    ], "Listing 31.1 - Partial fine-tuning: the practical basis of on-device "
       "personalisation.")

    h2("Federated learning")
    p("Federated learning trains a shared model across many devices without "
      "collecting their data. The canonical algorithm, **FedAvg**, is simple:")
    diagram([
        "   server                                 devices",
        "   ------                                 -------",
        "   broadcast global weights  ---------->  1..K selected clients",
        "                                          each trains E local epochs",
        "   aggregate:  w <- SUM_k (n_k/n) w_k  <-- each returns its weights",
        "   repeat for R rounds",
    ], "Figure 31.1 - One round of federated averaging.")
    tbl(["Challenge", "Why it is hard", "Approaches"],
        [["Non-IID data", "Each device sees a biased slice; local models diverge "
          "and averaging degrades", "FedProx (proximal term), SCAFFOLD (control "
          "variates), server momentum, personalised heads"],
         ["System heterogeneity", "Devices differ in speed and availability; "
          "stragglers stall a round", "Asynchronous or semi-synchronous "
          "aggregation, client sampling, deadline-based partial updates"],
         ["Communication cost", "Model updates are large and uplinks are slow",
          "Update quantization and sparsification, top-k updates, low-rank "
          "updates, fewer rounds with more local work"],
         ["Privacy", "Weights leak information; gradients can be inverted to "
          "reconstruct inputs", "Secure aggregation, differential privacy (noise "
          "+ clipping), trusted execution environments"],
         ["Evaluation", "No central test set", "Federated evaluation, held-out "
          "clients, careful per-client metrics"]],
        widths=[20, 36, 44], bold_first=True)
    eq(["Differentially private SGD, per client:",
        "  clip:   g <- g * min(1, C / ||g||)",
        "  noise:  g <- g + N(0, sigma^2 C^2 I)",
        "  privacy accounting composes over rounds -> (eps, delta) guarantee"])
    box("expert", "What the privacy guarantee actually says",
        "An (eps, delta)-differentially private mechanism guarantees that the "
        "output distribution barely changes if any single user's data is removed "
        "- so an adversary cannot confidently infer whether you participated. It "
        "does NOT guarantee that the model is safe to publish for other reasons, "
        "and eps values used in industry (often 5-10) are far weaker than the "
        "theoretical ideal of eps < 1. Report eps, delta, the clipping norm, the "
        "noise multiplier and the unit of privacy (per example or per user) - "
        "without all five, a privacy claim is not checkable.")

    h2("The deployment stack for edge machine learning")
    tbl(["Layer", "Options"],
        [["Training frameworks", "PyTorch, JAX, TensorFlow"],
         ["Export / IR", "ONNX, ExecuTorch, TFLite FlatBuffer, TorchScript"],
         ["Optimisation", "Quantization, pruning, operator fusion, constant "
          "folding, layout transformation"],
         ["Runtime", "ONNX Runtime, TFLite / LiteRT, ExecuTorch, TVM, "
          "CoreML, NNAPI, TensorRT"],
         ["Bare-metal / MCU", "TFLite Micro, CMSIS-NN, microTVM, "
          "vendor SDKs"],
         ["Accelerators", "NPU, DSP, GPU, or a fixed-function CNN engine on the SoC"]],
        widths=[22, 78], bold_first=True)
    checklist("Before shipping a model to a device", [
        "Measured latency, peak RAM and energy on the real hardware, not "
        "simulated.",
        "Accuracy verified with the target runtime's own arithmetic, not the "
        "training framework's.",
        "Thermal behaviour under sustained load checked - sustained throughput "
        "can be far below burst throughput.",
        "A fallback path if the accelerator is unavailable or busy.",
        "An update mechanism, with model versioning and rollback.",
        "On-device metrics collected (with consent) so drift is detectable.",
        "For on-device training: bounds on how far the local model may drift, and "
        "a way to reset to the global model.",
    ])

    h3("Exercises")
    bul([
        "Measure the peak memory of full fine-tuning, head-only training and "
        "bias-only training for the same model, and separate the weight, gradient, "
        "optimiser and activation components.",
        "Implement FedAvg over 20 simulated clients with IID and then "
        "pathologically non-IID splits; plot global accuracy against rounds.",
        "Add gradient clipping and Gaussian noise to the federated setup and plot "
        "the accuracy/privacy trade-off for several noise multipliers.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 32 ---
    chapter("Reinforcement Learning")
    p("In reinforcement learning an agent learns by acting. There is no dataset "
      "of correct answers - only a reward signal that may be sparse, delayed, and "
      "affected by everything the agent did earlier.")

    h2("The formalism: Markov decision processes")
    eq(["MDP = (S, A, P, R, gamma)",
        "  Policy      pi(a | s)",
        "  Return      G_t = SUM_(k>=0) gamma^k r_(t+k+1)",
        "  Value       V^pi(s) = E[ G_t | s_t = s ]",
        "  Q-value     Q^pi(s,a) = E[ G_t | s_t = s, a_t = a ]",
        "  Advantage   A(s,a) = Q(s,a) - V(s)"])
    eq(["Bellman optimality:  Q*(s,a) = E[ r + gamma * max_a' Q*(s', a') ]"])
    p("The discount factor gamma in [0, 1) makes infinite-horizon returns finite "
      "and encodes how much the agent cares about the future; 0.99 is a common "
      "default, and small changes to it can change behaviour drastically.")

    h2("The two families")
    tbl(["Family", "Learns", "Representative algorithms", "Character"],
        [["Value-based", "Q(s,a), acts greedily", "Q-learning, DQN, Double DQN, "
          "Rainbow", "Off-policy, sample-efficient, discrete actions"],
         ["Policy-based", "pi(a|s) directly", "REINFORCE, TRPO, PPO",
          "Handles continuous actions and stochastic policies; higher variance"],
         ["Actor-critic", "Both", "A2C/A3C, DDPG, TD3, SAC",
          "The practical middle ground; SAC and PPO are today's defaults"],
         ["Model-based", "A model of P and R", "Dyna, MuZero, Dreamer",
          "Much more sample-efficient; harder to build and to trust"]],
        widths=[16, 18, 34, 32], bold_first=True)

    h2("Q-learning and DQN")
    eq(["Tabular update:",
        "  Q(s,a) <- Q(s,a) + alpha [ r + gamma max_a' Q(s',a') - Q(s,a) ]",
        "",
        "DQN loss (neural approximation):",
        "  L = ( r + gamma max_a' Q_target(s',a') - Q(s,a) )^2"])
    bul([
        "**Replay buffer:** store transitions and sample uniformly (or by TD "
        "error - prioritised replay). Breaks the correlation between consecutive "
        "samples that would otherwise destabilise training.",
        "**Target network:** a periodically-copied frozen copy of Q supplies the "
        "bootstrap target, preventing the network from chasing its own moving "
        "predictions.",
        "**Double DQN:** select the action with the online network and evaluate "
        "it with the target network, removing the systematic overestimation of "
        "max.",
        "**Exploration:** epsilon-greedy decayed over training is the baseline; "
        "noisy networks and count-based or curiosity bonuses do better on "
        "hard-exploration tasks.",
    ])

    h2("Policy gradients and PPO")
    eq(["Policy gradient theorem:",
        "  grad J = E[ grad log pi(a|s) * A(s,a) ]",
        "",
        "PPO clipped objective:",
        "  L = E[ min( r_t A_t , clip(r_t, 1-e, 1+e) A_t ) ],  r_t = pi/pi_old"])
    p("The clipping keeps each update inside a trust region: if the new policy "
      "moves too far from the old one on a sample, the objective stops rewarding "
      "the move. PPO is the default on-policy algorithm because it is robust, "
      "simple to implement, and parallelises well - which is also why it became "
      "the workhorse of RLHF for language models.")
    bul([
        "**GAE** (generalised advantage estimation) interpolates between "
        "high-bias/low-variance TD and low-bias/high-variance Monte Carlo "
        "advantage estimates with a parameter lambda around 0.95.",
        "**SAC** adds an entropy bonus to the objective, producing a stochastic "
        "policy that explores by construction; it is the standard for continuous "
        "control and is markedly more sample-efficient than PPO.",
        "**Normalise observations and rewards**, clip the value loss, and "
        "anneal the learning rate - RL implementations are notoriously sensitive "
        "to these details, and published gains have repeatedly turned out to come "
        "from them rather than from the algorithm.",
    ])

    ex_ch32()

    h2("Where RL is worth it")
    bul([
        "Sequential decisions where actions change the future state: robotics, "
        "control, inventory, ad auctions, game playing.",
        "Alignment of language models from preferences (Chapter 24), and training "
        "for verifiable outcomes such as passing unit tests.",
        "Not worth it when a supervised model on logged decisions would do - "
        "start with behaviour cloning or contextual bandits, which are far easier "
        "to make work and to evaluate.",
    ])
    box("warn", "Offline evaluation is the hard part",
        "You cannot evaluate a new policy from logged data by simply replaying "
        "it - the logged actions came from a different policy. Use off-policy "
        "evaluation (importance sampling, doubly robust estimators), a simulator "
        "you have validated, or a carefully bounded online experiment. Reward "
        "misspecification is equally dangerous: an agent optimises exactly what "
        "you wrote, not what you meant, and reward hacking is the norm rather "
        "than the exception.")

    h3("Exercises")
    bul([
        "Implement tabular Q-learning on FrozenLake and plot the effect of "
        "epsilon decay and gamma.",
        "Implement DQN on CartPole in 150 lines with a replay buffer and target "
        "network; then remove each of the two and observe the failure.",
        "Implement PPO with GAE on a continuous-control task and compare against "
        "SAC in sample efficiency.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 33 ---
    chapter("Uncertainty, Robustness and Interpretability")
    h2("Two kinds of uncertainty")
    tbl(["Type", "Source", "Reducible by more data?", "Example"],
        [["Aleatoric", "Noise inherent in the data", "No",
          "Two identical X-rays with different outcomes; sensor noise"],
         ["Epistemic", "Ignorance of the right model or parameters", "Yes",
          "An input unlike anything in the training set"]],
        widths=[16, 28, 20, 36], bold_first=True)
    p("The distinction is operational: high epistemic uncertainty says 'collect "
      "data here or abstain'; high aleatoric uncertainty says 'this is as good as "
      "it gets - widen the interval'.")

    h2("Estimating uncertainty in deep networks")
    tbl(["Method", "How", "Cost", "Quality"],
        [["Softmax probability", "Take the max output", "Free",
          "Poor - modern networks are overconfident and confident off-distribution"],
         ["Temperature scaling", "One scalar fitted on validation", "Free",
          "Fixes calibration in-distribution only"],
         ["MC dropout", "Keep dropout on at inference, average N passes",
          "N forward passes", "Cheap approximation to a Bayesian posterior"],
         ["Deep ensembles", "Train 5 models with different seeds",
          "N trainings", "The strongest practical baseline, including under "
          "shift"],
         ["Bayesian NN (VI, Laplace, SWAG)", "Posterior over weights",
          "Moderate to high", "Principled; Laplace approximations are now cheap "
          "and practical"],
         ["Conformal prediction", "Calibrate a nonconformity score on held-out "
          "data", "Negligible", "Distribution-free FINITE-SAMPLE coverage "
          "guarantee - underused and excellent"],
         ["Evidential / quantile heads", "Predict distribution parameters or "
          "quantiles directly", "Free", "Single-pass; needs the right loss"]],
        widths=[24, 30, 18, 28], bold_first=True)
    box("key", "Conformal prediction in three lines",
        "Fit any model. On a held-out calibration set compute a nonconformity "
        "score for each sample (for classification, s = 1 - p(true class)). Take "
        "the ceil((n+1)(1-alpha))/n empirical quantile q of those scores. At test "
        "time, output the SET of classes with 1 - p(class) <= q. That set "
        "contains the true label with probability at least 1 - alpha, with no "
        "assumption about the model or the data distribution beyond "
        "exchangeability. It is the cheapest rigorous guarantee available in "
        "machine learning.")

    h2("Out-of-distribution detection and drift")
    bul([
        "**Score-based OOD:** maximum softmax probability, energy score, "
        "Mahalanobis distance in feature space, or k-NN distance to the training "
        "set. Feature-space methods beat output-space ones.",
        "**Input drift:** monitor feature distributions with population stability "
        "index, KS tests or MMD. Cheap and catches pipeline breakages.",
        "**Prediction drift:** monitor the distribution of outputs - it moves "
        "before labels arrive.",
        "**Concept drift:** the relationship X -> y changes; only labels reveal "
        "it, so invest in a delayed-label pipeline and a small continuously "
        "labelled sample.",
    ])

    h2("Adversarial robustness")
    eq(["FGSM:  x' = x + eps * sign( grad_x L(f(x), y) )",
        "PGD :  iterate x' <- clip_(x, eps)( x' + a * sign(grad_x L) )",
        "Adversarial training:  min_theta E[ max_(||d||<=eps) L(f(x+d), y) ]"])
    bul([
        "Imperceptible perturbations flip predictions on ordinary networks; this "
        "is a property of high-dimensional linear-ish decision boundaries, not a "
        "bug in a particular model.",
        "**Adversarial training** (train on PGD examples) is the only defence "
        "that has held up broadly. It costs 3-10x training time and typically "
        "several points of clean accuracy.",
        "**Certified defences** (randomised smoothing, interval bound "
        "propagation) give provable radii, at further cost.",
        "Beware evaluation pitfalls: gradient masking makes a defence look strong "
        "against weak attacks. Always evaluate with strong adaptive attacks such "
        "as AutoAttack.",
        "For most products, natural robustness (augmentation, distribution "
        "coverage, sanity checks on inputs) matters far more than L-infinity "
        "adversarial robustness - unless you face a genuine adversary.",
    ])

    h2("Interpretability")
    tbl(["Method", "Scope", "Notes"],
        [["Linear/tree coefficients", "Global, intrinsic", "Use an interpretable "
          "model when the stakes require it - often the right answer"],
         ["Permutation importance", "Global, post-hoc", "Model-agnostic; "
          "correlated features share credit"],
         ["Partial dependence / ALE", "Global", "Shows the average shape of a "
          "feature's effect; ALE handles correlation better than PDP"],
         ["SHAP", "Local and global", "Additive attributions with consistency "
          "guarantees; TreeSHAP is exact and fast"],
         ["LIME", "Local", "Fits a local surrogate; unstable across runs"],
         ["Integrated gradients", "Local, differentiable models", "Attribution "
          "along a path from a baseline; needs a meaningful baseline"],
         ["Grad-CAM", "Local, CNNs", "Class-discriminative heat maps from the "
          "last convolutional layer"],
         ["Attention maps", "Local, Transformers", "Attention is NOT explanation "
          "on its own; use with attribution methods"],
         ["Concept-based (TCAV), probing", "Global", "Tests whether a "
          "human-defined concept is encoded"],
         ["Mechanistic interpretability", "Circuit level", "Reverse-engineering "
          "internal algorithms; sparse autoencoders on activations are the "
          "current frontier"]],
        widths=[26, 20, 54], bold_first=True)
    box("warn", "Explanations can be confidently wrong",
        "Saliency maps can look identical for a trained and a randomly "
        "initialised network. LIME and SHAP make independence assumptions that "
        "correlated features violate. A plausible explanation is not evidence "
        "that the model reasons that way. Use explanations to generate "
        "hypotheses, then TEST them - by intervening on the input, by ablating "
        "the feature and retraining, or by constructing counterfactual cases.")

    h2("Fairness")
    bul([
        "Define the harm before the metric. **Demographic parity** (equal "
        "positive rates), **equalised odds** (equal TPR and FPR across groups) "
        "and **calibration within groups** are mutually incompatible except in "
        "degenerate cases - you must choose, and the choice is a value judgement, "
        "not a technical one.",
        "Mitigations act at three stages: pre-processing (reweighting, "
        "resampling), in-processing (constrained optimisation, adversarial "
        "debiasing), post-processing (group-specific thresholds - often the most "
        "practical, sometimes legally constrained).",
        "Removing the protected attribute does not remove the bias; proxies "
        "(postcode, device, name) carry it. Measuring by group requires having "
        "the attribute, which creates its own governance problem.",
        "Report per-group performance as standard practice, exactly as you report "
        "per-class performance.",
    ])

    h3("Exercises")
    bul([
        "Implement conformal prediction for a classifier and empirically verify "
        "90% coverage on a held-out set.",
        "Compare MC dropout, a 5-model deep ensemble and temperature scaling on "
        "both in-distribution and corrupted test data.",
        "Attack a small CNN with FGSM and PGD, then adversarially train it and "
        "measure the clean/robust accuracy trade-off.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 34 ---
    chapter("MLOps: Shipping and Keeping Models Alive")
    p("A model in a notebook has produced no value. This chapter is the "
      "engineering that stands between a good validation score and a system that "
      "keeps working for years.")

    h2("The lifecycle")
    diagram([
        "   +--------+   +---------+   +--------+   +---------+   +---------+",
        "   |  DATA  |-->| FEATURE |-->| TRAIN  |-->|EVALUATE |-->| DEPLOY  |",
        "   +--------+   +---------+   +--------+   +---------+   +---------+",
        "        ^                          ^                          |",
        "        |                          |                          v",
        "        |                     +---------+              +-----------+",
        "        +---------------------| RETRAIN |<-------------| MONITOR   |",
        "                              +---------+              +-----------+",
    ], "Figure 34.1 - The loop. Most teams build the top row and neglect the "
       "bottom one, which is where models die.")

    h2("Versioning everything")
    tbl(["Artefact", "Tool / practice"],
        [["Code", "Git, with the training entry point and config in the repo"],
         ["Data", "DVC, LakeFS, Delta Lake, or immutable dated snapshots plus a "
          "content hash"],
         ["Features", "A feature store, or at minimum shared feature code used by "
          "both training and serving"],
         ["Experiments", "MLflow, Weights & Biases, or structured logs - "
          "config, metrics, environment, seeds"],
         ["Models", "A model registry with stages (staging, production, "
          "archived), lineage back to data and code, and signed artefacts"],
         ["Environment", "Pinned dependencies and a container image digest"]],
        widths=[18, 82], bold_first=True)

    h2("Serving patterns")
    tbl(["Pattern", "Latency", "Use when"],
        [["Batch / offline scoring", "Hours", "Predictions can be precomputed - "
          "churn scores, recommendations refreshed nightly"],
         ["Online / real-time API", "10-500 ms", "Predictions depend on live "
          "input"],
         ["Streaming", "Seconds", "Event-driven scoring over Kafka/Flink"],
         ["Edge / on-device", "1-50 ms", "Privacy, offline, or cost constraints "
          "(Chapter 31)"],
         ["Embedded in the client", "-", "Small models shipped inside the app "
          "binary"]],
        widths=[24, 16, 60], bold_first=True)
    bul([
        "**Training/serving skew** is the number one production bug: the feature "
        "computed in the training pipeline differs from the one computed at "
        "serving time. The structural fix is to share one implementation, and to "
        "log serving features so you can compare distributions directly.",
        "**Shadow deployment:** run the new model alongside the old one on live "
        "traffic without acting on its output. Then **canary** to a small "
        "percentage, then ramp.",
        "**A/B test** against the business metric, not the offline metric. The "
        "two disagree more often than people expect.",
        "Always keep a **rollback** path, and rehearse it.",
    ])

    h2("Monitoring")
    checklist("What a production model dashboard must show", [
        "Operational: request rate, latency percentiles (p50/p95/p99), error "
        "rate, resource use.",
        "Input health: missing-value rates, out-of-range values, schema "
        "violations, cardinality changes.",
        "Drift: PSI or KS per important feature; embedding drift for "
        "unstructured inputs; prediction distribution over time.",
        "Performance: metrics on delayed labels, sliced by segment.",
        "Business: the metric the model exists to move.",
        "Alerting with thresholds someone has agreed to, and a documented "
        "response for each alert.",
    ])

    h2("Retraining")
    bul([
        "**Scheduled** (weekly/monthly): simple, predictable, and usually "
        "adequate.",
        "**Triggered** by drift or a performance drop: efficient but needs a "
        "trustworthy trigger and guard against thrashing.",
        "**Continual/online:** rarely necessary and easy to get wrong - feedback "
        "loops can make a model train on the consequences of its own predictions.",
        "Always validate a retrained model against the current production model "
        "on the same holdout before promoting it, and never promote automatically "
        "without that gate.",
    ])

    h2("Testing machine learning systems")
    tbl(["Test type", "Example"],
        [["Data validation", "Schema, ranges, null rates, class balance "
          "(Great Expectations, Pandera)"],
         ["Unit tests on features", "A known input produces the expected feature "
          "value, including edge cases"],
         ["Model behavioural tests", "Invariance (irrelevant change leaves the "
          "prediction alone), directional expectation (income up -> risk down), "
          "minimum functionality on a curated set"],
         ["Regression tests", "Performance on a frozen golden set does not drop "
          "below a threshold"],
         ["Slice tests", "Per-subgroup metrics stay within bounds"],
         ["Integration tests", "The full pipeline runs end to end on a small "
          "sample in CI"],
         ["Load tests", "Latency under peak concurrency, with realistic payloads"]],
        widths=[24, 76], bold_first=True)

    h2("Cost and carbon")
    bul([
        "Track cost per 1,000 predictions and per training run. Quantization, "
        "batching, caching, distillation and a smaller model are the levers, "
        "roughly in that order of return.",
        "Cache aggressively: identical or near-identical requests are common, and "
        "semantic caching works well for LLM workloads.",
        "Right-size the hardware - many production models run happily on CPU, and "
        "a GPU that is idle 90% of the time is pure cost.",
        "Report energy or estimated emissions for large training runs; it is "
        "increasingly expected in papers and in corporate reporting.",
    ])

    h3("Exercises")
    bul([
        "Take a model you have trained and wrap it in a container with a "
        "prediction endpoint, input validation and structured logging.",
        "Implement PSI-based drift monitoring on a feature and simulate a drift "
        "event to verify the alert fires.",
        "Write five behavioural tests for a model in your domain: two "
        "invariance, two directional, one minimum functionality.",
    ], ordered=True)


    # --------------------------------------------------------------- Ch 35 ---
    chapter("Doing Research and Reading the Literature")
    h2("Reading a paper efficiently")
    bul([
        "**Pass 1 (5 minutes):** title, abstract, figures, tables, conclusion. "
        "Decide whether to continue.",
        "**Pass 2 (30 minutes):** introduction, method, and the experimental "
        "setup. Write down, in your own words, the one idea and the one "
        "experiment that supports it.",
        "**Pass 3 (hours):** re-derive the equations, check the ablations, and "
        "ask what is missing - which baseline is absent, which hyperparameter "
        "budget was unequal, which dataset would break it.",
        "Keep notes in a searchable form with a one-line summary per paper. In a "
        "year you will remember the idea and not the title.",
    ])
    checklist("Questions to ask of any empirical claim", [
        "Is the baseline tuned as carefully as the proposed method?",
        "Are results averaged over seeds, with variance reported?",
        "Is the comparison at equal compute, equal parameters, or equal wall "
        "clock - and does the choice flatter the method?",
        "Is there an ablation isolating the claimed contribution?",
        "Could the gain come from the training recipe rather than the "
        "architecture?",
        "Is the test set possibly contaminated by the training data?",
        "Is the effect size larger than the noise, and is it practically "
        "meaningful?",
    ])

    h2("Running an experiment that survives scrutiny")
    bul([
        "Write the hypothesis and the decision rule **before** running: 'if X "
        "improves validation F1 by more than 0.5 points across 5 seeds, adopt "
        "it'.",
        "Change one thing at a time. A run that changes three things teaches you "
        "nothing when it improves.",
        "Keep a fixed, tuned baseline and re-run it whenever the codebase "
        "changes.",
        "Budget compute equally across compared methods, and say what the budget "
        "was.",
        "Log everything automatically; a result you cannot reproduce is a rumour.",
        "Report negative results to yourself honestly - the discipline of "
        "recording what failed is what stops you repeating it in six months.",
    ])

    h2("Where the field is heading")
    bul([
        "**Efficiency as the primary axis:** quantization, sparsity, distillation "
        "and better architectures are where most practical progress now lands, "
        "because inference cost dominates total cost of ownership.",
        "**Long context and memory:** state-space models, hybrid attention, and "
        "retrieval as an architectural component rather than a bolt-on.",
        "**Multimodality by default:** one model over text, image, audio and "
        "video, with tokenisers per modality.",
        "**Post-training and reasoning:** more of the capability gain now comes "
        "from what happens after pretraining - preference optimisation, "
        "verifiable-reward RL, and inference-time compute.",
        "**Agents and tool use:** models that act, with the attendant problems of "
        "reliability, evaluation and security.",
        "**On-device and private learning:** small capable models, personalised "
        "locally, with federated and differentially private updates.",
        "**Science of deep learning:** scaling laws, mechanistic "
        "interpretability, and a slowly improving theoretical account of why any "
        "of this generalises.",
    ])
    box("tip", "How to stay current without drowning",
        "Follow a small number of sources: two or three researchers' feeds, one "
        "curated newsletter, and the proceedings of NeurIPS/ICML/ICLR/CVPR/ACL "
        "skimmed once per cycle. Read one paper properly per week rather than "
        "twenty abstracts per day. Reimplement one method per quarter - "
        "implementation is the only reading comprehension test that works.")


# =============================================================================
#              PART VI - APPLIED DOMAINS, THEORY AND SYSTEMS
# =============================================================================
def part6():
    part("Applied Domains, Theory and Systems",
         "Why generalization is possible at all, the probabilistic view of "
         "learning, the four application domains with their own rules - time "
         "series, recommenders, vision beyond classification, language, audio "
         "and multimodal - the hardware and distributed systems that make scale "
         "possible, causal questions that prediction cannot answer, and the "
         "privacy and security obligations that come with shipping.")

    # --------------------------------------------------------------- Ch 37 ---
    chapter("Learning Theory: Why Generalization Is Possible At All",
            newpage=False)
    p("Chapter 3 showed empirically that a model can score well on training data "
      "and badly on new data. This chapter answers the harder question behind "
      "that observation: **why should fitting a finite sample ever tell you "
      "anything about the infinite population it was drawn from?** The answer is "
      "not obvious - and the theory that provides it also explains why some "
      "model classes need thousands of samples and others need millions, and "
      "why the classical story breaks in the deep-learning regime.")
    box("key", "The one-sentence version",
        "Generalization is possible because the number of genuinely different "
        "functions a model class can express on n points grows slowly enough "
        "that fitting the sample cannot be a coincidence - and the rate of that "
        "growth, not the number of parameters, is the quantity that controls "
        "the gap between training error and test error.")

    h2("Empirical risk minimization, stated precisely")
    p("Assume every example is drawn independently from a fixed but unknown "
      "distribution D over pairs (x, y). This is the __i.i.d. assumption__ and "
      "it is the load-bearing assumption of the whole field: break it and the "
      "results below say nothing.")
    eq(["True risk        R(h)     = E_(x,y)~D [ L(h(x), y) ]",
        "Empirical risk   R_emp(h) = (1/n) SUM_i L(h(x_i), y_i)",
        "ERM              h_hat    = argmin_(h in H) R_emp(h)"],
       "You can compute the second line. You care about the first. The gap "
       "between them is what theory bounds.")
    p("Three quantities decompose the failure of the model you actually train:")
    eq(["R(h_hat) - R(h*)   =   [ R(h_hat) - R_emp(h_hat) ]     generalization gap",
        "                     + [ R_emp(h_hat) - R_emp(h_opt) ] optimization gap",
        "                     + [ R_emp(h_opt) - R(h*) ]        approximation gap"],
       "h* is the best possible predictor of all; h_opt is the best in your "
       "class H; h_hat is what your optimizer returned.")
    tbl(["Gap", "Cause", "What reduces it"],
        [["Approximation", "H is too small to contain a good function",
          "A richer model class: more capacity, better inductive bias, "
          "pretraining"],
         ["Optimization", "SGD did not reach the best point in H",
          "Better optimizer, schedule, initialization, longer training"],
         ["Generalization", "H is rich enough to fit noise in this sample",
          "More data, regularization, restricting H, better inductive bias"]],
        widths=[20, 40, 40], bold_first=True,
        caption="Every disappointing model is one of these three. Diagnosing "
                "which one you have is the entire content of Chapter 20's "
                "playbook: train error high -> approximation or optimization; "
                "train error low and test error high -> generalization.")

    h2("A single hypothesis: Hoeffding's inequality")
    p("Fix one hypothesis h __before__ looking at the data, and let the loss be "
      "bounded in [0, 1]. Then R_emp(h) is an average of n independent bounded "
      "random variables whose expectation is R(h). Hoeffding's inequality says "
      "such an average concentrates:")
    eq(["P( |R_emp(h) - R(h)| > eps )  <=  2 exp( -2 n eps^2 )"],
       "The probability of being wrong by more than eps decays exponentially in "
       "the number of samples.")
    p("Inverting it: with probability at least 1 - delta over the draw of the "
      "sample,")
    eq(["|R_emp(h) - R(h)|  <=  sqrt( log(2/delta) / (2n) )"])
    p("With n = 10,000 and delta = 0.05 this is about 0.0136 - a validation "
      "score of 0.91 means the true accuracy is 0.91 plus or minus roughly one "
      "and a half points. **This is the correct way to read a single held-out "
      "number**, and it is why a 0.3-point improvement on a 2,000-row test set "
      "is not an improvement at all.")
    box("warn", "Why this is not yet a theory of learning",
        "Hoeffding applies to a hypothesis chosen before the data. The one you "
        "report was chosen __because__ it scored well - you searched. Searching "
        "over many hypotheses and keeping the best is exactly the setting where "
        "the maximum of many noisy numbers is biased upward. The rest of this "
        "chapter pays for that search.")

    h2("Finite hypothesis classes: the union bound")
    p("Suppose H is finite with |H| elements. The bad event is that __some__ h "
      "in H has a large gap. The union bound says the probability of a union is "
      "at most the sum of probabilities:")
    eq(["P( exists h : |R_emp(h) - R(h)| > eps )  <=  2 |H| exp( -2 n eps^2 )"])
    p("Setting the right-hand side to delta and solving for eps gives the first "
      "real generalization bound. With probability 1 - delta, __simultaneously "
      "for every h in H__:")
    eq(["R(h)  <=  R_emp(h)  +  sqrt( ( log|H| + log(2/delta) ) / (2n) )"],
       "Uniform convergence: the bound holds for the hypothesis you picked "
       "after searching, because it holds for all of them at once.")
    box("math", "Worked numbers",
        "Take a class of 20-bit decision rules, so |H| = 2^{20} = 1,048,576, "
        "with n = 10,000 and delta = 0.05. Then log|H| = 20 log 2 = 13.86, "
        "log(2/delta) = 3.69, the sum is 17.55, divided by 20,000 is 8.8e-4, "
        "and the square root is **0.030**. Fitting a million-hypothesis class "
        "on ten thousand samples costs about three accuracy points of "
        "uncertainty. Halve the data and the penalty grows by sqrt(2); square "
        "the class size and it grows by sqrt(2) as well - **the bound is "
        "logarithmic in the size of the class and inverse-square-root in the "
        "data**. That trade is the central fact of the subject.")
    p("Two consequences follow immediately and are worth internalizing:")
    bul([
        "**The sqrt(1/n) rate.** To halve your uncertainty you need four times "
        "the data. This is why data collection has diminishing returns, and why "
        "learning curves flatten (Chapter 3).",
        "**The log|H| price of search.** Trying 1,000 hyperparameter "
        "configurations on the validation set is a class of size 1,000; the "
        "penalty is sqrt(log 1000 / 2n), small but real. Trying 100,000 is only "
        "1.5x worse in the bound - but only if each was evaluated on a fresh "
        "sample, which it was not. This is the formal reason for a test set "
        "used exactly once.",
    ])

    h2("Infinite classes: shattering and VC dimension")
    p("Linear classifiers form an infinite class, so log|H| is infinite and the "
      "bound above is vacuous. The fix is to count not hypotheses but "
      "__behaviours on n points__. Two hypotheses that label every point in "
      "your sample identically are indistinguishable from the sample's point of "
      "view.")
    eq(["Growth function   Pi_H(n) = max over n points of the number of",
        "                            distinct labelings H can produce",
        "                            (at most 2^n)"])
    p("A set of points is __shattered__ by H if H realizes all 2^n labelings of "
      "it. The **VC dimension** d_VC is the size of the largest set that H can "
      "shatter.")
    tbl(["Hypothesis class", "VC dimension", "Note"],
        [["Thresholds on the line, x > a", "1", "Cannot shatter two points "
          "labelled (1, 0) left-to-right"],
         ["Intervals [a, b] on the line", "2", ""],
         ["Linear classifiers in R^d (with bias)", "d + 1", "3 points in the "
          "plane, in general position, can be shattered; 4 cannot"],
         ["Axis-aligned rectangles in R^2", "4", ""],
         ["1-nearest neighbour", "infinite", "Fits any labeling - and yet works; "
          "see the caveat below"],
         ["Neural net, W weights, ReLU", "O(W L log W)", "L = depth; the bound "
          "is loose but shows parameters matter"]],
        widths=[40, 22, 38], bold_first=True)
    p("Sauer's lemma is the combinatorial miracle that makes this useful: once n "
      "exceeds d_VC, the growth function stops doubling and becomes polynomial.")
    eq(["Pi_H(n)  <=  SUM_(i=0..d_VC) C(n, i)   <=  ( e n / d_VC )^d_VC"],
       "Exponential below the VC dimension, polynomial above it - a phase "
       "transition at n = d_VC.")
    p("Substituting the polynomial growth function for |H| gives the VC bound: "
      "with probability 1 - delta,")
    eq(["R(h)  <=  R_emp(h)  +  O( sqrt( ( d_VC log(n/d_VC) + log(1/delta) ) / n ) )"])
    box("key", "The practical reading of the VC bound",
        "You need on the order of d_VC samples (times a logarithmic factor) "
        "before the training error means anything. This is the rigorous version "
        "of the folklore '10 to 100 samples per parameter' rule quoted for "
        "classical models in Chapter 3 - and the reason that rule is quoted for "
        "**classical** models only.")

    h2("Rademacher complexity and margin bounds")
    p("VC dimension has two weaknesses: it ignores the data distribution, and it "
      "counts only labelings, not confidence. **Rademacher complexity** fixes "
      "the first by measuring how well the class can fit random noise __on your "
      "actual sample__:")
    eq(["R_n(H) = E_sigma [ sup_(h in H) (1/n) SUM_i sigma_i h(x_i) ]",
        "         sigma_i = +1 or -1 with probability 1/2 each"],
       "The expected best correlation between a hypothesis and a coin flip. "
       "Zero for a constant class; 1 for a class that can fit anything.")
    p("This is directly measurable: shuffle your labels and train. If the model "
      "reaches high training accuracy on randomized labels, its effective "
      "complexity on your data is large. That experiment - **the randomization "
      "test** - is the single most informative diagnostic in this chapter, and "
      "it should be part of any serious project.")
    eq(["R(h)  <=  R_emp(h)  +  2 R_n(H)  +  3 sqrt( log(2/delta) / (2n) )"])
    p("Margin bounds fix the second weakness. For classifiers that output a real "
      "score, a prediction that is correct by a wide margin is more robust than "
      "one that barely crosses the boundary. The margin bound replaces the "
      "0/1 training error with the fraction of points whose margin is below "
      "gamma, and scales the complexity term by 1/gamma:")
    eq(["R(h)  <=  R_gamma_emp(h)  +  O( R_n(H) / gamma )  +  small term"],
       "Large margins buy generalization. This is the theory behind SVMs "
       "(Chapter 10) and behind why weight decay and normalization help deep "
       "networks: both control the scale-sensitive complexity in the numerator.")

    h2("Where the classical story breaks: double descent")
    p("Modern networks have far more parameters than samples, can fit random "
      "labels perfectly (so their Rademacher complexity is near 1), and yet "
      "generalize well on real labels. Uniform-convergence bounds computed for "
      "the full class are therefore vacuous - they permit test errors above 1. "
      "This is not a flaw in the theorems; it means the bounds are being applied "
      "to the wrong class. The class that matters is not 'all networks of this "
      "size' but 'the networks SGD actually reaches from this initialization'.")
    diagram([
        " test",
        " error",
        "   |*                                     classical U-curve",
        "   | *                                    (underfit -> sweet spot -> overfit)",
        "   |  *          #",
        "   |   *       #   #     <- interpolation threshold: params ~ samples",
        "   |    *    #      #",
        "   |     ***#        #",
        "   |        #          # # #",
        "   |                        # # # #  <- modern regime: error falls again",
        "   +-------------------------------------------------> model capacity",
        "        classical         |          overparameterized",
    ], "Double descent. The classical bias-variance curve (*) is the left half; "
       "past the interpolation threshold the curve descends a second time (#).")
    p("The mechanism, in one paragraph: exactly at the interpolation threshold "
      "there is essentially one way to fit the data, and it is a wildly "
      "oscillating one, so the variance term explodes. Well past the threshold "
      "there are infinitely many interpolating solutions, and gradient descent "
      "with small initialization finds one of the __smoothest__ of them - "
      "implicit regularization. Capacity stops being the relevant axis; the "
      "bias of the optimization algorithm takes over. The same effect appears "
      "in **epoch-wise** double descent (test error rises then falls again as "
      "training continues) and **sample-wise** double descent (more data "
      "temporarily hurts near the threshold).")
    box("expert", "Implicit regularization, concretely",
        "For separable data, gradient descent on logistic loss converges in "
        "direction to the maximum-margin separator, even with no explicit "
        "penalty - a result of Soudry et al. For linear regression solved by "
        "gradient descent from zero, the solution converges to the minimum-norm "
        "interpolant. Neither is imposed; both fall out of the trajectory. This "
        "is why 'the optimizer is part of the model class' is the correct modern "
        "framing, and why a bound that ignores the optimizer cannot be tight.")

    h2("Scaling laws: the empirical theory that replaced the bounds")
    p("For large models, practitioners predict performance not from VC bounds "
      "but from measured power laws. Across many orders of magnitude, loss "
      "falls as a power of parameters N, dataset size D, and compute C:")
    eq(["L(N) = L_inf + (N_c / N)^alpha_N          alpha_N ~ 0.07 for LLMs",
        "L(D) = L_inf + (D_c / D)^alpha_D          alpha_D ~ 0.10",
        "L(C) = L_inf + (C_c / C)^alpha_C",
        "Compute            C ~ 6 N D  FLOPs for a dense Transformer"],
       "The 6ND rule: 2ND for the forward pass, 4ND for the backward pass, per "
       "token per parameter.")
    p("The Chinchilla result is the practically important one: for a fixed "
      "compute budget, N and D should be scaled **in equal proportion**, giving "
      "roughly 20 training tokens per parameter as the compute-optimal ratio. "
      "Models trained before that result were badly undertrained relative to "
      "their size, which is why a well-trained 7B model can beat a 175B model "
      "from an earlier generation. In deployment the calculus shifts again: if "
      "you will serve billions of tokens, training a smaller model on more data "
      "than Chinchilla-optimal is cheaper overall, because inference cost scales "
      "with N and not with D.")
    tbl(["Budget question", "What the laws say"],
        [["I have 10x more compute. What do I change?",
          "About 3.2x parameters and 3.2x tokens - not 10x either one."],
         ["My loss curve is above the law's prediction.",
          "Something is broken: data quality, learning rate, or duplication. "
          "The law is a ceiling you should nearly reach."],
         ["Should I train longer or grow the model?",
          "Below 20 tokens/parameter, train longer. Above it, and if inference "
          "cost is not dominant, grow."],
         ["Does this apply to my 50k-row tabular problem?",
          "No. Power-law extrapolation is validated for large-scale "
          "pretraining, not small supervised datasets."]],
        widths=[36, 64], bold_first=True)

    h2("What theory gives you, and what it does not")
    tbl(["Theory delivers", "Theory does not deliver"],
        [["The sqrt(1/n) rate, so you can budget data",
          "A usable numeric bound for a deep network"],
         ["The formal cost of searching over models",
          "Permission to skip a held-out test set"],
         ["Why margins, norms and smoothness help",
          "Which architecture will win on your data"],
         ["Why i.i.d. violations are fatal, not cosmetic",
          "Any guarantee at all under distribution shift"],
         ["The randomization test as a diagnostic",
          "A replacement for measurement"]],
        widths=[50, 50])
    box("tip", "The three things to carry away",
        "1. Report held-out numbers with an interval, computed from n. "
        "2. Every model you compare on the validation set enlarges the class "
        "you are implicitly searching, so keep the test set sacred. "
        "3. Run the label-randomization test once on any new architecture: if "
        "it memorizes noise as fast as it learns signal, your regularization "
        "and your data budget both need attention.")

    h3("Exercises")
    bul([
        "Compute the Hoeffding interval for your own validation set size at "
        "delta = 0.05. Compare it with the improvements you have been claiming "
        "in the last month.",
        "Show that the VC dimension of thresholds on the line is 1 by "
        "exhibiting a shattered set of size 1 and proving no set of size 2 is "
        "shattered.",
        "Verify Sauer's lemma numerically for d_VC = 3 and n = 10: compare "
        "2^{10} with the sum of binomial coefficients up to 3.",
        "Run the randomization test: shuffle the labels of your training set "
        "and train the same model. Record how many epochs it needs to reach "
        "90% training accuracy, and compare with the true-label run.",
        "Reproduce epoch-wise double descent on a small network: train far past "
        "the point where test error first rises, and plot the whole curve.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 38 ---
    chapter("Probabilistic Machine Learning: Bayes, EM, HMMs and Gaussian "
            "Processes")
    p("Most of this book optimizes a single set of parameters. The probabilistic "
      "view keeps a __distribution__ over parameters and over hidden structure "
      "instead. It costs more computation and buys three things nothing else "
      "gives you: honest uncertainty on small data, a principled way to handle "
      "missing and latent variables, and a language in which regularization, "
      "clustering, sequence models and active learning turn out to be the same "
      "idea seen from different angles.")

    h2("The Bayesian recipe in one page")
    eq(["Prior          p(theta)              belief before data",
        "Likelihood     p(D | theta)          how the model explains data",
        "Posterior      p(theta | D) = p(D|theta) p(theta) / p(D)",
        "Evidence       p(D) = INTEGRAL p(D|theta) p(theta) d(theta)",
        "Predictive     p(y* | x*, D) = INTEGRAL p(y*|x*,theta) p(theta|D) d(theta)"],
       "Learning is conditioning; prediction is averaging over everything you "
       "still do not know.")
    tbl(["Estimator", "Objective", "Uncertainty", "Cost"],
        [["MLE", "max p(D | theta)", "None (a point)", "One optimization"],
         ["MAP", "max p(D | theta) p(theta)", "None (a point)",
          "One optimization"],
         ["Full Bayes", "the whole posterior", "Full", "Integration: "
          "conjugacy, VI or MCMC"]],
        widths=[16, 34, 22, 28], bold_first=True)
    box("math", "Ridge regression is a Gaussian prior - the derivation",
        "Take a Gaussian likelihood y = x.w + noise with noise variance s^2, "
        "and a Gaussian prior w ~ N(0, t^2 I). The log posterior is "
        "-(1/2s^2) SUM (y_i - x_i.w)^2 - (1/2t^2) ||w||^2 + const. Maximizing "
        "it is exactly minimizing SUM (y_i - x_i.w)^2 + lambda ||w||^2 with "
        "lambda = s^2 / t^2. **Ridge is MAP under a Gaussian prior; Lasso is "
        "MAP under a Laplace prior.** Every penalty in Chapter 7 is a prior in "
        "disguise, and the strength of the penalty is a ratio of variances.")

    h2("Conjugacy, worked on real numbers")
    p("A prior is __conjugate__ to a likelihood when the posterior stays in the "
      "same family, so updating is arithmetic rather than integration. The "
      "Beta-Bernoulli pair is the one to know by heart.")
    eq(["Prior       Beta(a, b)",
        "Data        h heads and t tails out of n = h + t Bernoulli trials",
        "Posterior   Beta(a + h, b + t)",
        "Mean        (a + h) / (a + b + n)"],
       "The prior acts as a + b pseudo-counts you saw before the experiment.")
    p("Toss a coin ten times and see 7 heads. With a uniform prior Beta(1,1) the "
      "posterior is Beta(8,4): posterior mean 8/12 = **0.667**, against the MLE "
      "of 0.700. The 95% credible interval runs from about 0.39 to 0.89 - which "
      "is the honest answer after ten tosses, and exactly what a point estimate "
      "hides. Add 90 more tosses with 63 more heads and the posterior becomes "
      "Beta(71,31): mean 0.696, interval 0.60 to 0.78. **The prior's influence "
      "decays like 1/n**; with enough data Bayes and MLE agree, which is why "
      "the argument only matters in the small-data regime where it should.")
    tbl(["Likelihood", "Conjugate prior", "Posterior update", "Typical use"],
        [["Bernoulli / Binomial", "Beta(a, b)", "a += successes, b += failures",
          "Click-through rate, A/B tests"],
         ["Categorical / Multinomial", "Dirichlet(alpha)", "alpha += counts",
          "Topic models, naive Bayes smoothing"],
         ["Poisson", "Gamma(a, b)", "a += SUM x, b += n", "Counts, arrivals"],
         ["Gaussian, known variance", "Gaussian", "Precision-weighted average",
          "Kalman filters, sensor fusion"],
         ["Gaussian, unknown both", "Normal-Inverse-Gamma", "Closed form",
          "Small-sample regression"]],
        widths=[24, 22, 30, 24], bold_first=True)
    box("tip", "Where conjugacy earns its keep in production",
        "Ranking items by click-through rate with tiny denominators. A raw rate "
        "of 1/1 beats 480/1000, which is absurd. Ranking by the posterior mean "
        "of Beta(1 + clicks, 1 + misses) - or better, by a lower credible bound - "
        "fixes it with two lines of code and no model. Thompson sampling for "
        "bandits is the same posterior, sampled instead of averaged.")

    h2("Latent variables and the EM algorithm")
    p("Many models are easy if you know a hidden label z and easy if you know "
      "the parameters, but hard when both are unknown: which cluster produced "
      "this point, which topic produced this word, which state emitted this "
      "observation. Expectation-Maximization alternates the two easy problems.")
    eq(["Goal        max_theta  log p(X | theta) = log SUM_z p(X, z | theta)",
        "ELBO        log p(X|theta) >= E_q(z)[ log p(X,z|theta) ] + H(q)",
        "E-step      q(z) <- p(z | X, theta_old)      makes the bound tight",
        "M-step      theta <- argmax E_q(z)[ log p(X, z | theta) ]"],
       "Each step increases the true log-likelihood, so EM converges - to a "
       "local optimum, which is why initialization matters.")
    h3("Gaussian mixture model: the update equations")
    eq(["E-step (responsibility of component k for point i):",
        "  r_ik = pi_k N(x_i | mu_k, S_k) / SUM_j pi_j N(x_i | mu_j, S_j)",
        "M-step:",
        "  N_k  = SUM_i r_ik",
        "  mu_k = (1/N_k) SUM_i r_ik x_i",
        "  S_k  = (1/N_k) SUM_i r_ik (x_i - mu_k)(x_i - mu_k)^T",
        "  pi_k = N_k / n"],
       "k-means is the limit of this as all covariances shrink to zero: "
       "responsibilities become hard 0/1 assignments and the M-step becomes "
       "'average the members'.")
    box("math", "One EM iteration by hand",
        "Points 1, 2, 8, 9 on the line. Start with mu_1 = 2, mu_2 = 7, both "
        "variances 4, equal weights. For x = 8 the squared distances are 36 and "
        "1, so the unnormalized responsibilities are exp(-36/8) = 0.0111 and "
        "exp(-1/8) = 0.8825; normalized, r = 0.0124 and 0.9876. Repeating for "
        "all four points, the responsibility of component 2 is 0.0124, 0.0421, "
        "0.9876, 0.9964. The M-step then gives N_2 = 2.0385 and "
        "mu_2 = (1(0.0124) + 2(0.0421) + 8(0.9876) + 9(0.9964)) / 2.0385 = "
        "**8.32**, and symmetrically mu_1 = **1.55** - already almost the right "
        "answer after a single pass. **Soft assignment is the only difference "
        "from k-means**, and it is what lets the model report that a point "
        "between clusters is genuinely ambiguous.")

    code([
        "# GMM in NumPy - the whole algorithm is these ten lines",
        "for _ in range(n_iter):",
        "    # E-step: responsibilities, shape (n, K)",
        "    logp = np.stack([np.log(pi[k]) + gauss_logpdf(X, mu[k], S[k])",
        "                     for k in range(K)], axis=1)",
        "    logp -= logsumexp(logp, axis=1, keepdims=True)   # stable softmax",
        "    R = np.exp(logp)",
        "    # M-step",
        "    Nk = R.sum(0) + 1e-10",
        "    mu = (R.T @ X) / Nk[:, None]",
        "    for k in range(K):",
        "        d = X - mu[k]",
        "        S[k] = (R[:, k, None] * d).T @ d / Nk[k] + 1e-6 * np.eye(D)",
        "    pi = Nk / len(X)",
    ], "Always work in log space and always add a small ridge to the covariance: "
       "a component that captures a single point drives its covariance to zero "
       "and the likelihood to infinity. That singularity is the classic GMM "
       "failure.")

    h2("Hidden Markov models and dynamic programming")
    p("An HMM adds time: a hidden state evolves as a Markov chain and each state "
      "emits an observation. It remains the right model when states are "
      "genuinely discrete and interpretable - activity recognition, keyword "
      "spotting, gene finding, fault modes - and it is far cheaper than a "
      "recurrent network.")
    eq(["Parameters   pi (initial), A (transitions), B (emissions)",
        "Forward      alpha_t(j) = b_j(o_t) SUM_i alpha_(t-1)(i) A_ij",
        "Backward     beta_t(i)  = SUM_j A_ij b_j(o_(t+1)) beta_(t+1)(j)",
        "Likelihood   p(O) = SUM_i alpha_T(i)",
        "Viterbi      d_t(j) = b_j(o_t) MAX_i d_(t-1)(i) A_ij   (+ backpointers)",
        "Learning     Baum-Welch = EM with forward-backward in the E-step"],
       "Forward sums over paths; Viterbi maximizes over paths. Same recursion, "
       "different semiring - and the same trick as beam search in Chapter 24.")
    box("math", "Viterbi on three steps, by hand",
        "States Rain and Sun; start 0.6/0.4; transitions Rain->Rain 0.7, "
        "Sun->Sun 0.6; emissions p(umbrella | Rain) = 0.9, p(umbrella | Sun) = "
        "0.2. Observe umbrella, umbrella, no-umbrella. t=1: Rain 0.6*0.9 = "
        "0.54, Sun 0.4*0.2 = 0.08. t=2: Rain = 0.9 * max(0.54*0.7, 0.08*0.4) = "
        "0.9*0.378 = 0.340; Sun = 0.2 * max(0.54*0.3, 0.08*0.6) = 0.2*0.162 = "
        "0.0324. t=3: Rain = 0.1 * max(0.340*0.7, 0.0324*0.4) = 0.0238; Sun = "
        "0.8 * max(0.340*0.3, 0.0324*0.6) = 0.8*0.102 = 0.0816. The best final "
        "state is Sun, and its backpointer chain gives **Rain, Rain, Sun**. "
        "Note that the third observation flipped the state even though Rain was "
        "far ahead - evidence propagates, which is the point of the model.")
    p("Work in log space for any real sequence: alpha underflows within a few "
      "dozen steps in single precision. The Kalman filter is the same set of "
      "recursions for continuous states with linear-Gaussian dynamics, and a "
      "particle filter is their Monte Carlo version for nonlinear ones.")

    h2("Gaussian processes: distributions over functions")
    p("Instead of a prior over weights, put a prior directly over functions. A "
      "GP says: for any finite set of inputs, the function values are jointly "
      "Gaussian, with covariance given by a kernel k(x, x') that encodes how "
      "similar two inputs are.")
    eq(["Prior        f ~ GP( m(x), k(x, x') ),   usually m = 0",
        "RBF kernel   k(x,x') = s_f^2 exp( -||x - x'||^2 / (2 l^2) )",
        "Posterior mean  mu*  = K_*  [K + s_n^2 I]^-1  y",
        "Posterior cov   S*   = K_** - K_* [K + s_n^2 I]^-1 K_*^T"],
       "K is (n,n) over training inputs, K_* is (m,n) between test and training "
       "inputs, K_** is (m,m) over test inputs.")
    p("Two hyperparameters carry the meaning. The **lengthscale l** is how far "
      "you must move in input space before the function may change; the "
      "**signal variance s_f^2** is how far it may move vertically. Both are "
      "fitted by maximizing the marginal likelihood, which trades data fit "
      "against model complexity automatically - Occam's razor falls out of the "
      "log-determinant term rather than being imposed.")
    box("math", "A two-point GP, computed",
        "Observe f(0) = 1 and f(2) = 3 with noise variance 0.01, an RBF kernel "
        "with s_f = 1 and l = 1. Then k(0,0) = k(2,2) = 1 and k(0,2) = "
        "exp(-4/2) = 0.1353, so K + s_n^2 I = [[1.01, 0.1353], [0.1353, 1.01]]. "
        "Solving that system against y = (1, 3) gives alpha = (0.6029, 2.8895). "
        "Predict at x* = 1: k_* = (exp(-0.5), exp(-0.5)) = (0.6065, 0.6065), so "
        "the posterior mean is 0.6065(0.6029 + 2.8895) = **2.12** and the "
        "posterior variance is 1 - k_*^T K^-1 k_* = **0.358**, a standard "
        "deviation of 0.60. Midway between two observations one lengthscale "
        "apart, the GP interpolates and still reports substantial uncertainty. "
        "At x* = 10 the kernel vector is numerically zero, so the mean returns "
        "to the prior mean 0 and the variance to 1 - **a GP knows when it is "
        "extrapolating**, which is the property no plain neural network has for "
        "free.")

    tbl(["Property", "Gaussian process", "Neural network"],
        [["Cost", "O(n^3) to fit, O(n^2) per prediction", "O(n) per epoch"],
         ["Practical data size", "Up to ~10k exactly; sparse/inducing methods "
          "beyond", "Unbounded"],
         ["Uncertainty", "Exact and calibrated under the prior", "Requires "
          "ensembles or approximations (Chapter 33)"],
         ["Priors", "Explicit in the kernel: smoothness, periodicity, linear "
          "trends", "Implicit in architecture and initialization"],
         ["High-dimensional raw input", "Weak without a learned kernel",
          "The reason deep learning exists"]],
        widths=[20, 42, 38], bold_first=True)
    p("The killer application is **Bayesian optimization**: when each evaluation "
      "is expensive - a training run, a lab experiment, a hardware measurement - "
      "fit a GP to the results so far and pick the next point by maximizing an "
      "acquisition function such as expected improvement or the upper confidence "
      "bound mu(x) + kappa sigma(x). This is why GPs are the standard engine "
      "inside hyperparameter tuners for budgets of tens to a few hundred trials, "
      "where random search is wasteful and grid search is hopeless.")

    h2("When the integral is intractable: VI and MCMC")
    p("Conjugacy is a luxury. For everything else there are two families of "
      "approximation, and the choice between them is the classic speed-versus-"
      "accuracy trade in probabilistic modelling.")
    eq(["Variational inference:  pick q(theta) in a simple family,",
        "  maximize  ELBO(q) = E_q[ log p(D, theta) ] - E_q[ log q(theta) ]",
        "          = log p(D) - KL( q || p(theta|D) )",
        "so maximizing the ELBO minimizes KL to the true posterior."],
       "This is the same ELBO as the VAE in Chapter 25 - there, q is produced by "
       "an encoder network instead of being optimized per data point.")
    tbl(["", "Variational inference", "MCMC"],
        [["Idea", "Turn integration into optimization", "Sample a chain whose "
          "stationary distribution is the posterior"],
         ["Speed", "Fast, scales to large data with mini-batches",
          "Slow; typically thousands of passes"],
         ["Bias", "Biased: limited to the chosen family; mean-field q "
          "underestimates variance", "Asymptotically exact"],
         ["Workhorse", "ADVI, Bayes-by-backprop, VAEs",
          "Metropolis-Hastings, Gibbs, HMC / NUTS"],
         ["Diagnostics", "ELBO trace; compare families",
          "R-hat < 1.01, effective sample size, divergences"]],
        widths=[14, 43, 43], bold_first=True)
    code([
        "# Metropolis-Hastings: the entire algorithm",
        "theta = theta_init",
        "for t in range(T):",
        "    prop = theta + step * np.random.randn(*theta.shape)",
        "    log_ratio = log_post(prop) - log_post(theta)      # prior + likelihood",
        "    if np.log(np.random.rand()) < log_ratio:",
        "        theta = prop                                   # accept",
        "    chain.append(theta)",
        "# Tune 'step' for an acceptance rate near 0.234 for high-dimensional",
        "# random-walk proposals; discard the first half as burn-in.",
    ])
    box("warn", "The three ways probabilistic models are misused",
        "Reporting a posterior interval as if it were a frequentist confidence "
        "interval when the prior was chosen carelessly; running a chain for a "
        "few hundred steps and never checking R-hat, so the 'posterior' is a "
        "record of where the chain happened to start; and using mean-field VI "
        "and then quoting its variance, which is systematically too small. All "
        "three produce confident numbers that are wrong in the same direction: "
        "too certain.")

    h2("Choosing your weapon")
    tbl(["Situation", "Use"],
        [["Under ~1,000 rows, uncertainty matters", "Bayesian model with "
          "conjugate or GP structure"],
         ["Cheap ranking of items with small counts", "Beta posterior mean or "
          "lower bound"],
         ["Hidden discrete structure over time", "HMM (Baum-Welch); a "
          "recurrent net only if you have far more data"],
         ["Expensive black-box tuning, < 200 trials", "GP Bayesian optimization"],
         ["Millions of rows, uncertainty is secondary", "Deep model plus an "
          "ensemble or temperature scaling (Chapter 33)"],
         ["You need a probability you will act on financially",
          "Full posterior if the model is small; deep ensemble plus calibration "
          "if it is not"]],
        widths=[44, 56], bold_first=True)

    h3("Exercises")
    bul([
        "Derive the Beta-Bernoulli posterior from Bayes' rule and confirm that "
        "the posterior mean lies between the prior mean and the MLE.",
        "Implement the ten-line GMM above and run it on the four points 1, 2, "
        "8, 9. Verify the responsibilities quoted in the box.",
        "Implement Viterbi and reproduce the umbrella example, then check that "
        "the forward algorithm gives the total probability of the observation "
        "sequence.",
        "Fit a GP with an RBF kernel to five points of a sine wave and plot the "
        "mean with two-standard-deviation bands. Increase the lengthscale by "
        "10x and explain what happens to both.",
        "Take a logistic regression with 200 rows, fit it by MAP and then by "
        "Metropolis-Hastings, and compare the coefficient intervals with the "
        "bootstrap intervals from Chapter 13.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 39 ---
    chapter("Time Series and Forecasting")
    p("Time series break the assumption every earlier chapter rested on: the "
      "rows are not independent, and the future is not exchangeable with the "
      "past. That single change invalidates random splits, ordinary "
      "cross-validation, most feature engineering habits, and the intuition "
      "that more model capacity helps. It also creates the most common "
      "catastrophic bug in applied machine learning - a feature that quietly "
      "contains the future.")

    h2("What makes a time series different")
    tbl(["Property", "Consequence"],
        [["Observations are ordered and autocorrelated",
          "Random shuffling leaks the future into training; only time-ordered "
          "splits are valid"],
         ["The distribution drifts (non-stationarity)",
          "A model fitted on 2019 may be structurally wrong in 2024, not just "
          "stale"],
         ["Seasonality at several periods at once",
          "Daily, weekly and yearly cycles superimpose; each needs its own "
          "representation"],
         ["The horizon is part of the problem",
          "Predicting one step ahead and 28 steps ahead are different tasks "
          "with different achievable errors"],
         ["Data is revised after the fact",
          "The value you have today for last Tuesday may not be the value that "
          "was available last Tuesday"]],
        widths=[34, 66], bold_first=True)
    box("warn", "The number one bug in forecasting",
        "Computing any statistic over the whole series before splitting: a "
        "global mean and standard deviation for scaling, a target encoding, an "
        "imputation fill, a de-seasonalizing step. Every one of them carries "
        "future information backwards and produces a backtest that cannot be "
        "reproduced in production. **Fit every transformation on the training "
        "window only, then apply it forward.**")

    h2("Decomposition: trend, seasonality, remainder")
    eq(["Additive         y_t = T_t + S_t + R_t",
        "Multiplicative   y_t = T_t * S_t * R_t   (log => additive)"],
       "Use multiplicative when the seasonal swing grows with the level - retail "
       "sales, traffic. Taking logs first is usually simpler than changing "
       "model families.")
    p("STL decomposition (seasonal-trend by LOESS) is the workhorse: robust to "
      "outliers, handles a changing seasonal shape, and gives you three series "
      "to inspect. Plot them before modelling anything. Most 'the model is "
      "broken' reports resolve into 'the seasonality changed in March' once the "
      "decomposition is on screen.")

    h2("Stationarity, differencing, ACF and PACF")
    p("A series is (weakly) stationary if its mean, variance and autocovariance "
      "do not depend on t. Classical models require it; ML models tolerate "
      "non-stationarity only if you give them the right features. Differencing "
      "is the standard cure.")
    eq(["First difference     z_t = y_t - y_(t-1)          removes a linear trend",
        "Seasonal difference  z_t = y_t - y_(t-m)          removes a period-m cycle",
        "ACF(k)   = corr( y_t, y_(t-k) )         total correlation at lag k",
        "PACF(k)  = corr of the part of y_t and y_(t-k) not explained by lags 1..k-1"])
    tbl(["Pattern in the plots", "Reading"],
        [["ACF decays slowly, almost linearly", "Non-stationary: difference it"],
         ["ACF cuts off after lag q, PACF decays", "MA(q)"],
         ["PACF cuts off after lag p, ACF decays", "AR(p)"],
         ["Both decay", "ARMA(p,q); choose orders by AIC"],
         ["Spike at lag m and its multiples", "Seasonal component of period m"]],
        widths=[42, 58], bold_first=True)
    p("The augmented Dickey-Fuller test formalizes the first row, but the plot "
      "is usually enough and always more informative. Note that differencing "
      "twice when once was enough injects noise - prefer the smallest d that "
      "makes the ACF decay quickly.")

    h2("The classical families")
    eq(["AR(p)      y_t = c + SUM_(i=1..p) phi_i y_(t-i) + e_t",
        "MA(q)      y_t = c + e_t + SUM_(j=1..q) theta_j e_(t-j)",
        "ARIMA(p,d,q)  = ARMA(p,q) applied to the d-times differenced series",
        "SARIMA(p,d,q)(P,D,Q)_m adds the same structure at the seasonal lag m",
        "ETS        exponential smoothing of Error, Trend, Seasonal components"])
    box("math", "AR(1) by hand, and what its coefficient means",
        "Series 10, 12, 11, 13, 12 with mean 11.6. Centred: -1.6, 0.4, -0.6, "
        "1.4, 0.4. The lag-1 autocovariance is the average of the products of "
        "consecutive centred values: (-1.6)(0.4) + (0.4)(-0.6) + (-0.6)(1.4) + "
        "(1.4)(0.4) = -0.64 - 0.24 - 0.84 + 0.56 = -1.16, divided by 5 gives "
        "-0.232. The variance is (2.56 + 0.16 + 0.36 + 1.96 + 0.16)/5 = 1.04. "
        "So phi = -0.232/1.04 = **-0.223**: a negative coefficient, meaning the "
        "series alternates - a high value tends to be followed by a low one. "
        "The forecast for t = 6 is 11.6 + (-0.223)(12 - 11.6) = **11.51**, and "
        "every further step decays geometrically back to the mean. **An AR(1) "
        "forecast reverts to the mean at rate phi^h; if your business problem "
        "needs a long horizon, an AR model will give you a flat line and be "
        "right to do so.**")
    p("Holt-Winters (ETS with additive trend and seasonality) remains an "
      "excellent default for short, seasonal, low-noise series and takes three "
      "smoothing parameters. In the M4 and M5 forecasting competitions, simple "
      "statistical methods and their combinations beat most sophisticated "
      "entries; the winning entries were hybrids that used a global learned "
      "model on top of classical structure. **Always fit the classical baseline "
      "first.**")

    h2("The machine-learning approach: supervised windows")
    p("Reframe forecasting as regression: build a table whose row t contains "
      "features known strictly before t and whose target is y at t + h. This is "
      "the approach that wins most business forecasting problems, because it "
      "absorbs covariates - price, promotions, weather, holidays - that "
      "classical models handle awkwardly.")
    code([
        "# Direct multi-horizon framing: one model per horizon h",
        "def make_features(df, h):",
        "    X = pd.DataFrame(index=df.index)",
        "    for lag in [h, h+1, h+2, h+7, h+14, h+28]:      # never lag < h",
        "        X[f'lag_{lag}'] = df['y'].shift(lag)",
        "    for w in [7, 28]:",
        "        X[f'roll_mean_{w}'] = df['y'].shift(h).rolling(w).mean()",
        "        X[f'roll_std_{w}']  = df['y'].shift(h).rolling(w).std()",
        "    X['dow']   = df.index.dayofweek",
        "    X['month'] = df.index.month",
        "    X['is_holiday'] = df['holiday'].astype(int)      # known in advance",
        "    y = df['y'].shift(-0)                            # target at time t",
        "    return X, y",
    ], "The shift(h) on every rolling statistic is the whole game: at the moment "
       "of prediction you know values up to t - h, and nothing after. Write this "
       "function once, review it twice, and never compute a rolling window "
       "without an accompanying shift.")
    tbl(["Strategy", "How", "Trade-off"],
        [["Recursive", "One one-step model, feed predictions back in",
          "Cheap; errors compound over the horizon"],
         ["Direct", "One model per horizon h", "No compounding; h models to "
          "train and maintain"],
         ["Multi-output", "One model predicting the whole horizon vector",
          "Shares structure; needs a model that supports vector targets"]],
        widths=[16, 44, 40], bold_first=True)
    box("tip", "Local versus global models",
        "A __local__ model is fitted per series (one ARIMA per SKU). A "
        "__global__ model is one model fitted across all series with the series "
        "identity as a feature or embedding. Global models win when you have "
        "many related series with short histories - they borrow strength - and "
        "they are how gradient boosting and modern deep forecasters take retail "
        "problems with 50,000 SKUs. Local models win when series are few, long "
        "and genuinely unrelated.")

    h2("Deep learning for forecasting")
    tbl(["Model", "Idea", "When it is worth it"],
        [["DeepAR", "Autoregressive RNN emitting distribution parameters per "
          "step", "Many related series, probabilistic output required"],
         ["N-BEATS / N-HiTS", "Deep stacks of basis expansions with "
          "backcast/forecast residuals", "Univariate benchmarks, no covariates "
          "needed"],
         ["Temporal Fusion Transformer", "Attention over time plus gated "
          "variable selection", "Many covariates, and you need interpretable "
          "attention over them"],
         ["PatchTST / Transformers", "Patch the series into tokens, apply a "
          "Transformer", "Long horizons with abundant history"],
         ["Foundation forecasters", "Pretrained across millions of series, used "
          "zero-shot", "Cold-start series and rapid prototyping"]],
        widths=[22, 44, 34], bold_first=True)
    box("warn", "The honest state of the art",
        "On standard long-horizon benchmarks, a well-tuned linear model on "
        "lagged inputs matches or beats several published Transformer "
        "forecasters, a result that survived careful replication. Deep "
        "forecasting earns its keep with **many series, rich covariates, and "
        "distributional output** - not with a single univariate series, where "
        "ETS or gradient boosting on lag features is usually both better and "
        "a hundred times cheaper.")

    h2("Backtesting: the only evaluation that counts")
    diagram([
        "  |---------- train ----------|gap|-- test --|                fold 1",
        "  |---------------- train ----------|gap|-- test --|          fold 2",
        "  |---------------------- train ----------|gap|-- test --|    fold 3",
        "",
        "  expanding window (above) keeps all history;",
        "  a rolling window drops the oldest data instead - use it when",
        "  the process changes and old data actively misleads.",
    ], "Rolling-origin evaluation. The gap must be at least the forecast "
       "horizon, so no training row is closer to a test row than the horizon "
       "you claim to predict.")
    p("Rules that make a backtest believable: the test folds are contiguous and "
      "in the future; every transformation is refitted inside each fold; the "
      "horizon in the backtest equals the horizon in production; and the number "
      "of folds is large enough that you are averaging over several regimes, "
      "not one lucky quarter. Report the metric per fold, not only its mean - "
      "the spread across folds is the number that predicts how the model will "
      "behave next quarter.")

    h2("Metrics, and the one that is quietly broken")
    eq(["MAE   = mean |y - yhat|                       units of y, robust",
        "RMSE  = sqrt( mean (y - yhat)^2 )             punishes large misses",
        "MAPE  = mean |y - yhat| / |y| * 100           BREAKS when y ~ 0",
        "sMAPE = mean 2|y - yhat| / (|y| + |yhat|)     asymmetric in practice",
        "MASE  = MAE(model) / MAE(seasonal naive on the training set)",
        "Pinball_q = mean [ q(y - yhat) if y >= yhat else (1-q)(yhat - y) ]"],
       "MASE is the safe default: scale-free, defined at zero, and below 1 "
       "exactly when you beat the naive baseline.")
    box("math", "MASE computed",
        "A daily series where the seasonal-naive (last week's same weekday) "
        "forecast has MAE 12.0 on the training set. Your model scores MAE 9.6 "
        "on the backtest. MASE = 9.6 / 12.0 = **0.80**: you are 20% better than "
        "doing nothing clever. If MASE >= 1 - which happens more often than "
        "anyone admits - the model is worse than a one-line baseline and should "
        "not ship. **Always report the naive baseline next to the model.**")
    p("For probabilistic forecasts, evaluate the interval, not just the point: "
      "report pinball loss at the quantiles you actually use, and check "
      "**coverage** - the fraction of actuals falling inside the 80% interval "
      "should be 80%, not 55%. Inventory, staffing and capacity decisions all "
      "consume a quantile, not a mean, so a model with a good mean and a "
      "miscalibrated tail is the wrong model.")

    h2("Hierarchies, intermittency and anomalies")
    bul([
        "**Hierarchical forecasting.** Store-level forecasts must sum to "
        "region-level and national forecasts. Forecast every level "
        "independently, then reconcile - MinT reconciliation is the standard "
        "method and usually improves accuracy at every level, not only "
        "consistency.",
        "**Intermittent demand.** Series that are zero most days (spare parts) "
        "break MAPE and mislead RMSE. Croston's method or a two-part model "
        "(probability of a nonzero day x expected size) is the right shape.",
        "**Anomaly detection.** Fit a forecast, then flag points whose residual "
        "exceeds a robust threshold, for example a multiple of the median "
        "absolute deviation. Seasonal-hybrid ESD is the classical choice. "
        "Anomalies must then be replaced in the training window or the next "
        "forecast will chase them.",
        "**Change points.** A structural break - a pricing change, a pandemic, "
        "a new competitor - is not an outlier to be smoothed. Detect it, and "
        "either restrict the training window or add an indicator feature.",
    ])

    h3("Exercises")
    bul([
        "Take any daily series, plot the STL decomposition, and write one "
        "sentence describing each of the three components.",
        "Compute the AR(1) coefficient by hand on the five numbers in the box, "
        "then confirm it with a library fit.",
        "Build the supervised window table for h = 7, then deliberately remove "
        "the shift(h) from one rolling feature and measure how much the "
        "backtest score improves. That improvement is the size of the leak you "
        "would have shipped.",
        "Run a five-fold rolling-origin backtest of a seasonal-naive baseline "
        "and a gradient-boosted model, and report MASE per fold for both.",
        "Produce 10th, 50th and 90th percentile forecasts, measure empirical "
        "coverage of the 80% interval, and calibrate it if it is off.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 40 ---
    chapter("Recommender Systems")
    p("Recommendation is the highest-revenue application of machine learning in "
      "existence and the one whose textbook description least resembles its "
      "practice. The differences: the label depends on what you showed, so the "
      "data is generated by your own past model; the item catalogue is too "
      "large to score exhaustively; and the offline metric agrees with the "
      "online outcome only sometimes.")

    h2("The industrial shape of the problem")
    diagram([
        "  millions of items",
        "        |",
        "  [ RETRIEVAL ]   cheap, recall-oriented, many sources in parallel",
        "        |         (two-tower ANN, co-visitation, popularity, rules)",
        "   ~ 500 candidates",
        "        |",
        "  [ RANKING ]     expensive model, rich features, one score per item",
        "        |         (GBDT or deep ranker, tens of ms budget)",
        "    ~ 50 ranked",
        "        |",
        "  [ RE-RANKING ]  diversity, freshness, business rules, dedup, ads",
        "        |",
        "     10 shown",
    ], "The funnel. Each stage has a different objective and a different cost "
       "budget; confusing them is the most common architectural mistake.")
    tbl(["Stage", "Objective", "Latency budget", "Metric"],
        [["Retrieval", "Do not lose the good items", "1-10 ms over millions",
          "Recall@k"],
         ["Ranking", "Order the survivors correctly", "10-50 ms over hundreds",
          "NDCG, AUC, calibrated CTR"],
         ["Re-ranking", "Make the list good as a __set__", "< 5 ms",
          "Diversity, coverage, business KPIs"]],
        widths=[16, 40, 22, 22], bold_first=True)

    h2("Feedback data and what it really means")
    tbl(["Signal", "Density", "Bias"],
        [["Explicit ratings", "Very sparse (< 1% of pairs)",
          "Only motivated users rate; J-shaped distribution"],
         ["Clicks", "Dense", "Position bias, popularity bias, clickbait"],
         ["Dwell time / completion", "Dense", "Better proxy for satisfaction; "
          "content-length confound"],
         ["Purchases / subscriptions", "Sparse but decisive", "Delayed, and "
          "attribution is contested"],
         ["Explicit negatives (hide, not interested)", "Very sparse",
          "High precision, worth weighting heavily"]],
        widths=[30, 26, 44], bold_first=True)
    box("key", "Missing is not negative",
        "A user did not click an item either because they disliked it or "
        "because they never saw it. Treating all non-interactions as negatives "
        "biases the model towards whatever your previous system happened to "
        "show. The standard corrections are confidence weighting (implicit ALS), "
        "sampled negatives drawn from the catalogue rather than from "
        "impressions, and inverse-propensity weighting by the probability the "
        "item was shown.")

    h2("Neighbourhood collaborative filtering")
    eq(["Item-item score:",
        "  s(u, i) = SUM_(j in items rated by u) sim(i, j) r_uj",
        "            -------------------------------------------",
        "                     SUM_j |sim(i, j)|",
        "Cosine similarity:  sim(i,j) = (r_i . r_j) / (||r_i|| ||r_j||)"],
       "Item-item beats user-user in practice: item vectors are denser, more "
       "stable over time, and precomputable.")
    box("math", "Item-item on a tiny matrix",
        "Three users, ratings on items A, B, C: u1 = (5, 4, ?), u2 = (4, 5, 2), "
        "u3 = (1, 2, 5). Column A = (5,4,1), B = (4,5,2), C = (?,2,5) - use "
        "(0,2,5) for the cosine over co-rated users only. sim(A,B) = "
        "(20+20+2)/(sqrt(42) sqrt(45)) = 42/43.5 = **0.966**; sim(A,C) using "
        "users 2 and 3 = (8+5)/(sqrt(17) sqrt(29)) = 13/22.2 = **0.586**. "
        "Predicting C for u1 from their ratings of A and B: "
        "(0.586(5) + sim(B,C)(4)) / (0.586 + sim(B,C)). Over users 2 and 3, "
        "sim(B,C) = (10 + 10)/(sqrt(29) sqrt(29)) = 0.690, so the prediction is "
        "(2.93 + 2.76)/1.276 = **4.46** - which is too high, and usefully so: u1 looks like u2, who rated C low. The fix is to centre "
        "each user's ratings before computing similarities, which removes the "
        "'this user rates everything highly' effect. **Mean-centring is not "
        "optional in neighbourhood CF.**")

    h2("Matrix factorization, the model that won Netflix")
    eq(["rhat_ui = mu + b_u + b_i + p_u . q_i",
        "min  SUM_(u,i in observed) (r_ui - rhat_ui)^2",
        "     + lambda ( ||p_u||^2 + ||q_i||^2 + b_u^2 + b_i^2 )",
        "SGD updates, with e_ui = r_ui - rhat_ui:",
        "  b_u <- b_u + lr (e_ui - lambda b_u)",
        "  p_u <- p_u + lr (e_ui q_i - lambda p_u)",
        "  q_i <- q_i + lr (e_ui p_u - lambda q_i)"],
       "The bias terms alone - global mean, user leniency, item popularity - "
       "capture most of the achievable improvement over the global average. Fit "
       "them before adding factors.")
    box("math", "One SGD step, arithmetic included",
        "mu = 3.5, b_u = 0.2, b_i = -0.3, p_u = (0.1, 0.4), q_i = (0.5, -0.2), "
        "lr = 0.01, lambda = 0.05, true rating 5. Prediction = 3.5 + 0.2 - 0.3 "
        "+ (0.05 - 0.08) = 3.37. Error e = 1.63. Then b_u becomes 0.2 + "
        "0.01(1.63 - 0.05(0.2)) = **0.2162**; p_u becomes (0.1, 0.4) + "
        "0.01(1.63(0.5, -0.2) - 0.05(0.1, 0.4)) = (0.1 + 0.00810, 0.4 - "
        "0.00346) = **(0.1081, 0.3965)**. The first component of p_u moved "
        "towards q_i because the item was under-predicted; the second moved "
        "away because q_i's second component is negative. That is all matrix "
        "factorization does, a hundred million times.")
    p("For implicit feedback, the objective changes shape: every unobserved "
      "pair enters the sum with low confidence rather than being ignored.")
    eq(["Implicit ALS:  min SUM_(all u,i) c_ui ( pref_ui - p_u . q_i )^2 + reg",
        "  pref_ui = 1 if any interaction else 0",
        "  c_ui    = 1 + alpha * count_ui        (confidence grows with count)",
        "BPR (pairwise): max SUM log sigmoid( p_u.q_i - p_u.q_j )",
        "  i = an item the user interacted with, j = a sampled unseen item"],
       "ALS is embarrassingly parallel and closed-form per user; BPR optimizes "
       "ranking directly and is the better choice when you only care about the "
       "order of the top few.")

    h2("Neural retrieval and sequential models")
    p("The **two-tower** model is the modern retrieval workhorse: one encoder "
      "for the user context, one for the item, trained so that the dot product "
      "of their embeddings predicts interaction. Because the item tower does "
      "not see the user, all item embeddings can be precomputed and indexed; "
      "retrieval becomes approximate nearest-neighbour search.")
    code([
        "# Two-tower training with in-batch negatives (sampled softmax)",
        "u = user_tower(user_features)            # (B, d)",
        "v = item_tower(item_features)            # (B, d), the positives",
        "logits = u @ v.T / temperature           # (B, B); diagonal = positives",
        "# correct for popularity: subtract log of sampling probability",
        "logits = logits - torch.log(item_freq).unsqueeze(0)",
        "loss = F.cross_entropy(logits, torch.arange(len(u), device=u.device))",
    ], "Every other item in the batch serves as a negative, which is why large "
       "batches matter here. The log-frequency correction is essential: without "
       "it the model learns to retrieve popular items and nothing else.")
    tbl(["Index", "Structure", "Trade-off"],
        [["Flat / brute force", "Exact dot product over all items",
          "Perfect recall; fine up to ~1M items with a GPU"],
         ["IVF", "Cluster items, search a few clusters",
          "Tunable via nprobe; needs training"],
         ["HNSW", "Navigable small-world graph", "Best latency/recall; high "
          "memory, slow to build"],
         ["Product quantization", "Compress vectors to codes",
          "8-32x memory saving; some recall loss - the same trade as Chapter 28"]],
        widths=[22, 34, 44], bold_first=True)
    p("**Sequential recommenders** treat a user's history as a sequence and "
      "predict the next item: GRU4Rec used a recurrent net, SASRec a causal "
      "Transformer, BERT4Rec a masked one. They are the strongest family when "
      "order carries meaning - sessions, media consumption, learning paths - "
      "and they connect this chapter directly to Chapters 22 to 24: the "
      "architecture is identical, only the vocabulary is items instead of "
      "tokens.")

    h2("Ranking and its metrics")
    p("The ranker sees hundreds of candidates and rich features: user history "
      "aggregates, item statistics, context (time, device, position), and "
      "cross features. Gradient-boosted trees with a ranking objective "
      "(LambdaMART) remain extremely strong; deep rankers (Wide and Deep, DLRM, "
      "DCN) win when there are many high-cardinality categorical features whose "
      "interactions matter.")
    eq(["Precision@k = (relevant items in top k) / k",
        "Recall@k    = (relevant items in top k) / (all relevant items)",
        "DCG@k       = SUM_(i=1..k)  rel_i / log2(i + 1)",
        "NDCG@k      = DCG@k / IDCG@k     (IDCG = DCG of the perfect ordering)",
        "MRR         = mean of 1 / (rank of the first relevant item)"])
    box("math", "NDCG@3 by hand",
        "Relevances of the three items you showed, in the order you showed "
        "them: 1, 0, 2. DCG = 1/log2(2) + 0/log2(3) + 2/log2(4) = 1/1 + 0 + "
        "2/2 = **2.00**. The ideal ordering is 2, 1, 0, giving IDCG = "
        "2/1 + 1/1.585 + 0 = 2 + 0.631 = **2.631**. NDCG@3 = 2.00/2.631 = "
        "**0.760**. Now swap your first two items to get 0, 1, 2: DCG = 0 + "
        "1/1.585 + 1 = 1.631 and NDCG falls to 0.620. **The logarithmic "
        "discount is what makes the metric care about the top of the list** - "
        "moving a relevant item from position 2 to position 1 is worth far more "
        "than moving one from position 9 to position 8, which is exactly how "
        "users behave.")
    box("warn", "Offline metrics disagree with online outcomes",
        "An offline NDCG improvement can lose an A/B test, routinely. The three "
        "reasons: your offline data only contains items the old system showed, "
        "so a genuinely better retrieval looks worse; position bias inflates "
        "whatever the old ranker put on top; and the online objective (long-term "
        "retention) is not the offline label (this session's click). Treat "
        "offline metrics as a filter that decides what is worth testing, never "
        "as the decision itself.")

    h2("The problems that only recommenders have")
    tbl(["Problem", "What happens", "Standard treatment"],
        [["Cold start (item)", "New items have no interactions and are never "
          "shown", "Content features in the item tower; explicit exploration "
          "budget"],
         ["Cold start (user)", "No history to personalize on",
          "Popularity by segment, onboarding preferences, contextual bandits"],
         ["Position bias", "Top slots get clicks regardless of relevance",
          "Inverse-propensity weighting; randomized-slot data collection"],
         ["Popularity bias", "The rich get richer; the tail dies",
          "Frequency-corrected sampling, exposure-aware objectives"],
         ["Feedback loop", "Model trains on its own recommendations and "
          "narrows", "Logged exploration data, off-policy correction, "
          "diversity constraints"],
         ["Filter bubble / harms", "Users are pushed towards ever narrower or "
          "more extreme content", "Diversity and novelty objectives, "
          "content-quality classifiers, explicit ranking policy"]],
        widths=[20, 40, 40], bold_first=True)
    p("Off-policy evaluation gives a partial answer to 'how would the new "
      "ranker have done?' using logged data, by importance-weighting each "
      "logged interaction by the ratio of new-policy to logging-policy "
      "probability. Inverse propensity scoring is unbiased but high-variance; "
      "clipped and doubly-robust estimators trade a little bias for a lot of "
      "variance. All of them require that the logging policy was **stochastic** "
      "and that its probabilities were logged - a decision you must make before "
      "you need it, not after.")
    box("tip", "The one-week recommender",
        "Day 1: popularity baseline by segment, measured. Day 2: item-item "
        "co-visitation from the last 30 days - typically beats popularity by a "
        "wide margin and costs nothing. Day 3-4: implicit ALS or a two-tower "
        "model for retrieval. Day 5: a GBDT ranker over the candidates with "
        "twenty features. Day 6: diversity and dedup rules. Day 7: A/B test "
        "with a holdout that never receives personalization, so you can measure "
        "the value of the whole system for as long as it runs.")

    h3("Exercises")
    bul([
        "Compute NDCG@5 for two orderings of the same five items by hand, then "
        "verify with a library.",
        "Build the item-item co-visitation baseline on any interaction log and "
        "measure Recall@20 against a time-based holdout.",
        "Implement the matrix-factorization SGD update and reproduce the "
        "arithmetic in the worked box exactly.",
        "Train a two-tower model with and without the log-frequency correction "
        "and compare the popularity distribution of what each retrieves.",
        "Take a logged ranking dataset, estimate position bias by comparing "
        "click rates of the same item in different slots, and re-weight your "
        "training data accordingly.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 41 ---
    chapter("Computer Vision Beyond Classification")
    p("Chapter 21 stopped at 'which class is this image?'. Almost no real vision "
      "product stops there. This chapter covers what the other tasks are, the "
      "geometry and matching machinery they need, the metrics that are easy to "
      "misreport, and the deployment details that decide whether a detector "
      "runs at 5 or 50 frames per second.")

    h2("The task taxonomy")
    tbl(["Task", "Output per image", "Typical metric"],
        [["Classification", "One label (or a multi-label vector)",
          "Accuracy, mAP for multi-label"],
         ["Object detection", "A set of boxes with classes and scores",
          "mAP@[.50:.95]"],
         ["Semantic segmentation", "A class for every pixel", "mIoU"],
         ["Instance segmentation", "A mask per object instance",
          "Mask AP"],
         ["Panoptic segmentation", "Instances for things, regions for stuff",
          "Panoptic Quality"],
         ["Keypoints / pose", "Ordered landmark coordinates", "OKS-based AP"],
         ["Depth / normals", "A continuous value per pixel",
          "Abs-rel error, delta < 1.25"],
         ["Multi-object tracking", "Boxes plus consistent identities over time",
          "MOTA, IDF1, HOTA"]],
        widths=[24, 44, 32], bold_first=True)
    box("key", "The structural difference from classification",
        "The output is a **set of variable size**, not a fixed vector. That "
        "single fact forces everything that follows: a matching step between "
        "predictions and ground truth, a rule for suppressing duplicates, and a "
        "metric that must integrate over both confidence and overlap thresholds.")

    h2("IoU, the quantity everything is built on")
    eq(["IoU(A, B) = area(A INTERSECT B) / area(A UNION B)",
        "          = I / (area(A) + area(B) - I)"])
    box("math", "IoU computed on two boxes",
        "Prediction (x1,y1,x2,y2) = (10, 10, 50, 50), ground truth = "
        "(30, 20, 70, 60). The intersection spans x from max(10,30) = 30 to "
        "min(50,70) = 50 and y from max(10,20) = 20 to min(50,60) = 50, so it "
        "is 20 x 30 = **600**. The areas are 40 x 40 = 1600 each, so the union "
        "is 1600 + 1600 - 600 = **2600** and IoU = 600/2600 = **0.231**. That "
        "box would count as a false positive at the standard 0.5 threshold "
        "despite overlapping substantially - which is why 'the model found the "
        "object' and 'the model scored a true positive' are different claims.")
    p("Non-maximum suppression turns a dense score map into a set: sort boxes by "
      "score, keep the top one, delete every remaining box whose IoU with it "
      "exceeds a threshold, repeat. Its two failure modes are worth knowing: "
      "crowded scenes lose genuine overlapping objects (soft-NMS decays scores "
      "instead of deleting), and NMS is often the latency bottleneck on device "
      "because it is sequential and data-dependent.")

    h2("Detector families")
    tbl(["Family", "Representative", "Mechanism", "Trade-off"],
        [["Two-stage", "Faster R-CNN", "A region proposal network proposes, a "
          "head classifies and refines with RoIAlign", "Most accurate per "
          "FLOP historically; slower and more complex"],
         ["One-stage anchored", "RetinaNet, SSD, YOLOv3", "Dense predictions "
          "over predefined anchor boxes", "Fast; needs focal loss or hard "
          "negative mining for the 1000:1 background imbalance"],
         ["Anchor-free", "FCOS, CenterNet", "Predict object centres and "
          "distances to box sides", "No anchor hyperparameters to tune; "
          "simpler heads"],
         ["Set prediction", "DETR, DINO", "Transformer decoder with Hungarian "
          "matching to ground truth", "No NMS and no anchors; slow to converge "
          "originally, largely fixed by later variants"],
         ["Modern real-time", "YOLOv8-class, RT-DETR", "Anchor-free heads, "
          "heavy augmentation, distillation", "The practical default for "
          "deployment today"]],
        widths=[16, 18, 36, 30], bold_first=True)
    eq(["Focal loss   FL(p_t) = -alpha_t (1 - p_t)^gamma log(p_t)",
        "  gamma = 2 typical: an easy background example with p_t = 0.99",
        "  is down-weighted by (0.01)^2 = 1e-4 relative to plain cross-entropy"],
       "The whole idea: with 100,000 anchors and 5 objects, the sum of many "
       "tiny easy-negative losses drowns out the few that matter.")
    p("Hungarian matching in DETR replaces both anchors and NMS: predictions "
      "and ground-truth objects are matched one-to-one by minimizing a cost "
      "combining class probability and box distance, so duplicates are "
      "penalized by construction rather than removed afterwards. It is the "
      "clearest example in vision of replacing a hand-designed post-processing "
      "step with a learned, end-to-end one.")

    h2("Segmentation")
    diagram([
        "  U-Net: contracting path + expanding path with skip connections",
        "",
        "  input --> [conv] --> [conv] --> [conv] ---bottleneck---",
        "              |          |          |                    |",
        "              |skip      |skip      |skip                |",
        "              v          v          v                    v",
        "  output <-- [up] <---- [up] <---- [up] <----------------",
        "",
        "  The skips carry high-resolution detail that pooling destroyed;",
        "  without them the mask boundaries are blurred beyond usefulness.",
    ], "U-Net remains the default for medical and scientific segmentation with "
       "small datasets, fifteen years of newer architectures notwithstanding.")
    bul([
        "**FCN** replaced the classifier head with 1x1 convolutions and "
        "upsampling - the idea that started the field.",
        "**U-Net** added symmetric skip connections; it is data-efficient and "
        "trains on a few hundred annotated images.",
        "**DeepLab** used atrous (dilated) convolutions and ASPP to enlarge the "
        "receptive field without losing resolution.",
        "**Mask R-CNN** added a mask head to Faster R-CNN, making instance "
        "segmentation a small increment over detection.",
        "**Transformer-based** (SegFormer, Mask2Former) unified semantic, "
        "instance and panoptic segmentation as mask classification.",
        "**Promptable segmentation** (SAM-style) produces masks from a point or "
        "box prompt with no task-specific training, which turns annotation from "
        "hours of polygon drawing into seconds of clicking.",
    ])
    eq(["mIoU  = mean over classes of  TP / (TP + FP + FN)   at pixel level",
        "Dice  = 2 TP / (2 TP + FP + FN)      (= F1 on pixels)",
        "PQ    = (SUM_matched IoU) / (TP + 0.5 FP + 0.5 FN)"],
       "Dice and IoU are monotonically related but Dice is more forgiving on "
       "small objects, which is why medical papers quote it. Report both if "
       "your classes are very imbalanced in area.")

    h2("Mean average precision, computed honestly")
    p("AP is the area under the precision-recall curve for one class at one IoU "
      "threshold; mAP averages over classes, and COCO-style mAP averages "
      "further over IoU thresholds from 0.50 to 0.95 in steps of 0.05. That "
      "second average is why COCO mAP numbers look low: a detector with "
      "human-level box placement still loses points at IoU 0.95.")
    box("math", "AP from five detections",
        "One class, 3 ground-truth objects. Sorted by confidence, the "
        "detections are TP, FP, TP, TP, FP. Cumulative precision and recall "
        "after each: (1/1, 1/3) = (1.000, 0.333); (1/2, 1/3) = (0.500, 0.333); "
        "(2/3, 2/3) = (0.667, 0.667); (3/4, 3/3) = (0.750, 1.000); "
        "(3/5, 1.000) = (0.600, 1.000). Interpolated precision (the maximum "
        "precision at or beyond each recall level) is 1.000 at recall 1/3 and "
        "0.750 at recalls 2/3 and 1. The area, summing precision times the "
        "recall increments, is (1/3)(1.000) + (1/3)(0.750) + (1/3)(0.750) = "
        "**0.833**. Note the fourth detection - a low-confidence true positive "
        "- __raised__ AP even though it lowered precision at the top of the "
        "list, because recall matters as much as precision in this metric.")
    box("warn", "Three ways mAP gets misreported",
        "Quoting mAP@0.5 and comparing it against someone else's mAP@[.5:.95] "
        "(the first is typically 15-25 points higher); evaluating at a "
        "confidence threshold rather than over the whole curve; and reporting "
        "on a test set whose images share scenes with the training set, which "
        "is endemic in datasets scraped from video.")

    h2("Video, tracking and 3D")
    bul([
        "**Tracking-by-detection** is the dominant pipeline: run a detector "
        "per frame, then associate boxes across frames. SORT uses a Kalman "
        "filter for motion plus Hungarian matching on IoU; DeepSORT adds an "
        "appearance embedding so identities survive occlusion. The metric "
        "family (MOTA, IDF1, HOTA) separates detection quality from "
        "association quality - report HOTA if you can, since MOTA is dominated "
        "by detection errors.",
        "**Video understanding** needs temporal modelling: 3D convolutions "
        "(C3D, I3D), two-stream networks (appearance plus optical flow), and "
        "now video Transformers with spatio-temporal attention. Cost is the "
        "binding constraint - a 16-frame clip is 16x the pixels.",
        "**Depth and 3D**: monocular depth estimation is now a strong "
        "zero-shot capability; point-cloud networks (PointNet, sparse convs) "
        "handle lidar; and neural rendering (NeRF, Gaussian splatting) "
        "reconstructs a scene from posed images. These are separate "
        "sub-fields, but they share this book's core machinery entirely.",
    ])

    h2("Training and deploying detectors in practice")
    tbl(["Concern", "What to do"],
        [["Small objects dominate the errors",
          "Higher input resolution beats a bigger backbone; use feature "
          "pyramids; tile large images at inference"],
         ["Heavy augmentation is the norm",
          "Mosaic, scale jitter, random crop, colour jitter - and turn mosaic "
          "off for the last few epochs, which reliably gains a point"],
         ["Class imbalance across the catalogue",
          "Repeat-factor sampling for rare classes; do not simply oversample "
          "images"],
         ["Annotation quality dominates everything",
          "Measure inter-annotator IoU before blaming the model; a 0.8 "
          "agreement ceiling caps your mAP"],
         ["Latency on device",
          "Fuse conv-bn, use INT8 (Chapter 28), reduce input resolution first, "
          "and profile NMS separately - it is often 30% of the budget"],
         ["Preprocessing mismatch",
          "Letterboxing, channel order and normalization constants must be "
          "byte-identical between training and the deployed runtime; this is "
          "the most common cause of 'it was fine in Python'"]],
        widths=[32, 68], bold_first=True)

    h3("Exercises")
    bul([
        "Compute IoU by hand for three pairs of boxes, including one with no "
        "overlap, then implement it and check.",
        "Implement NMS in twenty lines and run it on a synthetic set of "
        "overlapping boxes at three IoU thresholds. Describe what changes.",
        "Reproduce the AP calculation in the worked box, then recompute it "
        "with the last two detections swapped.",
        "Fine-tune a small pretrained detector on 200 annotated images and "
        "report mAP@0.5 and mAP@[.5:.95] side by side.",
        "Measure your detector's end-to-end latency split into preprocessing, "
        "backbone, head and NMS. Optimize the largest term first.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 42 ---
    chapter("Natural Language Processing: From Counting Words to Retrieval")
    p("Chapter 24 covered large language models. This chapter covers everything "
      "that comes before and around them - representations that still win on "
      "small data, the tasks with their own structure, retrieval systems that "
      "give a model access to your documents, and the evaluation problem that "
      "makes language harder to measure than vision.")

    h2("The classical pipeline, and why it still matters")
    bul([
        "**Normalization**: case folding, Unicode NFKC, stripping or keeping "
        "accents and emoji. Every choice is a modelling decision; document it.",
        "**Tokenization**: whitespace and rules for classical models; subword "
        "(BPE, WordPiece, Unigram) for neural ones. Languages without spaces "
        "(Chinese, Japanese, Thai) need segmentation, and morphologically rich "
        "languages (Finnish, Turkish, Arabic) suffer most from a "
        "poorly-fitted vocabulary.",
        "**Stemming and lemmatization**: crude versus linguistic reduction to a "
        "base form. Useful for search and for bag-of-words models; harmful "
        "before a pretrained model, whose tokenizer expects raw text.",
        "**Stop words**: removing them helps TF-IDF retrieval and hurts "
        "anything that needs syntax. 'To be or not to be' is entirely stop "
        "words.",
    ])
    box("tip", "A baseline that embarrasses expensive models",
        "TF-IDF features plus linear logistic regression, on a few thousand "
        "labelled documents, trains in one second and frequently lands within a "
        "couple of points of a fine-tuned Transformer on topic classification. "
        "Run it first, always. If a large model cannot beat it by a margin that "
        "justifies its serving cost, it should not ship.")

    h2("Counting: TF-IDF and BM25")
    eq(["tf(t,d)    = count of term t in document d  (or 1 + log count)",
        "idf(t)     = log( N / df(t) )        or log( (N + 1)/(df(t) + 1) ) + 1",
        "tfidf(t,d) = tf(t,d) * idf(t),  then L2-normalize each document vector"])
    box("math", "TF-IDF on four documents",
        "N = 4 documents. The word 'the' appears in all four, so idf = "
        "log(4/4) = **0** - it contributes nothing, which is why stop-word "
        "removal is optional once you use IDF. The word 'quantization' appears "
        "in one, so idf = log(4/1) = **1.386**. In a document where "
        "'quantization' occurs 3 times and 'the' 12 times, the raw TF-IDF "
        "weights are 3 x 1.386 = 4.16 and 12 x 0 = 0. **Rarity, not frequency, "
        "is what carries information** - the single most transferable idea in "
        "information retrieval.")
    p("BM25 is TF-IDF's better-behaved successor and remains the strongest "
      "sparse retriever: it saturates term frequency (the tenth occurrence adds "
      "almost nothing) and normalizes by document length. In modern retrieval "
      "stacks BM25 is not a baseline to be replaced but a component to be "
      "combined - hybrid BM25-plus-dense retrieval beats either alone on almost "
      "every benchmark, because sparse matching catches exact names, codes and "
      "rare terms that embeddings blur.")

    h2("Word embeddings: dense meaning from co-occurrence")
    p("Word2vec's skip-gram model predicts context words from a centre word. "
      "The full softmax over a 100,000-word vocabulary is too expensive, so "
      "negative sampling replaces it with a set of binary decisions:")
    eq(["Skip-gram with negative sampling, for centre c and context o:",
        "  L = -log sigmoid( v_o . u_c )",
        "      - SUM_(k=1..K) log sigmoid( -v_k . u_c )    k sampled from P_n",
        "  P_n(w) proportional to freq(w)^0.75    (the 3/4 power matters:",
        "         it samples rare words more often than frequency alone)"],
       "Gradients: d L / d u_c = (sigmoid(v_o.u_c) - 1) v_o + SUM_k "
       "sigmoid(v_k.u_c) v_k. Two vectors per word - as centre and as context - "
       "and it is standard to keep or average them.")
    tbl(["Method", "What it optimizes", "Notable property"],
        [["word2vec (SGNS)", "Local context prediction",
          "Fast; famous analogy arithmetic king - man + woman ~ queen"],
         ["GloVe", "Weighted least squares on log co-occurrence counts",
          "Uses global statistics directly; similar quality"],
         ["FastText", "Skip-gram over character n-grams",
          "Handles out-of-vocabulary and rich morphology; the right default "
          "for non-English"],
         ["Contextual (BERT-style)", "Masked language modelling",
          "One vector per __occurrence__, so 'bank' differs by sentence"]],
        widths=[22, 38, 40], bold_first=True)
    box("warn", "Two things static embeddings get wrong",
        "They give one vector per word, so every sense of a polysemous word is "
        "averaged into a single point - 'bank' sits between rivers and finance "
        "and is a good representation of neither. And they encode the social "
        "biases of the corpus in a directly measurable way: occupation words "
        "align with gender directions, and models built on them inherit that "
        "alignment. Both are reasons the field moved to contextual "
        "representations, and the second does not disappear there.")

    h2("Tasks with structure")
    tbl(["Task", "Shape", "Standard approach"],
        [["Text classification", "Document -> label",
          "TF-IDF + linear, or fine-tuned encoder"],
         ["Sequence labelling (NER, POS)", "Token -> tag, with BIO encoding",
          "Encoder + per-token head, optionally a CRF layer"],
         ["Span extraction (QA)", "Text -> (start, end)",
          "Two heads predicting start and end positions"],
         ["Sentence pair (NLI, dedup)", "Two texts -> relation",
          "Cross-encoder for accuracy, bi-encoder for speed"],
         ["Generation (summarize, translate)", "Text -> text",
          "Encoder-decoder or decoder-only LLM"],
         ["Retrieval", "Query -> ranked documents",
          "Hybrid BM25 + dense bi-encoder, then a cross-encoder reranker"]],
        widths=[26, 30, 44], bold_first=True)
    p("BIO tagging is worth a line because it is where subtle bugs live: B-PER "
      "marks the beginning of a person entity, I-PER its continuation, O "
      "everything else. Entity-level F1 - not token accuracy - is the metric, "
      "because getting 4 of 5 tokens of a name right is not getting the name "
      "right. A CRF layer on top enforces valid transitions (an I- tag cannot "
      "follow O), which is worth one to three F1 points and costs almost "
      "nothing.")

    h2("Retrieval-augmented generation, done properly")
    diagram([
        "  query --> [rewrite] --> [BM25 search]  ---.",
        "                     \\-> [dense search] ---+--> [fuse/RRF] --> top 50",
        "                                                         |",
        "                                          [cross-encoder rerank] -> top 5",
        "                                                         |",
        "                              [prompt: question + passages] --> LLM",
        "                                                         |",
        "                                        answer + citations to passages",
    ], "The retrieval half of RAG is a search engineering problem, and it is "
       "where nearly all quality comes from. The generator can only be as good "
       "as the passages it is handed.")
    tbl(["Decision", "Guidance"],
        [["Chunk size", "200-500 tokens with 10-20% overlap; split on "
          "structure (headings, paragraphs) rather than fixed windows"],
         ["What to embed", "The chunk plus its document title and section "
          "path; a bare chunk loses the context that makes it findable"],
         ["Hybrid or dense only", "Hybrid, almost always. Dense retrieval "
          "misses exact identifiers, part numbers and rare names"],
         ["Reranking", "A cross-encoder over the top 50 is the highest "
          "value-per-millisecond component in the whole stack"],
         ["Evaluation", "Measure retrieval separately: Recall@k and MRR on "
          "questions with known answer passages, before judging the answers"],
         ["Grounding", "Require citations and check that cited passages "
          "actually contain the claim; unfaithful summaries of correct "
          "passages are the dominant failure"]],
        widths=[24, 76], bold_first=True)

    h2("Evaluating language output")
    tbl(["Metric", "Measures", "Weakness"],
        [["BLEU", "n-gram precision against references, with brevity penalty",
          "Insensitive to meaning; punishes valid paraphrase"],
         ["ROUGE-L", "Longest common subsequence recall",
          "Rewards copying; standard for summarization anyway"],
         ["chrF", "Character n-gram F-score",
          "Better for morphologically rich languages"],
         ["BERTScore", "Similarity of contextual embeddings",
          "Correlates better with humans; depends on the scoring model"],
         ["Exact match / F1 (QA)", "String overlap with the gold answer",
          "Brittle to formatting; use with normalization"],
         ["LLM-as-judge", "A model scores outputs against a rubric",
          "Position bias, verbosity bias, self-preference; needs paired "
          "randomized comparisons and a human-labelled calibration set"]],
        widths=[20, 42, 38], bold_first=True)
    box("warn", "The evaluation trap that costs the most time",
        "Benchmark contamination. If the test set existed on the public web "
        "before the model was pretrained, a high score measures memorization. "
        "For any claim that matters, build a small private evaluation set from "
        "your own data, keep it out of every prompt and log, and treat public "
        "leaderboard numbers as advertising.")

    h3("Exercises")
    bul([
        "Compute TF-IDF vectors by hand for four short documents and verify "
        "that a term appearing everywhere gets weight zero.",
        "Train word2vec on any corpus of a few million words and inspect the "
        "ten nearest neighbours of five words, including one ambiguous one.",
        "Build a TF-IDF plus logistic-regression baseline and a fine-tuned "
        "encoder for the same classification task; report accuracy, training "
        "time and inference cost for both.",
        "Build a minimal RAG pipeline over 500 of your own documents, then "
        "measure Recall@10 of the retriever alone on 30 hand-written questions.",
        "Take 50 generated summaries, score them with ROUGE and with an "
        "LLM judge, and compute the correlation of each with your own manual "
        "ratings.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 43 ---
    chapter("Speech, Audio and Multimodal Models")
    p("Audio is the modality where classical signal processing and deep learning "
      "meet most directly: the front end is a hundred years of Fourier analysis, "
      "and everything after it is a neural network. Multimodal models then join "
      "audio, vision and text in a shared space, which is the mechanism behind "
      "zero-shot classification, cross-modal search, and the vision-language "
      "assistants now built on top of Chapter 24's LLMs.")

    h2("From waveform to features")
    eq(["Sample rate     16 kHz for speech, 44.1/48 kHz for music",
        "Frame           25 ms window, 10 ms hop  ->  100 frames per second",
        "STFT            X(f, t) = FFT( window * frame_t )",
        "Power spectrum  |X(f,t)|^2",
        "Mel filterbank  80 triangular filters spaced by mel(f) = 2595 log10(1 + f/700)",
        "Log-mel         log( mel_energies + eps )      <- the modern default",
        "MFCC            DCT( log-mel ), keep 13 coefficients   <- classical"],
       "A 1-second clip at 16 kHz is 16,000 numbers; its log-mel spectrogram is "
       "100 x 80 = 8,000 - and a far easier learning problem, because the "
       "network no longer has to discover the Fourier transform.")
    p("The mel scale exists because human pitch perception is roughly "
      "logarithmic: the difference between 200 and 300 Hz is obvious, between "
      "5,000 and 5,100 Hz inaudible. MFCCs additionally decorrelate the "
      "filterbank outputs with a DCT, which mattered when models were Gaussian "
      "mixtures and matters little for convolutional or Transformer front ends "
      "- **use log-mel for neural models, MFCC only for classical pipelines or "
      "very tight compute budgets**.")
    tbl(["Augmentation", "What it simulates", "Note"],
        [["Additive noise at a target SNR", "Real environments",
          "Use a noise corpus, not white noise"],
         ["Room impulse response convolution", "Reverberation",
          "The single most valuable augmentation for far-field audio"],
         ["Speed / tempo perturbation (0.9x, 1.1x)", "Speaker rate variation",
          "Cheap and reliably helpful for ASR"],
         ["SpecAugment: time and frequency masking", "Occlusion in the "
          "spectrogram", "Applied to the features, not the audio; near-free "
          "and very effective"],
         ["Gain, clipping, codec round-trip", "Device and transport",
          "Match the codecs your product actually uses"]],
        widths=[30, 30, 40], bold_first=True)

    h2("Recognition: CTC, attention and transducers")
    p("Speech recognition has a structural problem: the input has 100 frames per "
      "second, the output has perhaps 3 characters per second, and no alignment "
      "between them is given. The three solutions define the field.")
    eq(["CTC: add a blank symbol, sum over all alignments that collapse",
        "     to the target after removing blanks and repeats.",
        "  p(y | x) = SUM over valid alignments a of PROD_t p(a_t | x)",
        "  computed by the same forward algorithm as an HMM (Chapter 37)",
        "  Assumption: outputs are conditionally independent given x."],
       "For target 'CAT' over 5 frames, valid alignments include C-A-T-_-_, "
       "CC-A-T-_, C-_-A-T-T and dozens more; CTC sums their probabilities with "
       "dynamic programming instead of enumerating them.")
    tbl(["Approach", "Streaming", "Strength", "Weakness"],
        [["CTC", "Yes, naturally", "Simple, fast, monotonic by construction",
          "No output-to-output dependency; needs an external language model"],
         ["Attention encoder-decoder", "No (needs the full utterance)",
          "Best accuracy offline; implicit language model",
          "Can hallucinate or loop; not monotonic"],
         ["RNN-Transducer (RNN-T)", "Yes", "Streaming plus an internal "
          "prediction network - the standard for on-device assistants",
          "More complex loss, heavier training"],
         ["Whisper-style encoder-decoder", "No (30 s windows)",
          "Multilingual, robust, trained weakly-supervised at scale",
          "Latency and hallucination on silence"]],
        widths=[22, 14, 34, 30], bold_first=True)
    box("math", "Word error rate, computed",
        "WER = (substitutions + insertions + deletions) / words in the "
        "reference, computed by Levenshtein alignment. Reference: 'the quick "
        "brown fox jumps' (5 words). Hypothesis: 'the quick brown box jump "
        "over' - one substitution (fox -> box), one substitution (jumps -> "
        "jump), one insertion (over). WER = 3/5 = **0.60**, or 60%. Note that "
        "WER can exceed 100% because of insertions, and that it weights a "
        "function word the same as the one content word your product actually "
        "needed - which is why keyword-spotting products report **false accepts "
        "per hour** and **false rejects at a fixed threshold** instead.")
    p("Decoding matters as much as the acoustic model. Greedy CTC decoding is "
      "the floor; beam search with an n-gram or neural language model typically "
      "removes 15-30% of the remaining errors on domain text, because the "
      "acoustic model has no idea that your product's proper nouns exist. "
      "Shallow fusion - adding lambda times the language-model log-probability "
      "to the beam score - is the standard mechanism, and a per-user contextual "
      "biasing list is how contact names get recognized.")

    h2("Speaking, separating and self-supervising")
    bul([
        "**Text to speech** is now two stages: an acoustic model (Tacotron, "
        "FastSpeech) turning text into a mel spectrogram, and a neural vocoder "
        "(HiFi-GAN, WaveRNN) turning that into a waveform. Non-autoregressive "
        "acoustic models with explicit duration prediction are the deployment "
        "default because they are fast and cannot loop.",
        "**Neural audio codecs** (SoundStream, EnCodec) compress audio to "
        "discrete tokens, which lets a language model generate speech and music "
        "with exactly the machinery of Chapter 24. This is the architecture "
        "behind current speech-to-speech systems.",
        "**Speaker tasks**: an embedding network (x-vector, ECAPA) trained with "
        "a margin softmax gives a vector per utterance; verification is a "
        "cosine threshold, and diarization is clustering those embeddings over "
        "time.",
        "**Self-supervised pretraining** (wav2vec 2.0, HuBERT, WavLM) is the "
        "reason low-resource ASR became feasible: pretrain on tens of thousands "
        "of unlabelled hours, fine-tune on ten labelled hours, and beat a "
        "system trained on a thousand labelled hours the old way.",
        "**Enhancement and separation** (speech denoising, source separation) "
        "operate on masks over the spectrogram or directly on the waveform, and "
        "are usually a preprocessing stage whose benefit must be measured "
        "end-to-end - a denoiser that improves human listening can hurt an ASR "
        "model that was trained on noisy audio.",
    ])
    box("tip", "On-device keyword spotting, the canonical tiny-ML task",
        "A wake-word model runs continuously on a battery: budgets are tens of "
        "kilobytes of weights and single-digit milliwatts. The recipe is a small "
        "depthwise-separable CNN or tiny Transformer over log-mel features, "
        "INT8 quantized (Chapter 28), pruned (Chapter 29), and cascaded - a "
        "1-kilobyte always-on stage gates a larger verifier. This is where "
        "Chapters 28 to 31 stop being theory.")

    h2("Multimodal models: one space for two modalities")
    eq(["CLIP-style contrastive objective (InfoNCE), batch of N pairs:",
        "  s_ij = cos( image_emb_i , text_emb_j ) / temperature",
        "  L = 0.5 * [ CE(rows of s, diagonal) + CE(columns of s, diagonal) ]",
        "The matched pair is the positive; the other N-1 texts (and images)",
        "in the batch are the negatives."],
       "Large batches are not an optimization detail here - they are the source "
       "of the negatives, which is why CLIP-class models are trained with "
       "batches in the tens of thousands.")
    p("Once image and text live in one space, zero-shot classification is "
      "retrieval: embed the candidate class names as sentences ('a photo of a "
      "{class}'), embed the image, take the nearest. Cross-modal search, "
      "duplicate detection and content moderation all become nearest-neighbour "
      "queries in the same index (Chapter 39's machinery, unchanged).")
    diagram([
        "  Vision-language model (LLaVA-style):",
        "",
        "   image --> [frozen vision encoder] --> patch embeddings",
        "                                              |",
        "                                    [projector: MLP or resampler]",
        "                                              |",
        "   text  --> [tokenizer] --> token embeddings + projected image tokens",
        "                                              |",
        "                                     [ pretrained LLM decoder ]",
        "                                              |",
        "                                           answer",
    ], "The projector is the only part trained in stage one; the LLM is then "
       "fine-tuned on instruction data in stage two. The image becomes, quite "
       "literally, a few hundred extra tokens in the context.")
    tbl(["Family", "Example capability", "Main failure mode"],
        [["Contrastive dual encoder", "Zero-shot classification, retrieval",
          "No compositional reasoning: 'dog left of cat' matches 'cat left of "
          "dog'"],
         ["Vision-language decoder", "Describe, answer, read charts and "
          "documents", "Object hallucination - naming objects that are not "
          "present"],
         ["Audio-language", "Speech instruction following, audio captioning",
          "Degrades under noise far faster than a dedicated ASR model"],
         ["Any-to-any", "Text, image, audio in and out",
          "Uneven quality across modalities; evaluation is largely unsolved"]],
        widths=[24, 38, 38], bold_first=True)
    box("warn", "Evaluating multimodal systems",
        "Captioning metrics (CIDEr, SPICE) and VQA accuracy reward safe, "
        "generic answers. Hallucination needs its own measurement: ask about "
        "objects that are absent (POPE-style probing) and report the false "
        "positive rate. And check the training data question - many public "
        "benchmarks appear in the pretraining corpora of the models being "
        "scored on them.")

    h3("Exercises")
    bul([
        "Compute the number of frames, and the log-mel feature-tensor shape, "
        "for a 3-second clip at 16 kHz with 25 ms windows and 10 ms hops.",
        "Implement WER with a Levenshtein alignment and reproduce the 0.60 in "
        "the worked box.",
        "Enumerate every valid CTC alignment of the target 'AB' over 4 frames "
        "and confirm the count against the dynamic-programming recursion.",
        "Fine-tune a pretrained self-supervised speech model on one hour of "
        "labelled audio and compare with a model trained from scratch on the "
        "same hour.",
        "Build a cross-modal search demo: embed 1,000 images with a CLIP-class "
        "model and retrieve them by text query. Then find a query where the "
        "compositional failure in the table above is visible.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 44 ---
    chapter("Systems and Scale: Hardware, Memory and Distributed Training")
    p("Beyond a certain size, machine learning stops being a modelling problem "
      "and becomes a systems problem: how many bytes fit, how fast they move, "
      "and how many machines can cooperate without spending all their time "
      "talking. This chapter gives the arithmetic to answer those questions "
      "before you rent the hardware.")

    h2("What a GPU actually is, for our purposes")
    tbl(["Component", "Role", "Order of magnitude (data-centre GPU)"],
        [["Tensor cores", "Matrix-multiply-accumulate in low precision",
          "Hundreds of TFLOP/s in bf16, more in fp8"],
         ["HBM (device memory)", "Where weights and activations live",
          "40-192 GB at 1.5-8 TB/s"],
         ["SRAM / shared memory", "On-chip scratchpad per streaming "
          "multiprocessor", "Tens of MB total, ~10x the bandwidth of HBM"],
         ["Interconnect (NVLink)", "GPU-to-GPU inside a node",
          "Hundreds of GB/s"],
         ["Network (InfiniBand/Ethernet)", "Node-to-node",
          "25-400 Gb/s - roughly an order of magnitude below NVLink"]],
        widths=[24, 36, 40], bold_first=True)
    eq(["Arithmetic intensity  I = FLOPs performed / bytes moved",
        "Roofline:  achievable FLOP/s = min( peak FLOP/s , I * memory bandwidth )",
        "Ridge point: I* = peak FLOP/s / bandwidth   (often 100-400 FLOP/byte)"],
       "Below the ridge point you are memory-bound and adding compute does "
       "nothing. This one inequality explains most disappointing benchmarks.")
    box("key", "Where the common operations land",
        "A large matrix multiply has intensity proportional to the shared "
        "dimension: **compute-bound**, which is why training is dominated by "
        "GEMMs and why bigger batches help. Elementwise operations (activation, "
        "normalization, dropout, residual add) read and write more bytes than "
        "they compute on: **memory-bound**, which is why kernel fusion - doing "
        "several of them in one pass over the data - is where framework "
        "compilers get their speedups. Single-token LLM decoding reads the "
        "whole weight matrix to compute one vector product: **severely "
        "memory-bound**, which is why decode throughput tracks memory bandwidth "
        "and not FLOP/s, and why quantization (Chapter 28) speeds up generation "
        "even when the arithmetic stays in higher precision.")

    h2("Training memory, accounted exactly")
    eq(["Per parameter, mixed-precision training with Adam:",
        "  bf16 weights          2 bytes",
        "  bf16 gradients        2 bytes",
        "  fp32 master weights   4 bytes",
        "  fp32 Adam m, v        8 bytes",
        "  ------------------------------",
        "  TOTAL                16 bytes per parameter",
        "",
        "Activations (per layer, per sample) ~ batch * seq * hidden * bytes",
        "  * a constant of roughly 10-20 for a Transformer block"],
       "The 16-bytes-per-parameter rule is the single most useful number in "
       "large-model engineering.")
    box("math", "Can I fine-tune a 7-billion-parameter model on one 80 GB GPU?",
        "States: 7e9 x 16 bytes = **112 GB**. That exceeds 80 GB before a "
        "single activation is stored, so full fine-tuning does not fit. The "
        "options, in increasing order of intrusiveness: shard the optimizer "
        "states across GPUs (ZeRO-1 across 4 GPUs brings it to 7e9 x (4 + 12/4) "
        "= 49 GB each); offload optimizer states to CPU; use 8-bit Adam "
        "(saves 6 bytes per parameter, giving 70 GB); or use LoRA (Chapter 24) "
        "where the base weights are frozen at 2 bytes and only ~0.1% of "
        "parameters have optimizer state - **7e9 x 2 + tiny = about 15 GB**, "
        "which fits comfortably and is why LoRA became the default. Inference "
        "alone needs 14 GB in bf16, or 7 GB in INT8, or 3.5 GB in INT4.")
    p("Activations are the other half and the one people forget. "
      "**Activation checkpointing** (gradient checkpointing) stores only the "
      "inputs of each block and recomputes the interior during the backward "
      "pass: memory falls from O(L) to about O(sqrt(L)) segments, at a cost of "
      "roughly 30% extra compute. On any model that nearly fits, it is the "
      "first lever to pull.")

    h2("Precision")
    tbl(["Format", "Bits (E/M)", "Property", "Use"],
        [["fp32", "8/23", "The reference", "Master weights, reductions, loss"],
         ["fp16", "5/10", "Narrow range; overflows",
          "Needs dynamic loss scaling; legacy hardware"],
         ["bf16", "8/7", "fp32's range, less mantissa",
          "The training default today - no loss scaling needed"],
         ["fp8 (E4M3/E5M2)", "4/3 and 5/2", "Per-tensor scaling required",
          "Forward and backward GEMMs on recent hardware"],
         ["INT8 / INT4", "integer", "Post-training or QAT (Chapter 28)",
          "Inference, and increasingly KV caches"]],
        widths=[16, 14, 34, 36], bold_first=True)
    p("The rule that keeps mixed precision stable: **compute in low precision, "
      "accumulate and update in high precision.** Matrix multiplies run in "
      "bf16 or fp8; their accumulators are fp32; the master weights and the "
      "optimizer moments stay fp32; loss and softmax reductions stay fp32. "
      "Violating the last point is the usual cause of a training run that "
      "diverges only at large batch sizes.")

    h2("The four axes of parallelism")
    tbl(["Axis", "What is split", "Communication", "When to use"],
        [["Data parallel", "The batch; every GPU holds all weights",
          "All-reduce of gradients once per step",
          "Always, first, until the model stops fitting"],
         ["ZeRO / FSDP", "Optimizer states, then gradients, then parameters",
          "All-gather of parameters per layer, reduce-scatter of gradients",
          "The standard way to train a model that does not fit, with minimal "
          "code change"],
         ["Tensor parallel", "Individual matrices, across GPUs",
          "All-reduce twice per Transformer block - very heavy",
          "Inside one node only, over NVLink"],
         ["Pipeline parallel", "Layers, across GPUs",
          "Point-to-point activations at stage boundaries",
          "Across nodes, when depth is large"],
         ["Sequence / context parallel", "The sequence dimension",
          "Ring exchange of keys and values",
          "Very long contexts, where activations dominate"],
         ["Expert parallel (MoE)", "Experts across devices",
          "All-to-all of tokens", "Sparse models with many experts"]],
        widths=[18, 26, 30, 26], bold_first=True)
    eq(["Ring all-reduce cost for S bytes over N workers:",
        "  time  ~  2 (N - 1)/N * S / bandwidth      ->  ~ 2S/BW for large N",
        "Pipeline bubble fraction with P stages and M microbatches:",
        "  bubble = (P - 1) / (M + P - 1)     ->  keep M >> P"],
       "With 4 pipeline stages and 8 microbatches, 27% of the time is bubble; "
       "with 64 microbatches it is 4.5%.")
    p("**3D parallelism** composes them: tensor-parallel within a node, "
      "pipeline-parallel across a small group of nodes, data-parallel across "
      "the rest. The ordering is not arbitrary - it puts the chattiest axis on "
      "the fastest link. A practical rule: use FSDP/ZeRO-3 alone until "
      "communication becomes the bottleneck, then introduce tensor parallelism "
      "inside the node, and only then pipelining.")
    code([
        "# Data-parallel training, the modern minimal form",
        "model = FSDP(model, sharding_strategy=FULL_SHARD,",
        "             mixed_precision=MixedPrecision(param_dtype=torch.bfloat16,",
        "                                            reduce_dtype=torch.float32))",
        "for step, batch in enumerate(loader):",
        "    with torch.autocast('cuda', dtype=torch.bfloat16):",
        "        loss = model(batch).loss / accum_steps",
        "    loss.backward()                       # gradients reduce-scattered",
        "    if (step + 1) % accum_steps == 0:",
        "        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)",
        "        opt.step(); opt.zero_grad(set_to_none=True)",
    ], "Gradient accumulation is the free way to raise the effective batch size "
       "when memory is the limit; note that the loss must be divided by the "
       "number of accumulation steps, and that gradient clipping belongs after "
       "the last accumulation, not inside the loop.")

    h2("Measuring whether your run is any good")
    eq(["Model FLOPs Utilization (MFU):",
        "  MFU = ( 6 * N_params * tokens_per_second ) / ( GPUs * peak FLOP/s )"],
       "The 6ND rule from Chapter 36, turned into a hardware efficiency number.")
    box("math", "An MFU calculation",
        "A 7B model training at 12,000 tokens/second on 8 GPUs with 400 "
        "TFLOP/s peak bf16 each. Numerator: 6 x 7e9 x 12,000 = 5.04e14 FLOP/s. "
        "Denominator: 8 x 4e14 = 3.2e15. MFU = **15.8%**. That is poor - a "
        "well-tuned dense Transformer run reaches 35-55%. The checklist, in the "
        "order that usually pays: is the data loader starving the GPU (profile "
        "it); is the sequence length so short that kernels are launch-bound; is "
        "activation checkpointing on when it need not be; is tensor parallelism "
        "spanning nodes; are you in fp32 by accident.")
    tbl(["Symptom", "Likely cause", "Check"],
        [["GPU utilization spiky, 40-70%", "Input pipeline",
          "Time one epoch of the loader with the model removed"],
         ["Utilization high, MFU low", "Memory-bound kernels, small shapes",
          "Profile; fuse; raise batch or sequence length"],
         ["Scaling breaks past 8 GPUs", "Gradient all-reduce over slow network",
          "Measure interconnect bandwidth; enable bucketing and overlap"],
         ["Loss spikes then diverges at scale", "fp16 range, or a bad LR "
          "warmup", "Switch to bf16; lengthen warmup; clip gradients"],
         ["Throughput falls over hours", "Thermal throttling or a straggler "
          "rank", "Log per-rank step time; the slowest rank sets the pace"]],
        widths=[26, 34, 40], bold_first=True)

    h2("Serving: a different bottleneck")
    p("Inference for autoregressive models has two phases with opposite "
      "characteristics, and conflating them is the classic mistake.")
    tbl(["Phase", "Work", "Bound by", "Lever"],
        [["Prefill (prompt)", "One big matrix multiply over all prompt tokens",
          "Compute", "Batching helps little; chunk long prompts"],
         ["Decode (generation)", "One token at a time, reading all weights and "
          "the KV cache", "Memory bandwidth",
          "Batching helps enormously; quantization helps directly"]],
        widths=[18, 38, 20, 24], bold_first=True)
    bul([
        "**Continuous batching** admits new requests into the running batch as "
        "others finish, instead of waiting for a whole batch to complete - "
        "typically a 2-4x throughput gain at the same latency.",
        "**Paged attention** stores the KV cache in fixed-size blocks like "
        "virtual memory pages, removing the fragmentation that otherwise wastes "
        "half the cache.",
        "**Speculative decoding** drafts several tokens with a small model and "
        "verifies them in one pass of the large one; acceptance rates of 60-80% "
        "give 2-3x lower latency with **identical** output distribution.",
        "**Quantized serving** (INT8, INT4, fp8 weights, and increasingly "
        "quantized KV caches) reduces both the memory read per token and the "
        "cache footprint, so it raises the batch size you can hold as well as "
        "the speed per token.",
    ])
    box("tip", "Sizing a serving deployment in five minutes",
        "Weights: params x bytes-per-weight. KV cache per token: "
        "2 x layers x kv_heads x head_dim x bytes. Multiply by the average "
        "sequence length and the number of concurrent requests. Add 10-20% "
        "overhead. If the total exceeds device memory, the fix is a smaller "
        "quantization, grouped-query attention (fewer kv_heads), a shorter "
        "context, or more GPUs - in that order of cost-effectiveness. Then "
        "measure tokens/second at your target p95 latency, not at maximum "
        "throughput, because those two operating points can differ by 5x.")

    h3("Exercises")
    bul([
        "Compute the training memory for a 1.3B model with Adam in mixed "
        "precision, then recompute it with 8-bit Adam and with LoRA.",
        "Measure the MFU of a training run you have access to, then remove the "
        "data loader (feed synthetic tensors) and measure again. The difference "
        "is your input pipeline's cost.",
        "Derive the pipeline bubble fraction and plot it for P = 4 and M from "
        "4 to 128.",
        "Serve a small model with and without continuous batching and compare "
        "throughput at fixed p95 latency.",
        "Take the roofline model and classify five operations in your own "
        "network as compute- or memory-bound, then verify with a profiler.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 45 ---
    chapter("Causal Inference and Experimentation")
    p("Every model in this book answers 'what is associated with what'. Almost "
      "every decision made with a model asks 'what happens if I intervene'. "
      "Those are different questions, and no amount of predictive accuracy "
      "converts one into the other. A model can predict hospital readmission "
      "perfectly and still be useless for deciding who to treat - and a feature "
      "with a large importance score can have the opposite sign as a causal "
      "effect.")

    h2("Prediction is not intervention")
    box("math", "Simpson's paradox, with the classic numbers",
        "Two treatments for kidney stones. Treatment A succeeds in 81 of 87 "
        "cases with small stones (**93%**) and 192 of 263 with large stones "
        "(**73%**). Treatment B succeeds in 234 of 270 small (**87%**) and 55 "
        "of 80 large (**69%**). A is better in both groups. Yet overall A is "
        "273/350 = **78%** and B is 289/350 = **83%** - B looks better. The "
        "reason is that doctors gave A to the hard cases: stone size is a "
        "**confounder**, causing both the treatment assignment and the outcome. "
        "Any model fitted on this data without stone size will confidently "
        "recommend the worse treatment. **No sample size fixes this**; it is "
        "not noise, it is structure.")
    eq(["Potential outcomes:   Y(1) = outcome if treated",
        "                      Y(0) = outcome if not treated",
        "Individual effect     tau_i = Y_i(1) - Y_i(0)      NEVER observed",
        "ATE   = E[ Y(1) - Y(0) ]                  average over everyone",
        "ATT   = E[ Y(1) - Y(0) | T = 1 ]          among the treated",
        "CATE  = E[ Y(1) - Y(0) | X = x ]          conditional on features"],
       "The fundamental problem of causal inference: for each unit you observe "
       "exactly one of the two potential outcomes. Causal inference is a "
       "missing-data problem.")
    p("Randomization solves it in one stroke: if treatment is assigned by a coin "
      "flip, then the treated and untreated groups differ only by chance in "
      "**every** variable, observed or not, so the difference in average "
      "outcomes estimates the ATE without bias. That is the entire justification "
      "for the A/B test, and it is why an experiment beats any observational "
      "analysis that is available.")

    h2("Running an experiment that means something")
    eq(["Sample size per arm, two-sided test at level alpha with power 1-beta:",
        "  n = 2 (z_(1-alpha/2) + z_(1-beta))^2 * sigma^2 / delta^2",
        "  For a proportion:  sigma^2 = p (1 - p)",
        "  z_0.975 = 1.960,   z_0.80 = 0.8416"])
    box("math", "How much traffic do I need?",
        "Baseline conversion 5%, and you want to detect a **relative** lift of "
        "2%, i.e. delta = 0.001 in absolute terms. sigma^2 = 0.05(0.95) = "
        "0.0475. Then n = 2(1.960 + 0.8416)^2 (0.0475) / (0.001)^2 = "
        "2(7.849)(0.0475)/1e-6 = **746,000 users per arm**. At 50,000 users a "
        "day that is a **30-day** experiment. Detecting a 10% relative lift "
        "instead needs 1/25 of that - about 30,000 per arm, or under two days. "
        "**Power scales with the square of the effect you are chasing**, which "
        "is why 'we will just run it and see' is not a plan and why small "
        "effects are usually undetectable at any realistic traffic.")
    tbl(["Threat to validity", "What goes wrong", "Treatment"],
        [["Peeking", "Checking daily and stopping at significance inflates "
          "the false-positive rate far above 5%",
          "Fix the horizon in advance, or use a sequential test (always-valid "
          "p-values, group-sequential boundaries)"],
         ["Multiple metrics", "Twenty metrics give one 'significant' result by "
          "chance", "Declare one primary metric; treat the rest as guardrails "
          "with corrected thresholds"],
         ["Interference (SUTVA violation)", "One user's treatment affects "
          "another - marketplaces, social graphs, shared inventory",
          "Cluster randomization, switchback designs, or budget-split designs"],
         ["Novelty and primacy effects", "Behaviour changes because the thing "
          "is new, then reverts",
          "Run long enough; analyse new versus returning users separately"],
         ["Sample-ratio mismatch", "Arms receive unequal traffic, revealing a "
          "broken assignment", "Chi-square test on the split every day; an SRM "
          "invalidates the experiment, full stop"],
         ["Under-powered launch decisions", "A non-significant result is read "
          "as 'no effect'", "Report the confidence interval; 'we could not "
          "detect an effect smaller than 3%' is the honest statement"]],
        widths=[22, 40, 38], bold_first=True)
    box("tip", "CUPED: the free variance reduction",
        "If you have a pre-experiment covariate X correlated with the outcome Y "
        "(typically the same metric measured before the experiment), analyse "
        "Y_adj = Y - theta (X - E[X]) with theta = Cov(X,Y)/Var(X). The "
        "adjusted metric has variance reduced by a factor (1 - rho^2). With a "
        "correlation of 0.7, that is half the variance and therefore **half the "
        "required sample size** - the cheapest experimental improvement "
        "available, and it is unbiased because X predates the assignment.")

    h2("When you cannot randomize")
    p("Sometimes the intervention is already deployed, unethical to withhold, or "
      "outside your control. Then you must adjust for confounding explicitly, "
      "and the first step is to draw the graph.")
    diagram([
        "   CONFOUNDER (adjust for it)      COLLIDER (do NOT adjust for it)",
        "                                                                  ",
        "          Z                                    T --> C <-- Y      ",
        "        /   \\                                                     ",
        "       v     v                       Conditioning on C creates a  ",
        "      T ----> Y                      spurious T-Y association     ",
        "                                     where none existed.          ",
        "                                                                  ",
        "   MEDIATOR (adjust only if you want the direct effect)           ",
        "      T --> M --> Y                                               ",
    ], "The backdoor criterion: to estimate the effect of T on Y, block every "
       "path that enters T through an arrow into it, and never open a path by "
       "conditioning on a collider or its descendants.")
    box("warn", "'Control for everything' is wrong, not just wasteful",
        "Adding every available variable to a regression is standard practice "
        "and can move an estimate away from the truth. Conditioning on a "
        "collider manufactures correlation; conditioning on a mediator removes "
        "the very effect you were measuring; conditioning on a post-treatment "
        "variable does both. **Which variables to adjust for is a question "
        "about the world, answerable only with domain knowledge - the data "
        "cannot tell you.**")
    tbl(["Design", "Assumption it needs", "Typical use"],
        [["Propensity matching / weighting",
          "No unmeasured confounders; overlap between groups",
          "Observational program evaluation"],
         ["Doubly robust (AIPW)", "Either the outcome model or the propensity "
          "model is correct", "The default estimator when you must adjust"],
         ["Difference-in-differences", "Parallel trends absent treatment",
          "A change rolled out to some regions or at some date"],
         ["Instrumental variables", "The instrument affects treatment only, "
          "not the outcome directly", "Encouragement designs, imperfect "
          "compliance, natural experiments"],
         ["Regression discontinuity", "Units just above and below a cutoff are "
          "comparable", "Eligibility thresholds, score cutoffs"],
         ["Synthetic control", "A weighted combination of untreated units "
          "tracks the treated one before treatment",
          "One treated region or market"]],
        widths=[26, 40, 34], bold_first=True)

    h2("Heterogeneous effects and uplift modelling")
    p("The average effect answers 'should we launch this'. The conditional "
      "effect answers 'for whom' - which is the question that makes targeting "
      "profitable. Note the four-way segmentation that makes uplift different "
      "from response modelling:")
    tbl(["Segment", "Treated outcome", "Untreated outcome", "Action"],
        [["Persuadables", "Converts", "Does not", "**Target these**"],
         ["Sure things", "Converts", "Converts", "Waste of budget"],
         ["Lost causes", "Does not", "Does not", "Waste of budget"],
         ["Sleeping dogs", "Does not", "Converts",
          "**Actively harmful to target**"]],
        widths=[24, 24, 24, 28], bold_first=True)
    p("A response model that predicts P(convert | treated) targets sure things, "
      "because they are the easiest to predict. Uplift models estimate the "
      "difference instead:")
    bul([
        "**S-learner**: one model with treatment as a feature; simple, but the "
        "model may ignore a weak treatment feature entirely.",
        "**T-learner**: separate models for treated and control; unbiased in "
        "structure, but the difference of two noisy models is noisier still.",
        "**X-learner**: impute each unit's counterfactual with the opposite "
        "model, then regress; much better with unbalanced arms.",
        "**Causal forests / DR-learner**: honest sample splitting with doubly "
        "robust scores; the current default for credible CATE estimates.",
    ])
    p("Evaluate with the **Qini or uplift curve**: sort by predicted uplift, and "
      "plot the cumulative incremental conversions against the fraction "
      "targeted. The area over the random line is the value of the targeting. "
      "Ordinary AUC is meaningless here - you can never observe the "
      "individual-level label being predicted.")
    box("key", "The rule that saves the most money",
        "Never evaluate a targeting policy on the same experiment that trained "
        "it, and never evaluate it on outcome prediction accuracy. Hold out a "
        "randomized slice permanently, and measure the incremental effect of "
        "the policy in that slice. Almost every 'our model increased revenue "
        "40%' claim that later evaporated was an uplift claim measured with a "
        "response metric.")

    h3("Exercises")
    bul([
        "Reproduce the kidney-stone numbers and confirm both the within-group "
        "and the aggregate comparison.",
        "Compute the required sample size for your own product's baseline "
        "conversion rate and the smallest lift worth shipping.",
        "Simulate peeking: generate 1,000 A/A experiments, test daily for 14 "
        "days, and count how often you would have declared significance.",
        "Apply CUPED to a past experiment using the pre-period metric and "
        "report the variance reduction achieved.",
        "Take an observational dataset, draw the DAG, and estimate an effect "
        "twice: once adjusting for a collider and once not. Report both.",
    ], ordered=True)

    # --------------------------------------------------------------- Ch 46 ---
    chapter("Privacy, Security and Governance")
    p("A model is a lossy, queryable copy of its training data, deployed at an "
      "endpoint anyone can probe. That framing makes the risks concrete: data "
      "can leak out of the weights, behaviour can be corrupted by data going "
      "in, and the interface itself is an attack surface. This chapter covers "
      "the mechanisms and the obligations, both of which now appear in "
      "procurement questionnaires and in law.")

    h2("The threat model")
    tbl(["Attack", "What the adversary gets", "Practical defence"],
        [["Membership inference", "Whether a specific record was in training",
          "Reduce overfitting, limit confidence output, differential privacy"],
         ["Training-data extraction", "Verbatim memorized secrets from a "
          "generative model", "Deduplicate the corpus, scan and filter "
          "secrets, DP fine-tuning, output filters"],
         ["Model inversion", "Reconstruction of typical class inputs",
          "Restrict query volume and returned detail"],
         ["Model extraction / stealing", "A functional copy from the API",
          "Rate limits, monitoring for systematic querying, watermarking"],
         ["Data poisoning / backdoor", "A trigger that flips predictions",
          "Provenance for training data, anomaly screening, hold out a trusted "
          "clean evaluation set"],
         ["Adversarial examples", "Wrong output from a tiny perturbation",
          "Adversarial training, input sanitization, ensembling (Chapter 33)"],
         ["Prompt injection", "An LLM agent follows instructions from "
          "retrieved content", "Treat all retrieved text as untrusted data; "
          "constrain tools; require confirmation for consequential actions"],
         ["Supply chain", "Malicious code in weights or a dependency",
          "Load only safetensors-style formats, never arbitrary pickles; pin "
          "and verify hashes"]],
        widths=[22, 38, 40], bold_first=True)
    box("warn", "Memorization is measurable, so measure it",
        "Large models reproduce rare training strings verbatim, and the rate "
        "rises with model size, with duplication in the corpus, and with the "
        "length of the prefix you supply. Before releasing a model trained on "
        "internal data, run the extraction test yourself: prompt it with "
        "prefixes of known-sensitive records and check what completes. "
        "Deduplication of the training corpus is the single most effective "
        "mitigation, and it improves quality at the same time.")

    h2("Differential privacy, precisely enough to use")
    eq(["A randomized mechanism M is (epsilon, delta)-differentially private if",
        "for any two datasets D, D' differing in one record, and any output S:",
        "",
        "    P[ M(D) in S ]  <=  e^epsilon * P[ M(D') in S ]  +  delta",
        "",
        "Interpretation: whatever anyone can conclude about you from the",
        "output, they could almost equally have concluded had you not",
        "participated at all."],
       "epsilon is a privacy budget: smaller is stronger, and budgets compose "
       "additively across queries.")
    code([
        "# DP-SGD: two changes to an ordinary training step",
        "for batch in loader:",
        "    per_sample_grads = compute_per_sample_gradients(model, batch)",
        "    # 1. clip each example's gradient to a fixed L2 norm C",
        "    clipped = [g * min(1.0, C / (g.norm() + 1e-6))",
        "               for g in per_sample_grads]",
        "    g_sum = sum(clipped)",
        "    # 2. add Gaussian noise calibrated to C and the noise multiplier",
        "    g_noisy = (g_sum + torch.normal(0., sigma * C, g_sum.shape)) / B",
        "    optimizer.step_with(g_noisy)",
        "# The accountant tracks epsilon from (sigma, sampling rate, steps).",
    ], "Clipping bounds any single example's influence; the noise hides it. The "
       "cost is real: per-sample gradients are memory-hungry, and accuracy "
       "falls - typically a few points at epsilon around 8, more on small or "
       "imbalanced datasets.")
    tbl(["epsilon", "Reading", "Where it is seen"],
        [["< 1", "Strong formal guarantee", "Aggregate statistics, census-style "
          "releases"],
         ["1 - 10", "Meaningful in practice; the usual operating range",
          "DP-SGD fine-tuning, telemetry collection"],
         ["> 20", "Little formal meaning; still blocks naive memorization",
          "Reported honestly, or not reported at all"]],
        widths=[14, 46, 40], bold_first=True)
    p("Federated learning (Chapter 31) is **not** privacy on its own: raw "
      "gradients can reveal their inputs, sometimes reconstructing images "
      "exactly. It becomes a privacy mechanism when combined with secure "
      "aggregation (the server sees only the sum of many updates) and "
      "user-level DP noise. State which of the three you have; they are "
      "routinely conflated in marketing material.")

    h2("Handling personal data")
    bul([
        "**Minimize**: the strongest protection for a field is not collecting "
        "it. Ask what decision each feature supports before it enters the "
        "warehouse.",
        "**Separate identity from behaviour**: pseudonymize with keyed hashes, "
        "hold the key separately, and rotate it. Note that pseudonymized data "
        "is still personal data under most regimes.",
        "**Do not rely on k-anonymity alone**: high-dimensional behavioural "
        "data re-identifies easily - a handful of timestamped locations or "
        "ratings is usually unique to one person.",
        "**Retention and deletion**: define a retention period per dataset and "
        "enforce it automatically. A deletion request must reach backups, "
        "feature stores, logs and derived datasets, not just the primary table.",
        "**Unlearning**: removing a record's influence from trained weights is "
        "genuinely hard. The practical answers are retraining on a schedule, "
        "sharded training so only one shard must be retrained, or DP training "
        "that bounds any single record's influence in advance. Decide which "
        "before you promise deletion.",
        "**Cross-border and vendor flows**: sending data to an external API is "
        "a transfer; check what the provider retains and for how long, and "
        "record that decision where an auditor can find it.",
    ])

    h2("Securing a deployed model, and an agent")
    tbl(["Layer", "Control"],
        [["Input", "Schema and range validation, size limits, content-type "
          "checks; reject rather than coerce"],
         ["Rate", "Per-key quotas and anomaly detection on query patterns - "
          "the defence against extraction and inversion"],
         ["Output", "Confidence rounding, refusal of out-of-scope requests, "
          "PII and secret filters on generated text"],
         ["Tools (agents)", "Least privilege per tool, allowlists for domains "
          "and commands, no ambient credentials, human confirmation for "
          "irreversible actions"],
         ["Context (agents)", "Every retrieved document, web page, email and "
          "tool result is **untrusted data**, never instructions; keep system "
          "policy outside the retrievable corpus"],
         ["Artefacts", "Signed model files, hash-pinned dependencies, no "
          "arbitrary code execution on load, provenance recorded in the "
          "registry"],
         ["Monitoring", "Log inputs and outputs (with privacy controls), alert "
          "on distribution shifts and on refusal-rate changes, and keep an "
          "incident runbook with a rollback path"]],
        widths=[18, 82], bold_first=True)
    box("key", "The agent security rule, stated once",
        "An LLM cannot reliably distinguish instructions written by your user "
        "from instructions embedded in content it reads. Therefore security "
        "cannot live in the prompt. It must live in the **capabilities**: what "
        "the tools can do, what credentials they carry, and which actions "
        "require a human. Design as if the model will at some point follow a "
        "malicious instruction, because eventually it will.")

    h2("Governance: the paperwork that is actually load-bearing")
    tbl(["Artefact", "Contents", "Why it pays for itself"],
        [["Datasheet for the dataset", "Provenance, consent basis, collection "
          "period, known gaps, licence", "Answers the question that stalls "
          "every deployment review"],
         ["Model card", "Intended use, out-of-scope use, training data "
          "summary, metrics by slice, limitations",
          "Forces the slice evaluation that finds the failure before users do"],
         ["Evaluation record", "Frozen test set, per-slice results, "
          "calibration, robustness and safety probes", "The evidence when a "
          "regression is disputed"],
         ["Risk classification", "The decision the model influences, who is "
          "affected, reversibility, human oversight",
          "Determines how much of the rest is required at all"],
         ["Change log and registry", "Versions, data snapshots, approvals, "
          "rollbacks", "Makes incident response minutes rather than days"]],
        widths=[22, 44, 34], bold_first=True)
    p("Regimes differ in detail and change often, but the shape is now stable "
      "across them: obligations scale with the **risk of the use case**, not "
      "with the size of the model. Systems that affect employment, credit, "
      "education, essential services, health or law enforcement attract "
      "documentation, human-oversight, accuracy and record-keeping duties; "
      "content generation attracts disclosure duties; most internal tooling "
      "attracts little beyond ordinary data protection. Classify your use case "
      "early - it is cheap then, and expensive after the architecture is "
      "fixed.")
    checklist("Before a model touches real users", [
        "The legal basis for every training data source is written down.",
        "Personal fields are minimized, pseudonymized, and on a retention "
        "clock.",
        "A memorization or membership probe has been run for generative or "
        "small-data models.",
        "Slice metrics exist for the groups the system can plausibly harm.",
        "Input validation, rate limits and output filters are deployed, not "
        "planned.",
        "Agent tools follow least privilege, with confirmation on irreversible "
        "actions.",
        "The model card, datasheet and evaluation record exist and are "
        "current.",
        "A rollback path and an incident owner are named and have been "
        "rehearsed.",
    ])

    h3("Exercises")
    bul([
        "Run a membership-inference check on a model you trained: compare the "
        "loss distribution on training rows against held-out rows. A visible "
        "gap is the attack surface.",
        "Fine-tune a small model with and without DP-SGD at epsilon around 8 "
        "and report the accuracy cost.",
        "Take a retrieval-augmented assistant and write three prompt-injection "
        "payloads into the corpus it reads. Then fix it at the capability "
        "layer rather than in the prompt.",
        "Write the model card and datasheet for a model you have already "
        "shipped. Note every question you cannot answer - each one is a gap.",
        "Trace a deletion request end to end through your systems and list "
        "every store that would retain the record.",
    ], ordered=True)

    ch_project()


# =============================================================================
#                              APPENDICES
# =============================================================================
_APPX = {"n": 0}

def appendix(title):
    _APPX["n"] += 1
    letter = chr(ord("A") + _APPX["n"] - 1)
    _counters["sec"] = 0
    _counters["chap"] = -1          # suppress numeric section prefixes
    txt = "Appendix %s.  %s" % (letter, title)
    t = Table([[Paragraph(mk(txt), S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    t._toc = (1, txt)
    add(PageBreak(), t, Spacer(1, 7))


def ah2(title):
    p_ = Paragraph(mk(title), S_H2)
    p_._toc = (2, title)
    add(p_, HRFlowable(width="100%", thickness=0.6, color=C_LIGHT,
                       spaceBefore=0, spaceAfter=4))


def appendices():
    part("Appendices",
         numbered=False,
         blurb="A compact mathematical reference, a glossary of every term used in "
         "this book, and a study roadmap with resources.")

    # ------------------------------------------------------------ Appendix A -
    appendix("Mathematical Reference")
    ah2("Linear algebra")
    eq(["Dot product        a . b = SUM_i a_i b_i",
        "Matrix product     (AB)_ij = SUM_k A_ik B_kj      (m,k)(k,n) -> (m,n)",
        "Transpose          (AB)^T = B^T A^T",
        "Inverse            (AB)^-1 = B^-1 A^-1",
        "Trace              tr(AB) = tr(BA),   tr(A) = SUM_i lambda_i",
        "Determinant        det(AB) = det(A)det(B),  det(A) = PROD_i lambda_i",
        "Norms              ||x||_1, ||x||_2, ||x||_inf",
        "Orthogonal Q       Q^T Q = I,  ||Qx|| = ||x||",
        "Eigen              A v = lambda v;  symmetric A = Q L Q^T",
        "SVD                A = U S V^T  (always exists)",
        "PSD                x^T A x >= 0 for all x  <=>  all eigenvalues >= 0"])
    ah2("Matrix calculus (denominator layout)")
    eq(["d(a^T x)/dx      = a",
        "d(x^T A x)/dx    = (A + A^T) x   = 2Ax if A symmetric",
        "d(||x||^2)/dx    = 2x",
        "d(||Ax - b||^2)/dx = 2 A^T (Ax - b)",
        "d(tr(AB))/dA     = B^T",
        "d(log det A)/dA  = A^-T",
        "Chain rule       dz/dx = (dz/dy)(dy/dx)"])
    ah2("Probability")
    eq(["Bayes          P(H|D) = P(D|H)P(H)/P(D)",
        "Expectation    E[aX + bY] = aE[X] + bE[Y]   (always)",
        "Variance       Var[X] = E[X^2] - E[X]^2",
        "               Var[aX] = a^2 Var[X]",
        "               Var[X+Y] = Var[X]+Var[Y] if independent",
        "Covariance     Cov[X,Y] = E[XY] - E[X]E[Y]",
        "Gaussian       p(x) = (1/sqrt(2 pi s^2)) exp( -(x-mu)^2 / (2 s^2) )",
        "CLT            mean of n iid samples -> N(mu, sigma^2/n)",
        "Jensen         f convex => f(E[X]) <= E[f(X)]"])
    ah2("Information theory")
    eq(["H(p)      = -SUM p log p",
        "H(p,q)    = -SUM p log q          (cross-entropy)",
        "KL(p||q)  = SUM p log(p/q) >= 0   (0 iff p = q)",
        "H(p,q)    = H(p) + KL(p||q)",
        "I(X;Y)    = H(X) - H(X|Y) = KL( p(x,y) || p(x)p(y) )"])
    ah2("Key derivatives used in this book")
    eq(["sigmoid s(z)          s'(z) = s(z)(1 - s(z))",
        "tanh(z)               1 - tanh^2(z)",
        "ReLU(z)               1 if z > 0 else 0",
        "GELU(z)               Phi(z) + z phi(z)",
        "softmax_i wrt z_j     p_i(delta_ij - p_j)",
        "CE(softmax) wrt z     p - y            <- the identity to remember",
        "BCE(sigmoid) wrt z    p - y            <- the same identity",
        "MSE wrt y_hat         2(y_hat - y)/n"])
    ah2("Complexity cheat-sheet")
    tbl(["Operation", "Cost"],
        [["Dense layer forward, batch n", "O(n * d_in * d_out)"],
         ["Backward pass", "About 2x the forward cost"],
         ["Conv layer", "O(K^2 * C_in * C_out * H * W)"],
         ["Self-attention", "O(n^2 d) time, O(n^2) memory naively"],
         ["Normal equations", "O(n d^2 + d^3)"],
         ["SVD of (n,d)", "O(n d min(n,d))"],
         ["k-NN query, brute force", "O(n d)"],
         ["Decision tree training", "O(n d log n)"],
         ["k-means iteration", "O(n k d)"]],
        widths=[46, 54], bold_first=True)
    ah2("Useful numbers")
    tbl(["Quantity", "Value"],
        [["FP32 / FP16 / INT8 bytes per value", "4 / 2 / 1"],
         ["Adam training memory", "~16 bytes per parameter (fp32) before "
          "activations"],
         ["Cross-entropy at random init, K classes", "log K (2.30 for K=10, "
          "6.91 for K=1000)"],
         ["Bootstrap sample coverage", "63.2% of rows appear at least once"],
         ["Chinchilla-optimal tokens per parameter", "~20"],
         ["KV cache bytes", "2 * layers * kv_heads * head_dim * seq * batch * "
          "bytes_per_value"],
         ["Rule of thumb, samples needed", "10-100x the number of free "
          "parameters for classical models; far less with pretraining"]],
        widths=[42, 58], bold_first=True)

    # ------------------------------------------------------------ Appendix B -
    appendix("Glossary")
    gloss = [
        ("Activation function", "Non-linearity applied to a neuron's weighted sum; "
         "without it, depth adds nothing."),
        ("AdamW", "Adam with decoupled weight decay; the default optimiser for "
         "Transformers."),
        ("Attention", "A mechanism that computes a weighted average of values, "
         "where the weights come from query-key similarity."),
        ("Autoregressive", "Generating a sequence one element at a time, each "
         "conditioned on all previous ones."),
        ("Backpropagation", "Reverse-mode automatic differentiation applied to a "
         "neural network."),
        ("Bagging", "Training models on bootstrap resamples and averaging them to "
         "cut variance."),
        ("Batch normalisation", "Normalising activations using statistics of the "
         "current mini-batch, with learned scale and shift."),
        ("Bias (statistical)", "Systematic error from a model class too simple to "
         "represent the truth."),
        ("Bias (parameter)", "The additive constant term in a linear or "
         "convolutional layer."),
        ("Boosting", "Sequentially adding weak models, each correcting the "
         "current ensemble's errors."),
        ("Calibration", "Agreement between predicted probabilities and observed "
         "frequencies."),
        ("Capacity", "How complex a function a model class can represent."),
        ("Catastrophic forgetting", "Loss of previously learned ability when "
         "fine-tuning on new data."),
        ("Checkpointing (gradient)", "Recomputing activations in the backward "
         "pass to save memory."),
        ("Contrastive learning", "Training representations by pulling matching "
         "pairs together and pushing others apart."),
        ("Convolution", "A weight-sharing local operation that slides a kernel "
         "over the input."),
        ("Cross-entropy", "The standard classification loss; equals KL divergence "
         "from the label distribution up to a constant."),
        ("Cross-validation", "Repeated train/validate splits used to estimate "
         "generalisation."),
        ("Diffusion model", "A generative model that learns to reverse a gradual "
         "noising process."),
        ("Distillation", "Training a small student to imitate a large teacher's "
         "outputs."),
        ("Distribution shift", "The deployment data distribution differing from "
         "the training one."),
        ("Dropout", "Randomly zeroing units during training as a regulariser."),
        ("Early stopping", "Halting training when validation performance stops "
         "improving."),
        ("Embedding", "A learned dense vector representing a discrete item."),
        ("Ensemble", "A combination of several models' predictions."),
        ("Epoch", "One full pass over the training set."),
        ("Feature", "One measured input variable."),
        ("Fine-tuning", "Continuing training of a pretrained model on a target "
         "task."),
        ("FLOPs", "Floating-point operations; a compute measure that is a poor "
         "proxy for latency."),
        ("Generalisation", "Performance on data not used for training."),
        ("Gradient descent", "Iteratively stepping parameters against the "
         "gradient of the loss."),
        ("Gradient clipping", "Rescaling gradients whose norm exceeds a threshold."),
        ("Hyperparameter", "A setting chosen before training rather than learned "
         "from the training loss."),
        ("Inductive bias", "The assumptions a model makes that let it prefer some "
         "solutions over others."),
        ("Inference", "Running a trained model to obtain predictions."),
        ("KV cache", "Stored keys and values from previous tokens, so generation "
         "does not recompute them."),
        ("Label smoothing", "Softening one-hot targets to reduce overconfidence."),
        ("Latent variable", "An unobserved variable inferred by the model."),
        ("Layer normalisation", "Normalising across features within one sample; "
         "batch-independent."),
        ("Learning rate", "The step size in gradient descent; the most important "
         "hyperparameter."),
        ("Logit", "An unbounded score before sigmoid or softmax."),
        ("LoRA", "Low-rank adaptation: training small low-rank updates to frozen "
         "weights."),
        ("Loss function", "The scalar measure of error that training minimises."),
        ("Mixed precision", "Training with 16-bit compute and 32-bit master "
         "weights."),
        ("MLP", "Multilayer perceptron; a stack of fully connected layers."),
        ("Momentum", "Accumulating a velocity of past gradients to smooth and "
         "accelerate descent."),
        ("Non-parametric", "A model whose complexity grows with the data, e.g. "
         "k-NN."),
        ("Overfitting", "Fitting noise in the training data, so test error rises."),
        ("Parameter", "A number learned from data during training."),
        ("Perplexity", "exp(cross-entropy); the standard language-model metric."),
        ("Pruning", "Removing weights, channels or blocks from a trained network."),
        ("Quantization", "Representing weights and activations with fewer bits."),
        ("RAG", "Retrieval-augmented generation: inserting retrieved documents "
         "into a model's prompt."),
        ("Receptive field", "The region of input that influences one output unit."),
        ("Regularisation", "Any change intended to reduce test error rather than "
         "training error."),
        ("Reinforcement learning", "Learning a policy from rewards received while "
         "acting."),
        ("Residual connection", "y = x + F(x); preserves gradient flow through "
         "depth."),
        ("RoPE", "Rotary positional embedding; encodes position by rotating "
         "queries and keys."),
        ("Self-supervised learning", "Supervised learning on labels derived "
         "automatically from the data itself."),
        ("Semi-supervised learning", "Using labelled and unlabelled data "
         "together."),
        ("SGD", "Stochastic gradient descent: updating from mini-batch gradients."),
        ("Softmax", "Turning a vector of logits into a probability distribution."),
        ("Sparsity", "The fraction of parameters or activations that are zero."),
        ("Straight-through estimator", "Treating a non-differentiable forward op "
         "as the identity in the backward pass."),
        ("Supervised learning", "Learning a mapping from labelled input-output "
         "pairs."),
        ("Tensor", "An n-dimensional array, with autograd support in deep-learning "
         "frameworks."),
        ("Tokenisation", "Splitting text into subword units a model can embed."),
        ("Transfer learning", "Reusing knowledge from one task to improve another."),
        ("Transformer", "An architecture built from self-attention and "
         "position-wise feedforward blocks with residual connections."),
        ("Underfitting", "The model is too simple; both training and test error "
         "are high."),
        ("Unsupervised learning", "Finding structure in data with no labels."),
        ("Validation set", "Held-out data used to choose hyperparameters and stop "
         "training."),
        ("Vanishing gradient", "Gradient magnitudes shrinking exponentially with "
         "depth, stalling early layers."),
        ("Variance (statistical)", "Sensitivity of the fitted model to which "
         "training sample was drawn."),
        ("Weight decay", "Shrinking weights towards zero each step; L2 "
         "regularisation, decoupled in AdamW."),
        ("Zero-shot", "Performing a task with no task-specific training examples."),
        ("A/B test", "A randomised controlled experiment on live traffic; the "
         "only design that estimates a causal effect without assumptions."),
        ("Arithmetic intensity", "FLOPs performed per byte moved; decides "
         "whether an operation is compute-bound or memory-bound."),
        ("ATE / CATE", "Average treatment effect over everyone, and the "
         "conditional version for a given feature vector."),
        ("Backdoor criterion", "The graphical rule for choosing which "
         "variables to adjust for when estimating a causal effect."),
        ("BM25", "A length-normalised, frequency-saturating sparse retrieval "
         "score; still the strongest non-neural retriever."),
        ("BPR", "Bayesian Personalised Ranking; a pairwise loss that trains a "
         "recommender to order a seen item above a sampled unseen one."),
        ("Collider", "A variable caused by two others; conditioning on it "
         "creates a spurious association between them."),
        ("CTC", "Connectionist Temporal Classification; a loss that sums over "
         "all alignments of an output sequence to a longer input."),
        ("CUPED", "Variance reduction in experiments using a pre-experiment "
         "covariate; typically halves the required sample size."),
        ("Differential privacy", "A formal guarantee, parameterised by "
         "epsilon, that one record's presence barely changes the output "
         "distribution."),
        ("Double descent", "The modern test-error curve: rising to a peak at "
         "the interpolation threshold, then falling again as capacity grows."),
        ("DP-SGD", "Training with per-example gradient clipping plus "
         "calibrated Gaussian noise, giving a differential-privacy bound."),
        ("ELBO", "Evidence lower bound; the objective maximised by variational "
         "inference and by variational autoencoders."),
        ("EM algorithm", "Alternating expected-assignment and "
         "parameter-update steps for models with latent variables."),
        ("FSDP / ZeRO", "Sharding optimiser states, gradients and parameters "
         "across data-parallel workers so a model too large for one device "
         "fits."),
        ("Gaussian process", "A prior over functions defined by a kernel; "
         "gives exact posterior uncertainty and drives Bayesian optimisation."),
        ("Hidden Markov model", "A latent discrete state sequence with "
         "observations; solved by forward-backward and Viterbi."),
        ("IoU", "Intersection over union of two regions; the matching "
         "criterion behind detection and segmentation metrics."),
        ("Log-mel spectrogram", "Log energies in mel-spaced frequency bands; "
         "the standard input representation for speech models."),
        ("mAP", "Mean average precision: area under the precision-recall "
         "curve, averaged over classes and (in COCO style) IoU thresholds."),
        ("MASE", "Mean absolute scaled error; forecast error divided by the "
         "naive baseline's error, so values below 1 mean you beat it."),
        ("Matrix factorisation", "Representing a user-item matrix as the "
         "product of low-rank user and item factors plus bias terms."),
        ("MFU", "Model FLOPs utilisation: achieved model FLOPs divided by the "
         "hardware's peak; 35-55% is a healthy dense training run."),
        ("NDCG", "Normalised discounted cumulative gain; the standard ranking "
         "metric, discounting relevance logarithmically by position."),
        ("Pipeline bubble", "Idle time in pipeline parallelism, equal to "
         "(P-1)/(M+P-1) for P stages and M microbatches."),
        ("Position bias", "The tendency of users to click higher-ranked items "
         "regardless of relevance; must be corrected before training on clicks."),
        ("Potential outcomes", "The pair of results a unit would have under "
         "treatment and under control; only one is ever observed."),
        ("Prompt injection", "Instructions hidden in retrieved content that an "
         "LLM agent follows; mitigated at the capability layer, not the prompt."),
        ("Propensity score", "The probability of receiving treatment given "
         "covariates; used for matching, weighting and off-policy estimates."),
        ("Rademacher complexity", "The expected ability of a class to fit "
         "random signs on your sample; a data-dependent complexity measure."),
        ("RAG", "Retrieval-augmented generation: retrieve passages, then "
         "condition the generator on them and cite them."),
        ("Roofline", "The bound min(peak FLOP/s, intensity x bandwidth) that "
         "explains most disappointing hardware benchmarks."),
        ("Scaling law", "An empirical power law relating loss to parameters, "
         "data and compute; the basis of Chinchilla-optimal training."),
        ("Speculative decoding", "Drafting tokens with a small model and "
         "verifying them with the large one, preserving the output "
         "distribution."),
        ("STL decomposition", "Splitting a series into seasonal, trend and "
         "remainder components using local regression."),
        ("Stationarity", "Constant mean, variance and autocovariance over "
         "time; required by classical time-series models, obtained by "
         "differencing."),
        ("Two-tower model", "Separate user and item encoders scored by dot "
         "product, allowing item embeddings to be indexed for fast retrieval."),
        ("Uplift model", "A model of the treatment effect rather than the "
         "outcome; targets persuadables and avoids sleeping dogs."),
        ("VC dimension", "The largest number of points a hypothesis class can "
         "label in every possible way; controls the classical generalisation "
         "bound."),
        ("Viterbi algorithm", "Dynamic programming for the most probable "
         "hidden state sequence in an HMM."),
        ("WER", "Word error rate: substitutions plus insertions plus deletions "
         "over reference words; can exceed 100%."),
    ]
    tbl(["Term", "Definition"],
        [[a, b] for a, b in sorted(gloss, key=lambda t: t[0].lower())],
        widths=[26, 74], bold_first=True)

    # ------------------------------------------------------------ Appendix C -
    appendix("Study Roadmap, Projects and Resources")
    ah2("A 30-week study plan")
    tbl(["Weeks", "Focus", "Deliverable"],
        [["1-2", "Python, NumPy, pandas, plotting; Chapters 1-2",
          "Load a dataset, clean it, plot five informative figures"],
         ["3-4", "Chapters 3-4: generalisation, splits, leakage, features",
          "A leak-free pipeline with cross-validation"],
         ["5-6", "Chapters 5-7: linear and logistic regression, regularisation",
          "Both implemented from scratch, matching scikit-learn"],
         ["7-8", "Chapters 8-11: k-NN, trees, SVM, ensembles",
          "A tuned gradient-boosting model on a real tabular dataset"],
         ["9-10", "Chapters 12-13: unsupervised learning, evaluation",
          "A clustering study and a full evaluation report with calibration"],
         ["11-13", "Chapters 14-17: MLP, backprop, activations, optimisers",
          "Backpropagation in NumPy, 97%+ on MNIST"],
         ["14-15", "Chapters 18-20: normalisation, regularisation, debugging",
          "A CNN on CIFAR-10 above 90% with a documented recipe"],
         ["16-17", "Chapter 21: CNNs and transfer learning",
          "Fine-tune a pretrained backbone on your own images"],
         ["18-20", "Chapters 22-24: sequences, Transformers, LLMs",
          "A character-level Transformer trained from scratch, plus a RAG demo"],
         ["21-22", "Chapters 25-27: generative and self-supervised models",
          "A VAE and a small diffusion model on 32x32 images"],
         ["23-24", "Chapters 28-31, 34: efficiency and deployment",
          "Quantize, prune and deploy one model to a device or an API, with "
          "measured latency"],
         ["25-26", "Chapters 36-37: learning theory, probabilistic modelling",
          "Run the label-randomisation test on two models; fit a GP and a GMM "
          "from scratch"],
         ["27-28", "Two domain chapters of your choice from 38-42",
          "One end-to-end project in that domain with the domain's own metric "
          "reported against a naive baseline"],
         ["29", "Chapter 43: hardware, memory and distributed training",
          "Measure MFU on a real run and account for every gigabyte of memory "
          "it uses"],
         ["30", "Chapters 45-46: causal inference, then the full project "
          "walkthrough", "Design an A/B test with a power calculation, then "
          "run the thirteen stages end to end"]],
        widths=[10, 42, 48], bold_first=True)

    ah2("Portfolio projects worth building")
    bul([
        "**End-to-end tabular:** a leak-free pipeline, tuned gradient boosting, "
        "SHAP explanations, calibrated probabilities, a threshold chosen from "
        "costs, and a deployed API. This single project demonstrates most of "
        "Parts I-II.",
        "**Vision transfer:** collect a few thousand of your own images, "
        "fine-tune a pretrained backbone, evaluate per class, and ship it to a "
        "phone with INT8 quantization.",
        "**From-scratch Transformer:** a character-level model trained on a text "
        "corpus you care about, with your own attention implementation.",
        "**Sensor / time-series:** windowing, leakage-safe group splits, a 1D-CNN "
        "or GRU baseline, and an on-device deployment with measured energy.",
        "**Compression study:** take one model, apply distillation, pruning and "
        "quantization, and produce the accuracy/size/latency Pareto curve on real "
        "hardware.",
        "**RAG assistant:** over documents you own, with an evaluation set you "
        "wrote and honest accuracy numbers.",
    ])

    ah2("Books")
    tbl(["Book", "Best for"],
        [["Hands-On Machine Learning (Geron)", "The best practical first book; "
          "scikit-learn and Keras"],
         ["An Introduction to Statistical Learning (James et al.)",
          "Classical ML with clear statistics; free PDF"],
         ["The Elements of Statistical Learning (Hastie et al.)",
          "The rigorous companion to the above"],
         ["Deep Learning (Goodfellow, Bengio, Courville)",
          "Foundational theory; free online"],
         ["Dive into Deep Learning (Zhang et al.)",
          "Free, interactive, code-first, kept current"],
         ["Pattern Recognition and Machine Learning (Bishop)",
          "The Bayesian perspective"],
         ["Probabilistic Machine Learning (Murphy)",
          "Comprehensive modern reference in two volumes"],
         ["Reinforcement Learning: An Introduction (Sutton & Barto)",
          "The RL text; free online"],
         ["Designing Machine Learning Systems (Huyen)", "Production and MLOps"],
         ["Efficient Deep Learning / TinyML literature",
          "Quantization, pruning and edge deployment"]],
        widths=[42, 58], bold_first=True)

    ah2("Courses, tools and venues")
    bul([
        "**Courses:** Andrew Ng's Machine Learning Specialization and Deep "
        "Learning Specialization; fast.ai Practical Deep Learning; Stanford "
        "CS231n (vision), CS224n (NLP), CS234 (RL); MIT 6.5940 (efficient deep "
        "learning); Hugging Face courses (NLP, diffusion, RL).",
        "**Libraries:** NumPy, pandas, scikit-learn, PyTorch, JAX, "
        "LightGBM/XGBoost/CatBoost, Hugging Face transformers/datasets/peft, "
        "Optuna, ONNX Runtime, ExecuTorch, TFLite, vLLM.",
        "**Data and practice:** Kaggle, OpenML, UCI, Hugging Face Datasets, "
        "Papers with Code.",
        "**Venues to skim:** NeurIPS, ICML, ICLR (general); CVPR, ICCV, ECCV "
        "(vision); ACL, EMNLP (language); MLSys (systems); arXiv cs.LG and cs.CV "
        "for preprints.",
    ])

    box("key", "The last piece of advice",
        "Depth beats breadth. One project finished end to end - data collected, "
        "model trained, honestly evaluated, deployed, monitored, and improved "
        "after it failed in production - teaches more than twenty tutorials. The "
        "field will keep producing new architectures; the habits in Chapters 3, "
        "13 and 20 will still be what separates a working system from a good "
        "validation score.")


# =============================================================================
#            EXPANDED EXPLANATIONS AND WORKED EXAMPLES (inserted inline)
# =============================================================================

def ex_ch1():
    h2("Why machine learning works now and not in 1990")
    p("The core algorithms are old: least squares is from 1805, the perceptron "
      "from 1958, backpropagation was popularised in 1986, and convolutional "
      "networks recognised digits commercially in the early 1990s. Nothing "
      "conceptual was missing. Three practical things changed, and it is worth "
      "knowing which one you are short of when a project stalls.")
    tbl(["Ingredient", "Then", "Now", "Why it mattered"],
        [["Data", "Thousands of hand-collected samples",
          "Billions of images, trillions of text tokens",
          "Large models need large data; the internet supplied it"],
         ["Compute", "A workstation doing millions of operations per second",
          "A GPU doing 10^14 operations per second",
          "Training that took a year now takes an hour, so you get hundreds of "
          "attempts instead of one"],
         ["Method", "Sigmoid units, random initialisation, plain SGD",
          "ReLU, He initialisation, batch norm, residual connections, Adam",
          "These made deep networks trainable at all - before them, depth beyond "
          "a few layers simply did not converge"]],
        widths=[12, 26, 28, 34], bold_first=True)
    box("intuit", "Which of the three is your bottleneck?",
        "If more data reliably improves your validation score, you are "
        "data-bound: buy labels or use self-supervision. If your model has "
        "already fitted the training set perfectly and you cannot afford a "
        "bigger one, you are compute-bound. If training is unstable, "
        "diverging, or plateauing far above a reasonable loss, you are "
        "method-bound - and Part III is the chapter list for that.")

    h2("A day in the life of a machine-learning project")
    p("Textbooks present modelling as the main activity. It is not. Here is "
      "where the time actually goes on a typical supervised project, and the "
      "chapter that covers each stage.")
    tbl(["Stage", "Share of effort", "What it involves", "Chapter"],
        [["Framing the problem", "5%", "Deciding what to predict, what a "
          "prediction is worth, and what a mistake costs", "1, 13"],
         ["Getting and labelling data", "35%", "Collection, joins, consent, "
          "labelling guidelines, adjudicating disagreements", "4"],
         ["Cleaning and features", "25%", "Missing values, outliers, encodings, "
          "aggregations, leakage audits", "4"],
         ["Modelling", "10%", "Baseline, then a stronger model, then tuning",
          "5-27"],
         ["Evaluation", "10%", "Metrics, slices, calibration, error analysis",
          "3, 13"],
         ["Deployment and monitoring", "15%", "Serving, drift, retraining, "
          "incident response", "34"]],
        widths=[26, 14, 46, 14], bold_first=True)
    box("warn", "The most common beginner mistake",
        "Spending three weeks on architectures before spending three days "
        "looking at the data. Print fifty random rows. Look at fifty random "
        "images with their labels. Find the ten samples your baseline gets most "
        "wrong and read them one by one. Almost every project has a data "
        "problem hiding in plain sight, and no architecture fixes a wrong "
        "label.")

    h2("Reading the training loop as a sentence")
    p("Every training run, in every framework, in every architecture in this "
      "book, is the same five-line sentence. If you can narrate these five "
      "lines you can read any deep-learning codebase.")
    code([
        "for xb, yb in loader:          # 1. take a batch of examples",
        "    pred = model(xb)           # 2. FORWARD:  guess the answers",
        "    loss = lossf(pred, yb)     # 3. SCORE:    how wrong were the guesses?",
        "    loss.backward()            # 4. BACKWARD: how should each weight change?",
        "    opt.step()                 # 5. UPDATE:   change every weight a little",
        "    opt.zero_grad()            #    then forget the old gradients",
    ], "Listing 1.2 - The five verbs: batch, forward, score, backward, update.")
    p("Chapters 14-17 explain each verb in full: forward is a stack of matrix "
      "multiplications and non-linearities; score is the negative log-likelihood "
      "of your data under an assumed noise model; backward is the chain rule "
      "applied right to left; and update is a small step downhill with a "
      "per-parameter step size. Everything else - convolutions, attention, "
      "diffusion - changes only what happens inside step 2.")


def ex_ch2_notation():
    h2("How to read the mathematics in this book")
    p("Mathematical notation is compressed English. This section decompresses "
      "the five symbols that do most of the work, so that no equation later in "
      "the book is opaque.")
    tbl(["Symbol", "Read it aloud as", "Example", "Meaning of the example"],
        [["SUM_i x_i", "the sum over i of x sub i", "SUM_i x_i", "Add up every "
          "element of the list x"],
         ["PROD_i x_i", "the product over i", "PROD_i p_i", "Multiply all the "
          "probabilities together"],
         ["argmin_w f(w)", "the w that makes f smallest",
          "argmin_w J(w)", "The parameters with the lowest loss - not the loss "
          "value itself, the PARAMETERS"],
         ["E[X]", "the expected value of X", "E[loss]", "The average loss if you "
          "could see infinite data"],
         ["x ~ D", "x is drawn from the distribution D", "eps ~ N(0, 1)",
          "The noise is a random draw from a standard normal"],
         ["dJ/dw", "the derivative of J with respect to w", "dJ/dw = 3",
          "If w increases by 0.01, J increases by about 0.03"],
         ["||x||", "the norm, i.e. the length of x", "||w||^2",
          "The squared length of the weight vector"],
         ["a := b or a <- b", "a is defined as / set to b", "w <- w - eta g",
          "Overwrite w with the new value"]],
        widths=[16, 26, 18, 40], bold_first=True)
    box("tip", "The trick that makes equations readable",
        "Whenever you meet an unfamiliar equation, do two things. First, say "
        "out loud what each symbol IS - a scalar, a vector, a matrix, and of "
        "what shape. Second, substitute the smallest possible concrete case: "
        "one sample, two features, one output. Almost every equation in machine "
        "learning becomes obvious at n = 1, d = 2, and the general case is only "
        "bookkeeping on top of that.")

def ex_ch2_examples():
    h2("Worked example: matrix shapes in a real layer")
    p("Suppose a batch of 4 samples, each with 3 features, entering a layer with "
      "2 output units. Track the shapes:")
    eq(["X  (4, 3)     four samples, three features each",
        "W  (2, 3)     two units, each with three weights",
        "b  (2,)       one bias per unit",
        "",
        "Z = X W^T + b        (4,3) x (3,2) -> (4,2),  b broadcasts over rows",
        "A = phi(Z)           (4,2)  elementwise, shape unchanged"])
    p("Read `X W^T` as: for each of the 4 rows of X, take the dot product with "
      "each of the 2 rows of W. That is 4 x 2 = 8 dot products, each of length "
      "3, which is exactly what a GPU does in one fused operation. If you ever "
      "see a shape error in deep-learning code, write the three shapes down in "
      "this form and the mismatch becomes visible immediately.")

    h2("Worked example: a derivative you can check by hand")
    p("Take `J(w) = (w - 3)^2`, the simplest possible loss. Its derivative is "
      "`dJ/dw = 2(w - 3)`. Start at w = 0 with a learning rate of 0.1 and turn "
      "the crank:")
    tbl(["Step t", "w", "J(w)", "dJ/dw", "New w = w - 0.1 * dJ/dw"],
        [["0", "0.000", "9.000", "-6.000", "0.600"],
         ["1", "0.600", "5.760", "-4.800", "1.080"],
         ["2", "1.080", "3.686", "-3.840", "1.464"],
         ["3", "1.464", "2.359", "-3.072", "1.771"],
         ["10", "2.678", "0.104", "-0.644", "2.742"],
         ["30", "2.996", "0.000", "-0.007", "2.997"]],
        widths=[12, 18, 18, 20, 32], bold_first=True)
    p("Three lessons live in that table, and all three carry over unchanged to a "
      "billion-parameter network. The steps are large when the gradient is large "
      "and shrink automatically as you approach the minimum. The loss falls "
      "quickly at first and then slowly - which is why loss curves are shaped "
      "the way they are. And the process never quite arrives: it converges "
      "geometrically towards w = 3, which is why 'train until it stops "
      "improving' is a practical rule rather than a mathematical one.")
    box("math", "What happens if the learning rate is wrong",
        "With eta = 0.1 the update is w <- w - 0.2(w - 3), so the distance to "
        "the optimum is multiplied by 0.8 each step - smooth convergence. With "
        "eta = 0.5 the factor is 0, and you land exactly on the optimum in one "
        "step. With eta = 0.9 the factor is -0.8: you overshoot and oscillate, "
        "but still converge. With eta = 1.1 the factor is -1.2, and the distance "
        "GROWS every step - divergence. For this loss the exact threshold is "
        "eta < 1, which is 2/L with curvature L = 2. That is the general rule "
        "from Chapter 17 in miniature.")

    h2("Worked example: Bayes' rule as counting")
    p("Probability is easier when you count people instead of manipulating "
      "fractions. Take 100,000 people, a disease affecting 1 in 1,000, and a "
      "test with 99% sensitivity and 99% specificity:")
    diagram([
        "   100,000 people",
        "     |",
        "     +-- 100 ill        --> 99 test positive     (true positives)",
        "     |                      1 tests negative     (false negative)",
        "     |",
        "     +-- 99,900 healthy --> 999 test positive    (false positives)",
        "                            98,901 test negative (true negatives)",
        "",
        "   positives = 99 + 999 = 1,098",
        "   P(ill | positive) = 99 / 1,098 = 9.0%",
    ], "Figure 2.2 - Bayes' rule done by counting people rather than by algebra.")
    p("The result is identical to the algebra in the box above, but the "
      "counting version makes the cause visible: there are simply far more "
      "healthy people than ill ones, so even a small false-positive RATE "
      "produces a large false-positive COUNT. Keep this picture in mind for "
      "Chapter 13, where the same arithmetic explains why a 99%-accurate fraud "
      "detector can still be wrong nine times out of ten.")


def ex_ch3():
    h2("Overfitting made concrete: one dataset, three models")
    p("Twenty-five points were generated from `y = sin(x) + noise`. Three "
      "polynomials were fitted to the same 20 training points and evaluated on "
      "the same 5 held-out points. Nothing differs except the degree.")
    tbl(["Degree", "Train RMSE", "Test RMSE", "Diagnosis", "What the curve does"],
        [["1", "0.42", "0.45", "Underfitting - high bias", "A straight line "
          "through a wave: wrong everywhere, equally wrong on new data"],
         ["3", "0.11", "0.13", "About right", "Follows the wave, ignores the "
          "noise"],
         ["15", "0.01", "1.87", "Overfitting - high variance", "Passes through "
          "every training point and swings wildly between them"]],
        widths=[10, 14, 14, 24, 38], bold_first=True)
    p("Notice the signature of overfitting in the numbers: training error goes "
      "**down** while test error goes **up**. That divergence, not the absolute "
      "value of either, is the thing to watch. A model with 5% training error "
      "and 6% test error is healthier than one with 0.1% training error and 4% "
      "test error, even though the second has a better test score - the second "
      "one is telling you it would improve with regularisation or more data.")
    box("intuit", "Memorising versus understanding",
        "A student who memorises the answers to last year's exam scores 100% on "
        "last year's exam and 40% on this year's. A student who understands the "
        "material scores 85% on both. Training error is last year's exam. It is "
        "not a measure of learning; it is a measure of memory capacity, and "
        "every model has more of that than you think.")

    h2("Cross-validation, step by step")
    p("The mechanics of 5-fold cross-validation, spelled out, because the order "
      "of operations is exactly where mistakes happen:")
    bul([
        "Shuffle the training data once (stratified by class if classifying) and "
        "cut it into 5 equal blocks.",
        "For fold 1: hold out block 1. **Fit the scaler, the imputer, any "
        "feature selection and the model on blocks 2-5 only.** Transform block 1 "
        "with those fitted objects and score it.",
        "Repeat for folds 2 to 5, each time refitting everything from scratch.",
        "You now have 5 scores. Report their mean and standard deviation. The "
        "standard deviation is not decoration - it tells you whether a 0.3-point "
        "difference between two models is real.",
        "Finally, refit the whole pipeline on all 5 blocks and use that as your "
        "model. The cross-validation was an estimate of how well this final "
        "model will do, not the model itself.",
    ], ordered=True)
    box("warn", "The single most common leak, in one line of code",
        "`X = scaler.fit_transform(X)` written BEFORE the split. The scaler's "
        "mean and standard deviation now contain information from the test rows, "
        "so every model you evaluate afterwards has peeked. The score inflates "
        "by a little on large datasets and by a lot on small ones, and the "
        "inflation is invisible - it looks like a good result. Putting the "
        "scaler inside a Pipeline makes this class of bug structurally "
        "impossible.")

    h2("How much data do I need?")
    p("There is no universal answer, but there are usable anchors, and a "
      "learning curve settles the question empirically for your problem in an "
      "afternoon:")
    tbl(["Situation", "Rough requirement"],
        [["Linear or logistic model, d features", "At least 10-20 samples per "
          "feature; more if classes are imbalanced"],
         ["Gradient boosting on tabular data", "A few thousand rows is often "
          "enough; it degrades gracefully below that"],
         ["Small CNN trained from scratch", "1,000-10,000 labelled images per "
          "class"],
         ["Fine-tuning a pretrained backbone", "50-500 images per class - two "
          "orders of magnitude less, which is why transfer learning dominates"],
         ["Fine-tuning an LLM for style or format", "500-5,000 high-quality "
          "instruction pairs"],
         ["Training a foundation model from scratch", "Do not; the cost is in "
          "the millions and the result is available for download"]],
        widths=[36, 64], bold_first=True)
    p("The reliable procedure: train on 10%, 25%, 50% and 100% of what you "
      "have, and plot validation error against sample count. If the curve is "
      "still descending steeply at 100%, more data is the cheapest improvement "
      "available. If it has flattened, more data will not help and you should "
      "spend the budget on features, capacity or better labels instead.")


def ex_ch4():
    h2("A worked cleaning session")
    p("Below is a five-row extract from a realistic sensor dataset, with the "
      "problems a real file contains. Each column heading is followed by the "
      "decision it forces.")
    tbl(["user_id", "timestamp", "hr_bpm", "steps", "device", "label"],
        [["A17", "2024-03-01 08:00", "72", "1200", "watch_v2", "walking"],
         ["A17", "2024-03-01 08:01", "", "1350", "watch_v2", "walking"],
         ["B03", "2024-03-01 08:01", "910", "0", "Watch V2", "sitting"],
         ["B03", "2024-03-01 08:02", "68", "-5", "watch_v2", "sitting"],
         ["A17", "2024-03-01 08:00", "72", "1200", "watch_v2", "walking"]],
        widths=[14, 26, 12, 12, 18, 18], bold_first=True)
    bul([
        "**Missing heart rate (row 2):** not random - the sensor drops readings "
        "during motion, so missingness correlates with the label. Impute, and "
        "add an `hr_missing` indicator column; dropping the row would bias the "
        "dataset towards stationary activities.",
        "**910 bpm (row 3):** physiologically impossible, so it is an error, not "
        "a rare truth. Clip to a plausible range or mark as missing. Decide the "
        "rule from domain knowledge, never from the data alone.",
        "**-5 steps (row 4):** a counter reset or an integer underflow. Same "
        "treatment.",
        "**'Watch V2' versus 'watch_v2':** the same device in two spellings. "
        "Normalise case and whitespace, or you will train a model with two "
        "unrelated one-hot columns for one device.",
        "**Row 5 duplicates row 1:** exact duplicates inflate the effective "
        "weight of one moment and, if they land on opposite sides of a split, "
        "leak. Deduplicate on the natural key (user, timestamp).",
        "**user_id present:** never feed it as a feature, and always split by it. "
        "Otherwise the model learns 'A17 walks' rather than 'this signal means "
        "walking', and it will fail on every new user.",
    ])

    h2("Windowing time series, correctly")
    p("Sensor and time-series data must be converted into fixed-length windows "
      "before most models can consume it. Three choices define the conversion, "
      "and each one has a trap.")
    tbl(["Choice", "Typical value", "The trap"],
        [["Window length", "1-10 seconds for human activity; long enough to "
          "contain one cycle of the phenomenon", "Too short and the pattern is "
          "not in the window at all"],
         ["Overlap / stride", "50% overlap is common for training",
          "Overlapping windows across a train/test boundary share samples - a "
          "leak. Split by TIME or by SUBJECT first, then window each part "
          "separately"],
         ["Label of a window", "Majority label, or discard mixed windows",
          "Windows straddling a transition carry two activities and add label "
          "noise"]],
        widths=[20, 36, 44], bold_first=True)
    code([
        "import numpy as np",
        "",
        "def windows(sig, fs=50, sec=2.0, overlap=0.5):",
        "    n = int(fs * sec); step = int(n * (1 - overlap))",
        "    return np.stack([sig[i:i + n]",
        "                     for i in range(0, len(sig) - n + 1, step)])",
        "",
        "# Feature set per window that is hard to beat on IMU data:",
        "def feats(w):                       # w: (n_samples, 3) for x, y, z",
        "    mag = np.linalg.norm(w, axis=1)",
        "    out = []",
        "    for ch in [w[:, 0], w[:, 1], w[:, 2], mag]:",
        "        out += [ch.mean(), ch.std(), ch.min(), ch.max(),",
        "                np.percentile(ch, 25), np.percentile(ch, 75),",
        "                np.abs(np.diff(ch)).mean(),          # mean abs change",
        "                ((ch[:-1] * ch[1:]) < 0).sum()]      # zero crossings",
        "    # frequency domain: dominant frequency and spectral energy",
        "    P = np.abs(np.fft.rfft(mag)) ** 2",
        "    out += [P[1:].argmax() + 1, P.sum(), (P / P.sum() *",
        "            np.log(P / P.sum() + 1e-12)).sum() * -1]   # spectral entropy",
        "    return np.array(out)",
    ], "Listing 4.2 - Window extraction and a strong classical feature set. On "
       "many sensor tasks these features plus gradient boosting beat a deep "
       "network trained on raw signal, and they train in seconds.")


def ex_ch5():
    h2("The five houses, solved completely by hand")
    p("Chapter 1 quoted a fitted line without deriving it. Here is the whole "
      "computation, with every number, so that the closed-form solution stops "
      "being a formula you trust and becomes one you can check.")
    tbl(["i", "size x_i", "price y_i", "x_i - x_bar", "y_i - y_bar",
         "(x-x_bar)(y-y_bar)", "(x-x_bar)^2"],
        [["1", "50", "150", "-40", "-102", "4080", "1600"],
         ["2", "70", "195", "-20", "-57", "1140", "400"],
         ["3", "90", "260", "0", "8", "0", "0"],
         ["4", "110", "300", "20", "48", "960", "400"],
         ["5", "130", "355", "40", "103", "4120", "1600"],
         ["sum", "450", "1260", "0", "0", "10300", "4000"],
         ["mean", "90", "252", "-", "-", "-", "-"]],
        widths=[8, 13, 14, 15, 15, 21, 14], bold_first=True)
    eq(["w = SUM (x-x_bar)(y-y_bar) / SUM (x-x_bar)^2  =  10300 / 4000  =  2.575",
        "b = y_bar - w * x_bar  =  252 - 2.575 * 90  =  20.25"])
    p("So the fitted line is `price = 2.575 * size + 20.25`: each square metre "
      "is worth 2,575 EUR, and the intercept of 20.25k is the model's guess for "
      "a house of zero size - a reminder that the intercept is often "
      "meaningless in isolation and exists only to position the line.")
    tbl(["Size", "Actual", "Predicted", "Residual"],
        [["50", "150", "149.00", "+1.00"],
         ["70", "195", "200.50", "-5.50"],
         ["90", "260", "252.00", "+8.00"],
         ["110", "300", "303.50", "-3.50"],
         ["130", "355", "355.00", "0.00"]],
        widths=[20, 22, 26, 32], bold_first=True)
    eq(["MSE  = (1.00^2 + 5.50^2 + 8.00^2 + 3.50^2 + 0^2) / 5 = 21.5",
        "RMSE = sqrt(21.5) = 4.64  (thousand EUR - the natural error unit)",
        "R^2  = 1 - 107.5 / 26630 = 0.996"])
    p("Two sanity checks worth internalising. The residuals sum to zero - that "
      "is a mathematical consequence of fitting an intercept by least squares, "
      "and if yours do not, you have a bug. And RMSE is in the units of the "
      "target, which is why it is the number to quote to a stakeholder; R^2 = "
      "0.996 sounds impressive but says nothing about whether being off by "
      "4,600 EUR is acceptable.")
    box("math", "Why the formula looks like that",
        "Set the derivative of J to zero. dJ/db = 0 gives b = y_bar - w x_bar, "
        "i.e. the line passes through the centre of mass of the data. "
        "Substituting that back into dJ/dw = 0 gives w = Cov(x,y)/Var(x). So "
        "the slope is literally 'how much y moves with x, divided by how much x "
        "moves on its own'. Every regression coefficient in this book is a "
        "version of that ratio.")

    h2("The same fit by gradient descent, step by step")
    p("With standardised features (x_std = (x - 90)/28.28) and a learning rate "
      "of 0.1, starting from w = b = 0:")
    tbl(["Step", "w", "b", "J (MSE)", "dJ/dw", "dJ/db"],
        [["0", "0.00", "0.00", "68830", "-145.7", "-504.0"],
         ["1", "14.57", "50.40", "44059", "-116.5", "-403.2"],
         ["2", "26.22", "90.72", "28205", "-93.2", "-322.6"],
         ["3", "35.54", "122.98", "18059", "-74.6", "-258.0"],
         ["4", "43.00", "148.78", "11566", "-59.7", "-206.4"],
         ["...", "...", "...", "...", "...", "..."],
         ["converged", "72.83", "252.00", "21.5", "0.0", "0.0"]],
        widths=[16, 16, 16, 18, 17, 17], bold_first=True)
    p("It arrives at the same solution the normal equations gave in one line - "
      "on standardised inputs the converged slope 72.83 corresponds to 72.83 / "
      "28.28 = 2.575 in original units, and the converged intercept is the mean "
      "price. Gradient descent is slower here and would be absurd for five "
      "points; its advantage appears when there are ten million rows and ten "
      "thousand features, where the matrix inverse is impossible and each step "
      "costs only one pass over a mini-batch.")
    box("tip", "Why the gradients start so large",
        "At w = b = 0 the model predicts 0 for every house, so residuals are "
        "around -250 and the squared loss is 68,830. Large loss means large "
        "gradient means large first steps - which is exactly why an untuned "
        "learning rate diverges most often in the first few iterations, and why "
        "warmup (Chapter 17) exists.")


def ex_ch6():
    h2("Logistic regression on four points, by hand")
    p("Four samples with one feature: x = 1, 2 label 0; x = 3, 4 label 1. Start "
      "from w = 0, b = 0 with a learning rate of 0.5.")
    tbl(["Step", "w", "b", "Predictions p", "Loss J", "Gradient (w, b)"],
        [["0", "0.000", "0.000", "0.50, 0.50, 0.50, 0.50", "0.693",
          "(-0.500, 0.000)"],
         ["1", "0.250", "0.000", "0.56, 0.62, 0.68, 0.73", "0.625",
          "(-0.058, 0.149)"],
         ["2", "0.279", "-0.074", "0.55, 0.62, 0.68, 0.74", "0.612",
          "(-0.053, 0.148)"],
         ["converged", "5.80", "-14.32", "0.00, 0.00, 1.00, 1.00", "~0",
          "(0, 0)"]],
        widths=[14, 12, 14, 30, 12, 18], bold_first=True)
    p("Read the first row carefully, because it is the whole of Chapter 6 in "
      "one line. At w = b = 0 every prediction is 0.5 and the loss is "
      "-log(0.5) = 0.693 - which is the loss any binary classifier has before "
      "it learns anything, and therefore the number your training log should "
      "start near. The gradient with respect to w is the average of "
      "`(p - y) * x` = (0.5*1 + 0.5*2 - 0.5*3 - 0.5*4)/4 = -0.5: negative, so w "
      "increases, so the score rises with x, which is exactly the right "
      "direction because the positive class sits at large x.")
    box("warn", "Why the converged weights are so large",
        "This data is perfectly separable, so the likelihood keeps improving as "
        "the boundary gets steeper: w grows without bound and the model becomes "
        "infinitely confident. With any regularisation at all (scikit-learn's "
        "default C = 1) w stops at a modest value. Unbounded weights on "
        "separable data is not a curiosity - it is why an unregularised logistic "
        "model can produce probabilities of 0.99999 that mean nothing.")
    eq(["Decision boundary:  w x + b = 0  =>  x = -b/w = 14.32/5.80 = 2.47",
        "Odds ratio per unit of x:  exp(w) = exp(5.80) = 331"])

    h2("Sigmoid, logit and probability: three views of one number")
    tbl(["Logit z", "Probability sigma(z)", "Odds p/(1-p)", "Reading"],
        [["-4", "0.018", "1 : 55", "Almost certainly negative"],
         ["-2", "0.119", "1 : 7.4", "Probably negative"],
         ["-1", "0.269", "1 : 2.7", "Leaning negative"],
         ["0", "0.500", "1 : 1", "No information"],
         ["+1", "0.731", "2.7 : 1", "Leaning positive"],
         ["+2", "0.881", "7.4 : 1", "Probably positive"],
         ["+4", "0.982", "55 : 1", "Almost certainly positive"]],
        widths=[14, 24, 22, 40], bold_first=True)
    p("Two facts to carry forward. Adding 1 to the logit always multiplies the "
      "odds by e = 2.718, whatever the starting point - that constancy is what "
      "makes coefficients interpretable. And beyond about |z| = 4 the "
      "probability barely moves while the logit keeps growing, which is the "
      "saturation that kills gradients in deep sigmoid networks.")


def ex_ch9():
    h2("A complete split search on a tiny dataset")
    p("Ten samples, one feature (age), one binary label (bought). The algorithm "
      "sorts by the feature, considers each midpoint between adjacent distinct "
      "values as a candidate threshold, and scores them all.")
    tbl(["Age", "22", "25", "28", "33", "37", "41", "45", "52", "58", "63"],
        [["Bought", "0", "0", "0", "1", "0", "1", "1", "1", "1", "1"]],
        widths=[16, 8.4, 8.4, 8.4, 8.4, 8.4, 8.4, 8.4, 8.4, 8.4, 8.4],
        bold_first=True)
    p("Parent impurity: the ten samples split 4 zeros and 6 ones, so "
      "Gini = 1 - 0.4^2 - 0.6^2 = 0.48.")
    tbl(["Threshold", "Left (n, ones)", "Gini L", "Right (n, ones)", "Gini R",
         "Weighted", "Gain"],
        [["age < 26.5", "2, 0", "0.000", "8, 6", "0.375", "0.300", "0.180"],
         ["age < 30.5", "3, 0", "0.000", "7, 6", "0.245", "0.171", "0.309"],
         ["age < 35.0", "4, 1", "0.375", "6, 5", "0.278", "0.317", "0.163"],
         ["age < 39.0", "5, 1", "0.320", "5, 5", "0.000", "0.160", "0.320"],
         ["age < 43.0", "6, 2", "0.444", "4, 4", "0.000", "0.267", "0.213"],
         ["age < 48.5", "7, 3", "0.490", "3, 3", "0.000", "0.343", "0.137"]],
        widths=[16, 18, 11, 18, 11, 12, 14], bold_first=True)
    p("The winner is `age < 39.0` with a gain of 0.320. Look at why it beats "
      "`age < 30.5`, which also looks natural: both isolate a clean group, but "
      "the 39.0 split makes the right child perfectly pure (five ones, Gini 0) "
      "while leaving only one misplaced sample on the left, whereas the 30.5 "
      "split leaves the awkward 37-year-old buried in a seven-sample child that "
      "stays impure. Impurity gain is a weighted average, so it rewards making "
      "one LARGE child clean over making one small child clean.")
    p("Note also what the algorithm never considered: a rule such as "
      "`33 <= age <= 45`. A single split is always one threshold on one "
      "feature, so every band, diagonal or interaction has to be assembled from "
      "nested splits. That is why trees need depth to express what a linear "
      "model states in one coefficient, and why a diagonal boundary comes out "
      "of a tree as a staircase.")
    box("math", "Doing the arithmetic for one row yourself",
        "Take `age < 39.0`. The left child holds ages 22, 25, 28, 33, 37 with "
        "labels 0, 0, 0, 1, 0 - one positive out of five, so Gini = 1 - 0.2^2 - "
        "0.8^2 = 0.32. The right child holds 41, 45, 52, 58, 63, all positive, "
        "so Gini = 0. Weighted impurity = (5/10)(0.32) + (5/10)(0) = 0.16, and "
        "the gain is 0.48 - 0.16 = 0.32. Re-derive one more row from the table "
        "and the algorithm will never be mysterious again - a decision tree is "
        "this loop, repeated over every feature and every threshold, then "
        "recursed on each child.")

    h2("Reading a tree out loud")
    p("A trained tree is a set of nested if-statements, and you should be able "
      "to convert one into English. The tree in Figure 9.1 says:")
    bul([
        "If the customer is under 45 and earns under 30k, predicted probability "
        "0.12 - the low-risk group.",
        "If under 45 and earning 30k or more, 0.34.",
        "If 45 or over and a smoker, 0.71 - the highest-risk leaf.",
        "If 45 or over and not a smoker, 0.28.",
    ])
    p("Each leaf value is simply the fraction of positive training samples that "
      "landed in that leaf. That is worth stating plainly because it explains "
      "two behaviours: leaves with few samples give extreme, unreliable "
      "probabilities (hence `min_samples_leaf`), and a tree can never predict a "
      "value it did not see in training - it cannot extrapolate above the "
      "highest leaf mean, which is why trees are poor at trending time series.")


def ex_ch11():
    h2("Gradient boosting on six points, three rounds")
    p("Target values 10, 12, 14, 20, 22, 30. The first model is the mean, 18. "
      "Each round fits a depth-1 tree (a single split) to the current "
      "residuals, and adds it with a learning rate of 0.5.")
    tbl(["Round", "Residuals fed to the tree", "Tree's split and outputs",
         "Ensemble prediction after the round", "MSE"],
        [["0", "-", "constant 18", "18, 18, 18, 18, 18, 18", "46.67"],
         ["1", "-8, -6, -4, +2, +4, +12", "split after 3rd: -6 / +6",
          "15, 15, 15, 21, 21, 21", "19.67"],
         ["2", "-5, -3, -1, -1, +1, +9", "split after 5th: -1.8 / +9",
          "14.1, 14.1, 14.1, 20.1, 20.1, 25.5", "7.52"],
         ["3", "-4.1, -2.1, -0.1, -0.1, +1.9, +4.5", "split after 4th: -1.6 / +3.2",
          "13.3, 13.3, 13.3, 19.3, 21.7, 27.1", "3.68"]],
        widths=[9, 24, 22, 32, 13], bold_first=True)
    p("The error falls 46.67 -> 19.67 -> 7.52 -> 3.68. Each tree is individually "
      "useless - it is a single threshold - but each one attacks precisely what "
      "the ensemble still gets wrong, and the errors shrink geometrically. That "
      "is the whole of boosting; XGBoost and LightGBM differ from this table "
      "only in how they find the split, how they regularise the leaf values, "
      "and how fast they do it.")
    box("key", "Why the learning rate is 0.5 and not 1.0",
        "With nu = 1.0 the first tree would remove the residuals entirely on "
        "the training data and the ensemble would immediately be fitting noise. "
        "Shrinkage forces each tree to take only part of the credit, so the "
        "correction is spread over many trees and no single one dominates. This "
        "is the same principle as a small learning rate in gradient descent, "
        "and it is the main reason boosting generalises rather than merely "
        "memorising.")

    h2("Bagging versus boosting, side by side")
    tbl(["Question", "Random forest (bagging)", "Gradient boosting"],
        [["What is each tree trained on?", "A bootstrap resample, with a random "
          "subset of features per split", "The residuals of everything built so "
          "far"],
         ["How deep are the trees?", "Deep, often unlimited", "Shallow - depth "
          "3-8, or 31-255 leaves"],
         ["Can it be parallelised?", "Yes, trees are independent",
          "No across trees (each needs the previous); yes within a tree"],
         ["What happens with more trees?", "Error flattens; more trees never "
          "hurt accuracy", "Error keeps falling then RISES - you must early-stop"],
         ["Main risk", "Underfitting if trees are too shallow", "Overfitting if "
          "the learning rate is high or you boost too long"],
         ["Tuning effort", "Very low - defaults are close to optimal",
          "Moderate - learning rate, depth, and rounds interact"],
         ["Typical winner on tabular data", "Strong baseline",
          "Usually the best, by a small but consistent margin"]],
        widths=[24, 38, 38], bold_first=True)


def ex_ch12():
    h2("k-means, iteration by iteration")
    p("Six one-dimensional points - 1, 2, 4, 7, 8, 10 - with k = 2 and the "
      "unlucky initial centroids 1 and 10:")
    tbl(["Iteration", "Assignment", "New centroids",
         "Inertia at the start of the step"],
        [["1", "{1, 2, 4} -> c1;  {7, 8, 10} -> c2", "c1 = 2.33, c2 = 8.33",
          "23.00"],
         ["2", "{1, 2, 4} -> c1;  {7, 8, 10} -> c2", "c1 = 2.33, c2 = 8.33 "
          "(unchanged)", "9.33"],
         ["3", "no change - converged", "-", "9.33"]],
        widths=[14, 36, 34, 16], bold_first=True)
    p("Two iterations, and the inertia drops from 23.0 to 9.33 - the value the "
      "algorithm reports. Now try initialising at 1 and 2 instead: the first "
      "assignment puts {1} in one cluster and {2, 4, 7, 8, 10} in the other, "
      "and the algorithm converges to a visibly worse partition with higher "
      "inertia. Same data, same k, different answer. That is why you run "
      "`n_init` restarts and keep the lowest inertia, and why k-means++ seeding "
      "(choose the next centroid far from the existing ones, with probability "
      "proportional to squared distance) is the default.")

    h2("PCA on ten points, computed in full")
    p("Ten two-dimensional points with a strong positive correlation. Centre "
      "them, form the covariance matrix, and take its eigenvectors:")
    eq(["mean = (1.81, 1.91)",
        "",
        "covariance = [ 0.6166  0.6154 ]",
        "             [ 0.6154  0.7166 ]",
        "",
        "eigenvalues  = 1.284  and  0.049",
        "PC1 = ( 0.678,  0.735)      explains 1.284/1.333 = 96.3% of variance",
        "PC2 = (-0.735,  0.678)      explains 3.7%"])
    p("PC1 points along the diagonal, which is where the data actually varies; "
      "PC2 is perpendicular to it, as it must be, and captures almost nothing. "
      "Projecting onto PC1 alone turns each 2-D point into one number - a 50% "
      "compression - and reconstructing from that single number recovers the "
      "original points with an RMSE of 0.15, small compared with the spread of "
      "the data. That is the entire method: rotate so the axes line up with the "
      "variance, then drop the axes that barely move.")
    box("intuit", "PCA as choosing a camera angle",
        "Imagine a flat, disc-shaped galaxy of points floating in 3-D. "
        "Photographed face-on you see its full structure; photographed edge-on "
        "it collapses to a line and you lose everything. PCA finds the face-on "
        "angle automatically, by maximising the spread of the shadow. The "
        "eigenvalues tell you how much structure each angle preserves, and the "
        "explained-variance ratio is just those numbers normalised to sum to "
        "one.")
    box("warn", "The direction with the most variance is not always the one you "
        "want",
        "PCA is unsupervised - it never looks at the labels. If your classes "
        "differ along a low-variance direction (a small but consistent offset) "
        "PCA may discard exactly that direction while faithfully preserving an "
        "irrelevant high-variance one such as overall brightness. Always check "
        "downstream accuracy after reducing, and consider LDA when you have "
        "labels and separation is the goal.")


def ex_ch13():
    h2("One confusion matrix, every metric computed")
    p("A fraud model is evaluated on 1,000 transactions, of which 100 are "
      "genuinely fraudulent. It flags 140, of which 80 are correct.")
    diagram([
        "                        PREDICTED",
        "                    fraud      legit        total",
        "                +----------+----------+",
        "   A    fraud   |  TP = 80 |  FN = 20 |     100",
        "   C            +----------+----------+",
        "   T    legit   |  FP = 60 |  TN =840 |     900",
        "   U            +----------+----------+",
        "   A    total       140         860        1000",
    ], "Figure 13.2 - The worked example used throughout this section.")
    tbl(["Metric", "Computation", "Value", "What it tells you"],
        [["Accuracy", "(80+840)/1000", "0.920", "Looks excellent - but always "
          "predicting 'legit' scores 0.900, so the model has bought you 2 points"],
         ["Precision", "80/140", "0.571", "43% of the alerts are wrong; this is "
          "the analyst's wasted time"],
         ["Recall", "80/100", "0.800", "One fraud in five still gets through"],
         ["F1", "2(0.571)(0.8)/(0.571+0.8)", "0.667", "The balance of the two"],
         ["Specificity", "840/900", "0.933", "Most legitimate customers are left "
          "alone"],
         ["Balanced accuracy", "(0.800+0.933)/2", "0.867", "Accuracy that is not "
          "fooled by the class ratio"],
         ["MCC", "correlation form", "0.634", "The single most informative "
          "scalar here"],
         ["False positive rate", "60/900", "0.067", "The x-axis of the ROC curve"]],
        widths=[18, 22, 12, 48], bold_first=True)
    box("key", "Now convert the metrics into money",
        "Suppose an investigated alert costs 20 EUR of analyst time and a missed "
        "fraud costs 500 EUR. This model costs 140 x 20 + 20 x 500 = 12,800 EUR. "
        "Lower the threshold until recall reaches 0.95: perhaps 300 alerts and "
        "5 misses, costing 300 x 20 + 5 x 500 = 8,500 EUR - materially better, "
        "with WORSE precision and WORSE accuracy. This is why Chapter 13 insists "
        "that the threshold is a business decision. Compute the cost curve, "
        "then pick the operating point; never accept 0.5 by default.")

    h2("Reading a ROC curve and a PR curve of the same model")
    diagram([
        "   ROC  (TPR vs FPR)                PR  (precision vs recall)",
        "   1 |      ____----                1 |--__",
        "     |    _/                          |    \\__",
        "   T |  _/                          P |       \\____",
        "   P | /                            r |            \\____",
        "   R |/                             e |                 \\___",
        "   0 +------------------ 1         0 +---------------------- 1",
        "          FPR                              Recall",
        "   baseline = the diagonal          baseline = the positive rate (0.10)",
        "   AUC = 0.93 (looks great)         AP = 0.61 (the honest picture)",
    ], "Figure 13.3 - The same predictions, two curves, two impressions.")
    p("The ROC curve's baseline is the diagonal regardless of class balance, so "
      "a rare-positive problem always looks flattering. The PR curve's baseline "
      "is the positive rate - here 0.10 - so an average precision of 0.61 is "
      "correctly read as 'six times better than guessing', not as 'nearly "
      "perfect'. When positives are rare, quote average precision and show the "
      "curve.")


def ex_ch15():
    h2("Backpropagation on real numbers, end to end")
    p("Everything in this chapter becomes concrete once you push one sample "
      "through a network by hand. Here is a 2-2-1 network with ReLU hidden "
      "units and a sigmoid output, one training sample, and every number "
      "written out. Verify each line with a calculator; it takes ten minutes "
      "and permanently removes the mystery.")
    diagram([
        "        x1=1.0 ---.                                                  ",
        "                   \\   W1 = [ 0.5  0.3 ]   b1 = [ 0.1 ]              ",
        "                    >-------[ 0.2  0.8 ]        [-0.1 ]  -> h1, h2   ",
        "        x2=2.0 ---'                                                  ",
        "                                                                     ",
        "        h1, h2 --> W2 = [1.0, -1.0], b2 = 0.5 --> z2 --> sigmoid --> p",
        "                                                                     ",
        "        true label y = 1        loss = binary cross-entropy          ",
        "        (note: W1 row 2 is [-0.2, 0.8] in the arithmetic below)      ",
    ], "Figure 15.2 - The network used for the hand computation.")
    h3("Forward pass")
    eq(["z1_1 = 0.5(1.0) + 0.3(2.0) + 0.1  =  1.2      a1_1 = ReLU(1.2) = 1.2",
        "z1_2 = -0.2(1.0) + 0.8(2.0) - 0.1 =  1.3      a1_2 = ReLU(1.3) = 1.3",
        "",
        "z2   = 1.0(1.2) + (-1.0)(1.3) + 0.5 = 0.4",
        "p    = sigmoid(0.4) = 1/(1 + e^-0.4) = 0.5987",
        "L    = -log(0.5987) = 0.5130"])
    h3("Backward pass")
    p("Start at the output and walk backwards, applying the four equations from "
      "the previous section. Every quantity below is a number you can check.")
    eq(["delta2 = p - y = 0.5987 - 1 = -0.4013            <- the clean identity",
        "",
        "dL/dW2 = delta2 * a1 = -0.4013 * [1.2, 1.3] = [-0.4816, -0.5217]",
        "dL/db2 = delta2 = -0.4013",
        "",
        "dL/da1 = W2^T * delta2 = [1.0, -1.0] * -0.4013 = [-0.4013, +0.4013]",
        "delta1 = dL/da1 * ReLU'(z1) = [-0.4013, 0.4013] * [1, 1] = [-0.4013, 0.4013]",
        "",
        "dL/dW1 = delta1 (x)^T = [ -0.4013*1.0   -0.4013*2.0 ]",
        "                        [ +0.4013*1.0   +0.4013*2.0 ]",
        "                      = [ -0.4013  -0.8026 ]",
        "                        [ +0.4013  +0.8026 ]",
        "dL/db1 = delta1 = [-0.4013, +0.4013]"])
    h3("The update, and proof that it worked")
    eq(["With eta = 0.1:",
        "  W1 <- [ 0.5401   0.3803 ]      W2 <- [1.0482, -0.9478]",
        "        [-0.2401   0.7197 ]      b2 <- 0.5401",
        "",
        "Re-running the forward pass with the new weights:",
        "  z2 = 1.0464     p = 0.7401     L = 0.3010",
        "",
        "The loss fell from 0.5130 to 0.3010 in one step, and the predicted",
        "probability moved from 0.60 towards the true label 1. That is",
        "learning, in its entirety."])
    box("math", "Confirming the gradient numerically",
        "Perturb W1[0,0] by eps = 1e-6 in each direction and recompute the "
        "loss: (L(+eps) - L(-eps)) / (2 eps) = -0.401312, which matches the "
        "analytic -0.401312 to six decimals. Do this for all four entries of W1 "
        "and you have written your own gradient checker - the tool that "
        "distinguishes a derivation error from a training-hyperparameter "
        "problem.")
    box("intuit", "Reading the numbers as a story",
        "delta2 = -0.4013 says the output was too LOW by about 0.4 (in "
        "probability terms). The gradient on W2 is negative for both hidden "
        "units, so both connections strengthen - the network decides to listen "
        "more to h1 and less negatively to h2. The gradient on W1 row 2 is "
        "positive, so those weights DECREASE, which lowers h2, which raises z2 "
        "because W2's second entry is negative. Every sign in the computation "
        "has a plain-language reason, and tracing them is the best debugging "
        "skill you can develop.")

    h2("What ReLU's gate does to the gradient")
    p("In the example above both hidden pre-activations were positive, so both "
      "gates were open and gradient flowed to every weight. Change x to (1, "
      "-2) and z1_1 becomes 0.5 - 0.6 + 0.1 = 0.0 while z1_2 becomes -0.2 - 1.6 "
      "- 0.1 = -1.9. The second unit's ReLU derivative is then 0, so:")
    eq(["delta1 = dL/da1 * [1, 0] = [-0.4013, 0]",
        "dL/dW1 row 2 = [0, 0]     <- this unit learns NOTHING from this sample"])
    p("That is the mechanism behind three things you will meet repeatedly: "
      "ReLU networks are sparse (typically half the units are inactive on any "
      "given input, which is a form of free regularisation); a unit whose "
      "pre-activation is negative for **every** sample receives zero gradient "
      "forever and is dead; and gradient can vanish not only by shrinking but "
      "by being gated off entirely. Leaky ReLU exists precisely to leave the "
      "gate slightly ajar.")


def ex_ch17():
    h2("One Adam update, arithmetic included")
    p("Adam's formula has four moving parts, and seeing them evaluate on a "
      "constant gradient makes the design obvious. Take g = 0.5 at every step, "
      "with beta1 = 0.9, beta2 = 0.999, eta = 0.001, eps = 1e-8.")
    tbl(["Step t", "m (first moment)", "v (second moment)", "m_hat", "v_hat",
         "Update size"],
        [["1", "0.05000", "0.000250", "0.50000", "0.250000", "0.001000"],
         ["2", "0.09500", "0.000500", "0.50000", "0.250000", "0.001000"],
         ["3", "0.13550", "0.000749", "0.50000", "0.250000", "0.001000"]],
        widths=[10, 20, 20, 16, 16, 18], bold_first=True)
    box("key", "Three things this table proves",
        "(1) BIAS CORRECTION MATTERS: the raw m at step 1 is 0.05, ten times "
        "smaller than the true gradient 0.5, because the moving average starts "
        "from zero. Dividing by (1 - beta1^t) restores it exactly. Without "
        "correction, Adam would take absurdly small steps for the first hundred "
        "iterations. (2) THE UPDATE IS SCALE-FREE: it comes out at 0.001 = the "
        "learning rate, and it would still be 0.001 if the gradient were 0.5, "
        "50, or 5,000, because m_hat/sqrt(v_hat) cancels the magnitude. That is "
        "why Adam needs so little tuning across wildly different layers and "
        "losses. (3) THE UNITS ARE INTERPRETABLE: with Adam, the learning rate "
        "IS roughly the per-step change in each parameter - which is why 1e-3 "
        "and 3e-4 are such durable defaults.")
    p("The flip side of scale invariance is that Adam ignores information SGD "
      "uses: a parameter with a genuinely tiny gradient still gets a full-sized "
      "step. That is one reason well-tuned SGD with momentum still edges out "
      "Adam on some vision benchmarks, and why the gap closes when Adam is "
      "paired with decoupled weight decay.")

    h2("Choosing a learning rate: what each failure looks like")
    diagram([
        "  loss                                                          ",
        "   |  \\                                                         ",
        "   |   \\____________________  eta far too small (barely moves)  ",
        "   |  \\                                                         ",
        "   |   \\__                                                      ",
        "   |      \\____                                                 ",
        "   |           \\_______  eta good (fast, then flattens)         ",
        "   |  \\/\\/\\                                                     ",
        "   |       \\/\\/\\/\\/\\/\\/  eta slightly high (noisy plateau)      ",
        "   |  /\\                                                        ",
        "   | /  \\  /\\    /\\                                             ",
        "   |/    \\/  \\__/  \\___ NaN   eta far too high (diverges)       ",
        "   +---------------------------------------------> steps       ",
    ], "Figure 17.1 - Four learning rates, four distinctive loss-curve shapes.")
    tbl(["What you see", "Diagnosis", "Action"],
        [["Loss barely changes over an epoch", "Learning rate 10-100x too small",
          "Multiply by 10 and retry; run the LR range test"],
         ["Smooth fall then a flat floor", "Healthy", "Add a decay schedule to "
          "squeeze the last few percent"],
         ["Falls then plateaus with visible noise", "Slightly too high for the "
          "final phase", "Cosine or step decay; this is exactly what a schedule "
          "fixes"],
         ["Spikes upward, then NaN", "Far too high, or exploding gradients",
          "Reduce by 10x, add gradient clipping, check for bad inputs"],
         ["Falls, then rises steadily", "Not an LR problem - this is "
          "overfitting", "Regularise; early stop"]],
        widths=[28, 30, 42], bold_first=True)

    h2("Momentum, seen as a ball on a surface")
    box("intuit", "Why momentum is not just 'bigger steps'",
        "Picture a narrow valley whose floor slopes gently towards the minimum "
        "while its walls are steep. Plain gradient descent is dominated by the "
        "steep direction: it bounces from wall to wall and creeps along the "
        "floor. Momentum accumulates a velocity, and because the wall-bouncing "
        "components alternate in sign they CANCEL, while the floor component "
        "always points the same way and ACCUMULATES. With beta = 0.9 the "
        "consistent direction is amplified by roughly 1/(1 - 0.9) = 10x, and "
        "the oscillation is damped. That is why momentum both stabilises and "
        "accelerates, which sounds contradictory until you see the cancellation.")


def ex_ch21():
    h2("Convolution arithmetic worked through")
    p("Three formulas do all the work. Here they are applied to the cases you "
      "will actually meet.")
    tbl(["Input", "Kernel", "Padding", "Stride", "Output", "Comment"],
        [["32x32", "3x3", "1", "1", "32x32", "'same' padding - the standard "
          "feature-extraction layer"],
         ["32x32", "3x3", "0", "1", "30x30", "'valid' - loses a ring of pixels "
          "each layer"],
         ["32x32", "3x3", "1", "2", "16x16", "Strided downsample, replaces "
          "pooling"],
         ["224x224", "7x7", "3", "2", "112x112", "The ResNet stem"],
         ["32x32", "1x1", "0", "1", "32x32", "Channel mixing only - spatial size "
          "untouched"]],
        widths=[13, 12, 12, 11, 14, 38], bold_first=True)
    eq(["O = floor( (I + 2P - K) / S ) + 1",
        "",
        "Check the third row: (32 + 2 - 3)/2 + 1 = floor(15.5) + 1 = 16.  OK."])

    h2("Cost of one real layer, counted exactly")
    p("Take a 3x3 convolution with 64 input channels and 128 output channels, "
      "operating on a 32x32 feature map:")
    eq(["Parameters = K*K*C_in*C_out + C_out",
        "           = 3*3*64*128 + 128 = 73,728 + 128 = 73,856",
        "",
        "Multiply-adds = K*K*C_in*C_out*H_out*W_out",
        "              = 3*3*64*128*32*32 = 75,497,472  (~75 M per image)"])
    p("Now replace it with a depthwise separable block - a 3x3 depthwise "
      "convolution followed by a 1x1 pointwise convolution:")
    eq(["Parameters = (3*3*64 + 64) + (64*128 + 128) = 640 + 8,320 = 8,960",
        "Multiply-adds = (3*3*64 + 64*128) * 32*32 = 8,978,432   (~9 M)",
        "",
        "Parameters:  8.2x fewer.    Compute:  8.4x fewer."])
    box("key", "Where the saving comes from",
        "A standard convolution does two jobs at once: it mixes across SPACE "
        "(the 3x3 neighbourhood) and across CHANNELS (all 64 inputs feeding all "
        "128 outputs), and it pays the product of the two costs. Separating "
        "them turns a product into a sum: 3*3*64 for space plus 64*128 for "
        "channels. The saving is roughly 1/C_out + 1/K^2, which for typical "
        "values is 8-9x. Every efficient mobile architecture is built on this "
        "one observation.")

    h2("Receptive field, computed layer by layer")
    p("A unit's receptive field is the patch of input that can influence it. "
      "Grow it with the recurrence `RF <- RF + (K - 1) * (product of all "
      "previous strides)`:")
    tbl(["Layer", "Kernel", "Stride", "Cumulative stride", "Receptive field"],
        [["input", "-", "-", "1", "1"],
         ["conv 3x3", "3", "1", "1", "3"],
         ["conv 3x3", "3", "1", "1", "5"],
         ["maxpool 2x2", "2", "2", "2", "6"],
         ["conv 3x3", "3", "1", "2", "10"],
         ["conv 3x3", "3", "1", "2", "14"],
         ["maxpool 2x2", "2", "2", "4", "16"],
         ["conv 3x3", "3", "1", "4", "24"]],
        widths=[20, 12, 12, 24, 32], bold_first=True)
    p("Two practical consequences. Downsampling grows the receptive field far "
      "faster than depth alone - after the second pool, each extra 3x3 "
      "convolution adds 8 pixels of context instead of 2. And if your task "
      "needs context wider than the final receptive field - a 200-pixel object "
      "seen by units with a 24-pixel view - no amount of training will fix it; "
      "the architecture is the constraint. Dilated convolutions, more "
      "downsampling, or attention are the three ways out.")


def ex_ch23():
    h2("Attention computed on three tokens")
    p("Nothing clarifies attention like doing it with small numbers. Three "
      "tokens, d_k = 2, with queries and keys chosen so the pattern is "
      "readable:")
    eq(["Q = K = [ 1  0 ]        V = [ 1  0 ]",
        "        [ 0  1 ]            [ 0  2 ]",
        "        [ 1  1 ]            [ 3  1 ]",
        "",
        "token 1 points along x, token 2 along y, token 3 along both."])
    h3("Step 1 - scores")
    eq(["Q K^T / sqrt(2) = [ 0.707   0.000   0.707 ]",
        "                  [ 0.000   0.707   0.707 ]",
        "                  [ 0.707   0.707   1.414 ]"])
    p("Row 3 is the interesting one: token 3 scores 1.414 against itself and "
      "0.707 against each of the others, because its direction overlaps both. "
      "Rows 1 and 2 each score 0 against the orthogonal token - orthogonal "
      "means 'unrelated', and the dot product says so numerically.")
    h3("Step 2 - softmax over each row")
    eq(["weights = [ 0.401   0.198   0.401 ]     <- token 1 attends to 1 and 3",
        "          [ 0.198   0.401   0.401 ]     <- token 2 attends to 2 and 3",
        "          [ 0.248   0.248   0.504 ]     <- token 3 attends mostly to 3"])
    h3("Step 3 - weighted sum of values")
    eq(["output row 1 = 0.401*[1,0] + 0.198*[0,2] + 0.401*[3,1] = [1.604, 0.797]",
        "output row 2 = 0.198*[1,0] + 0.401*[0,2] + 0.401*[3,1] = [1.401, 1.203]",
        "output row 3 = 0.248*[1,0] + 0.248*[0,2] + 0.504*[3,1] = [1.759, 1.000]"])
    p("Each token has been replaced by a blend of all tokens' values, weighted "
      "by relevance. That is the entire operation. Everything else in a "
      "Transformer - multiple heads, the projections W_Q/W_K/W_V, residuals, "
      "the feedforward block - is packaging around these three steps.")
    box("math", "Watching the sqrt(d_k) do its job",
        "Without the scaling, row 1's scores are 1, 0, 1 and the softmax gives "
        "0.422, 0.155, 0.422 - a bit sharper. With d_k = 2 the difference is "
        "small, but scores grow like sqrt(d_k): at d_k = 64 an unscaled logit "
        "gap of 8 instead of 1 turns the softmax nearly one-hot, its gradient "
        "to nearly zero, and training stalls at initialisation. The division is "
        "not cosmetic; it is what keeps the softmax differentiable at realistic "
        "widths.")

    h2("Why causal masking makes parallel training possible")
    diagram([
        "  Mask for a 4-token causal decoder (1 = allowed, . = -inf before softmax)",
        "",
        "            attends to:  t1  t2  t3  t4",
        "     query t1            1    .   .   .      token 1 sees only itself",
        "     query t2            1    1   .   .      token 2 sees 1 and 2",
        "     query t3            1    1   1   .",
        "     query t4            1    1   1   1",
        "",
        "  One forward pass computes the prediction for EVERY position at once,",
        "  each conditioned only on its own past. An RNN needs 4 sequential steps",
        "  to do the same thing. This is why Transformers train so much faster.",
    ], "Figure 23.2 - The causal mask: n training examples from one sequence, in "
       "one parallel pass.")
    p("At **inference** the advantage disappears - tokens must still be "
      "generated one at a time, each attending to all previous ones. That "
      "asymmetry (parallel training, sequential generation) is why the KV cache "
      "exists, why generation is memory-bandwidth bound, and why speculative "
      "decoding is worth the complexity. Chapter 24 follows the consequences.")

    h2("Sizing a Transformer block")
    p("For d_model = 512 with 8 heads and a 4x feedforward expansion:")
    tbl(["Component", "Shape", "Parameters"],
        [["W_Q, W_K, W_V", "3 x (512 x 512)", "786,432"],
         ["W_O (output projection)", "512 x 512", "262,144"],
         ["Feedforward up", "512 x 2048", "1,048,576"],
         ["Feedforward down", "2048 x 512", "1,048,576"],
         ["2 x LayerNorm", "2 x 2 x 512", "2,048"],
         ["Total per block", "-", "~3.15 M"],
         ["12 blocks", "-", "~37.7 M, plus embeddings"]],
        widths=[34, 30, 36], bold_first=True)
    p("Note the split: attention holds about a third of the parameters and the "
      "feedforward block about two thirds. That ratio holds across most model "
      "sizes, and it is why pruning and quantization work on the feedforward "
      "matrices give the largest returns (Chapters 28-29), and why "
      "mixture-of-experts replaces exactly that block.")


def ex_ch24():
    h2("What 'next token prediction' actually looks like")
    p("The training objective is unglamorous: given a prefix, predict the "
      "distribution over the next token. Every capability people find "
      "surprising is a side effect of doing this extremely well on a very large "
      "corpus.")
    diagram([
        "  text:      'The capital of France is Paris'",
        "  tokens:    [The] [ capital] [ of] [ France] [ is] [ Paris]",
        "",
        "  training example 1:  The                       -> ' capital'",
        "  training example 2:  The capital               -> ' of'",
        "  training example 3:  The capital of            -> ' France'",
        "  training example 4:  The capital of France     -> ' is'",
        "  training example 5:  The capital of France is  -> ' Paris'",
        "",
        "  All five are computed in ONE forward pass, thanks to causal masking.",
    ], "Figure 24.1 - One six-token sentence yields five supervised examples.")
    p("To predict ' Paris' reliably, a model must store a fact. To predict the "
      "closing bracket of a nested expression it must track state. To predict "
      "the next line of a proof it must do something that looks like reasoning. "
      "None of these were trained for directly; they are what minimising "
      "prediction error on a large enough corpus requires.")
    tbl(["Loss value", "Perplexity", "Interpretation"],
        [["11.0", "~60,000", "Untrained - uniform over the vocabulary"],
         ["6.9", "~1,000", "Learned token frequencies only"],
         ["4.0", "~55", "Basic grammar and local coherence"],
         ["3.0", "~20", "Fluent text, weak factuality"],
         ["2.0", "~7.4", "Strong modern model on general text"],
         ["1.5", "~4.5", "Approaching the noise floor of natural text"]],
        widths=[16, 18, 66], bold_first=True)
    p("Perplexity is just `exp(cross-entropy)` and reads as 'the model is as "
      "uncertain as if it were choosing uniformly among this many tokens'. "
      "Watch it during any language-model training run: it should start near "
      "the vocabulary size and fall fast.")

    h2("The KV cache, sized with real numbers")
    p("During generation the model re-reads every previous token's keys and "
      "values. Caching them avoids recomputation, but the cache is large:")
    eq(["bytes = 2 (K and V) * layers * kv_heads * head_dim * seq_len",
        "        * batch * bytes_per_value",
        "",
        "7B-class model, 32 layers, 32 heads, head_dim 128, 8k context, fp16:",
        "  2 * 32 * 32 * 128 * 8192 * 1 * 2 = 4.3 GB",
        "",
        "Same model with grouped-query attention, 8 KV heads:",
        "  2 * 32 *  8 * 128 * 8192 * 1 * 2 = 1.07 GB    (4x smaller)"])
    p("Compare that with the weights themselves: 7B parameters in fp16 is 14 GB. "
      "So a single 8k-context conversation adds nearly a third again on top of "
      "the model - and it scales linearly with both context length and batch "
      "size, which is why serving many users at long context is a memory "
      "problem before it is a compute problem. Grouped-query attention, paged "
      "attention and 8-bit KV quantization each attack this directly.")

    h2("Prompting, from worst to best")
    tbl(["Version", "Prompt", "Why it behaves better"],
        [["Bad", "'Summarise this.'", "No audience, no length, no format - the "
          "model guesses all three"],
         ["Better", "'Summarise the text below in 3 bullet points for a "
          "non-technical manager.'", "Audience, length and format are now "
          "constraints rather than guesses"],
         ["Good", "Add: 'Use only information from the text. If a fact is not "
          "stated, omit it.'", "Reduces fabrication by making abstention an "
          "explicit option"],
         ["Best", "Add: 'Return JSON: {summary: string[], omitted_topics: "
          "string[]}' plus 2 examples", "Machine-parseable, and the examples "
          "pin down the style far more precisely than adjectives can"]],
        widths=[12, 46, 42], bold_first=True)
    box("tip", "The two highest-value prompting habits",
        "First, give the model somewhere to put its uncertainty - an "
        "'unknown' field, permission to say the text does not answer the "
        "question, a confidence score. A model with no legitimate way to "
        "express doubt will invent an answer. Second, show rather than "
        "describe: two examples of the exact output you want beat two "
        "paragraphs describing it, because the examples constrain format, tone "
        "and depth simultaneously.")


def ex_ch28():
    h2("Quantizing eight real weights, by hand")
    p("Take these eight trained weights and quantize them to symmetric INT8 "
      "per-tensor. Every number below is computed, not illustrative.")
    eq(["w = [-0.82, -0.31, 0.05, 0.11, 0.47, 1.23, -1.05, 0.63]",
        "",
        "absmax = 1.23",
        "scale s = absmax / 127 = 1.23 / 127 = 0.009685",
        "q_i = round(w_i / s), clipped to [-127, 127]"])
    tbl(["Original w", "w / s", "Quantized q", "Dequantized q*s", "Error"],
        [["-0.82", "-84.67", "-85", "-0.8232", "-0.0032"],
         ["-0.31", "-32.01", "-32", "-0.3099", "+0.0001"],
         ["0.05", "5.16", "5", "0.0484", "-0.0016"],
         ["0.11", "11.36", "11", "0.1065", "-0.0035"],
         ["0.47", "48.53", "49", "0.4746", "+0.0046"],
         ["1.23", "127.00", "127", "1.2300", "0.0000"],
         ["-1.05", "-108.42", "-108", "-1.0460", "+0.0040"],
         ["0.63", "65.05", "65", "0.6295", "-0.0005"]],
        widths=[18, 16, 18, 24, 24], bold_first=True)
    eq(["Max absolute error = 0.0046      RMSE = 0.0028",
        "Storage: 8 floats (32 B) -> 8 int8 (8 B) + 1 float scale (4 B) = 12 B"])
    p("Two observations that generalise. The largest-magnitude weight is "
      "represented exactly, because it defines the scale - so the widest weight "
      "in a tensor gets perfect treatment while everything else is rounded, "
      "which is precisely why a single outlier ruins per-tensor quantization "
      "for the other 4,095 weights in its row. And the error is bounded by half "
      "a step, s/2 = 0.0048, uniformly across the range: quantization error is "
      "roughly uniform noise, not proportional error.")

    h2("What happens as the bits come off")
    tbl(["Bit width", "Levels", "Step size s", "RMSE on the weights above",
         "Rule of thumb"],
        [["8-bit", "255", "0.0097", "0.0028", "Essentially free; PTQ suffices"],
         ["4-bit", "15", "0.176", "0.0507", "18x worse; needs per-group scales "
          "or GPTQ/AWQ"],
         ["2-bit", "3", "1.23", "0.334", "120x worse; needs QAT and usually "
          "still hurts"]],
        widths=[14, 12, 16, 26, 32], bold_first=True)
    p("Error grows roughly as 2^(-b), so each bit removed doubles the noise. "
      "That is the whole trade-off curve, and it explains why INT8 is nearly "
      "free while INT4 needs help and INT2 needs a rethink of the training "
      "itself.")

    h2("Asymmetric quantization for activations, worked")
    p("Post-ReLU activations are non-negative, so a symmetric scheme wastes "
      "half its codes on values that never occur. With a calibrated range of "
      "[0, 4.0] into uint8:")
    eq(["s = (4.0 - 0.0) / 255 = 0.015686        z = 0  (since r_min = 0)",
        "",
        "a = 0.0  -> q = 0    -> 0.0000",
        "a = 0.4  -> q = 26   -> 0.4078",
        "a = 1.2  -> q = 76   -> 1.1922",
        "a = 2.8  -> q = 178  -> 2.7922",
        "a = 3.9  -> q = 249  -> 3.9059"])
    box("key", "Why exact zero must map to an exact code",
        "Here z = 0, so the real value 0.0 maps to the integer 0 with no error "
        "at all. That is essential: padding, masking and ReLU all produce exact "
        "zeros in bulk, and if 0.0 quantized to, say, 0.008 instead, every "
        "padded position in every sequence would contribute a small systematic "
        "bias that accumulates across layers. The zero-point exists to make "
        "this impossible.")

    h2("The whole INT8 layer, arithmetic included")
    eq(["Real:      y = SUM_i w_i x_i",
        "Quantized: w_i = s_w q_w_i,   x_i = s_x (q_x_i - z_x)",
        "",
        "y = s_w s_x [ SUM_i q_w_i q_x_i  -  z_x SUM_i q_w_i ]",
        "             \\___ int8 x int8 -> int32 ___/  \\__ constant __/",
        "",
        "The bracketed sum is pure integer arithmetic. The second term depends",
        "only on the weights, so it is precomputed once and folded into the",
        "bias. The float scales multiply the int32 accumulator once at the end -",
        "and even that is usually done as a fixed-point multiply-and-shift, so",
        "a device with no floating-point unit can run the layer end to end."])
    p("This is the reason INT8 inference is fast rather than merely small: the "
      "inner loop is integer multiply-accumulate, which is what DSPs, NPUs and "
      "microcontroller SIMD units are built for, and which costs roughly an "
      "order of magnitude less energy per operation than the float equivalent.")


def ex_ch29():
    h2("Pruning a small layer, weight by weight")
    p("Take a 4x4 weight matrix and apply 50% magnitude pruning three ways. The "
      "difference between the three is the entire practical content of this "
      "chapter.")
    eq(["W = [  0.90  -0.05   0.60   0.02 ]      row norms (L2):",
        "    [  0.03   0.01  -0.02   0.04 ]        row 1: 1.08",
        "    [ -0.70   0.80   0.10  -0.50 ]        row 2: 0.06",
        "    [  0.20  -0.15   0.05   0.30 ]        row 3: 1.19",
        "                                          row 4: 0.39"])
    tbl(["Scheme", "What is removed", "Result", "Speedup on a dense kernel"],
        [["Unstructured, 50%", "The 8 smallest |w| anywhere",
          "Scattered zeros; W keeps its 4x4 shape", "None - the kernel still "
          "multiplies 16 numbers"],
         ["2:4 semi-structured", "The 2 smallest of every 4 consecutive weights",
          "Exactly 2 non-zeros per group of 4", "Up to ~2x on sparse tensor "
          "cores"],
         ["Structured (rows), 50%", "The 2 rows with the smallest norm - rows 2 "
          "and 4", "A genuine 2x4 matrix", "2x everywhere, on any hardware"]],
        widths=[20, 32, 26, 22], bold_first=True)
    p("Look at what structured pruning chose. Row 2 has every weight near zero: "
      "removing it costs almost nothing, and it removes a whole output "
      "channel - the next layer loses an input, the tensor genuinely shrinks, "
      "and every runtime on earth is faster as a result. Row 4 is a real "
      "sacrifice: its norm is 0.39, so some signal is lost. That is the "
      "structured/unstructured trade in miniature - unstructured pruning "
      "removes exactly the least useful weights but changes nothing about the "
      "computation, while structured pruning removes some useful weights and "
      "actually makes the model smaller.")
    box("warn", "The reported-sparsity trap",
        "A paper or a blog post that says '95% of weights removed, 0.3% "
        "accuracy lost' and shows no latency measurement has almost certainly "
        "measured nothing that a deployment would feel. Ask three questions: "
        "which granularity, which runtime, and what was the measured "
        "milliseconds-per-inference before and after on the target device. If "
        "the answer to the third is missing, the compression is theoretical.")

    h2("How far can you actually prune?")
    tbl(["Sparsity", "Typical accuracy effect (with fine-tuning)", "Notes"],
        [["0-50%", "None measurable on an over-parameterised model",
          "Essentially free; the network was carrying redundancy"],
         ["50-80%", "0-1 point", "Needs gradual pruning plus fine-tuning"],
         ["80-95%", "1-4 points", "Needs iterative pruning; small layers must be "
          "protected"],
         [">95%", "Large and erratic", "Only for heavily over-parameterised "
          "models; consider a smaller architecture instead"]],
        widths=[14, 40, 46], bold_first=True)
    box("tip", "Prune the right layers",
        "Never prune the first and last layers at the same rate as the middle. "
        "The first layer has few parameters but sees the raw input, and the "
        "last maps to the classes - damage there is disproportionate, while the "
        "savings are trivial because both are small. Global magnitude pruning "
        "with no exclusions will happily gut them, which is the most common "
        "reason a pruning run collapses.")

    h2("Compression stacked, with the numbers")
    tbl(["Stage", "Size", "Latency", "Accuracy", "What changed"],
        [["Dense FP32 baseline", "14.0 MB", "100 ms", "94.2%", "-"],
         ["+ 50% channel pruning", "7.2 MB", "58 ms", "93.6%", "Genuinely "
          "smaller tensors"],
         ["+ INT8 quantization", "1.9 MB", "24 ms", "92.7%", "4x memory, integer "
          "kernels"],
         ["+ distillation from the dense teacher", "1.9 MB", "24 ms", "93.9%",
          "Same model, better weights"]],
        widths=[34, 14, 16, 16, 20], bold_first=True)
    p("Read the last row carefully: distillation changed nothing about the "
      "model's size or speed, and recovered most of the accuracy lost to the "
      "first two stages. That is the standard modern recipe - compress "
      "aggressively, then use the uncompressed model as a teacher to repair the "
      "damage. It is almost always better than compressing less.")


def ex_ch32():
    h2("A gridworld you can solve on paper")
    p("Reinforcement learning becomes concrete on a four-state corridor. States "
      "S1..S4, actions left and right, reward +1 for reaching S4 and 0 "
      "elsewhere, gamma = 0.9.")
    diagram([
        "     [S1] <---> [S2] <---> [S3] <---> [S4 goal, +1]",
        "",
        "  Optimal values, working backwards from the goal:",
        "     V(S4) = 1.0        (terminal)",
        "     V(S3) = 0 + 0.9 * 1.0   = 0.90",
        "     V(S2) = 0 + 0.9 * 0.90  = 0.81",
        "     V(S1) = 0 + 0.9 * 0.81  = 0.729",
    ], "Figure 32.1 - Value propagates backwards from reward, decaying by gamma "
       "per step.")
    p("This tiny example shows the three ideas that carry all the way to "
      "AlphaZero. Value is **discounted distance to reward**: gamma = 0.9 means "
      "a reward three steps away is worth 0.729 now, so the agent prefers "
      "shorter paths without being told to. Value **propagates backwards** one "
      "step per update, which is why sparse-reward problems need so many "
      "episodes - the signal has to crawl back from the goal. And a **policy "
      "falls out of the values for free**: in each state, move to the "
      "neighbouring state with the higher value.")
    tbl(["gamma", "Value of a reward 10 steps away", "Behaviour"],
        [["0.5", "0.001", "Extremely myopic - ignores anything beyond a few "
          "steps"],
         ["0.9", "0.35", "Balanced; the common default"],
         ["0.99", "0.90", "Far-sighted; needed for long tasks, but slows "
          "learning and increases variance"],
         ["1.0", "1.00", "No discounting - only valid for episodes guaranteed to "
          "terminate"]],
        widths=[12, 32, 56], bold_first=True)

    h2("Why reinforcement learning is harder than supervised learning")
    tbl(["Difficulty", "Supervised learning", "Reinforcement learning"],
        [["Where the data comes from", "A fixed dataset, independent of the "
          "model", "The agent's own behaviour - a bad policy collects bad data"],
         ["Feedback", "The correct answer, for every sample",
          "A scalar reward, often delayed by hundreds of steps"],
         ["Credit assignment", "Immediate: this prediction, this loss",
          "Which of the last 200 actions caused the reward?"],
         ["Stationarity", "The target never moves",
          "The target moves - the value function bootstraps from itself"],
         ["Evaluation", "Held-out test set", "You must run the policy to know "
          "how good it is, and running it may be expensive or unsafe"],
         ["Failure mode", "Overfitting", "Collapse, reward hacking, or silently "
          "converging to a mediocre policy"]],
        widths=[22, 34, 44], bold_first=True)
    box("tip", "The order to try things in",
        "If you can log what a good decision-maker did, start with behaviour "
        "cloning - it is plain supervised learning and it works. If decisions "
        "do not affect future state, use a contextual bandit. Only when actions "
        "genuinely change the world you observe next is full reinforcement "
        "learning the right tool, and even then start with PPO or SAC and a "
        "carefully shaped reward rather than an exotic algorithm.")




def ch_project():
    chapter("A Complete Project, Step by Step")
    p("Every previous chapter taught a piece. This one puts them in order. It "
      "is a single continuous procedure - thirteen stages from an unclear "
      "business request to a monitored production model - written so that you "
      "can follow it literally on your own data. Two full worked projects "
      "close the chapter: a tabular classifier and a deep-learning sensor "
      "model, each with the code that actually runs.")
    diagram([
        "  0. FRAME      what is predicted, what a mistake costs, what 'done' means",
        "  1. SET UP     repository, environment, seeds, experiment log",
        "  2. DATA       collect, document, and split BEFORE looking",
        "  3. EXPLORE    on the training split only",
        "  4. BASELINE   trivial, then simple - never skip this",
        "  5. PIPELINE   leak-free preprocessing as one object",
        "  6. MODEL      classical track first, deep track if justified",
        "  7. TUNE       search the few hyperparameters that matter",
        "  8. EVALUATE   slices, calibration, error analysis, confidence intervals",
        "  9. COMPRESS   quantize / prune / distil to the deployment budget",
        " 10. PACKAGE    freeze artefacts, write the inference path, test it",
        " 11. DEPLOY     shadow, canary, ramp, with rollback ready",
        " 12. MONITOR    drift, performance, cost - and retrain on a trigger",
    ], "Figure 36.1 - The thirteen stages. Work them in order; the expensive "
       "mistakes come from skipping forward.")

    h2("Stage 0 - Frame the problem before touching data")
    p("The most costly errors in machine learning are made before any code is "
      "written, and they all have the same shape: building a model that works "
      "but answers the wrong question. Write a one-page charter and get it "
      "agreed. If you cannot fill in every row below, you are not ready to "
      "start.")
    tbl(["Question", "Why it decides everything downstream", "Example answer"],
        [["What exactly is predicted, for what entity, at what moment?",
          "Defines the unit of analysis and the exact timestamp at which "
          "features must be available - i.e. what counts as leakage",
          "For each transaction, at authorisation time, the probability it is "
          "fraudulent"],
         ["What decision does the prediction drive?",
          "A number nobody acts on has no value; the action determines the "
          "metric", "Send to a human analyst, or auto-decline"],
         ["What does each kind of error cost?",
          "Sets the metric and the decision threshold (Chapter 13)",
          "False positive: 20 EUR of analyst time. False negative: ~500 EUR "
          "average loss"],
         ["What is the current baseline?",
          "You must beat something that already exists, or the project has no "
          "measurable value", "A hand-written rule set catching 55% of fraud "
          "with 8% precision"],
         ["What would make this a success?",
          "The go/no-go number, agreed in advance, in business units",
          "Same recall at 3x the precision, evaluated on next quarter's data"],
         ["What are the constraints?",
          "Latency, memory, privacy, regulation, explainability - each one "
          "removes options", "Under 50 ms at p99; must run on-premise; the "
          "reason for a decline must be explainable"],
         ["Who owns it after launch?",
          "An unowned model rots within months", "The risk team, with a monthly "
          "review"]],
        widths=[24, 40, 36], bold_first=True)
    box("warn", "Three framings that sink projects",
        "PREDICTING SOMETHING NOBODY CAN ACT ON: a churn score delivered the "
        "day the customer leaves. THE TARGET IS A PROXY THAT DRIFTS FROM THE "
        "GOAL: optimising click-through when the goal is satisfaction. THE "
        "LABEL DOES NOT EXIST YET: 'predict which customers will love the new "
        "product' when the product has never shipped. In all three cases the "
        "modelling will succeed and the project will fail.")

    h2("Stage 1 - Set up the repository and the environment")
    p("Do this on day one, not after the first promising result. The cost is "
      "thirty minutes; the cost of not doing it is being unable to reproduce "
      "the result that mattered.")
    code([
        "project/",
        "|-- data/",
        "|   |-- raw/            # immutable. NEVER write here after download",
        "|   |-- interim/        # intermediate, reproducible from raw",
        "|   +-- processed/      # model-ready tables/tensors",
        "|-- notebooks/          # exploration only; nothing importable lives here",
        "|-- src/",
        "|   |-- data.py         # loading, splitting, validation",
        "|   |-- features.py     # the preprocessing pipeline (one object)",
        "|   |-- train.py        # takes a config, writes a run directory",
        "|   |-- evaluate.py     # metrics, slices, plots",
        "|   +-- serve.py        # the inference path used in production",
        "|-- configs/            # one YAML per experiment, version-controlled",
        "|-- models/             # saved artefacts, one folder per run id",
        "|-- reports/            # figures, model cards, results tables",
        "|-- tests/              # data validation + behavioural tests",
        "|-- requirements.txt    # pinned versions, not ranges",
        "+-- README.md           # how to reproduce, in five commands or fewer",
    ], "Listing 36.1 - A layout that scales from a notebook to a team.")
    code([
        "# src/utils.py - the reproducibility preamble every run should call",
        "import os, random, json, subprocess, datetime",
        "import numpy as np, torch",
        "",
        "def set_seed(seed: int = 42):",
        "    random.seed(seed); np.random.seed(seed)",
        "    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)",
        "    os.environ['PYTHONHASHSEED'] = str(seed)",
        "    # bit-exactness costs speed; enable only when you need it",
        "    # torch.use_deterministic_algorithms(True)",
        "",
        "def run_metadata(cfg: dict) -> dict:",
        "    return {",
        "        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),",
        "        'git_commit': subprocess.check_output(",
        "            ['git', 'rev-parse', 'HEAD']).decode().strip(),",
        "        'git_dirty': bool(subprocess.check_output(",
        "            ['git', 'status', '--porcelain']).decode().strip()),",
        "        'config': cfg,",
        "        'data_hash': cfg.get('data_hash'),",
        "    }",
        "",
        "# At the end of training, write this next to the weights:",
        "# json.dump(run_metadata(cfg), open(run_dir / 'meta.json', 'w'), indent=2)",
    ], "Listing 36.2 - Seeds, commit hash and config saved with every run. A "
       "checkpoint whose hyperparameters are unknown is nearly worthless.")
    checklist("Day-one setup", [
        "Git repository initialised, with data/ in .gitignore.",
        "Virtual environment with pinned versions; the exact Python version "
        "recorded.",
        "A `make train` or `python -m src.train --config configs/baseline.yaml` "
        "entry point that runs end to end on a 1% sample in under a minute.",
        "An experiment log - MLflow, Weights and Biases, or a CSV that every "
        "run appends to.",
        "The README explains how to reproduce the current best result from a "
        "clean checkout.",
    ])

    h2("Stage 2 - Get the data, document it, and split it first")
    p("The split comes before exploration, not after. Every look at the test "
      "set spends a little of its value, and the first look is the one that "
      "biases every later decision.")
    bul([
        "**Choose the split axis from the deployment reality.** If the model "
        "will see future data, split by time. If it will see new users, "
        "patients or devices, split by that entity. Random splitting is "
        "correct only when rows are genuinely independent - which, in practice, "
        "is rarer than it looks.",
        "**Freeze the test set.** Write it to disk with a hash, and do not "
        "regenerate it when the data is refreshed - or your numbers stop being "
        "comparable across weeks.",
        "**Record provenance:** where each field came from, when it was "
        "collected, its licence and consent basis, and known gaps in coverage.",
        "**Validate the schema automatically** so that a silent upstream change "
        "fails the pipeline instead of quietly degrading the model.",
    ], ordered=True)
    code([
        "# src/data.py",
        "import hashlib, pandas as pd",
        "from sklearn.model_selection import StratifiedGroupKFold, train_test_split",
        "",
        "def load_raw(path):",
        "    df = pd.read_parquet(path)",
        "    h = hashlib.sha256(pd.util.hash_pandas_object(df).values).hexdigest()",
        "    return df, h[:12]                  # goes into the run metadata",
        "",
        "def split_by_time(df, ts_col, val_frac=0.15, test_frac=0.15):",
        "    df = df.sort_values(ts_col)",
        "    n = len(df); i_te = int(n * (1 - test_frac))",
        "    i_va = int(i_te * (1 - val_frac))",
        "    return df.iloc[:i_va], df.iloc[i_va:i_te], df.iloc[i_te:]",
        "",
        "def split_by_group(df, group_col, y_col, seed=42):",
        "    # keeps every row of one subject/user/device on one side only",
        "    g = df[group_col].unique()",
        "    tr_g, te_g = train_test_split(g, test_size=0.2, random_state=seed)",
        "    tr_g, va_g = train_test_split(tr_g, test_size=0.2, random_state=seed)",
        "    m = lambda ids: df[df[group_col].isin(ids)]",
        "    return m(tr_g), m(va_g), m(te_g)",
        "",
        "def assert_no_overlap(tr, va, te, key):",
        "    a, b, c = set(tr[key]), set(va[key]), set(te[key])",
        "    assert not (a & b) and not (a & c) and not (b & c), 'split leak!'",
    ], "Listing 36.3 - The three splits you will actually need, plus the "
       "assertion that catches the mistake.")
    box("key", "The leakage audit, one question per feature",
        "Go through every column and ask: __at the exact moment I must make "
        "this prediction, would this value be known, and would it have this "
        "value?__ A column such as `total_amount_paid` fails for a default-"
        "prediction model because it is filled in afterwards. `account_status` "
        "fails if it is overwritten to 'closed' when fraud is confirmed. This "
        "audit takes an hour and routinely saves a project.")

    h2("Stage 3 - Explore, on the training split only")
    checklist("The exploration pass that pays for itself", [
        "Shape, dtypes, memory. Does the row count match what you were told?",
        "Target distribution. What is the positive rate, or the shape of y?",
        "Missing-value rate per column; is missingness correlated with the "
        "target?",
        "Cardinality of every categorical; are there near-duplicate levels "
        "('watch_v2' vs 'Watch V2')?",
        "Numeric ranges and impossible values; physical or business "
        "plausibility.",
        "Duplicates, exact and near.",
        "Time coverage: gaps, seasonality, a regime change halfway through.",
        "Correlations with the target - and be suspicious of anything above "
        "0.95, which usually means leakage rather than luck.",
        "Look at 50 raw samples with your own eyes. Every single time.",
    ])
    box("warn", "The suspiciously good feature",
        "A single feature with an AUC of 0.99 on its own is almost never a "
        "discovery; it is almost always leakage, a duplicate of the label under "
        "another name, or an artefact of how the dataset was assembled. Treat "
        "it as a bug report and go find the cause before celebrating.")

    h2("Stage 4 - Establish baselines before modelling")
    p("You need two numbers before any real model: what you get for free, and "
      "what you get for very little. Without them you cannot tell whether a "
      "later result is good.")
    tbl(["Baseline", "Classification", "Regression", "Why it matters"],
        [["Trivial", "Always predict the majority class",
          "Always predict the mean or median",
          "Any metric must beat this or the model has learned nothing"],
         ["Naive domain rule", "The existing hand-written rules",
          "Last value carried forward",
          "This is what you are actually replacing"],
         ["Simple model", "Logistic regression on the raw columns",
          "Ridge regression", "Fast, interpretable, and surprisingly hard to "
          "beat; it also smoke-tests the whole pipeline"],
         ["Strong classical", "Gradient boosting with defaults",
          "Gradient boosting with defaults", "On tabular data this is often the "
          "final model; anything fancier must beat it"]],
        widths=[16, 26, 24, 34], bold_first=True)
    code([
        "from sklearn.dummy import DummyClassifier",
        "from sklearn.linear_model import LogisticRegression",
        "from sklearn.ensemble import HistGradientBoostingClassifier",
        "from sklearn.metrics import average_precision_score",
        "",
        "for name, model in [",
        "    ('trivial',  DummyClassifier(strategy='prior')),",
        "    ('logistic', make_pipeline(pre, LogisticRegression(max_iter=2000))),",
        "    ('gbdt',     make_pipeline(pre, HistGradientBoostingClassifier())),",
        "]:",
        "    model.fit(X_tr, y_tr)",
        "    ap = average_precision_score(y_va, model.predict_proba(X_va)[:, 1])",
        "    print(f'{name:9s} val AP = {ap:.4f}')",
        "",
        "# Typical output on an imbalanced problem:",
        "#   trivial   val AP = 0.0310      <- this is the floor (the positive rate)",
        "#   logistic  val AP = 0.2840",
        "#   gbdt      val AP = 0.4120      <- the number to beat from now on",
    ], "Listing 36.4 - Three baselines in fifteen lines. Run this on day two.")

    h2("Stage 5 - Build the preprocessing pipeline as one object")
    p("Everything data-dependent - imputation, scaling, encoding, feature "
      "selection, resampling - must live inside a single fitted object that is "
      "refitted on each training fold and saved with the model. This is not "
      "style; it is the structural defence against the leakage of Chapter 3 "
      "and against training/serving skew in Chapter 34.")
    code([
        "# src/features.py",
        "from sklearn.pipeline import Pipeline",
        "from sklearn.compose import ColumnTransformer",
        "from sklearn.impute import SimpleImputer",
        "from sklearn.preprocessing import StandardScaler, OneHotEncoder",
        "",
        "NUM = ['amount', 'age_days', 'n_prior_tx', 'hour_sin', 'hour_cos']",
        "CAT = ['country', 'device', 'merchant_category']",
        "",
        "def build_preprocessor():",
        "    num = Pipeline([",
        "        ('imp', SimpleImputer(strategy='median', add_indicator=True)),",
        "        ('sc',  StandardScaler()),",
        "    ])",
        "    cat = Pipeline([",
        "        ('imp', SimpleImputer(strategy='constant', fill_value='__NA__')),",
        "        ('oh',  OneHotEncoder(handle_unknown='ignore', min_frequency=20)),",
        "    ])",
        "    return ColumnTransformer([('num', num, NUM), ('cat', cat, CAT)],",
        "                             remainder='drop')   # be explicit, always",
        "",
        "def add_derived(df):",
        "    # derived features computed from ONE row's own past only",
        "    df = df.copy()",
        "    df['hour_sin'] = np.sin(2*np.pi*df['ts'].dt.hour/24)",
        "    df['hour_cos'] = np.cos(2*np.pi*df['ts'].dt.hour/24)",
        "    df['amount_per_prior'] = df['amount'] / (df['n_prior_tx'] + 1)",
        "    return df",
    ], "Listing 36.5 - One preprocessor object, used identically in training, "
       "cross-validation and serving.")
    box("tip", "`remainder='drop'` is a safety feature",
        "Listing every column you intend to use, and dropping the rest, means "
        "that a new column appearing upstream cannot silently enter the model - "
        "and that an ID column cannot accidentally become a feature. The "
        "default of silently passing everything through is how identifiers end "
        "up as predictors.")

    h2("Stage 6 - Model iteration: two tracks")
    p("Choose the track from the data, not from ambition. On tabular data with "
      "fewer than a million rows, the classical track usually wins and always "
      "wins on effort per point of accuracy. On perceptual data - images, "
      "audio, text, raw waveforms - the deep track wins decisively, and you "
      "should start from pretrained weights.")
    tbl(["Signal", "Take the classical track", "Take the deep track"],
        [["Data type", "Tabular, mixed numeric/categorical",
          "Images, audio, text, raw sensor streams"],
         ["Rows", "10^3 - 10^6", "10^4+ from scratch, or 10^2+ with a "
          "pretrained backbone"],
         ["Feature semantics", "Meaningful named columns",
          "Raw signal where useful features are unknown"],
         ["Constraints", "Explainability, tiny training budget, CPU-only",
          "GPU available, latency budget allows a network"],
         ["First model", "HistGradientBoosting / LightGBM defaults",
          "A pretrained backbone plus a new head"]],
        widths=[16, 42, 42], bold_first=True)
    h3("The iteration loop, one change at a time")
    bul([
        "Form a hypothesis: 'adding 7-day rolling aggregates will help because "
        "fraud is bursty'.",
        "Change exactly one thing. Two changes in one run teach you nothing "
        "about either.",
        "Evaluate on the validation split (or by cross-validation), with the "
        "same seed policy as your baseline.",
        "Record the result in the experiment log, including failures - the log "
        "of what did not work is what stops you retrying it in six weeks.",
        "Keep the change only if it beats the current best by more than the "
        "seed-to-seed noise you measured in stage 4.",
    ], ordered=True)
    box("key", "The order that finds accuracy fastest",
        "1. Fix data problems - label noise, leakage, wrong splits. Nothing "
        "else matters until these are clean. 2. Add features (classical) or "
        "improve augmentation and the backbone (deep). 3. Tune the "
        "hyperparameters that actually move the metric. 4. Ensemble. Most "
        "people run this list backwards and spend a week on step 4 for a "
        "quarter of the gain step 1 would have given them.")

    h2("Stage 7 - Tune only what matters")
    tbl(["Model", "Tune first", "Tune next", "Leave alone"],
        [["Gradient boosting", "learning_rate + n_estimators (with early "
          "stopping)", "num_leaves / max_depth, min_samples_leaf",
          "Everything else, usually"],
         ["Random forest", "max_features", "min_samples_leaf, n_estimators",
          "Criterion"],
         ["Linear / logistic", "C or alpha (log scale)", "Penalty type",
          "Solver, unless it fails to converge"],
         ["Neural network", "learning rate + schedule", "Batch size, weight "
          "decay, augmentation strength, width/depth", "Optimiser betas, "
          "epsilon, activation function"]],
        widths=[18, 30, 32, 20], bold_first=True)
    p("Use random or Bayesian search over log-uniform ranges (Chapter 7), give "
      "the search a fixed budget decided in advance, and always include the "
      "default configuration as one of the trials - it wins more often than "
      "people expect, and if it does, you have learned that tuning is not your "
      "bottleneck.")

    h2("Stage 8 - Evaluate like a sceptic")
    checklist("Before you claim a result", [
        "Metric matches the decision and its costs, chosen in stage 0 - not "
        "accuracy by default.",
        "Compared against the trivial and the existing baseline, on the same "
        "split.",
        "Averaged over 3-5 seeds, with the spread reported.",
        "Bootstrap confidence interval on the test metric.",
        "Per-slice metrics: by class, by subgroup, by data source, by time "
        "period, by difficulty.",
        "Calibration checked, and fixed with temperature or isotonic scaling if "
        "the probability is used downstream.",
        "Decision threshold chosen on validation using the cost matrix, not "
        "left at 0.5.",
        "Error analysis: read 50 of the worst errors and categorise them. This "
        "is where the next feature idea comes from.",
        "Test set touched exactly once, at the very end.",
    ])
    code([
        "# src/evaluate.py - the error-analysis step people skip",
        "import numpy as np, pandas as pd",
        "",
        "proba = model.predict_proba(X_va)[:, 1]",
        "err = pd.DataFrame({'y': y_va, 'p': proba}).assign(",
        "    loss=lambda d: -(d.y*np.log(d.p+1e-9) + (1-d.y)*np.log(1-d.p+1e-9)))",
        "worst = err.sort_values('loss', ascending=False).head(50).index",
        "",
        "review = X_va.loc[worst].copy()",
        "review['true'] = y_va.loc[worst]; review['pred'] = proba[worst]",
        "review.to_csv('reports/worst_50.csv')",
        "# Now READ it. Group the failures into 3-5 named categories and count",
        "# them. Each category is either a data fix, a feature idea, or a",
        "# genuine limit of the problem - and you cannot tell which from a",
        "# metric alone.",
    ], "Listing 36.6 - Error analysis. Half an hour here beats a day of tuning.")

    h2("Stage 9 - Compress to the deployment budget")
    p("If the model runs in the cloud with generous latency, skip this stage. "
      "If it runs on a phone, a vehicle, a wearable or a microcontroller, this "
      "is where Chapters 28-31 are applied, in this order:")
    tbl(["Step", "Action", "Typical result", "Check afterwards"],
        [["1", "Measure the dense baseline ON THE TARGET DEVICE",
          "The only latency number that means anything", "p50 and p99, not the "
          "mean"],
         ["2", "Distil into a smaller architecture if the gap allows",
          "2-10x smaller at a small accuracy cost", "Accuracy against the "
          "teacher"],
         ["3", "Structured pruning of channels, heads or blocks",
          "30-50% fewer parameters, real speedup", "Rebuild the model with "
          "smaller layers, then re-measure"],
         ["4", "INT8 post-training quantization with a calibration set",
          "4x smaller, 2-4x faster", "Evaluate with the target RUNTIME, not the "
          "simulator"],
         ["5", "Quantization-aware fine-tuning if PTQ lost too much",
          "Recovers most of the gap", "Per-class accuracy, not just the average"],
         ["6", "Re-measure everything on the device",
          "The number you report", "Memory, energy, and thermal behaviour under "
          "sustained load"]],
        widths=[7, 33, 30, 30], bold_first=True)
    box("warn", "Compression damage is not uniform",
        "Quantization and pruning almost always hurt rare classes and unusual "
        "inputs more than the average. A model that loses 0.4 points overall "
        "can easily lose 6 points on the smallest class. Always compare the "
        "per-slice table before and after, and treat a large per-slice drop as "
        "a blocker even when the headline number looks fine.")

    h2("Stage 10 - Package the artefact")
    p("What ships is not the notebook. It is a directory containing everything "
      "needed to reproduce a prediction, and an inference function that is "
      "tested.")
    code([
        "models/2024-11-03_gbdt_v7/",
        "|-- model.joblib          # the FULL pipeline: preprocessing + estimator",
        "|-- meta.json             # git commit, config, data hash, seeds",
        "|-- metrics.json          # test metrics, per slice, with CIs",
        "|-- threshold.json        # the operating point and how it was chosen",
        "|-- feature_schema.json   # names, dtypes, allowed ranges",
        "+-- model_card.md         # intended use, data, limits, ethics",
    ], "Listing 36.7 - A deployable run directory.")
    code([
        "# src/serve.py - the one code path production uses",
        "import joblib, json, numpy as np, pandas as pd",
        "",
        "class Predictor:",
        "    def __init__(self, run_dir):",
        "        self.pipe = joblib.load(f'{run_dir}/model.joblib')",
        "        self.schema = json.load(open(f'{run_dir}/feature_schema.json'))",
        "        self.thr = json.load(open(f'{run_dir}/threshold.json'))['value']",
        "",
        "    def _validate(self, df):",
        "        missing = set(self.schema['columns']) - set(df.columns)",
        "        if missing:",
        "            raise ValueError(f'missing columns: {sorted(missing)}')",
        "        for c, (lo, hi) in self.schema.get('ranges', {}).items():",
        "            bad = df[c].dropna().between(lo, hi).eq(False).sum()",
        "            if bad:",
        "                raise ValueError(f'{bad} out-of-range values in {c}')",
        "",
        "    def predict(self, records: list[dict]) -> list[dict]:",
        "        df = add_derived(pd.DataFrame(records))",
        "        self._validate(df)",
        "        p = self.pipe.predict_proba(df)[:, 1]",
        "        return [{'score': float(s), 'decision': bool(s >= self.thr)}",
        "                for s in p]",
    ], "Listing 36.8 - Inference with input validation. The validation is not "
       "optional: silent schema drift is the most common production failure.")
    code([
        "# tests/test_serve.py",
        "def test_known_case():",
        "    out = predictor.predict([GOLDEN_RECORD])[0]",
        "    assert abs(out['score'] - 0.8123) < 1e-4      # regression guard",
        "",
        "def test_invariance():",
        "    a = predictor.predict([REC])[0]['score']",
        "    b = predictor.predict([{**REC, 'customer_name': 'different'}])[0]['score']",
        "    assert a == b            # an irrelevant field must not move the score",
        "",
        "def test_direction():",
        "    low  = predictor.predict([{**REC, 'amount': 10}])[0]['score']",
        "    high = predictor.predict([{**REC, 'amount': 10_000}])[0]['score']",
        "    assert high > low        # domain knowledge, encoded as a test",
        "",
        "def test_rejects_bad_input():",
        "    with pytest.raises(ValueError):",
        "        predictor.predict([{**REC, 'amount': -5}])",
    ], "Listing 36.9 - Behavioural tests. These catch the failures that unit "
       "tests on training code never will.")

    h2("Stage 11 - Deploy carefully")
    bul([
        "**Shadow:** run the new model on live traffic, log its output, act on "
        "nothing. Compare its score distribution against the offline "
        "distribution - a mismatch here means training/serving skew, and it is "
        "common.",
        "**Canary:** route 1-5% of traffic to it, watch the operational and "
        "business metrics for a defined period.",
        "**Ramp:** 25%, 50%, 100%, with a documented rollback trigger at each "
        "step.",
        "**Keep the previous model warm** and rehearse the rollback before you "
        "need it.",
        "**A/B test against the business metric**, not the offline metric - "
        "they disagree more often than they agree.",
    ])

    h2("Stage 12 - Monitor, and plan for decay")
    p("A deployed model is a photograph of the past. Assume it will degrade "
      "and instrument for it from the first day.")
    tbl(["Signal", "How to measure", "Alert when"],
        [["Input drift", "PSI or KS per feature against a training reference",
          "PSI > 0.2 on an important feature"],
         ["Prediction drift", "Score distribution over time",
          "Mean score moves beyond its historical band"],
         ["Performance", "Metrics on delayed labels",
          "Below the agreed floor for two consecutive periods"],
         ["Data health", "Null rates, schema, cardinality",
          "Any schema violation - fail loudly, never silently impute"],
         ["Operational", "Latency p99, error rate, cost per 1k predictions",
          "Breaches the SLA"],
         ["Business", "The metric from stage 0", "Any sustained decline"]],
        widths=[18, 44, 38], bold_first=True)
    p("Decide the retraining policy in advance: scheduled (simplest and usually "
      "adequate), or triggered by drift. Whichever you choose, a retrained "
      "model is promoted only after beating the incumbent on a frozen "
      "comparison set - automatic training is fine, automatic promotion is not.")

    h2("Worked project A - a tabular classifier, end to end")
    p("Fraud detection on transactions: 500,000 rows, 3% positive, 40 columns, "
      "a 50 ms latency budget, and a requirement that any decline be "
      "explainable. Here is the whole project as one script, with the "
      "decisions annotated.")
    code([
        "# 0. FRAME  -> metric: average precision; threshold from the cost matrix",
        "#             (FP = 20 EUR analyst time, FN = 500 EUR loss)",
        "# 2. SPLIT  -> by TIME: fraud patterns evolve, so future data is the",
        "#             honest test. Never random-split transactional data.",
        "df, data_hash = load_raw('data/raw/tx.parquet')",
        "df = add_derived(df)",
        "tr, va, te = split_by_time(df, 'ts')",
        "X_tr, y_tr = tr.drop(columns=['is_fraud']), tr['is_fraud']",
        "X_va, y_va = va.drop(columns=['is_fraud']), va['is_fraud']",
        "",
        "# 4. BASELINES",
        "#    trivial AP = 0.031   logistic AP = 0.284   gbdt AP = 0.412",
        "",
        "# 5-6. PIPELINE + MODEL",
        "import lightgbm as lgb",
        "pre = build_preprocessor()",
        "Xt, Xv = pre.fit_transform(X_tr), pre.transform(X_va)",
        "",
        "model = lgb.LGBMClassifier(",
        "    objective='binary', n_estimators=5000, learning_rate=0.03,",
        "    num_leaves=63, min_child_samples=50, subsample=0.8,",
        "    colsample_bytree=0.8, reg_lambda=1.0,",
        "    scale_pos_weight=1.0)          # prefer threshold tuning to reweighting",
        "model.fit(Xt, y_tr, eval_set=[(Xv, y_va)], eval_metric='average_precision',",
        "          callbacks=[lgb.early_stopping(200), lgb.log_evaluation(0)])",
        "",
        "# 8. THRESHOLD from costs, chosen on VALIDATION",
        "import numpy as np",
        "p_va = model.predict_proba(Xv)[:, 1]",
        "ths = np.linspace(0.01, 0.99, 99)",
        "cost = [(20 * ((p_va >= t) & (y_va == 0)).sum() +",
        "         500 * ((p_va <  t) & (y_va == 1)).sum()) for t in ths]",
        "t_star = ths[int(np.argmin(cost))]",
        "print('threshold', round(t_star, 3), 'expected cost', min(cost))",
        "",
        "# 8. SLICES - the table that decides whether this ships",
        "for col in ['country', 'device', 'merchant_category']:",
        "    for lvl, idx in X_va.groupby(col).groups.items():",
        "        if len(idx) < 200: continue",
        "        ap = average_precision_score(y_va.loc[idx], p_va[X_va.index.get_indexer(idx)])",
        "        print(f'{col}={lvl:20s} n={len(idx):6d} AP={ap:.3f}')",
        "",
        "# 8. EXPLAINABILITY - required by stage 0, so it is part of the model",
        "import shap",
        "explainer = shap.TreeExplainer(model)",
        "def reason_codes(x_row, k=3):",
        "    sv = explainer.shap_values(x_row)",
        "    order = np.argsort(-np.abs(sv))[:k]",
        "    return [(feature_names[i], float(sv[i])) for i in order]",
    ], "Listing 36.10 - Project A. Note what is NOT here: no neural network, no "
       "exotic sampling, no stacking. On tabular data those come last, if at "
       "all.")
    p("The experiment log for this project is reproduced below. The numbers "
      "are from one representative run; what matters is the SHAPE of the "
      "table - which changes paid, which did not, and which decision each "
      "result triggered.")
    tbl(["Stage", "Result", "Decision taken"],
        [["Baselines", "trivial 0.031, logistic 0.284, GBDT 0.412",
          "GBDT is the track; logistic stays as the sanity check"],
         ["+ rolling 7-day aggregates per card", "0.468",
          "Kept - largest single gain, and it matches the domain story"],
         ["+ 60 tuning trials (Optuna)", "0.487", "Kept, but note it is worth "
          "less than one good feature"],
         ["+ 5-seed ensemble", "0.494", "Rejected - 0.007 AP is not worth 5x the "
          "serving cost at a 50 ms budget"],
         ["Threshold from costs", "t* = 0.19", "Expected cost falls 41% versus "
          "the 0.5 default, with no model change"],
         ["Slice check", "AP 0.31 on one country with 4% of traffic",
          "Blocker - investigated, traced to a missing merchant category "
          "mapping, fixed in the pipeline"],
         ["Final on frozen test", "AP 0.481 (95% CI 0.462-0.499)",
          "Ships. Beats the rule set at 3.1x the precision at equal recall"]],
        widths=[26, 30, 44], bold_first=True)

    h2("Worked project B - a deep model for sensor data, on-device")
    p("Human activity recognition from a wrist accelerometer: 30 subjects, "
      "50 Hz, 6 activities, and the model must run on the watch itself in under "
      "20 ms with less than 256 KB of RAM. This is the project this repository "
      "is about, and every constraint changes a decision.")
    code([
        "# 2. SPLIT BY SUBJECT. A random split here would let the model",
        "#    recognise the person instead of the activity and would report",
        "#    ~99% accuracy that collapses on a new wearer.",
        "tr, va, te = split_by_group(df, group_col='subject_id', y_col='activity')",
        "assert_no_overlap(tr, va, te, 'subject_id')",
        "",
        "# 3-5. WINDOWING - 2 s windows, 50% overlap, computed WITHIN each split",
        "Xtr, ytr = make_windows(tr, fs=50, sec=2.0, overlap=0.5)   # (N, 100, 3)",
        "Xva, yva = make_windows(va, fs=50, sec=2.0, overlap=0.0)   # no overlap",
        "",
        "# 4. BASELINE FIRST - classical features + GBDT, 30 seconds to train",
        "#    accuracy 0.883.  A deep model must beat this to justify itself.",
        "",
        "# 6. DEEP TRACK - a small 1D CNN sized for the device from the start",
        "import torch.nn as nn",
        "def block(cin, cout, k=5, s=2):",
        "    return nn.Sequential(",
        "        nn.Conv1d(cin, cin, k, s, k//2, groups=cin, bias=False),  # depthwise",
        "        nn.Conv1d(cin, cout, 1, bias=False),                      # pointwise",
        "        nn.BatchNorm1d(cout), nn.ReLU())",
        "",
        "model = nn.Sequential(",
        "    nn.Conv1d(3, 32, 7, 2, 3, bias=False), nn.BatchNorm1d(32), nn.ReLU(),",
        "    block(32, 64), block(64, 64), block(64, 128),",
        "    nn.AdaptiveAvgPool1d(1), nn.Flatten(),",
        "    nn.Dropout(0.3), nn.Linear(128, 6))",
        "# 17,158 parameters -> 67 KB in fp32, 17 KB in INT8. Weights fit the",
        "# budget with room left for activations, which for a (100, 3) input and",
        "# these widths peak at about 25 KB - the number that actually binds.",
        "",
        "# 6. AUGMENTATION that encodes true invariances for this sensor",
        "#    jitter, scaling, time warping, small rotations of the sensor frame.",
        "#    NOT horizontal flip - reversing time is not an invariance here.",
        "",
        "# 9. COMPRESS to the device budget. Sizes below are computed from the",
        "#    parameter counts; the latency and accuracy columns are the shape",
        "#    of a representative run - measure your own on the real device.",
        "#                              weights   latency   accuracy",
        "#    fp32 dense                  67 KB     31 ms     0.921",
        "#    + 30% channel prune + FT    38 KB     22 ms     0.916",
        "#    + INT8 QAT                  10 KB      9 ms     0.913",
        "#    + distil from the teacher   10 KB      9 ms     0.919  <- ships",
    ], "Listing 36.11 - Project B. The architecture was chosen against the "
       "memory budget before training started, not shrunk afterwards.")
    box("key", "What differed between the two projects",
        "Project A split by time, project B by subject - both because of how "
        "the model will be used, not because of a convention. A used no deep "
        "learning at all; B used a small one and still had to beat a classical "
        "baseline to justify it. A's hard constraint was explainability, which "
        "kept it on trees; B's was 256 KB of RAM, which decided the "
        "architecture before the first epoch. The thirteen stages were "
        "identical; every decision inside them came from stage 0.")

    h2("Time budget and the failure timeline")
    tbl(["Week", "What a healthy project is doing", "What a failing one is doing"],
        [["1", "Charter agreed; repository set up; data loaded and split; "
          "baselines running", "Reading papers; choosing a framework; building "
          "a model with no baseline"],
         ["2", "Leakage audit; exploration; first real model beating the "
          "baseline", "Tuning a model whose split is wrong"],
         ["3-4", "Feature or augmentation iteration; error analysis driving the "
          "next change", "Trying a fifth architecture; the metric has not moved "
          "since week 2"],
         ["5", "Slice evaluation; calibration; threshold from costs; test set "
          "touched once", "Discovering the test set has been used for selection "
          "all along"],
         ["6", "Packaging, behavioural tests, shadow deployment",
          "Realising the features cannot be computed at serving time"],
         ["7+", "Canary, ramp, monitoring, first retraining rehearsal",
          "A model that scores well and has never seen a real request"]],
        widths=[8, 46, 46], bold_first=True)

    h2("The one-page master checklist")
    checklist("Framing and data", [
        "The prediction target, the entity and the decision moment are written "
        "down.",
        "The cost of each error type is quantified.",
        "The baseline being replaced is measured.",
        "The success criterion was agreed before modelling started.",
        "The split axis matches deployment (time / group / random).",
        "The test set is frozen and hashed.",
        "Every feature passed the 'available at prediction time' audit.",
    ])
    checklist("Modelling and evaluation", [
        "Trivial and simple baselines exist and are beaten.",
        "All preprocessing lives inside the pipeline object.",
        "One change per experiment; every run logged with its config and commit.",
        "Results averaged over seeds, with the spread reported.",
        "Per-slice metrics computed; no slice regressed unacceptably.",
        "Calibration checked; the threshold was chosen from costs on validation.",
        "50 worst errors were read and categorised.",
        "The test set was used exactly once.",
    ])
    checklist("Shipping and keeping it alive", [
        "Latency, memory and energy measured on the target device with the "
        "target runtime.",
        "The artefact directory contains model, metadata, metrics, threshold, "
        "schema and model card.",
        "Input validation and behavioural tests exist and run in CI.",
        "Shadow and canary stages completed; rollback rehearsed.",
        "Drift, performance and cost monitoring are live with owned alerts.",
        "The retraining policy and the promotion gate are written down.",
        "An owner is named.",
    ])
    box("tip", "If you remember only one thing from this chapter",
        "Stage 0 and stage 4 - a written charter and an honest baseline - cost "
        "one day between them and determine whether the other twelve stages "
        "produce anything of value. Teams that skip them build models that are "
        "technically excellent answers to questions nobody asked, measured "
        "against nothing.")

    h3("Exercises")
    bul([
        "Take a dataset you already have and write its stage-0 charter. If you "
        "cannot fill in the cost of a false positive, go and find out - that "
        "conversation is the exercise.",
        "Reproduce the thirteen stages on a public dataset, timing each one. "
        "Most people are surprised by how much of the total lands in stages "
        "2-3.",
        "Take a model you trained earlier in this book, package it as in stage "
        "10, and write four behavioural tests for it.",
        "Deliberately choose the wrong split axis for a grouped dataset, then "
        "the right one, and report both numbers. Keep the pair - it is the most "
        "convincing argument you will ever have for careful splitting.",
    ], ordered=True)


# =============================================================================
#                                  BUILD
# =============================================================================
def main():
    front_matter()
    part1(); part2(); part3(); part4(); part5(); part6()
    appendices()
    doc = Book(OUTPUT,
               title="Machine Learning and Deep Learning - The Complete Guide",
               author="Generated with Claude Code",
               subject="A beginner-to-expert guide to machine learning and "
                       "deep learning",
               creator="gen_ml_dl_guide_pdf.py")
    doc.multiBuild(STORY)
    size = os.path.getsize(OUTPUT) / 1024.0
    print("Wrote %s (%.0f KB)" % (OUTPUT, size))


if __name__ == "__main__":
    main()
