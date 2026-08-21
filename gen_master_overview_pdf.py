"""
Master Overview PDF Generator
Covers all coding files, their relationships, purposes, and all function syntaxes.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Output path ───────────────────────────────────────────────────────────────
OUTPUT = r"F:\technical material\Master thesis\claude\on_device training\Master_Overview.pdf"

# ── XML-escape helper ─────────────────────────────────────────────────────────
def xe(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK_BLUE   = colors.HexColor("#1a3a5c")
C_MID_BLUE    = colors.HexColor("#2962a8")
C_LIGHT_BLUE  = colors.HexColor("#ddeeff")
C_CODE_BG     = colors.HexColor("#f5f5f5")
C_CODE_BORDER = colors.HexColor("#cccccc")
C_GREEN_BG    = colors.HexColor("#e8f5e9")
C_GREEN_BDR   = colors.HexColor("#388e3c")
C_ORANGE_BG   = colors.HexColor("#fff3e0")
C_ORANGE_BDR  = colors.HexColor("#e65100")
C_PURPLE_BG   = colors.HexColor("#f3e5f5")
C_PURPLE_BDR  = colors.HexColor("#7b1fa2")
C_TEAL_BG     = colors.HexColor("#e0f7fa")
C_TEAL_BDR    = colors.HexColor("#00695c")
C_YELLOW_BG   = colors.HexColor("#fffde7")
C_YELLOW_BDR  = colors.HexColor("#f57f17")
C_RED_BG      = colors.HexColor("#ffebee")
C_RED_BDR     = colors.HexColor("#c62828")
C_WHITE       = colors.white
C_BLACK       = colors.black
C_GREY        = colors.HexColor("#555555")
C_LIGHT_GREY  = colors.HexColor("#eeeeee")

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

S_TITLE = ParagraphStyle("S_TITLE",
    fontSize=28, leading=34, textColor=C_DARK_BLUE,
    alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Bold")

S_SUBTITLE = ParagraphStyle("S_SUBTITLE",
    fontSize=14, leading=18, textColor=C_MID_BLUE,
    alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica")

S_H1 = ParagraphStyle("S_H1",
    fontSize=18, leading=22, textColor=C_WHITE,
    fontName="Helvetica-Bold", spaceAfter=2)

S_H2 = ParagraphStyle("S_H2",
    fontSize=14, leading=18, textColor=C_DARK_BLUE,
    fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)

S_H3 = ParagraphStyle("S_H3",
    fontSize=12, leading=15, textColor=C_MID_BLUE,
    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)

S_BODY = ParagraphStyle("S_BODY",
    fontSize=10, leading=14, textColor=C_BLACK,
    fontName="Helvetica", spaceAfter=4, alignment=TA_JUSTIFY)

S_CODE = ParagraphStyle("S_CODE",
    fontSize=8.5, leading=12, textColor=C_BLACK,
    fontName="Courier", spaceAfter=2)

S_CODE_COMMENT = ParagraphStyle("S_CODE_COMMENT",
    fontSize=8.5, leading=12, textColor=colors.HexColor("#006600"),
    fontName="Courier-Oblique", spaceAfter=2)

S_LABEL = ParagraphStyle("S_LABEL",
    fontSize=9, leading=12, textColor=C_MID_BLUE,
    fontName="Helvetica-Bold", spaceAfter=2)

S_NOTE = ParagraphStyle("S_NOTE",
    fontSize=9, leading=13, textColor=C_BLACK,
    fontName="Helvetica", spaceAfter=2)

S_EXPLAIN = ParagraphStyle("S_EXPLAIN",
    fontSize=10, leading=14, textColor=C_BLACK,
    fontName="Helvetica", spaceAfter=3, leftIndent=6)

S_TOC = ParagraphStyle("S_TOC",
    fontSize=11, leading=16, textColor=C_DARK_BLUE,
    fontName="Helvetica", spaceAfter=2, leftIndent=0)

S_TOC_SUB = ParagraphStyle("S_TOC_SUB",
    fontSize=10, leading=14, textColor=C_GREY,
    fontName="Helvetica", spaceAfter=1, leftIndent=12)

# ── Helper builders ───────────────────────────────────────────────────────────

def section_header(title, color=C_DARK_BLUE):
    """Full-width dark banner for major section headings."""
    data = [[Paragraph(xe(title), S_H1)]]
    t = Table(data, colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), color),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING",(0,0), (-1,-1), 10),
    ]))
    return t

def sub_header(title):
    return Paragraph(xe(title), S_H2)

def func_header(sig):
    """Highlighted box for a function signature."""
    data = [[Paragraph(xe(sig), S_CODE)]]
    t = Table(data, colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_CODE_BG),
        ("BOX",           (0,0), (-1,-1), 1, C_CODE_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    return t

def explain_box(label, text, bg=C_LIGHT_BLUE, bdr=C_MID_BLUE):
    """Coloured explanation box."""
    content = [
        Paragraph(xe(label), S_LABEL),
        Paragraph(xe(text),  S_NOTE),
    ]
    data = [[content]]
    t = Table(data, colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("BOX",           (0,0), (-1,-1), 1, bdr),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t

def purpose_box(text):
    return explain_box("PURPOSE", text, C_GREEN_BG, C_GREEN_BDR)

def depends_box(text):
    return explain_box("DEPENDS ON", text, C_ORANGE_BG, C_ORANGE_BDR)

def used_by_box(text):
    return explain_box("USED BY", text, C_PURPLE_BG, C_PURPLE_BDR)

def why_box(text):
    return explain_box("WHY THIS FILE EXISTS", text, C_TEAL_BG, C_TEAL_BDR)

def note_box(text):
    return explain_box("NOTE", text, C_YELLOW_BG, C_YELLOW_BDR)

def func_block(sig, purpose, params, returns=None, notes=None):
    """Complete function documentation block."""
    items = []
    items.append(func_header(sig))
    items.append(explain_box("PURPOSE", purpose, C_GREEN_BG, C_GREEN_BDR))
    if params:
        items.append(explain_box("PARAMETERS", params, C_LIGHT_BLUE, C_MID_BLUE))
    if returns:
        items.append(explain_box("RETURNS", returns, C_PURPLE_BG, C_PURPLE_BDR))
    if notes:
        items.append(explain_box("NOTES", notes, C_YELLOW_BG, C_YELLOW_BDR))
    items.append(Spacer(1, 6))
    return KeepTogether(items)

def dep_table(rows):
    """Two-column dependency table: File | Depends On."""
    header = [
        Paragraph("<b>File</b>", S_CODE),
        Paragraph("<b>Includes / Depends On</b>", S_CODE),
    ]
    data = [header] + [[Paragraph(xe(a), S_NOTE), Paragraph(xe(b), S_NOTE)] for a, b in rows]
    t = Table(data, colWidths=[55*mm, 115*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_LIGHT_GREY]),
        ("BOX",           (0,0), (-1,-1), 0.5, C_CODE_BORDER),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, C_CODE_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t

def layer_table(rows):
    """Architecture layer table."""
    header = [
        Paragraph("<b>Layer</b>", S_CODE),
        Paragraph("<b>Files</b>", S_CODE),
        Paragraph("<b>Role</b>", S_CODE),
    ]
    data = [header] + [[Paragraph(xe(a), S_NOTE), Paragraph(xe(b), S_NOTE), Paragraph(xe(c), S_NOTE)] for a,b,c in rows]
    t = Table(data, colWidths=[30*mm, 55*mm, 85*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_LIGHT_GREY]),
        ("BOX",           (0,0), (-1,-1), 0.5, C_CODE_BORDER),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, C_CODE_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t

def sp(n=6):
    return Spacer(1, n)

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT STORY
# ══════════════════════════════════════════════════════════════════════════════
story = []

# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────
story.append(Spacer(1, 40*mm))
story.append(Paragraph("On-Device Training Library", S_TITLE))
story.append(Paragraph("Master Code Overview", S_SUBTITLE))
story.append(Spacer(1, 6))
story.append(Paragraph("All Files · Relationships · Function Reference", S_SUBTITLE))
story.append(Spacer(1, 20*mm))
story.append(HRFlowable(width="100%", thickness=2, color=C_MID_BLUE))
story.append(sp(8))
story.append(Paragraph(
    "This document is a complete reference for the On-Device Training (ODT) C library. "
    "It covers every source file in the project, explains why each file exists, describes "
    "how files depend on each other, and documents every public function with its full "
    "syntax, parameter meanings, return value, and usage notes.",
    S_BODY))
story.append(sp(8))
story.append(Paragraph(
    "The project implements a lightweight neural-network training and inference engine "
    "designed to run on microcontrollers such as the STM32 Nucleo-F746ZG. "
    "It supports quantized tensors, arithmetic operations, convolutional and dense layers, "
    "loss functions, optimizers, serialization, and a clean user-facing API.",
    S_BODY))
story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 – ARCHITECTURE OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("1.  Project Architecture Overview"))
story.append(sp(8))
story.append(Paragraph(
    "The library is organised into eight layers. Each layer builds on the layer below it. "
    "A file in layer N can only include files from layer N or lower — it never reaches up.",
    S_BODY))
story.append(sp(6))

story.append(layer_table([
    ("Layer 0\n(Foundation)", "Common.h\nDTypes.h / DTypes.c", "Compiler macros (debug printing). Raw byte read/write helpers for int32 and float."),
    ("Layer 1\n(Data types)", "Quantization.h / Quantization.c", "Enum of quantization schemes (INT32, FLOAT32, SYM_INT32, SYM, ASYM, BOOL) and their config structs."),
    ("Layer 2\n(Tensor)", "Tensor.h / Tensor.c", "Core tensor_t struct: data buffer, shape, quantization, sparsity. All shape/index/size calculations live here."),
    ("Layer 3\n(Conversion)", "TensorConversion.h / TensorConversion.c", "Convert a tensor from one numeric type to another (e.g. float to quantized int). The conversionMatrix dispatch table."),
    ("Layer 4\n(Arithmetic)", "Arithmetic.h / Arithmetic.c\nAdd, Sub, Mul, Div, Matmul,\nMinMax, Log, Square, Sum,\nRounding, Comparison, ...", "Element-wise and reduction operations on tensors. Arithmetic.h/.c provides the generic engine; each operation file (Add.h/.c, etc.) provides the concrete math function."),
    ("Layer 5\n(Layers)", "Layer.h / Layer.c\nLinear, Conv1d, Relu,\nSoftmax, Dropout,\nFlatten, LayerNorm,\nAvgPool1d, MaxPool1d, ...", "Neural-network layer implementations. Each layer has a forward pass (inference) and backward pass (gradient computation) built on top of Layer 4."),
    ("Layer 6\n(Training)", "LossFunction, CrossEntropy,\nMSE, Optimizer, Sgd,\nDataLoader, NPYLoader,\nRNG, Bernoulli", "Loss computation, gradient-based weight update (SGD), dataset loading from .npy files, and random-number generation for Dropout."),
    ("Layer 7\n(User API)", "src/userApi/*\nInferenceApi, TrainingLoopApi,\nStateDictApi, StorageApi,\nTensorApi, QuantizationApi, ...", "High-level entry points that a user calls to build, train, save, and run a model. Wraps everything below behind clean function calls."),
]))

story.append(sp(10))
story.append(sub_header("Reading the dependency arrows"))
story.append(Paragraph(
    "Every arrow in the diagram below points FROM a file TO the file it includes. "
    "If file A includes file B, then A depends on B — B must compile first, and any "
    "change to B's header forces A to recompile.",
    S_BODY))
story.append(sp(6))
story.append(dep_table([
    ("Common.h",          "— (no project dependencies; only standard headers: stdio.h, string.h, stdbool.h)"),
    ("DTypes.h / .c",     "— (no project dependencies; only stddef.h, stdint.h)"),
    ("Quantization.h/.c", "Rounding.h (for rounding-mode enum)"),
    ("Tensor.h / .c",     "Common.h, DTypes.h, Quantization.h"),
    ("TensorConversion.h/.c","Common.h, DTypes.h, Tensor.h, Quantization.h"),
    ("Arithmetic.h / .c", "Common.h, DTypes.h, Tensor.h, Matmul.h"),
    ("Add.h / .c",        "Arithmetic.h, Tensor.h"),
    ("Sub.h / .c",        "Arithmetic.h, Tensor.h"),
    ("Mul.h / .c",        "Arithmetic.h, Tensor.h"),
    ("Div.h / .c",        "Arithmetic.h, Tensor.h"),
    ("Matmul.h / .c",     "Arithmetic.h, DTypes.h, Tensor.h"),
    ("Layer.h / .c",      "Tensor.h, Arithmetic.h, TensorConversion.h"),
    ("Linear.h / .c",     "Layer.h, Matmul.h, Add.h"),
    ("Conv1d.h / .c",     "Layer.h, Conv1dKernel.h, Add.h"),
    ("Relu.h / .c",       "Layer.h, Arithmetic.h"),
    ("Softmax.h / .c",    "Layer.h, Arithmetic.h, Sum.h"),
    ("LossFunction.h/.c", "Tensor.h, Arithmetic.h"),
    ("CrossEntropy.h/.c", "LossFunction.h, Log.h, Sum.h"),
    ("MSE.h / .c",        "LossFunction.h, Arithmetic.h"),
    ("Optimizer.h / .c",  "Tensor.h, Arithmetic.h"),
    ("Sgd.h / .c",        "Optimizer.h, Arithmetic.h"),
    ("DataLoader.h / .c", "Tensor.h, Dataset.h"),
    ("NPYLoader.h / .c",  "DataLoader.h, DTypes.h"),
    ("Serialize.h / .c",  "Tensor.h, DTypes.h"),
    ("Deserialize.h/.c",  "Tensor.h, DTypes.h"),
    ("RNG.h / .c",        "— (no project dependencies)"),
    ("Bernoulli.h / .c",  "RNG.h, Tensor.h"),
    ("src/userApi/*",     "All layers above"),
]))
story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 – Common.h
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("2.  Common.h", C_DARK_BLUE))
story.append(sp(8))
story.append(purpose_box(
    "Common.h is the debug-printing infrastructure for the entire library. "
    "It defines three print macros (PRINT_DEBUG, PRINT_INFO, PRINT_ERROR) plus "
    "PRINT_BYTE_ARRAY. Every other .c file can include Common.h and immediately "
    "get coloured, level-controlled console output with the source file name and "
    "calling function name automatically included."))
story.append(sp(4))
story.append(why_box(
    "On a microcontroller you cannot attach a debugger and step through code. "
    "The only feedback you get is what you print over UART. Having a single, "
    "uniform macro that prints the file name, function name, and message — and "
    "that can be silenced completely by not defining DEBUG_MODE_* — is therefore "
    "essential. Without Common.h, every .c file would need its own printf boilerplate."))
story.append(sp(4))
story.append(depends_box("Standard library only: stdio.h, string.h, stdbool.h. No other project file."))
story.append(sp(4))
story.append(used_by_box(
    "Every .c file in the project. It is the most widely included header in the codebase."))

story.append(sp(8))
story.append(sub_header("Macros defined in Common.h"))

story.append(func_block(
    "#define DLEVEL  0 | 1 | 2 | 3",
    "Sets the global debug level. 0 = silent, 1 = errors only, 2 = info+errors, 3 = all. "
    "Determined at compile time by whether DEBUG_MODE_ERROR, DEBUG_MODE_INFO, or "
    "DEBUG_MODE_DEBUG is defined as a compiler flag (e.g. -DDEBUG_MODE_DEBUG).",
    "No parameters — this is a compile-time constant.",
    None,
    "If none of the DEBUG_MODE_* flags are set, DLEVEL = 0 and ALL print macros "
    "produce zero code — the compiler optimises the entire do{...}while(false) away."))

story.append(func_block(
    "#define PRINT_DEBUG(str, ...)",
    "Prints a yellow-coloured debug message to stdout. Only active when DLEVEL >= 3 "
    "(i.e. -DDEBUG_MODE_DEBUG was passed to the compiler). "
    "The output format is: [SourceFile: FunctionName] your message",
    "str: a printf-style format string literal. ...: optional extra arguments matching the format string.",
    None,
    "The SOURCE_FILE macro is defined by each .c file with #define SOURCE_FILE \"MYFILE\" "
    "before including Common.h. The __FUNCTION__ macro is a C99 built-in that expands to "
    "the name of the current function at compile time."))

story.append(func_block(
    "#define PRINT_INFO(str, ...)",
    "Prints a plain (no colour) informational message. Active when DLEVEL >= 2.",
    "str: format string. ...: variadic arguments.",
    None, None))

story.append(func_block(
    "#define PRINT_ERROR(str, ...)",
    "Prints a RED-coloured error message. Active when DLEVEL >= 1. "
    "Used throughout the library to report illegal arguments, mismatched dimensions, "
    "and unsupported type combinations before calling exit(1).",
    "str: format string. ...: variadic arguments.",
    None,
    "PRINT_ERROR is always paired with exit(1) in the project code. "
    "The macro does not call exit itself — the calling function does that."))

story.append(func_block(
    "#define PRINT_BYTE_ARRAY(prefix, byteArray, numberOfBytes)",
    "Dumps a raw byte array to stdout in hex format, e.g. 0x1A 0x2B 0x3C. "
    "Useful for inspecting the raw memory content of a tensor's data field.",
    "prefix: a label string printed before the hex bytes.\n"
    "byteArray: pointer to uint8_t array.\n"
    "numberOfBytes: how many bytes to print.",
    None, None))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 – DTypes.h / DTypes.c
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("3.  DTypes.h / DTypes.c", C_DARK_BLUE))
story.append(sp(8))
story.append(purpose_box(
    "DTypes provides the bridge between the raw byte storage inside a tensor and the "
    "typed C values (int32_t, float) that arithmetic code needs to work with. "
    "A tensor stores all its data as a uint8_t byte array. Before you can add two "
    "tensor elements you must reassemble four bytes back into an int32_t or float. "
    "DTypes does exactly that — and nothing else."))
story.append(sp(4))
story.append(why_box(
    "C does not let you safely cast a uint8_t* to an int32_t* — that would violate "
    "strict aliasing rules and produce undefined behaviour. The correct approach is "
    "memcpy, which DTypes wraps in named functions so the rest of the code stays "
    "readable. Having this in one place also means you change the byte order or "
    "packing format in exactly one file if hardware requires it."))
story.append(sp(4))
story.append(depends_box("stddef.h (for size_t), stdint.h (for uint8_t, int32_t). No project dependencies."))
story.append(sp(4))
story.append(used_by_box(
    "Tensor.c, TensorConversion.c, Arithmetic.c (and every file that does arithmetic "
    "or conversion), Serialize.c, Deserialize.c, NPYLoader.c."))

story.append(sp(8))
story.append(sub_header("Functions in DTypes.h / DTypes.c"))

story.append(func_block(
    "int32_t  readBytesAsInt32(uint8_t *bytes)",
    "Reads 4 bytes from the address 'bytes' and reassembles them into a signed 32-bit integer. "
    "Uses memcpy internally to avoid undefined behaviour.",
    "bytes: pointer to the first of the 4 bytes to read. "
    "In practice this is always &tensor->data[byteIndex] where byteIndex is a multiple of 4.",
    "Returns the int32_t value stored at that memory location.",
    "This is the single most-called function in the entire library. "
    "Every arithmetic operation on INT32 or SYM_INT32 tensors calls it once per element."))

story.append(func_block(
    "int32_t  readNumberOfBytesAsInt32(uint8_t *data, size_t numberOfBytes)",
    "Reads 'numberOfBytes' bytes (not necessarily 4) and sign-extends them into an int32_t. "
    "Used for tensors that pack data at less than 32 bits per element.",
    "data: pointer to byte array.\nnumberOfBytes: how many bytes to consume (1, 2, 3, or 4).",
    "int32_t: the sign-extended integer value.",
    None))

story.append(func_block(
    "void  readBytesAsInt32Array(size_t numberOfValues, uint8_t *bytes, int32_t *outputArray)",
    "Converts an entire byte buffer into an array of int32_t values by calling "
    "readBytesAsInt32 in a loop — one call per 4-byte group.",
    "numberOfValues: number of int32_t values to extract.\n"
    "bytes: source byte array (must be at least numberOfValues*4 bytes long).\n"
    "outputArray: pre-allocated int32_t array that receives the results.",
    "void (writes into outputArray).", None))

story.append(func_block(
    "float  readBytesAsFloat(uint8_t *bytes)",
    "Reads 4 bytes and reassembles them as an IEEE 754 single-precision float. "
    "The companion of readBytesAsInt32 for FLOAT32 tensors.",
    "bytes: pointer to 4 bytes in the tensor data buffer.",
    "float: the floating-point value at that location.",
    "Like readBytesAsInt32, this uses memcpy to stay within the C standard."))

story.append(func_block(
    "void  readBytesAsFloatArray(size_t numberOfValues, uint8_t *bytes, float *outputArray)",
    "Bulk-converts a byte buffer into a float array.",
    "numberOfValues, bytes, outputArray — same pattern as readBytesAsInt32Array.",
    "void (writes into outputArray).", None))

story.append(func_block(
    "void  writeInt32ToByteArray(int32_t value, uint8_t *bytes)",
    "Writes a 32-bit signed integer into 4 consecutive bytes of a byte array. "
    "This is the inverse of readBytesAsInt32 and is called after every arithmetic result "
    "to store the answer back into a tensor's data field.",
    "value: the int32_t result to store.\n"
    "bytes: pointer to 4 bytes in the output tensor's data buffer.",
    "void — modifies the bytes in place.",
    "Always call this with &tensor->data[i*4] where i is the element index."))

story.append(func_block(
    "void  writeInt32ArrayToByteArray(size_t numberOfValues, int32_t *valueArray, uint8_t *bytes)",
    "Bulk-writes an array of int32_t values into a byte buffer.",
    "numberOfValues: number of values to write.\n"
    "valueArray: source int32_t array.\n"
    "bytes: destination byte buffer (must be at least numberOfValues*4 bytes).",
    "void.", None))

story.append(func_block(
    "void  writeFloatToByteArray(float value, uint8_t *bytes)",
    "Writes a float into 4 consecutive bytes. Inverse of readBytesAsFloat.",
    "value: the float to store.\nbytes: destination in the tensor data buffer.",
    "void.", None))

story.append(func_block(
    "void  writeFloatArrayToByteArray(size_t numberOfValues, float *valueArray, uint8_t *bytes)",
    "Bulk float-to-bytes write.",
    "numberOfValues, valueArray, bytes.", "void.", None))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 – Quantization.h / Quantization.c
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("4.  Quantization.h / Quantization.c", C_DARK_BLUE))
story.append(sp(8))
story.append(purpose_box(
    "Quantization.h defines the type system for how tensors store numbers. "
    "On a microcontroller you cannot afford 32-bit floats everywhere. "
    "Quantization lets you represent values as small integers with a scale factor. "
    "This file defines: (a) the qtype_t enum naming the six supported schemes, "
    "(b) the config structs that store scale, zeroPoint, and bit-width for each scheme, "
    "and (c) init functions that fill those structs with safe default values."))
story.append(sp(4))
story.append(why_box(
    "Without a uniform type system, every function would need to know whether a tensor "
    "holds floats, ints, or some quantized variant. The quantization_t struct bundles "
    "the scheme (qtype_t) with its parameters (qConfig void*) so that any function "
    "receiving a tensor_t can immediately inspect what kind of numbers are inside."))
story.append(sp(4))
story.append(depends_box("Rounding.h (for roundingMode_t enum used in qConfig structs)."))
story.append(sp(4))
story.append(used_by_box("Tensor.h (embedded in tensor_t), TensorConversion.h/.c, any layer that creates tensors."))

story.append(sp(8))
story.append(sub_header("Key types defined in Quantization.h"))
story.append(note_box(
    "qtype_t enum — six values:\n"
    "  INT32    — raw 32-bit signed integer, no scale (used for intermediate accumulation)\n"
    "  FLOAT32  — IEEE 754 single-precision float\n"
    "  SYM_INT32 — symmetric quantization: real = mantissa * scale, centred at 0\n"
    "  SYM     — symmetric with configurable bit-width (e.g. 8-bit)\n"
    "  ASYM    — asymmetric: real = (mantissa - zeroPoint) * scale\n"
    "  BOOL    — single-bit boolean stored in packed bytes\n\n"
    "quantization_t struct — two fields:\n"
    "  qtype_t type   — which scheme is being used\n"
    "  void *qConfig  — pointer to the matching config struct (symInt32QConfig_t, "
    "asymQConfig_t, etc.)"))

story.append(sp(6))
story.append(sub_header("Functions in Quantization.h / Quantization.c"))

story.append(func_block(
    "void  initSymInt32QConfig(roundingMode_t roundingMode, symInt32QConfig_t *symInt32QConfig)",
    "Fills a symInt32QConfig_t with default values: scale = 1.0, qMaxBits = 16. "
    "The scale of 1.0 means no quantization effect initially — it is updated by "
    "requantSymInt32Tensor when the actual range is known.",
    "roundingMode: how to round when quantizing (e.g. ROUND_NEAREST).\n"
    "symInt32QConfig: pointer to the struct to initialise.",
    "void.", None))

story.append(func_block(
    "void  initSymInt32QConfigWithQMaxBits(roundingMode_t roundingMode,\n"
    "          symInt32QConfig_t *symInt32QConfig, uint8_t qMaxBits)",
    "Same as initSymInt32QConfig but lets you choose a custom bit-width instead "
    "of the default 16. qMax = 2^(qMaxBits-1) - 1.",
    "roundingMode, symInt32QConfig: same as above.\nqMaxBits: number of bits for the quantized range.",
    "void.", None))

story.append(func_block(
    "void  initSymQConfig(uint8_t qBits, roundingMode_t roundingMode, symQConfig_t *symQConfig)",
    "Initialises a symQConfig_t for symmetric quantization at a given bit-width.",
    "qBits: total bits per element (e.g. 8).\nroundingMode.\nsymQConfig: target struct.",
    "void.", None))

story.append(func_block(
    "void  initAsymQConfig(uint8_t qBits, roundingMode_t roundingMode, asymQConfig_t *asymQConfig)",
    "Initialises an asymQConfig_t. Sets scale=1.0, zeroPoint=0 as defaults.",
    "qBits, roundingMode, asymQConfig.", "void.", None))

story.append(func_block(
    "void  initInt32Quantization(quantization_t *quantization)",
    "Sets quantization->type = INT32 and quantization->qConfig = NULL. "
    "Use this when a tensor will store raw int32_t values with no scale factor.",
    "quantization: pointer to the quantization_t to initialise.", "void.", None))

story.append(func_block(
    "void  initFloat32Quantization(quantization_t *quantization)",
    "Sets type = FLOAT32, qConfig = NULL.",
    "quantization.", "void.", None))

story.append(func_block(
    "void  initBoolQuantization(quantization_t *quantization)",
    "Sets type = BOOL, qConfig = NULL.",
    "quantization.", "void.", None))

story.append(func_block(
    "void  initSymInt32Quantization(symInt32QConfig_t *symInt32QConfig,\n"
    "          quantization_t *quantization)",
    "Sets type = SYM_INT32, qConfig = symInt32QConfig (cast to void*). "
    "After calling this, the quantization_t is fully wired: the type field tells "
    "code which scheme to use and the qConfig pointer leads to the scale and bit-width.",
    "symInt32QConfig: pre-filled config struct.\nquantization: target wrapper struct.",
    "void.", None))

story.append(func_block(
    "void  initSymQuantization(symQConfig_t *symQConfig, quantization_t *quantization)",
    "Sets type = SYM, qConfig = symQConfig.", "symQConfig, quantization.", "void.", None))

story.append(func_block(
    "void  initAsymQuantization(asymQConfig_t *asymQConfig, quantization_t *quantization)",
    "Sets type = ASYM, qConfig = asymQConfig.", "asymQConfig, quantization.", "void.", None))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 – Tensor.h / Tensor.c
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("5.  Tensor.h / Tensor.c", C_DARK_BLUE))
story.append(sp(8))
story.append(purpose_box(
    "Tensor.h defines the fundamental data structure of the entire library: tensor_t. "
    "A tensor is an N-dimensional array of numbers. tensor_t bundles together the raw "
    "byte buffer (data), the shape metadata (how many dimensions and how large each is), "
    "the quantization info (what kind of numbers are stored), and an optional sparsity "
    "descriptor. Tensor.c implements all the utility functions for working with that struct."))
story.append(sp(4))
story.append(why_box(
    "Every layer, every operation, every loss function operates on tensor_t pointers. "
    "By keeping the data type generic (uint8_t*) and attaching quantization metadata, "
    "the same tensor struct can hold floats, ints, or quantized integers without "
    "changing any of the layer code. The layer just reads the quantization field to "
    "know how to interpret the bytes."))
story.append(sp(4))
story.append(depends_box("Common.h, DTypes.h, Quantization.h, stdbool.h, stddef.h, stdint.h."))
story.append(sp(4))
story.append(used_by_box("Every single other file in the project. Tensor.h is the most important header."))

story.append(sp(6))
story.append(note_box(
    "Key structs:\n\n"
    "shape_t {\n"
    "  size_t  numberOfDimensions;   // how many axes (1=vector, 2=matrix, ...)\n"
    "  size_t *dimensions;           // size of each axis, in PHYSICAL storage order\n"
    "  size_t *orderOfDimensions;    // logical axis ordering (supports transpose)\n"
    "}\n\n"
    "tensor_t {\n"
    "  uint8_t       *data;          // raw byte storage for all elements\n"
    "  shape_t       *shape;         // dimension metadata\n"
    "  quantization_t *quantization; // how bytes map to real values\n"
    "  sparsity_t    *sparsity;      // optional sparsity structure (can be NULL)\n"
    "}\n\n"
    "parameter_t {\n"
    "  tensor_t *param;  // the weight tensor\n"
    "  tensor_t *grad;   // the gradient tensor (same shape as param)\n"
    "}"))

story.append(sp(8))
story.append(sub_header("Functions in Tensor.h / Tensor.c"))

story.append(func_block(
    "uint32_t  getBitmask(uint32_t startbit, uint32_t endbit)",
    "Returns a 32-bit integer with bits set to 1 from startbit to endbit (inclusive). "
    "Used internally for bit-level tensor operations such as packing BOOL tensors.",
    "startbit: lowest bit position (0 = LSB).\nendbit: highest bit position.",
    "uint32_t bitmask.", None))

story.append(func_block(
    "uint8_t  writeByte(uint8_t existingData, uint8_t data, uint8_t startbit, uint8_t endbit)",
    "Writes bits from 'data' into positions startbit..endbit of 'existingData', "
    "leaving all other bits untouched. Used for BOOL tensor packing.",
    "existingData: the byte being modified.\ndata: the value to write into the bit range.\n"
    "startbit / endbit: bit range within the byte.",
    "uint8_t: the modified byte.", None))

story.append(func_block(
    "uint8_t  readByte(uint8_t data, uint8_t startbit, uint8_t endbit)",
    "Extracts bits startbit..endbit from 'data' and returns them right-aligned.",
    "data: the source byte.\nstartbit / endbit: bit range to extract.",
    "uint8_t: extracted bit field.", None))

story.append(func_block(
    "void  byteConversion(uint8_t *dataIn, size_t dataInBits,\n"
    "          uint8_t *dataOut, size_t dataOutBits, size_t numValues)",
    "Converts between different per-element bit widths. For example, going from "
    "1-bit (BOOL) to 8-bit storage or vice versa.",
    "dataIn: source byte array.\ndataInBits: bits per element in source.\n"
    "dataOut: destination byte array.\ndataOutBits: bits per element in destination.\n"
    "numValues: how many logical values to convert.",
    "void.", None))

story.append(func_block(
    "bool  tensorBoolGet(tensor_t const *tensor, size_t flatIndex)",
    "Reads a single boolean value from a BOOL tensor at a given flat element index. "
    "Since booleans are stored packed (1 bit each), this extracts the correct bit "
    "from the correct byte.",
    "tensor: pointer to a BOOL tensor.\nflatIndex: zero-based element index.",
    "bool: true or false.", None))

story.append(func_block(
    "void  tensorBoolSet(tensor_t *tensor, size_t flatIndex, bool value)",
    "Writes a boolean value into a BOOL tensor at flatIndex.",
    "tensor: BOOL tensor.\nflatIndex: element index.\nvalue: true or false.",
    "void.", None))

story.append(func_block(
    "tensor_t *getParamFromParameter(parameter_t *parameter)",
    "Returns the weight tensor pointer from a parameter_t.",
    "parameter: pointer to a parameter_t.", "tensor_t *param.", None))

story.append(func_block(
    "tensor_t *getGradFromParameter(parameter_t *parameter)",
    "Returns the gradient tensor pointer from a parameter_t.",
    "parameter: pointer to a parameter_t.", "tensor_t *grad.", None))

story.append(func_block(
    "size_t  calcBytesPerElement(quantization_t *quantization)",
    "Returns how many bytes one element occupies, based on the quantization type. "
    "INT32 and FLOAT32 and SYM_INT32 return 4. BOOL returns 0 (sub-byte). "
    "SYM and ASYM return bytes based on qBits.",
    "quantization: the quantization descriptor of a tensor.",
    "size_t: bytes per element.", None))

story.append(func_block(
    "size_t  calcBitsPerElement(quantization_t *quantization)",
    "Like calcBytesPerElement but returns bits. Needed for BOOL (1 bit/element).",
    "quantization.", "size_t: bits per element.", None))

story.append(func_block(
    "size_t  calcBytesPerTensor(tensor_t *tensor)",
    "Returns the total number of bytes occupied by all elements in the tensor's "
    "data buffer. Equal to numberOfElements * bytesPerElement (rounded up for BOOL).",
    "tensor: any tensor_t.", "size_t: total byte count.", None))

story.append(func_block(
    "size_t  calcNumberOfBytesForData(quantization_t *q, size_t numberOfElements)",
    "Given a quantization scheme and element count, returns the byte count needed. "
    "Lower-level version of calcBytesPerTensor — used when you have the count "
    "before the tensor is fully built.",
    "q: quantization descriptor.\nnumberOfElements: how many values to store.",
    "size_t: byte count.", None))

story.append(func_block(
    "size_t  calcNumberOfElementsByShape(shape_t *shape)",
    "Multiplies all dimension sizes together to get the total element count. "
    "For a 3×4×5 tensor this returns 60.",
    "shape: pointer to a shape_t.",
    "size_t: total element count.", None))

story.append(func_block(
    "size_t  calcNumberOfElementsByTensor(tensor_t *tensor)",
    "Convenience wrapper: calls calcNumberOfElementsByShape on tensor->shape.",
    "tensor: any tensor_t.", "size_t: total element count.", None))

story.append(func_block(
    "size_t  calcNumberOfElementsByParameter(parameter_t *parameter)",
    "Returns element count of the param tensor inside the parameter_t.",
    "parameter.", "size_t.", None))

story.append(func_block(
    "void  transposeTensor(tensor_t *tensor, size_t dim0Index, size_t dim1Index)",
    "Swaps two axes of a tensor by swapping their entries in orderOfDimensions. "
    "No data is moved — only the metadata changes. Any subsequent index calculation "
    "using calcElementIndexByIndices will automatically respect the new order.",
    "tensor: the tensor to transpose.\n"
    "dim0Index: logical index of the first axis to swap.\n"
    "dim1Index: logical index of the second axis to swap.",
    "void (modifies tensor->shape->orderOfDimensions in place).",
    "This is a zero-cost transpose — it is O(1) regardless of tensor size."))

story.append(func_block(
    "void  setTensorValues(tensor_t *tensor, uint8_t *data, shape_t *shape,\n"
    "          quantization_t *quantization, sparsity_t *sparsity)",
    "Fills all four fields of a tensor_t at once. This is the standard way to "
    "initialise a tensor after the caller has already allocated all the sub-structs.",
    "tensor: the tensor to fill.\ndata: pre-allocated byte buffer.\n"
    "shape: pre-filled shape.\nquantization: pre-filled quantization.\n"
    "sparsity: sparsity descriptor or NULL.",
    "void.", None))

story.append(func_block(
    "void  setTensorValuesForConversion(uint8_t *data, quantization_t *q,\n"
    "          tensor_t *originalTensor, tensor_t *outputTensor)",
    "Sets up outputTensor to use the given data buffer and quantization while "
    "copying shape and sparsity from originalTensor. Used in TensorConversion.c "
    "when the output tensor needs the same shape but a different numeric type.",
    "data: new byte buffer for the output.\nq: output quantization.\n"
    "originalTensor: source for shape/sparsity.\noutputTensor: tensor to configure.",
    "void.", None))

story.append(func_block(
    "void  setParameterValues(parameter_t *parameter, tensor_t *param, tensor_t *grad)",
    "Fills a parameter_t with its weight and gradient tensors.",
    "parameter, param, grad.", "void.", None))

story.append(func_block(
    "void  setOrderOfDimsForNewTensor(size_t numberOfDimensions, size_t *orderOfDimensions)",
    "Initialises orderOfDimensions to the identity: [0, 1, 2, ..., N-1]. "
    "Call this when creating a new tensor that is not transposed.",
    "numberOfDimensions: number of axes.\norderOfDimensions: array to fill.",
    "void.", None))

story.append(func_block(
    "void  setShape(shape_t *shape, size_t *dims, size_t numberOfDims, size_t *orderOfDims)",
    "Fills all three fields of a shape_t at once.",
    "shape: target struct.\ndims: dimension sizes.\nnumberOfDims: rank.\norderOfDims: ordering array.",
    "void.", None))

story.append(func_block(
    "void  printTensor(tensor_t *t)",
    "Prints tensor shape and raw byte data to stdout. Used for debugging.",
    "t: any tensor.", "void.", None))

story.append(func_block(
    "void  printShape(shape_t *shape)",
    "Prints dimension count and each dimension size.",
    "shape.", "void.", None))

story.append(func_block(
    "void  copyTensor(tensor_t *dest, tensor_t *src)",
    "Copies all fields of src into dest. This is a shallow copy of the struct "
    "fields (the pointers themselves are copied, not the data they point to).",
    "dest: destination tensor.\nsrc: source tensor.",
    "void.", None))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 – TensorConversion.h / TensorConversion.c
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("6.  TensorConversion.h / TensorConversion.c", C_DARK_BLUE))
story.append(sp(8))
story.append(purpose_box(
    "TensorConversion converts tensors from one numeric type to another. "
    "It answers the question: 'I have a FLOAT32 tensor; I need a SYM_INT32 tensor "
    "with the same values.' The conversion dispatch table (conversionMatrix) is a "
    "6×6 grid of function pointers indexed by [fromType][toType]. "
    "The single public entry point convertTensor() looks up and calls the right converter."))
story.append(sp(4))
story.append(why_box(
    "Neural-network training produces activations as floats but the hardware stores "
    "weights as quantized integers. You need a systematic way to move data between "
    "representations without writing special-case code everywhere. "
    "The matrix dispatch pattern means adding a new type requires filling in one new "
    "row and column, not touching existing code."))
story.append(sp(4))
story.append(depends_box("Common.h, DTypes.h, Tensor.h, Quantization.h."))
story.append(sp(4))
story.append(used_by_box("Layer files that need to requantize activations, the user API QuantizationApi, and directly by training loop code."))

story.append(sp(8))
story.append(sub_header("The conversionMatrix — the dispatch table"))
story.append(Paragraph(
    "conversionMatrix[6][6] is declared as extern in TensorConversion.h and defined "
    "in TensorConversion.c. Entry [i][j] holds a pointer to the function that converts "
    "from type i to type j. If a conversion is not supported, the entry holds "
    "a pointer to unsupportedConversionTypes() which prints an error and exits. "
    "The indices map to the qtype_t enum: "
    "0=INT32, 1=FLOAT32, 2=SYM_INT32, 3=SYM, 4=ASYM, 5=BOOL.",
    S_BODY))
story.append(sp(4))
story.append(note_box(
    "A _Static_assert at the bottom of TensorConversion.c checks that BOOL+1 == 6. "
    "If a new qtype_t value is ever added to the enum, this assertion will fail at "
    "compile time, reminding the developer to extend the matrix. "
    "This is a safety net built into the code."))

story.append(sp(8))
story.append(sub_header("Functions in TensorConversion.h / TensorConversion.c"))

story.append(func_block(
    "typedef void (*conversionFunction_t)(tensor_t *inputTensor, tensor_t *outputTensor)",
    "Defines the function-pointer type used in conversionMatrix. "
    "Every converter in the file has this exact signature: take the input tensor and "
    "the output tensor (which is already allocated), and fill the output with converted values.",
    "inputTensor: the source tensor whose data field will be read.\n"
    "outputTensor: the destination tensor whose data field will be written.",
    "void (the output tensor is modified in place).",
    "This is a typedef, not a function. It creates a new type name. "
    "You can declare a variable of this type: conversionFunction_t fn = someFunction;"))

story.append(func_block(
    "void  convertTensor(tensor_t *inputTensor, tensor_t *outputTensor)",
    "The main entry point for all type conversions. "
    "First checks if input and output have the same qtype_t — if so, calls "
    "convertTensorsWithSameType (memmove + copy metadata). "
    "Otherwise looks up conversionMatrix[inputType][outputType] and calls that function.",
    "inputTensor: source tensor.\noutputTensor: pre-allocated output tensor with the desired quantization set.",
    "void.", None))

story.append(func_block(
    "void  requantSymInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor)",
    "Re-quantizes a SYM_INT32 tensor into another SYM_INT32 tensor using a "
    "DYNAMICALLY computed scale. Two-pass algorithm:\n"
    "  Pass A (read-only): scan all elements to find absMax = max|mantissa * inScale|.\n"
    "  Compute fresh scale = absMax / qMax.\n"
    "  Pass B: for each element, out = round(clamp(mantissa * inScale / scale, qMin, qMax)).\n"
    "Writes the new scale to outputTensor->quantization->qConfig->scale.",
    "inputTensor: SYM_INT32 source.\noutputTensor: SYM_INT32 destination with qMaxBits set.",
    "void.",
    "IN-PLACE SAFE: inputTensor == outputTensor is allowed because Pass A only reads "
    "and Pass B does a same-index read-then-write. The new scale is computed before "
    "any writes begin. This function is wired into conversionMatrix[SYM_INT32][SYM_INT32]."))

story.append(func_block(
    "void  requantSymInt32TensorToScale(tensor_t *inputTensor, tensor_t *outputTensor)",
    "Like requantSymInt32Tensor but uses a PRE-SET target scale from "
    "outputTensor->quantization->qConfig->scale instead of computing a fresh one. "
    "Values that fall outside [qMin, qMax] are clamped (saturated). "
    "The caller must set the output scale before calling this function.",
    "inputTensor: SYM_INT32 source.\noutputTensor: SYM_INT32 destination with scale already set.",
    "void.",
    "SATURATES BY DESIGN: the clamping is intentional, not an error. "
    "NOT wired into conversionMatrix — must be called directly."))

story.append(func_block(
    "char *quantTypeToString(qtype_t t)",
    "Returns a human-readable string for a qtype_t value, e.g. \"SYM_INT32\". "
    "Used in error messages and debug output.",
    "t: any qtype_t value.", "char*: static string literal.", None))

story.append(func_block(
    "extern conversionFunction_t conversionMatrix[6][6]",
    "The dispatch table. Declared extern so other files can read it directly, "
    "e.g. to call conversionMatrix[SYM_INT32][FLOAT32](input, output).",
    "N/A — this is a variable declaration, not a function.",
    "N/A.", None))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 – Arithmetic.h / Arithmetic.c
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("7.  Arithmetic.h / Arithmetic.c", C_DARK_BLUE))
story.append(sp(8))
story.append(purpose_box(
    "Arithmetic.h / Arithmetic.c provides the generic engine for element-wise "
    "(point-wise) operations on tensors. Instead of implementing 'add', 'subtract', "
    "'multiply' as separate loops, this file implements a SINGLE loop that takes a "
    "function pointer as a parameter. You pass in a function like 'int32 add(a, b)' "
    "and the loop calls it for every corresponding pair of elements. "
    "This pattern means all element-wise ops share one engine and any new operation "
    "is just one small function."))
story.append(sp(4))
story.append(why_box(
    "Writing a separate loop for Add, Sub, Mul, Div, etc. would duplicate hundreds "
    "of lines of index calculation code. The function-pointer pattern keeps the "
    "loop logic in one place (Arithmetic.c) and keeps each concrete operation "
    "small (just the math, no looping). It also means index operations (including "
    "transpose-aware addressing) need to be correct in only one place."))
story.append(sp(4))
story.append(depends_box("Common.h, DTypes.h, Tensor.h, Matmul.h (for calcNumberOfElementsByTensor)."))
story.append(sp(4))
story.append(used_by_box("Add.h/.c, Sub.h/.c, Mul.h/.c, Div.h/.c, and all other operation files. Also Layer.h/.c."))

story.append(sp(6))
story.append(note_box(
    "Two function-pointer typedefs:\n\n"
    "  typedef int32_t (*int32ElementArithmeticFunc_t)(int32_t a, int32_t b)\n"
    "  -- A function that takes two int32_t values and returns one int32_t.\n"
    "     Example: int32_t addInts(int32_t a, int32_t b) { return a + b; }\n\n"
    "  typedef float (*floatElementArithmeticFunc_t)(float a, float b)\n"
    "  -- The float version of the same pattern.\n\n"
    "Four operation patterns:\n"
    "  PointWise             -- A op B -> output  (two tensors in, one tensor out)\n"
    "  PointWiseInplace      -- A op B -> A       (result overwrites A)\n"
    "  ElementWithTensor     -- scalar x op every element of tensor -> output\n"
    "  ElementWithTensorInplace -- same but result overwrites tensor"))

story.append(sp(8))
story.append(sub_header("Index helper functions"))

story.append(func_block(
    "size_t  getDimensionsByIndex(tensor_t *tensor, size_t index)",
    "Finds the logical dimension size for axis 'index'. "
    "Loops through orderOfDimensions[] to find which physical slot has logical index 'index', "
    "then returns dimensions[that slot]. This respects any transpose that was applied.",
    "tensor: any tensor.\nindex: logical axis number (0 = outermost / row axis).",
    "size_t: size of that logical dimension.  Exits with error if not found.",
    None))

story.append(func_block(
    "void  orderDims(tensor_t *tensor, size_t *orderedDims)",
    "Fills orderedDims[0..N-1] with the logical dimension sizes in logical order. "
    "orderedDims[i] = getDimensionsByIndex(tensor, i). "
    "After this call, orderedDims is a transpose-aware snapshot of the shape.",
    "tensor: any tensor.\norderedDims: caller-allocated array of size numberOfDimensions.",
    "void.", None))

story.append(func_block(
    "bool  doDimensionsMatch(tensor_t *a, tensor_t *b)",
    "Checks that two tensors have the same rank and identical logical dimension sizes. "
    "First checks rank. Then calls orderDims on both and compares element by element. "
    "Exits with PRINT_ERROR if ranks differ.",
    "a, b: two tensors to compare.",
    "true if all dimensions match, false if any logical dimension differs.",
    "Must be called before any PointWise operation to guard against shape mismatches. "
    "All PointWise functions call this internally as their first step."))

story.append(func_block(
    "size_t  calcTensorIndexByIndices(size_t numberOfDimensions,\n"
    "          size_t *dimensions, size_t *indices)",
    "Converts a multi-dimensional index (e.g. [row=1, col=2]) into a flat integer "
    "index using row-major order. Formula (for 2D): flat = row * numCols + col. "
    "For N dimensions: starts from the last dimension and works backwards, "
    "accumulating an offset that grows by one dimension size per step.",
    "numberOfDimensions: rank.\ndimensions: array of dimension sizes.\nindices: array of per-axis positions.",
    "size_t: the flat element index.",
    "Example: tensor shape [3,4], indices [1,2] → flat = 1*4 + 2 = 6."))

story.append(func_block(
    "void  calcIndicesByRawIndex(size_t numberOfDims, size_t *dims,\n"
    "          size_t rawIndex, size_t *indices)",
    "The INVERSE of calcTensorIndexByIndices. Given a flat index, recovers the "
    "per-axis indices. First computes total elements as the product of all dims. "
    "Then peels off one axis at a time from the outermost: "
    "indices[i] = rawIndex / (total / dims[i]), then reduces rawIndex by that amount.",
    "numberOfDims: rank.\ndims: dimension sizes.\nrawIndex: the flat position.\nindices: array to fill.",
    "void (fills the indices array).",
    "Example: dims=[3,4], rawIndex=6 → total=12, peel dim0: 6/4=1, rest=6-4=2; peel dim1: 2/1=2 → [1,2]."))

story.append(func_block(
    "size_t  calcElementIndexByIndices(size_t numberOfDims, size_t *dims,\n"
    "          size_t *indices, size_t *orderOfDimensions)",
    "TRANSPOSE-AWARE flat index. First remaps the logical indices to physical order "
    "using orderOfDimensions, then applies the same row-major formula as "
    "calcTensorIndexByIndices. This is the key function that makes transposed "
    "tensors work correctly: the same logical element appears at a different physical "
    "byte position depending on the transpose state.",
    "numberOfDims, dims: shape info.\nindices: logical per-axis positions.\n"
    "orderOfDimensions: the orderOfDimensions array from the tensor's shape.",
    "size_t: the physical flat index into the data buffer.",
    "Used inside PointWise loops so that tensor A and tensor B can have different "
    "transpose states and still be combined correctly element-by-element."))

story.append(sp(8))
story.append(sub_header("PointWise arithmetic functions (two tensors)"))

story.append(func_block(
    "void  int32PointWiseArithmetic(\n"
    "          tensor_t *aTensor, tensor_t *bTensor,\n"
    "          int32ElementArithmeticFunc_t arithmeticFunc,\n"
    "          tensor_t *outputTensor)",
    "The core element-wise loop for int32 tensors, writing to a SEPARATE output tensor. "
    "For each flat position i: decode i → logical indices in A → physical byte offset in A; "
    "repeat for B; read both values; call arithmeticFunc(a, b); write result sequentially to output.",
    "aTensor: first operand (INT32 or SYM_INT32).\nbTensor: second operand.\n"
    "arithmeticFunc: the operation to apply (add, subtract, multiply, etc.).\n"
    "outputTensor: pre-allocated result tensor.",
    "void.",
    "The output is always written SEQUENTIALLY (i * bytesPerElement) even if A and B "
    "are transposed. The output tensor gets a non-transposed layout."))

story.append(func_block(
    "void  int32PointWiseArithmeticInplace(\n"
    "          tensor_t *aTensor, tensor_t *bTensor,\n"
    "          int32ElementArithmeticFunc_t arithmeticFunc)",
    "Same logic as int32PointWiseArithmetic but writes the result back into aTensor->data "
    "instead of a separate output. No output tensor parameter.",
    "aTensor: first operand; also receives the result.\nbTensor: second operand.\n"
    "arithmeticFunc: operation to apply.",
    "void (aTensor is modified in place).",
    "Use this when you no longer need the original aTensor values after the operation."))

story.append(func_block(
    "void  floatPointWiseArithmetic(\n"
    "          tensor_t *aTensor, tensor_t *bTensor,\n"
    "          floatElementArithmeticFunc_t arithmeticFunc,\n"
    "          tensor_t *outputTensor)",
    "Identical to int32PointWiseArithmetic but for FLOAT32 tensors. "
    "Uses readBytesAsFloat / writeFloatToByteArray instead of the int32 variants.",
    "aTensor, bTensor: FLOAT32 tensors.\narithmeticFunc: float operation.\noutputTensor: FLOAT32 result.",
    "void.", None))

story.append(func_block(
    "void  floatPointWiseArithmeticInplace(\n"
    "          tensor_t *aTensor, tensor_t *bTensor,\n"
    "          floatElementArithmeticFunc_t arithmeticFunc)",
    "Float in-place version. Result overwrites aTensor.",
    "aTensor, bTensor: FLOAT32 tensors.\narithmeticFunc: float operation.",
    "void.", None))

story.append(sp(8))
story.append(sub_header("ElementWithTensor functions (scalar × tensor)"))

story.append(func_block(
    "void  int32ElementWithTensorArithmetic(\n"
    "          tensor_t *aTensor, int32_t x,\n"
    "          int32ElementArithmeticFunc_t arithmeticFunc,\n"
    "          tensor_t *outputTensor)",
    "Applies arithmeticFunc(element, x) to every element of aTensor, writing to outputTensor. "
    "Simpler than PointWise — no dimension check needed and the loop is purely sequential "
    "because the scalar x is the same for every element.",
    "aTensor: input tensor.\nx: the scalar operand.\n"
    "arithmeticFunc: operation (e.g. multiply all elements by x).\noutputTensor: result.",
    "void.", None))

story.append(func_block(
    "void  int32ElementWithTensorArithmeticInplace(\n"
    "          tensor_t *aTensor, int32_t x,\n"
    "          int32ElementArithmeticFunc_t arithmeticFunc)",
    "Same but writes the result back to aTensor.",
    "aTensor: input and output.\nx: scalar.\narithmeticFunc: operation.",
    "void.", None))

story.append(func_block(
    "void  floatElementWithTensorArithmetic(\n"
    "          tensor_t *aTensor, float x,\n"
    "          floatElementArithmeticFunc_t arithmeticFunc,\n"
    "          tensor_t *outputTensor)",
    "Float version: applies arithmeticFunc(element, x) to every float element, writing to output.",
    "aTensor: FLOAT32 input.\nx: float scalar.\narithmeticFunc.\noutputTensor: FLOAT32 result.",
    "void.", None))

story.append(func_block(
    "void  floatElementWithTensorArithmeticInplace(\n"
    "          tensor_t *aTensor, float x,\n"
    "          floatElementArithmeticFunc_t arithmeticFunc)",
    "Float scalar in-place version.",
    "aTensor: FLOAT32 input and output.\nx: scalar.\narithmeticFunc.",
    "void.", None))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 – Higher-Level Files (summary)
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("8.  Higher-Level Files — Summary", C_DARK_BLUE))
story.append(sp(8))
story.append(Paragraph(
    "The files described below are built on top of the foundation files (Sections 2–7). "
    "They use the same patterns — tensor_t, function pointers, quantization types — "
    "but focus on specific neural-network operations rather than generic primitives.",
    S_BODY))

story.append(sp(6))
story.append(sub_header("8.1  Specialised Arithmetic Files (src/arithmetic/)"))
story.append(Paragraph(
    "Each file implements one concrete operation by providing a function that matches "
    "int32ElementArithmeticFunc_t or floatElementArithmeticFunc_t and passing it "
    "to the generic engine in Arithmetic.c. "
    "Add.c contains int32 add(a,b){return a+b;} and a wrapper that calls "
    "int32PointWiseArithmetic with that function. Sub, Mul, Div follow the same pattern. "
    "Matmul.c implements matrix multiplication using its own loop (not the element-wise engine). "
    "MinMax.c finds minimum or maximum. Log.c computes natural logarithm. "
    "Square.c squares every element. Sum.c sums all elements into a scalar. "
    "Rounding.c provides the round/floor/ceil modes used by quantization. "
    "Comparison.c does element-wise greater-than, less-than, equal. "
    "Distributions.c implements softmax probability distribution. "
    "Kernel.c, SlidingWindow1d.c, AdaptiveWindow1d.c, Conv1dKernel.c, "
    "ConvTranspose1dKernel.c implement the inner loops of convolution operations.",
    S_BODY))

story.append(sp(6))
story.append(sub_header("8.2  Neural-Network Layer Files (src/layer/)"))
story.append(Paragraph(
    "Layer.h / Layer.c defines the base layer struct and forward/backward function "
    "pointer types. Each specific layer (Linear, Conv1d, Relu, Softmax, Dropout, "
    "Flatten, LayerNorm, AvgPool1d, MaxPool1d, AdaptiveAvgPool1d, QuantizationLayer) "
    "implements the forward pass (inference: compute output from input) and the backward "
    "pass (training: compute gradients with respect to weights and inputs). "
    "A Linear layer computes output = input × weight + bias using Matmul.c and Add.c. "
    "A Conv1d layer uses Conv1dKernel.c to slide a filter over the input. "
    "Relu sets negative values to zero using Comparison.c and Arithmetic.c. "
    "Softmax calls Distributions.c. QuantizationLayer calls TensorConversion.c "
    "to quantize activations between layers.",
    S_BODY))

story.append(sp(6))
story.append(sub_header("8.3  Training Infrastructure"))
story.append(Paragraph(
    "LossFunction.h / .c is the base for loss computation. CrossEntropy.h/.c implements "
    "the cross-entropy loss used for classification. MSE.h/.c implements mean-squared error. "
    "Both compute a scalar loss value and its gradient with respect to the layer output. "
    "Optimizer.h / .c is the base for weight-update rules. Sgd.h/.c implements stochastic "
    "gradient descent: for each parameter, weight -= learningRate * gradient. "
    "DataLoader.h / .c provides a dataset iterator. NPYLoader.h/.c reads NumPy .npy "
    "binary files from storage and fills tensor_t structs, enabling the model to be "
    "trained from real data files saved from Python.",
    S_BODY))

story.append(sp(6))
story.append(sub_header("8.4  Serialization (src/serial/)"))
story.append(Paragraph(
    "Serialize.h/.c writes a model's weight tensors to a binary file in flash or SD card "
    "memory. Deserialize.h/.c reads them back. These files make it possible to "
    "save a trained model once and reload it on subsequent boots without re-training.",
    S_BODY))

story.append(sp(6))
story.append(sub_header("8.5  RNG (src/rng/)"))
story.append(Paragraph(
    "RNG.h/.c provides a random-number generator. Bernoulli.h/.c generates a binary mask "
    "tensor where each entry is independently 1 with probability p and 0 with probability "
    "1-p. This mask is used by Dropout to randomly zero out activations during training.",
    S_BODY))

story.append(sp(6))
story.append(sub_header("8.6  User API (src/userApi/)"))
story.append(Paragraph(
    "The userApi folder contains one file per domain. InferenceApi.h provides functions "
    "to run a forward pass through the full model. TrainingLoopApi.h provides a "
    "train-one-epoch loop. StateDictApi.h provides load/save for named model parameters. "
    "StorageApi.h abstracts flash or file-system storage. TensorApi.h wraps tensor creation "
    "and access for the user. QuantizationApi.h wraps scale initialisation. "
    "LayerWeightsApi.h gives access to weight tensors by layer index. "
    "ModelValidationApi.h provides validation-set evaluation. "
    "Each layer has its own Api file (LinearApi, Conv1dApi, ReluApi, etc.) that "
    "lets the user configure and connect that layer without touching internal structs.",
    S_BODY))

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 – QUICK REFERENCE
# ─────────────────────────────────────────────────────────────────────────────
story.append(section_header("9.  Quick Function Reference Card", C_DARK_BLUE))
story.append(sp(8))
story.append(Paragraph(
    "The table below lists every public function covered in this document with its file "
    "and a one-line description. Use it as an index when you are looking for a specific function.",
    S_BODY))
story.append(sp(6))

ref_rows = [
    ["Function / Macro", "File", "One-line description"],
    # Common.h
    ["PRINT_DEBUG(str,...)",   "Common.h", "Print yellow debug message (DLEVEL>=3)"],
    ["PRINT_INFO(str,...)",    "Common.h", "Print info message (DLEVEL>=2)"],
    ["PRINT_ERROR(str,...)",   "Common.h", "Print red error message (DLEVEL>=1)"],
    ["PRINT_BYTE_ARRAY(p,a,n)","Common.h", "Dump byte array as hex"],
    # DTypes
    ["readBytesAsInt32",       "DTypes.h",  "4 bytes → int32_t"],
    ["readNumberOfBytesAsInt32","DTypes.h", "N bytes → int32_t (sign-extended)"],
    ["readBytesAsInt32Array",  "DTypes.h",  "Byte buffer → int32_t array"],
    ["readBytesAsFloat",       "DTypes.h",  "4 bytes → float"],
    ["readBytesAsFloatArray",  "DTypes.h",  "Byte buffer → float array"],
    ["writeInt32ToByteArray",  "DTypes.h",  "int32_t → 4 bytes"],
    ["writeInt32ArrayToByteArray","DTypes.h","int32_t array → byte buffer"],
    ["writeFloatToByteArray",  "DTypes.h",  "float → 4 bytes"],
    ["writeFloatArrayToByteArray","DTypes.h","float array → byte buffer"],
    # Quantization
    ["initSymInt32QConfig",    "Quantization.h","Fill symInt32QConfig (default 16-bit)"],
    ["initSymInt32QConfigWithQMaxBits","Quantization.h","Fill symInt32QConfig (custom bits)"],
    ["initSymQConfig",         "Quantization.h","Fill symQConfig"],
    ["initAsymQConfig",        "Quantization.h","Fill asymQConfig"],
    ["initInt32Quantization",  "Quantization.h","Set type=INT32"],
    ["initFloat32Quantization","Quantization.h","Set type=FLOAT32"],
    ["initBoolQuantization",   "Quantization.h","Set type=BOOL"],
    ["initSymInt32Quantization","Quantization.h","Set type=SYM_INT32 + link config"],
    ["initSymQuantization",    "Quantization.h","Set type=SYM + link config"],
    ["initAsymQuantization",   "Quantization.h","Set type=ASYM + link config"],
    # Tensor
    ["getBitmask",             "Tensor.h", "Build a bit mask for startbit..endbit"],
    ["writeByte",              "Tensor.h", "Write bits into a byte"],
    ["readByte",               "Tensor.h", "Extract bits from a byte"],
    ["byteConversion",         "Tensor.h", "Convert between different bit-widths"],
    ["tensorBoolGet",          "Tensor.h", "Read one bool from a BOOL tensor"],
    ["tensorBoolSet",          "Tensor.h", "Write one bool to a BOOL tensor"],
    ["getParamFromParameter",  "Tensor.h", "Get weight tensor from parameter_t"],
    ["getGradFromParameter",   "Tensor.h", "Get gradient tensor from parameter_t"],
    ["calcBytesPerElement",    "Tensor.h", "Bytes per element for a given qtype"],
    ["calcBitsPerElement",     "Tensor.h", "Bits per element for a given qtype"],
    ["calcBytesPerTensor",     "Tensor.h", "Total bytes in tensor data buffer"],
    ["calcNumberOfBytesForData","Tensor.h","Bytes needed for N elements of given type"],
    ["calcNumberOfElementsByShape","Tensor.h","Product of all dimension sizes"],
    ["calcNumberOfElementsByTensor","Tensor.h","Elements in a tensor"],
    ["calcNumberOfElementsByParameter","Tensor.h","Elements in parameter's weight"],
    ["transposeTensor",        "Tensor.h", "Swap two axes (zero-cost metadata change)"],
    ["setTensorValues",        "Tensor.h", "Fill all four tensor_t fields at once"],
    ["setTensorValuesForConversion","Tensor.h","Set data+quant, copy shape from other"],
    ["setParameterValues",     "Tensor.h", "Fill a parameter_t"],
    ["setOrderOfDimsForNewTensor","Tensor.h","Init orderOfDimensions to identity"],
    ["setShape",               "Tensor.h", "Fill a shape_t"],
    ["printTensor",            "Tensor.h", "Debug-print tensor to stdout"],
    ["printShape",             "Tensor.h", "Debug-print shape to stdout"],
    ["copyTensor",             "Tensor.h", "Shallow copy of tensor_t fields"],
    # TensorConversion
    ["convertTensor",          "TensorConversion.h","Dispatch conversion via matrix"],
    ["requantSymInt32Tensor",  "TensorConversion.h","SYM_INT32 → SYM_INT32 dynamic scale"],
    ["requantSymInt32TensorToScale","TensorConversion.h","SYM_INT32 → SYM_INT32 fixed scale"],
    ["quantTypeToString",      "TensorConversion.h","qtype_t → readable string"],
    ["conversionMatrix[6][6]", "TensorConversion.h","Dispatch table of converters"],
    # Arithmetic
    ["getDimensionsByIndex",   "Arithmetic.h","Logical dimension size for an axis"],
    ["orderDims",              "Arithmetic.h","Fill array with logical dim sizes"],
    ["doDimensionsMatch",      "Arithmetic.h","Check two tensors have same shape"],
    ["calcTensorIndexByIndices","Arithmetic.h","Multi-dim indices → flat index"],
    ["calcIndicesByRawIndex",  "Arithmetic.h","Flat index → multi-dim indices"],
    ["calcElementIndexByIndices","Arithmetic.h","Transpose-aware flat index"],
    ["int32PointWiseArithmetic","Arithmetic.h","Element-wise int32 A op B → output"],
    ["int32PointWiseArithmeticInplace","Arithmetic.h","Element-wise int32 A op B → A"],
    ["floatPointWiseArithmetic","Arithmetic.h","Element-wise float A op B → output"],
    ["floatPointWiseArithmeticInplace","Arithmetic.h","Element-wise float A op B → A"],
    ["int32ElementWithTensorArithmetic","Arithmetic.h","int32 scalar op every element → out"],
    ["int32ElementWithTensorArithmeticInplace","Arithmetic.h","int32 scalar op tensor → tensor"],
    ["floatElementWithTensorArithmetic","Arithmetic.h","float scalar op every element → out"],
    ["floatElementWithTensorArithmeticInplace","Arithmetic.h","float scalar op tensor → tensor"],
]

ref_data = []
for row in ref_rows:
    if row == ref_rows[0]:  # header
        ref_data.append([Paragraph(f"<b>{xe(c)}</b>", S_CODE) for c in row])
    else:
        ref_data.append([Paragraph(xe(c), S_NOTE) for c in row])

ref_table = Table(ref_data, colWidths=[65*mm, 42*mm, 63*mm])
ref_table.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), C_DARK_BLUE),
    ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_LIGHT_GREY]),
    ("BOX",           (0,0), (-1,-1), 0.5, C_CODE_BORDER),
    ("INNERGRID",     (0,0), (-1,-1), 0.3, C_CODE_BORDER),
    ("TOPPADDING",    (0,0), (-1,-1), 3),
    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ("LEFTPADDING",   (0,0), (-1,-1), 4),
    ("RIGHTPADDING",  (0,0), (-1,-1), 4),
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
]))
story.append(ref_table)

# ── Build PDF ────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=18*mm,  bottomMargin=18*mm,
    title="On-Device Training Library — Master Code Overview",
    author="Auto-generated",
)

doc.build(story)
print(f"PDF written to: {OUTPUT}")
