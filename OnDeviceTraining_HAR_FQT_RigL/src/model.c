/* model.c — 1D-CNN: forward pass, backward pass, INT8 inference */

#include "model.h"
#include <string.h>
#include <math.h>
#include <stdio.h>

/* ── Local helpers ────────────────────────────────────────────────── */

static uint32_t rng = 1;
static float rand_f(void)       /* uniform [0,1) */
{
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
    return (float)(rng & 0x7FFFFFFF) / (float)0x7FFFFFFF;
}
static float rand_range(float lo, float hi) { return lo + (hi - lo) * rand_f(); }

static inline float relu(float x)  { return x > 0.0f ? x : 0.0f; }
static inline float fabs_l(float x){ return x < 0.0f ? -x : x; }

/* ── Glorot uniform initialisation ───────────────────────────────── */

static void glorot_init(float *w, int fan_in, int fan_out, int size)
{
    float lim = sqrtf(6.0f / (float)(fan_in + fan_out));
    for (int i = 0; i < size; i++)
        w[i] = rand_range(-lim, lim);
}

/* ── model_init ───────────────────────────────────────────────────── */

void model_init(CNN_Model *m, uint32_t seed)
{
    rng = (seed == 0) ? 1 : seed;
    memset(m, 0, sizeof(CNN_Model));

    /* Glorot init for conv/dense weights */
    glorot_init(m->conv1_w,  INPUT_C * CONV1_K, CONV1_F,  CONV1_W_SZ);
    glorot_init(m->conv2_w,  CONV1_F * CONV2_K, CONV2_F,  CONV2_W_SZ);
    glorot_init(m->dense1_w, GAP_SIZE,           DENSE1_S, DENSE1_W_SZ);
    glorot_init(m->dense2_w, DENSE1_S,           NUM_CLS,  DENSE2_W_SZ);
    /* biases stay zero */

    /* RigL masks: 75 % sparsity (not applied to dense2) */
    rigl_init_mask(m->mask_conv1,  CONV1_W_SZ,  RIGL_SPARSITY, seed ^ 0xAABB);
    rigl_init_mask(m->mask_conv2,  CONV2_W_SZ,  RIGL_SPARSITY, seed ^ 0xCCDD);
    rigl_init_mask(m->mask_dense1, DENSE1_W_SZ, RIGL_SPARSITY, seed ^ 0xEEFF);

    /* Apply masks to shadow weights immediately */
    model_apply_masks(m);
}

/* ── Float 1-D convolution ────────────────────────────────────────── */
/* input [T][C_in], kernel [C_out][C_in][K], bias [C_out]
 * output [OT][C_out] (OT = T - K + 1)
 * mask [C_out*C_in*K] or NULL                                        */
static void conv1d_float(const float *input, int T, int C_in,
                         const float *kernel, int C_out, int K,
                         const float *bias,
                         const uint8_t *mask,
                         float *output)
{
    int OT = T - K + 1;
    for (int t = 0; t < OT; t++) {
        for (int f = 0; f < C_out; f++) {
            float acc = bias[f];
            for (int c = 0; c < C_in; c++) {
                for (int k = 0; k < K; k++) {
                    int w_idx = f * C_in * K + c * K + k;
                    if (mask && !mask[w_idx]) continue;
                    acc += input[(t + k) * C_in + c] * kernel[w_idx];
                }
            }
            output[t * C_out + f] = acc;
        }
    }
}

/* ── Float max-pool ───────────────────────────────────────────────── */
/* input [T][C], output [T/2][C], idx [T/2][C] (argmax over T-axis) */
static void maxpool_float(const float *input, int T, int C,
                          float *output, int *idx)
{
    int OT = T / 2;
    for (int t = 0; t < OT; t++) {
        for (int c = 0; c < C; c++) {
            float v0 = input[(2*t)   * C + c];
            float v1 = input[(2*t+1) * C + c];
            if (v0 >= v1) { output[t*C+c] = v0; idx[t*C+c] = 2*t;   }
            else           { output[t*C+c] = v1; idx[t*C+c] = 2*t+1; }
        }
    }
}

/* ── Float global average pool ────────────────────────────────────── */
/* input [T][C], output [C] */
static void gap_float(const float *input, int T, int C, float *output)
{
    float inv_T = 1.0f / (float)T;
    for (int c = 0; c < C; c++) {
        float acc = 0.0f;
        for (int t = 0; t < T; t++) acc += input[t * C + c];
        output[c] = acc * inv_T;
    }
}

/* ── Float dense layer ────────────────────────────────────────────── */
/* input [in_sz], weight [out_sz][in_sz], bias [out_sz], output [out_sz] */
static void dense_float(const float *input, int in_sz,
                        const float *weight, int out_sz,
                        const float *bias,
                        const uint8_t *mask,
                        float *output)
{
    for (int o = 0; o < out_sz; o++) {
        float acc = bias[o];
        const float *row = weight + o * in_sz;
        for (int i = 0; i < in_sz; i++) {
            int w_idx = o * in_sz + i;
            if (mask && !mask[w_idx]) continue;
            acc += input[i] * row[i];
        }
        output[o] = acc;
    }
}

/* ── Softmax ─────────────────────────────────────────────────────── */
static void softmax(float *x, int n)
{
    float max_v = x[0];
    for (int i = 1; i < n; i++) if (x[i] > max_v) max_v = x[i];
    float sum = 0.0f;
    for (int i = 0; i < n; i++) { x[i] = expf(x[i] - max_v); sum += x[i]; }
    float inv = 1.0f / sum;
    for (int i = 0; i < n; i++) x[i] *= inv;
}

/* ── model_forward (float, training) ─────────────────────────────── */

float model_forward(CNN_Model *m,
                    const float *input,
                    int label,
                    ForwardCache *cache)
{
    /* --- Conv1 --- */
    conv1d_float(input, INPUT_T, INPUT_C,
                 m->conv1_w, CONV1_F, CONV1_K, m->conv1_b,
                 m->mask_conv1, cache->conv1_pre);

    /* Store conv1_pre, then apply ReLU → pool1 input */
    float conv1_relu[ACT_CONV1_SZ];
    for (int i = 0; i < ACT_CONV1_SZ; i++)
        conv1_relu[i] = relu(cache->conv1_pre[i]);

    /* --- MaxPool1 --- */
    maxpool_float(conv1_relu, CONV1_OT, CONV1_F,
                  cache->pool1_out, cache->pool1_idx);

    /* --- Conv2 --- */
    conv1d_float(cache->pool1_out, POOL1_OT, CONV1_F,
                 m->conv2_w, CONV2_F, CONV2_K, m->conv2_b,
                 m->mask_conv2, cache->conv2_pre);

    float conv2_relu[ACT_CONV2_SZ];
    for (int i = 0; i < ACT_CONV2_SZ; i++)
        conv2_relu[i] = relu(cache->conv2_pre[i]);

    /* --- MaxPool2 --- */
    maxpool_float(conv2_relu, CONV2_OT, CONV2_F,
                  cache->pool2_out, cache->pool2_idx);

    /* --- GlobalAvgPool --- */
    gap_float(cache->pool2_out, POOL2_OT, CONV2_F, cache->gap_out);

    /* --- Dense1 --- */
    dense_float(cache->gap_out, GAP_SIZE,
                m->dense1_w, DENSE1_S, m->dense1_b,
                m->mask_dense1, cache->d1_pre);
    for (int i = 0; i < DENSE1_S; i++)
        cache->d1_out[i] = relu(cache->d1_pre[i]);

    /* --- Dense2 --- */
    dense_float(cache->d1_out, DENSE1_S,
                m->dense2_w, NUM_CLS, m->dense2_b,
                NULL, cache->d2_out);

    /* --- Softmax --- */
    memcpy(cache->probs, cache->d2_out, NUM_CLS * sizeof(float));
    softmax(cache->probs, NUM_CLS);

    /* --- Cross-entropy loss (add epsilon for numerical stability) --- */
    float loss = -logf(cache->probs[label] + 1e-8f);
    return loss;
}

/* ── model_backward (float) ──────────────────────────────────────── */
/*
 * All gradients computed via chain rule.
 * RigL straight-through: backprop ignores masks → grads for pruned
 * weights are non-zero and used by rigl_step() for regrow decisions.
 */
void model_backward(CNN_Model *m,
                    const float *input,
                    int label,
                    const ForwardCache *cache,
                    WeightGrads *grads)
{
    memset(grads, 0, sizeof(WeightGrads));

    /* ── dL/d(logits) = probs - one_hot ──────────────────────────── */
    float d_logits[NUM_CLS];
    for (int i = 0; i < NUM_CLS; i++)
        d_logits[i] = cache->probs[i] - (float)(i == label);

    /* ── Dense2 backward ─────────────────────────────────────────── */
    /* d_logits [NUM_CLS],  d1_out [DENSE1_S] */
    float d_d1_out[DENSE1_S];
    memset(d_d1_out, 0, sizeof(d_d1_out));
    for (int o = 0; o < NUM_CLS; o++) {
        float g = d_logits[o];
        grads->dense2_b[o] += g;
        for (int i = 0; i < DENSE1_S; i++) {
            grads->dense2_w[o * DENSE1_S + i] += g * cache->d1_out[i];
            d_d1_out[i] += g * m->dense2_w[o * DENSE1_S + i];
        }
    }

    /* ── ReLU backward (Dense1) ──────────────────────────────────── */
    float d_d1_pre[DENSE1_S];
    for (int i = 0; i < DENSE1_S; i++)
        d_d1_pre[i] = (cache->d1_pre[i] > 0.0f) ? d_d1_out[i] : 0.0f;

    /* ── Dense1 backward ─────────────────────────────────────────── */
    float d_gap[GAP_SIZE];
    memset(d_gap, 0, sizeof(d_gap));
    for (int o = 0; o < DENSE1_S; o++) {
        float g = d_d1_pre[o];
        grads->dense1_b[o] += g;
        for (int i = 0; i < GAP_SIZE; i++) {
            /* straight-through: ignore mask here for gradient flow */
            grads->dense1_w[o * GAP_SIZE + i] += g * cache->gap_out[i];
            d_gap[i] += g * m->dense1_w[o * GAP_SIZE + i];
        }
    }

    /* ── GlobalAvgPool backward ──────────────────────────────────── */
    /* GAP: out[c] = mean(pool2_out[:, c])
     * dL/d(pool2_out[t,c]) = d_gap[c] / POOL2_OT                   */
    float d_pool2[ACT_POOL2_SZ];
    float inv_T2 = 1.0f / (float)POOL2_OT;
    for (int t = 0; t < POOL2_OT; t++)
        for (int c = 0; c < CONV2_F; c++)
            d_pool2[t * CONV2_F + c] = d_gap[c] * inv_T2;

    /* ── MaxPool2 backward ───────────────────────────────────────── */
    /* Route gradient to the position that was the max */
    float d_conv2_relu[ACT_CONV2_SZ];
    memset(d_conv2_relu, 0, sizeof(d_conv2_relu));
    for (int i = 0; i < ACT_POOL2_SZ; i++) {
        int src = cache->pool2_idx[i];   /* index in conv2_relu       */
        int c   = i % CONV2_F;
        d_conv2_relu[src * CONV2_F + c] += d_pool2[i];
    }

    /* ── ReLU backward (Conv2) ───────────────────────────────────── */
    float d_conv2_pre[ACT_CONV2_SZ];
    for (int i = 0; i < ACT_CONV2_SZ; i++)
        d_conv2_pre[i] = (cache->conv2_pre[i] > 0.0f) ? d_conv2_relu[i] : 0.0f;

    /* ── Conv2 backward ──────────────────────────────────────────── */
    float d_pool1[ACT_POOL1_SZ];
    memset(d_pool1, 0, sizeof(d_pool1));

    for (int t = 0; t < CONV2_OT; t++) {
        for (int f = 0; f < CONV2_F; f++) {
            float g = d_conv2_pre[t * CONV2_F + f];
            grads->conv2_b[f] += g;
            for (int c = 0; c < CONV1_F; c++) {
                for (int k = 0; k < CONV2_K; k++) {
                    int w_idx = f * CONV1_F * CONV2_K + c * CONV2_K + k;
                    /* straight-through: always update gradient */
                    grads->conv2_w[w_idx] += g * cache->pool1_out[(t+k)*CONV1_F+c];
                    d_pool1[(t+k)*CONV1_F+c] += g * m->conv2_w[w_idx];
                }
            }
        }
    }

    /* ── MaxPool1 backward ───────────────────────────────────────── */
    float d_conv1_relu[ACT_CONV1_SZ];
    memset(d_conv1_relu, 0, sizeof(d_conv1_relu));
    for (int i = 0; i < ACT_POOL1_SZ; i++) {
        int src = cache->pool1_idx[i];
        int c   = i % CONV1_F;
        d_conv1_relu[src * CONV1_F + c] += d_pool1[i];
    }

    /* ── ReLU backward (Conv1) ───────────────────────────────────── */
    float d_conv1_pre[ACT_CONV1_SZ];
    for (int i = 0; i < ACT_CONV1_SZ; i++)
        d_conv1_pre[i] = (cache->conv1_pre[i] > 0.0f) ? d_conv1_relu[i] : 0.0f;

    /* ── Conv1 backward ──────────────────────────────────────────── */
    for (int t = 0; t < CONV1_OT; t++) {
        for (int f = 0; f < CONV1_F; f++) {
            float g = d_conv1_pre[t * CONV1_F + f];
            grads->conv1_b[f] += g;
            for (int c = 0; c < INPUT_C; c++) {
                for (int k = 0; k < CONV1_K; k++) {
                    int w_idx = f * INPUT_C * CONV1_K + c * CONV1_K + k;
                    grads->conv1_w[w_idx] += g * input[(t+k)*INPUT_C+c];
                }
            }
        }
    }
}

/* ── INT8 inference forward pass ─────────────────────────────────── */

int model_infer(CNN_Model *m, const float *input, float *pred_probs)
{
    /* Quantise input */
    static int8_t q_input[INPUT_T * INPUT_C];
    m->sc_input = fqt_compute_scale(input, INPUT_T * INPUT_C);
    fqt_quantize(input, q_input, m->sc_input, INPUT_T * INPUT_C);

    /* Conv1 */
    static int8_t q_conv1[ACT_CONV1_SZ];
    fqt_conv1d_int8(q_input, INPUT_T, INPUT_C,
                    m->conv1_wq, CONV1_F, CONV1_K,
                    m->conv1_bq, m->mask_conv1, q_conv1,
                    m->sc_input, m->sc_conv1_w, m->sc_conv1_act);
    fqt_relu_int8(q_conv1, ACT_CONV1_SZ);

    /* MaxPool1 */
    static int8_t q_pool1[ACT_POOL1_SZ];
    fqt_maxpool_int8(q_conv1, CONV1_OT, CONV1_F, 2, q_pool1);

    /* Conv2 */
    static int8_t q_conv2[ACT_CONV2_SZ];
    fqt_conv1d_int8(q_pool1, POOL1_OT, CONV1_F,
                    m->conv2_wq, CONV2_F, CONV2_K,
                    m->conv2_bq, m->mask_conv2, q_conv2,
                    m->sc_conv1_act, m->sc_conv2_w, m->sc_conv2_act);
    fqt_relu_int8(q_conv2, ACT_CONV2_SZ);

    /* MaxPool2 */
    static int8_t q_pool2[ACT_POOL2_SZ];
    fqt_maxpool_int8(q_conv2, CONV2_OT, CONV2_F, 2, q_pool2);

    /* GlobalAvgPool */
    static int8_t q_gap[GAP_SIZE];
    fqt_global_avg_pool_int8(q_pool2, POOL2_OT, CONV2_F, q_gap);

    /* Dense1 */
    static int8_t q_d1[DENSE1_S];
    fqt_dense_int8(q_gap, GAP_SIZE,
                   m->dense1_wq, DENSE1_S, m->dense1_bq, q_d1,
                   m->sc_conv2_act, m->sc_d1_w, m->sc_d1_act);
    fqt_relu_int8(q_d1, DENSE1_S);

    /* Dense2 */
    static int8_t q_d2[NUM_CLS];
    fqt_dense_int8(q_d1, DENSE1_S,
                   m->dense2_wq, NUM_CLS, m->dense2_bq, q_d2,
                   m->sc_d1_act, m->sc_d2_w, m->sc_d2_act);

    /* Dequantise → softmax for probabilities */
    float logits[NUM_CLS];
    fqt_dequantize(q_d2, logits, m->sc_d2_act, NUM_CLS);
    softmax(logits, NUM_CLS);

    /* Find argmax */
    int best = 0;
    for (int i = 1; i < NUM_CLS; i++)
        if (logits[i] > logits[best]) best = i;

    if (pred_probs)
        memcpy(pred_probs, logits, NUM_CLS * sizeof(float));

    return best;
}

/* ── model_requantize ─────────────────────────────────────────────── */

void model_requantize(CNN_Model *m, const float *input_sample)
{
    fqt_quantize_layer(m->conv1_w,  m->conv1_wq,  &m->sc_conv1_w,  CONV1_W_SZ);
    fqt_quantize_layer(m->conv2_w,  m->conv2_wq,  &m->sc_conv2_w,  CONV2_W_SZ);
    fqt_quantize_layer(m->dense1_w, m->dense1_wq, &m->sc_d1_w,     DENSE1_W_SZ);
    fqt_quantize_layer(m->dense2_w, m->dense2_wq, &m->sc_d2_w,     DENSE2_W_SZ);

    /* Estimate activation scales from a calibration sample (simple heuristic) */
    if (input_sample) {
        m->sc_input     = fqt_compute_scale(input_sample, INPUT_T * INPUT_C);
        m->sc_conv1_act = m->sc_conv1_w * m->sc_input * (float)CONV1_K * 2.0f;
        m->sc_conv2_act = m->sc_conv2_w * m->sc_conv1_act * (float)CONV2_K * 2.0f;
        m->sc_d1_act    = m->sc_d1_w * m->sc_conv2_act * 2.0f;
        m->sc_d2_act    = m->sc_d2_w * m->sc_d1_act * 2.0f;
    }

    /* Quantise biases */
    fqt_quantize_bias(m->conv1_b,  m->conv1_bq,  CONV1_F,  m->sc_input,     m->sc_conv1_w);
    fqt_quantize_bias(m->conv2_b,  m->conv2_bq,  CONV2_F,  m->sc_conv1_act, m->sc_conv2_w);
    fqt_quantize_bias(m->dense1_b, m->dense1_bq, DENSE1_S, m->sc_conv2_act, m->sc_d1_w);
    fqt_quantize_bias(m->dense2_b, m->dense2_bq, NUM_CLS,  m->sc_d1_act,    m->sc_d2_w);
}

/* ── model_apply_masks ────────────────────────────────────────────── */

void model_apply_masks(CNN_Model *m)
{
    rigl_apply_mask(m->conv1_w,  m->mask_conv1,  CONV1_W_SZ);
    rigl_apply_mask(m->conv2_w,  m->mask_conv2,  CONV2_W_SZ);
    rigl_apply_mask(m->dense1_w, m->mask_dense1, DENSE1_W_SZ);
}

/* ── model_print_sparsity ─────────────────────────────────────────── */

void model_print_sparsity(const CNN_Model *m)
{
    printf("[Sparsity] conv1=%.1f%%  conv2=%.1f%%  dense1=%.1f%%\n",
           rigl_actual_sparsity(m->mask_conv1,  CONV1_W_SZ)  * 100.0f,
           rigl_actual_sparsity(m->mask_conv2,  CONV2_W_SZ)  * 100.0f,
           rigl_actual_sparsity(m->mask_dense1, DENSE1_W_SZ) * 100.0f);
}
