/*
 * RigL.c - the RigL mask update.
 *
 * Consolidated from ODT_Complete_Reference_v2.pdf section 39.7, with the
 * DROP/GROW logic cross-checked against sections 2.2 and 33.4.
 *
 * Three defects from the source are fixed here and marked FIX D1/D2/D9.
 * Defect D8 (malloc in the K-selection helpers) is NOT fixed here - see
 * MinMax_rigl.c for the fixed-memory variant.
 */
#define SOURCE_FILE "RIGL"

#include "Common.h"
#include "RigL.h"
#include "Tensor.h"
#include "MinMax.h"
#include "Layer.h"
#include "Linear.h"
#include <math.h>       /* cosf, fabsf */
#include <stdbool.h>

#define RIGL_PI 3.14159265f

void rigLStep(layer_t **model, size_t numLayers,
              float alphaInit, size_t step, size_t tEnd)
{
    /* ---- alpha schedule -------------------------------------------------
     * alpha(t) = (alphaInit/2) * (1 + cos(pi * t / tEnd))
     *
     * FIX D9: the source computes prog = step/totalSteps, so alpha reaches
     * zero only at the very last step. The schedule in section 2.3 wants the
     * mask frozen at 80% of training, so the horizon is an explicit tEnd and
     * we return early once it passes.
     */
    if (tEnd == 0) return;
    if (step >= tEnd) return;               /* mask frozen */

    const float prog  = (float)step / (float)tEnd;
    const float alpha = 0.5f * alphaInit * (1.0f + cosf(RIGL_PI * prog));

    for (size_t l = 0; l < numLayers; l++) {

        if (model[l]->type != LINEAR) continue;     /* Conv1d not supported */

        linearConfig_t *cfg = model[l]->config->linear;
        tensor_t *mask = cfg->weightMask;
        if (mask == NULL) continue;                 /* dense layer */

        tensor_t *weights = cfg->weights->param;
        tensor_t *grads   = cfg->weights->grad;

        const size_t n = calcNumberOfElementsByTensor(weights);
        float *w = (float *)weights->data;          /* FLOAT32 only */
        float *g = (float *)grads->data;

        size_t numActive = 0;
        for (size_t i = 0; i < n; i++)
            if (tensorBoolGet(mask, i)) numActive++;

        const size_t K = (size_t)(alpha * (float)numActive);
        if (K == 0) continue;                       /* nothing to swap */

        PRINT_INFO("rigLStep: layer=%zu step=%zu alpha=%.4f K=%zu active=%zu",
                   l, step, alpha, K, numActive);

        /* FIX D2: snapshot the mask before DROP, so that weights dropped in
         * this step cannot be regrown in the same step. */
        tensor_t *prevMask = cloneBoolTensor(mask);
        if (prevMask == NULL) {
            PRINT_ERROR("rigLStep: cannot clone mask for layer %zu", l);
            continue;
        }

        /* ---- DROP: deactivate the K smallest |w| among active ---------- */
        const float dropThresh = findAbsKthSmallestActive(weights, mask, K);
        size_t dropped = 0;
        for (size_t i = 0; i < n; i++) {
            /* FIX D1: strict < drops exactly K. The source uses <=, which
             * with a zero-indexed K-th value drops K+1 (see its own worked
             * example in section 39.2, which miscounts). */
            if (tensorBoolGet(mask, i) && fabsf(w[i]) < dropThresh) {
                tensorBoolSet(mask, i, false);
                w[i] = 0.0f;
                dropped++;
            }
        }
        PRINT_DEBUG("  drop thresh=%.6e dropped=%zu", dropThresh, dropped);

        /* ---- GROW: activate the `dropped` largest |g| among weights that
         * were ALREADY inactive before the drop (FIX D2). Growing exactly
         * `dropped` rather than K keeps the active count exactly conserved. */
        const float growThresh =
            findAbsKthLargestInactive(grads, prevMask, dropped);

        size_t grown = 0;
        for (size_t i = 0; i < n && grown < dropped; i++) {
            if (!tensorBoolGet(prevMask, i) &&      /* inactive before DROP */
                !tensorBoolGet(mask, i) &&          /* still inactive now   */
                fabsf(g[i]) > growThresh) {
                tensorBoolSet(mask, i, true);
                w[i] = 0.0f;                        /* grown weights start at 0 */
                grown++;
            }
        }
        PRINT_DEBUG("  grow thresh=%.6e grown=%zu", growThresh, grown);

        /* Conservation assertion. If this fires, sparsity is drifting: the
         * usual cause is defect D3 - the inactive gradients are all zero
         * because they were never computed or were zeroed by the optimiser. */
        if (grown != dropped)
            PRINT_ERROR("rigLStep: layer=%zu dropped=%zu grown=%zu "
                        "(sparsity drifting; check D3)", l, dropped, grown);

        freeBoolTensor(prevMask);

        /* ---- clear gradients of everything still inactive --------------- */
        for (size_t i = 0; i < n; i++)
            if (!tensorBoolGet(mask, i)) g[i] = 0.0f;
    }
}
