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

int32_t roundSRHalfAway(const float input) {                                          //Stochastic rounding introduces random noise before performing a standard round. This prevents structural bias and quantization 
                                                                                        noise in machine learning, graphics, or signal processing applications.
                                                                                        Let \(x\) be the input and \(R\) be the random float drawn from \(U[0, 1)\). The function computes:\(\text{Result}=\text{round}(x+R-0.5)\)
                                                                                        Because \(R \sim U[0, 1)\), the value \((R - 0.5)\) represents a uniform noise distribution between \([-0.5, 0.5)\).
    return roundHalfAway(input + randfloat() - 0.5f);
}

int32_t roundByMode(const float input, const roundingMode_t roundingMode) {           //It uses a switch statement to check the enum variable roundingMode. It evaluates whether to run deterministic rounding (HALF_AWAY) or 
                                                                                        stochastic rounding (SR_HALF_AWAY). If an invalid or unhandled mode is passed, it returns a fallback value of 0.
    switch (roundingMode) {
    case HALF_AWAY:
        return roundHalfAway(input);
    case SR_HALF_AWAY:
        return roundSRHalfAway(input);
    }
    return 0;
}

float clamp(float input, float min, float max) {                                      //If input is less than min, it clips it up to min.If input is greater than max, it clips it down to max.Otherwise, 
                                                                                        it returns the input unchanged.
                                                                                        While not called directly in this snippet, clamping is vital before or after converting float to int32_t to prevent integer overflow bugs.
    if (input < min) {
        return min;
    }
    if (input > max) {
        return max;
    }
    return input;
}
