#define SOURCE_FILE "ROUNDING"

#include <math.h>
#include <stdio.h>

#include "RNG.h"
#include "Rounding.h"

// C round(): rounds half away from zero (C17 7.12.9.6)
int32_t roundHalfAway(float input) {                                                  //It rounds the number to the nearest integer. If the fractional part is exactly \(0.5\),
                                                                                        it rounds away from zero (towards positive infinity for positive numbers, and towards negative infinity for negative numbers).
    return round(input);
}
                                                                                      //Based on standard implementations of stochastic rounding, this function is assumed to return a random uniform floating-point 
                                                                                        value in the range \([0.0, 1.0)\).
float randfloat() {
    return rngNextFloat();
}

int32_t roundSRHalfAway(const float input) {
    return roundHalfAway(input + randfloat() - 0.5f);
}

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
