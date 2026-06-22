/* config.h — Project-wide constants for OnDeviceTraining_HAR_FQT_RigL
 *
 * Architecture (matches har_classifier_v2):
 *   Conv1d(9→16, K=7, SAME) + ReLU + MaxPool(2,2)
 *   Conv1d(16→32, K=5, SAME) + ReLU + MaxPool(2,2)
 *   Conv1d(32→64, K=3, SAME) + ReLU + AvgPool(32,32)
 *   Flatten → Linear(64→6) → Softmax
 *
 * Training : float32 via OnDeviceTraining framework + RigL sparse masks
 * INT8 infer: fqt.h routines applied to float weights after training
 * Target    : PC (simulation) / Raspberry Pi Pico (RP2040)
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

/* ── UCI-HAR input ──────────────────────────────────────────────── */
#define INPUT_T     128   /* timesteps per window                    */
#define INPUT_C     9     /* channels: body-acc XYZ, gyro XYZ, total-acc XYZ */
#define NUM_CLS     6     /* WALKING/UPSTAIRS/DOWNSTAIRS/SIT/STAND/LAY */

/* ── 1D-CNN topology (must match buildModel() in main.c) ────────── */
#define CONV1_F     16    /* Conv block 1 output channels            */
#define CONV1_K     7     /* Conv block 1 kernel size                */
#define CONV2_F     32    /* Conv block 2 output channels            */
#define CONV2_K     5     /* Conv block 2 kernel size                */
#define CONV3_F     64    /* Conv block 3 output channels            */
#define CONV3_K     3     /* Conv block 3 kernel size                */
/* Pool(2,2) × 2 → 128/4 = 32; AvgPool(32,32) → 1 per channel     */
#define FC_IN       64    /* Linear head input features (= CONV3_F) */
#define MODEL_SIZE  12    /* total layers in model[]                 */

/* ── RigL sparse-training indices into model[] ──────────────────── */
/* Parameterised layers: conv1@0, conv2@3, conv3@6, linear@10       */
#define RIGL_NUM_LAYERS  4

/* ── Fixed-Point Quantization (FQT) ─────────────────────────────── */
/* Training uses float32.  INT8 inference via fqt.h post-training.  */
#define FQT_BITS    8
#define FQT_QMAX    127
#define FQT_QMIN   -128

/* ── RigL hyper-parameters ───────────────────────────────────────── */
#define RIGL_SPARSITY  0.75f   /* target fraction of zeros           */
#define RIGL_DELTA_T   100     /* prune-regrow every N batches       */
#define RIGL_FRAC      0.20f   /* fraction of active weights cycled  */

/* ── Training hyper-parameters ───────────────────────────────────── */
#define LR           0.01f
#define MOMENTUM     0.9f
#define BATCH_SIZE   64
#define NUM_EPOCHS   20
#define SEED         42
#define SHUFFLE_SEED 42

/* ── HAR class labels ────────────────────────────────────────────── */
#define LABEL_WALKING            0
#define LABEL_WALKING_UPSTAIRS   1
#define LABEL_WALKING_DOWNSTAIRS 2
#define LABEL_SITTING            3
#define LABEL_STANDING           4
#define LABEL_LAYING             5

/* ── Utility macros ──────────────────────────────────────────────── */
#define CLAMP(x, lo, hi)  ((x) < (lo) ? (lo) : ((x) > (hi) ? (hi) : (x)))

#endif /* CONFIG_H */
