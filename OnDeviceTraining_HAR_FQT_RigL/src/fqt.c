/* fqt.c — Fixed-Point Quantization Training implementation */

#include "fqt.h"
#include <math.h>
#include <string.h>

/* ── Helpers ─────────────────────────────────────────────────────────── */

static inline float fabsf_local(float x) { return x < 0.0f ? -x : x; }

static inline int8_t clamp_i8(int32_t v)
{
    if (v >  FQT_QMAX) return (int8_t) FQT_QMAX;
    if (v <  FQT_QMIN) return (int8_t) FQT_QMIN;
    return (int8_t)v;
}

static inline int32_t round_i32(float v)
{
    return (int32_t)(v >= 0.0f ? v + 0.5f : v - 0.5f);
}

/* ── Scale computation ─────────────────────────────────────────────── */

float fqt_compute_scale(const float *data, int len)
{
    float max_abs = 1e-8f;   /* avoid divide-by-zero */
    for (int i = 0; i < len; i++) {
        float a = fabsf_local(data[i]);
        if (a > max_abs) max_abs = a;
    }
    return max_abs / (float)FQT_QMAX;
}

/* ── Quantize / Dequantize ─────────────────────────────────────────── */

void fqt_quantize(const float *in, int8_t *out, float scale, int len)
{
    float inv = 1.0f / scale;
    for (int i = 0; i < len; i++)
        out[i] = clamp_i8(round_i32(in[i] * inv));
}

void fqt_dequantize(const int8_t *in, float *out, float scale, int len)
{
    for (int i = 0; i < len; i++)
        out[i] = (float)in[i] * scale;
}

void fqt_quantize_layer(const float *w, int8_t *wq, float *scale, int len)
{
    *scale = fqt_compute_scale(w, len);
    fqt_quantize(w, wq, *scale, len);
}

/* ── Bias quantization ─────────────────────────────────────────────── */

void fqt_quantize_bias(const float *bias_f, int32_t *bias_q,
                       int len, float in_scale, float w_scale)
{
    float inv = 1.0f / (in_scale * w_scale);
    for (int i = 0; i < len; i++)
        bias_q[i] = round_i32(bias_f[i] * inv);
}

/* ── ReLU (INT8) ───────────────────────────────────────────────────── */

void fqt_relu_int8(int8_t *data, int len)
{
    for (int i = 0; i < len; i++)
        if (data[i] < 0) data[i] = 0;
}

/* ── Max-pool (INT8) ───────────────────────────────────────────────── */

void fqt_maxpool_int8(const int8_t *input, int T, int C,
                      int pool_sz, int8_t *output)
{
    int OT = T / pool_sz;
    for (int t = 0; t < OT; t++) {
        for (int c = 0; c < C; c++) {
            int8_t mx = (int8_t)FQT_QMIN;
            for (int p = 0; p < pool_sz; p++) {
                int8_t v = input[(t * pool_sz + p) * C + c];
                if (v > mx) mx = v;
            }
            output[t * C + c] = mx;
        }
    }
}

/* ── Global Average Pool (INT8) ────────────────────────────────────── */

void fqt_global_avg_pool_int8(const int8_t *input, int T, int C,
                               int8_t *output)
{
    for (int c = 0; c < C; c++) {
        int32_t acc = 0;
        for (int t = 0; t < T; t++)
            acc += input[t * C + c];
        /* round-to-nearest divide by T */
        int32_t avg = (acc >= 0) ? (acc + T/2) / T : (acc - T/2) / T;
        output[c] = clamp_i8(avg);
    }
}

/* ── INT8 1-D Convolution ──────────────────────────────────────────── */
/*
 * input  [T][C_in]           — row-major
 * kernel [C_out][C_in][K]    — row-major
 * output [OT][C_out]         — OT = T - K + 1
 *
 * Accumulation in int32, then requantise to int8:
 *   q_out = round( acc * (in_sc * w_sc) / out_sc )
 */
void fqt_conv1d_int8(const int8_t *input, int T, int C_in,
                     const int8_t *kernel, int C_out, int K,
                     const int32_t *bias,
                     const uint8_t *mask,
                     int8_t *output,
                     float in_scale, float w_scale, float out_scale)
{
    int OT = T - K + 1;
    float reqs = (in_scale * w_scale) / out_scale;

    for (int t = 0; t < OT; t++) {
        for (int f = 0; f < C_out; f++) {
            int32_t acc = bias ? bias[f] : 0;
            for (int c = 0; c < C_in; c++) {
                for (int k = 0; k < K; k++) {
                    int w_idx = f * C_in * K + c * K + k;
                    if (mask && !mask[w_idx]) continue;
                    acc += (int32_t)input[(t + k) * C_in + c]
                         * (int32_t)kernel[w_idx];
                }
            }
            /* requantize */
            float scaled = (float)acc * reqs;
            output[t * C_out + f] = clamp_i8(round_i32(scaled));
        }
    }
}

/* ── INT8 Dense (fully-connected) ──────────────────────────────────── */

void fqt_dense_int8(const int8_t *input, int in_sz,
                    const int8_t *weight, int out_sz,
                    const int32_t *bias,
                    int8_t *output,
                    float in_scale, float w_scale, float out_scale)
{
    float reqs = (in_scale * w_scale) / out_scale;
    for (int o = 0; o < out_sz; o++) {
        int32_t acc = bias ? bias[o] : 0;
        const int8_t *row = weight + o * in_sz;
        for (int i = 0; i < in_sz; i++)
            acc += (int32_t)input[i] * (int32_t)row[i];
        float scaled = (float)acc * reqs;
        output[o] = clamp_i8(round_i32(scaled));
    }
}
