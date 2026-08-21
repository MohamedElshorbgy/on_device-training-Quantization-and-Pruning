/* main.c — HAR FQT+RigL training (OnDeviceTraining framework)
 *
 * Architecture (matches har_classifier_v2):
 *   Conv1d(9→16,K=7,SAME)+ReLU+MaxPool(2,2)
 *   Conv1d(16→32,K=5,SAME)+ReLU+MaxPool(2,2)
 *   Conv1d(32→64,K=3,SAME)+ReLU+AvgPool(32,32)
 *   Flatten → Linear(64→6) → Softmax
 *
 * Evaluation follows Evci et al. (RigL, ICML 2020):
 *   - Per-layer parameter count (total and active)
 *   - Inference FLOPs: dense baseline vs sparse (with mask)
 *   - Training FLOPs: total computation across all epochs
 *   - Test accuracy, precision, recall, F1 (macro-averaged)
 *   - Confusion matrix and per-class accuracy
 *
 * Run from the OnDeviceTraining project root:
 *   ./build_pc/OnDeviceTraining_HAR_FQT_RigL/har_fqt_rigl
 * or pass data dir as first argument:
 *   ./har_fqt_rigl  /path/to/har_classifier/data
 */

#define SOURCE_FILE "HAR_FQT_RIGL_MAIN"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

/* ── Memory tracking ─────────────────────────────────────────────────
 * Linux/WSL : reads /proc/self/status (VmRSS, VmPeak, VmSize)
 * Windows   : uses GetProcessMemoryInfo from psapi.h
 * STM32     : stub (no OS memory API available)               */
#if defined(__linux__)
#  include <sys/resource.h>
static void printProcessMemory(const char *label)
{
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) { printf("[mem] (%s) /proc/self/status unavailable\n", label); return; }
    long vm_rss_kb = 0, vm_peak_kb = 0, vm_size_kb = 0;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        if      (strncmp(line, "VmRSS:",  6) == 0) sscanf(line + 6, "%ld", &vm_rss_kb);
        else if (strncmp(line, "VmPeak:", 7) == 0) sscanf(line + 7, "%ld", &vm_peak_kb);
        else if (strncmp(line, "VmSize:", 7) == 0) sscanf(line + 7, "%ld", &vm_size_kb);
    }
    fclose(f);
    printf("[mem] %-30s  RSS=%-7ld KB  Virtual=%-7ld KB  PeakRSS=%-7ld KB\n",
           label, vm_rss_kb, vm_size_kb, vm_peak_kb);
}
#elif defined(_WIN32) || defined(_WIN64)
#  include <windows.h>
#  include <psapi.h>
static void printProcessMemory(const char *label)
{
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        long rss_kb      = (long)(pmc.WorkingSetSize      / 1024);
        long peak_rss_kb = (long)(pmc.PeakWorkingSetSize  / 1024);
        long pagefile_kb = (long)(pmc.PagefileUsage       / 1024);
        printf("[mem] %-30s  RSS=%-7ld KB  PageFile=%-7ld KB  PeakRSS=%-7ld KB\n",
               label, rss_kb, pagefile_kb, peak_rss_kb);
    } else {
        printf("[mem] (%s) GetProcessMemoryInfo failed\n", label);
    }
}
#else
/* Stub for STM32 / bare-metal */
static void printProcessMemory(const char *label) { (void)label; }
#endif

/* ── OnDeviceTraining framework ─────────────────────────────────── */
#include "CalculateGradsSequential.h"
#include "Common.h"
#include "Conv1dApi.h"
#include "DataLoader.h"
#include "DataLoaderApi.h"
#include "FlattenApi.h"
#include "InferenceApi.h"
#include "Layer.h"
#include "LayerQuant.h"
#include "LinearApi.h"
#include "LossFunction.h"
#include "NPYLoaderApi.h"
#include "Optimizer.h"
#include "OptimizerApi.h"
#include "Pool1dApi.h"
#include "QuantizationApi.h"
#include "ReluApi.h"
#include "SgdApi.h"
#include "SoftmaxApi.h"
#include "StorageApi.h"
#include "Tensor.h"
#include "TensorApi.h"
#include "TrainingBatchDefault.h"
#include "TrainingLoopApi.h"

/* ── Project headers ─────────────────────────────────────────────── */
#include "config.h"
#include "rigl.h"

/* ═══════════════════════════════════════════════════════════════════
 *  FLOPs constants  (Evci et al. §5 methodology)
 *
 *  Conv1d dense FLOPs = 2 × K × Cin × Cout × Lout
 *    (×2 because each MAC = 1 multiply + 1 add)
 *  Linear dense FLOPs = 2 × Fin × Fout
 *
 *  After MaxPool(2,2): Lout = Lin/2
 *  After second MaxPool: Lout = Lin/4
 *  AvgPool output is 1 per channel → only 1 timestep into Linear.
 * ═══════════════════════════════════════════════════════════════════ */
#define L1   INPUT_T          /* conv1 output length (SAME pad) = 128 */
#define L2   (INPUT_T / 2)    /* after MaxPool1                  =  64 */
#define L3   (INPUT_T / 4)    /* after MaxPool2                  =  32 */

/* Dense FLOPs per inference pass for each parameterised layer */
static const long long DENSE_FLOPS[RIGL_NUM_LAYERS] = {
    2LL * CONV1_K * INPUT_C * CONV1_F * L1,   /* conv1: 258,048  */
    2LL * CONV2_K * CONV1_F * CONV2_F * L2,   /* conv2: 327,680  */
    2LL * CONV3_K * CONV2_F * CONV3_F * L3,   /* conv3: 393,216  */
    2LL * FC_IN   * NUM_CLS,                   /* linear:    768  */
};

/* Dense parameter counts per layer */
static const long long DENSE_PARAMS[RIGL_NUM_LAYERS] = {
    (long long)CONV1_K * INPUT_C * CONV1_F,   /* 1,008  */
    (long long)CONV2_K * CONV1_F * CONV2_F,   /* 2,560  */
    (long long)CONV3_K * CONV2_F * CONV3_F,   /* 6,144  */
    (long long)FC_IN   * NUM_CLS,             /*   384  */
};

static const char *LAYER_NAMES[RIGL_NUM_LAYERS] = {
    "Conv1(9→16,K=7)", "Conv2(16→32,K=5)",
    "Conv3(32→64,K=3)", "Linear(64→6)"
};

static const char *CLASS_NAMES[NUM_CLS] = {
    "WALKING", "UPSTAIRS", "DOWNSTAIRS",
    "SITTING", "STANDING", "LAYING"
};

/* Indices of parameterised layers in model[] */
static const int RIGL_IDX[RIGL_NUM_LAYERS] = {0, 3, 6, 10};

/* ═══════════════════════════════════════════════════════════════════
 *  Streaming dataset loader — one batch at a time
 * ═══════════════════════════════════════════════════════════════════
 *
 * Instead of loading the full .npy dataset into RAM (~34 MB for
 * train_x), we keep the file open and fseek/fread one sample per
 * getSample() call.  Labels are tiny (~29 KB) and stay in RAM.
 *
 * We pre-allocate BATCH_SIZE sample slots so the DataLoader can hold
 * a full batch simultaneously.  Slots are reused round-robin.
 *
 * Memory: ~BATCH_SIZE × (INPUT_T × INPUT_C + NUM_CLS) × 4 bytes
 *       = 64 × (1152 + 6) × 4 ≈ 295 KB   (vs ~34 MB before)
 * ═══════════════════════════════════════════════════════════════════ */

#include "NPYLoader.h"   /* openNPYFile, checkMagic, readHeaderSize,
                            readHeader, getNumberOfDimsFromHeader,
                            getShapeFromHeader                        */

typedef struct {
    FILE    *f;            /* X file kept open for streaming          */
    long     data_offset;  /* byte offset where raw X data starts     */
    size_t   sample_bytes; /* bytes per X sample (T*C*sizeof(float))  */
    size_t   n_samples;    /* total number of samples in dataset      */
    int32_t *labels;       /* all integer labels loaded in RAM        */
    sample_t *pool[BATCH_SIZE]; /* pre-allocated sample slots         */
    size_t    slot;        /* round-robin slot counter                */
} StreamLoader;

static StreamLoader g_trainStream;
static StreamLoader g_valStream;
static StreamLoader g_testStream;

static void streamLoaderInit(StreamLoader *sl,
                             const char *x_path, const char *y_path)
{
    /* ── Open X file and parse header ─────────────────────────────── */
    sl->f = openNPYFile((char *)x_path);
    checkMagic(sl->f);
    uint32_t hsize = readHeaderSize(sl->f);
    char *hdr = malloc(hsize + 1);
    readHeader(hdr, hsize, sl->f);

    size_t ndims = getNumberOfDimsFromHeader(hdr);
    size_t dims[ndims], order[ndims];
    shape_t shape;
    shape.dimensions        = dims;
    shape.orderOfDimensions = order;
    shape.numberOfDimensions = ndims;
    getShapeFromHeader(&shape, dims, order, hdr, ndims);
    free(hdr);

    sl->n_samples   = dims[0];
    sl->data_offset = ftell(sl->f);

    sl->sample_bytes = sizeof(float);
    for (size_t i = 1; i < ndims; i++) sl->sample_bytes *= dims[i];

    /* ── Load all labels into RAM (small: n_samples × 4 bytes) ───── */
    FILE *fy = openNPYFile((char *)y_path);
    checkMagic(fy);
    uint32_t yhsize = readHeaderSize(fy);
    char *yhdr = malloc(yhsize + 1);
    readHeader(yhdr, yhsize, fy);
    free(yhdr);

    sl->labels = malloc(sl->n_samples * sizeof(int32_t));
    size_t nr = fread(sl->labels, sizeof(int32_t), sl->n_samples, fy);
    if (nr != sl->n_samples) { fprintf(stderr,"label fread error\n"); exit(1); }
    fclose(fy);

    /* ── Pre-allocate BATCH_SIZE sample slots ─────────────────────── */
    quantization_t *qf = quantizationInitFloat();

    for (int s = 0; s < BATCH_SIZE; s++) {
        sl->pool[s] = malloc(sizeof(sample_t));

        /* Input tensor: shape [1, dims[1], ..., dims[ndims-1]] */
        size_t *xd  = reserveMemory(ndims * sizeof(size_t));
        size_t *xo  = reserveMemory(ndims * sizeof(size_t));
        xd[0] = 1;
        for (size_t i = 1; i < ndims; i++) xd[i] = dims[i];
        for (size_t i = 0; i < ndims; i++) xo[i] = i;
        shape_t *xs = reserveMemory(sizeof(shape_t));
        xs->dimensions        = xd;
        xs->orderOfDimensions = xo;
        xs->numberOfDimensions = ndims;
        sl->pool[s]->item = initTensor(xs, getQLike(qf), NULL);

        /* Label tensor: one-hot [NUM_CLS] */
        size_t *yd  = reserveMemory(sizeof(size_t));
        size_t *yo  = reserveMemory(sizeof(size_t));
        yd[0] = NUM_CLS; yo[0] = 0;
        shape_t *ys = reserveMemory(sizeof(shape_t));
        ys->dimensions        = yd;
        ys->orderOfDimensions = yo;
        ys->numberOfDimensions = 1;
        sl->pool[s]->label = initTensor(ys, getQLike(qf), NULL);
    }
    freeQuantization(qf);
    sl->slot = 0;
}

/* Called by the DataLoader for each sample in a batch. */
static sample_t *streamGetSample(StreamLoader *sl, size_t id)
{
    size_t s = sl->slot % BATCH_SIZE;
    sl->slot++;

    /* Load X into the pool slot's tensor buffer */
    fseek(sl->f, sl->data_offset + (long)(id * sl->sample_bytes), SEEK_SET);
    fread(sl->pool[s]->item->data, 1, sl->sample_bytes, sl->f);

    /* Build one-hot label in the pool slot's label buffer */
    int32_t cls = sl->labels[id];
    float  *yd  = (float *)sl->pool[s]->label->data;
    for (int c = 0; c < NUM_CLS; c++)
        yd[c] = (c == cls) ? 1.0f : 0.0f;

    /* Return a thin malloc'd wrapper — the DataLoader calls freeSample()
     * → free() on this pointer after each batch.  By returning a fresh
     * wrapper (not the pool slot itself), freeSample() only frees the
     * wrapper; the pool's tensor buffers stay valid for the next batch.
     * This matches the pattern used by npyGetSample() in the framework. */
    sample_t *wrap = malloc(sizeof(sample_t));
    wrap->item  = sl->pool[s]->item;
    wrap->label = sl->pool[s]->label;
    return wrap;
}

static void initDataSets(const char *dataDir)
{
    char xp[512], yp[512];

#define INIT_STREAM(split, sl) \
    snprintf(xp, sizeof(xp), "%s/" split "_x.npy", dataDir); \
    snprintf(yp, sizeof(yp), "%s/" split "_y.npy", dataDir); \
    streamLoaderInit(&(sl), xp, yp);

    INIT_STREAM("train", g_trainStream)
    INIT_STREAM("val",   g_valStream)
    INIT_STREAM("test",  g_testStream)
#undef INIT_STREAM

    printf("[data] train=%-5zu  val=%-5zu  test=%zu  (streaming — one batch at a time)\n",
           g_trainStream.n_samples,
           g_valStream.n_samples,
           g_testStream.n_samples);
}

static sample_t *getTrainSample(size_t id) { return streamGetSample(&g_trainStream, id); }
static sample_t *getValSample  (size_t id) { return streamGetSample(&g_valStream,   id); }
static sample_t *getTestSample (size_t id) { return streamGetSample(&g_testStream,  id); }
static size_t    getTrainSize  (void)      { return g_trainStream.n_samples; }
static size_t    getValSize    (void)      { return g_valStream.n_samples;   }
static size_t    getTestSize   (void)      { return g_testStream.n_samples;  }

/* ═══════════════════════════════════════════════════════════════════
 *  Model (identical topology to har_classifier_v2)
 * ═══════════════════════════════════════════════════════════════════ */
static void buildModel(layer_t **model, layerQuant_t *lq)
{
    model[0] = conv1dLayerInit(
        &(conv1dInit_t){.inChannels=INPUT_C,.outChannels=CONV1_F,
                        .kernelSize=CONV1_K,.padding=SAME}, lq);
    model[1] = reluLayerInit(lq);
    model[2] = maxPool1dLayerInit(
        &(maxPool1dInit_t){.kernelSize=2,.stride=2,
                           .inputChannels=CONV1_F,.inputLength=INPUT_T}, lq);
    model[3] = conv1dLayerInit(
        &(conv1dInit_t){.inChannels=CONV1_F,.outChannels=CONV2_F,
                        .kernelSize=CONV2_K,.padding=SAME}, lq);
    model[4] = reluLayerInit(lq);
    model[5] = maxPool1dLayerInit(
        &(maxPool1dInit_t){.kernelSize=2,.stride=2,
                           .inputChannels=CONV2_F,.inputLength=INPUT_T/2}, lq);
    model[6] = conv1dLayerInit(
        &(conv1dInit_t){.inChannels=CONV2_F,.outChannels=CONV3_F,
                        .kernelSize=CONV3_K,.padding=SAME}, lq);
    model[7] = reluLayerInit(lq);
    model[8] = avgPool1dLayerInit(
        &(avgPool1dInit_t){.kernelSize=INPUT_T/4,.stride=INPUT_T/4}, lq);
    model[9]  = flattenLayerInit();
    model[10] = linearLayerInit(
        &(linearInit_t){.inFeatures=FC_IN,.outFeatures=NUM_CLS}, lq);
    model[11] = softmaxLayerInit(lq);
}

/* ═══════════════════════════════════════════════════════════════════
 *  RigL mask management
 * ═══════════════════════════════════════════════════════════════════ */
static uint8_t *g_masks[RIGL_NUM_LAYERS];

/* ERK layer descriptors — must match RIGL_IDX order:
 * conv1@0 (9→16,K=7), conv2@3 (16→32,K=5), conv3@6 (32→64,K=3),
 * linear@10 (64→6)                                                    */
static const rigl_layer_info_t ERK_INFO[RIGL_NUM_LAYERS] = {
    {9,  16, 7, 1},   /* Conv1 */
    {16, 32, 5, 1},   /* Conv2 */
    {32, 64, 3, 1},   /* Conv3 */
    {64,  6, 1, 0},   /* Linear */
};

static void riglInit(layer_t **model)
{
    /* Compute per-layer sizes */
    int sizes[RIGL_NUM_LAYERS];
    for (int i = 0; i < RIGL_NUM_LAYERS; i++)
        sizes[i] = (int)rigl_layer_size(model[RIGL_IDX[i]]);

    /* ERK: compute non-uniform per-layer sparsities */
    float erk_sp[RIGL_NUM_LAYERS];
    rigl_erk_sparsities(ERK_INFO, sizes, RIGL_NUM_LAYERS, RIGL_SPARSITY, erk_sp);

    printf("\n[RigL] ERK sparsity distribution (global target = %.0f%%):\n",
           RIGL_SPARSITY * 100.0f);
    const char *names[] = {"Conv1","Conv2","Conv3","Linear"};
    for (int i = 0; i < RIGL_NUM_LAYERS; i++)
        printf("  %-8s  params=%-5d  sparsity=%.1f%%\n",
               names[i], sizes[i], (double)(erk_sp[i] * 100.0f));
    printf("\n");

    for (int i = 0; i < RIGL_NUM_LAYERS; i++) {
        g_masks[i] = (uint8_t *)malloc((size_t)sizes[i]);
        if (!g_masks[i]) { fprintf(stderr,"OOM mask %d\n",i); exit(1); }
        rigl_init_from_layer(model[RIGL_IDX[i]], g_masks[i],
                             erk_sp[i], (uint32_t)(SEED + i * 7));
        rigl_apply_to_layer(model[RIGL_IDX[i]], g_masks[i]);
    }
}

static void riglApplyAll(layer_t **model)
{
    for (int i = 0; i < RIGL_NUM_LAYERS; i++)
        rigl_apply_to_layer(model[RIGL_IDX[i]], g_masks[i]);
}

/* ── Cosine decay for the cycling fraction ───────────────────────────
 * frac(t) = frac_0 * 0.5 * (1 + cos(pi * t / T_end))
 *
 * t      : current RigL update step (0-indexed)
 * t_end  : total number of RigL update steps over full training
 *
 * At t=0       : frac = frac_0        (maximum exploration)
 * At t=t_end/2 : frac = frac_0 * 0.5
 * At t=t_end   : frac = 0             (mask frozen)           */
static float riglDecayedFrac(int t, int t_end)
{
    if (t_end <= 0 || t >= t_end) return 0.0f;
    float cos_val = cosf((float)M_PI * (float)t / (float)t_end);
    float frac = RIGL_FRAC * 0.5f * (1.0f + cos_val);
    return frac < 0.0f ? 0.0f : frac;
}

/* Global RigL update step counter and total steps (set in main). */
static int g_rigl_step   = 0;
static int g_rigl_t_end  = 1;

static void riglUpdateAll(layer_t **model)
{
    float frac = riglDecayedFrac(g_rigl_step, g_rigl_t_end);
    for (int i = 0; i < RIGL_NUM_LAYERS; i++) {
        rigl_step_layer(model[RIGL_IDX[i]], g_masks[i], RIGL_SPARSITY, frac);
        rigl_apply_to_layer(model[RIGL_IDX[i]], g_masks[i]);
    }
    g_rigl_step++;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Evaluation reporting  (follows RigL paper Table 1/2 format)
 * ═══════════════════════════════════════════════════════════════════ */

/* ── Model summary: per-layer param count and sparsity ───────────── */
static void printModelSummary(layer_t **model)
{
    printf("\n┌─────────────────────────────────────────────────────────────────┐\n");
    printf("│  Model Summary                                                   │\n");
    printf("├──────────────────┬──────────┬──────────┬──────────┬─────────────┤\n");
    printf("│ Layer            │ Params   │ Active   │ Pruned   │ Sparsity    │\n");
    printf("├──────────────────┼──────────┼──────────┼──────────┼─────────────┤\n");

    long long total_params  = 0;
    long long total_active  = 0;

    for (int i = 0; i < RIGL_NUM_LAYERS; i++) {
        size_t n      = rigl_layer_size(model[RIGL_IDX[i]]);
        int    active = rigl_active_count(g_masks[i], (int)n);
        int    pruned = (int)n - active;
        float  sp     = rigl_actual_sparsity(g_masks[i], (int)n);
        printf("│ %-16s │ %8lld │ %8d │ %8d │ %9.1f%% │\n",
               LAYER_NAMES[i], DENSE_PARAMS[i], active, pruned, (double)(sp*100.f));
        total_params += DENSE_PARAMS[i];
        total_active += active;
    }

    printf("├──────────────────┼──────────┼──────────┼──────────┼─────────────┤\n");
    printf("│ TOTAL            │ %8lld │ %8lld │ %8lld │ %9.1f%% │\n",
           total_params, total_active,
           total_params - total_active,
           (double)((total_params - total_active) * 100.0 / total_params));
    printf("└──────────────────┴──────────┴──────────┴──────────┴─────────────┘\n");
}

/* ── FLOPs analysis ───────────────────────────────────────────────── */
static void printFLOPsReport(layer_t **model, size_t totalBatches,
                             size_t trainSamples)
{
    long long dense_total  = 0;
    long long sparse_total = 0;

    printf("\n┌─────────────────────────────────────────────────────────────────┐\n");
    printf("│  Inference FLOPs  (Evci et al., ICML 2020 — Table 1 format)     │\n");
    printf("├──────────────────┬──────────────┬──────────────┬────────────────┤\n");
    printf("│ Layer            │ Dense FLOPs  │ Sparse FLOPs │  FLOPs ratio   │\n");
    printf("├──────────────────┼──────────────┼──────────────┼────────────────┤\n");

    for (int i = 0; i < RIGL_NUM_LAYERS; i++) {
        size_t n     = rigl_layer_size(model[RIGL_IDX[i]]);
        int    active = rigl_active_count(g_masks[i], (int)n);
        double sp    = 1.0 - (double)active / (double)n;
        long long sp_flops = (long long)(DENSE_FLOPS[i] * (1.0 - sp));
        printf("│ %-16s │ %12lld │ %12lld │ %12.3fx   │\n",
               LAYER_NAMES[i], DENSE_FLOPS[i], sp_flops,
               (double)sp_flops / (double)DENSE_FLOPS[i]);
        dense_total  += DENSE_FLOPS[i];
        sparse_total += sp_flops;
    }

    printf("├──────────────────┼──────────────┼──────────────┼────────────────┤\n");
    printf("│ TOTAL            │ %12lld │ %12lld │ %12.3fx   │\n",
           dense_total, sparse_total,
           (double)sparse_total / (double)dense_total);
    printf("└──────────────────┴──────────────┴──────────────┴────────────────┘\n");

    /* Training FLOPs
     * Forward ≈ 1× sparse inference FLOPs per sample
     * Backward ≈ 2× sparse inference FLOPs per sample
     * RigL regrow overhead: one dense grad pass every RIGL_DELTA_T batches
     */
    long long rigl_updates   = (long long)(totalBatches / RIGL_DELTA_T + 1);
    long long train_flops    = (long long)NUM_EPOCHS * (long long)trainSamples
                               * 3LL * sparse_total;
    long long rigl_overhead  = rigl_updates * 2LL * dense_total; /* grad scan */
    long long total_train    = train_flops + rigl_overhead;
    long long dense_train    = (long long)NUM_EPOCHS * (long long)trainSamples
                               * 3LL * dense_total;

    printf("\n┌─────────────────────────────────────────────────────────────────┐\n");
    printf("│  Training FLOPs                                                  │\n");
    printf("├──────────────────────────────────────────┬──────────────────────┤\n");
    printf("│ Dense baseline training FLOPs            │ %20lld │\n", dense_train);
    printf("│ RigL sparse training FLOPs               │ %20lld │\n", train_flops);
    printf("│ RigL regrow overhead (%4lld updates)     │ %20lld │\n",
           rigl_updates, rigl_overhead);
    printf("│ RigL total training FLOPs                │ %20lld │\n", total_train);
    printf("│ FLOPs ratio vs dense                     │ %19.3fx  │\n",
           (double)total_train / (double)dense_train);
    printf("└──────────────────────────────────────────┴──────────────────────┘\n");
}

/* ── Full classification report ──────────────────────────────────── */
static void printClassificationReport(classificationReport_t *rpt)
{
    epochStats_t *s = &rpt->stats;
    printf("\n┌─────────────────────────────────────────────────────────────────┐\n");
    printf("│  Classification Report                                           │\n");
    printf("├──────────────────────┬────────────┬────────────┬────────────────┤\n");
    printf("│ Metric               │   Value    │            │                │\n");
    printf("├──────────────────────┼────────────┼────────────┼────────────────┤\n");
    printf("│ Test Accuracy        │ %8.4f   │            │                │\n",
           (double)s->accuracy);
    printf("│ Test Loss            │ %8.4f   │            │                │\n",
           (double)s->loss);
    printf("│ Precision (macro)    │ %8.4f   │            │                │\n",
           (double)s->precision);
    printf("│ Recall    (macro)    │ %8.4f   │            │                │\n",
           (double)s->recall);
    printf("│ F1-Score  (macro)    │ %8.4f   │            │                │\n",
           (double)s->f1);
    printf("└──────────────────────┴────────────┴────────────┴────────────────┘\n");

    /* Per-class accuracy from confusion matrix
     * cm[pred * numClasses + actual]                                */
    printf("\n┌──────────────────┬──────────┬──────────┬──────────┬────────────┐\n");
    printf("│ Class            │ TP       │ Total    │ Accuracy │ Support    │\n");
    printf("├──────────────────┼──────────┼──────────┼──────────┼────────────┤\n");

    size_t C = rpt->numClasses;
    for (size_t c = 0; c < C; c++) {
        /* TP = cm[c * C + c] (predicted=c, actual=c)              */
        size_t tp    = rpt->confusionMatrix[c * C + c];
        /* support (total actual class c) = sum over pred col      */
        size_t total = 0;
        for (size_t p = 0; p < C; p++)
            total += rpt->confusionMatrix[p * C + c];
        double acc = total > 0 ? (double)tp / (double)total : 0.0;
        printf("│ %-16s │ %8zu │ %8zu │ %7.2f%% │ %10zu │\n",
               CLASS_NAMES[c], tp, total, acc * 100.0, total);
    }
    printf("└──────────────────┴──────────┴──────────┴──────────┴────────────┘\n");

    /* Confusion matrix */
    printf("\nConfusion Matrix (rows=Predicted, cols=Actual):\n");
    printf("         ");
    for (size_t c = 0; c < C; c++)
        printf("%-11s", CLASS_NAMES[c]);
    printf("\n");
    for (size_t p = 0; p < C; p++) {
        printf("%-9s", CLASS_NAMES[p]);
        for (size_t a = 0; a < C; a++)
            printf("%-11zu", rpt->confusionMatrix[p * C + a]);
        printf("\n");
    }
}

/* ── Sparsity table (printed every 5 epochs) ─────────────────────── */
static void printSparsityTable(layer_t **model)
{
    printf("  [sparsity]");
    for (int i = 0; i < RIGL_NUM_LAYERS; i++) {
        size_t n = rigl_layer_size(model[RIGL_IDX[i]]);
        printf("  layer[%2d]=%.1f%%",
               RIGL_IDX[i],
               (double)(rigl_actual_sparsity(g_masks[i], (int)n) * 100.f));
    }
    printf("\n");
}

/* ═══════════════════════════════════════════════════════════════════
 *  Custom training epoch with RigL hooks
 * ═══════════════════════════════════════════════════════════════════ */
static float trainingEpochRigL(layer_t **model, size_t modelSize,
                                lossConfig_t lossConfig,
                                dataLoader_t *trainLoader,
                                optimizer_t  *optimizer,
                                size_t *batchCounterInOut)
{
    optimizerFunctions_t optimFns = optimizerFunctions[optimizer->type];
    size_t numBatches  = trainLoader->getDatasetSize() / trainLoader->batchSize;
    float  totalLoss   = 0.0f;

    for (size_t b = 0; b < numBatches; b++) {
        batch_t  *batch    = trainLoader->getBatch(trainLoader, b);
        tensor_t *labelRef = batch->samples[0]->label;

        totalLoss += trainingBatchDefault(model, modelSize, lossConfig, batch,
                                          calculateGradsSequential,
                                          lossConfig.backwardReduction);

        if (lossConfig.backwardReduction == REDUCTION_MEAN) {
            float scale = lossFunctions[lossConfig.funcType]
                              .computeMeanScale(batch->size, labelRef);
            scaleOptimizerGradients(optimizer, scale);
        }

        optimFns.step(optimizer);

        /* RigL: zero pruned weights after every optimizer step */
        riglApplyAll(model);

        (*batchCounterInOut)++;

        /* RigL: prune + regrow every RIGL_DELTA_T batches */
        if ((*batchCounterInOut) % RIGL_DELTA_T == 0)
            riglUpdateAll(model);

        optimFns.zero(optimizer);
        freeBatch(batch);
    }

    return totalLoss / (float)numBatches;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Theoretical memory breakdown
 *  All sizes in bytes.  FLOAT32 = 4 B/element, uint8_t mask = 1 B.
 * ═══════════════════════════════════════════════════════════════════ */
static void printMemoryBreakdown(void)
{
    /* ── Weight tensors ────────────────────────────────────────────── */
    size_t w_conv1  = (size_t)CONV1_K * INPUT_C * CONV1_F * 4;   /* weights */
    size_t b_conv1  = (size_t)CONV1_F * 4;                        /* bias    */
    size_t w_conv2  = (size_t)CONV2_K * CONV1_F * CONV2_F * 4;
    size_t b_conv2  = (size_t)CONV2_F * 4;
    size_t w_conv3  = (size_t)CONV3_K * CONV2_F * CONV3_F * 4;
    size_t b_conv3  = (size_t)CONV3_F * 4;
    size_t w_fc     = (size_t)FC_IN   * NUM_CLS  * 4;
    size_t b_fc     = (size_t)NUM_CLS * 4;

    size_t total_weights = w_conv1 + b_conv1 + w_conv2 + b_conv2
                         + w_conv3 + b_conv3 + w_fc    + b_fc;

    /* Gradients: same shape as weights (float32) */
    size_t total_grads = total_weights;

    /* Momentum buffers (SGD_M): same shape as weights */
    size_t total_momentum = total_weights;

    /* RigL masks: 1 uint8_t per weight element (NOT bias) */
    size_t total_masks = (size_t)(CONV1_K * INPUT_C * CONV1_F
                                + CONV2_K * CONV1_F * CONV2_F
                                + CONV3_K * CONV2_F * CONV3_F
                                + FC_IN   * NUM_CLS);

    /* ── Activations (per sample, forward pass VLA) ─────────────────
     * CalculateGradsSequential stores MODEL_SIZE+1 tensor pointers.
     * Each tensor holds BATCH_SIZE samples.                           */
    size_t act[13]; /* one per layer output */
    act[0]  = (size_t)BATCH_SIZE * INPUT_C          * INPUT_T        * 4; /* input     */
    act[1]  = (size_t)BATCH_SIZE * CONV1_F          * INPUT_T        * 4; /* conv1 out */
    act[2]  = act[1];                                                       /* relu1 out */
    act[3]  = (size_t)BATCH_SIZE * CONV1_F          * (INPUT_T/2)    * 4; /* maxpool1  */
    act[4]  = (size_t)BATCH_SIZE * CONV2_F          * (INPUT_T/2)    * 4; /* conv2 out */
    act[5]  = act[4];                                                       /* relu2 out */
    act[6]  = (size_t)BATCH_SIZE * CONV2_F          * (INPUT_T/4)    * 4; /* maxpool2  */
    act[7]  = (size_t)BATCH_SIZE * CONV3_F          * (INPUT_T/4)    * 4; /* conv3 out */
    act[8]  = act[7];                                                       /* relu3 out */
    act[9]  = (size_t)BATCH_SIZE * CONV3_F          * 1              * 4; /* avgpool   */
    act[10] = (size_t)BATCH_SIZE * FC_IN                             * 4; /* flatten   */
    act[11] = (size_t)BATCH_SIZE * NUM_CLS                           * 4; /* linear    */
    act[12] = act[11];                                                      /* softmax   */
    size_t total_acts = 0;
    for (int i = 0; i < 13; i++) total_acts += act[i];

    /* MaxPool argmax buffers: int32_t, same shape as pool output */
    size_t argmax1 = (size_t)BATCH_SIZE * CONV1_F * (INPUT_T/2) * 4;
    size_t argmax2 = (size_t)BATCH_SIZE * CONV2_F * (INPUT_T/4) * 4;

    size_t grand_total = total_weights + total_grads + total_momentum
                       + total_masks + total_acts + argmax1 + argmax2;

    printf("\n┌─────────────────────────────────────────────────────────────────┐\n");
    printf("│  Memory Breakdown  (theoretical, batch=%d)                      │\n", BATCH_SIZE);
    printf("├──────────────────────────────────────┬────────────┬─────────────┤\n");
    printf("│ Category                             │  Bytes     │   KB        │\n");
    printf("├──────────────────────────────────────┼────────────┼─────────────┤\n");
    printf("│ Weights  (params)                    │ %10zu │ %11.2f │\n", total_weights,   total_weights   / 1024.0);
    printf("│   Conv1 weights+bias                 │ %10zu │ %11.2f │\n", w_conv1+b_conv1, (w_conv1+b_conv1)/1024.0);
    printf("│   Conv2 weights+bias                 │ %10zu │ %11.2f │\n", w_conv2+b_conv2, (w_conv2+b_conv2)/1024.0);
    printf("│   Conv3 weights+bias                 │ %10zu │ %11.2f │\n", w_conv3+b_conv3, (w_conv3+b_conv3)/1024.0);
    printf("│   Linear weights+bias                │ %10zu │ %11.2f │\n", w_fc+b_fc,       (w_fc+b_fc)      /1024.0);
    printf("├──────────────────────────────────────┼────────────┼─────────────┤\n");
    printf("│ Gradients (float32, same as weights) │ %10zu │ %11.2f │\n", total_grads,     total_grads     / 1024.0);
    printf("│ Momentum buffers (SGD-M)             │ %10zu │ %11.2f │\n", total_momentum,  total_momentum  / 1024.0);
    printf("│ RigL masks (uint8_t)                 │ %10zu │ %11.2f │\n", total_masks,     total_masks     / 1024.0);
    printf("├──────────────────────────────────────┼────────────┼─────────────┤\n");
    printf("│ Activations (all layers, 1 batch)    │ %10zu │ %11.2f │\n", total_acts,      total_acts      / 1024.0);
    printf("│   Input  [B×%2d×%3d]                  │ %10zu │ %11.2f │\n", INPUT_C, INPUT_T,        act[0],  act[0] /1024.0);
    printf("│   Conv1  [B×%2d×%3d]                  │ %10zu │ %11.2f │\n", CONV1_F, INPUT_T,        act[1],  act[1] /1024.0);
    printf("│   Pool1  [B×%2d×%3d]                  │ %10zu │ %11.2f │\n", CONV1_F, INPUT_T/2,      act[3],  act[3] /1024.0);
    printf("│   Conv2  [B×%2d×%3d]                  │ %10zu │ %11.2f │\n", CONV2_F, INPUT_T/2,      act[4],  act[4] /1024.0);
    printf("│   Pool2  [B×%2d×%3d]                  │ %10zu │ %11.2f │\n", CONV2_F, INPUT_T/4,      act[6],  act[6] /1024.0);
    printf("│   Conv3  [B×%2d×%3d]                  │ %10zu │ %11.2f │\n", CONV3_F, INPUT_T/4,      act[7],  act[7] /1024.0);
    printf("│   FC/Out [B×%2d×  1]                  │ %10zu │ %11.2f │\n", FC_IN,             act[10], act[10]/1024.0);
    printf("│ MaxPool argmax buffers               │ %10zu │ %11.2f │\n", argmax1+argmax2, (argmax1+argmax2)/1024.0);
    printf("├──────────────────────────────────────┼────────────┼─────────────┤\n");
    printf("│ TOTAL (theoretical)                  │ %10zu │ %11.2f │\n", grand_total, grand_total / 1024.0);
    printf("│   (STM32 has 320 KB SRAM total)      │            │             │\n");
    printf("└──────────────────────────────────────┴────────────┴─────────────┘\n");
}

/* ═══════════════════════════════════════════════════════════════════
 *  main
 * ═══════════════════════════════════════════════════════════════════ */
int main(int argc, char *argv[])
{
    const char *dataDir = (argc >= 2)
        ? argv[1]
        : "examples/har_classifier/data";

    printf("\n");
    printf("╔═════════════════════════════════════════════════════════════════╗\n");
    printf("║  On-Device HAR Training: FQT + RigL                            ║\n");
    printf("║  Reference: Evci et al. \"Rigging the Lottery\", ICML 2020       ║\n");
    printf("╠═════════════════════════════════════════════════════════════════╣\n");
    printf("║  Dataset  : UCI-HAR  (%d classes, 128×9 input)                 ║\n", NUM_CLS);
    printf("║  Model    : 1D-CNN  (%d-%d-%d) → FC%d                         ║\n",
           CONV1_F, CONV2_F, CONV3_F, NUM_CLS);
    printf("║  Sparsity : %.0f%%  (target, uniform across layers)              ║\n",
           (double)(RIGL_SPARSITY * 100.f));
    printf("║  RigL ΔT  : every %d batches  |  frac=%.2f                    ║\n",
           RIGL_DELTA_T, (double)RIGL_FRAC);
    printf("║  Epochs   : %d   Batch: %d   LR: %.4f   Momentum: %.1f       ║\n",
           NUM_EPOCHS, BATCH_SIZE, (double)LR, (double)MOMENTUM);
    printf("╚═════════════════════════════════════════════════════════════════╝\n\n");

    printProcessMemory("startup (before data load)");
    mcuSimPrintStatus("startup");

    /* ── Load data ───────────────────────────────────────────────── */
    initDataSets(dataDir);
    printProcessMemory("after dataset load");
    mcuSimPrintStatus("after dataset load");
    size_t trainSamples = g_trainStream.n_samples;

    dataLoader_t *trainLoader =
        dataLoaderInit(getTrainSample, getTrainSize, BATCH_SIZE,
                       NULL, NULL, true, SHUFFLE_SEED, true);
    dataLoader_t *valLoader =
        dataLoaderInit(getValSample, getValSize, 1,
                       NULL, NULL, false, 0, true);
    dataLoader_t *testLoader =
        dataLoaderInit(getTestSample, getTestSize, 1,
                       NULL, NULL, false, 0, true);

    /* ── Build model ─────────────────────────────────────────────── */
    layerQuant_t lq;
    layerQuantInitUniform(&lq, quantizationInitFloat());
    layer_t *model[MODEL_SIZE];
    buildModel(model, &lq);

    /* ── Optimizer ───────────────────────────────────────────────── */
    optimizer_t *sgd = sgdMCreateOptim(LR, MOMENTUM, 0.0f,
                                       model, MODEL_SIZE, FLOAT32);

    lossConfig_t lossConfig = {
        .funcType          = CROSS_ENTROPY,
        .backwardReduction = REDUCTION_MEAN,
        .classWeights      = NULL,
    };

    printProcessMemory("after model + optimizer build");
    mcuSimPrintStatus("after model + optimizer");
    printMemoryBreakdown();

    /* ── RigL: initialise sparse masks ───────────────────────────── */
    printf("[rigl] Initialising masks (sparsity=%.0f%%)...\n",
           (double)(RIGL_SPARSITY * 100.f));
    riglInit(model);
    printModelSummary(model);
    printProcessMemory("after RigL mask init");
    mcuSimPrintStatus("after RigL masks");

    /* ── Activation stack cost (inference-only vs training) ─────────
     * CalculateGradsSequential allocates VLAs on the stack for all
     * (MODEL_SIZE+1) layer outputs at BATCH_SIZE.  This is extra RAM
     * on top of the heap tracked above.                              */
    {
        size_t act_per_sample =
            (size_t)(INPUT_T * INPUT_C)                  /* input        */
          + (size_t)(INPUT_T * CONV1_F)                  /* conv1 out    */
          + (size_t)(INPUT_T/2 * CONV1_F)                /* pool1 out    */
          + (size_t)(INPUT_T/2 * CONV1_F)                /* relu1        */
          + (size_t)(INPUT_T/2 * CONV2_F)                /* conv2 out    */
          + (size_t)(INPUT_T/4 * CONV2_F)                /* pool2 out    */
          + (size_t)(INPUT_T/4 * CONV2_F)                /* relu2        */
          + (size_t)(INPUT_T/4 * CONV3_F)                /* conv3 out    */
          + (size_t)(CONV3_F)                            /* avgpool out  */
          + (size_t)(CONV3_F)                            /* relu3        */
          + (size_t)(CONV3_F)                            /* flatten      */
          + (size_t)(NUM_CLS)                            /* linear out   */
          + (size_t)(NUM_CLS);                           /* softmax out  */
        size_t act_train_kb = act_per_sample * BATCH_SIZE * sizeof(float) / 1024;
        size_t act_infer_kb = act_per_sample * 1          * sizeof(float) / 1024;
        size_t heap_kb      = mcuSimGetTotal() / 1024;

        printf("\n┌─────────────────────────────────────────────────────┐\n");
        printf("│           MCU SRAM Budget (320 KB limit)            │\n");
        printf("├──────────────────────────────────┬──────────────────┤\n");
        printf("│ Component                        │ Size             │\n");
        printf("├──────────────────────────────────┼──────────────────┤\n");
        printf("│ Heap (weights+grads+momentum+cfg)│ %6zu KB        │\n", heap_kb);
        printf("│ Activations — inference (batch=1)│ %6zu KB        │\n", act_infer_kb);
        printf("│ Activations — training  (batch=%-2d)│ %6zu KB       │\n", BATCH_SIZE, act_train_kb);
        printf("├──────────────────────────────────┼──────────────────┤\n");
        printf("│ TOTAL (inference)                │ %6zu KB / 320  │\n", heap_kb + act_infer_kb);
        printf("│ TOTAL (training)                 │ %6zu KB / 320  │\n", heap_kb + act_train_kb);
        printf("└──────────────────────────────────┴──────────────────┘\n\n");
    }

    /* ── Pre-compute total RigL update steps for cosine decay ───────
     * batches_per_epoch = ceil(train_samples / BATCH_SIZE)
     * total_rigl_steps  = NUM_EPOCHS * batches_per_epoch / RIGL_DELTA_T */
    {
        size_t n_train     = g_trainStream.n_samples;
        size_t batches_per = (n_train + BATCH_SIZE - 1) / BATCH_SIZE;
        g_rigl_t_end = (int)((NUM_EPOCHS * batches_per) / RIGL_DELTA_T);
        if (g_rigl_t_end < 1) g_rigl_t_end = 1;
        printf("[RigL] Cosine decay: frac_0=%.2f  total_updates=%d\n\n",
               (double)RIGL_FRAC, g_rigl_t_end);
    }

    /* ── Training loop ───────────────────────────────────────────── */
    printf("%-6s  %-10s  %-10s  %-10s  %-8s  %-8s\n",
           "Epoch", "TrainLoss", "ValLoss", "ValAcc", "Wall(s)", "Frac");
    printf("──────  ──────────  ──────────  ──────────  ────────  ────────\n");

    size_t batchCounter = 0;
    struct timespec t0, t1;

    for (size_t epoch = 0; epoch < NUM_EPOCHS; epoch++) {
        clock_gettime(CLOCK_MONOTONIC, &t0);

        float trainLoss = trainingEpochRigL(model, MODEL_SIZE, lossConfig,
                                            trainLoader, sgd, &batchCounter);

        epochStats_t valStats =
            evaluationEpochWithMetrics(model, MODEL_SIZE, CROSS_ENTROPY,
                                       valLoader, inferenceWithLoss,
                                       REDUCTION_MEAN);

        clock_gettime(CLOCK_MONOTONIC, &t1);
        double wall = (double)(t1.tv_sec  - t0.tv_sec) +
                      (double)(t1.tv_nsec - t0.tv_nsec) * 1e-9;

        float cur_frac = riglDecayedFrac(g_rigl_step, g_rigl_t_end);
        printf("%-6zu  %-10.4f  %-10.4f  %-10.4f  %-8.2f  %-8.4f",
               epoch,
               (double)trainLoss,
               (double)valStats.loss,
               (double)valStats.accuracy,
               wall,
               (double)cur_frac);

        /* Print RSS inline every epoch — cheap call, one line */
        {
#ifdef __linux__
            FILE *mf = fopen("/proc/self/status", "r");
            long rss = 0;
            if (mf) {
                char ln[128];
                while (fgets(ln, sizeof(ln), mf))
                    if (strncmp(ln, "VmRSS:", 6) == 0) { sscanf(ln+6, "%ld", &rss); break; }
                fclose(mf);
            }
            printf("  mem=%ldKB", rss);
#endif
        }
        printf("\n");

        if ((epoch + 1) % 5 == 0)
            printSparsityTable(model);

        fflush(stdout);
    }

    printProcessMemory("after training loop");

    /* ── FLOPs report (using final mask state) ───────────────────── */
    printFLOPsReport(model, batchCounter, trainSamples);

    /* ── Final model summary (sparsity after training) ───────────── */
    printf("\n[Final sparsity after %zu epochs]\n", (size_t)NUM_EPOCHS);
    printModelSummary(model);

    /* ── Full test evaluation with classification report ─────────── */
    size_t cmBuffer[NUM_CLS * NUM_CLS];
    classificationReport_t rpt =
        evaluationEpochWithReport(model, MODEL_SIZE, CROSS_ENTROPY,
                                  testLoader, inferenceWithLoss,
                                  cmBuffer, NUM_CLS, REDUCTION_MEAN);

    printClassificationReport(&rpt);

    printf("\n╔═════════════════════════════════════════════════════════════════╗\n");
    printf("║  FINAL RESULTS                                                  ║\n");
    printf("╠═════════════════════════════════════════════════════════════════╣\n");
    printf("║  Test Accuracy  : %.4f  (%.2f%%)                               ║\n",
           (double)rpt.stats.accuracy,
           (double)(rpt.stats.accuracy * 100.f));
    printf("║  F1-Score       : %.4f                                         ║\n",
           (double)rpt.stats.f1);
    printf("║  Sparsity       : %.1f%%  (target %.0f%%)                        ║\n",
           (double)(100.f * (1.f - (float)(
               rigl_active_count(g_masks[0], (int)rigl_layer_size(model[RIGL_IDX[0]])) +
               rigl_active_count(g_masks[1], (int)rigl_layer_size(model[RIGL_IDX[1]])) +
               rigl_active_count(g_masks[2], (int)rigl_layer_size(model[RIGL_IDX[2]])) +
               rigl_active_count(g_masks[3], (int)rigl_layer_size(model[RIGL_IDX[3]]))
           ) / (float)(
               DENSE_PARAMS[0]+DENSE_PARAMS[1]+DENSE_PARAMS[2]+DENSE_PARAMS[3]
           ))),
           (double)(RIGL_SPARSITY * 100.f));
    printf("╚═════════════════════════════════════════════════════════════════╝\n\n");

    return 0;
}
