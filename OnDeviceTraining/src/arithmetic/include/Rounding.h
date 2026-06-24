#ifndef ROUNDING_H
#define ROUNDING_H
#include <stdint.h>

/*! @brief Describes rounding
 * HALF_AWAY = round half away from zero (C round(), C17 7.12.9.6)
 * SR_HALF_AWAY = stochastic rounding: uniform jitter in [-0.5, 0.5) is added
 *                before rounding half away from zero
 */
typedef enum roundingMode { HALF_AWAY, SR_HALF_AWAY } roundingMode_t;

int32_t roundByMode(float input, roundingMode_t roundingMode);

float clamp(float input, float min, float max);

#endif // ROUNDING_H     


/*An enum is a way to create a custom list of options. Instead of remembering cryptic numbers like 0 and 1, a programmer can use readable text names. This enum creates two rounding strategies:
  *Option A: HALF_AWAY (Standard Rounding) This is the normal rounding you learned in school. If a number ends in exactly .5, it rounds away from zero to the nearest whole number.
  *Option B: SR_HALF_AWAY (Stochastic Rounding) This is an advanced, randomized rounding method used to prevent statistical bias.
  *Before rounding, the computer injects a tiny bit of random "noise" or "jitter" between -0.5 and 0.5
  *Why do this?: If you always round 2.5 up to 3, and you do this to millions of data points, your final average will skew slightly too high.
  *By adding a random tiny shift first, a 2.5 will sometimes round up to 3 and sometimes round down to 2. Over time, the math errors cancel each other out perfectly.*/
