/*
 * MinMax_rigl.c - K-selection helpers for RigL.
 *
 * Extracted from ODT_Complete_Reference_v2.pdf sections 7.4 and 39.2-39.3.
 * Add these two functions to MinMax.c (declarations in MinMax.h or RigL.h).
 *
 * TWO IMPLEMENTATIONS are provided:
 *
 *   RIGL_EXACT_KSELECT   the source's partial selection sort. Exact, but
 *                        allocates count*4 bytes on the heap - up to 259 KB
 *                        for the inactive side of a 1152x64 layer, on a
 *                        320 KB device. This is defect D8.
 *
 *   (default)            a histogram threshold: O(n) time, ~512 bytes of
 *                        stack, no allocation. The threshold is approximate
 *                        to within one bin width, which is harmless - the
 *                        decision is remade every 100 steps.
 *
 * Build with -DRIGL_EXACT_KSELECT to get the source's version verbatim.
 */
#define SOURCE_FILE "MINMAX"

#include "Common.h"
#include "Tensor.h"
#include <math.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef RIGL_EXACT_KSELECT
/* ------------------------------------------------------------------------
 * Exact variant - the source's code, verbatim apart from returning an error
 * instead of calling exit(1) on allocation failure.
 * ---------------------------------------------------------------------- */

float findAbsKthSmallestActive(tensor_t *weights, tensor_t *mask, size_t K)
{
    const size_t n = calcNumberOfElementsByTensor(weights);
    const float *w = (const float *)weights->data;

    size_t count = 0;
    for (size_t i = 0; i < n; i++)
        if (tensorBoolGet(mask, i)) count++;

    if (K >= count) return 1e38f;               /* keep all */

    float *vals = (float *)malloc(count * sizeof(float));
    if (!vals) {
        PRINT_ERROR("findAbsKthSmallestActive: malloc(%zu) failed",
                    count * sizeof(float));
        return 0.0f;                            /* drop nothing */
    }

    size_t idx = 0;
    for (size_t i = 0; i < n; i++)
        if (tensorBoolGet(mask, i)) vals[idx++] = fabsf(w[i]);

    for (size_t i = 0; i <= K && i < count; i++) {
        size_t minIdx = i;
        for (size_t j = i + 1; j < count; j++)
            if (vals[j] < vals[minIdx]) minIdx = j;
        const float tmp = vals[i];
        vals[i] = vals[minIdx];
        vals[minIdx] = tmp;
    }

    const float thresh = vals[K < count ? K : count - 1];
    free(vals);
    return thresh;
}

float findAbsKthLargestInactive(tensor_t *grads, tensor_t *mask, size_t K)
{
    const size_t n = calcNumberOfElementsByTensor(grads);
    const float *g = (const float *)grads->data;

    size_t count = 0;
    for (size_t i = 0; i < n; i++)
        if (!tensorBoolGet(mask, i)) count++;

    if (K >= count) return 0.0f;                /* grow all */

    float *vals = (float *)malloc(count * sizeof(float));
    if (!vals) {
        PRINT_ERROR("findAbsKthLargestInactive: malloc(%zu) failed",
                    count * sizeof(float));
        return 1e38f;                           /* grow nothing */
    }

    size_t idx = 0;
    for (size_t i = 0; i < n; i++)
        if (!tensorBoolGet(mask, i)) vals[idx++] = fabsf(g[i]);

    for (size_t i = 0; i <= K && i < count; i++) {
        size_t maxIdx = i;
        for (size_t j = i + 1; j < count; j++)
            if (vals[j] > vals[maxIdx]) maxIdx = j;
        const float tmp = vals[i];
        vals[i] = vals[maxIdx];
        vals[maxIdx] = tmp;
    }

    const float thresh = vals[K < count ? K : count - 1];
    free(vals);
    return thresh;
}

#else
/* ------------------------------------------------------------------------
 * Histogram variant - fixed memory, no allocation. Resolves defect D8.
 * ---------------------------------------------------------------------- */

#define RIGL_NBINS 256

/* active = true  -> K-th SMALLEST |value| among mask==1 positions
 * active = false -> K-th LARGEST  |value| among mask==0 positions */
static float kthByHistogram(const float *v, tensor_t *mask, size_t n,
                            size_t K, bool active)
{
    uint32_t hist[RIGL_NBINS];
    for (int b = 0; b < RIGL_NBINS; b++) hist[b] = 0;

    /* Pass 1: range and population of the selected set. */
    float vmax = 0.0f;
    size_t count = 0;
    for (size_t i = 0; i < n; i++) {
        if (tensorBoolGet(mask, i) != active) continue;
        const float a = fabsf(v[i]);
        if (a > vmax) vmax = a;
        count++;
    }

    /* No candidates: return the threshold that selects nothing. For the
     * active/DROP side that is 0 (nothing has |w| < 0); for the inactive/GROW
     * side it is +inf (nothing has |g| > inf). */
    if (count == 0)  return active ? 0.0f : 1e38f;
    if (K >= count)  return active ? 1e38f : 0.0f;    /* select all */
    if (vmax <= 0.0f) return 0.0f;                    /* all values zero */

    /* Pass 2: bin the magnitudes. */
    const float scale = (float)(RIGL_NBINS - 1) / vmax;
    for (size_t i = 0; i < n; i++) {
        if (tensorBoolGet(mask, i) != active) continue;
        size_t b = (size_t)(fabsf(v[i]) * scale);
        if (b >= RIGL_NBINS) b = RIGL_NBINS - 1;
        hist[b]++;
    }

    /* Pass 3: walk the histogram until K elements are accounted for. */
    size_t acc = 0;
    if (active) {
        for (int b = 0; b < RIGL_NBINS; b++) {        /* ascending */
            acc += hist[b];
            if (acc >= K) return (float)(b + 1) / scale;
        }
        return 1e38f;
    }
    for (int b = RIGL_NBINS - 1; b >= 0; b--) {       /* descending */
        acc += hist[b];
        /* Half a bin BELOW the lower edge, so that every value in bin b
         * satisfies the strict `> thresh` test used by the GROW step - the
         * largest element can sit exactly on the lower edge of the top bin. */
        if (acc >= K) return ((float)b - 0.5f) / scale;
    }
    return 0.0f;
}

float findAbsKthSmallestActive(tensor_t *weights, tensor_t *mask, size_t K)
{
    return kthByHistogram((const float *)weights->data, mask,
                          calcNumberOfElementsByTensor(weights), K, true);
}

float findAbsKthLargestInactive(tensor_t *grads, tensor_t *mask, size_t K)
{
    return kthByHistogram((const float *)grads->data, mask,
                          calcNumberOfElementsByTensor(grads), K, false);
}

#endif /* RIGL_EXACT_KSELECT */
