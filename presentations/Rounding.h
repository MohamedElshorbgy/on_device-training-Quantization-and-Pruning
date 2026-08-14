\\Rounding.c provides the two rounding strategies used throughout quantization. The first is Half-To-Even rounding,
 which is the standard deterministic strategy: 0.5 rounds to the nearest even integer. The
second is Stochastic Rounding Half-To-Even, which is the core mathematical trick that makes Fully Quantized Training
work. Stochastic Rounding adds a small random value (called a dither) before rounding, so that a gradient value of 0.1
will round up to 1 about 10% of the time and round down to 0 about 90% of the time — preserving the expected value of
the gradient even though individual samples are rounded to integers.

#ifndef ROUNDING_H
#define ROUNDING_H
#include <stdint.h>
\\stdint.h defines types like int32_t (a signed 32-bit integer), uint8_t (an unsigned 8-bit integer), etc. These
types have guaranteed sizes on every platform, unlike plain "int" which
can vary.
/*! @brief Describes rounding
 * HALF_AWAY = round half away from zero (C round(), C17 7.12.9.6)
 * SR_HALF_AWAY = stochastic rounding: uniform jitter in [-0.5, 0.5) is added
 *                before rounding half away from zero
 */
typedef enum roundingMode { HALF_AWAY, SR_HALF_AWAY } roundingMode_t;
\\An enum (enumeration) is a way to define a set of named integer constants. "typedef" means we are also creating a type alias so we 
can write "roundingMode_t" instead of the longer "enum roundingMode" everywhere.
Half-To-Even is the standard deterministic rounding rule: when a value is exactly halfway between two integers (like
2.5), it rounds to whichever integer is even (2 in this case). 
Stochastic Rounding adds a random number uniformly distributed between -0.5 and +0.5 to the input
before applying Half-To-Even rounding. This means the result is random,
but its statistical average equals the original float value — an important
property for training neural networks with integers.
int32_t roundByMode(float input, roundingMode_t roundingMode);
\\This tells the compiler that a function called roundByMode exists somewhere, takes a 32-bit floating-point number
and a rounding mode, and returns a 32-bit signed integer
float clamp(float input, float min, float max);
\\"Clamping" means forcing a
value to stay within a given range. If the input is below min, return min. If it is above max, return max. Otherwise return the input unchanged.
This prevents integer overflow during quantization.
#endif // ROUNDING_H

--------------------------------------------------------------------------------------------------------------------------------------------

#define SOURCE_FILE "ROUNDING"
\\Any call to PRINT_DEBUG or PRINT_ERROR inside this file will include the text "ROUNDING" in the output, making it easy to trace which 
module produced a given debug line.
#include <math.h>
\\math.h provides round(), which is the C standard library function for rounding a float to the nearest integer.
Without this include, the compiler would not know what round() is.

#include <stdio.h>

#include "RNG.h"
#include "Rounding.h"
\\The .c file includes its own .h file to get access to the roundingMode_t type definition it declared there
// C round(): rounds half away from zero (C17 7.12.9.6)
int32_t roundHalfAway(float input) {
    return round(input);
}

float randfloat() {
    return rngNextFloat();
}
randfloat is a wrapper function to call the real function rngNextFloat which exist in RNG.h
int32_t roundSRHalfAway(const float input) {
    return roundHalfAway(input + randfloat() - 0.5f);
}
\\randfloat() returns a number in [0, 1).Subtracting 0.5 shifts it to the range [-0.5, 0.5). Adding this to the input
shifts it by a random amount, then Half-To-Even rounding snaps it to an integer. A value of 0.1 will be shifted to somewhere in [-0.4, 0.6). About
10% of the time (when the shift pushes it above 0.5) it rounds up to 1, and 90% of the time it rounds down to 0. Over many training steps, the
average is preserved at 0.1.
int32_t roundByMode(const float input, const roundingMode_t roundingMode) {
    switch (roundingMode) {
    case HALF_AWAY:
        return roundHalfAway(input);
    case SR_HALF_AWAY:
        return roundSRHalfAway(input);
    }
    return 0;
}

float clamp(float input, float min, float max) {
    if (input < min) {
        return min;
    }
    if (input > max) {
        return max;
    }
    return input;
}
