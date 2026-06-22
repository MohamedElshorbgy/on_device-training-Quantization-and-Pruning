/* model.h — 1D-CNN model for on-device HAR with FQT + RigL
 *
 * Architecture:
 *   Input  [128][9]
 *   Conv1  16 filters, kernel 5  → [124][16]  + ReLU
 *   MaxPool(2)                   → [62][16]
 *   Conv2  32 filters, kernel 3  → [60][32]   + ReLU
 *   MaxPool(2)                   → [30][32]
 *   GlobalAvgPool                → [32]
 *   Dense1 32→32                 + ReLU       (with RigL mask)
 *   Dense2 32→6                  (no RigL on output layer)
 *   Softmax                      → probabilities
 *
 * Training : float shadow weights + float forward/backward pass.
 * Inference: INT8 quantized weights for efficient on-device prediction.
 *
 * Memory footprint (static global arrays, never on stack):
 *   Shadow weights : ~14 KB  (float)
 *   INT8 weights   :  ~3.5 KB
 *   RigL masks     :  ~3.5 KB
 *   Activation buf :  ~51 KB  (for training cache)
 *   Gradient buf   :  ~38 KB
 *   Total          : ~110 KB  ← fits in RP2040's 264 KB SRAM
 */

#ifndef MODEL_H
#define MODEL_H

#include <stdint.h>
#include "config.h"
#include "fqt.h"
#include "rigl.h"

/* ── Activation buffer sizes ────────────────────────────────────── */
#define ACT_CONV1_SZ    (CONV1_OT * CONV1_F)   /* 124*16 = 1984   */
#define ACT_POOL1_SZ    (POOL1_OT * CONV1_F)   /* 62*16  = 992    */
#define ACT_CONV2_SZ    (CONV2_OT * CONV2_F)   /* 60*32  = 1920   */
#define ACT_POOL2_SZ    (POOL2_OT * CONV2_F)   /* 30*32  = 960    */
#define ACT_GAP_SZ      GAP_SIZE                /* 32              */
#define ACT_D1_SZ       DENSE1_S               /* 32              */
#define ACT_D2_SZ       NUM_CLS                 /* 6               */

/* ── Forward-pass cache (needed for backprop) ───────────────────── */
typedef struct {
    float conv1_pre [ACT_CONV1_SZ];  /* before ReLU                  */
    float pool1_out [ACT_POOL1_SZ];  /* after MaxPool                 */
    int   pool1_idx [ACT_POOL1_SZ];  /* argmax positions (backprop)  */
    float conv2_pre [ACT_CONV2_SZ];  /* before ReLU                  */
    float pool2_out [ACT_POOL2_SZ];  /* after MaxPool                 */
    int   pool2_idx [ACT_POOL2_SZ];  /* argmax positions             */
    float gap_out   [ACT_GAP_SZ];    /* after GlobalAvgPool           */
    float d1_pre    [ACT_D1_SZ];     /* Dense1 before ReLU            */
    float d1_out    [ACT_D1_SZ];     /* Dense1 after ReLU             */
    float d2_out    [ACT_D2_SZ];     /* Dense2 logits                 */
    float probs     [ACT_D2_SZ];     /* Softmax output                */
} ForwardCache;

/* ── Weight gradient buffer ─────────────────────────────────────── */
typedef struct {
    float conv1_w [CONV1_W_SZ];
    float conv1_b [CONV1_F];
    float conv2_w [CONV2_W_SZ];
    float conv2_b [CONV2_F];
    float dense1_w[DENSE1_W_SZ];
    float dense1_b[DENSE1_S];
    float dense2_w[DENSE2_W_SZ];
    float dense2_b[NUM_CLS];
} WeightGrads;

/* ── Model struct ───────────────────────────────────────────────── */
typedef struct {
    /* --- Float shadow weights (trained with SGD) --- */
    float conv1_w [CONV1_W_SZ];   /* [C_out=16][C_in=9][K=5]    */
    float conv1_b [CONV1_F];
    float conv2_w [CONV2_W_SZ];   /* [C_out=32][C_in=16][K=3]   */
    float conv2_b [CONV2_F];
    float dense1_w[DENSE1_W_SZ];  /* [32][32]                    */
    float dense1_b[DENSE1_S];
    float dense2_w[DENSE2_W_SZ];  /* [6][32]                     */
    float dense2_b[NUM_CLS];

    /* --- INT8 quantized copies (for inference) --- */
    int8_t  conv1_wq [CONV1_W_SZ];
    int8_t  conv2_wq [CONV2_W_SZ];
    int8_t  dense1_wq[DENSE1_W_SZ];
    int8_t  dense2_wq[DENSE2_W_SZ];
    int32_t conv1_bq [CONV1_F];
    int32_t conv2_bq [CONV2_F];
    int32_t dense1_bq[DENSE1_S];
    int32_t dense2_bq[NUM_CLS];

    /* --- Per-layer scales --- */
    float sc_conv1_w, sc_conv1_act;
    float sc_conv2_w, sc_conv2_act;
    float sc_d1_w,    sc_d1_act;
    float sc_d2_w,    sc_d2_act;
    float sc_input;

    /* --- RigL masks (1=active, 0=pruned) --- */
    uint8_t mask_conv1 [CONV1_W_SZ];
    uint8_t mask_conv2 [CONV2_W_SZ];
    uint8_t mask_dense1[DENSE1_W_SZ];
    /* dense2 has no mask (output layer) */

    /* --- SGD momentum buffers --- */
    float vel_conv1_w [CONV1_W_SZ];
    float vel_conv1_b [CONV1_F];
    float vel_conv2_w [CONV2_W_SZ];
    float vel_conv2_b [CONV2_F];
    float vel_dense1_w[DENSE1_W_SZ];
    float vel_dense1_b[DENSE1_S];
    float vel_dense2_w[DENSE2_W_SZ];
    float vel_dense2_b[NUM_CLS];
} CNN_Model;

/* ── API ──────────────────────────────────────────────────────────── */

/* Initialise model: Glorot-uniform weights, random sparse masks. */
void model_init(CNN_Model *m, uint32_t seed);

/* Float forward pass (training).
 *   input : [INPUT_T][INPUT_C] float (pre-normalised to [-1, 1])
 *   cache : intermediate activations stored for backprop
 *   Returns cross-entropy loss for label `label`.
 */
float model_forward(CNN_Model *m,
                    const float *input,
                    int label,
                    ForwardCache *cache);

/* Float backward pass. Fills grads with ∂L/∂W for all layers.
 * Gradients for pruned weights ARE computed (straight-through)
 * so rigl_step() can use them for the regrow decision.
 */
void model_backward(CNN_Model *m,
                    const float *input,
                    int label,
                    const ForwardCache *cache,
                    WeightGrads *grads);

/* INT8 inference forward pass (no cache, no backprop).
 *   Requantises float weights → INT8 before running.
 *   pred_probs : optional float[NUM_CLS] output (can be NULL)
 *   Returns predicted class index.
 */
int model_infer(CNN_Model *m, const float *input, float *pred_probs);

/* Re-quantise all float shadow weights to INT8 (call after weight update). */
void model_requantize(CNN_Model *m, const float *input_sample);

/* Apply all RigL masks to shadow weights (zero pruned positions). */
void model_apply_masks(CNN_Model *m);

/* Print sparsity stats over serial (printf). */
void model_print_sparsity(const CNN_Model *m);

#endif /* MODEL_H */
