"""
RigL on ODT - Complete Implementation, Line by Line
===================================================
Extracts every RigL code fragment scattered across the 39 chapters of
'text books/drafts/ODT_Complete_Reference_v2.pdf' into one consolidated,
build-ordered reference, with a line-by-line explanation of every line of
code and an engineering review of the issues found during extraction.

Reuses the layout engine of gen_ml_dl_guide_pdf.py.

Usage:
    python gen_rigl_implementation_pdf.py
Output:
    RigL_Implementation_Line_by_Line.pdf
"""

import os
import gen_ml_dl_guide_pdf as G
from gen_ml_dl_guide_pdf import (
    add, p, h2, h3, bul, code, eq, box, tbl, diagram, checklist, chapter,
    part, pb, sp, mk, xe, Paragraph, Table, TableStyle, Spacer, KeepTogether,
    colors, mm, CONTENT_W, C_DARK, C_MID, C_LIGHT, C_GREY, C_CODE_BG,
    C_CODE_BD, S_H1, S_CAP, S_TD, S_TDB, S_TH, _ps, TA_CENTER,
)

G.HEADER_TEXT = "RigL on ODT - Complete Implementation, Line by Line"
G.FOOTER_TEXT = "Extracted from ODT_Complete_Reference_v2.pdf"

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "RigL_Implementation_Line_by_Line.pdf")

SOURCE = "ODT_Complete_Reference_v2.pdf"

# --------------------------------------------------------------- helpers ----
S_LNUM = _ps("LNUM", fontSize=7.2, leading=10.6, fontName="Courier",
             textColor=colors.HexColor("#8a94a6"))
S_LCODE = _ps("LCODE", fontSize=8.0, leading=10.6, fontName="Courier",
              textColor=colors.HexColor("#102030"))


def listing(lines, caption=None, start=1):
    """Numbered code listing; line numbers align with the explain() tables."""
    rows = []
    n = start
    for ln in lines:
        esc = xe(ln.rstrip()).replace(" ", "&nbsp;")
        stripped = ln.strip()
        if stripped.startswith("//") or stripped.startswith("/*") \
                or stripped.startswith("*"):
            esc = '<font color="#2e7d32"><i>%s</i></font>' % esc
        elif stripped.startswith("#"):
            esc = '<font color="#7b1fa2">%s</font>' % esc
        rows.append([Paragraph("%d" % n, S_LNUM),
                     Paragraph(esc if esc else "&nbsp;", S_LCODE)])
        n += 1
    t = Table(rows, colWidths=[9 * mm, CONTENT_W - 9 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CODE_BG),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8ebf0")),
        ("BOX", (0, 0), (-1, -1), 0.7, C_CODE_BD),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, C_CODE_BD),
        ("LEFTPADDING", (0, 0), (0, -1), 2),
        ("RIGHTPADDING", (0, 0), (0, -1), 3),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("LEFTPADDING", (1, 0), (1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
    ]))
    add(Spacer(1, 3), t)
    add(Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 6))


def explain(rows, caption=None):
    """Line-by-line explanation table: (line-ref, code fragment, meaning)."""
    data = [[Paragraph(mk(h), S_TH) for h in ("Line", "Code", "What it does and why")]]
    for ref, frag, why in rows:
        data.append([
            # plain hyphen: U+2011 has no glyph in Helvetica and renders as a
            # black box. The 13mm column is wide enough that "16-18" fits.
            Paragraph(mk(str(ref)), S_TDB),
            Paragraph('<font face="Courier" size="7.6">%s</font>' % xe(frag), S_TD),
            Paragraph(mk(why), S_TD),
        ])
    t = Table(data, colWidths=[13 * mm, 0.34 * (CONTENT_W - 13 * mm),
                               0.66 * (CONTENT_W - 13 * mm)], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_MID),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0bec5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i),
                          colors.HexColor("#f4f7fa")))
    t.setStyle(TableStyle(style))
    add(Spacer(1, 3), t)
    add(Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 7))


def origin(sections):
    """Provenance banner: which sections of the source PDF this came from."""
    txt = "Source: %s, %s" % (SOURCE, sections)
    t = Table([[Paragraph(mk(txt), _ps("org", fontSize=8, leading=11,
                                       textColor=colors.white))]],
              colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_GREY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    add(Spacer(1, 2), t, Spacer(1, 6))


# =============================================================================
#                              FRONT MATTER
# =============================================================================
def front():
    add(Spacer(1, 40 * mm))
    add(Paragraph("RigL on ODT", G.S_TITLE))
    add(Spacer(1, 2))
    add(G.HRFlowable(width="55%", thickness=2, color=C_MID, spaceAfter=10,
                     hAlign="CENTER"))
    add(Paragraph("The Complete Implementation, Line by Line", G.S_SUBTITLE))
    add(Spacer(1, 6))
    add(Paragraph("Every RigL code fragment from the 39-chapter ODT reference, "
                  "consolidated into build order, with each line explained",
                  G.S_SUBTITLE))
    add(Spacer(1, 16 * mm))
    rows = [
        ["Extracted from", SOURCE + " (142 pages, 39 chapters)"],
        ["Source sections", "41 RigL sections: 2.1-2.4, the 'Missing RigL Code' "
         "section of every chapter, and Chapter 39 in full"],
        ["Components", "7 required + 2 optional (AdamW, Conv1d), in dependency "
         "order"],
        ["Target", "STM32 Nucleo-F746ZG, Cortex-M7 at 216 MHz, 320 KB SRAM"],
        ["Code", "C99, every line numbered and explained individually"],
        ["Also included", "An engineering review of the defects found while "
         "extracting, and ready-to-compile RigL.h / RigL.c"],
    ]
    t = Table([[Paragraph(mk(a), S_TDB), Paragraph(mk(b), S_TD)] for a, b in rows],
              colWidths=[34 * mm, CONTENT_W - 34 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eceff1")),
        ("BOX", (0, 0), (-1, -1), 0.8, C_MID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    add(t)
    pb()

    t = Table([[Paragraph("What This Document Is", S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    add(t, Spacer(1, 8))
    p("In the source reference, the RigL implementation is **not in one place**. "
      "It is distributed across 41 sections of 39 chapters: each chapter "
      "documents one source file of the ODT library and ends with a 'Missing "
      "RigL Code' section describing what that particular file still needs. "
      "Chapter 39 then gathers seven of those fragments, but not all of them, "
      "and in places states the code differently from the chapter it came from.")
    p("This document does the consolidation properly. It collects **every** "
      "RigL fragment, orders them by build dependency rather than by file "
      "name, explains every line of every fragment individually, and records "
      "where each piece came from so you can always go back to the original.")

    h3("How to read a component chapter")
    bul([
        "**Provenance bar** - the grey strip naming the exact section of the "
        "source PDF the code came from.",
        "**Purpose** - what the component does and which other components "
        "depend on it.",
        "**Numbered listing** - the complete code, one line per row.",
        "**Line-by-line table** - every line of that listing, with what it does "
        "and, more usefully, why it is written that way.",
        "**Notes** - complexity, memory cost on the target MCU, and any defect "
        "found in that fragment.",
    ])

    h3("A note on fidelity")
    p("The code in this document is the code from the source, transcribed "
      "faithfully. Where the source contains an error, the error is reproduced "
      "in the listing and then flagged in the line-by-line table and in "
      "Chapter 17, rather than silently corrected - you need to know what the "
      "original said. Corrected versions are given separately, and always "
      "marked as corrections.")
    box("warn", "Nine defects were found during extraction",
        "The source is a careful document, but consolidating it surfaces "
        "problems that are invisible when each chapter is read on its own: two "
        "sections give contradictory instructions about when to call "
        "rigLStep(); one memory figure is wrong by a factor of 250; the DROP "
        "and GROW steps as written do not preserve the exact-K conservation "
        "the algorithm depends on; and the gradient the GROW step needs is "
        "zeroed by another component before GROW can use it. Chapter 17 lists "
        "all ten with a proposed fix for each. Read it before you implement.")

    h3("Build order")
    diagram([
        "   1. findAbsKthSmallestActive()  MinMax.c    no dependencies",
        "   2. findAbsKthLargestInactive() MinMax.c    no dependencies",
        "        |",
        "   3. weightMask field            Linear.h    enables everything below",
        "        |",
        "        +--> 4. mask-aware matmul     Matmul.c   (forward speedup)",
        "        +--> 5. mask-aware SGD        Sgd.c      (keeps zeros at zero)",
        "        +--> 5b. mask-aware AdamW     AdamW.c    (optional optimiser)",
        "        |",
        "   6. rigLStep()                  RigL.c      needs 1, 2, 3",
        "        |",
        "   7. serializeSparsity()         Serialize.c persist the mask",
        "        |",
        "   8. mask init + UserAPI         UserAPI.c   create the mask",
        "        |",
        "   9. training-loop integration   TrainingLoopApi.c",
    ], "Figure 0.1 - Dependency order. Implement top to bottom; each step is "
       "testable on its own.")

    t = Table([[Paragraph("Contents", S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    add(G.PageBreak(), t, Spacer(1, 8))
    toc = G.TableOfContents()
    toc.levelStyles = [G.S_TOC1, G.S_TOC2, G.S_TOC3]
    add(toc)


# =============================================================================
def ch_algorithm():
    chapter("The RigL Algorithm")
    origin("sections 2.1, 2.2, 2.3, 2.4 and 33.4")
    p("RigL - Rigging the Lottery - trains a sparse network from scratch in a "
      "single pass. It keeps a fixed number of active weights throughout "
      "training and periodically changes **which** weights are active: it drops "
      "the active weights that are smallest in magnitude, and grows the "
      "inactive weights whose gradients are largest.")

    h2("Why this works")
    tbl(["Signal", "Used for", "Reasoning"],
        [["|w[i]| small, weight active", "DROP it",
          "A small weight contributes little to the output, so removing it "
          "costs little accuracy"],
         ["|g[i]| large, weight inactive", "GROW it",
          "The gradient of an inactive weight says how much the loss WOULD fall "
          "if that connection were allowed to move. It is a direct estimate of "
          "the value of activating it"],
         ["K dropped = K grown", "Conservation",
          "The active count never changes, so memory and compute stay fixed for "
          "the whole run - the property that makes RigL viable on an MCU"]],
        widths=[26, 16, 58], bold_first=True)
    box("key", "The one idea",
        "A pruned weight is not dead. Its gradient can still be computed, and "
        "that gradient tells you whether it deserves to come back. RigL is the "
        "algorithm that acts on this observation: magnitude decides what "
        "leaves, gradient decides what enters, and the two are balanced so the "
        "sparsity level never moves.")

    h2("The algorithm as stated in the source")
    listing([
        "RIGL (per sparse layer, every T training steps):",
        "",
        "  alpha(t) = (0.3/2) * (1 + cos(pi * t / T_end))   // cosine decay",
        "  K        = floor( alpha(t) * (1 - s) * N )       // weights to swap",
        "",
        "  DROP K active weights with smallest |W|:",
        "    thresh = K-th smallest |W[i]| in the active set",
        "    for M[i]=1 and |W[i]| <= thresh:  M[i]=0; W[i]=0; G[i]=0",
        "",
        "  GROW K inactive weights with largest |G|:",
        "    thresh = K-th largest |G[i]| in the inactive set",
        "    for M[i]=0 and |G[i]| >= thresh:  M[i]=1; W[i]=0",
        "",
        "  Zero the gradients of all remaining inactive weights: G[i]=0",
    ], "Listing 1.1 - The algorithm, transcribed from section 2.2 of the source.")
    tbl(["Symbol", "Meaning", "Typical value for the HAR model"],
        [["s", "Target sparsity", "0.9 - nine of every ten weights inactive"],
         ["N", "Total weights in the layer", "73,728 for the 1152 x 64 linear layer"],
         ["(1-s)*N", "Active weights - constant for the whole run", "7,373"],
         ["alpha(t)", "Fraction of active weights swapped at step t", "0.30 "
          "falling to 0.00"],
         ["K", "Number swapped this step = alpha * active", "2,212 at step 0, "
          "0 after T_end"],
         ["T", "Steps between mask updates", "100"],
         ["T_end", "Step after which the mask is frozen", "8,280 = 80% of 10,350"]],
        widths=[14, 34, 52], bold_first=True)

    h2("The cosine schedule, and why it is shaped that way")
    eq(["alpha(t) = (alpha_init / 2) * (1 + cos(pi * t / T_end))",
        "",
        "t = 0        alpha = 0.30    K = 30% of active   explore",
        "t = T_end/2  alpha = 0.15    K = 15% of active   consolidate",
        "t = T_end    alpha = 0.00    K = 0               mask frozen",
        "t > T_end    alpha = 0       only weight VALUES change, not positions"])
    p("The mask must stop moving before training ends. If connectivity were "
      "still changing in the final epochs, the newly grown weights - which "
      "start at exactly zero - would never get enough updates to become "
      "useful, and every swap would cost accuracy instead of buying it. "
      "Freezing the mask at 80% of training leaves a fifth of the run to "
      "refine a fixed structure.")
    box("intuit", "Why it pairs with a cosine learning rate",
        "Both schedules decay together, and they are saying the same thing at "
        "different levels. Early on: a high learning rate explores weight "
        "VALUES while a high alpha explores weight POSITIONS. Late on: a low "
        "learning rate refines values while alpha = 0 holds positions still. "
        "Running CosineAnnealingLR and the RigL alpha decay with the same "
        "T_max is not a coincidence of convenience - it keeps exploration and "
        "refinement aligned in both spaces.")

    h2("Where it stands against dense training")
    tbl(["Setting", "Accuracy", "Note"],
        [["ResNet-50 / ImageNet, dense", "76.8%", "The reference"],
         ["RigL, 80% sparse, 1x training", "74.6%", "2.2 points below dense at "
          "one fifth of the weights"],
         ["RigL, 80% sparse, 5x training", "76.4%", "Matches dense - the "
          "accuracy is recoverable with a longer run"],
         ["HAR, 90% sparse + FQT", "~90-93% (estimate)", "The target for this "
          "implementation; not yet measured"]],
        widths=[36, 20, 44], bold_first=True)
    box("note", "Which of these numbers are measurements",
        "The ResNet-50 rows are published results quoted by the source. The HAR "
        "row is described in the source as an estimate, and it is repeated here "
        "as one. Nothing in this document reports a measurement taken on the "
        "STM32 target; when you run it, the numbers in Chapters 14 and 15 are the ones "
        "to fill in.")


def ch_component_map():
    chapter("What Exists, What Is Missing, and Where Each Piece Lives")
    origin("section 2.4 ('RigL: ODT Gap') and the 'Missing RigL Code' section "
           "of all 39 chapters")
    p("Before writing anything, it is worth knowing exactly how much of RigL "
      "the ODT library already provides. The answer is: the primitives exist, "
      "the algorithm does not.")
    tbl(["Already in ODT", "What it gives you"],
        [["BOOL tensor type", "A bit-packed tensor - the mask storage format, "
          "1 bit per weight rather than 1 byte"],
         ["tensorBoolGet / tensorBoolSet", "Read and write one mask bit by flat "
          "index"],
         ["bernoulliFillMask", "Fill a BOOL tensor with independent Bernoulli "
          "draws - the random initial mask"],
         ["calcNumberOfElementsByTensor", "Element count, used by every loop in "
          "this document"],
         ["XorShift32 RNG with seeding", "Reproducible masks and reproducible "
          "stochastic rounding"],
         ["Cosine LR scheduler", "The same cosine math the alpha schedule "
          "needs"]],
        widths=[32, 68], bold_first=True)
    tbl(["Missing - must be built", "File", "This document"],
        [["findAbsKthSmallestActive()", "MinMax.c", "Chapter 5"],
         ["findAbsKthLargestInactive()", "MinMax.c", "Chapter 6"],
         ["weightMask field in linearConfig_t", "Linear.h", "Chapter 7"],
         ["Mask-aware inner loop", "Matmul.c", "Chapter 8"],
         ["Mask-aware parameter update", "Sgd.c", "Chapter 9"],
         ["Mask-aware update with moment clearing", "AdamW.c", "Chapter 10"],
         ["rigLStep()", "RigL.h / RigL.c (new)", "Chapter 11"],
         ["serializeSparsity() / deserializeSparsity()", "Serialize.c",
          "Chapter 12"],
         ["Mask creation for sparse layers", "UserAPI.c", "Chapter 13"],
         ["rigLStep() call site and config fields", "TrainingLoopApi.c",
          "Chapter 13"]],
        widths=[46, 30, 24], bold_first=True)
    box("note", "Seven, eight or ten components?",
        "The source says seven. That count omits deserializeSparsity() - "
        "without which a saved mask cannot be loaded back, so checkpointing is "
        "only half implemented - and it omits the UserAPI and training-loop "
        "integration described in chapters 38 and 37, without which nothing "
        "ever calls rigLStep(). Counting honestly there are ten pieces of work, "
        "which is why this document has ten component chapters rather than "
        "seven.")

    h2("Files this touches, and how much of each")
    tbl(["File", "Change", "Size of change", "Risk if wrong"],
        [["MinMax.c / .h", "Two new functions", "~60 lines",
          "Wrong threshold - drops or grows the wrong count"],
         ["Linear.h", "One struct field, one initialiser line", "2 lines",
          "None if NULL-defaulted; dense layers keep working"],
         ["Matmul.c", "One conditional in the hot loop", "~4 lines",
          "Silently wrong outputs if the flat index is miscomputed"],
         ["Sgd.c", "One conditional in the update loop", "~5 lines",
          "Inactive weights drift away from zero and sparsity is fake"],
         ["AdamW.c", "One conditional plus moment clearing", "~8 lines",
          "Stale moments cause a bad first step after a grow"],
         ["RigL.c / .h", "New file", "~50 lines", "The algorithm itself"],
         ["Serialize.c", "Two functions", "~25 lines",
          "Mask lost at checkpoint - the model reloads dense"],
         ["UserAPI.c", "Mask allocation for sparse specs", "~8 lines",
          "No mask means rigLStep() silently skips every layer"],
         ["TrainingLoopApi.c", "Config fields and one call", "~10 lines",
          "The mask never updates; you get static random sparsity"]],
        widths=[16, 30, 16, 38], bold_first=True)


# =============================================================================
def ch_kth_smallest():
    chapter("Component 1 - findAbsKthSmallestActive()")
    origin("section 7.4 (primary) and section 39.2 (variant)")
    p("**Purpose.** Find the K-th smallest absolute weight value among the "
      "**active** weights of a layer. This single number is the DROP "
      "threshold: every active weight whose magnitude is at or below it will "
      "be deactivated. **Depends on:** nothing. **Used by:** rigLStep() "
      "(Chapter 11). This is the first thing to implement and the easiest to "
      "unit-test.")
    listing([
        "float findAbsKthSmallestActive(tensor_t *weights,",
        "                               tensor_t *mask,",
        "                               size_t K) {",
        "    size_t n = calcNumberOfElementsByTensor(weights);",
        "    float *w = (float *)weights->data;",
        "",
        "    /* Pass 1: how many weights are currently active? */",
        "    size_t count = 0;",
        "    for (size_t i = 0; i < n; i++)",
        "        if (tensorBoolGet(mask, i)) count++;",
        "",
        "    if (K >= count) return 1e38f;   /* keep all: threshold = +inf */",
        "",
        "    float *vals = malloc(count * sizeof(float));",
        "    if (!vals) { exit(1); }",
        "",
        "    /* Pass 2: gather |w| of the active weights only. */",
        "    size_t idx = 0;",
        "    for (size_t i = 0; i < n; i++)",
        "        if (tensorBoolGet(mask, i)) vals[idx++] = fabsf(w[i]);",
        "",
        "    /* Partial selection sort: sorts only the first K+1 positions. */",
        "    for (size_t i = 0; i <= K && i < count; i++) {",
        "        size_t minIdx = i;",
        "        for (size_t j = i + 1; j < count; j++)",
        "            if (vals[j] < vals[minIdx]) minIdx = j;",
        "        float tmp = vals[i];",
        "        vals[i] = vals[minIdx];",
        "        vals[minIdx] = tmp;",
        "    }",
        "",
        "    float thresh = vals[K < count ? K : count - 1];",
        "    free(vals);",
        "    return thresh;",
        "}",
    ], "Listing 3.1 - findAbsKthSmallestActive(), transcribed from section 7.4.")

    h2("Line by line")
    explain([
        ("1", "float findAbsKthSmallestActive(tensor_t *weights,",
         "**Does:** declares a function returning a float threshold. "
         "**Why a float and not a list of indices:** returning a threshold "
         "makes the function pure and stateless - it allocates nothing the "
         "caller must free, and the caller decides what to do with it. A "
         "function that returned 'the K indices to drop' would need a buffer, "
         "an ownership convention, and a second pass anyway."),
        ("2", "tensor_t *mask,",
         "**Does:** the mask defining which weights count. "
         "**Why it is a parameter rather than read from the layer:** this keeps "
         "the function independent of `linearConfig_t`, so it can be unit "
         "tested with two bare tensors and no model - which is exactly how "
         "Chapter 14 tests it."),
        ("3", "size_t K) {",
         "**Does:** how many weights the caller intends to drop. "
         "**Why `size_t`:** it indexes into the array on line 31, and a signed "
         "type would invite a negative K that indexes backwards."),
        ("4", "size_t n = calcNumberOfElementsByTensor(weights);",
         "**Does:** the total element count, active and inactive. "
         "**Why total and not active:** the loops on lines 9 and 18 walk the "
         "whole tensor, because the mask is a bitmap with no index list. "
         "**Careful:** ELEMENTS, not bytes - the mask must report the same "
         "number."),
        ("5", "float *w = (float *)weights->data;",
         "**Does:** a raw float view, bypassing the tensor accessors. "
         "**Why:** this pointer is dereferenced up to n times in the gather "
         "loop; a function call per element would dominate the cost. "
         "**If wrong:** valid only for FLOAT32. A SYM_INT32 tensor holds int32 "
         "mantissas, and reinterpreting those bits as floats yields magnitudes "
         "unrelated to the real weights. The fix is to reconstruct "
         "`mantissa * scale` first - a planned enhancement in the source, not "
         "implemented."),
        ("7", "/* Pass 1: how many weights are currently active? */",
         "**Does:** nothing at runtime. **Why it earns its place:** this "
         "function makes three passes over the data and a reader needs to know "
         "which one they are in."),
        ("8", "size_t count = 0;",
         "**Does:** initialises the active counter. "
         "**Why it must be counted at all:** nothing in ODT stores the active "
         "count; the mask is the sole record, so it is recomputed on every "
         "call."),
        ("9", "for (size_t i = 0; i < n; i++)",
         "**Does:** the counting scan. "
         "**Why over n and not over some smaller set:** there is no list of "
         "active positions to iterate - finding them IS this loop."),
        ("10", "if (tensorBoolGet(mask, i)) count++;",
         "**Does:** tests one mask bit; increments if set. "
         "**Cost:** `tensorBoolGet` is a load, a shift and an AND - about 3-4 "
         "cycles on a Cortex-M7, so this pass costs roughly 4n cycles. For the "
         "HAR layer, about 300,000 cycles, or 1.4 ms at 216 MHz."),
        ("12", "if (K >= count) return 1e38f;",
         "**Does:** handles the case where the caller asks to drop at least as "
         "many weights as are active. "
         "**Why 1e38 specifically:** it is a finite float just under FLT_MAX "
         "(3.4e38), so it compares cleanly and never becomes an infinity that "
         "could propagate as a NaN in later arithmetic. Every active weight "
         "satisfies `|w| <= 1e38`, so all of them drop - the correct reading of "
         "'you asked for more than exist'. "
         "**Second job:** it guarantees `K < count` for line 31, which would "
         "otherwise index past the end of the buffer."),
        ("14", "float *vals = malloc(count * sizeof(float));",
         "**Does:** allocates a scratch buffer holding one float per active "
         "weight. "
         "**Why heap:** `count` is a runtime value, so a fixed-size array would "
         "have to be sized for the worst case. "
         "**Why this is the worst line in the file on an MCU:** 29 KB here, and "
         "259 KB in the sibling function, on a 320 KB device with no MMU, "
         "allocated and freed every 100 steps. Repeated allocation of "
         "differently-sized blocks fragments the heap; the failure mode is a "
         "NULL return hours into a run. Defect D8."),
        ("15", "if (!vals) { exit(1); }",
         "**Does:** aborts on allocation failure. "
         "**Why it is unacceptable on the target:** there is no operating "
         "system to exit to. On bare metal `exit()` either hangs in a loop or "
         "invokes undefined behaviour, and either way a training run dies with "
         "no diagnostic. Return an error and let the caller skip this layer's "
         "RigL step - one missed swap is harmless."),
        ("17", "size_t idx = 0;",
         "**Does:** the write cursor into the scratch buffer. "
         "**Why a separate counter:** the read index `i` walks all n positions "
         "while the write index advances only on active ones, so the two cannot "
         "be the same variable."),
        ("18", "for (size_t i = 0; i < n; i++)",
         "**Does:** the gather scan - the second full pass. "
         "**Why not fused with pass 1:** the buffer cannot be allocated until "
         "its size is known, and its size is what pass 1 computes. Fusing them "
         "would need a growable buffer or an upper-bound allocation of n "
         "floats, which for the HAR layer is 288 KB - worse than the problem it "
         "solves."),
        ("19", "if (tensorBoolGet(mask, i)) vals[idx++] = fabsf(w[i]);",
         "**Does:** copies |w| of each active weight into the dense buffer. "
         "**Why absolute value:** RigL ranks by magnitude - a weight of -0.8 is "
         "just as influential as +0.8. "
         "**Why `fabsf` and not `fabs`:** the float version. `fabs` takes a "
         "double, so it promotes, computes in double, and demotes - on an M7 "
         "with a single-precision FPU that means a software double routine, "
         "costing tens of cycles per element instead of one. "
         "**Postcondition:** `idx == count`."),
        ("21", "/* Partial selection sort: first K+1 positions. */",
         "**Does:** nothing at runtime. **Why it matters:** without this "
         "comment a reader assumes the loop below is a broken full sort."),
        ("22", "for (size_t i = 0; i <= K && i < count; i++) {",
         "**Does:** the outer loop of a partial selection sort, running K+1 "
         "times. **Why `<= K` and not `< K`:** positions 0..K must all be "
         "settled, because line 31 reads `vals[K]`. "
         "**Why partial at all:** a full sort is O(count^2) here; stopping "
         "early makes it O(count x K). For the HAR layer that is 16.3 M "
         "comparisons instead of 54 M. "
         "**The `i < count` term** is redundant given line 12, but survives a "
         "future change to that guard."),
        ("23", "size_t minIdx = i;",
         "**Does:** assumes the current position holds the smallest remaining "
         "value. **Why:** selection sort's invariant - everything before `i` is "
         "already in its final place, so the search starts at `i`."),
        ("24", "for (size_t j = i + 1; j < count; j++)",
         "**Does:** scans the unsorted tail. "
         "**Why from `i+1`:** positions at or below `i` are settled. "
         "**Cost:** this is the hot loop; it executes about count x K times in "
         "total and is where essentially all the function's time goes."),
        ("25", "if (vals[j] < vals[minIdx]) minIdx = j;",
         "**Does:** tracks the index of the smallest value seen. "
         "**Why `<` and not `<=`:** with `<=` the index would keep moving among "
         "equal values for no benefit; either is correct, `<` does less work. "
         "**Note:** this is the ONE line that differs between this function and "
         "its sibling, where it becomes `>`."),
        ("26", "float tmp = vals[i];",
         "**Does:** the first step of a three-line swap. "
         "**Why a manual swap:** C has no swap operator, and a memcpy of four "
         "bytes would be slower than three register moves."),
        ("27", "vals[i] = vals[minIdx];",
         "**Does:** moves the smallest remaining value into position `i`."),
        ("28", "vals[minIdx] = tmp;",
         "**Does:** completes the swap. "
         "**Postcondition after the outer loop:** positions 0..K hold the K+1 "
         "smallest magnitudes in ascending order; positions K+1.. are in "
         "arbitrary order, which is fine because they are never read."),
        ("31", "float thresh = vals[K < count ? K : count - 1];",
         "**Does:** reads the K-th smallest magnitude, zero-indexed - so "
         "actually the (K+1)-th smallest value. Toy layer: `vals[2]` = 0.30. "
         "**Why the ternary:** redundant given line 12, but it makes the "
         "function safe on its own terms rather than relying on a guard forty "
         "lines away. "
         "**Where defect D1 lives:** paired with the `<=` in rigLStep(), this "
         "selects K+1 weights. Either return `vals[K-1]` and keep `<=`, or keep "
         "this and use a strict `<`."),
        ("32", "free(vals);",
         "**Does:** releases the scratch buffer. "
         "**Why here and not after the return:** it must precede the return, "
         "and `thresh` was copied out on line 31 precisely so that this is "
         "possible. Every path except the `exit(1)` frees, so there is no "
         "leak."),
        ("33", "return thresh;",
         "**Does:** hands the caller a single float. "
         "**What the caller does with it:** compares every active weight "
         "against it. The function itself never touches the mask - it is "
         "read-only over its inputs, which is what makes it safe to call twice "
         "or to test in isolation."),
        ("34", "}",
         "**Does:** end of function. Note what is NOT here: no mask mutation, "
         "no weight mutation, no logging, no global state. That purity is why "
         "this is the first component to implement and the easiest to trust."),
    ], "Table 5.1 - Every line of findAbsKthSmallestActive(). Toy-layer values "
       "refer to the 8-weight example of Chapter 2.")

    h2("Worked example")
    p("The source gives this example in section 39.2. It is worth working "
      "through carefully, because it exposes a defect.")
    eq(["active |w| = [0.01, 0.05, 0.03, 0.12, 0.08],   K = 2",
        "",
        "after the partial sort: [0.01, 0.03, 0.05, ...]",
        "thresh = vals[2] = 0.05",
        "",
        "the source then states: 'weights with |w| <= 0.05 are dropped:",
        "0.01 and 0.03. Exactly 2 weights dropped = K.'"])
    box("warn", "The example undercounts by one",
        "The condition is `|w| <= 0.05` and the value 0.05 is itself in the "
        "active set - so THREE weights match: 0.01, 0.03 and 0.05. To drop "
        "exactly K you need either `thresh = vals[K-1]` with `<=`, or "
        "`thresh = vals[K]` with a strict `<`. As written, DROP removes K+1 "
        "weights. The GROW step has the mirror-image error, so the two happen "
        "to cancel and total sparsity is preserved - but the swap size is not "
        "the K you asked for, and with duplicate magnitudes the cancellation "
        "stops being exact. Chapter 17, defect D1.")

    h2("Cost on the target")
    tbl(["Quantity", "Value for the HAR 1152 x 64 layer at 90% sparsity"],
        [["n (all weights)", "73,728"],
         ["count (active)", "7,373"],
         ["K at alpha = 0.3", "2,212"],
         ["Comparisons, O(count*K)", "7,373 x 2,212 = 16.3 M"],
         ["Scratch memory", "7,373 x 4 B = 29 KB on the heap"],
         ["Frequency", "Once per sparse layer, every 100 steps"]],
        widths=[34, 66], bold_first=True)
    box("note", "The source's complexity estimate is off",
        "Section 7.4 estimates the cost as `n * K` and gives 8192 x 819 = 6.7 M "
        "comparisons for a 128 x 64 layer. The sort runs over the ACTIVE "
        "values only, so the true cost is `count * K`, which at 90% sparsity is "
        "an order of magnitude smaller than the n-based figure. The estimate is "
        "conservative in the safe direction, but if you are budgeting cycles, "
        "use count, not n. Chapter 17, defect D10.")
    box("warn", "malloc on a Cortex-M7",
        "29 KB from the heap, allocated and freed every 100 steps, for every "
        "sparse layer, on a device with 320 KB of SRAM and no MMU. Repeated "
        "allocation of differently-sized blocks fragments the heap, and the "
        "failure mode is a NULL return at some unpredictable point hours into "
        "training. Two fixes: allocate one scratch buffer of the largest layer "
        "size ONCE at initialisation and reuse it, or replace the "
        "gather-and-sort with a two-pass histogram over magnitudes that needs "
        "only a fixed-size bin array. The first fix is a ten-line change and is "
        "what this document recommends.")


def ch_kth_largest():
    chapter("Component 2 - findAbsKthLargestInactive()")
    origin("section 7.4 (primary) and section 39.3 (variant)")
    p("**Purpose.** Find the K-th largest absolute **gradient** among the "
      "**inactive** weights. This is the GROW threshold: every inactive weight "
      "whose gradient magnitude is at or above it will be activated. It is the "
      "mirror image of Component 1 - inactive instead of active, gradients "
      "instead of weights, largest instead of smallest.")
    listing([
        "float findAbsKthLargestInactive(tensor_t *grads,",
        "                                tensor_t *mask,",
        "                                size_t K) {",
        "    size_t n = calcNumberOfElementsByTensor(grads);",
        "    float *g = (float *)grads->data;",
        "",
        "    size_t count = 0;",
        "    for (size_t i = 0; i < n; i++)",
        "        if (!tensorBoolGet(mask, i)) count++;",
        "",
        "    if (K >= count) return 0.0f;    /* grow all: threshold = 0 */",
        "",
        "    float *vals = malloc(count * sizeof(float));",
        "    if (!vals) { exit(1); }",
        "",
        "    size_t idx = 0;",
        "    for (size_t i = 0; i < n; i++)",
        "        if (!tensorBoolGet(mask, i)) vals[idx++] = fabsf(g[i]);",
        "",
        "    /* Partial selection sort, DESCENDING this time. */",
        "    for (size_t i = 0; i <= K && i < count; i++) {",
        "        size_t maxIdx = i;",
        "        for (size_t j = i + 1; j < count; j++)",
        "            if (vals[j] > vals[maxIdx]) maxIdx = j;",
        "        float tmp = vals[i];",
        "        vals[i] = vals[maxIdx];",
        "        vals[maxIdx] = tmp;",
        "    }",
        "",
        "    float thresh = vals[K < count ? K : count - 1];",
        "    free(vals);",
        "    return thresh;",
        "}",
    ], "Listing 4.1 - findAbsKthLargestInactive(), from section 7.4.")

    h2("Line by line - only the differences from Component 1")
    explain([
        ("1", "float findAbsKthLargestInactive(tensor_t *grads,",
         "**Does:** declares the GROW-side selector. "
         "**Why the first argument is GRADIENTS, not weights:** this is the "
         "conceptual heart of RigL. An inactive weight is exactly zero, so its "
         "magnitude carries no information at all. Its GRADIENT, by contrast, "
         "is the derivative of the loss with respect to that connection - a "
         "direct estimate of how much the loss would fall if it were switched "
         "on. Ranking by it is what makes RigL better than random regrowth."),
        ("2", "tensor_t *mask,", "**Does:** the same mask as Component 1, but "
         "read with the opposite polarity. **Why one mask serves both:** a "
         "single bitmap defines both sets - active is bit 1, inactive is bit 0 "
         "- so there is nothing to keep in sync."),
        ("3", "size_t K) {", "**Does:** how many connections to activate. "
         "**Why it should equal the number actually dropped, not the nominal "
         "K:** if DROP removed K+1 because of the tie behaviour in Component 1, "
         "growing only K leaves the layer one connection sparser than it "
         "started. The fix in Appendix A passes `dropped` here for exactly "
         "this reason."),
        ("4", "size_t n = calcNumberOfElementsByTensor(grads);",
         "**Does:** total elements. **Why from the gradient tensor:** it has "
         "the same shape as the weights, so either would do; taking it from the "
         "tensor actually being read keeps the function self-consistent."),
        ("5", "float *g = (float *)grads->data;",
         "**Does:** raw float view of the gradients. "
         "**If wrong:** the FQT caveat is sharper here than in Component 1. "
         "Gradient tensors in ODT are the ones most likely to be SYM_INT32, "
         "because that is the point of fully quantized training - so this cast "
         "is the first thing to revisit when FQT is switched on. Defect D3b."),
        ("7", "size_t count = 0;", "**Does:** initialises the INACTIVE "
         "counter. **Scale note:** at 90% sparsity this will reach about "
         "66,355 for the HAR layer - nine times what Component 1 counts, which "
         "is what makes this the expensive half."),
        ("8", "for (size_t i = 0; i < n; i++)", "**Does:** the counting scan, "
         "identical in structure to Component 1."),
        ("9", "if (!tensorBoolGet(mask, i)) count++;",
         "**Does:** counts CLEAR bits. "
         "**The one character that matters:** the `!`. Copying this function "
         "from its sibling and forgetting the negation gives you a threshold "
         "computed over the wrong population - and since both functions return "
         "a plausible small float, nothing about the result looks wrong."),
        ("11", "if (K >= count) return 0.0f;",
         "**Does:** the degenerate guard. "
         "**Why 0.0 and not 1e38 as in Component 1:** because the GROW "
         "comparison is `|g| >= thresh`. A threshold of zero matches every "
         "inactive weight, so all of them grow - the correct meaning of 'you "
         "asked for more than exist'. "
         "**If wrong:** returning 1e38 here, by false symmetry with Component "
         "1, would grow NOTHING while DROP still removed K - and the layer "
         "would get sparser at every RigL step until it was empty. This is the "
         "most instructive asymmetry in the whole implementation."),
        ("13", "float *vals = malloc(count * sizeof(float));",
         "**Does:** allocates the scratch buffer. "
         "**Why this is the blocker, not merely a smell:** count is the "
         "INACTIVE population, so for the HAR layer this asks for "
         "66,355 x 4 = 259 KB on a device with 320 KB of SRAM total, while "
         "weights, gradients and activations are all resident. It will not "
         "allocate. Component 1's 29 KB might; this will not. Defect D8, and "
         "the histogram replacement is in Chapter 17."),
        ("14", "if (!vals) { exit(1); }",
         "**Does:** aborts on failure - which, given the line above, is the "
         "path you should expect to take on the target. "
         "**Better:** return 1e38f, which grows nothing and lets this RigL step "
         "be skipped harmlessly, and log the failure."),
        ("16-18", "gather |g| of inactive weights into vals",
         "**Does:** the second pass, mirroring Component 1 but selecting the "
         "complementary set. "
         "**Where defect D3 becomes visible:** if the inactive gradients were "
         "never computed - because the weight-gradient matmul was masked - or "
         "were zeroed by the optimiser or by the previous rigLStep(), then "
         "every value written here is 0.0. The function still returns a "
         "number, the threshold is 0.0, and GROW then matches every inactive "
         "weight in index order. Nothing crashes; RigL simply stops being "
         "RigL."),
        ("20", "/* Partial selection sort, DESCENDING this time. */",
         "**Does:** nothing at runtime, but flags the single structural "
         "difference from Component 1."),
        ("21", "for (size_t i = 0; i <= K && i < count; i++) {",
         "**Does:** the same partial sort loop, K+1 iterations. "
         "**Cost:** count x K here is 66,355 x 2,212 = 147 M comparisons for "
         "the HAR layer - nine times Component 1, and the reason a cheaper "
         "selection method matters more on this side."),
        ("22", "size_t maxIdx = i;",
         "**Does:** tracks the largest remaining value rather than the "
         "smallest. **Why the rename from `minIdx`:** it is not cosmetic - a "
         "reader scanning for the difference between these two functions "
         "should find it in the identifier, not only in the comparison."),
        ("23-24", "if (vals[j] > vals[maxIdx]) maxIdx = j;",
         "**Does:** the comparison flipped to `>`. "
         "**This is the entire algorithmic difference** between Components 1 "
         "and 2. Everything else - the counting pass, the gather, the swap, the "
         "guards - is the same code with the mask polarity inverted."),
        ("25-27", "swap vals[i] and vals[maxIdx]",
         "**Does:** moves the largest remaining value into position `i`. "
         "**Postcondition:** positions 0..K hold the K+1 largest gradient "
         "magnitudes in DESCENDING order."),
        ("29", "float thresh = vals[K < count ? K : count - 1];",
         "**Does:** the K-th largest magnitude, zero-indexed. Toy layer: "
         "`vals[2]` = 0.40. "
         "**Defect D1, mirrored:** paired with a non-strict `>=` in rigLStep() "
         "this activates K+1 weights. Since DROP also over-selects by one, the "
         "two cancel and the active count survives - by luck rather than "
         "design, and the luck runs out when magnitudes tie unevenly."),
        ("30-31", "free(vals); return thresh;",
         "**Does:** releases the buffer and returns the threshold. "
         "**Same purity as Component 1:** no mask mutation, no global state, "
         "testable with four numbers in an array."),
    ], "Table 6.1 - Every line of findAbsKthLargestInactive(), with the "
       "differences from Component 1 called out.")
    box("key", "Why the two guards return opposite extremes",
        "This asymmetry looks like an inconsistency and is in fact the "
        "correct design. The DROP guard returns +inf so that `|w| <= inf` "
        "matches everything; the GROW guard returns 0 so that `|g| >= 0` "
        "matches everything. Both mean 'process all candidates'. If you copy "
        "one function to make the other - which is the obvious way to write "
        "them - this is the line to check first.")

    h2("Cost on the target")
    tbl(["Quantity", "Value for the HAR 1152 x 64 layer at 90% sparsity"],
        [["count (inactive)", "66,355 - nine times Component 1"],
         ["K at alpha = 0.3", "2,212"],
         ["Comparisons, O(count*K)", "66,355 x 2,212 = 147 M"],
         ["Scratch memory", "66,355 x 4 B = 259 KB on the heap"],
         ["Verdict", "Infeasible as written on a 320 KB device"]],
        widths=[34, 66], bold_first=True)
    box("warn", "This is the component that will not fit",
        "259 KB of scratch heap on a device with 320 KB of SRAM total, while "
        "the weights, gradients, activations and optimiser state are also "
        "resident, is not going to allocate. Component 2 is where the malloc "
        "approach stops being merely inelegant and becomes a blocker. The "
        "histogram alternative - two passes over the gradients accumulating "
        "counts into, say, 256 magnitude bins, then a partial scan to find the "
        "bin containing the K-th largest - needs about 1 KB and no allocation "
        "at all, at the cost of a threshold that is approximate to within one "
        "bin width. For a swap decision that is re-made every 100 steps, an "
        "approximate threshold is entirely acceptable. Chapter 17, defect D8.")


# =============================================================================
def ch_weightmask():
    chapter("Component 3 - The weightMask Field")
    origin("section 11.4 (primary) and section 39.4 (variant)")
    p("**Purpose.** Give a linear layer somewhere to keep its mask. This is "
      "two lines of code and it is the keystone of the whole implementation: "
      "the matmul, the optimiser and rigLStep() all reach for this one field. "
      "**Depends on:** nothing. **Everything else depends on it.**")
    listing([
        "/* Linear.h - add one field to the config struct */",
        "typedef struct linearConfig {",
        "    parameter_t *weights;",
        "    parameter_t *bias;",
        "    bool hasBias;",
        "    arithmetic_t arithType;",
        "    tensor_t *weightMask;   /* NEW: NULL = dense, non-NULL = RigL */",
        "} linearConfig_t;",
        "",
        "/* Linear.c - in linearInitConfig() */",
        "cfg->weightMask = NULL;     /* dense by default */",
        "",
        "/* To enable RigL on a layer, at model-build time: */",
        "tensor_t *mask = createBoolTensor(outFeatures * inFeatures);",
        "bernoulliFillMask(mask, 1.0f - targetSparsity);  /* 0.1 => 90% sparse */",
        "cfg->weightMask = mask;",
    ], "Listing 5.1 - The weightMask field and its initialisation.")

    h2("Line by line")
    explain([
        ("2", "typedef struct linearConfig {",
         "**Does:** opens the existing config struct. "
         "**Warning:** do not retype this struct from either listing in the "
         "source - sections 11.4 and 39.4 show different field lists and at "
         "least one is wrong. Open the real header and add the single field."),
        ("3-6", "weights, bias, hasBias, arithType (existing fields)",
         "**Does:** nothing new; shown for context. "
         "**Why they matter here:** `weights` is a `parameter_t`, which bundles "
         "the value tensor with its gradient tensor. rigLStep() reaches both "
         "through this one field, which is why the mask can live beside it and "
         "share a flat index with both."),
        ("7", "tensor_t *weightMask;",
         "**Does:** adds a pointer to the layer's BOOL mask tensor. "
         "**Why a pointer and not an embedded tensor_t:** a dense layer then "
         "pays 4 bytes for a null pointer instead of carrying an unused "
         "structure, and the mask can be allocated, replaced or freed "
         "independently of the config. "
         "**Why in linearConfig_t and not layer_t:** only linear layers support "
         "RigL in this implementation; putting it in the generic layer struct "
         "would imply conv and pooling layers have masks too."),
        ("8", "} linearConfig_t;",
         "**Does:** closes the struct. "
         "**Binary compatibility note:** adding a field changes `sizeof` and "
         "every offset after it. Anything that serializes this struct raw, or "
         "was compiled against the old header, must be rebuilt."),
        ("11", "cfg->weightMask = NULL;",
         "**Does:** the default, set in `linearInitConfig()`. "
         "**Why this is the single most important line in the component:** "
         "every consumer tests `if (mask != NULL)` first, so NULL means "
         "'behave exactly as before'. That is what makes this change additive - "
         "no existing model, test or checkpoint changes behaviour. "
         "**If wrong:** omit it and the pointer is whatever was on the heap. "
         "The matmul then calls `tensorBoolGet` on garbage and you get a hard "
         "fault at a random point, in code that looks unrelated."),
        ("14", "tensor_t *mask = createBoolTensor(outFeatures * inFeatures);",
         "**Does:** allocates a bit-packed mask with one bit per weight. "
         "**Why this exact size:** it must equal "
         "`calcNumberOfElementsByTensor(weights)` exactly, because the matmul, "
         "the optimiser and rigLStep() all index the mask with the weight's "
         "flat index. Note the bias is NOT masked - it is a separate tensor and "
         "biases are left dense. "
         "**Concretely:** 64 x 1152 = 73,728 bits = 9,216 bytes."),
        ("15", "bernoulliFillMask(mask, 1.0f - targetSparsity);",
         "**Does:** fills the mask with independent Bernoulli draws. "
         "**The inversion trap:** the argument is P(ACTIVE). For 90% sparsity "
         "you pass 0.1, not 0.9. Passing 0.9 gives a 90% DENSE model that "
         "trains correctly and is nine times slower than you expected - a bug "
         "with no error message. "
         "**Why the realised count is not exact:** independent draws make it "
         "binomial. For 73,728 weights at p = 0.1 the mean is 7,373 with a "
         "standard deviation of about 81, so 7,412 active is normal, not a "
         "fault. If you need exactly the target, shuffle an array with exactly "
         "that many ones instead."),
        ("16", "cfg->weightMask = mask;",
         "**Does:** attaches the mask, switching the layer into sparse mode. "
         "**What is missing here:** two things. First, `zeroInactiveWeights()` "
         "- `bernoulliFillMask` sets bits but does not touch the weights, so "
         "until you zero them the inactive positions still hold their random "
         "initial values. Section 38.4 includes that call and section 11.4 does "
         "not. Second, ownership: nothing records who frees this tensor. "
         "`linearConfig_t` already has an `ownsQuantizations` flag for exactly "
         "this kind of question, and the mask needs the same treatment or it "
         "leaks on every model teardown."),
    ], "Table 7.1 - Every line of the weightMask change. Two lines of code, "
       "and both of the notes above are things the source leaves unstated.")
    box("warn", "Two things the source leaves unstated",
        "OWNERSHIP: nothing says who frees this tensor. `linearConfig_t` "
        "already has an `ownsQuantizations` flag for exactly this kind of "
        "question, and the mask needs the same treatment or it leaks on every "
        "model teardown. ENFORCEMENT AT INIT: `bernoulliFillMask` sets the mask "
        "bits but does not touch the weights, so immediately after "
        "initialisation 90% of the weights are inactive yet still hold their "
        "random initial values. Section 38.4 calls `zeroInactiveWeights()` to "
        "fix this and section 11.4 does not mention it. If you skip it, the "
        "first forward pass is dense-valued but mask-skipped, and your loss "
        "curve starts from the wrong place.")

    h2("Two struct definitions, one field")
    p("Sections 11.4 and 39.4 both show `linearConfig_t`, and they disagree "
      "about the other fields:")
    tbl(["Section 11.4 shows", "Section 39.4 shows"],
        [["weights, bias, hasBias, arithType", "weights, bias, four separate "
          "arithmetic_t fields, two quantization_t pointers, two outputMode_t "
          "fields, ownsQuantizations"]],
        widths=[36, 64])
    p("Only the second is plausible for a library that supports FQT - the four "
      "arithmetic fields correspond to the forward, weight-gradient, "
      "bias-gradient and loss-propagation paths. The lesson for you is "
      "practical: **do not retype the struct from either listing.** Open "
      "Linear.h, find `linearConfig_t`, and add the one field. Chapter 17, "
      "defect D7.")

    h2("Memory cost")
    tbl(["Item", "Bytes", "Note"],
        [["Mask, 1152 x 64 layer", "9,216", "1 bit per weight, bit-packed"],
         ["Mask, 64 x 6 output layer", "48", "Usually left dense - see below"],
         ["Weight tensor, unchanged", "294,912", "Still stored densely, with "
          "zeros in the inactive positions"],
         ["Overhead of masking", "3.1%", "9,216 / 294,912"]],
        widths=[34, 16, 50], bold_first=True)
    box("key", "Sparse here means skipped, not absent",
        "The weight tensor keeps its full dense allocation; the mask only says "
        "which entries participate. So RigL as implemented here buys COMPUTE, "
        "not weight MEMORY - the 294 KB tensor is still 294 KB. Getting the "
        "memory back needs a compressed format such as CSR, which costs "
        "indices and destroys the O(1) random access that the mask-aware matmul "
        "relies on. For a device where the bottleneck is cycles and energy "
        "rather than flash, dense-plus-mask is the right trade, but be clear "
        "about which resource you are actually saving before quoting a 10x "
        "figure to anyone.")
    box("note", "Do not sparsify the last layer",
        "The 64 x 6 classifier holds 384 weights - 0.5% of the model. Making it "
        "90% sparse saves nothing measurable and removes connections to "
        "individual output classes, which is exactly where damage hurts most. "
        "The same argument applies to biases and normalisation parameters, and "
        "it is the standard practice from the pruning literature: leave the "
        "first and last layers dense.")


def ch_matmul():
    chapter("Component 4 - Mask-Aware Matmul")
    origin("section 8.4 (primary) and section 39.5 (variant)")
    p("**Purpose.** Skip the multiply-accumulate for inactive weights. This is "
      "the component that converts sparsity into speed: at 90% sparsity, nine "
      "of every ten inner-loop iterations exit early. **Depends on:** "
      "Component 3.")
    listing([
        "/* Matmul.c - inside matmulFloatCore(), innermost loop */",
        "for (size_t i = 0; i < aColumns; i++) {",
        "",
        "    size_t flatIdx = rowIndex * aColumns + i;",
        "",
        "    if (weightMask != NULL &&",
        "        !tensorBoolGet(weightMask, flatIdx))",
        "        continue;                  /* inactive: contributes nothing */",
        "",
        "    float aVal = readBytesAsFloat(&A->data[aByteIdx]);",
        "    float bVal = readBytesAsFloat(&B->data[bByteIdx]);",
        "    result += aVal * bVal;",
        "}",
    ], "Listing 6.1 - The masked inner loop, from section 8.4.")

    h2("Line by line")
    explain([
        ("1", "/* Matmul.c - inside matmulFloatCore() */",
         "**Does:** locates the change. **Why this function:** ODT routes every "
         "float matrix multiply through this one kernel, so a single edit "
         "covers the forward pass of every linear layer in every model."),
        ("2", "for (size_t i = 0; i < aColumns; i++) {",
         "**Does:** the reduction loop - for one output element, sum over the "
         "shared dimension. `aColumns` is the number of input features, 1,152 "
         "for the HAR layer and 4 for the toy layer. "
         "**Why this loop and not an outer one:** it executes "
         "outputs x inputs = 73,728 times per sample, which makes it the "
         "hottest code in the library and the only place where skipping work "
         "is worth a branch."),
        ("4", "size_t flatIdx = rowIndex * aColumns + i;",
         "**Does:** converts the 2-D position (output neuron, input feature) "
         "into the 1-D index the mask uses. Toy layer, output 1 and input 2: "
         "1 x 4 + 2 = 6. "
         "**Why it is correct here:** weights are stored [out, in] row-major "
         "and transposed in O(1) before the matmul, so `rowIndex` is the output "
         "neuron and `i` the input. **Why it is fragile:** that O(1) transpose "
         "is an assumption about the caller. If anyone ever makes it a real "
         "data movement, or changes the storage order, this line silently "
         "addresses the wrong bit. "
         "**If wrong:** no crash. You skip the wrong weights and the model "
         "trains to a plausible but incorrect result - the worst failure mode "
         "in this document. Chapter 3 gives the five-minute test that catches "
         "it."),
        ("6", "if (weightMask != NULL &&",
         "**Does:** tests whether this layer is sparse at all. "
         "**Why NULL-first:** C guarantees left-to-right short-circuit "
         "evaluation, so `tensorBoolGet` is never reached on a dense layer. "
         "This one test is what lets a single kernel serve both cases. "
         "**Cost on dense layers:** one perfectly predicted branch per "
         "iteration - a fraction of a cycle on an M7 with branch prediction, "
         "and the price of not maintaining two copies of the kernel."),
        ("7", "!tensorBoolGet(weightMask, flatIdx))",
         "**Does:** reads one mask bit; the negation selects INACTIVE weights. "
         "**What it compiles to:** `(data[idx>>3] >> (idx&7)) & 1` - a byte "
         "load, a shift and an AND, roughly 3-4 cycles. "
         "**The break-even calculation:** it is protecting one fused "
         "multiply-add, about 1 cycle. So the check pays only when it skips "
         "often. At 90% sparsity you spend 4 cycles to save 9 x 1 - a clear "
         "win. At 20% sparsity you spend 4 to save 0.25, and the masked kernel "
         "is SLOWER than the dense one. Sparse is not automatically fast."),
        ("8", "continue;",
         "**Does:** skips to the next input feature. "
         "**Why nothing else happens here:** no zero is accumulated, no counter "
         "incremented. The inactive weight is simply absent from the sum, which "
         "is arithmetically identical to multiplying by a stored zero - and "
         "that equivalence is exactly what the verification test in Chapter 14 "
         "exploits."),
        ("10", "float aVal = readBytesAsFloat(&A->data[aByteIdx]);",
         "**Does:** reads one activation. "
         "**Why not a direct `*(float*)` dereference:** tensor buffers are not "
         "guaranteed 4-byte aligned. On a Cortex-M7 an unaligned word load is "
         "legal but slower; on stricter cores it faults. `readBytesAsFloat` "
         "does the safe thing."),
        ("11", "float bVal = readBytesAsFloat(&B->data[bByteIdx]);",
         "**Does:** reads the corresponding weight. "
         "**Note:** this is reached only for active weights, so the memory "
         "traffic of the weight tensor also falls by the sparsity fraction - "
         "which on a bandwidth-bound device matters as much as the arithmetic "
         "saved."),
        ("12", "result += aVal * bVal;",
         "**Does:** the multiply-accumulate. "
         "**Why it is one line and not two:** an M7 with the single-precision "
         "FPU issues a fused multiply-add in one instruction, so the compiler "
         "should emit VFMA here. If it does not, check that "
         "`-ffp-contract=fast` is enabled."),
        ("13", "}",
         "**Does:** closes the reduction loop. "
         "**What has changed overall:** at 90% sparsity, nine of every ten "
         "iterations reach line 8 and stop. The instruction counter should "
         "report about 7,373 multiply-accumulates instead of 73,728 - the "
         "measurement that proves this edit is live."),
    ], "Table 8.1 - Every line of the masked inner loop.")

    h2("Plumbing the mask into the kernel")
    p("The listing assumes `weightMask` is in scope inside `matmulFloatCore()`, "
      "and in the existing code it is not. The source offers two options and "
      "recommends one:")
    tbl(["Option", "How", "Verdict"],
        [["Thread the parameter", "Add a `tensor_t *weightMask` argument to "
          "matmulFloatCore() and a new public matmulFloat32TensorsWithMask() "
          "that passes it; existing callers pass NULL",
          "Recommended. Explicit, re-entrant, and the compiler finds every call "
          "site for you"],
         ["Global context variable", "Set a file-scope mask pointer before "
          "calling the existing function", "Rejected. Not re-entrant, breaks "
          "under any future threading, and a forgotten reset silently applies "
          "one layer's mask to another"]],
        widths=[18, 52, 30], bold_first=True)

    h2("Verifying it actually works")
    box("tip", "The instruction counter test",
        "ODT exposes `getMatmulInstructionCounter()`. Run one forward pass "
        "dense and one masked at 90% sparsity on the same 64 x 1152 layer. "
        "Dense should report 73,728 multiply-accumulates; masked should report "
        "roughly 7,373. If masked still reports 73,728, the mask is not "
        "reaching the kernel - most likely you added the parameter but a "
        "wrapper is still passing NULL. If it reports something between the "
        "two, your flat index is misaligned with the mask and you are skipping "
        "the wrong weights, which is far worse than not skipping at all "
        "because the model will still appear to train.")

    h2("The gradient matmul must NOT be masked")
    box("warn", "The single most important warning in this document",
        "RigL grows connections using the gradients of INACTIVE weights. Those "
        "gradients come from the weight-gradient matmul, dL/dW = delta^T x, "
        "which is a different call from the forward matmul. If you apply the "
        "mask to the weight-gradient computation as well - which looks "
        "consistent and saves more compute - then every inactive weight has a "
        "gradient of exactly zero, `findAbsKthLargestInactive()` returns 0, and "
        "the GROW step selects essentially arbitrary positions. The model will "
        "still train, the sparsity will still look correct, and the mask will "
        "be evolving at random: you will have implemented static sparse "
        "training with extra steps. MASK THE FORWARD MATMUL AND THE "
        "LOSS-PROPAGATION MATMUL; LEAVE THE WEIGHT-GRADIENT MATMUL DENSE. "
        "Chapter 17, defect D3.")
    p("This is also where RigL's real cost sits. The forward pass gets nine "
      "tenths cheaper, but the weight-gradient pass stays dense, so the "
      "end-to-end training speedup is well under the 10x that the sparsity "
      "figure suggests. The published algorithm accepts exactly this trade: "
      "dense gradients are the price of learning the connectivity.")


# =============================================================================
def ch_sgd():
    chapter("Component 5 - Mask-Aware SGD")
    origin("section 12.4 (primary) and section 39.6 (variant)")
    p("**Purpose.** Stop the optimiser from moving inactive weights away from "
      "zero. Without this, weight decay, momentum and any residual gradient "
      "will gradually give every 'pruned' weight a non-zero value, and the "
      "sparsity becomes a fiction that only the mask believes in. "
      "**Depends on:** Component 3.")
    listing([
        "static void sgdUpdateKernelMasked(tensor_t **op, size_t n,",
        "                                  tensor_t *rawOut, tensor_t *aux,",
        "                                  const void *ctxv) {",
        "    const sgdUpdateCtx_t *ctx = ctxv;",
        "    tensor_t *mask = ctx->weightMask;      /* NULL for dense layers */",
        "",
        "    float *param = (float *)op[0]->data;",
        "    float *grad  = (float *)op[1]->data;",
        "    float *out   = (float *)rawOut->data;",
        "    size_t nElem = calcNumberOfElementsByTensor(rawOut);",
        "",
        "    for (size_t i = 0; i < nElem; i++) {",
        "",
        "        if (mask != NULL && !tensorBoolGet(mask, i)) {",
        "            out[i]  = 0.0f;",
        "            grad[i] = 0.0f;",
        "            continue;",
        "        }",
        "",
        "        float g = grad[i] + ctx->weightDecay * param[i];",
        "        out[i]  = param[i] - ctx->lr * g;",
        "    }",
        "}",
    ], "Listing 7.1 - Mask-aware SGD update, merged from sections 12.4 and 39.6.")

    h2("Line by line")
    explain([
        ("1-3", "static void sgdUpdateKernelMasked(tensor_t **op, ...)",
         "**Does:** declares an ODT kernel - invoked through the executeOp "
         "funnel with an operand array rather than named tensors. "
         "**Why `static`:** file-local; the funnel holds the pointer, so no "
         "external linkage is needed. "
         "**Design note:** the source presents this as a NEW function beside "
         "the existing `sgdUpdateKernel`. Adding the mask check to the existing "
         "one, with NULL meaning dense, would avoid two nearly identical "
         "kernels drifting apart."),
        ("4", "const sgdUpdateCtx_t *ctx = ctxv;",
         "**Does:** recovers the typed context from the funnel's `void *`. "
         "**Why `const`:** the kernel reads hyperparameters and must not "
         "mutate them; the qualifier lets the compiler keep `lr` in a register "
         "across the loop."),
        ("5", "tensor_t *mask = ctx->weightMask;",
         "**Does:** fetches the mask from the optimiser context. "
         "**Why from the context and not the operands:** operands are the "
         "tensors being updated; the mask is configuration. "
         "**The plumbing step everyone forgets:** `sgdUpdateCtx_t` needs this "
         "new field AND something must copy `linearConfig_t.weightMask` into it "
         "when the optimiser is configured. Miss that and the code compiles, "
         "runs, and masks nothing."),
        ("7", "float *param = (float *)op[0]->data;",
         "**Does:** the current weights. **Why index 0:** the funnel's operand "
         "ordering convention - parameters first, gradients second."),
        ("8", "float *grad = (float *)op[1]->data;",
         "**Does:** the gradients accumulated since the last update."),
        ("9", "float *out = (float *)rawOut->data;",
         "**Does:** where the new weights are written. "
         "**Why a separate pointer:** `out` and `param` MAY alias the same "
         "buffer for an in-place update. Nothing in this kernel breaks if they "
         "do, because every element is read before it is written."),
        ("10", "size_t nElem = calcNumberOfElementsByTensor(rawOut);",
         "**Does:** the element count, taken from the OUTPUT tensor. "
         "**If wrong:** the mask must have exactly this many bits. A mismatch "
         "reads past the mask's storage - one of the few ways this code can "
         "corrupt memory rather than merely compute the wrong answer."),
        ("12", "for (size_t i = 0; i < nElem; i++) {",
         "**Does:** one pass over every parameter. "
         "**Cost context:** this runs once per optimiser step, not once per "
         "multiply-accumulate, so unlike the matmul the branch below costs "
         "nothing worth measuring. The mask check here is about correctness."),
        ("14", "if (mask != NULL && !tensorBoolGet(mask, i)) {",
         "**Does:** selects inactive weights. "
         "**Why the same NULL-first pattern as the matmul:** dense layers must "
         "behave exactly as before, so that adding RigL cannot regress any "
         "existing model."),
        ("15", "out[i] = 0.0f;",
         "**Does:** forces the weight to exactly zero. "
         "**Why not simply skip the write:** if you `continue` without writing, "
         "the weight keeps its old value. The masked matmul ignores it, so "
         "every test still passes - until the model is checkpointed and "
         "reloaded with a lost or misaligned mask, at which point untrained "
         "values are suddenly live. Writing the zero puts the invariant in the "
         "DATA, and the data is what survives serialization."),
        ("16", "grad[i] = 0.0f;",
         "**Does:** clears the gradient accumulator for this position. "
         "**Why gradients need clearing at all:** ODT accumulates gradients "
         "across micro-batches, so without a reset the sums grow without "
         "bound. "
         "**The tension with RigL:** this line destroys exactly the signal "
         "GROW ranks by. It is safe only because rigLStep() runs BEFORE the "
         "optimiser in the same iteration. Reverse the order and every inactive "
         "gradient is zero by the time GROW looks - defects D3 and D4."),
        ("17", "continue;",
         "**Does:** skips the update arithmetic for this element."),
        ("18", "}",
         "**Does:** closes the inactive branch. "
         "**Missing here:** the momentum buffer. If your SGD carries velocity, "
         "a regrown weight inherits the velocity it had before it was dropped "
         "and takes its first step in a stale direction. Clear it in this "
         "branch. Defect D5."),
        ("20", "float g = grad[i] + ctx->weightDecay * param[i];",
         "**Does:** adds L2 weight decay to the gradient. "
         "**Why COUPLED and not decoupled:** for plain SGD the two formulations "
         "differ only by a factor of the learning rate, so folding decay into "
         "the gradient is standard. AdamW is the case where the distinction "
         "matters, because its adaptive scaling would otherwise divide the "
         "decay away - see Chapter 10, line 15."),
        ("21", "out[i] = param[i] - ctx->lr * g;",
         "**Does:** the gradient descent step. "
         "**Why this is the whole of SGD:** everything else in this kernel is "
         "bookkeeping. Momentum, if configured, is applied elsewhere in the ODT "
         "pipeline, which is why it is not visible - and why it is easy to "
         "forget when adding the mask."),
        ("22-23", "} }",
         "**Does:** closes the loop and the function. "
         "**Postcondition worth asserting in a test:** after this kernel, every "
         "position whose mask bit is 0 holds exactly 0.0f in both `out` and "
         "`grad`. That is a two-line check and it catches most plumbing "
         "mistakes."),
    ], "Table 9.1 - Every line of the mask-aware SGD kernel.")
    box("key", "Why forcing the weight to zero matters more than it looks",
        "Suppose you skip line 15 and simply `continue` without writing. The "
        "inactive weight keeps whatever value it had. The masked matmul still "
        "ignores it, so the forward pass is unchanged and every test passes. "
        "Then you checkpoint the model, and on reload the mask is gone or "
        "misaligned - and suddenly those weights are live again with values "
        "that were never trained. Writing the zero makes the invariant "
        "'inactive implies zero' hold in the DATA, not just in the mask, and "
        "the data is what survives serialization.")


def ch_adamw():
    chapter("Component 5b - Mask-Aware AdamW")
    origin("section 13.4")
    p("**Purpose.** The same protection as Component 5, plus one extra step "
      "that SGD does not need: clearing the first and second moment buffers "
      "for inactive weights. **Depends on:** Component 3. **Optional** - "
      "needed only if you train with AdamW rather than SGD.")
    listing([
        "for (size_t i = 0; i < n; i++) {",
        "",
        "    if (mask != NULL && !tensorBoolGet(mask, i)) {",
        "        param[i] = 0.0f;",
        "        grad[i]  = 0.0f;",
        "        m[i]     = 0.0f;      /* clear first-moment history  */",
        "        v[i]     = 0.0f;      /* clear second-moment history */",
        "        continue;",
        "    }",
        "",
        "    float g = grad[i];",
        "    m[i] = beta1 * m[i] + (1.0f - beta1) * g;",
        "    v[i] = beta2 * v[i] + (1.0f - beta2) * g * g;",
        "    param[i] -= lrCorr * m[i] / (sqrtf(v[i]) + eps);",
        "    param[i] -= lr * weightDecay * param[i];",
        "    grad[i] = 0.0f;",
        "}",
    ], "Listing 8.1 - Mask-aware AdamW, from section 13.4.")

    h2("Line by line - what differs from SGD")
    explain([
        ("1", "for (size_t i = 0; i < n; i++) {",
         "**Does:** one pass over every parameter, exactly as in SGD. "
         "**Why AdamW needs its own kernel at all:** it carries two extra "
         "per-parameter state tensors, `m` and `v`, and those must be masked "
         "too - which is the whole reason this component exists separately."),
        ("3", "if (mask != NULL && !tensorBoolGet(mask, i)) {",
         "**Does:** selects inactive weights, same NULL-first pattern as "
         "everywhere else."),
        ("4", "param[i] = 0.0f;",
         "**Does:** forces the weight to exactly zero, as in SGD. "
         "**Why it is written to `param` here and to `out` in the SGD kernel:** "
         "the AdamW kernel updates in place, so there is no separate output "
         "tensor. Check which convention your ODT build uses before copying "
         "either listing."),
        ("5", "grad[i] = 0.0f;",
         "**Does:** clears the gradient accumulator. "
         "**Same tension as SGD line 16:** this destroys the signal GROW needs, "
         "and is safe only because rigLStep() runs first in the iteration."),
        ("6", "m[i] = 0.0f;",
         "**Does:** clears the first-moment estimate - the exponential moving "
         "average of the gradient. "
         "**Why this line exists, concretely:** suppose a weight is dropped at "
         "step 1000 and regrown at step 1500. Without clearing, `m` still holds "
         "the average gradient from before the drop. On the first step after "
         "regrowth, Adam applies that stale direction at full size to a weight "
         "that was just reset to zero - a large, confident step computed from "
         "history that no longer describes the loss surface. Clearing it means "
         "the regrown weight's first update comes only from its current "
         "gradient, exactly as a freshly initialised parameter's would."),
        ("7", "v[i] = 0.0f;",
         "**Does:** clears the second-moment estimate - the moving average of "
         "the squared gradient. "
         "**Why the effect is subtler than for `m`:** Adam divides by "
         "sqrt(v_hat), so a stale LARGE v would make the regrown weight almost "
         "frozen - it would sit at zero and contribute nothing for hundreds of "
         "steps, quietly wasting the connection RigL just spent budget to "
         "create. With v cleared, the bias correction makes the first step "
         "approximately +/- the learning rate, the same size any fresh "
         "parameter takes."),
        ("8", "continue;",
         "**Does:** skips the Adam arithmetic. "
         "**Also missing here, as in SGD:** nothing resets the step counter "
         "used for bias correction. Adam's correction terms depend on a global "
         "`t`, so a regrown weight is treated as if it had been training since "
         "step 0. With m and v both zero the practical effect is small, but it "
         "is worth knowing when reading the first update after a grow."),
        ("9", "}", "**Does:** closes the inactive branch. Everything below is "
         "reached only by active weights."),
        ("11", "float g = grad[i];",
         "**Does:** takes the raw gradient. "
         "**Note what is NOT added here:** weight decay. Unlike the SGD kernel, "
         "which folds decay into `g`, AdamW applies it separately on line 15 - "
         "that separation is the entire difference between Adam and AdamW."),
        ("12", "m[i] = beta1 * m[i] + (1.0f - beta1) * g;",
         "**Does:** updates the first moment - an exponential moving average of "
         "the gradient with beta1, typically 0.9. "
         "**Intuition:** momentum. It smooths the noisy per-batch gradient into "
         "a running direction, so that consistent signal accumulates and "
         "oscillation cancels."),
        ("13", "v[i] = beta2 * v[i] + (1.0f - beta2) * g * g;",
         "**Does:** updates the second moment - the moving average of the "
         "SQUARED gradient, with beta2 typically 0.999. "
         "**Intuition:** a per-parameter estimate of how large gradients "
         "usually are here. Dividing by its square root on the next line gives "
         "every parameter a step size scaled to its own gradient history, which "
         "is why Adam needs so little tuning across layers of very different "
         "magnitudes."),
        ("14", "param[i] -= lrCorr * m[i] / (sqrtf(v[i]) + eps);",
         "**Does:** the Adam step. "
         "**Why `lrCorr` rather than `lr`:** it folds in both bias corrections, "
         "1/(1-beta1^t) and 1/(1-beta2^t), so the division happens once per "
         "element instead of twice - worth doing on an M7 where a float divide "
         "costs about 14 cycles. "
         "**Why `+ eps` and not a zero check:** v is zero for a parameter that "
         "has never seen a gradient - including every weight RigL just grew - "
         "so without eps this divides by zero on the first step after every "
         "single grow."),
        ("15", "param[i] -= lr * weightDecay * param[i];",
         "**Does:** decoupled weight decay, applied to the parameter directly. "
         "**Why it is a separate line and not folded into `g`:** if decay went "
         "through the gradient it would be divided by sqrt(v) along with "
         "everything else, so parameters with large gradients would be barely "
         "regularised and parameters with small ones heavily. Keeping it "
         "outside the adaptive scaling is the W in AdamW, and it reliably "
         "improves generalisation."),
        ("16", "grad[i] = 0.0f;",
         "**Does:** resets the accumulator for the next micro-batch, on the "
         "ACTIVE path this time."),
        ("17", "}", "**Does:** closes the loop. "
         "**Memory reality check:** this kernel touches four dense float "
         "tensors per layer - param, grad, m, v - which for the HAR 1152 x 64 "
         "layer is 1.13 MB. That does not fit in 320 KB, whatever the sparsity, "
         "because m and v are allocated densely regardless of the mask. Defect "
         "D6."),
    ], "Table 10.1 - Every line of the mask-aware AdamW update.")
    box("note", "Also clear the SGD momentum buffer",
        "Section 13.4 correctly identifies stale moments as a hazard for AdamW "
        "and says nothing about SGD with momentum, which has exactly the same "
        "problem in a milder form: a regrown weight inherits the velocity it "
        "had before it was dropped. If your SGD carries a momentum buffer, "
        "clear that entry too, in the branch on line 14-18 of Listing 7.1. "
        "Chapter 17, defect D5.")

    h2("Memory cost of AdamW under sparsity")
    tbl(["Tensor", "Elements", "Bytes", "Note"],
        [["Weights", "73,728", "294,912", "Dense storage regardless of mask"],
         ["Gradients", "73,728", "294,912", "Must stay dense - GROW needs them"],
         ["m (first moment)", "73,728", "294,912", "Allocated densely"],
         ["v (second moment)", "73,728", "294,912", "Allocated densely"],
         ["Mask", "73,728 bits", "9,216", "3% overhead"],
         ["Total for one layer", "-", "1,188,864", "1.13 MB - exceeds the "
          "320 KB SRAM on its own"]],
        widths=[24, 18, 16, 42], bold_first=True)
    box("warn", "AdamW plus this layer does not fit on the target",
        "Section 13.4 states the AdamW cost as 88 KB by counting only the 7,373 "
        "ACTIVE weights. That figure is right only if the moment tensors are "
        "stored sparsely - and nothing in the implementation does that; `m` and "
        "`v` are allocated with the same dense shape as the parameters. The "
        "honest number for this layer is 1.13 MB, which does not fit. Either "
        "use SGD (which needs no moment buffers and brings the layer to 599 KB "
        "- still too large), or shrink the layer, which is what the source "
        "itself recommends in section 39.10 when it suggests a Conv1d feature "
        "extractor ahead of a much smaller linear head. Chapter 17, defect D6.")


# =============================================================================
def ch_riglstep():
    chapter("Component 6 - rigLStep(), the Algorithm Itself")
    origin("section 39.7, with the DROP/GROW logic cross-checked against "
           "sections 2.2 and 33.4")
    p("**Purpose.** Everything so far has been scaffolding. This function is "
      "RigL: it computes the swap size from the cosine schedule, drops the "
      "weakest active weights, grows the most promising inactive ones, and "
      "leaves the layer with the same number of active weights it started "
      "with. **Depends on:** Components 1, 2 and 3.")
    listing([
        "void rigLStep(layer_t **model, size_t numLayers,",
        "              float sparsityTarget, size_t step, size_t totalSteps) {",
        "",
        "    /* Cosine decay of the swap fraction. */",
        "    float prog  = (float)step / (float)(totalSteps > 0 ? totalSteps : 1);",
        "    float alpha = 0.3f * 0.5f * (1.0f + cosf(3.14159265f * prog));",
        "",
        "    for (size_t l = 0; l < numLayers; l++) {",
        "",
        "        if (model[l]->type != LINEAR) continue;",
        "",
        "        linearConfig_t *cfg = model[l]->config->linear;",
        "        tensor_t *mask = cfg->weightMask;",
        "        if (mask == NULL) continue;          /* dense layer */",
        "",
        "        tensor_t *weights = cfg->weights->param;",
        "        tensor_t *grads   = cfg->weights->grad;",
        "        size_t n = calcNumberOfElementsByTensor(weights);",
        "        float *w = (float *)weights->data;",
        "        float *g = (float *)grads->data;",
        "",
        "        size_t numActive = 0;",
        "        for (size_t i = 0; i < n; i++)",
        "            if (tensorBoolGet(mask, i)) numActive++;",
        "",
        "        size_t K = (size_t)(alpha * (float)numActive);",
        "        if (K == 0) continue;                /* nothing to swap */",
        "",
        "        /* ---- DROP: deactivate the K smallest |w| ---- */",
        "        float dropThresh = findAbsKthSmallestActive(weights, mask, K);",
        "        for (size_t i = 0; i < n; i++) {",
        "            if (tensorBoolGet(mask, i) && fabsf(w[i]) <= dropThresh) {",
        "                tensorBoolSet(mask, i, false);",
        "                w[i] = 0.0f;",
        "            }",
        "        }",
        "",
        "        /* ---- GROW: activate the K largest |g| among inactive ---- */",
        "        float growThresh = findAbsKthLargestInactive(grads, mask, K);",
        "        for (size_t i = 0; i < n; i++) {",
        "            if (!tensorBoolGet(mask, i) && fabsf(g[i]) >= growThresh) {",
        "                tensorBoolSet(mask, i, true);",
        "                w[i] = 0.0f;                 /* grow at zero */",
        "            }",
        "        }",
        "",
        "        /* ---- Zero the gradients of still-inactive weights ---- */",
        "        for (size_t i = 0; i < n; i++)",
        "            if (!tensorBoolGet(mask, i)) g[i] = 0.0f;",
        "    }",
        "}",
    ], "Listing 9.1 - rigLStep(), transcribed from section 39.7.")

    h2("Line by line")
    explain([
        ("1", "void rigLStep(layer_t **model,",
         "**Does:** declares the entry point. Returns `void` - the function "
         "reports nothing and mutates the model in place. "
         "**Why:** `layer_t **` is an array of layer pointers, the same "
         "representation the training loop already holds, so no conversion is "
         "needed at the call site. "
         "**If wrong:** passing a `layer_t *` (array of structs) instead of "
         "`layer_t **` compiles with a warning and then walks memory at the "
         "wrong stride."),
        ("2", "size_t numLayers, float sparsityTarget,",
         "**Does:** the layer count and, nominally, the target sparsity. "
         "**Why:** `numLayers` is needed because C arrays carry no length. "
         "**Note:** `sparsityTarget` is **never read in the body**. Sparsity is "
         "fixed once by `bernoulliFillMask()` at initialisation; this function "
         "only preserves whatever the mask already encodes. The parameter is "
         "misleading and should be removed or honoured."),
        ("2", "size_t step, size_t totalSteps) {",
         "**Does:** the current global step and the schedule horizon. "
         "**Why:** the pair defines training progress, which drives alpha. "
         "**If wrong:** passing the true total instead of 0.8 x total leaves "
         "alpha non-zero into the final epoch, so connections are still being "
         "swapped when there is no time left to train them - defect D9."),
        ("4", "/* Cosine decay of the swap fraction. */",
         "**Does:** nothing at runtime. **Why:** marks the boundary between the "
         "schedule computation, which is per-call, and the per-layer loop that "
         "follows."),
        ("5", "float prog = (float)step / (float)(totalSteps > 0 ? ... : 1);",
         "**Does:** training progress as a fraction in [0, 1]. "
         "**Why:** both operands are cast to `float` FIRST. `step/totalSteps` "
         "in integer arithmetic would be 0 for the entire run except the last "
         "step, making alpha constant at alphaInit and the mask thrash until "
         "training ended. The ternary guards a caller that passes 0. "
         "**If wrong:** dropping either cast is the single most likely silent "
         "bug in this function - it compiles, runs, and produces a schedule "
         "that never decays."),
        ("6", "float alpha = 0.3f * 0.5f * (1.0f + cosf(3.14159265f * prog));",
         "**Does:** evaluates alpha(t) = (alphaInit/2)(1 + cos(pi t / T_end)). "
         "At prog=0, cos(0)=1 so alpha=0.3; at prog=1, cos(pi)=-1 so alpha=0. "
         "**Why the halving:** cos ranges over [-1, 1], so (1+cos) ranges over "
         "[0, 2]; multiplying by 0.5 brings it to [0, 1] and by 0.3 to "
         "[0, 0.3]. **Why cosine and not linear:** the derivative is zero at "
         "both ends, so the swap rate changes slowly at the start (while the "
         "network is still finding structure) and slowly at the end (while it "
         "settles), and fastest in the middle. "
         "**Note:** 0.3f and the constant pi are hard-coded; both belong in "
         "parameters."),
        ("8", "for (size_t l = 0; l < numLayers; l++) {",
         "**Does:** iterates every layer of the model. "
         "**Why:** one call updates the whole model, so the training loop needs "
         "a single line rather than a loop of its own. Note that alpha is "
         "computed once, outside this loop - every layer swaps the same "
         "FRACTION, not the same COUNT."),
        ("10", "if (model[l]->type != LINEAR) continue;",
         "**Does:** skips anything that is not a fully connected layer. "
         "**Why this is not optional:** `config` is a UNION. Reading "
         "`->linear` on a Conv1d layer does not fail - it reinterprets those "
         "bytes as a `linearConfig_t` and hands you a garbage `weightMask` "
         "pointer that will be dereferenced two lines later. "
         "**Consequence:** conv kernels are never sparsified, even though "
         "section 20.4 of the source describes a `kernelMask` for them."),
        ("12", "linearConfig_t *cfg = model[l]->config->linear;",
         "**Does:** narrows the union to the linear view. "
         "**Why:** every field this function needs - the mask, the weights, the "
         "gradients - hangs off this one pointer, so it is worth naming once "
         "rather than repeating the chain."),
        ("13", "tensor_t *mask = cfg->weightMask;",
         "**Does:** fetches the layer's mask. "
         "**Why:** this single field is what distinguishes a sparse layer from "
         "a dense one; everything below branches on it."),
        ("14", "if (mask == NULL) continue;",
         "**Does:** skips dense layers. "
         "**Why:** combined with line 10, this makes `rigLStep()` safe to call "
         "on any model at all - including a fully dense one, where it does "
         "nothing. That is what lets the training loop call it "
         "unconditionally. **If wrong:** omitting it dereferences NULL on the "
         "first dense layer, which at least fails loudly."),
        ("16", "tensor_t *weights = cfg->weights->param;",
         "**Does:** the weight tensor. **Why:** DROP ranks by |weight|, so this "
         "is the DROP input. Note `cfg->weights` is a `parameter_t`, which "
         "bundles the values and their gradients - line 17 takes the other "
         "half."),
        ("17", "tensor_t *grads = cfg->weights->grad;",
         "**Does:** the gradient tensor, filled by the backward pass of this "
         "same iteration. **Why:** GROW ranks by |gradient|. "
         "**Critical:** these gradients must be present for INACTIVE weights, "
         "which means the weight-gradient matmul must not be masked and the "
         "optimiser must not have run yet. This one line is where defect D3 "
         "bites."),
        ("18", "size_t n = calcNumberOfElementsByTensor(weights);",
         "**Does:** the element count - 73,728 for the HAR layer, 8 for the toy "
         "layer of Chapter 2. **Why:** every loop below runs over it, and the "
         "mask must have exactly this many bits. **If wrong:** a mask sized "
         "differently from the weights reads past its own buffer."),
        ("19", "float *w = (float *)weights->data;",
         "**Does:** a raw float view of the weights. "
         "**Why:** the tensor accessors would cost a function call per element "
         "inside three O(n) loops. **If wrong:** valid ONLY for FLOAT32. Under "
         "FQT the tensor holds int32 mantissas, and this cast reinterprets "
         "their bit patterns as floats - producing magnitudes with no relation "
         "to the real weights, so DROP selects essentially at random."),
        ("20", "float *g = (float *)grads->data;",
         "**Does:** the same for gradients. **Why and if wrong:** identical to "
         "line 19; in ODT the gradient tensor is if anything MORE likely to be "
         "SYM_INT32 than the weight tensor."),
        ("22", "size_t numActive = 0;",
         "**Does:** initialises the active-weight counter. "
         "**Why:** the count is not stored anywhere - the mask is the only "
         "record of it, so it must be recomputed each time."),
        ("23-24", "for (i...) if (tensorBoolGet(mask, i)) numActive++;",
         "**Does:** counts set bits. For the toy layer: 4. For the HAR layer at "
         "initialisation: about 7,412. "
         "**Why:** K is a fraction of the ACTIVE count, not of n. "
         "**Cost:** this is the third full pass over the mask in this function "
         "and `findAbsKthSmallestActive()` will make two more; caching the "
         "count in the layer config would remove three O(n) scans per step."),
        ("26", "size_t K = (size_t)(alpha * (float)numActive);",
         "**Does:** how many weights to swap. Toy layer: 0.5 x 4 = 2. HAR at "
         "step 0: 0.3 x 7,412 = 2,223. "
         "**Why the cast:** truncation toward zero implements the floor() of "
         "the published algorithm. "
         "**Why active and not n:** section 2.2 defines K = alpha (1-s) N, and "
         "numActive IS (1-s)N - so this matches, and it also means K shrinks "
         "automatically if sparsity ever drifts."),
        ("27", "if (K == 0) continue;",
         "**Does:** skips the layer once the swap size rounds to zero. "
         "**Why:** this is how the mask freezes at the end of the schedule - "
         "there is no separate end-of-schedule test. It also protects "
         "`findAbsKthSmallestActive(..., 0)` from being asked for a "
         "zeroth-smallest element."),
        ("29", "/* ---- DROP: deactivate the K smallest |w| ---- */",
         "**Does:** nothing at runtime, but marks the first of the three phases "
         "- DROP, GROW, clear - that every reader should be able to name."),
        ("30", "float dropThresh = findAbsKthSmallestActive(weights, mask, K);",
         "**Does:** computes the DROP threshold using Component 1. Toy layer: "
         "0.30. **Why it is computed BEFORE the loop:** the threshold must "
         "describe the mask as it was at the start of the step. Recomputing it "
         "inside the loop would make each decision depend on the previous "
         "ones."),
        ("31", "for (size_t i = 0; i < n; i++) {",
         "**Does:** walks every weight, active or not. "
         "**Why not just the active ones:** there is no list of active indices "
         "- the mask is a bitmap, so finding them requires this scan anyway."),
        ("32", "if (tensorBoolGet(mask, i) && fabsf(w[i]) <= dropThresh) {",
         "**Does:** selects active weights at or below the threshold. "
         "**Why the mask test first:** short-circuit evaluation skips the "
         "`fabsf` for the 90% of weights that are inactive. "
         "**If wrong - and it is wrong as written:** the non-strict `<=` "
         "combined with a zero-indexed K-th value selects K+1 weights, and "
         "more when magnitudes tie. In the toy layer it drops index 4 "
         "(|w| = 0.30 = the threshold) which should have survived. Use a "
         "strict `<`. Defect D1."),
        ("33", "tensorBoolSet(mask, i, false);",
         "**Does:** clears the mask bit - the connection is now inactive. "
         "**Why here rather than in a second pass:** the GROW loop that follows "
         "reads this same mask, so the DROP must be complete first."),
        ("34", "w[i] = 0.0f;",
         "**Does:** zeroes the weight itself. "
         "**Why it matters more than it looks:** without it the value survives "
         "in the tensor, invisible because the matmul skips it - until the "
         "model is serialized and reloaded with a lost or misaligned mask, at "
         "which point untrained values come back to life. Writing the zero "
         "puts the invariant in the DATA, and the data is what persists."),
        ("35-36", "} }",
         "**Does:** closes the conditional and the DROP loop. At this point the "
         "layer is temporarily BELOW its target density - the toy layer has 2 "
         "active weights instead of 4."),
        ("38", "/* ---- GROW: activate K largest |g| among inactive ---- */",
         "**Does:** marks phase two. **Why the order matters:** DROP frees the "
         "budget that GROW spends. Reversing them would push the layer above "
         "target density before trimming it back."),
        ("39", "float growThresh = findAbsKthLargestInactive(grads, mask, K);",
         "**Does:** computes the GROW threshold using Component 2. Toy layer: "
         "0.40. "
         "**If wrong - and it is:** `mask` here is the POST-drop mask, so the "
         "K weights just deactivated are candidates for immediate reactivation. "
         "In the toy layer index 1 is dropped for |w| = 0.05 and instantly "
         "regrown for |g| = 0.85, destroying a trained value and consuming "
         "part of the swap budget. Pass a snapshot of the pre-drop mask. "
         "Defect D2."),
        ("40", "for (size_t i = 0; i < n; i++) {",
         "**Does:** a second full scan. **Why a separate loop:** the threshold "
         "on line 39 must see the completed DROP, so the two phases cannot be "
         "fused into one pass."),
        ("41", "if (!tensorBoolGet(mask, i) && fabsf(g[i]) >= growThresh) {",
         "**Does:** selects inactive weights whose gradient is at or above the "
         "threshold. **Why gradient and not weight:** an inactive weight is "
         "zero, so its magnitude carries no information; its GRADIENT says how "
         "much the loss would fall if it were switched on. This is the entire "
         "idea of RigL in one condition. "
         "**If wrong:** the non-strict `>=` mirrors defect D1 and grows K+1. "
         "The two errors cancel in the count, which is luck rather than "
         "design."),
        ("42", "tensorBoolSet(mask, i, true);",
         "**Does:** sets the mask bit - the connection is live from the next "
         "forward pass onward."),
        ("43", "w[i] = 0.0f;    /* grow at zero */",
         "**Does:** starts the new connection at exactly zero. "
         "**Why not at a random value:** the network is mid-convergence; "
         "injecting an arbitrary weight is a perturbation with no justification. "
         "Starting at zero means the connection contributes nothing at first "
         "and is shaped entirely by gradients - it earns its value. "
         "**Consequence:** a grown weight needs time to become useful, which is "
         "exactly why the mask must freeze well before training ends."),
        ("44-45", "} }",
         "**Does:** closes the GROW loop. Density is now back at target - the "
         "toy layer has 4 active weights again, at positions {0, 4, 5, 7}."),
        ("47", "/* ---- Zero gradients of still-inactive weights ---- */",
         "**Does:** marks phase three, the one most readers skip."),
        ("48-49", "for (i...) if (!tensorBoolGet(mask,i)) g[i] = 0.0f;",
         "**Does:** clears the gradient of every weight that remains inactive. "
         "**Why:** without it, a weight that once had a large gradient keeps "
         "that stale value and looks permanently attractive to every future "
         "GROW step, so the same few positions would be selected again and "
         "again. **Interaction:** these gradients will be refilled by the next "
         "backward pass, which is why the dense weight-gradient matmul is "
         "non-negotiable."),
        ("50", "}",
         "**Does:** closes the per-layer loop. Each layer is handled "
         "independently and shares only the alpha computed on line 6."),
        ("51", "}",
         "**Does:** end of function. Nothing is returned and nothing is "
         "allocated, so there is nothing for the caller to clean up - which is "
         "why the D2 fix in Appendix A has to be careful to free the mask "
         "snapshot it introduces."),
    ], "Table 11.1 - Every line of rigLStep(). Values quoted as 'toy layer' "
       "refer to the 8-weight example computed in Chapter 2.")

    h2("What one call actually does, in order")
    diagram([
        "  step 900, alpha = 0.28, layer has 7,373 active of 73,728",
        "",
        "  1. K = floor(0.28 * 7373) = 2,064",
        "  2. dropThresh = 2064-th smallest |w| among the 7,373 active",
        "  3. DROP  : ~2,065 weights  mask 1->0, w := 0",
        "             active: 7,373 -> 5,308",
        "  4. growThresh = 2064-th largest |g| among the now-68,420 inactive",
        "  5. GROW  : ~2,065 weights  mask 0->1, w := 0",
        "             active: 5,308 -> 7,373        <- conserved",
        "  6. zero g[i] for all 66,355 still-inactive weights",
        "",
        "  net effect: 2,065 connections have moved to better positions,",
        "              the active count is unchanged, and 2,065 weights",
        "              that were carrying trained values are now zero.",
    ], "Figure 9.1 - One rigLStep() on the HAR layer at step 900.")
    box("key", "The cost nobody mentions",
        "Every swap throws away a trained weight and installs a zero. At alpha "
        "= 0.3 that is 28% of the layer's learned values discarded in a single "
        "step. This is why the cosine decay is not optional and why the "
        "interval T matters: swap too often, or keep alpha high for too long, "
        "and the network spends the whole run relearning connections instead of "
        "converging. If your loss spikes at every multiple of 100 steps and "
        "does not recover before the next one, alpha is too high or T is too "
        "small.")


def ch_serialize():
    chapter("Component 7 - Persisting the Mask")
    origin("section 17.5 (both functions) and section 39.8 (write only)")
    p("**Purpose.** Save the mask with the checkpoint and load it back. After "
      "50 epochs the mask IS the learned architecture - which 10% of "
      "connections matter - and a checkpoint without it restores a model that "
      "is dense, wrong, and 10x slower. **Depends on:** Component 3.")
    listing([
        "void serializeSparsity(tensor_t *mask, FILE *fp) {",
        "",
        "    if (mask == NULL || mask->quantization->type != BOOL) {",
        "        uint8_t noMask = 0;",
        "        fwrite(&noMask, 1, 1, fp);",
        "        return;",
        "    }",
        "",
        "    uint8_t hasMask = 1;",
        "    fwrite(&hasMask, 1, 1, fp);",
        "",
        "    size_t n     = calcNumberOfElementsByTensor(mask);",
        "    size_t bytes = (n + 7) / 8;",
        "    fwrite(mask->data, 1, bytes, fp);",
        "}",
        "",
        "tensor_t *deserializeSparsity(size_t n, FILE *fp) {",
        "",
        "    uint8_t hasMask = 0;",
        "    fread(&hasMask, 1, 1, fp);",
        "    if (!hasMask) return NULL;          /* dense layer */",
        "",
        "    tensor_t *mask = allocBoolTensor(n);",
        "    size_t bytes = (n + 7) / 8;",
        "    fread(mask->data, 1, bytes, fp);",
        "    return mask;",
        "}",
    ], "Listing 10.1 - Mask serialization, from section 17.5.")

    h2("Line by line")
    explain([
        ("1", "void serializeSparsity(tensor_t *mask, FILE *fp) {",
         "**Does:** writes one mask to an open file. "
         "**Why it takes the mask as a parameter:** the original stub took no "
         "arguments, which is why it could not work. The mask lives on the "
         "layer config, so the caller - `serializeLinear()` - must pass it "
         "down. **Why `FILE *` and not a buffer:** ODT checkpoints stream to "
         "disk or SD card; buffering a 294 KB tensor first would need memory "
         "the MCU does not have."),
        ("3", "if (mask == NULL || mask->quantization->type != BOOL) {",
         "**Does:** two guards in one. NULL means a dense layer; a non-BOOL "
         "tensor means something else was attached by mistake. "
         "**Why the second check matters:** without it, attaching a FLOAT32 "
         "tensor by accident would write `(n+7)/8` bytes of float data as if it "
         "were a mask - a file that loads without error and produces a "
         "meaningless mask. Failing safe to 'no mask' is the right degradation."),
        ("4", "uint8_t noMask = 0;",
         "**Does:** the presence flag, cleared. "
         "**Why `uint8_t` and not `int`:** the file format is byte-exact and "
         "must not depend on the host's `int` width or endianness."),
        ("5", "fwrite(&noMask, 1, 1, fp);",
         "**Does:** writes one zero byte. "
         "**Why write anything at all for a dense layer:** so the reader always "
         "consumes exactly one byte here and learns from its value whether more "
         "follows. A format where a field is sometimes absent cannot be parsed "
         "without out-of-band knowledge. "
         "**Not checked:** the return value. A full disk or a failed SD write "
         "silently truncates the checkpoint."),
        ("6", "return;", "**Does:** ends the dense case. The record is exactly "
         "one byte."),
        ("9", "uint8_t hasMask = 1;",
         "**Does:** the presence flag, set."),
        ("10", "fwrite(&hasMask, 1, 1, fp);",
         "**Does:** writes it. "
         "**Why the flag precedes the data:** a streaming reader never has to "
         "seek backwards - it reads one byte, then knows exactly how many "
         "follow."),
        ("12", "size_t n = calcNumberOfElementsByTensor(mask);",
         "**Does:** the number of BITS, since a BOOL tensor's element count is "
         "its bit count. "
         "**Why n is not written to the file:** it is implied by the weight "
         "tensor that precedes this record. That saves four bytes per layer and "
         "couples the two records - a trade the format makes deliberately, and "
         "the reason `deserializeSparsity()` takes n as an argument."),
        ("13", "size_t bytes = (n + 7) / 8;",
         "**Does:** ceiling division - how many whole bytes hold n bits. "
         "**Why `(n+7)/8` and not `ceil(n/8.0)`:** exact integer arithmetic, no "
         "floating point, no rounding surprises, and it is the standard C "
         "idiom. For 73,728 bits it gives exactly 9,216; for 73,730 it would "
         "give 9,217 with six bits of the last byte unused."),
        ("14", "fwrite(mask->data, 1, bytes, fp);",
         "**Does:** writes the packed bit array verbatim. "
         "**What this bakes into the format:** the in-memory bit order. A file "
         "written by the host trainer is readable on the MCU only if both pack "
         "bits identically. ODT defines `tensorBoolGet` as "
         "`(data[i>>3] >> (i&7)) & 1` on both, so they do - but that agreement "
         "is undocumented and deserves a comment here, because it is the kind "
         "of assumption that breaks silently when someone optimises the "
         "accessor."),
        ("15", "}", "**Does:** ends the write path. Total cost for the HAR "
         "layer: 9,217 bytes, against 294,912 for the weights - about 3%."),
        ("18", "tensor_t *deserializeSparsity(size_t n, FILE *fp) {",
         "**Does:** the reader. **Why it returns a tensor rather than filling "
         "one:** the caller does not know whether a mask exists until the flag "
         "is read, so allocation has to happen here. **Consequence:** the "
         "caller owns the result and must attach it to `cfg->weightMask` and "
         "eventually free it - the second place in this implementation where "
         "mask ownership is undefined."),
        ("20", "uint8_t hasMask = 0;",
         "**Does:** initialises the flag. **Why initialising matters:** if the "
         "`fread` on the next line fails, this stays 0 and the function returns "
         "NULL - degrading to a dense layer rather than acting on a garbage "
         "flag."),
        ("21", "fread(&hasMask, 1, 1, fp);",
         "**Does:** reads the presence byte. "
         "**Not checked:** the return value again. A truncated file yields a "
         "partly-initialised mask and no error, which on an embedded target "
         "reading from an SD card is not a theoretical risk."),
        ("22", "if (!hasMask) return NULL;",
         "**Does:** returns NULL for a dense layer. "
         "**Why NULL is exactly right:** it matches the default set in "
         "Component 3, so a dense checkpoint loads into a dense layer with no "
         "special case anywhere."),
        ("24", "tensor_t *mask = allocBoolTensor(n);",
         "**Does:** allocates a bit-packed tensor of n bits. "
         "**Why n comes from the caller:** as noted on line 12, the bit count "
         "is not in the file - the caller derives it from the weight tensor it "
         "just read."),
        ("25", "size_t bytes = (n + 7) / 8;",
         "**Does:** the same ceiling division as the writer. "
         "**Why it must be the same expression:** writer and reader compute the "
         "record length independently. If they ever disagree - say one uses "
         "n/8 - every subsequent record in the file is misaligned, and the "
         "failure appears in a completely different layer."),
        ("26", "fread(mask->data, 1, bytes, fp);",
         "**Does:** reads the packed bits straight into the tensor's buffer."),
        ("27", "return mask;",
         "**Does:** hands ownership to the caller. "
         "**What the caller must then do:** assign it to `cfg->weightMask`, and "
         "- worth asserting - check that the restored active count matches what "
         "was saved. A mask that loads with the wrong bit order still yields a "
         "plausible sparsity while being a completely different network."),
    ], "Table 12.1 - Every line of mask serialization and deserialization.")

    h2("Wiring it into the tensor record")
    listing([
        "void serializeTensor(tensor_t *t, tensor_t *mask, FILE *f) {",
        "    serializeShape(t->shape, f);",
        "    serializeQuantization(t->quantization, f);",
        "    serialWriteBytes(t->data, calcBytesPerTensor(t), f);",
        "    serializeSparsity(mask, f);          /* now saves the mask */",
        "}",
        "",
        "/* called from serializeLinear() as: */",
        "serializeTensor(weights, cfg->weightMask, f);",
    ], "Listing 10.2 - Threading the mask through serializeTensor(), from "
       "section 17.5.")
    box("warn", "This changes a format the source calls 'locked'",
        "Chapter 17 of the source describes the checkpoint format as 'Locked "
        "Binary Format v2', and adding a presence byte to every tensor record "
        "changes it for DENSE models too - old files no longer parse, and old "
        "readers cannot read new files. If the format really is locked, this "
        "belongs behind a version bump to v3, with the reader accepting both. "
        "The change is one byte per tensor, so the cost of doing it properly is "
        "trivial; the cost of not doing it is a checkpoint corpus that silently "
        "splits in two. Chapter 17, defect D9.")
    tbl(["What is stored", "Bytes for the HAR 1152 x 64 layer"],
        [["Weight data", "294,912"],
         ["Presence flag", "1"],
         ["Packed mask", "9,216"],
         ["Mask overhead", "3.1% of the record"]],
        widths=[46, 54], bold_first=True)


# =============================================================================
def ch_integration():
    chapter("Components 8 to 10 - Initialization, Training Loop, Schedules")
    origin("sections 9.4, 14.4, 37.4, 38.4 and 39.9")

    h2("Component 8 - creating the mask (UserAPI)")
    p("Nothing built so far ever creates a mask. `buildSequentialModel()` must "
      "do it when a layer spec asks for sparsity.")
    listing([
        "/* UserAPI.c - inside buildSequentialModel(), per LINEAR layer spec */",
        "if (spec->sparse) {",
        "    size_t maskBits = inFeat * outFeat;",
        "    tensor_t *mask  = createBoolTensor(maskBits);",
        "    bernoulliFillMask(mask, 1.0f - spec->sparsity);",
        "    zeroInactiveWeights(linearCfg, mask);",
        "    linearCfg->weightMask = mask;",
        "}",
    ], "Listing 11.1 - Mask creation, from section 38.4.")
    explain([
        ("2", "if (spec->sparse)",
         "A new field on `layerSpec_t`, alongside a `float sparsity`. Layers "
         "that do not ask for sparsity are untouched and keep weightMask = "
         "NULL."),
        ("3", "maskBits = inFeat * outFeat",
         "One bit per weight. This must equal "
         "calcNumberOfElementsByTensor(weights) exactly - if the layer has a "
         "bias, it is NOT masked, and the bias is a separate tensor, so the "
         "product of the two feature counts is right."),
        ("4", "createBoolTensor(maskBits)",
         "Allocates ceil(bits/8) bytes of bit-packed storage plus the tensor "
         "header."),
        ("5", "bernoulliFillMask(mask, 1.0f - spec->sparsity)",
         "The argument is P(active). For `spec->sparsity = 0.9` this passes "
         "0.1. Because the draws are independent, the realised active count is "
         "binomial around 7,373 with a standard deviation of about 81 - so "
         "your first log line will read 7,412 active, not 7,373, and that is "
         "correct behaviour, not a bug."),
        ("6", "zeroInactiveWeights(linearCfg, mask)",
         "Enforces the invariant at initialisation: every inactive weight is "
         "set to exactly zero. Section 11.4 omits this call and section 38.4 "
         "includes it; without it, inactive positions keep their random init "
         "values, which then appear in the checkpoint and come back to life if "
         "the mask is ever lost."),
        ("7", "linearCfg->weightMask = mask;",
         "Attach. From this point the matmul, the optimiser and rigLStep() all "
         "see the layer as sparse."),
    ])
    box("tip", "Seed before you fill",
        "Section 9.4 makes a point worth repeating: call `rngSetSeed()` before "
        "`bernoulliFillMask()` AND before the training loop. The mask draw "
        "consumes RNG state that stochastic rounding would otherwise have used, "
        "so the two are coupled - the same seed gives you the same mask and the "
        "same rounding sequence only if the ORDER of operations is also the "
        "same. This is the difference between an experiment you can reproduce "
        "and one you cannot.")

    h2("Component 9 - the training loop")
    listing([
        "#define RIGL_INTERVAL 100        /* update the mask every 100 steps */",
        "",
        "size_t step = 0;",
        "for (size_t epoch = 0; epoch < epochs; epoch++) {",
        "",
        "    for (size_t i = 0; i < trainSize; i++) {",
        "",
        "        batch_t *b = loader.getBatch(&loader, i);",
        "",
        "        forward(model, b->input);",
        "        backward(model, b->label);",
        "",
        "        if (step % RIGL_INTERVAL == 0)",
        "            rigLStep(model, nLayers, 0.9f, step, totalSteps);",
        "",
        "        optimizerFunctions[SGD_M].step(&optim);",
        "        step++;",
        "    }",
        "",
        "    lrSchedulerStep(&sched);",
        "}",
    ], "Listing 11.2 - The training loop, from section 39.9.")
    explain([
        ("1", "#define RIGL_INTERVAL 100",
         "T from the algorithm. Over a 10,350-step run this gives 103 mask "
         "updates. Too small and the network never settles between swaps; too "
         "large and the connectivity barely explores."),
        ("10-11", "forward(); backward();",
         "The gradients that rigLStep() will read are produced here. **The "
         "backward pass must produce gradients for INACTIVE weights too** - see "
         "Chapter 8 - or the GROW step has nothing to rank."),
        ("13-14", "if (step % RIGL_INTERVAL == 0) rigLStep(...)",
         "The mask update, placed AFTER backward and BEFORE the optimiser "
         "step."),
        ("16", "optimizerFunctions[SGD_M].step(&optim)",
         "The mask-aware update from Component 5. Because it runs after "
         "rigLStep(), the weights just grown get their first update in this "
         "very iteration rather than waiting a full step."),
        ("21", "lrSchedulerStep(&sched)",
         "Learning-rate decay, once per epoch, independent of the alpha "
         "schedule inside rigLStep()."),
    ])
    box("warn", "The source contradicts itself about this ordering",
        "Section 37.4 states: 'rigLStep() must be called AFTER the optimizer "
        "step but BEFORE the next forward pass. The order matters.' Section "
        "39.9 states the opposite: 'Run rigLStep() BEFORE the optimizer step. "
        "If rigLStep() runs AFTER the optimizer, the new weights miss their "
        "first update.' The code in 39.9 implements the second. Both cannot be "
        "right, and the difference is observable: it decides whether a grown "
        "weight waits 0 or 100 steps for its first gradient, and whether the "
        "gradients rigLStep() reads have already been zeroed by the optimiser "
        "(Component 5 line 16 clears them). BEFORE the optimiser is the correct "
        "choice, for exactly the reason 39.9 gives, and because the optimiser "
        "would otherwise have wiped the inactive gradients that GROW depends "
        "on. Chapter 17, defect D4.")

    h2("Component 10 - the two schedules")
    p("The learning-rate schedule and the alpha schedule are separate cosines "
      "that should share a horizon.")
    listing([
        "cosineAnnealingLrInit(&sched, &optimizer,",
        "                      0.01f,          /* eta_max */",
        "                      totalEpochs,",
        "                      1e-5f);         /* eta_min */",
        "",
        "/* alpha(step) = (0.3/2) * (1 + cos(pi * step / T_end)) */",
        "/* with T_end = 0.8 * totalSteps                        */",
    ], "Listing 11.3 - Learning rate and alpha, from section 14.4.")
    tbl(["Step", "Epoch", "alpha", "K (of 7,373 active)", "Learning rate",
         "Phase"],
        [["0", "0", "0.300", "2,212", "0.010", "Explore both values and "
          "connectivity"],
         ["4,140", "20", "0.150", "1,106", "~0.006", "Consolidate"],
         ["8,280", "40", "0.000", "0", "~0.001", "Mask frozen"],
         ["10,350", "50", "0.000", "0", "1e-5", "Refine values only"]],
        widths=[10, 9, 11, 22, 16, 32], bold_first=True)
    box("key", "Pass T_end, not totalSteps",
        "rigLStep() computes `prog = step / totalSteps` and reaches alpha = 0 "
        "only when prog = 1, i.e. at the very last step. The schedule the "
        "source specifies wants alpha = 0 at 80% of training. So the caller "
        "must pass `0.8f * totalSteps` as the `totalSteps` argument - the "
        "parameter is misnamed, and passing the true total leaves the mask "
        "swapping into the final epoch, which is precisely what the schedule "
        "exists to prevent. Chapter 17, defect D9.")


def ch_verification():
    chapter("Verifying the Implementation")
    p("Each component has a test that isolates it. Run them in build order; "
      "a failure at step k with steps 1..k-1 passing localises the bug to one "
      "function.")

    h2("Unit tests, component by component")
    tbl(["Component", "Test", "Expected"],
        [["1 - kth smallest", "Mask with 5 known active weights "
          "[0.01,0.05,0.03,0.12,0.08], K=2",
          "Returns 0.05. Then count how many satisfy `<= 0.05`: you should get "
          "3, which demonstrates defect D1"],
         ["1 - guard", "K = count", "Returns 1e38, and every active weight "
          "drops"],
         ["2 - kth largest", "Inactive gradients [0.5,0.1,0.9,0.3], K=1",
          "Returns 0.5"],
         ["2 - guard", "K = count", "Returns 0.0, and every inactive weight "
          "grows"],
         ["3 - default", "Build a model with no sparse specs",
          "Every weightMask is NULL; all existing tests still pass unchanged"],
         ["4 - matmul", "Dense vs 90%-masked forward on identical inputs",
          "Instruction counter falls from 73,728 to about 7,373; outputs differ "
          "only in the masked contributions"],
         ["4 - equivalence", "Zero the inactive weights, then run the DENSE "
          "matmul", "Bit-identical to the masked result - this is the strongest "
          "single check that your flat index is right"],
         ["5 - SGD", "One step with 90% of the mask clear",
          "Every inactive weight is exactly 0.0f afterwards, and its gradient "
          "is 0.0f"],
         ["6 - rigLStep", "Count active before and after one call",
          "Equal, or differing only by the tie effects of D1"],
         ["6 - schedule", "Call at step 0, T_end/2 and T_end",
          "alpha = 0.30, 0.15, 0.00 and K scales with it"],
         ["7 - round trip", "serializeSparsity then deserializeSparsity",
          "Every one of the 73,728 bits matches"]],
        widths=[16, 38, 46], bold_first=True)

    h2("Integration checks during a real run")
    checklist("Log these every epoch and watch their shape", [
        "Active weight count per sparse layer. It must be FLAT. A downward "
        "drift means GROW is finding fewer candidates than DROP removes - "
        "usually because inactive gradients are zero (defect D3).",
        "Number of mask bits that changed since the last RigL step. It should "
        "start near K and fall to zero as alpha decays. If it is zero from the "
        "beginning, K is rounding to zero or the mask is NULL.",
        "Fraction of swaps that are re-grows of weights dropped in the same "
        "step. Should be small; a large fraction is defect D2.",
        "Training loss around each RigL step. A spike is expected; failure to "
        "recover before the next step means alpha is too high or T too small.",
        "Matmul instruction count. Should stay near (1 - sparsity) x dense for "
        "the whole run.",
        "Peak heap usage, if you kept the malloc approach. This is where the "
        "run dies on the target.",
    ])
    h2("Results of a reference simulation")
    p("The consolidated code in Appendix A was compiled against stub headers "
      "and run for 8,200 steps on a synthetic 8,192-weight layer initialised "
      "at 10% density, with fresh random dense gradients supplied at each RigL "
      "step. This exercises the mask dynamics only - there is no forward pass, "
      "no loss and no optimiser - so it says nothing about accuracy. What it "
      "does test is every invariant this document claims.")
    tbl(["Check", "Result"],
        [["Active count at initialisation", "828 of 8,192 (10.1%) - binomial "
          "scatter around the requested 819, as expected"],
         ["Active count after every one of 83 mask updates", "828. Conservation "
          "held exactly at every step"],
         ["Inactive weights holding a non-zero value at the end", "0"],
         ["alpha at steps 0 / 4,000 / 7,600", "0.3000 / 0.1500 / 0.0018 - the "
          "cosine schedule"],
         ["Behaviour after tEnd = 8,000", "K = 0 and the mask stops changing"]],
        widths=[42, 58], bold_first=True)
    box("note", "One finding the simulation surfaced",
        "The DROP step consistently removed 249 weights while K fell from 248 "
        "to 1. The cause is instructive: grown weights are set to exactly 0.0, "
        "and in this simulation nothing ever moves them, so after the first "
        "update hundreds of active weights share the identical magnitude 0.0. "
        "No threshold can separate a tied group, so any threshold at or above "
        "zero takes all of them. In a real run the optimiser moves grown "
        "weights off zero within one step and the ties disappear - but this is "
        "exactly the tie pathology behind defect D1, made visible. It is also "
        "why the Appendix A code grows `dropped` weights rather than `K`: "
        "whatever DROP actually removed, GROW restores the same number, so "
        "conservation survives a tie that the K-based version would not.")
    box("tip", "The one test that catches the most",
        "Zero every inactive weight, then run the ORDINARY dense matmul and "
        "compare against your masked matmul bit for bit. They must agree "
        "exactly - masking and zeroing are mathematically identical operations. "
        "This single test validates the flat-index computation, the mask "
        "plumbing, and the bit-packing convention all at once, and it is the "
        "test that catches the silent index-misalignment failure that "
        "everything else lets through.")


# =============================================================================
def ch_defects():
    chapter("Ten Defects Found While Consolidating")
    p("These are not criticisms of the source, which is a careful and unusually "
      "complete piece of documentation. They are what surfaces when fragments "
      "written in 39 separate chapters are placed side by side: "
      "inconsistencies that are invisible locally and obvious globally. Each "
      "entry gives the evidence, the consequence, and a fix.")

    h2("Severity summary")
    tbl(["ID", "Defect", "Severity", "Fix cost"],
        [["D1", "DROP/GROW thresholds swap K+1 weights, not K", "Low", "1 line"],
         ["D2", "Just-dropped weights can be regrown in the same step",
          "Medium", "~6 lines"],
         ["D3", "GROW depends on gradients that may never be computed",
          "**Critical**", "Design decision"],
         ["D4", "Two sections give opposite call ordering", "High", "Doc fix"],
         ["D5", "Momentum buffer not cleared on regrowth", "Medium", "1 line"],
         ["D6", "AdamW memory figure counts only active weights", "High",
          "Re-plan the model"],
         ["D7", "Two incompatible linearConfig_t definitions", "Low", "Doc fix"],
         ["D8", "malloc of 259 KB on a 320 KB device", "**Critical**",
          "~15 lines"],
         ["D9", "T_end vs totalSteps; format version not bumped", "Medium",
          "2 lines"],
         ["D10", "Complexity estimate uses n where count is correct", "Low",
          "Doc fix"]],
        widths=[7, 51, 21, 21], bold_first=True)

    h2("D1 - The thresholds are off by one")
    p("**Evidence.** Section 39.2's own worked example: active magnitudes "
      "[0.01, 0.05, 0.03, 0.12, 0.08] with K = 2 give thresh = vals[2] = 0.05, "
      "and the text claims 'exactly 2 weights dropped'. The condition is "
      "`|w| <= 0.05`, which matches 0.01, 0.03 **and 0.05** - three weights.")
    p("**Consequence.** Every DROP removes K+1 and every GROW adds K+1, so the "
      "active count is preserved by cancellation. The swap is one larger than "
      "requested, and where magnitudes tie - which happens constantly, because "
      "newly grown weights are all exactly 0.0 - the cancellation is no longer "
      "exact and sparsity drifts.")
    p("**Fix.** Make the comparison strict on one side:")
    listing([
        "/* DROP: drop exactly K */",
        "if (tensorBoolGet(mask,i) && fabsf(w[i]) < dropThresh) { ... }",
        "",
        "/* or keep <= and take the (K-1)-th value instead:      */",
        "float dropThresh = findAbsKthSmallestActive(weights, mask, K - 1);",
    ], "Listing 12.1 - Two equivalent one-line fixes for D1.")

    h2("D2 - Drop and grow are not disjoint")
    p("**Evidence.** In Listing 9.1, `findAbsKthLargestInactive()` on line 39 "
      "runs after the DROP loop has already cleared mask bits. The "
      "just-dropped weights are inactive by then, so they compete for growth.")
    p("**Consequence.** A weight with a small value but a steep gradient is "
      "dropped and immediately regrown - its trained value destroyed for "
      "nothing, and part of the swap budget wasted. The RigL paper draws the "
      "grow candidates from the set that was inactive **before** the drop.")
    p("**Fix.** Snapshot the mask before dropping, and require a grow candidate "
      "to have been inactive in the snapshot:")
    listing([
        "/* before the DROP loop */",
        "tensor_t *prevMask = cloneBoolTensor(mask);",
        "",
        "/* in the GROW loop, add one condition */",
        "if (!tensorBoolGet(mask, i) &&",
        "    !tensorBoolGet(prevMask, i) &&        /* was ALREADY inactive */",
        "    fabsf(g[i]) >= growThresh) { ... }",
        "",
        "freeBoolTensor(prevMask);",
    ], "Listing 12.2 - Excluding just-dropped weights. Costs one extra 9 KB "
       "mask per sparse layer, transiently.")

    h2("D3 - The gradients GROW needs may not exist")
    box("warn", "This is the defect that silently turns RigL into static sparsity",
        "GROW ranks inactive weights by |gradient|. Three separate parts of "
        "this implementation can leave those gradients at zero. (a) If the "
        "weight-gradient matmul is masked like the forward matmul (Chapter 8), "
        "inactive weights never receive a gradient at all. (b) Component 5 (Chapter 9) "
        "line 16 sets `grad[i] = 0.0f` for inactive weights on EVERY optimiser "
        "step. (c) rigLStep() itself zeroes them at the end of every call. If "
        "any of these wins the race, `findAbsKthLargestInactive()` sees all "
        "zeros, returns 0.0, and the GROW condition `|g| >= 0` matches every "
        "inactive weight - so the first K+1 encountered in index order are "
        "activated. The mask then evolves by scan order, not by gradient. "
        "Training still converges, sparsity still looks right, and RigL is not "
        "actually running.")
    p("**Fix.** Three things must all hold: the weight-gradient matmul stays "
      "dense; rigLStep() runs before the optimiser clears anything (D4); and "
      "the gradients rigLStep() reads are the ones from the backward pass of "
      "the same iteration. **Verify it** by asserting that "
      "`findAbsKthLargestInactive()` returns a strictly positive threshold - "
      "if it ever returns 0.0 on a layer with more inactive weights than K, "
      "you have this bug.")

    h2("D4 - Contradictory ordering instructions")
    tbl(["Section", "Says", "Reason given"],
        [["37.4", "AFTER the optimizer step, before the next forward",
          "'This ensures that the gradient used for GROW reflects the current "
          "weight update'"],
         ["39.9", "BEFORE the optimizer step",
          "'This ensures that newly grown weights (w=0) get their first "
          "gradient update in the same step they are activated'"]],
        widths=[10, 40, 50], bold_first=True)
    p("**Resolution.** 39.9 is correct and its code implements it. Beyond the "
      "argument it gives, running after the optimiser would mean the inactive "
      "gradients had already been zeroed by Component 5 - straight into defect "
      "D3. Section 37.4 should be corrected.")

    h2("D5 - Stale momentum on regrowth")
    p("Section 13.4 identifies stale Adam moments as a hazard and clears `m` "
      "and `v`. SGD with momentum has the same problem: the velocity buffer "
      "entry for a regrown weight still holds the velocity it had before it was "
      "dropped, so its first update is a jump in a stale direction. Clear it in "
      "the same branch that zeroes the weight.")

    h2("D6 - The AdamW memory figure is not achievable")
    p("**Evidence.** Section 13.4: '7,373 active weights x 3 tensors x 4 bytes "
      "= 88 KB'. That arithmetic is right; the premise is not. `m` and `v` are "
      "allocated with the same dense shape as the parameters, so the real "
      "figure counts 73,728 elements, not 7,373: four dense float tensors plus "
      "the mask is 1,188,864 bytes for this one layer, on a device with 320 KB "
      "of SRAM.")
    p("**Fix.** Either store the moments sparsely - a real change, since it "
      "breaks O(1) indexing - or accept SGD, or shrink the layer. The source "
      "itself points at the third option in 39.10.")

    h2("D7 - Two struct definitions")
    p("Sections 11.4 and 39.4 both present `linearConfig_t` with different "
      "field lists (Chapter 7 of this document tabulates them). Retyping either "
      "one will break the build. Edit the real header instead.")

    h2("D8 - malloc on the target")
    p("`findAbsKthLargestInactive()` allocates `count * sizeof(float)` where "
      "count is the number of INACTIVE weights - 66,355 for the HAR layer, so "
      "259 KB of a 320 KB device, transiently, every 100 steps, while "
      "everything else is resident. It will not allocate; and if a smaller "
      "layer lets it succeed, repeated allocation and release of large "
      "differently-sized blocks fragments the heap.")
    p("**Fix.** Either allocate one scratch buffer at initialisation sized for "
      "the largest sparse layer and reuse it, or replace the sort with a "
      "histogram:")
    listing([
        "/* Histogram threshold: O(n) time, O(1) memory, no allocation. */",
        "#define NBINS 256",
        "uint16_t hist[NBINS] = {0};",
        "",
        "/* pass 1: find the maximum magnitude among inactive weights */",
        "float gmax = 0.0f;",
        "for (size_t i = 0; i < n; i++)",
        "    if (!tensorBoolGet(mask,i) && fabsf(g[i]) > gmax) gmax = fabsf(g[i]);",
        "",
        "/* pass 2: bin the magnitudes */",
        "float scale = (float)(NBINS - 1) / (gmax > 0.0f ? gmax : 1.0f);",
        "for (size_t i = 0; i < n; i++)",
        "    if (!tensorBoolGet(mask,i))",
        "        hist[(size_t)(fabsf(g[i]) * scale)]++;",
        "",
        "/* pass 3: walk down from the top bin until K are accounted for */",
        "size_t acc = 0;",
        "int b = NBINS - 1;",
        "for (; b >= 0; b--) {",
        "    acc += hist[b];",
        "    if (acc >= K) break;",
        "}",
        "float thresh = (float)b / scale;   /* approximate to one bin width */",
    ], "Listing 12.3 - A fixed-memory replacement for the selection sort. "
       "512 bytes of histogram instead of 259 KB of heap, and O(n) instead of "
       "O(n*K).")
    box("note", "Is an approximate threshold acceptable?",
        "Yes, and this is worth being explicit about. The threshold decides "
        "which connections to try next; it is re-computed 103 times over a run, "
        "and a weight that misses the cut this time will be considered again in "
        "100 steps. Being within one bin width of the exact K-th value changes "
        "which few borderline weights are grown, not whether the algorithm "
        "works. Exactness here buys nothing and costs 259 KB.")

    h2("D9 - Two smaller correctness gaps")
    bul([
        "**T_end.** rigLStep() reaches alpha = 0 only at `step == totalSteps`, "
        "but the schedule in section 2.3 specifies T_end = 0.8 x total. The "
        "caller must pass `0.8f * totalSteps`, or the mask keeps swapping into "
        "the final epoch. Better: give rigLStep() an explicit `tEnd` parameter "
        "instead of overloading `totalSteps`.",
        "**Format version.** Adding the sparsity presence byte changes every "
        "tensor record, including in dense checkpoints, while chapter 17 of the SOURCE calls "
        "the format 'locked v2'. Bump to v3 and have the reader accept both.",
    ])

    h2("D10 - The complexity estimate uses the wrong n")
    p("Section 7.4 gives `n * K` = 8192 x 819 = 6.7 M comparisons. The sort "
      "runs over the gathered ACTIVE values, so the cost is `count * K`. At 90% "
      "sparsity that is ten times smaller for the DROP side - and, importantly, "
      "nine times LARGER for the GROW side, where count is the inactive "
      "population. The corrected figures are in Chapters 5 and 6.")

    box("key", "What to do with this list",
        "Fix D3, D8 and D4 before you run anything - they are the difference "
        "between RigL and an expensive random mask. Fix D1, D2 and D5 before "
        "you trust an accuracy number. D6 changes what model you can train at "
        "all, so settle it while the architecture is still on paper. D7, D9 and "
        "D10 are documentation and hygiene, and cost minutes.")


def ch_appendix_code():
    chapter("Appendix - Consolidated RigL.h and RigL.c")
    p("Everything above, assembled into the two new files the implementation "
      "adds. The other components are edits to existing files and are listed in "
      "the chapters that describe them. This listing is the source's code with "
      "the D1, D2 and D9 fixes applied, and each fix marked; it is offered as a "
      "starting point, not as tested software.")

    h2("RigL.h")
    listing([
        "#ifndef RIGL_H",
        "#define RIGL_H",
        "",
        "#include <stddef.h>",
        "#include \"Tensor.h\"",
        "#include \"Layer.h\"",
        "",
        "/* K-selection helpers (implemented in MinMax.c) */",
        "float findAbsKthSmallestActive (tensor_t *weights, tensor_t *mask,",
        "                                size_t K);",
        "float findAbsKthLargestInactive(tensor_t *grads,   tensor_t *mask,",
        "                                size_t K);",
        "",
        "/* One RigL mask update over every sparse LINEAR layer of the model.",
        " * Call AFTER backward() and BEFORE the optimiser step.",
        " * tEnd: the step at which alpha reaches zero (typically 0.8*total). */",
        "void rigLStep(layer_t **model, size_t numLayers,",
        "              float alphaInit, size_t step, size_t tEnd);",
        "",
        "#endif /* RIGL_H */",
    ], "Listing A.1 - RigL.h.")

    h2("RigL.c")
    listing([
        "#define SOURCE_FILE \"RIGL\"",
        "",
        "#include \"Common.h\"",
        "#include \"RigL.h\"",
        "#include \"Tensor.h\"",
        "#include \"MinMax.h\"",
        "#include \"Layer.h\"",
        "#include \"Linear.h\"",
        "#include <math.h>      /* cosf, fabsf */",
        "",
        "void rigLStep(layer_t **model, size_t numLayers,",
        "              float alphaInit, size_t step, size_t tEnd) {",
        "",
        "    /* --- alpha schedule; frozen once step passes tEnd (fix D9) --- */",
        "    if (tEnd == 0) return;",
        "    if (step >= tEnd) return;",
        "    float prog  = (float)step / (float)tEnd;",
        "    float alpha = 0.5f * alphaInit * (1.0f + cosf(3.14159265f * prog));",
        "",
        "    for (size_t l = 0; l < numLayers; l++) {",
        "",
        "        if (model[l]->type != LINEAR) continue;",
        "",
        "        linearConfig_t *cfg = model[l]->config->linear;",
        "        tensor_t *mask = cfg->weightMask;",
        "        if (mask == NULL) continue;",
        "",
        "        tensor_t *weights = cfg->weights->param;",
        "        tensor_t *grads   = cfg->weights->grad;",
        "        size_t n = calcNumberOfElementsByTensor(weights);",
        "        float *w = (float *)weights->data;",
        "        float *g = (float *)grads->data;",
        "",
        "        size_t numActive = 0;",
        "        for (size_t i = 0; i < n; i++)",
        "            if (tensorBoolGet(mask, i)) numActive++;",
        "",
        "        size_t K = (size_t)(alpha * (float)numActive);",
        "        if (K == 0) continue;",
        "",
        "        PRINT_INFO(\"rigLStep: layer=%zu step=%zu alpha=%.4f K=%zu\",",
        "                   l, step, alpha, K);",
        "",
        "        /* snapshot of the pre-drop mask (fix D2) */",
        "        tensor_t *prevMask = cloneBoolTensor(mask);",
        "",
        "        /* ---- DROP: strict < drops exactly K (fix D1) ---- */",
        "        float dropThresh = findAbsKthSmallestActive(weights, mask, K);",
        "        size_t dropped = 0;",
        "        for (size_t i = 0; i < n; i++) {",
        "            if (tensorBoolGet(mask, i) && fabsf(w[i]) < dropThresh) {",
        "                tensorBoolSet(mask, i, false);",
        "                w[i] = 0.0f;",
        "                dropped++;",
        "            }",
        "        }",
        "",
        "        /* ---- GROW: only weights inactive BEFORE the drop (D2) ---- */",
        "        float growThresh = findAbsKthLargestInactive(grads, prevMask,",
        "                                                     dropped);",
        "        size_t grown = 0;",
        "        for (size_t i = 0; i < n && grown < dropped; i++) {",
        "            if (!tensorBoolGet(prevMask, i) &&",
        "                !tensorBoolGet(mask, i) &&",
        "                fabsf(g[i]) > growThresh) {",
        "                tensorBoolSet(mask, i, true);",
        "                w[i] = 0.0f;          /* grown connections start at 0 */",
        "                grown++;",
        "            }",
        "        }",
        "",
        "        if (grown != dropped)",
        "            PRINT_ERROR(\"rigLStep: layer=%zu dropped=%zu grown=%zu\",",
        "                        l, dropped, grown);",
        "",
        "        freeBoolTensor(prevMask);",
        "",
        "        /* ---- clear gradients of everything still inactive ---- */",
        "        for (size_t i = 0; i < n; i++)",
        "            if (!tensorBoolGet(mask, i)) g[i] = 0.0f;",
        "    }",
        "}",
    ], "Listing A.2 - RigL.c with the D1, D2 and D9 fixes applied and marked. "
       "The `grown != dropped` check is the runtime assertion of the "
       "conservation property - if it ever fires, sparsity is drifting.")
    box("warn", "What this listing is and is not",
        "It is a faithful consolidation of the source's algorithm with three "
        "specific defects repaired and the repairs labelled. It has not been "
        "compiled against the ODT headers, and it assumes helpers - "
        "`cloneBoolTensor`, `freeBoolTensor` - that the source does not "
        "document and you may have to write. It still uses the malloc-based "
        "K-selection, so defect D8 remains open; apply Listing 12.3 before "
        "putting this on the target.")


def ch_appendix_index():
    chapter("Appendix - Where Every Fragment Came From")
    p("The full extraction map, so any statement in this document can be "
      "traced back to the source PDF.")
    tbl(["Source section", "Chapter of the source", "Content", "Used in"],
        [["2.1", "Part 2 intro", "Why sparse training; drop/grow rationale",
          "Ch 1"],
         ["2.2", "Part 2 intro", "The algorithm in pseudocode", "Ch 1, 9"],
         ["2.3", "Part 2 intro", "Cosine alpha schedule and LR synergy",
          "Ch 1, 11"],
         ["2.4", "Part 2 intro", "Published results; the ODT gap list",
          "Ch 1, 2"],
         ["1.4", "Common.h", "SOURCE_FILE pattern, logging for RigL.c",
          "Appendix A"],
         ["2.4 (ch 2)", "DTypes", "FLOAT32 vs SYM_INT32 access", "Ch 3, 9"],
         ["7.4", "MinMax", "Both K-selection functions, complexity",
          "Ch 3, 4, 12"],
         ["8.4", "Matmul", "Mask-aware inner loop; counter verification",
          "Ch 6"],
         ["9.4", "RNG/Bernoulli", "Mask initialisation and seeding", "Ch 11"],
         ["11.4", "Linear", "weightMask field; mask memory", "Ch 5"],
         ["12.4", "Sgd", "Mask-aware SGD kernel", "Ch 7"],
         ["13.4", "AdamW", "Mask-aware AdamW; moment clearing", "Ch 8, 12"],
         ["14.4", "LrScheduler", "LR and alpha schedule together", "Ch 11"],
         ["17.5", "Serialize", "serializeSparsity, deserializeSparsity",
          "Ch 10"],
         ["20.4", "Conv1d", "kernelMask extension (not implemented)", "Ch 2"],
         ["33.4", "Comparison", "DROP/GROW as threshold comparisons", "Ch 1"],
         ["37.4", "TrainingLoopApi", "Integration point; ordering claim",
          "Ch 11, 12"],
         ["38.4", "UserAPI", "Mask creation in buildSequentialModel", "Ch 11"],
         ["39.1-39.10", "RigL Complete", "All seven components; training loop; "
          "expected results", "Ch 3-11"]],
        widths=[14, 20, 44, 22], bold_first=True)
    p("Sections 3.4, 4.4, 5.4, 6.4, 10.4, 15.6, 16.4, 18.4, 19.4, 21.4, 22.4, "
      "23.4, 24.4, 25.5, 26.4, 27.4, 28.4, 29.6, 30.4, 31.4, 32.5, 34.5, 35.4 "
      "and 36.4 were read and contain no RigL code - they state that the file "
      "in question needs no change, which is itself useful information: it "
      "means the mask does not have to be threaded through activations, "
      "pooling, normalisation, flattening, the data loader, or the PPCA replay "
      "path.")




# =============================================================================
def ch_worked_step():
    chapter("One RigL Step, Computed by Hand")
    p("Before any C code, work one complete RigL step on a layer small enough "
      "to hold in your head. Every number below was computed and checked; you "
      "can verify each one with a calculator in about ten minutes. If you "
      "understand this chapter, the 51-line rigLStep() in Chapter 11 contains "
      "no surprises.")

    h2("The toy layer")
    p("A linear layer with 2 output neurons and 4 inputs - so 8 weights - at "
      "50% sparsity, meaning 4 are active. Weights are stored row-major: row 0 "
      "is output neuron 0, row 1 is output neuron 1.")
    diagram([
        "  weight matrix, [out=2, in=4], row-major",
        "",
        "                in0     in1     in2     in3",
        "  out0  [   0.80   -0.05    0.00    0.00 ]     flat indices 0 1 2 3",
        "  out1  [   0.30    0.00   -0.12    0.00 ]     flat indices 4 5 6 7",
        "",
        "  mask  [      1       1       0       0",
        "               1       0       1       0 ]",
        "",
        "  active = {0, 1, 4, 6}      inactive = {2, 3, 5, 7}",
    ], "Figure 2.1 - The toy layer. Inactive weights are exactly 0.0, which is "
       "the invariant every component in this document maintains.")
    tbl(["Flat index", "0", "1", "2", "3", "4", "5", "6", "7"],
        [["weight w", "0.80", "-0.05", "0.00", "0.00", "0.30", "0.00", "-0.12",
          "0.00"],
         ["mask m", "1", "1", "0", "0", "1", "0", "1", "0"],
         ["gradient g", "0.02", "0.85", "0.40", "-0.03", "0.05", "0.90", "0.01",
          "-0.70"]],
        widths=[18, 10.25, 10.25, 10.25, 10.25, 10.25, 10.25, 10.25, 10.25],
        bold_first=True)
    p("The gradients are the ones the backward pass just produced. Note that "
      "**inactive weights have gradients too** - positions 2, 3, 5 and 7 carry "
      "0.40, -0.03, 0.90 and -0.70. That is not an accident of this example; it "
      "is the precondition RigL cannot work without, and Chapter 17 (defect D3) "
      "is entirely about the ways that precondition gets broken.")

    h2("Step 1 - how many weights to swap")
    eq(["numActive = 4",
        "alpha     = 0.5      (say we are early in training)",
        "K         = floor(alpha * numActive) = floor(0.5 * 4) = 2"])
    p("So this step will deactivate 2 connections and activate 2 others, "
      "leaving the layer with 4 active weights - the same number it started "
      "with.")

    h2("Step 2 - DROP the two weakest active weights")
    p("Collect the magnitudes of the ACTIVE weights only, and sort them:")
    tbl(["Rank (0-indexed)", "0", "1", "2", "3"],
        [["|w|", "0.05", "0.12", "0.30", "0.80"],
         ["at flat index", "1", "6", "4", "0"]],
        widths=[24, 19, 19, 19, 19], bold_first=True)
    eq(["dropThresh = vals[K] = vals[2] = 0.30",
        "",
        "the two weakest are index 1 (|w| = 0.05) and index 6 (|w| = 0.12)"])
    box("warn", "Watch what the source's comparison does here",
        "The source tests `|w| <= dropThresh`, i.e. `|w| <= 0.30`. That matches "
        "index 1 (0.05), index 6 (0.12) **and index 4 (0.30)** - three weights, "
        "not the two we asked for. Using a strict `<` instead matches exactly "
        "the two intended. This is defect D1, and it is visible in a layer of "
        "eight weights; in a layer of 73,728 it is invisible until you count.")
    p("Taking the corrected version, DROP deactivates indices **1 and 6**:")
    eq(["mask[1] = 0,  w[1] = 0.0      (was -0.05)",
        "mask[6] = 0,  w[6] = 0.0      (was -0.12)",
        "",
        "active is now {0, 4} - only 2 weights, temporarily below target"])

    h2("Step 3 - GROW the two most promising inactive weights")
    p("Now rank the INACTIVE weights by gradient magnitude. The question each "
      "gradient answers is: __if this connection were switched on, how fast "
      "would the loss fall?__")
    tbl(["Rank (0-indexed)", "0", "1", "2", "3"],
        [["|g|", "0.90", "0.70", "0.40", "0.03"],
         ["at flat index", "5", "7", "2", "3"]],
        widths=[24, 19, 19, 19, 19], bold_first=True)
    eq(["growThresh = vals[K] = vals[2] = 0.40",
        "",
        "the two most promising are index 5 (|g| = 0.90) and index 7 (|g| = 0.70)"])
    p("GROW activates indices **5 and 7**, both starting at exactly zero:")
    eq(["mask[5] = 1,  w[5] = 0.0",
        "mask[7] = 1,  w[7] = 0.0",
        "",
        "active is back to {0, 4, 5, 7} - four weights, conserved"])
    box("key", "Why a grown weight starts at zero and not at something useful",
        "A newly activated connection has never been trained. Giving it any "
        "non-zero value would inject an arbitrary perturbation into a network "
        "that is otherwise converging. Starting at zero means the connection "
        "contributes nothing on its first forward pass and is then shaped "
        "entirely by gradients - it earns its value. The cost is that it needs "
        "time to become useful, which is precisely why the mask must stop "
        "changing well before training ends.")

    h2("Step 4 - clear the gradients of everything still inactive")
    p("Positions 1, 2, 3 and 6 are inactive after the swap. Their gradients are "
      "zeroed so that this step's values cannot influence the NEXT swap - "
      "without this, a weight that had a large gradient once would keep looking "
      "attractive forever.")

    h2("The layer before and after")
    tbl(["Flat index", "0", "1", "2", "3", "4", "5", "6", "7"],
        [["mask BEFORE", "1", "1", "0", "0", "1", "0", "1", "0"],
         ["w BEFORE", "0.80", "-0.05", "0", "0", "0.30", "0", "-0.12", "0"],
         ["mask AFTER", "1", "0", "0", "0", "1", "1", "0", "1"],
         ["w AFTER", "0.80", "0", "0", "0", "0.30", "0", "0", "0"]],
        widths=[18, 10.25, 10.25, 10.25, 10.25, 10.25, 10.25, 10.25, 10.25],
        bold_first=True)
    eq(["active before: {0, 1, 4, 6}      4 weights",
        "active after : {0, 4, 5, 7}      4 weights      <- conserved",
        "",
        "two connections moved from weak positions (1, 6)",
        "to positions the gradient says are promising (5, 7)"])
    p("Notice what survived: index 0 with |w| = 0.80 and index 4 with 0.30 were "
      "never in danger - large weights are exactly what DROP protects. And "
      "notice the price: the trained values -0.05 and -0.12 are gone forever. "
      "Every swap discards learned information in exchange for a better "
      "position, which is why alpha decays.")

    h2("The same step with the source's code, and why it differs")
    p("Run the identical data through the source's version - non-strict "
      "comparisons, and GROW ranking the post-DROP inactive set - and the "
      "result changes:")
    tbl(["Step", "Corrected version", "Source version"],
        [["DROP candidates", "|w| < 0.30 -> indices 1, 6", "|w| <= 0.30 -> "
          "indices 1, 6, **4**"],
         ["Weights dropped", "2", "3 (defect D1)"],
         ["GROW candidate set", "Weights inactive BEFORE the drop: {2, 3, 5, 7}",
          "Weights inactive AFTER the drop: {1, 2, 3, 5, 6, 7} - including the "
          "ones just dropped"],
         ["Ranking by |g|", "0.90 (i5), 0.70 (i7), 0.40 (i2), 0.03 (i3)",
          "0.90 (i5), **0.85 (i1)**, 0.70 (i7), 0.40 (i2), ..."],
         ["Weights grown", "indices 5, 7", "indices 5, **1**, 7 (defect D2 and "
          "D1 together)"],
         ["Net effect on index 1", "Dropped, stays out", "Dropped, then "
          "IMMEDIATELY regrown in the same step - its trained value -0.05 "
          "destroyed for nothing"]],
        widths=[18, 40, 42], bold_first=True)
    box("intuit", "Why index 1 is the perfect illustration of defect D2",
        "Its weight is tiny (-0.05) so DROP judges it useless, but its gradient "
        "is large (0.85) so GROW judges it valuable. Both judgements are "
        "reasonable - a weight can be small and still be on a steep part of the "
        "loss surface. The published algorithm resolves the conflict by "
        "excluding just-dropped weights from growth, so the connection is "
        "genuinely retired for at least one interval. The source's version "
        "resolves it by resetting a trained weight to zero and putting it back, "
        "which is strictly worse than leaving it alone.")

    h2("The life of one connection, over a whole run")
    diagram([
        "  step      0   mask=1, w=+0.031   born active in the random init mask",
        "  step    500   mask=1, w=+0.008   gradients are small; it is shrinking",
        "  step   1000   mask=1, w=+0.002   now among the weakest active weights",
        "  step   1100   mask=0, w= 0.000   DROPPED. Its value is gone.",
        "  step   1100+  mask=0, w= 0.000   still receives a gradient each step,",
        "                                   because the weight-gradient matmul",
        "                                   stays dense (see Chapter 8)",
        "  step   3400   mask=0, |g|=0.21   the loss surface has changed; this",
        "                                   connection now looks valuable",
        "  step   3400   mask=1, w= 0.000   REGROWN, starting from zero",
        "  step   3500   mask=1, w=-0.014   the optimiser has begun shaping it",
        "  step   8000   mask=1, w=-0.190   alpha has reached 0; the mask is",
        "                                   frozen and only this value changes",
    ], "Figure 2.2 - One connection's trajectory. The mask decides whether it "
       "participates; the optimiser decides its value; the gradient decides "
       "whether it comes back.")
    box("key", "The sentence to remember",
        "RigL never asks 'which weights should I delete'. It asks, every 100 "
        "steps, 'given what the gradients now say, is the current set of "
        "connections still the best set of this size?' - and swaps the few "
        "positions where the answer is clearly no. The sparsity level is fixed "
        "by you; the PATTERN is learned.")


# =============================================================================
def ch_prerequisites():
    chapter("Prerequisites - the ODT Data Model")
    origin("chapters 3, 4, 6, 10 and 11 of the source")
    p("The code in the component chapters manipulates four ODT concepts. "
      "Fifteen minutes here makes every later listing readable; skipping it "
      "makes the flat-index arithmetic look like magic.")

    h2("tensor_t - the universal container")
    p("Every array in ODT is a `tensor_t`: a shape, a quantization descriptor "
      "saying how the bytes are interpreted, and a flat byte buffer. It is "
      "always **one-dimensional in memory**; the shape only says how to read "
      "it.")
    tbl(["Field", "Holds", "Why RigL cares"],
        [["shape", "Dimensions, e.g. [64, 1152]",
          "Tells you the row length needed to convert (row, col) to a flat "
          "index"],
         ["quantization", "FLOAT32, SYM_INT32, BOOL, ...",
          "Decides whether `(float*)t->data` is a legal cast. For a mask it "
          "must be BOOL"],
         ["data", "A flat byte buffer",
          "The thing every loop in this document walks"]],
        widths=[16, 34, 50], bold_first=True)
    eq(["calcNumberOfElementsByTensor(t)  -> the number of ELEMENTS (not bytes)",
        "",
        "FLOAT32 tensor of 8 elements  ->  8 elements,  32 bytes",
        "BOOL    tensor of 8 elements  ->  8 elements,   1 byte  (bit-packed)"])
    box("warn", "Elements, not bytes - and the mask must match exactly",
        "The mask and the weight tensor must report the SAME element count, "
        "because every consumer indexes both with the same flat index. They "
        "occupy wildly different amounts of memory - 4 bytes per weight against "
        "1 bit per mask entry - and confusing the two is how you end up reading "
        "past the end of the mask buffer.")

    h2("BOOL tensors and bit packing, worked out")
    p("A mask stores one bit per weight, eight bits to a byte. The accessor is:")
    listing([
        "bool tensorBoolGet(tensor_t *t, size_t i) {",
        "    uint8_t *d = (uint8_t *)t->data;",
        "    return (d[i >> 3] >> (i & 7)) & 1;",
        "}",
        "",
        "void tensorBoolSet(tensor_t *t, size_t i, bool v) {",
        "    uint8_t *d = (uint8_t *)t->data;",
        "    if (v) d[i >> 3] |=  (1u << (i & 7));",
        "    else   d[i >> 3] &= ~(1u << (i & 7));",
        "}",
    ], "Listing 3.1 - The two accessors every RigL loop calls.")
    explain([
        ("3", "d[i >> 3]",
         "`i >> 3` is `i / 8` - which byte holds bit i. A shift rather than a "
         "division because the compiler generates one instruction either way "
         "for unsigned types, and the intent is clearer as a bit operation."),
        ("3", ">> (i & 7)",
         "`i & 7` is `i % 8` - the bit's position within its byte. Shifting it "
         "down to position 0..."),
        ("3", "& 1",
         "...and masking off everything above it leaves 0 or 1."),
        ("8", "d[..] |= (1u << (i & 7))",
         "Set: OR in a single 1 bit at that position, leaving the other seven "
         "bits of the byte untouched."),
        ("9", "d[..] &= ~(1u << (i & 7))",
         "Clear: AND with a mask that is all ones except at that position."),
    ])
    p("Take the toy layer from Chapter 2. Its mask is 8 bits, so exactly one "
      "byte:")
    diagram([
        "  flat index      7   6   5   4   3   2   1   0",
        "  mask BEFORE     0   1   0   1   0   0   1   1     = 0x53 = 83",
        "  mask AFTER      1   0   1   1   0   0   0   1     = 0xB1 = 177",
        "",
        "  bit i sits at position (i & 7) of byte (i >> 3), so index 0 is the",
        "  LOW bit and the byte reads right-to-left when written this way.",
        "",
        "  tensorBoolGet(mask, 5) on 0xB1:",
        "     5 >> 3 = 0        -> byte 0, which is 0xB1 = 1011 0001",
        "     5 & 7  = 5        -> shift right by 5: 0000 0101",
        "     & 1               -> 1, so weight 5 is ACTIVE",
    ], "Figure 3.1 - The toy layer's mask as actual bits.")
    tbl(["Layer", "Weights", "Mask bytes", "Weight bytes (FP32)", "Overhead"],
        [["Toy example", "8", "1", "32", "3.1%"],
         ["HAR 1152 x 64", "73,728", "9,216", "294,912", "3.1%"],
         ["Output 64 x 6", "384", "48", "1,536", "3.1%"]],
        widths=[22, 16, 16, 24, 22], bold_first=True)
    p("The overhead is always 1 bit per 32, i.e. 3.125%, whatever the layer "
      "size - a useful constant to quote when someone asks what the mask "
      "costs.")

    h2("Flat indices - the mapping that must never be wrong")
    p("The weight matrix is logically 2-D and physically 1-D. Row-major means "
      "row 0 comes first, complete, then row 1:")
    eq(["flatIdx = rowIndex * columnsPerRow + columnIndex",
        "",
        "toy layer: 2 outputs x 4 inputs, so columnsPerRow = 4",
        "",
        "  (out 0, in 0) -> 0*4 + 0 = 0        (out 1, in 0) -> 1*4 + 0 = 4",
        "  (out 0, in 1) -> 0*4 + 1 = 1        (out 1, in 1) -> 1*4 + 1 = 5",
        "  (out 0, in 2) -> 0*4 + 2 = 2        (out 1, in 2) -> 1*4 + 2 = 6",
        "  (out 0, in 3) -> 0*4 + 3 = 3        (out 1, in 3) -> 1*4 + 3 = 7"])
    p("In the mask-aware matmul of Chapter 8 this appears as `flatIdx = "
      "rowIndex * aColumns + i`, where `rowIndex` is the output neuron being "
      "computed and `i` walks the inputs. It is the same formula. The reason it "
      "deserves this much attention is that a mistake here does not crash - it "
      "skips the wrong weights, and the model trains happily to a wrong "
      "answer.")
    box("tip", "The five-minute check that proves your index is right",
        "Set every inactive weight to 0.0, then run the ORDINARY dense matmul "
        "and compare against your masked one. They must agree bit for bit, "
        "because skipping a weight and multiplying by a stored zero are the "
        "same arithmetic. If they disagree, your flat index does not match the "
        "mask's ordering. This one test is worth more than any amount of "
        "staring at the formula.")

    h2("parameter_t - a weight and its gradient, together")
    eq(["typedef struct {",
        "    tensor_t *param;    /* the weights themselves */",
        "    tensor_t *grad;     /* dL/dW, same shape, filled by backward() */",
        "} parameter_t;"])
    p("rigLStep() needs both halves: `param` for the DROP decision and `grad` "
      "for GROW. They have identical shapes and element counts, so one flat "
      "index addresses the weight, its gradient and its mask bit - which is "
      "what makes the loops in Chapter 11 as simple as they are.")

    h2("layer_t and the config union")
    eq(["layer_t   { layerType_t type;  layerConfig_t *config;  ... }",
        "layerConfig_t is a UNION: .linear, .conv1d, .relu, ...",
        "",
        "so: model[l]->config->linear  is valid ONLY when",
        "    model[l]->type == LINEAR"])
    box("warn", "Why the type check comes first in rigLStep()",
        "`config` is a union, so reading `->linear` on a Conv1d layer does not "
        "fail - it reinterprets whatever bytes are there as a linearConfig_t "
        "and hands you a garbage `weightMask` pointer. The line `if "
        "(model[l]->type != LINEAR) continue;` is not a filter for tidiness; it "
        "is what stops the function from dereferencing nonsense.")

    h2("Where RigL sits in one training iteration")
    diagram([
        "   getBatch()",
        "       |",
        "   forward()          <- masked matmul: skips inactive weights",
        "       |",
        "   loss",
        "       |",
        "   backward()         <- weight-gradient matmul: DENSE, so that",
        "       |                 inactive weights still receive gradients",
        "       |",
        "   rigLStep()         <- every 100 steps: DROP + GROW using those",
        "       |                 gradients, before anything clears them",
        "       |",
        "   optimizer.step()   <- masked update: active weights move,",
        "       |                 inactive ones are forced to exactly 0",
        "   next iteration",
    ], "Figure 3.2 - The order of operations. Two things in this diagram are "
       "load-bearing: backward() must be dense, and rigLStep() must run before "
       "the optimiser. Chapter 17 explains what breaks otherwise.")


# =============================================================================
def ch_logs():
    chapter("What You Will See in the Logs")
    p("Every defect in this document has a signature in the training log. "
      "Knowing what healthy output looks like means you can spot a broken "
      "implementation within the first few hundred steps instead of after a "
      "50-epoch run.")

    h2("Healthy output")
    listing([
        "[RIGL] rigLStep: layer=0 step=0    alpha=0.3000 K=2212 active=7412",
        "[RIGL]   drop thresh=2.481e-03 dropped=2212",
        "[RIGL]   grow thresh=8.113e-04 grown=2212",
        "[RIGL] rigLStep: layer=0 step=100  alpha=0.2999 K=2211 active=7412",
        "[RIGL]   drop thresh=2.106e-03 dropped=2211",
        "[RIGL]   grow thresh=7.984e-04 grown=2211",
        "...",
        "[RIGL] rigLStep: layer=0 step=4100 alpha=0.1500 K=1111 active=7412",
        "[RIGL]   drop thresh=9.02e-04  dropped=1111",
        "[RIGL]   grow thresh=1.219e-03 grown=1111",
        "...",
        "[RIGL] rigLStep: layer=0 step=8200 alpha=0.0000 K=0    active=7412",
        "(no further output - K is zero, the mask is frozen)",
    ], "Listing 13.1 - What a correct run looks like.")
    tbl(["Signal", "Healthy behaviour", "Why"],
        [["active", "Identical on every line, for the whole run",
          "Conservation: K dropped = K grown"],
         ["alpha", "Starts at 0.3000, decays smoothly, reaches 0 at tEnd",
          "The cosine schedule"],
         ["K", "Tracks alpha x active, falls to 0", "K = floor(alpha * active)"],
         ["dropped and grown", "Equal to each other on every line",
          "If they differ, sparsity is drifting"],
         ["drop thresh", "Small and slowly FALLING",
          "As training proceeds the surviving weights grow, so the K-th "
          "smallest gets smaller"],
         ["grow thresh", "Small and slowly RISING",
          "Gradients on inactive weights shrink as the model converges, so the "
          "bar for being interesting rises relative to them"]],
        widths=[16, 34, 50], bold_first=True)

    h2("Failure signatures")
    tbl(["What you see", "Almost certainly", "Where to look"],
        [["`grow thresh=0.000000` on every line",
          "**Defect D3.** The inactive gradients are all zero, so the threshold "
          "collapses and GROW is picking by scan order. RigL is not running",
          "Is the weight-gradient matmul masked? Is rigLStep() after the "
          "optimiser?"],
         ["`active` falls a little on every RigL step",
          "DROP is removing more than GROW restores - usually the same D3, with "
          "too few gradients above the threshold",
          "Compare dropped and grown on each line"],
         ["`active` rises over time",
          "GROW is over-matching, typically many gradients tied at exactly the "
          "threshold", "The tie handling of defect D1"],
         ["`dropped` and `grown` differ by 1 consistently",
          "**Defect D1**, the off-by-one from non-strict comparisons",
          "The `<=` and `>=` in rigLStep()"],
         ["`dropped` is constant while K falls",
          "Many active weights share an identical magnitude - usually 0.0 "
          "because grown weights were never updated",
          "Is the optimiser running? Is it masked correctly?"],
         ["No `[RIGL]` lines at all",
          "Every weightMask is NULL, so rigLStep() skips every layer",
          "Did buildSequentialModel() get `sparse=true`?"],
         ["`K=0` from the very first step",
          "alpha or numActive is zero - a mask filled with the wrong "
          "probability, or `bernoulliFillMask(mask, 0.9)` when you meant 0.1",
          "The P(active) inversion in Chapter 13"],
         ["Loss spikes at every RigL step and never recovers",
          "alpha too high or the interval too short - the network cannot "
          "re-learn 2,000 connections in 100 steps",
          "Lower alphaInit, or raise RIGL_INTERVAL"],
         ["Instruction counter unchanged after masking",
          "The mask is not reaching the matmul kernel",
          "A wrapper is still passing NULL"],
         ["Hard fault or malloc failure a few steps in",
          "**Defect D8** - 259 KB of scratch heap on a 320 KB device",
          "Build the histogram variant"]],
        widths=[26, 42, 32], bold_first=True)

    h2("The three numbers to plot")
    bul([
        "**Active count per layer, against step.** Should be a flat line. This "
        "single plot catches D1, D3 and most plumbing mistakes.",
        "**Mask churn** - how many bits changed since the last RigL step - "
        "against step. Should start near K and decay to zero with alpha. A "
        "flat-zero churn means the mask is not moving; a churn that stays high "
        "after tEnd means you passed totalSteps instead of 0.8 x totalSteps "
        "(defect D9).",
        "**Training loss, with the RigL steps marked.** You should see a small "
        "spike at each swap that recovers within a few dozen steps, and the "
        "spikes should shrink as alpha decays. Spikes that grow over time mean "
        "the swaps are destroying more than they gain.",
    ])
    box("tip", "Add one assertion and most of this becomes unnecessary",
        "The consolidated code in Appendix A logs an error whenever `grown != "
        "dropped`. That one check turns the silent, slow-motion failure of "
        "sparsity drift into a loud message on the step it first happens. If "
        "you take nothing else from this chapter, take that assertion.")


def ch_plan():
    chapter("An Implementation Plan")
    p("Ten components, ordered so that each one is testable before the next "
      "depends on it. The estimates assume familiarity with the ODT codebase "
      "and no surprises; they are there to show the SHAPE of the work, not to "
      "be held to.")
    tbl(["Order", "Task", "Chapter", "Rough effort", "Done when"],
        [["1", "Read the prerequisites and the hand-worked step", "2, 3",
          "1 hour", "You can predict the DROP and GROW sets of the toy layer "
          "without running anything"],
         ["2", "findAbsKthSmallestActive + unit test", "5", "2 hours",
          "The toy example returns 0.30, and the K >= count guard returns "
          "1e38"],
         ["3", "findAbsKthLargestInactive + unit test", "6", "1 hour",
          "Returns 0.40 on the toy example; the guard returns 0.0"],
         ["4", "Decide exact vs histogram K-selection", "6, 17", "1 hour",
          "You have measured the scratch allocation your largest layer would "
          "need and compared it against free SRAM"],
         ["5", "weightMask field + NULL default", "7", "30 minutes",
          "The whole existing test suite still passes unchanged"],
         ["6", "Mask-aware matmul + the zero-equivalence test", "8", "3 hours",
          "Masked output is bit-identical to dense-with-zeros, and the "
          "instruction counter drops to ~10%"],
         ["7", "Mask-aware SGD (and AdamW if used)", "9, 10", "2 hours",
          "After one step, every inactive weight is exactly 0.0f"],
         ["8", "rigLStep() itself", "11", "4 hours",
          "Active count is conserved across 100 simulated steps"],
         ["9", "serializeSparsity + deserializeSparsity", "12", "2 hours",
          "A save/load round trip reproduces all 73,728 bits"],
         ["10", "UserAPI mask creation", "13", "1 hour",
          "A model built with sparse=true logs the expected active count"],
         ["11", "Training-loop integration", "13", "1 hour",
          "The [RIGL] lines of Chapter 15 appear, with dropped == grown"],
         ["12", "First real run + the three plots", "15", "1 day",
          "Flat active count, decaying churn, recovering loss spikes"]],
        widths=[7, 26, 9, 13, 45], bold_first=True)

    h2("Checkpoints where you should stop and verify")
    checklist("Do not proceed past these until they hold", [
        "After step 6: masked matmul equals dense-with-zeros, bit for bit. If "
        "this fails, everything downstream is built on a wrong index.",
        "After step 7: inactive weights are exactly 0.0f after an optimiser "
        "step - not merely small.",
        "After step 8: 100 simulated rigLStep() calls leave the active count "
        "unchanged, and `grown == dropped` never logs an error.",
        "After step 11: `grow thresh` is strictly positive on every line. A "
        "zero there means defect D3 and everything above it was wasted effort.",
    ])
    box("key", "The order is not arbitrary",
        "Each step is verifiable using only the steps before it. Building "
        "rigLStep() first - the tempting move, since it is the interesting part "
        "- means its first test depends on four unverified components at once, "
        "and a failure tells you nothing about where the fault is. The "
        "K-selection functions are pure, take no ODT state, and can be tested "
        "with eight numbers in an array; start there.")


def ch_faq():
    chapter("Common Confusions")

    h3("Is RigL pruning?")
    p("No, and the distinction matters. Pruning trains a dense network and then "
      "removes weights, so you pay for dense training first. RigL is sparse "
      "from step one and stays at a fixed sparsity for the whole run - the "
      "memory and forward-pass compute never exceed the sparse budget. What it "
      "learns, in addition to the weight values, is WHICH connections should "
      "exist.")

    h3("If 90% of weights are skipped, why is training not 10x faster?")
    p("Because only the forward pass and the loss-propagation matmul are "
      "masked. The weight-gradient matmul must stay dense, or the GROW step "
      "has no signal to rank inactive weights by (Chapter 8, defect D3). "
      "Roughly speaking you save on two of the three matmuls, so the "
      "end-to-end training speedup is well short of the sparsity ratio. "
      "**Inference**, where only the forward pass runs, does get close to the "
      "full benefit - which is the case that matters on the device.")

    h3("Does the model get smaller?")
    p("Not as implemented here. The weight tensor keeps its full dense "
      "allocation and simply contains zeros at inactive positions, so a "
      "73,728-weight layer still occupies 288 KB plus a 9 KB mask. Getting the "
      "memory back requires a compressed format such as CSR, which costs index "
      "storage and destroys the O(1) random access the masked matmul relies "
      "on. What RigL buys here is compute and energy, not footprint - be "
      "precise about that when reporting results.")

    h3("Why not just keep the largest weights and stop swapping?")
    p("That is magnitude pruning with a fixed mask, and it is a reasonable "
      "baseline - worth measuring, in fact. The problem is that the best "
      "connectivity early in training is not the best connectivity later: a "
      "connection that looks useless at step 500 may be exactly what the "
      "network needs at step 5,000, and a fixed mask can never discover it. "
      "The gradient of an inactive weight is the only signal that can tell you "
      "this, and using it is the whole contribution of RigL.")

    h3("What happens if I never call rigLStep()?")
    p("You get static random sparsity: the Bernoulli mask from initialisation, "
      "frozen. The model still trains and will reach a noticeably worse "
      "accuracy than either dense or RigL. This is also, unfortunately, what "
      "defect D3 silently degrades to - which is why the `grow thresh` line in "
      "your log deserves attention.")

    h3("Why every 100 steps and not every step?")
    p("Two reasons. Cost: a RigL step is O(n) or worse per layer and would be a "
      "significant fraction of the per-step budget if run every iteration. "
      "Stability: a grown weight starts at zero and needs time to become "
      "useful; swapping every step means nothing ever settles. The interval is "
      "a hyperparameter - 100 is the source's choice and a sensible default, "
      "and it interacts with alpha, since what matters is how many connections "
      "move per unit of training time.")

    h3("Can I use RigL on convolutional layers?")
    p("In principle yes - section 20.4 of the source sketches a `kernelMask` "
      "for `conv1dConfig_t` with the same treatment. In practice the "
      "consolidated `rigLStep()` skips anything that is not LINEAR, so conv "
      "support means extending both the layer loop and the conv inner loop. "
      "For the HAR model it also matters less: a 16 x 9 x 3 kernel has 432 "
      "weights against the linear layer's 73,728, so the linear layers are "
      "where the compute is.")

    h3("Should the last layer be sparse?")
    p("No. The 64 x 6 classifier is 0.5% of the model's weights, so sparsifying "
      "it saves nothing measurable, and removing connections there removes them "
      "from individual output classes - the place where damage is most visible. "
      "The same argument covers biases and normalisation parameters. Leaving "
      "the first and last layers dense is standard practice in the pruning "
      "literature and costs you almost nothing in compression.")

    h3("What is the difference between sparsity and the mask?")
    p("Sparsity is a number you choose - 0.9 - and it is fixed for the run. The "
      "mask is the specific set of active positions realising that number, and "
      "it changes every 100 steps. Note that `rigLStep()` takes a "
      "`sparsityTarget` argument in the source and never uses it: the sparsity "
      "is whatever the initial `bernoulliFillMask()` created, and rigLStep only "
      "preserves it.")

    h3("My active count is 7,412 but I asked for 7,373. Is that a bug?")
    p("No. `bernoulliFillMask` makes an independent draw per weight, so the "
      "realised count is binomial: for 73,728 weights at p = 0.1 the mean is "
      "7,373 with a standard deviation of about 81. A count within a few "
      "hundred of the target is expected. If you need exactly the target, "
      "shuffle an array with exactly that many ones instead of drawing "
      "independently.")

    h3("Do I need FQT and quantization working before RigL?")
    p("No, and it is easier if you do not. Everything in this document assumes "
      "FLOAT32 weights and gradients - the direct `(float*)t->data` casts are "
      "only valid in that case. Get RigL correct in float first; extending the "
      "threshold comparisons to SYM_INT32 mantissas, which requires "
      "reconstructing `mantissa * scale` before comparing magnitudes, is a "
      "separate and clearly-scoped piece of work.")


# =============================================================================
def ch_appendix_glossary():
    chapter("Appendix - Glossary")
    p("Every term used in this document, in one place. ODT-specific terms are "
      "marked (ODT); the rest are general to sparse training.")
    gloss = [
        ("active weight", "A weight whose mask bit is 1. It participates in the "
         "forward pass and is updated by the optimiser."),
        ("alpha, alpha(t)", "The fraction of active weights swapped at a RigL "
         "step. Decays from alphaInit (0.3) to zero on a cosine schedule."),
        ("alphaInit", "The starting value of alpha. 0.3 in the source, meaning "
         "30% of connections move at the first swap."),
        ("bernoulliFillMask", "(ODT) Fills a BOOL tensor with independent "
         "Bernoulli draws. Its argument is P(ACTIVE), so 90% sparsity means "
         "passing 0.1."),
        ("bit packing", "Storing one boolean per bit rather than per byte. A "
         "73,728-element mask occupies 9,216 bytes."),
        ("BOOL tensor", "(ODT) A tensor whose quantization type is BOOL; the "
         "storage format for a mask."),
        ("conservation", "The RigL invariant that K weights dropped equals K "
         "weights grown, so the active count never changes."),
        ("CSR", "Compressed Sparse Row - a format that stores only non-zeros "
         "plus indices. Saves memory, loses O(1) random access; not used here."),
        ("dense", "The ordinary, unmasked case. In ODT a layer is dense exactly "
         "when its weightMask is NULL."),
        ("DROP", "The half of a RigL step that deactivates the K active weights "
         "with the smallest |w|."),
        ("executeOp", "(ODT) The universal funnel through which kernels are "
         "invoked, with prologue, kernel and epilogue stages."),
        ("flat index", "The one-dimensional position of an element in a "
         "row-major tensor: row * columnsPerRow + column. The mask, the weight "
         "and its gradient all share it."),
        ("FQT", "Fully Quantized Training - the integer-arithmetic training path "
         "in ODT, in which weights and gradients may be SYM_INT32 rather than "
         "FLOAT32."),
        ("GROW", "The half of a RigL step that activates the K inactive weights "
         "with the largest |gradient|."),
        ("HAR", "Human Activity Recognition - the target task: classifying "
         "activities from wrist-worn IMU signals."),
        ("inactive weight", "A weight whose mask bit is 0. Skipped in the "
         "forward pass, forced to exactly 0.0 by the optimiser, but still "
         "receiving a gradient - which is what makes GROW possible."),
        ("K", "The number of weights swapped at one RigL step: "
         "floor(alpha * numActive)."),
        ("K-selection", "Finding the K-th smallest or largest value in a set. "
         "Implemented here by partial selection sort or by histogram."),
        ("kernelMask", "(ODT, proposed) The Conv1d analogue of weightMask; "
         "described in section 20.4 of the source, not implemented."),
        ("layerConfig_t", "(ODT) A union of per-layer-type configs. Reading "
         ".linear on a non-LINEAR layer yields garbage, which is why "
         "rigLStep() checks the type first."),
        ("magnitude pruning", "Removing the smallest-magnitude weights. RigL's "
         "DROP step, but without any regrowth."),
        ("mask", "The BOOL tensor recording which weights are active. One bit "
         "per weight, same element count as the weight tensor."),
        ("mask churn", "How many mask bits changed at a RigL step. Should track "
         "K and decay to zero."),
        ("MCU", "Microcontroller unit - here an STM32 Nucleo-F746ZG: Cortex-M7 "
         "at 216 MHz with 320 KB of SRAM and no MMU."),
        ("parameter_t", "(ODT) A weight tensor paired with its gradient tensor."),
        ("partial selection sort", "Selection sort stopped after K+1 positions. "
         "O(count*K) rather than O(count^2)."),
        ("PPCA replay", "(ODT) Probabilistic-PCA-based continual learning in the "
         "library; unrelated to RigL, and its chapter confirms it needs no "
         "changes."),
        ("RigL", "Rigging the Lottery: sparse training in which connectivity is "
         "learned by dropping low-magnitude weights and growing "
         "high-gradient ones."),
        ("rigLStep", "The function that performs one DROP/GROW update over "
         "every sparse layer of a model."),
        ("SR", "Stochastic rounding - rounding up or down at random with "
         "probability proportional to distance, used in ODT's integer training "
         "path."),
        ("sparsity, s", "The fraction of weights that are inactive. 0.9 means "
         "nine in ten are off."),
        ("straight-through estimator", "Treating a non-differentiable forward "
         "operation as the identity in the backward pass; used in quantization, "
         "not needed by RigL."),
        ("SYM_INT32", "(ODT) A symmetric integer tensor type storing int32 "
         "mantissas plus a scale. Weight and gradient tensors may use it under "
         "FQT, which invalidates the direct float* casts in this document."),
        ("tEnd", "The step at which alpha reaches zero and the mask freezes. "
         "Should be 0.8 x totalSteps, not totalSteps."),
        ("tensor_t", "(ODT) The universal container: shape, quantization "
         "descriptor and a flat byte buffer."),
        ("tensorBoolGet / Set", "(ODT) Read or write one mask bit by flat "
         "index."),
        ("weightMask", "(ODT) The field added to linearConfig_t holding the "
         "layer's mask, or NULL for a dense layer."),
        ("zeroInactiveWeights", "(ODT) Enforces the invariant that every "
         "inactive weight is exactly 0.0; called once at initialisation."),
    ]
    tbl(["Term", "Meaning"], [[a, b] for a, b in gloss],
        widths=[24, 76], bold_first=True)


# =============================================================================
def main():
    G.STORY.clear()
    G._counters["part"] = 0
    G._counters["chap"] = 0
    G._counters["sec"] = 0

    front()
    ch_algorithm()
    ch_worked_step()
    ch_prerequisites()
    ch_component_map()
    ch_kth_smallest()
    ch_kth_largest()
    ch_weightmask()
    ch_matmul()
    ch_sgd()
    ch_adamw()
    ch_riglstep()
    ch_serialize()
    ch_integration()
    ch_verification()
    ch_logs()
    ch_plan()
    ch_defects()
    ch_faq()
    ch_appendix_code()
    ch_appendix_glossary()
    ch_appendix_index()

    doc = G.Book(OUTPUT,
                 title="RigL on ODT - Complete Implementation, Line by Line",
                 author="Extracted from " + SOURCE,
                 subject="Consolidated RigL implementation with line-by-line "
                         "explanation",
                 creator="gen_rigl_implementation_pdf.py")
    doc.multiBuild(G.STORY)
    print("Wrote %s (%.0f KB)" % (OUTPUT, os.path.getsize(OUTPUT) / 1024.0))


if __name__ == "__main__":
    main()
