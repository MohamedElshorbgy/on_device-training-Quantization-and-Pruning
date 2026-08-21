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
 * RigL drop-and-grow (Evci et al., ICML 2020):
 *
 *   k = floor(frac × n_active)   — connections to cycle this step
 *
 *   DROP  : remove k active connections with smallest |weight|
 *           → these have least impact on output (weight magnitude criterion)
 *
 *   GROW  : add k pruned connections with largest |gradient|
 *           → these have most potential to reduce loss (gradient criterion)
 *           → newly grown weights keep value 0; gradient will push them away
 *
 * Implementation uses a single-pass threshold scan (O(n)) instead of
 * k separate passes (O(k×n)), making it practical for large layers.
 *
 * Step 1 — find the k-th smallest |weight| among active weights
 *           (drop threshold)
 * Step 2 — find the k-th largest  |grad|  among pruned weights
 *           (grow threshold)
 * Step 3 — apply both thresholds in one final pass
 */
void rigl_step(const float *weights, const float *grads,
               uint8_t *mask, int size,
               float sparsity, float frac)
{
    int n_active = rigl_active_count(mask, size);
    int k = (int)(frac * (float)n_active);   /* floor — paper formula */
    if (k < 1) { (void)sparsity; return; }   /* nothing to cycle      */

    /* ── Step 1: DROP threshold — k-th smallest |weight| among active
     *
     * Single pass: collect all |weight| values for active weights,
     * then find the k-th smallest using a simple selection.
     * We use an insertion-based running top-k buffer of size k.      */
    float drop_thresh = 0.0f;
    {
        /* Find k-th smallest |w| with one linear scan using a max-heap
         * of size k (kept as an unsorted array for simplicity — k is
         * usually small, e.g. 20% of a few thousand weights).         */
        float heap[k];   /* VLA — holds the k smallest values seen so far */
        int   heap_sz = 0;
        float heap_max = 0.0f;
        int   heap_max_i = 0;

        for (int i = 0; i < size; i++) {
            if (!mask[i]) continue;
            float v = fabs_local(weights[i]);
            if (heap_sz < k) {
                heap[heap_sz] = v;
                if (v > heap_max) { heap_max = v; heap_max_i = heap_sz; }
                heap_sz++;
            } else if (v < heap_max) {
                heap[heap_max_i] = v;
                /* recompute max */
                heap_max = heap[0]; heap_max_i = 0;
                for (int j = 1; j < k; j++)
                    if (heap[j] > heap_max) { heap_max = heap[j]; heap_max_i = j; }
            }
        }
        drop_thresh = heap_max;   /* k-th smallest = largest in the heap */
    }

    /* ── Step 2: GROW threshold — k-th largest |grad| among pruned   */
    float grow_thresh = 0.0f;
    {
        /* Find k-th largest |grad| → equivalent to k-th smallest of negated.
         * Use a min-heap of size k (holds the k largest values).      */
        float heap[k];
        int   heap_sz = 0;
        float heap_min = 0.0f;
        int   heap_min_i = 0;

        for (int i = 0; i < size; i++) {
            if (mask[i]) continue;   /* only pruned candidates */
            float v = fabs_local(grads[i]);
            if (heap_sz < k) {
                heap[heap_sz] = v;
                if (heap_sz == 0 || v < heap_min) { heap_min = v; heap_min_i = heap_sz; }
                heap_sz++;
            } else if (v > heap_min) {
                heap[heap_min_i] = v;
                heap_min = heap[0]; heap_min_i = 0;
                for (int j = 1; j < k; j++)
                    if (heap[j] < heap_min) { heap_min = heap[j]; heap_min_i = j; }
            }
        }
        grow_thresh = heap_min;   /* k-th largest = smallest in the heap */
    }

    /* ── Step 3: apply drop and grow in a single final pass          */
    int dropped = 0, grown = 0;
    for (int i = 0; i < size; i++) {
        if (mask[i] && dropped < k) {
            if (fabs_local(weights[i]) <= drop_thresh) {
                mask[i] = 0;
                dropped++;
            }
        } else if (!mask[i] && grown < k) {
            if (fabs_local(grads[i]) >= grow_thresh) {
                mask[i] = 1;
                /* weight stays 0 — gradient will grow it from scratch */
                grown++;
            }
        }
    }

    (void)sparsity;
}

/* ── ERK sparsity distribution ───────────────────────────────────── */
/*
 * ERK score for layer i:
 *   Conv1d : (n_in + n_out + kernel) / (n_in * n_out * kernel)
 *   Linear : (n_in + n_out)          / (n_in * n_out)
 *
 * Scale factor s is chosen so:
 *   sum_i( s * score_i * sizes_i ) = total_params * (1 - global_sp)
 *   => s = total_nonzero / sum_i(score_i * sizes_i)
 *
 * Per-layer sparsity:
 *   sp_i = 1 - clamp(s * score_i, 0.01, 1.0)
 */
void rigl_erk_sparsities(const rigl_layer_info_t *info,
                         const int *sizes,
                         int n_layers,
                         float global_sp,
                         float *out_sp)
{
    /* Step 1 — compute raw ERK scores */
    float scores[n_layers];
    for (int i = 0; i < n_layers; i++) {
        float num, den;
        if (info[i].is_conv) {
            num = (float)(info[i].n_in + info[i].n_out + info[i].kernel);
            den = (float)(info[i].n_in * info[i].n_out * info[i].kernel);
        } else {
            num = (float)(info[i].n_in + info[i].n_out);
            den = (float)(info[i].n_in * info[i].n_out);
        }
        scores[i] = (den > 0.0f) ? (num / den) : 1.0f;
    }

    /* Step 2 — total params and target non-zero count */
    int total_params = 0;
    for (int i = 0; i < n_layers; i++) total_params += sizes[i];
    float target_nonzero = (float)total_params * (1.0f - global_sp);

    /* Step 3 — compute scale s */
    float score_sum = 0.0f;
    for (int i = 0; i < n_layers; i++)
        score_sum += scores[i] * (float)sizes[i];
    float s = (score_sum > 0.0f) ? (target_nonzero / score_sum) : 1.0f;

    /* Step 4 — per-layer sparsity = 1 - clamp(s * score, 0.01, 1.0) */
    for (int i = 0; i < n_layers; i++) {
        float density = s * scores[i];
        if (density < 0.01f) density = 0.01f;
        if (density > 1.00f) density = 1.00f;
        out_sp[i] = 1.0f - density;
    }
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
