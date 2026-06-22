/* dataset.c — UCI-HAR data loading and normalisation
 *
 * UART protocol (binary, little-endian):
 *   Host → Pico:  [uint8 label] [float32 × INPUT_T × INPUT_C]
 *   Pico → Host:  [uint8 step_echo] [float32 loss] [float32 acc]
 *
 * Embedded test set: populated by tools/prepare_data.py.
 * If not generated, DATASET_TEST_N = 0 and the arrays are empty stubs.
 */

#include "dataset.h"
#include <string.h>
#include <stdio.h>

/* Pico SDK UART / stdio */
#ifdef PICO_BUILD
#include "pico/stdlib.h"
#endif

/* ── Per-channel normalisation stats ─────────────────────────────── */
/* Pre-computed from UCI-HAR training split (9 channels):
 * Order: body-acc-X/Y/Z, body-gyro-X/Y/Z, total-acc-X/Y/Z
 * Values from paper / dataset readme (approximate).                  */
static const float CH_MEAN[INPUT_C] = {
     0.0000f,  0.0000f,  0.0000f,   /* body acc  (already zero-mean) */
     0.0000f,  0.0000f,  0.0000f,   /* body gyro                     */
     0.0136f,  0.0064f,  0.0125f    /* total acc                     */
};
static const float CH_STD[INPUT_C] = {
     0.1140f,  0.0783f,  0.1024f,
     0.1600f,  0.1050f,  0.0862f,
     0.5715f,  0.5733f,  0.4012f
};

/* ── UART helpers (Pico only) ────────────────────────────────────── */
#ifdef PICO_BUILD

static int read_exact(uint8_t *buf, int n)
{
    for (int i = 0; i < n; i++) {
        int c = getchar_timeout_us(500000);
        if (c == PICO_ERROR_TIMEOUT) return 0;
        buf[i] = (uint8_t)c;
    }
    return 1;
}

static void write_exact(const uint8_t *buf, int n)
{
    for (int i = 0; i < n; i++)
        putchar_raw(buf[i]);
}

int dataset_uart_recv(float *sample_out, int *label_out)
{
    uint8_t lbl;
    if (!read_exact(&lbl, 1)) return 0;
    if (lbl >= NUM_CLS) return 0;
    *label_out = (int)lbl;
    int n_bytes = INPUT_T * INPUT_C * (int)sizeof(float);
    if (!read_exact((uint8_t *)sample_out, n_bytes)) return 0;
    dataset_normalize(sample_out);
    return 1;
}

void dataset_uart_send(int step, float loss, float acc)
{
    uint8_t buf[9];
    buf[0] = (uint8_t)(step & 0xFF);
    memcpy(buf + 1, &loss, 4);
    memcpy(buf + 5, &acc,  4);
    write_exact(buf, 9);
}

#endif /* PICO_BUILD */

/* ── Normalisation ───────────────────────────────────────────────── */

void dataset_normalize(float *sample)
{
    /* Z-score per channel over the window */
    for (int c = 0; c < INPUT_C; c++) {
        float inv_std = 1.0f / (CH_STD[c] + 1e-8f);
        for (int t = 0; t < INPUT_T; t++) {
            float *v = &sample[t * INPUT_C + c];
            *v = (*v - CH_MEAN[c]) * inv_std;
            /* Clamp to [-3, 3] (≈ 3σ) so INT8 quantisation stays valid */
            if (*v >  3.0f) *v =  3.0f;
            if (*v < -3.0f) *v = -3.0f;
        }
    }
}

/* ── Class names ─────────────────────────────────────────────────── */

static const char *CLASS_NAMES[NUM_CLS] = {
    "WALKING", "WALKING_UPSTAIRS", "WALKING_DOWNSTAIRS",
    "SITTING", "STANDING", "LAYING"
};

const char *dataset_class_name(int label)
{
    if (label < 0 || label >= NUM_CLS) return "UNKNOWN";
    return CLASS_NAMES[label];
}

/* ── Embedded test set ───────────────────────────────────────────── */
/*
 * This section is populated by tools/prepare_data.py.
 * Until that script is run, DATASET_TEST_N = 0 (stub mode).
 *
 * To generate:
 *   python3 tools/prepare_data.py --ucihar-dir /path/to/UCI\ HAR\ Dataset \
 *                                  --n-per-class 10
 * which overwrites the arrays below with real normalised samples.
 */

/* ── BEGIN auto-generated test data (replace with prepare_data.py output) ── */
const int DATASET_TEST_N = 0;
const float DATASET_TEST_X[1][INPUT_T * INPUT_C] = {{ 0 }};  /* placeholder */
const uint8_t DATASET_TEST_Y[1] = { 0 };                      /* placeholder */
/* ── END auto-generated test data ────────────────────────────────────────── */

/* ── PC .npy dataset loader ───────────────────────────────────────── */
/*
 * Reads the pre-processed .npy files produced by:
 *   python examples/har_classifier/prepare_data.py
 * (run once from the OnDeviceTraining project root)
 *
 * File shapes:
 *   {split}_x.npy : float32 [N, 9, 128]  — channels-first
 *   {split}_y.npy : int32   [N]           — labels 0..5
 *
 * We transpose X to [N, 128, 9] (channels-last) to match our model.
 */
#ifndef PICO_BUILD

#include <stdlib.h>
#include <time.h>

/* ── Minimal NPY v1.0 / v2.0 reader ─────────────────────────────── */
/*
 * NPY format:
 *   magic   : 6 bytes  \x93NUMPY
 *   major   : 1 byte
 *   minor   : 1 byte
 *   hdr_len : 2 bytes (v1) or 4 bytes (v2), little-endian uint
 *   header  : hdr_len bytes — Python dict as ASCII string
 *   data    : raw little-endian binary
 *
 * We parse the 'shape' tuple and 'descr' from the header string,
 * then read hdr_len bytes and interpret as packed binary.
 */

/* Parse a decimal integer from *p, advance *p past it. */
static size_t parse_uint(const char *p, const char **end)
{
    while (*p == ' ' || *p == ',') p++;
    size_t v = 0;
    while (*p >= '0' && *p <= '9') { v = v * 10 + (size_t)(*p - '0'); p++; }
    if (end) *end = p;
    return v;
}

/* Load an NPY file.  Returns malloc'd data buffer and fills *out_N,
 * *out_elems_per_row (product of dims[1..]).
 * dtype must be '<f4' (float32) or '<i4' (int32).
 * Returns NULL on error.                                              */
static void *npy_load(const char *path,
                      size_t *out_N,
                      size_t *out_elems_per_row,
                      int    *out_is_float)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "[npy] Cannot open: %s\n", path);
        return NULL;
    }

    /* --- Magic + version --- */
    uint8_t magic[6];
    uint8_t major, minor;
    if (fread(magic, 1, 6, f) != 6 || fread(&major, 1, 1, f) != 1
        || fread(&minor, 1, 1, f) != 1) {
        fprintf(stderr, "[npy] Short read on magic: %s\n", path);
        fclose(f); return NULL;
    }
    (void)minor;

    /* --- Header length --- */
    size_t hdr_len;
    if (major == 1) {
        uint8_t hl[2];
        if (fread(hl, 1, 2, f) != 2) { fclose(f); return NULL; }
        hdr_len = (size_t)hl[0] | ((size_t)hl[1] << 8);
    } else {
        uint8_t hl[4];
        if (fread(hl, 1, 4, f) != 4) { fclose(f); return NULL; }
        hdr_len = (size_t)hl[0] | ((size_t)hl[1]<<8)
                | ((size_t)hl[2]<<16) | ((size_t)hl[3]<<24);
    }

    /* --- Header string --- */
    char *hdr = (char *)malloc(hdr_len + 1);
    if (!hdr) { fclose(f); return NULL; }
    if (fread(hdr, 1, hdr_len, f) != hdr_len) {
        free(hdr); fclose(f); return NULL;
    }
    hdr[hdr_len] = '\0';

    /* Detect dtype */
    int is_float = (strstr(hdr, "'<f4'") || strstr(hdr, "\"<f4\"")
                    || strstr(hdr, "float32"));
    if (out_is_float) *out_is_float = is_float;

    /* Parse shape tuple: find "shape': (" then read comma-sep integers */
    const char *sp = strstr(hdr, "'shape'");
    if (!sp) sp = strstr(hdr, "\"shape\"");
    if (!sp) { fprintf(stderr, "[npy] No shape in header: %s\n", path);
               free(hdr); fclose(f); return NULL; }
    sp = strchr(sp, '(');
    if (!sp) { free(hdr); fclose(f); return NULL; }
    sp++; /* skip '(' */

    size_t dims[8]; int ndim = 0;
    while (*sp && *sp != ')' && ndim < 8) {
        while (*sp == ' ') sp++;
        if (*sp == ')') break;
        dims[ndim++] = parse_uint(sp, &sp);
        while (*sp == ' ' || *sp == ',') sp++;
    }
    free(hdr);

    if (ndim < 1) { fclose(f); return NULL; }
    size_t N = dims[0];
    size_t row = 1;
    for (int d = 1; d < ndim; d++) row *= dims[d];

    size_t elem_sz = 4; /* float32 or int32 */
    size_t total   = N * row;

    void *buf = malloc(total * elem_sz);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, elem_sz, total, f) != total) {
        fprintf(stderr, "[npy] Short read on data: %s (wanted %zu elems)\n",
                path, total);
        free(buf); fclose(f); return NULL;
    }
    fclose(f);

    *out_N            = N;
    *out_elems_per_row = row;
    return buf;
}

/* ── pc_dataset_load ─────────────────────────────────────────────── */
/*
 * data_dir : path to the folder containing {split}_x.npy, {split}_y.npy
 *            e.g. "../OnDeviceTraining/examples/har_classifier/data"
 * split    : "train", "val", or "test"
 *
 * X.npy shape : [N, 9, 128]  channels-first → we transpose to [N, 128, 9]
 * y.npy shape : [N]          int32, labels already 0-based
 */
int pc_dataset_load(PC_Dataset *ds, const char *data_dir, const char *split)
{
    char xpath[512], ypath[512];
    snprintf(xpath, sizeof(xpath), "%s/%s_x.npy", data_dir, split);
    snprintf(ypath, sizeof(ypath), "%s/%s_y.npy", data_dir, split);

    /* ── Load X ────────────────────────────────────────────────── */
    size_t N, row; int is_float;
    float *raw_x = (float *)npy_load(xpath, &N, &row, &is_float);
    if (!raw_x) return 0;
    if (!is_float || row != (size_t)(INPUT_C * INPUT_T)) {
        fprintf(stderr,
            "[dataset] Unexpected X shape in %s (row=%zu, expected %d)\n",
            xpath, row, INPUT_C * INPUT_T);
        free(raw_x); return 0;
    }

    /* ── Load y ────────────────────────────────────────────────── */
    size_t Ny, ry; int yf;
    int32_t *raw_y = (int32_t *)npy_load(ypath, &Ny, &ry, &yf);
    if (!raw_y) { free(raw_x); return 0; }
    if (Ny != N) {
        fprintf(stderr, "[dataset] X/y size mismatch (%zu vs %zu)\n", N, Ny);
        free(raw_x); free(raw_y); return 0;
    }

    /* ── Allocate dataset ──────────────────────────────────────── */
    ds->N      = (int)N;
    ds->cursor = 0;
    ds->X = (float   *)malloc(N * INPUT_T * INPUT_C * sizeof(float));
    ds->y = (uint8_t *)malloc(N * sizeof(uint8_t));
    if (!ds->X || !ds->y) {
        fprintf(stderr, "[dataset] OOM\n");
        free(raw_x); free(raw_y); return 0;
    }

    /* ── Transpose [N, 9, 128] → [N, 128, 9] ─────────────────── */
    for (size_t i = 0; i < N; i++) {
        for (int c = 0; c < INPUT_C; c++) {
            for (int t = 0; t < INPUT_T; t++) {
                /* src: [i][c][t] in row-major [N][9][128] */
                float v = raw_x[i * INPUT_C * INPUT_T + c * INPUT_T + t];
                /* dst: [i][t][c] in row-major [N][128][9] */
                ds->X[i * INPUT_T * INPUT_C + t * INPUT_C + c] = v;
            }
        }
        ds->y[i] = (uint8_t)raw_y[i];   /* already 0-based from prepare_data.py */
    }

    free(raw_x);
    free(raw_y);

    printf("[dataset] %-5s split: %d samples  (X=[%d,%d,%d]→[%d,%d,%d])\n",
           split, (int)N,
           (int)N, INPUT_C, INPUT_T,
           (int)N, INPUT_T, INPUT_C);
    return 1;
}

/* ── pc_dataset_free ─────────────────────────────────────────────── */

void pc_dataset_free(PC_Dataset *ds)
{
    free(ds->X); ds->X = NULL;
    free(ds->y); ds->y = NULL;
    ds->N = ds->cursor = 0;
}

/* ── pc_dataset_next ─────────────────────────────────────────────── */

void pc_dataset_next(PC_Dataset *ds, float *sample_out, int *label_out)
{
    int idx = ds->cursor % ds->N;
    float *src = ds->X + (size_t)idx * INPUT_T * INPUT_C;
    memcpy(sample_out, src, INPUT_T * INPUT_C * sizeof(float));
    dataset_normalize(sample_out);
    *label_out = (int)ds->y[idx];
    ds->cursor++;
}

/* ── pc_dataset_shuffle ──────────────────────────────────────────── */

void pc_dataset_shuffle(PC_Dataset *ds)
{
    srand((unsigned)time(NULL));
    int row_sz = INPUT_T * INPUT_C;
    float *tmp = (float *)malloc((size_t)row_sz * sizeof(float));
    if (!tmp) return;
    for (int i = ds->N - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        if (i == j) continue;
        memcpy(tmp,
               ds->X + (size_t)i * row_sz, (size_t)row_sz * sizeof(float));
        memcpy(ds->X + (size_t)i * row_sz,
               ds->X + (size_t)j * row_sz, (size_t)row_sz * sizeof(float));
        memcpy(ds->X + (size_t)j * row_sz,
               tmp,                          (size_t)row_sz * sizeof(float));
        uint8_t ty = ds->y[i]; ds->y[i] = ds->y[j]; ds->y[j] = ty;
    }
    free(tmp);
}

#endif /* !PICO_BUILD */
