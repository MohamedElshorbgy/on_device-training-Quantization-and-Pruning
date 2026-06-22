/* fqt.h — Fixed-Point Quantization Training (FQT) API
 *
 * Strategy: "shadow float" weights are trained with full-precision SGD;
 * INT8 copies are derived for each forward pass (QAT style).
 *
 * Scale convention (symmetric, per-tensor):
 *   q = clamp( round(x / scale), QMIN, QMAX )
 *   x_approx = q * scale
 *   scale = max(|x|) / QMAX
 */

#ifndef FQT_H
#define FQT_H

#include <stdint.h>
#include "config.h"

/* ── Scale computation ─────────────────────────────────────────────── */

/* Compute symmetric INT8 scale from an array of floats.
 * Returns scale factor s such that q = round(x/s) stays in [-127,127]. */
float fqt_compute_scale(const float *data, int len);

/* ── Quantize / Dequantize ─────────────────────────────────────────── */

/* Quantize float array → int8 using pre-computed scale. */
void fqt_quantize(const float *in, int8_t *out, float scale, int len);

/* Dequantize int8 array → float. */
void fqt_dequantize(const int8_t *in, float *out, float scale, int len);

/* Quantize and update scale in one call (used before each forward pass). */
void fqt_quantize_layer(const float *w, int8_t *wq, float *scale, int len);

/* ── INT8 forward-pass primitives ──────────────────────────────────── */

/* 1-D convolution (INT8 weights, INT32 accumulator, INT8 output).
 *
 *   input  : [T][C_in]   flattened, int8
 *   kernel : [C_out][C_in][K]  flattened, int8
 *   bias   : [C_out]  int32  (= float_bias / (in_scale * w_scale))
 *   output : [T-K+1][C_out]  int8
 *   mask   : [C_out*C_in*K]  uint8  (1=active, 0=pruned), or NULL
 *
 *   Requantization: out_q = round( acc * (in_scale*w_scale) / out_scale )
 */
void fqt_conv1d_int8(const int8_t *input, int T, int C_in,
                     const int8_t *kernel, int C_out, int K,
                     const int32_t *bias,
                     const uint8_t *mask,
                     int8_t *output,
                     float in_scale, float w_scale, float out_scale);

/* Global Average Pooling over time axis.
 *   input  : [T][C]  int8
 *   output : [C]     int8  (mean over T, same scale)
 */
void fqt_global_avg_pool_int8(const int8_t *input, int T, int C,
                               int8_t *output);

/* Dense (fully-connected) layer (INT8).
 *   input  : [in_sz]       int8
 *   weight : [out_sz][in_sz]  int8  (flattened row-major)
 *   bias   : [out_sz]      int32
 *   output : [out_sz]      int8
 */
void fqt_dense_int8(const int8_t *input, int in_sz,
                    const int8_t *weight, int out_sz,
                    const int32_t *bias,
                    int8_t *output,
                    float in_scale, float w_scale, float out_scale);

/* ReLU on int8 array (clamp negatives to 0). */
void fqt_relu_int8(int8_t *data, int len);

/* Max-pool over time axis (stride = pool_size).
 *   input  : [T][C]           int8
 *   output : [T/pool_sz][C]   int8
 */
void fqt_maxpool_int8(const int8_t *input, int T, int C,
                      int pool_sz, int8_t *output);

/* Bias helper: compute int32 bias from float bias given scales.
 *   bias_q[i] = round( bias_f[i] / (in_scale * w_scale) )
 */
void fqt_quantize_bias(const float *bias_f, int32_t *bias_q,
                       int len, float in_scale, float w_scale);

#endif /* FQT_H */
