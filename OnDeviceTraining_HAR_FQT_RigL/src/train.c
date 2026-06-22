/* train.c — Training loop: SGD + RigL scheduling */

#include "train.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

/* Static buffers (avoid stack allocation for large structs on Pico) */
static ForwardCache s_cache;
static WeightGrads  s_grads;

/* ── train_state_init ────────────────────────────────────────────── */

void train_state_init(TrainState *state)
{
    memset(state, 0, sizeof(TrainState));
    state->running_loss = 2.0f;   /* initial guess ≈ -ln(1/6) */
    state->running_acc  = 1.0f / (float)NUM_CLS;
}

/* ── train_sgd_step ──────────────────────────────────────────────── */

/* Macro: velocity ← mom*vel + lr*grad; weight ← weight - vel */
#define SGD_UPDATE(w_arr, v_arr, g_arr, sz, lr_, mom_)          \
    do {                                                         \
        for (int _i = 0; _i < (sz); _i++) {                     \
            (v_arr)[_i] = (mom_) * (v_arr)[_i]                  \
                         + (lr_) * (g_arr)[_i];                  \
            (w_arr)[_i] -= (v_arr)[_i];                         \
        }                                                        \
    } while (0)

void train_sgd_step(CNN_Model *m, const WeightGrads *grads,
                    float lr, float momentum)
{
    SGD_UPDATE(m->conv1_w,  m->vel_conv1_w,  grads->conv1_w,  CONV1_W_SZ,  lr, momentum);
    SGD_UPDATE(m->conv1_b,  m->vel_conv1_b,  grads->conv1_b,  CONV1_F,     lr, momentum);
    SGD_UPDATE(m->conv2_w,  m->vel_conv2_w,  grads->conv2_w,  CONV2_W_SZ,  lr, momentum);
    SGD_UPDATE(m->conv2_b,  m->vel_conv2_b,  grads->conv2_b,  CONV2_F,     lr, momentum);
    SGD_UPDATE(m->dense1_w, m->vel_dense1_w, grads->dense1_w, DENSE1_W_SZ, lr, momentum);
    SGD_UPDATE(m->dense1_b, m->vel_dense1_b, grads->dense1_b, DENSE1_S,    lr, momentum);
    SGD_UPDATE(m->dense2_w, m->vel_dense2_w, grads->dense2_w, DENSE2_W_SZ, lr, momentum);
    SGD_UPDATE(m->dense2_b, m->vel_dense2_b, grads->dense2_b, NUM_CLS,     lr, momentum);
}

/* ── train_step ──────────────────────────────────────────────────── */

float train_step(CNN_Model *m, TrainState *state,
                 const float *input, int label)
{
    /* 1. Float forward pass */
    float loss = model_forward(m, input, label, &s_cache);

    /* 2. Float backward pass (straight-through: no mask in backprop) */
    model_backward(m, input, label, &s_cache, &s_grads);

    /* 3. SGD update */
    train_sgd_step(m, &s_grads, LR, MOMENTUM);

    /* 4. Re-apply RigL masks to shadow weights */
    model_apply_masks(m);

    /* 5. RigL prune-and-regrow every RIGL_DELTA_T steps */
    if (state->step > 0 && (state->step % RIGL_DELTA_T) == 0) {
        rigl_step(m->conv1_w,  s_grads.conv1_w,  m->mask_conv1,
                  CONV1_W_SZ,  RIGL_SPARSITY, RIGL_FRAC);
        rigl_step(m->conv2_w,  s_grads.conv2_w,  m->mask_conv2,
                  CONV2_W_SZ,  RIGL_SPARSITY, RIGL_FRAC);
        rigl_step(m->dense1_w, s_grads.dense1_w, m->mask_dense1,
                  DENSE1_W_SZ, RIGL_SPARSITY, RIGL_FRAC);
        /* After regrowing, zero-initialise newly active weights */
        model_apply_masks(m);
    }

    /* 6. Update training stats (EMA, α = 0.05) */
    float alpha = 0.05f;
    state->running_loss = (1.0f - alpha) * state->running_loss + alpha * loss;

    /* Predict class for accuracy tracking */
    float probs[NUM_CLS];
    memcpy(probs, s_cache.probs, sizeof(probs));
    int pred = 0;
    for (int i = 1; i < NUM_CLS; i++)
        if (probs[i] > probs[pred]) pred = i;
    float correct = (pred == label) ? 1.0f : 0.0f;
    state->running_acc = (1.0f - alpha) * state->running_acc + alpha * correct;

    state->total++;
    if (pred == label) state->correct++;
    state->step++;

    return loss;
}

/* ── train_evaluate ──────────────────────────────────────────────── */

float train_evaluate(CNN_Model *m)
{
    if (DATASET_TEST_N == 0) {
        printf("[Eval] No embedded test data. Run tools/prepare_data.py first.\n");
        return 0.0f;
    }

    /* Re-quantise model weights before INT8 inference */
    model_requantize(m, DATASET_TEST_X[0]);

    int correct = 0;
    int per_class_correct[NUM_CLS] = {0};
    int per_class_total[NUM_CLS]   = {0};

    for (int i = 0; i < DATASET_TEST_N; i++) {
        int label = (int)DATASET_TEST_Y[i];
        int pred  = model_infer(m, DATASET_TEST_X[i], NULL);
        per_class_total[label]++;
        if (pred == label) { correct++; per_class_correct[label]++; }
    }

    float acc = (float)correct / (float)DATASET_TEST_N;
    printf("[Eval] Test accuracy: %.2f%% (%d/%d)\n",
           acc * 100.0f, correct, DATASET_TEST_N);
    for (int c = 0; c < NUM_CLS; c++) {
        if (per_class_total[c] == 0) continue;
        printf("  %-24s %d/%d  (%.0f%%)\n",
               dataset_class_name(c),
               per_class_correct[c], per_class_total[c],
               100.0f * per_class_correct[c] / per_class_total[c]);
    }
    model_print_sparsity(m);
    return acc;
}

/* ── train_print_epoch ───────────────────────────────────────────── */

void train_print_epoch(const TrainState *state)
{
    float epoch_acc = (state->total > 0)
                    ? (float)state->correct / (float)state->total
                    : 0.0f;
    printf("[Epoch %3d | step %5d]  loss=%.4f  train_acc=%.2f%%\n",
           state->epoch,
           state->step,
           state->running_loss,
           epoch_acc * 100.0f);
}
