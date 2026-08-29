/*
 * RigL.h - Rigging the Lottery: sparse training with dynamic connectivity.
 *
 * Extracted and consolidated from ODT_Complete_Reference_v2.pdf,
 * sections 2.2, 7.4, 33.4 and 39.1-39.9.
 *
 * See RigL_Implementation_Line_by_Line.pdf for a line-by-line explanation
 * of every function declared here.
 */
#ifndef RIGL_H
#define RIGL_H

#include <stddef.h>
#include "Tensor.h"
#include "Layer.h"

/*
 * K-th smallest |weight| among ACTIVE (mask bit = 1) weights.
 * Used as the DROP threshold. Returns 1e38f when K >= the active count,
 * which makes every active weight eligible to drop.
 * Source: section 7.4. Implemented in MinMax_rigl.c.
 */
float findAbsKthSmallestActive(tensor_t *weights, tensor_t *mask, size_t K);

/*
 * K-th largest |gradient| among INACTIVE (mask bit = 0) weights.
 * Used as the GROW threshold. Returns 0.0f when K >= the inactive count,
 * which makes every inactive weight eligible to grow.
 *
 * NOTE the asymmetry with the function above: +inf vs 0. Both mean
 * "process all candidates", because DROP tests <= and GROW tests >=.
 * Source: section 7.4. Implemented in MinMax_rigl.c.
 */
float findAbsKthLargestInactive(tensor_t *grads, tensor_t *mask, size_t K);

/*
 * One RigL mask update across every sparse LINEAR layer of the model.
 *
 *   alphaInit  initial swap fraction (0.3 in the source)
 *   step       current global training step
 *   tEnd       step at which alpha reaches zero and the mask freezes.
 *              Pass 0.8 * totalSteps, NOT totalSteps - see defect D9.
 *
 * Call AFTER backward() and BEFORE the optimiser step. Ordering matters:
 * the optimiser zeroes the gradients of inactive weights, which are
 * exactly the gradients the GROW step ranks (defects D3 and D4).
 *
 * Layers whose weightMask is NULL are skipped, so this is safe to call on
 * a fully dense model.
 */
void rigLStep(layer_t **model, size_t numLayers,
              float alphaInit, size_t step, size_t tEnd);

#endif /* RIGL_H */
