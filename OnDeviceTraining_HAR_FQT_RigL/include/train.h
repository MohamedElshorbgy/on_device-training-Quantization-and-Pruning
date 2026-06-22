/* train.h — Training loop, SGD update, RigL scheduling */

#ifndef TRAIN_H
#define TRAIN_H

#include "model.h"
#include "dataset.h"

/* ── Training state ──────────────────────────────────────────────── */
typedef struct {
    int   step;            /* global training step counter             */
    int   epoch;           /* current epoch                            */
    float running_loss;    /* exponential moving average of loss       */
    float running_acc;     /* EMA of step-wise accuracy (0-1)          */
    int   correct;         /* correct predictions this epoch           */
    int   total;           /* total samples this epoch                 */
} TrainState;

/* ── SGD with momentum weight update ─────────────────────────────── */
/*
 * For each layer:
 *   vel  ← MOMENTUM * vel  +  lr * grad
 *   w    ← w  -  vel
 * Masks are applied after the update.
 */
void train_sgd_step(CNN_Model *m, const WeightGrads *grads,
                    float lr, float momentum);

/* ── Single training step ─────────────────────────────────────────── */
/*
 *   input : float[INPUT_T * INPUT_C]  (normalised)
 *   label : 0–5
 * Runs forward → backward → SGD update.
 * Triggers rigl_step() every RIGL_DELTA_T steps.
 * Updates state->running_loss and state->running_acc.
 * Returns loss for this sample.
 */
float train_step(CNN_Model *m, TrainState *state,
                 const float *input, int label);

/* ── Evaluation on embedded test set ─────────────────────────────── */
/*
 * Runs INT8 inference on all DATASET_TEST_N samples.
 * Returns accuracy (0-1). Prints per-class stats to stdout.
 */
float train_evaluate(CNN_Model *m);

/* ── Epoch summary ───────────────────────────────────────────────── */
void train_print_epoch(const TrainState *state);

/* ── Initialise state ─────────────────────────────────────────────── */
void train_state_init(TrainState *state);

#endif /* TRAIN_H */
