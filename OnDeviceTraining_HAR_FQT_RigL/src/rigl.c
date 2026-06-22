/* rigl.c — RigL sparse training implementation
 *
 * Primitive API: pure C, no OnDeviceTraining dependencies.
 * Framework layer API: bridges to layer_t / parameter_t; compiled only
 *   when RIGL_USE_FRAMEWORK is defined (set by CMakeLists_PC.txt).
 */

#include "rigl.h"
#include <string.h>

/* ── Simple PRNG (xorshift32) ────────────────────────────────────── */

static uint32_t rng_state = 12345;

static uint32_t xorshift32(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return rng_state;
}

/* ── Helpers ─────────────────────────────────────────────────────── */

static inline float fabs_local(float x) { return x < 0.0f ? -x : x; }

/* Partial selection: find the k-th smallest value in arr[0..n-1]
 * using a simple linear scan for the threshold.
 * Returns the threshold value (values <= threshold are "small").
 *
 * For small arrays on Cortex-M0+ a simple O(k*n) approach is fine.
 */
static float kth_smallest_abs(const float *arr, const uint8_t *mask,
                               int n, int k, int want_active)
{
    /* want_active=1 → look at active weights (mask==1)
     * want_active=0 → look at pruned weights (mask==0)         */
    if (k <= 0) return -1.0f;

    /* collect |values| into a scratch pass; use insertion-sort top-k */
    float threshold = 1e38f;
    int   found     = 0;

    /* We do k passes over the array to find the k smallest. */
    float prev_min = -1.0f;
    for (int pass = 0; pass < k; pass++) {
        float cur_min = 1e38f;
        for (int i = 0; i < n; i++) {
            if (want_active && !mask[i]) continue;
            if (!want_active && mask[i]) continue;
            float v = fabs_local(arr[i]);
            if (v > prev_min && v < cur_min)
                cur_min = v;
        }
        if (cur_min >= 1e38f) break;
        threshold = cur_min;
        prev_min  = cur_min;
        found++;
    }
    (void)found;
    return threshold;
}

/* ── Mask initialisation ─────────────────────────────────────────── */

void rigl_init_mask(uint8_t *mask, int size, float sparsity, uint32_t seed)
{
    rng_state = (seed == 0) ? 12345 : seed;

    int n_prune = (int)(sparsity * (float)size + 0.5f);

    /* Start with all active */
    memset(mask, 1, (size_t)size);

    /* Fisher-Yates partial shuffle to choose n_prune positions to prune */
    /* Use index array trick: track remaining candidates inline */
    /* For memory efficiency on Pico, use a simple repeated-random approach */
    int pruned = 0;
    int attempts = 0;
    while (pruned < n_prune && attempts < size * 4) {
        int idx = (int)(xorshift32() % (uint32_t)size);
        if (mask[idx] == 1) {
            mask[idx] = 0;
            pruned++;
        }
        attempts++;
    }
    /* Fallback: if random didn't converge, prune sequentially */
    for (int i = 0; pruned < n_prune && i < size; i++) {
        if (mask[i] == 1) {
            mask[i] = 0;
            pruned++;
        }
    }
}

/* ── Apply mask ──────────────────────────────────────────────────── */

void rigl_apply_mask(float *weights, const uint8_t *mask, int size)
{
    for (int i = 0; i < size; i++)
        if (!mask[i]) weights[i] = 0.0f;
}

/* ── Prune-and-Regrow step ───────────────────────────────────────── */
/*
 * Algorithm:
 *  1. Count active (mask==1) weights → n_active.
 *  2. k = round(frac * n_active)  — number to cycle.
 *  3. PRUNE  : set mask=0 for k active weights with smallest |weight|.
 *  4. REGROW : set mask=1 for k pruned weights with largest  |grad|.
 *
 * The target sparsity is maintained approximately; exact sparsity is
 * enforced by rigl_actual_sparsity() monitoring in the training loop.
 */
void rigl_step(const float *weights, const float *grads,
               uint8_t *mask, int size,
               float sparsity, float frac)
{
    int n_active = rigl_active_count(mask, size);
    int k = (int)(frac * (float)n_active + 0.5f);
    if (k < 1) k = 1;

    /* ── PRUNE: k smallest |weight| among active ─────────────────── */
    /* We sweep k times; each sweep finds and zeroes the current minimum */
    for (int pass = 0; pass < k; pass++) {
        float min_val = 1e38f;
        int   min_idx = -1;
        for (int i = 0; i < size; i++) {
            if (!mask[i]) continue;
            float v = fabs_local(weights[i]);
            if (v < min_val) { min_val = v; min_idx = i; }
        }
        if (min_idx < 0) break;
        mask[min_idx] = 0;
    }

    /* ── REGROW: k largest |grad| among pruned ───────────────────── */
    for (int pass = 0; pass < k; pass++) {
        float max_val = -1.0f;
        int   max_idx = -1;
        for (int i = 0; i < size; i++) {
            if (mask[i]) continue;  /* already active */
            float v = fabs_local(grads[i]);
            if (v > max_val) { max_val = v; max_idx = i; }
        }
        if (max_idx < 0) break;
        mask[max_idx] = 1;
        /* Newly regrown weights start at zero — will grow via gradient */
        /* (weights array is not modified here; caller owns that) */
    }

    (void)sparsity; /* target sparsity used for init only in this impl */
}

/* ── Diagnostics ─────────────────────────────────────────────────── */

float rigl_actual_sparsity(const uint8_t *mask, int size)
{
    int zeros = 0;
    for (int i = 0; i < size; i++)
        if (!mask[i]) zeros++;
    return (float)zeros / (float)size;
}

int rigl_active_count(const uint8_t *mask, int size)
{
    int cnt = 0;
    for (int i = 0; i < size; i++)
        if (mask[i]) cnt++;
    return cnt;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Framework layer API — OnDeviceTraining integration
 *
 *  Access pattern (FLOAT32 layerQuant):
 *    conv1dConfig_t *c = layer->config->conv1d;
 *    float *w = (float *)c->weights->param->data;
 *    float *g = (float *)c->weights->grad->data;
 *    size_t n = calcNumberOfElementsByParameter(c->weights);
 * ═══════════════════════════════════════════════════════════════════ */

#include "Conv1d.h"   /* conv1dConfig_t  */
#include "Linear.h"   /* linearConfig_t  */
#include "Tensor.h"   /* calcNumberOfElementsByParameter */

size_t rigl_layer_size(layer_t *layer)
{
    if (layer->type == CONV1D)
        return calcNumberOfElementsByParameter(layer->config->conv1d->weights);
    if (layer->type == LINEAR)
        return calcNumberOfElementsByParameter(layer->config->linear->weights);
    return 0;
}

static float *layer_weights(layer_t *layer)
{
    if (layer->type == CONV1D)
        return (float *)layer->config->conv1d->weights->param->data;
    if (layer->type == LINEAR)
        return (float *)layer->config->linear->weights->param->data;
    return NULL;
}

static float *layer_grads(layer_t *layer)
{
    if (layer->type == CONV1D)
        return (float *)layer->config->conv1d->weights->grad->data;
    if (layer->type == LINEAR)
        return (float *)layer->config->linear->weights->grad->data;
    return NULL;
}

void rigl_init_from_layer(layer_t *layer, uint8_t *mask,
                          float sparsity, uint32_t seed)
{
    size_t n = rigl_layer_size(layer);
    if (n == 0) return;
    rigl_init_mask(mask, (int)n, sparsity, seed);
}

void rigl_apply_to_layer(layer_t *layer, const uint8_t *mask)
{
    float *w = layer_weights(layer);
    size_t n = rigl_layer_size(layer);
    if (w && n > 0)
        rigl_apply_mask(w, mask, (int)n);
}

void rigl_step_layer(layer_t *layer, uint8_t *mask,
                     float sparsity, float frac)
{
    float  *w = layer_weights(layer);
    float  *g = layer_grads(layer);
    size_t  n = rigl_layer_size(layer);
    if (w && g && n > 0)
        rigl_step(w, g, mask, (int)n, sparsity, frac);
}
