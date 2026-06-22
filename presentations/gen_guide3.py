"""
Code Reading Guide 3 — files 20-24
OnDeviceTraining framework: Data Pipeline, Backpropagation, Training Loop, Inference
Same expanded line-by-line style as guide 2 expanded.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUT = "code_reading_guide_3.pdf"

# ── palette ─────────────────────────────────────────────────────────────────
C_HDR   = colors.HexColor("#1a3a5c")
C_PH    = colors.HexColor("#0063b1")
C_ACC   = colors.HexColor("#ddeeff")
C_TIP   = colors.HexColor("#d4edda")
C_TIPB  = colors.HexColor("#1e7e34")
C_WARN  = colors.HexColor("#fff3cd")
C_WARNB = colors.HexColor("#856404")
C_GREY  = colors.HexColor("#555555")
C_WHITE = colors.white
C_BLK   = colors.HexColor("#1a1a1a")
W, H = A4
BW = W - 4*cm

styles = getSampleStyleSheet()

def PS(name, parent="Normal", **kw):
    return ParagraphStyle(name+str(id(kw)), parent=styles[parent], **kw)

BODY = PS("b", fontSize=9.5, leading=15, textColor=C_BLK, alignment=TA_JUSTIFY, spaceAfter=5)
CODE = PS("c", fontName="Courier", fontSize=8, leading=12.5, textColor=C_BLK)
ANNO = PS("a", fontSize=9,   leading=14, textColor=C_BLK, alignment=TA_JUSTIFY)
GREY = PS("g", fontSize=8.5, leading=13, textColor=C_GREY)

story = []

def S(n=5):  story.append(Spacer(1, n))
def HR():    story.append(HRFlowable(width="100%", thickness=0.4, color=colors.lightgrey, spaceAfter=3))
def PB():    story.append(PageBreak())

def H1(text):
    story.append(Paragraph(text, PS("H1", fontSize=14, textColor=C_WHITE,
        backColor=C_HDR, borderPadding=(7,10,7,10), spaceAfter=5, spaceBefore=14)))

def H2(text):
    story.append(Paragraph(text, PS("H2", fontSize=11, textColor=C_HDR,
        fontName="Helvetica-Bold", spaceBefore=9, spaceAfter=3)))

def H3(text):
    story.append(Paragraph(text, PS("H3", fontSize=9.5, textColor=C_HDR,
        fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2)))

def BD(text):   story.append(Paragraph(text, BODY))
def NT(text):   story.append(Paragraph(text, GREY))

def tip(text, label="NOTE", bg=C_TIP, bc=C_TIPB):
    p = Paragraph(f"<b>{label}:</b>  {text}", PS("ti", fontSize=8.5, leading=13))
    t = Table([[p]], colWidths=[BW])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),("BOX",(0,0),(-1,-1),1,bc),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t); S(4)

def warn(text): tip(text, "WARNING", C_WARN, colors.HexColor("#f0ad4e"))

def code_line_table(rows):
    """rows = list of (code_text, annotation_text)"""
    data = []
    for code, ann in rows:
        cp = Paragraph(code, CODE)
        ap = Paragraph(ann,  ANNO)
        data.append([cp, ap])
    t = Table(data, colWidths=[BW*0.40, BW*0.60])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1), C_ACC),
        ("BACKGROUND",(1,0),(1,-1), colors.HexColor("#f8fbff")),
        ("BOX",(0,0),(-1,-1),0.5,colors.grey),
        ("INNERGRID",(0,0),(-1,-1),0.25,colors.lightgrey),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t); S(4)

def plain_code(lines, bg=C_ACC):
    p = Paragraph("<br/>".join(lines), CODE)
    t = Table([[p]], colWidths=[BW])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("BOX",(0,0),(-1,-1),0.5,colors.grey),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(t); S(4)

# ═══════════════════════════════════════════════════════════════════════════
# COVER
# ═══════════════════════════════════════════════════════════════════════════
S(1.5*cm)
story.append(Paragraph("OnDeviceTraining",
    PS("tl","Title", fontSize=22, textColor=C_HDR, alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph("Code Reading Guide 3",
    PS("t2","Title", fontSize=18, textColor=C_PH,  alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph(
    "Line-by-Line Syntax &amp; Explanation — Beginner Edition<br/>"
    "Files 20–24: Data Pipeline · Backpropagation · Training Loop · Inference",
    PS("t3","Normal", fontSize=10, textColor=C_GREY, alignment=TA_CENTER, spaceAfter=14)))
HR(); S(4)
story.append(Paragraph(
    "Mohamed · Master's Thesis · 2026",
    PS("au","Normal", fontSize=9, textColor=C_GREY, alignment=TA_CENTER, spaceAfter=14)))
S(4)
BD("This guide continues from Guide 2 (which covered files 1–19, Phases 1–8). "
   "Guide 3 covers the five file groups that complete the usable training framework: "
   "the data pipeline that feeds samples into the model (Dataset, DataLoader, NPYLoader), "
   "the backpropagation engine that computes gradients "
   "(CalculateGradsSequential), the training-loop orchestration "
   "(TrainingBatchDefault, TrainingEpochDefault, TrainingLoopApi), "
   "and the inference engine (InferenceApi). "
   "Every line of C code is shown with a syntax label on the left and "
   "a plain-English explanation on the right. "
   "Read Guide 1 first for the phase overview; use this guide to understand "
   "the code itself.")
S(8)

story.append(Paragraph("Contents", PS("co","Heading2", fontSize=11, textColor=C_HDR,
    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)))
toc = [
    ("Phase 9", "Data Pipeline",          "20 · Dataset.h  21 · DataLoader.h / DataLoader.c  21 · NPYLoader.h / NPYLoader.c"),
    ("Phase 10","Backpropagation Engine", "22 · TrainingLoopApi.h  22 · CalculateGradsSequential.h / .c"),
    ("Phase 11","Training Orchestration", "23 · TrainingBatchDefault  23 · TrainingEpochDefault"),
    ("Phase 12","Inference Engine",       "24 · InferenceApi.h / InferenceApi.c"),
    ("—",       "Syntax Quick Reference", "Last page"),
]
toc_data = [["Phase","Topic","Files"]] + [[p,t,f] for p,t,f in toc]
th = PS("th2", fontName="Helvetica-Bold", fontSize=8.5, textColor=C_WHITE)
td = PS("td2", fontSize=8.5, leading=13)
trows = []
for i,r in enumerate(toc_data):
    if i==0:
        trows.append([Paragraph(c,th) for c in r])
    else:
        trows.append([Paragraph(c,td) for c in r])
tt = Table(trows, colWidths=[BW*0.13, BW*0.26, BW*0.61])
tt.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0),C_HDR),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE, C_ACC]),
    ("BOX",(0,0),(-1,-1),0.5,colors.grey),
    ("INNERGRID",(0,0),(-1,-1),0.3,colors.lightgrey),
    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ("LEFTPADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP"),
]))
story.append(tt); S(6)
PB()

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 9 — Data Pipeline
# ═══════════════════════════════════════════════════════════════════════════
H1("Phase 9 — Data Pipeline")
story.append(Paragraph(
    "Dataset.h  ·  DataLoader.h / DataLoader.c  ·  NPYLoader.h / NPYLoader.c",
    PS("ph",fontSize=10,textColor=C_HDR,fontName="Helvetica-Bold",spaceAfter=5)))
S(2)
BD("The data pipeline is the bridge between your .npy files on disk and the "
   "tensors the training loop consumes. It works in three layers: "
   "<b>Dataset.h</b> defines the raw data structures (sample, batch, dataset), "
   "<b>DataLoader.h / DataLoader.c</b> adds shuffling and batching logic, and "
   "<b>NPYLoader.h / NPYLoader.c</b> actually reads the binary .npy file format "
   "from disk. By the time a tensor reaches the training loop, it has been "
   "loaded from disk, parsed, shuffled (if requested), and grouped into a batch "
   "of the configured size.")
S(6)

# ── File 20: Dataset.h ───────────────────────────────────────────────────
H2("20 · Dataset.h")
NT("src/data_loader/include/Dataset.h")
S(3)
BD("Dataset.h is a pure struct-definition header — it contains no functions. "
   "It defines four struct types that form the building blocks of the entire "
   "data pipeline. Every object that passes between the data loader and the "
   "training loop is one of these four types.")
S(4)

code_line_table([
    ("#ifndef DATASET_H",
     "Include guard — top. Prevents the compiler from reading this header twice. "
     "If DATASET_H is not yet defined, continue; if it is, skip to #endif."),

    ("#define DATASET_H",
     "Define the guard symbol. After this line, any second #include of Dataset.h "
     "will be skipped entirely."),

    ('#include "Tensor.h"',
     "Pull in the tensor_t struct. Every sample and every label is stored in a "
     "tensor_t, so the definition of tensor_t must be known before the structs below."),

    ("typedef enum { FLOAT_32, INT_32 } dtype_t;",
     "Data-type enumeration. dtype_t has two possible values: FLOAT_32 (single-"
     "precision floating point, 4 bytes per element) and INT_32 (32-bit signed "
     "integer). NPYLoader uses this to record what numeric format the .npy file "
     "contains. typedef gives the anonymous enum the alias dtype_t so you can "
     "write dtype_t x instead of enum {...} x everywhere."),

    ("typedef struct sample {",
     "Begin the sample struct. A sample is one training example — one pair of "
     "(input, expected-output). typedef + struct together mean you can write "
     "sample_t instead of struct sample everywhere."),

    ("    tensor_t *item;",
     "Pointer to the input tensor. For HAR, this is one 9-channel 128-timestep "
     "window of sensor readings, stored as a float32 tensor of shape [9, 128]. "
     "An asterisk (*) means pointer — item holds the address where the actual "
     "tensor data lives, not a copy."),

    ("    tensor_t *label;",
     "Pointer to the label tensor. For classification, this is the one-hot "
     "encoded class vector (e.g. [0,0,1,0,0,0] for class 2 — WALKING_DOWNSTAIRS). "
     "Labels are also tensor_t objects, allowing them to carry quantization and "
     "shape information alongside the raw values."),

    ("} sample_t;",
     "Close and name the struct. The semicolon is required after every struct "
     "definition in C."),

    ("typedef struct batch {",
     "Begin the batch struct. A batch groups batchSize many samples together "
     "so the model can process them in parallel (vectorised computation, "
     "gradient averaging over the batch)."),

    ("    sample_t **samples;",
     "Array of pointers to sample_t objects. Double pointer (**): samples is "
     "a pointer to the first element of an array, and each element is itself a "
     "pointer to a sample_t. This avoids copying the sample data — only "
     "addresses are stored in the array."),

    ("    size_t size;",
     "The number of samples in this batch. size_t is an unsigned integer type "
     "guaranteed to be large enough to hold any object size on the platform "
     "(32-bit on ARM Cortex-M, 64-bit on x86-64). Used as the loop bound when "
     "iterating over samples."),

    ("} batch_t;",
     "Close the batch struct and give it the alias batch_t."),

    ("typedef struct tensorArray {",
     "Begin the tensorArray struct. tensorArray is a helper that bundles an "
     "array of tensor_t pointers with its length. Used by dataset_t below to "
     "store all items and all labels as two separate collections."),

    ("    tensor_t **array;",
     "Pointer to the first element of an array of tensor_t pointers. "
     "The actual tensors live elsewhere in memory; this array holds their addresses."),

    ("    size_t size;",
     "Number of tensors in the array — i.e. the total number of samples in "
     "the split (train, validation, or test)."),

    ("} tensorArray_t;",
     "Close tensorArray and name it tensorArray_t."),

    ("typedef struct dataset {",
     "Begin the top-level dataset struct. A dataset_t pairs all input tensors "
     "with all label tensors for one split (e.g. the training set)."),

    ("    tensorArray_t *items;",
     "Pointer to the collection of input tensors. For HAR: 7352 float32 tensors "
     "of shape [9, 128] for the training split."),

    ("    tensorArray_t *labels;",
     "Pointer to the collection of label tensors. Parallel to items: labels->array[i] "
     "is the ground-truth class for items->array[i]."),

    ("} dataset_t;",
     "Close the dataset struct. This struct is the complete in-memory "
     "representation of one data split."),

    ("#endif // DATASET_H",
     "End of the include guard. Every #ifndef must have a matching #endif."),
])
PB()

# ── File 21a: DataLoader.h ───────────────────────────────────────────────
H2("21 · DataLoader.h / DataLoader.c")
NT("src/data_loader/include/DataLoader.h + src/data_loader/DataLoader.c")
S(3)
BD("DataLoader sits on top of Dataset. Its job is to expose a clean interface "
   "for the training loop — the training loop only calls "
   "<font face='Courier'>getBatch(loader, i)</font> and never touches the raw "
   "arrays directly. DataLoader also handles optional shuffling (so every epoch "
   "sees the data in a different order) and the dropLast policy (silently discard "
   "the final partial batch if the dataset size is not divisible by batchSize).")
S(4)

H3("Header — DataLoader.h")
S(2)
code_line_table([
    ('#include <stdbool.h>',
     "Pull in the bool type. C99 introduced bool (true/false) via this header. "
     "It is used for the shuffle and dropLast flags."),

    ('typedef struct dataLoader dataLoader_t;',
     "Forward declaration. This line declares that a struct named dataLoader "
     "exists and gives it the alias dataLoader_t, without yet showing its fields. "
     "This is needed so function pointer typedefs below can refer to dataLoader_t* "
     "before the full struct definition appears."),

    ("typedef tensor_t *(*transformFn_t)(tensor_t *tensor);",
     "Function pointer type for a transform. A transformFn_t variable holds "
     "the address of any function that takes a tensor_t* and returns a tensor_t*. "
     "The parentheses around *transformFn_t are required to distinguish a "
     "function pointer from a function returning a pointer. Transforms are "
     "optional per-sample preprocessing steps (e.g. normalisation)."),

    ("typedef sample_t *(*getSampleFn_t)(size_t id);",
     "Function pointer type that returns one sample by index. The training "
     "code calls loader->getSample(i) and gets back a fully constructed sample_t."),

    ("typedef size_t (*getDatasetSizeFn_t)();",
     "Function pointer type for a zero-argument function that returns the total "
     "number of samples. Called once during initDataLoader to allocate the index array."),

    ("typedef batch_t *(*getBatchFn_t)(dataLoader_t *dataLoader, size_t index);",
     "Function pointer type for fetching one batch. index is the batch number "
     "(0, 1, 2 ...). The implementation calls getSample for each slot in the batch, "
     "respecting the shuffled index array."),

    ("struct dataLoader {",
     "Full struct definition (now that the typedef above already named it "
     "dataLoader_t). Each field below stores one piece of the loader's configuration."),

    ("    getSampleFn_t getSample;",
     "Stored pointer to the user-supplied getSample function. Called by getBatch."),

    ("    getDatasetSizeFn_t getDatasetSize;",
     "Stored pointer to the size function. Called during init and by the training "
     "loop to compute numberOfBatches = datasetSize / batchSize."),

    ("    uint16_t batchSize;",
     "Number of samples per batch, stored as a 16-bit unsigned integer. "
     "uint16_t fits values up to 65535 — more than enough for any realistic batch size."),

    ("    getBatchFn_t getBatch;",
     "Stored pointer to the getBatch function. The training loop calls this."),

    ("    transformFn_t transform;",
     "Optional preprocessing applied once after loading (e.g. feature scaling). "
     "NULL if not needed."),

    ("    transformFn_t targetTransform;",
     "Optional transform applied to each label after getBatch. "
     "NULL if not needed."),

    ("    bool shuffle;",
     "If true, the index array is shuffled (random permutation) at init time so "
     "each epoch presents samples in a different order."),

    ("    uint64_t shuffleSeed;",
     "64-bit seed for the shuffle RNG. Using the same seed across runs makes "
     "the data order reproducible (important for comparing experiments)."),

    ("    size_t *indices;",
     "Pointer to an array of getDatasetSize() integers. indices[0..N-1] "
     "initially holds {0,1,2,...,N-1}. After shuffling, the order is randomised. "
     "getBatch uses indices[batchIndex*batchSize + j] instead of a plain integer j "
     "to look up the j-th sample in the batch."),

    ("    bool dropLast;",
     "If true (currently the only supported mode), discard the final batch when "
     "datasetSize % batchSize != 0. This ensures every batch has exactly batchSize "
     "samples, simplifying gradient accumulation arithmetic."),
])

S(4)
H3("Implementation — DataLoader.c")
S(2)
code_line_table([
    ('#define SOURCE_FILE "DATA_LOADER"',
     "Label this .c file as DATA_LOADER for the PRINT_ERROR macro. "
     "When an error is printed, the shell output will show [DATA_LOADER] as the "
     "source location."),

    ('#include <stdint.h>',
     "Fixed-width integer types (uint16_t, size_t, uint64_t)."),

    ('#include <stdlib.h>',
     "Standard library: exit() for fatal errors."),

    ('#include "Common.h"',
     "PRINT_ERROR macro and debug utilities."),

    ('#include "DataLoader.h"',
     "Own header — brings in the dataLoader_t struct definition and function signatures."),

    ('#include "RNG.h"',
     "Random number generator. rngSetSeed() and rngShuffleIndices() are called "
     "below to shuffle the index array."),

    ("void initDataLoader(dataLoader_t *dataLoader, ...)",
     "The only public function. Takes a pointer to an already-allocated "
     "dataLoader_t and fills every field. The caller owns the struct (stack or heap)."),

    ("    if (dropLast == false) {",
     "Validation check. dropLast == false (i.e. keep partial batches) is not "
     "yet implemented. Calling with dropLast=false immediately exits with an error "
     "rather than silently producing wrong batch sizes."),

    ("        PRINT_ERROR(...); exit(1);",
     "Print an error message and terminate. exit(1) signals abnormal termination "
     "to the operating system. On the Pico, exit() triggers a hard fault handler."),

    ("    dataLoader->getSample = getSample;",
     "Store the function pointer. The arrow operator (->) dereferences the pointer "
     "dataLoader and accesses its getSample field. This is equivalent to "
     "(*dataLoader).getSample = getSample."),

    ("    for (size_t i = 0; i < sizeDataset; ++i) { indices[i] = i; }",
     "Fill the index array with the identity permutation {0,1,...,N-1}. "
     "++i (pre-increment) and i++ (post-increment) are equivalent here; "
     "++i is a minor style preference to avoid creating an unused temporary."),

    ("    if (shuffle) { rngSetSeed(shuffleSeed); rngShuffleIndices(indices, sizeDataset); }",
     "Conditionally shuffle. rngSetSeed() initialises the xorshift64 generator "
     "with shuffleSeed, making the permutation deterministic and reproducible. "
     "rngShuffleIndices() performs an in-place Fisher-Yates shuffle: it swaps "
     "each element with a randomly chosen element to its right."),
])
PB()

# ── File 21b: NPYLoader.h / NPYLoader.c ─────────────────────────────────
H2("21 (continued) · NPYLoader.h / NPYLoader.c")
NT("src/data_loader/include/NPYLoader.h + src/data_loader/NPYLoader.c")
S(3)
BD("NPYLoader parses the NumPy binary array format (.npy). A .npy file stores "
   "one multi-dimensional array as: a 6-byte magic signature, a 1-byte major "
   "version, a 1-byte minor version, a 2-byte (v1) or 4-byte (v2) header length, "
   "then a Python-dict-like ASCII header containing the dtype, C/F order, and shape, "
   "followed immediately by the raw binary data. NPYLoader reads each field in order "
   "and reconstructs the shape metadata and dtype for use by the tensor system.")
S(4)

H3("Header — NPYLoader.h (function declarations)")
S(2)
BD("NPYLoader.h declares six functions, each responsible for one parsing step:")
plain_code([
    "FILE *openNPYFile(char *path)          — open file, check it exists",
    "void  checkMagic(FILE *f)              — verify the 6-byte signature",
    "uint32_t readHeaderSize(FILE *f)       — read version + header length",
    "void  readHeader(char *header, ...)    — read the ASCII header string",
    "dtype_t getDTypeFromHeader(char *h)    — extract data type (float32/int32)",
    "size_t getNumberOfDimsFromHeader(...)  — count dimensions",
    "void getShapeFromHeader(...)           — fill the shape_t struct",
])
S(4)

H3("Implementation — NPYLoader.c")
S(2)
code_line_table([
    ('FILE *openNPYFile(char *path) {',
     "Open a file in binary read mode. Returns a FILE* — a C standard library "
     "file handle. If fopen returns NULL (file does not exist, no permission, etc.), "
     "PRINT_ERROR + exit(1) terminates the program."),

    ('    FILE *f = fopen(path, "rb");',
     'fopen — standard C function to open a file. "rb" = read binary: the file '
     "is opened for reading and no newline translation is performed (essential "
     "for binary formats where a newline byte 0x0A must be read as-is)."),

    ("void checkMagic(FILE *f) {",
     "Validate the .npy signature. If this check fails the file is not a valid "
     ".npy file and the program exits immediately to avoid reading garbage data."),

    ('    char magic[7] = {0};',
     "Declare a 7-byte char array, zero-initialised with {0}. The .npy magic is "
     "6 bytes (0x93, 'N','U','M','P','Y'); the 7th byte is reserved for a null "
     "terminator so strcmp works correctly."),

    ('    fread(magic, 1, 6, f);',
     "Read 6 bytes from f into magic. fread arguments: buffer, element size, "
     "element count, file pointer. Returns the number of elements successfully read."),

    ('    if (strcmp(magic, "\\x93NUMPY") != 0) {',
     "Compare the 6 bytes to the required magic. \\x93 is hexadecimal 0x93 = 147. "
     "strcmp returns 0 if the strings are identical; != 0 means mismatch."),

    ("uint32_t readHeaderSize(FILE *f) {",
     "Read the format version and header length. Returns the header length as "
     "a 32-bit unsigned integer regardless of whether the file is version 1 or 2."),

    ("    uint8_t major, minor;",
     "Declare two 8-bit variables for the major and minor version numbers. "
     "uint8_t is an unsigned byte (0–255). NumPy version 1.0 files are most common; "
     "version 2.0 files use a 4-byte header length instead of 2."),

    ("    fread(&major, 1, 1, f); fread(&minor, 1, 1, f);",
     "Read one byte each. The & address-of operator passes the address of major/minor "
     "so fread knows where to store the byte it reads."),

    ("    if (major == 1) { uint16_t hl16; fread(&hl16, 2, 1, f); header_len = hl16; }",
     "Version 1: header length is a 2-byte little-endian unsigned integer. "
     "Read into uint16_t hl16 (2 bytes), then widen to uint32_t."),

    ("    else { fread(&header_len, 4, 1, f); }",
     "Version 2: header length is a 4-byte little-endian unsigned integer. "
     "Read directly into the uint32_t return value."),

    ("dtype_t getDTypeFromHeader(char *header) {",
     "Extract the element data type from the ASCII header. The header is a "
     "Python dict literal like: {'descr': '&lt;f4', 'fortran_order': False, 'shape': (7352, 9, 128)}."),

    ('    char descr[8]; sscanf(strstr(header,"\'descr\'"),"\'descr\': \'%7[^\']\'",descr);',
     "Parse the descr field. strstr finds the substring 'descr' inside header. "
     "sscanf with format '%7[^']' reads up to 7 characters until a single-quote, "
     "extracting the type string (e.g. '&lt;f4')."),

    ('    if (strcmp(s, "&lt;f4") == 0) return FLOAT_32;',
     "'&lt;f4' means little-endian float32. &lt; = little-endian, f = float, 4 = 4 bytes. "
     "FLOAT_32 is the FLOAT_32 member of dtype_t."),

    ('    if (strcmp(s, "&lt;i4") == 0) return INT_32;',
     "'&lt;i4' means little-endian int32. i = signed integer, 4 = 4 bytes."),

    ("size_t getNumberOfDimsFromHeader(char *header) {",
     "Count how many dimensions the array has. Walks the shape tuple in the header "
     "(e.g. '(7352, 9, 128)') and counts how many numbers appear between '(' and ')'."),

    ("    char *p = strstr(header, \"shape\"); p = strchr(p, '(') + 1;",
     "Find 'shape' in the header, then advance to the character after '('. "
     "strchr finds the first '(' from that position; +1 skips the bracket itself."),

    ("    while (*p != ')') { ... if (*p >= '0' && *p <= '9') numberOfDims++; ... }",
     "Walk character by character until ')'. When we see a digit, we have found "
     "the start of another dimension integer — increment the counter and skip "
     "all digit characters. Skip commas and spaces between numbers."),

    ("void getShapeFromHeader(shape_t *shape, ...) {",
     "Fill the shape_t struct with dimension sizes. Called after getNumberOfDimsFromHeader "
     "has told us how many dimensions to expect. Allocates nothing — the caller "
     "passes pre-allocated dims and orderOfDims arrays."),

    ("    char *end; size_t value = strtoull(p, &end, 10);",
     "Parse one integer from the string. strtoull converts the decimal string at p "
     "to a 64-bit unsigned integer. end is set to point to the first character after "
     "the number, ready for the next iteration."),

    ("    shape->dimensions[i] = value; shape->orderOfDimensions[i] = i;",
     "Store the dimension size and its canonical order index. orderOfDimensions[i] = i "
     "means the dimensions are in row-major (C) order — the default for NumPy arrays."),
])
PB()

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 10 — Backpropagation Engine
# ═══════════════════════════════════════════════════════════════════════════
H1("Phase 10 — Backpropagation Engine")
story.append(Paragraph(
    "TrainingLoopApi.h  ·  CalculateGradsSequential.h / CalculateGradsSequential.c",
    PS("ph",fontSize=10,textColor=C_HDR,fontName="Helvetica-Bold",spaceAfter=5)))
S(2)
BD("Backpropagation is the algorithm that computes gradients — the direction and "
   "magnitude in which each weight should change to reduce the loss. "
   "CalculateGradsSequential implements the full forward-then-backward pass for "
   "a sequential (layer-by-layer) model. It is the most complex file in the framework: "
   "it allocates intermediate tensors for every layer's output, runs the forward pass, "
   "computes the loss, then walks backwards through the layers calling each layer's "
   "backward function to propagate gradients all the way to the first layer.")
S(6)

H2("22 · TrainingLoopApi.h")
NT("src/userApi/training_loop/include/TrainingLoopApi.h")
S(3)
BD("TrainingLoopApi.h is the central header for the training loop. It defines all "
   "struct types (trainingStats_t, epochStats_t, classificationReport_t) and "
   "function pointer typedefs (calculateGradsFn_t, inferenceWithLossFn_t) that "
   "tie the backpropagation, inference, and orchestration layers together.")
S(4)

code_line_table([
    ("typedef struct trainingStats { tensor_t *output; float loss; } trainingStats_t;",
     "Result of one forward+backward pass on a single sample. "
     "output holds the model's prediction tensor (class probabilities after Softmax). "
     "loss is the scalar loss value for this sample (e.g. cross-entropy)."),

    ("typedef struct epochStats { float loss; float accuracy; float precision; "
     "float recall; float f1; } epochStats_t;",
     "Aggregate metrics over a full evaluation epoch. "
     "loss: mean cross-entropy. accuracy: fraction of correct predictions. "
     "precision, recall, f1: macro-averaged (mean over all classes) — "
     "the same metric set reported in the Evci et al. RigL paper."),

    ("typedef struct classificationReport { epochStats_t stats; size_t *confusionMatrix; "
     "size_t numClasses; } classificationReport_t;",
     "Full evaluation result including the confusion matrix. "
     "confusionMatrix is a flat array of size numClasses*numClasses: "
     "cm[predicted*numClasses + actual] counts how many times class actual was "
     "predicted as class predicted. Caller owns and pre-allocates this buffer."),

    ("typedef trainingStats_t *(*calculateGradsFn_t)(...);",
     "Function pointer type for any backpropagation implementation. "
     "The training loop is decoupled from the specific backprop strategy — "
     "it only knows this type. Passing calculateGradsSequential fills this slot. "
     "Custom implementations (e.g. with RigL hooks) can replace it."),

    ("classificationReport_t evaluationEpochWithReport(...);",
     "Public function that runs the full evaluation epoch and returns a "
     "classificationReport_t. Used in main.c after each training epoch and "
     "for the final test evaluation. Internally calls inferenceWithLoss for "
     "each sample, accumulates the confusion matrix, then computes all metrics."),

    ("trainingRunResult_t trainingRun(...);",
     "High-level convenience function that runs the complete training loop "
     "(all epochs). Not used in the RigL project because RigL needs per-batch "
     "hooks (mask application, prune-regrow) that trainingRun does not expose. "
     "Instead the project calls trainingBatchDefault directly."),
])
S(6)

H2("22 (continued) · CalculateGradsSequential.h / CalculateGradsSequential.c")
NT("src/userApi/training_loop/calculate_grads/ CalculateGradsSequential.h + .c")
S(3)
BD("CalculateGradsSequential is the core engine. It performs a full "
   "forward pass (layers 0 → N-1), computes the loss, then runs the "
   "backward pass (layers N-1 → 0). Every intermediate activation tensor "
   "is allocated on the heap before the forward pass and freed after the backward "
   "pass to keep memory usage bounded.")
S(4)

code_line_table([
    ("trainingStats_t *calculateGradsSequential(layer_t **model, size_t modelSize, ...)",
     "Main entry point. Takes the model array, its size, a loss configuration "
     "(which loss function, which reduction), one input tensor, and one label tensor. "
     "Returns a heap-allocated trainingStats_t containing the prediction and loss."),

    ("    tensor_t *layerOutputs[modelSize + 1];",
     "Variable-length array (VLA) of tensor pointers — one per layer plus the "
     "input. layerOutputs[0] = input (the raw sensor data). After the forward pass, "
     "layerOutputs[i] holds the output activation of layer i-1. "
     "VLAs are allocated on the call stack, so the array of pointers is stack memory; "
     "the actual tensor data they point to is heap memory (via reserveMemory)."),

    ("    layerOutputs[0] = input;",
     "The first 'activation' is simply the input tensor — no layer has processed "
     "it yet. The forward loop starts with this as its input."),

    ("    setDropoutLayersTraining(model, modelSize, true);",
     "Enable dropout for training. Dropout randomly zeroes some activations "
     "during training to reduce overfitting, but must be disabled during evaluation "
     "so every neuron contributes deterministically. This function sets a training "
     "flag in each DROPOUT layer config."),

    ("    initLayerOutputs(layerOutputs, model, modelSize);",
     "Allocate output tensors for every layer. This calls calcOutputShape for "
     "each layer to determine the output dimensions, then reserveMemory to "
     "allocate the data buffer and associated shape/quantization structs."),

    ("    for (size_t i = 0; i < modelSize; i++) { ... forward(...); }",
     "Forward pass loop. For each layer i, looks up its forward function in the "
     "layerFunctions vtable (layerFunctions[type].forward), then calls it with "
     "layerOutputs[i] as input and layerOutputs[i+1] as the output buffer."),

    ("    float loss = lossFns.forward(layerOutputs[modelSize], label, forwardReduction);",
     "Compute the scalar loss. lossFns is a row of the lossFunctions dispatch table "
     "selected by lossConfig.funcType (e.g. CROSS_ENTROPY). The forward function "
     "computes cross-entropy between the model's class-probability output and the "
     "one-hot label vector."),

    ("    if (lossConfig.funcType == CROSS_ENTROPY) { backwardIndex -= 1; }",
     "Special case for cross-entropy + softmax. The cross-entropy backward pass "
     "is fused with the Softmax backward pass (their combined gradient simplifies "
     "to prediction - label). Skipping the Softmax backward layer avoids computing "
     "the Jacobian of Softmax twice."),

    ("    tensor_t gradNext; initGradTensor(&gradNext, layerOutputs[modelSize]);",
     "Allocate the initial gradient tensor. At the start of backpropagation "
     "(the output end), gradNext holds dLoss/dOutput — how the loss changes "
     "with each element of the final layer's output. Its shape matches the output."),

    ("    lossFns.backward(layerOutputs[modelSize], label, &gradNext);",
     "Compute the loss gradient with respect to the model output. For cross-entropy, "
     "this is (softmax_output - one_hot_label) — a simple element-wise subtraction."),

    ("    for (int i = (int)backwardIndex; i >= 0; i--) { ... backward(...); }",
     "Backward pass loop — runs in reverse order. For each layer i, calls its "
     "backward function which: (a) accumulates gradients into the layer's weight "
     "gradient tensors (used by the optimizer), and (b) computes gradCurr — "
     "the gradient to pass further back."),

    ("    backward(model[i], layerOutputs[i], &gradNext, &gradCurr);",
     "Each layer's backward function signature: layer config (holds weight tensors), "
     "the layer's saved input (needed to compute weight gradients), the gradient "
     "coming from the next layer (gradNext), and a buffer for the gradient to pass "
     "to the previous layer (gradCurr). After the call, gradCurr becomes gradNext "
     "for the next iteration."),

    ("    deInitGradTensor(&gradNext); gradNext = gradCurr;",
     "Free the previous gradNext and advance: gradNext = gradCurr. "
     "This is the 'shift' step — each iteration processes one layer and passes "
     "its gradient one step further back."),

    ("    deInitLayerOutputs(layerOutputs, modelSize);",
     "Free all intermediate activation tensors allocated during initLayerOutputs. "
     "They were only needed for the backward pass (to compute weight gradients); "
     "once backprop is done, they can be released."),
])
PB()

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 11 — Training Orchestration
# ═══════════════════════════════════════════════════════════════════════════
H1("Phase 11 — Training Orchestration")
story.append(Paragraph(
    "TrainingBatchDefault.h / .c  ·  TrainingEpochDefault.h / .c",
    PS("ph",fontSize=10,textColor=C_HDR,fontName="Helvetica-Bold",spaceAfter=5)))
S(2)
BD("The orchestration layer calls CalculateGradsSequential in the right order "
   "and feeds gradients to the optimizer. It is split into two levels: "
   "<b>TrainingBatchDefault</b> processes one batch (iterates over the batch's "
   "samples, accumulates loss), and <b>TrainingEpochDefault</b> processes one "
   "full epoch (iterates over all batches, steps the optimizer after each).")
S(6)

H2("23 · TrainingBatchDefault.h / TrainingBatchDefault.c")
NT("src/userApi/training_loop/training_batch/TrainingBatchDefault.h + .c")
S(3)
BD("TrainingBatchDefault is intentionally minimal — its only job is to iterate "
   "over the samples in a batch, call the gradient-computation function for each, "
   "accumulate the total loss, and return the mean. The optimizer step is NOT "
   "called here; it happens in TrainingEpochDefault after the batch is complete.")
S(4)

code_line_table([
    ("float trainingBatchDefault(layer_t **model, size_t modelSize,",
     "Returns the loss for this batch as a float. model and modelSize describe "
     "the network. lossConfig selects the loss function. batch holds the samples. "
     "calculateGradsFn is a function pointer — passing calculateGradsSequential "
     "here decouples the batch function from any specific backprop implementation."),

    ("    for (size_t i = 0; i < batch->size; i++) {",
     "Iterate over every sample in the batch. batch->size equals batchSize "
     "(the dropLast policy guarantees no partial batches)."),

    ("        trainingStats_t *stats = calculateGradsFn(model, modelSize, lossConfig,",
     "Call the backpropagation function for this single sample. "
     "calculateGradsFn is the function pointer passed by the caller — "
     "in normal use this is calculateGradsSequential, but for RigL the project "
     "calls trainingBatchDefault from its own custom epoch loop."),

    ("                 forwardReduction, batch->samples[i]->item, batch->samples[i]->label);",
     "Pass the i-th sample's input tensor and its label tensor. "
     "->item is the input (sensor readings), ->label is the one-hot target."),

    ("        totalLoss += stats->loss;",
     "Accumulate the scalar loss. After the loop, totalLoss is the sum of "
     "per-sample losses across the batch."),

    ("        freeTrainingStats(stats);",
     "Release the trainingStats_t returned by calculateGradsFn. "
     "This frees the output prediction tensor and the struct itself."),

    ("        freeSample(batch->samples[i]);",
     "Release the sample's memory. Each getBatch call allocates sample_t structs "
     "and their tensors; freeSample releases them. The underlying dataset arrays "
     "are NOT freed — only the per-batch wrappers."),

    ("    if (forwardReduction == REDUCTION_MEAN) { return totalLoss / (float)batch->size; }",
     "If loss was averaged per-sample inside calculateGradsSequential "
     "(REDUCTION_MEAN), return the mean over the batch. "
     "The (float) cast prevents integer division. "
     "If REDUCTION_SUM, return the raw sum."),
])
S(6)

H2("23 (continued) · TrainingEpochDefault.h / TrainingEpochDefault.c")
NT("src/userApi/training_loop/training_epoch/TrainingEpochDefault.h + .c")
S(3)
BD("TrainingEpochDefault is the outer loop — it iterates over all batches in the "
   "training DataLoader for one full pass through the training set. After each "
   "batch, it applies the mean-scale correction (if REDUCTION_MEAN), steps the "
   "optimizer (updates weights), and zeroes the gradient accumulators. "
   "At the end it returns the mean epoch loss.")
S(4)

code_line_table([
    ("float trainingEpochDefault(layer_t **model, size_t modelSize, lossConfig_t lossConfig,",
     "Returns the mean training loss for this epoch. All arguments are passed "
     "straight through to trainingBatchDefault, plus the optimizer."),

    ("    size_t numberOfBatches = datasetSize / dataLoader->batchSize;",
     "Compute how many full batches fit in the dataset. Integer division silently "
     "discards the remainder (the dropLast guarantee means no partial batches)."),

    ("    optimizerFunctions_t optimFns = optimizerFunctions[optimizer->type];",
     "Fetch the optimizer's vtable row. optimizerFunctions is a dispatch table "
     "(defined in Optimizer.c) that maps optimizer type (e.g. SGD) to its step, "
     "zero, and scale functions. Caching the row in a local variable avoids "
     "repeated table lookups inside the loop."),

    ("    batch_t *batch = dataLoader->getBatch(dataLoader, i);",
     "Fetch the i-th batch. getBatch uses the shuffled index array to pick "
     "batchSize samples in the shuffled order for this epoch."),

    ("    tensor_t *labelRef = batch->samples[0]->label;",
     "Save a pointer to the first sample's label BEFORE trainingBatchDefault "
     "consumes the batch. freeSample (called inside trainingBatchDefault) only "
     "frees the sample_t wrapper — the underlying label tensor in the dataset "
     "array remains alive, so labelRef remains valid for computeMeanScale below."),

    ("    totalLoss += trainingBatchDefault(model, modelSize, lossConfig, batch, ...);",
     "Process the batch: forward pass for all samples, accumulate gradients, "
     "return the batch loss. Note: the optimizer step happens AFTER this call, "
     "so all samples in the batch contribute to the gradients before any weight update."),

    ("    if (lossConfig.backwardReduction == REDUCTION_MEAN) {",
     "If gradient reduction is MEAN: the gradients accumulated across the batch "
     "are per-sample averages, but the optimizer needs the batch-mean gradient. "
     "Apply a correction factor so the weight update magnitude is independent "
     "of batch size."),

    ("        float meanScale = lossFunctions[...].computeMeanScale(batch->size, labelRef);",
     "Compute the scaling factor. For cross-entropy with one-hot labels, "
     "computeMeanScale returns 1/(batch->size * NUM_CLASSES), normalising "
     "the gradient by both the batch size and the label vector width."),

    ("        scaleOptimizerGradients(optimizer, meanScale);",
     "Multiply every parameter's gradient accumulator by meanScale. "
     "This is applied once per batch, after all samples have contributed."),

    ("    optimFns.step(optimizer);",
     "Run the optimizer update step. For SGD with momentum: "
     "velocity_i = momentum * velocity_i - lr * gradient_i; "
     "weight_i += velocity_i. "
     "This modifies the weight tensors in place."),

    ("    optimFns.zero(optimizer);",
     "Reset all gradient accumulators to zero. Must be called after every "
     "optimizer step, before the next batch's gradients start accumulating. "
     "Forgetting this would sum gradients across batches (unintended)."),

    ("    freeBatch(batch);",
     "Free the batch struct and the sample_t wrappers. The actual tensor data "
     "in the dataset arrays is NOT freed — only the getBatch-allocated wrappers."),

    ("    return totalLoss / (float)numberOfBatches;",
     "Return the mean epoch loss: sum of all batch losses divided by the number "
     "of batches. This is the number printed as 'Training Loss: X.XXX'."),
])
PB()

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 12 — Inference Engine
# ═══════════════════════════════════════════════════════════════════════════
H1("Phase 12 — Inference Engine")
story.append(Paragraph(
    "InferenceApi.h / InferenceApi.c",
    PS("ph",fontSize=10,textColor=C_HDR,fontName="Helvetica-Bold",spaceAfter=5)))
S(2)
BD("InferenceApi runs the model in forward-only mode — no gradient computation, "
   "no backward pass. It is used during evaluation (to measure accuracy on the "
   "validation/test set) and for deployment on the Pico (to classify new sensor "
   "windows). Unlike CalculateGradsSequential which allocates a separate output "
   "tensor for every layer simultaneously, InferenceApi uses a ping-pong buffer "
   "strategy: it keeps only two tensors alive at any time (the current layer's "
   "input and the current layer's output), dramatically reducing peak memory use.")
S(6)

H2("24 · InferenceApi.h")
NT("src/userApi/include/InferenceApi.h")
S(3)
code_line_table([
    ("typedef struct inferenceStats { tensor_t *output; float loss; } inferenceStats_t;",
     "Result of one inference call with loss computation. "
     "output holds the model's prediction (class probabilities). "
     "loss is the cross-entropy against the ground-truth label. "
     "Analogous to trainingStats_t but without gradient information."),

    ("tensor_t *inference(layer_t **model, size_t numberOfLayers, tensor_t *input);",
     "Run a single forward pass. Returns a heap-allocated tensor_t containing "
     "the model's output (class probabilities after Softmax). "
     "The caller is responsible for freeing this tensor."),

    ("tensor_t **inferenceBatched(layer_t **model, size_t numberOfLayers, batch_t *batch);",
     "Run inference on a full batch. Returns an array of tensor_t pointers — "
     "one per sample. Used when evaluating multiple samples at once. "
     "The caller frees both the array and each tensor."),

    ("inferenceStats_t *inferenceWithLoss(..., lossFuncType_t funcType, reduction_t fwd);",
     "Run inference AND compute the loss against the supplied label. "
     "This is what the evaluation loop uses: it needs both the prediction "
     "(to check correctness) and the loss (to track test loss)."),
])
S(6)

H2("24 (continued) · InferenceApi.c — the ping-pong buffer pattern")
S(3)
BD("The key architectural decision in InferenceApi.c is the ping-pong buffer: "
   "instead of pre-allocating N+1 tensors (one per layer), it allocates just "
   "two — outputNext (the current input to the layer) and outputCurr (the current "
   "layer's output). After each layer, outputNext is freed and replaced by "
   "outputCurr. This keeps memory proportional to the single largest layer "
   "output rather than the sum of all layer outputs.")
S(4)

code_line_table([
    ("tensor_t *inference(layer_t **model, size_t numberOfLayers, tensor_t *input) {",
     "Entry point for single-sample inference. Returns a tensor_t* that the "
     "caller owns and must eventually free."),

    ("    tensor_t outputNext; initBufferInput(input, &outputNext);",
     "Create a copy of the input tensor in a local stack variable. "
     "initBufferInput allocates heap memory for the data buffer and shape/quant "
     "structs, then copies the input values. Using a local stack variable for "
     "the tensor_t struct (not a pointer) avoids one heap allocation."),

    ("    for (size_t i = 0; i < numberOfLayers; i++) {",
     "Iterate over every layer in the model, left to right."),

    ("        tensor_t outputCurr;",
     "Stack variable for the current layer's output tensor. Like outputNext, "
     "the tensor_t header is on the stack; only its data buffer is on the heap."),

    ("        initBufferOutput(&outputCurr, currentLayer, outputNext.shape, ...);",
     "Allocate the output buffer. Calls calcOutputShape to determine the "
     "output dimensions (e.g. after a MaxPool with stride 2, the length halves), "
     "then reserveMemory for the data."),

    ("        forward(currentLayer, &outputNext, &outputCurr);",
     "Run the layer's forward computation: reads from outputNext, writes to "
     "outputCurr. The specific function called depends on currentLayerType "
     "(via the layerFunctions vtable)."),

    ("        deInitBuffer(&outputNext); outputNext = outputCurr;",
     "The ping-pong step: free outputNext (its data is no longer needed), "
     "then copy the outputCurr struct into outputNext for the next iteration. "
     "This is a struct assignment — it copies the pointer values inside the struct, "
     "not the pointed-to data. The heap memory now belongs to outputNext."),

    ("    tensor_t *output = getTensorLike(&outputNext);",
     "Allocate the final return tensor with the same shape and quantization "
     "as the last layer's output."),

    ("    convertTensor(&outputNext, output);",
     "Copy (and optionally type-convert) the last activation into output. "
     "convertTensor handles quantization type differences."),

    ("    deInitBuffer(&outputNext); return output;",
     "Free the last ping-pong buffer, then return the allocated output tensor. "
     "The caller owns this tensor and must call freeTensor when done."),

    ("inferenceStats_t *inferenceWithLoss(... tensor_t *label, lossFuncType_t funcType ...) {",
     "Same forward pass as inference(), plus a loss computation at the end. "
     "Used by the evaluation loop to compute both test accuracy and test loss."),

    ("    float loss = lossFns.forward(&outputNext, label, forwardReduction);",
     "Compute the scalar loss between the model's output and the label. "
     "For cross-entropy: loss = -sum(label_i * log(output_i)). "
     "The result is stored in inferenceStats->loss."),
])
PB()

# ═══════════════════════════════════════════════════════════════════════════
# QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════════════════
H1("Syntax Quick Reference — Guide 3 Additions")
S(4)
BD("This table collects every new C syntax construct introduced in Guide 3 that "
   "did not appear in Guide 2.")

ref = [
    ["Syntax","Full name","What it does"],
    ["FILE *f = fopen(p, mode)",  "File open",
     "Opens the file at path p. mode 'rb' = read binary. Returns NULL on failure."],
    ["fread(buf, size, n, f)",    "File read",
     "Reads n items of size bytes each from file f into buffer buf."],
    ["strcmp(a, b)",              "String compare",
     "Returns 0 if strings a and b are identical, nonzero otherwise."],
    ["sscanf(str, fmt, ...)",     "String scan",
     "Parses str using format string fmt, stores results in the following pointers."],
    ["strstr(hay, needle)",       "String search",
     "Returns a pointer to the first occurrence of needle inside hay, or NULL."],
    ["strtoull(p, &end, base)",   "String to unsigned long long",
     "Converts the decimal number at p to size_t. Sets end to the first non-digit."],
    ["tensor_t x; (stack)",       "Stack-allocated struct",
     "The struct header lives on the call stack. The data it points to may still be heap."],
    ["tensor_t *x; (heap)",       "Heap-allocated struct",
     "reserveMemory allocates the struct on the heap. Must be explicitly freed."],
    ["outputNext = outputCurr;",  "Struct assignment",
     "Copies all fields of the struct (pointer values, not pointed-to data)."],
    ["for (int i=(int)N-1; i>=0; i--)", "Reverse loop",
     "Walks an array backwards. The cast (int) is needed because size_t is unsigned "
     "and i>=0 would never be false for size_t."],
    ["vtable[type].fn(args)",     "Dispatch table call",
     "Selects the correct function for this layer type and calls it. "
     "C-style polymorphism without virtual keyword."],
    ["fn_ptr(args)",              "Function pointer call",
     "Calls the function whose address is stored in fn_ptr. Used for calculateGradsFn."],
]
th = PS("th3",fontName="Helvetica-Bold",fontSize=8.5,textColor=C_WHITE)
td = PS("td3",fontSize=8.5,leading=12)
rws = []
for i,r in enumerate(ref):
    if i==0: rws.append([Paragraph(c,th) for c in r])
    else:    rws.append([Paragraph(c,td) for c in r])
tt2 = Table(rws, colWidths=[BW*0.28, BW*0.22, BW*0.50])
tt2.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0),C_HDR),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE,C_ACC]),
    ("BOX",(0,0),(-1,-1),0.5,colors.grey),
    ("INNERGRID",(0,0),(-1,-1),0.3,colors.lightgrey),
    ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("LEFTPADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP"),
]))
story.append(tt2); S(8)
HR()
story.append(Paragraph(
    "Next step — Guide 4: Conv1d / Linear layer internals, Pool layers, "
    "Optimizer internals, Serialization (Serialize / Deserialize), "
    "and the HAR example main program.",
    PS("nx","Normal",fontSize=8.5,textColor=C_GREY,alignment=TA_CENTER)))
S(4)
story.append(Paragraph(
    "Mohamed (matef517@gmail.com)  ·  OnDevice HAR FQT+RigL  ·  2026",
    PS("ft","Normal",fontSize=8,textColor=C_GREY,alignment=TA_CENTER)))

# ── Build ────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm,  bottomMargin=2*cm,
    title="Code Reading Guide 3 — Files 20-24",
    author="Mohamed",
)
doc.build(story)
print("Done:", OUT)
