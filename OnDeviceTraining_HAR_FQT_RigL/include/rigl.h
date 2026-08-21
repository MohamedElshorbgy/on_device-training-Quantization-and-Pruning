/* rigl.h — RigL sparse training (Evci et al., ICML 2020)
 *
 * Reference: "Rigging the Lottery: Making All Tickets Winners", ICML 2020.
 *
 * Algorithm:
 *   1. Initialise masks with random sparsity = RIGL_SPARSITY.
 *   2. Every RIGL_DELTA_T batches:
 *        a. PRUNE : zero out RIGL_FRAC * n_active weights with
 *                   smallest |weight| (mask → 0).
 *        b. REGROW: activate RIGL_FRAC * n_active pruned weights with
 *                   largest |gradient| (mask → 1).
 *   3. After each weight update, apply mask (zero pruned weights).
 *
 * Gradients for pruned weights are computed via straight-through
 * estimator — backprop ignores the mask, then the raw gradient is
 * used to rank candidates for regrowing.
 *
 * Two-level API:
 *  - Primitive: rigl_init_mask / rigl_apply_mask / rigl_step
 *  - Framework: rigl_init_from_layer / rigl_apply_to_layer / rigl_step_layer
 *    (bridges into OnDeviceTraining's layer_t / parameter_t types)
 */

#ifndef RIGL_H
#define RIGL_H

#include <stddef.h>
#include <stdint.h>

/* ── Primitive API (no framework dependencies) ───────────────────── */

/* Fill mask[0..size-1] so that round(sparsity * size) entries are 0.
 * Uses xorshift32 RNG seeded by `seed`.                            */
void rigl_init_mask(uint8_t *mask, int size, float sparsity, uint32_t seed);

/* Zero out every weights[i] where mask[i] == 0. */
void rigl_apply_mask(float *weights, const uint8_t *mask, int size);

/* Execute one RigL prune-regrow step.
 *   weights  : float shadow weights (read-only)
 *   grads    : gradients for ALL positions including pruned ones
 *   mask     : binary mask, updated in place
 *   size     : total number of elements
 *   sparsity : target fraction of zeros (e.g. 0.75)
 *   frac     : fraction of active weights to cycle (e.g. 0.20)
 *
 * Call rigl_apply_mask() on the weights after this.               */
void rigl_step(const float *weights, const float *grads,
               uint8_t *mask, int size, float sparsity, float frac);

/* Return fraction of zeros in mask. */
float rigl_actual_sparsity(const uint8_t *mask, int size);

/* Return count of active (mask == 1) weights. */
int rigl_active_count(const uint8_t *mask, int size);

/* ── ERK sparsity distribution ───────────────────────────────────── */

/* Describes one layer's shape for ERK score computation.
 * For Conv1d : n_in=in_channels, n_out=out_channels, kernel=kernel_size
 * For Linear : n_in=in_features,  n_out=out_features, kernel=1        */
typedef struct {
    int n_in;
    int n_out;
    int kernel;   /* kernel size; set to 1 for Linear layers */
    int is_conv;  /* 1 = Conv1d, 0 = Linear                 */
} rigl_layer_info_t;

/* Compute per-layer sparsities using the ERK distribution so that the
 * total non-zero weight count across all layers equals:
 *   sum_i(sizes[i]) * (1 - global_sparsity)
 *
 * Parameters:
 *   info[]     : shape descriptor for each layer  (length = n_layers)
 *   sizes[]    : total weight count per layer      (length = n_layers)
 *   n_layers   : number of layers
 *   global_sp  : target overall sparsity (e.g. 0.80)
 *   out_sp[]   : output — per-layer sparsity       (length = n_layers)
 *
 * Sparsity values are clamped to [0.05, 0.99].                        */
void rigl_erk_sparsities(const rigl_layer_info_t *info,
                         const int *sizes,
                         int n_layers,
                         float global_sp,
                         float *out_sp);

/* ── Framework layer API (OnDeviceTraining integration) ─────────── */

#include "Layer.h"   /* layer_t, layerType_t: CONV1D, LINEAR, ... */

/* Number of weight elements for a CONV1D or LINEAR layer; 0 otherwise. */
size_t rigl_layer_size(layer_t *layer);

/* Initialise mask from the weight tensor of `layer`.
 * `mask` must be pre-allocated with rigl_layer_size(layer) bytes. */
void rigl_init_from_layer(layer_t *layer, uint8_t *mask,
                          float sparsity, uint32_t seed);

/* Apply mask to the layer's float32 weight data in place. */
void rigl_apply_to_layer(layer_t *layer, const uint8_t *mask);

/* Run one prune-regrow step using the layer's weight and gradient
 * tensors. Requires float32 layerQuant (FLOAT32 forward/weight math). */
void rigl_step_layer(layer_t *layer, uint8_t *mask,
                     float sparsity, float frac);

#endif /* RIGL_H */
