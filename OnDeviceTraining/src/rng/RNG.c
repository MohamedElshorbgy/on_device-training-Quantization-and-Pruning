#define SOURCE_FILE "RNG"

#include "RNG.h"

static rng32_t rng = {.state = 1};                                //The file declares a single, private instance of your structure named rng using the static keyword. This keeps the variable locked inside this .c file so
                                                                    other parts of the application cannot modify it directly.It initializes state to 1. This is critical: a Xorshift engine must never have a state of 0. If
                                                                    the state drops to 0, the math fails, and it will output nothing but 0s forever.

static uint32_t rngNext(rng32_t *rng) {                           //Instead of using slow arithmetic operations like multiplication or division, this code uses bit-shifting (<<, >>) and exclusive OR (^=) operators. 
                                                                    This executes in just a few clock cycles on a CPU.It takes the current number, shifts its binary bits left by 13 positions, and blends it with the 
                                                                    original number (x ^= x << 13).It repeats this by shifting right by 17, and then left by 5.This specific sequence (13, 17, 5) is a mathematically proven
                                                                    combination discovered by George Marsaglia. It guarantees that the engine will cycle through 4.2 billion numbers before ever repeating itself.
    uint32_t x = rng->state; 
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    rng->state = x;
    return x;
}

static size_t rngBounded(rng32_t *rng, size_t bound) {            //If you need a random number between 0 and 5, you might be tempted to use rngNext() % 6. However, because UINT32_MAX (the max limit of a 32-bit integer)
                                                                    is not perfectly divisible by 6, certain numbers will have a slightly higher mathematical probability of appearing. This is called Modulo Bias.This function
                                                                    completely eliminates modulo bias using a technique called Rejection Sampling.It calculates a strict maximum cutoff limit (limit). If rngNext() generates 
                                                                    a number that falls into the awkward remainder zone at the absolute top end of the integer range, the do-while loop throws it away and requests a brand-new number.
    uint32_t x;
    uint32_t limit = UINT32_MAX - (UINT32_MAX % bound);

    do {
        x = rngNext(rng);
    } while (x >= limit);

    return x % bound;
}

void rngShuffleIndices(size_t *indices, size_t n) {               //This is a standard implementation of the Fisher-Yates Shuffle used to mix lists up randomly.It steps backward through the list from the last element down to the
                                                                    beginning.For every slot i, it picks a random index j from the unshuffled remaining part of the list using rngBounded.It then swaps the values at positions 
                                                                    i and j. This guarantees a perfectly uniform random distribution—every possible variation of the list has an equal chance of appearing.
    if (n < 2) {
        return;
    }

    for (size_t i = n - 1; i > 0; --i) {
        size_t j = rngBounded(&rng, i + 1);

        size_t tmp = indices[i];
        indices[i] = indices[j];
        indices[j] = tmp;
    }
}

void rngSetSeed(uint32_t seed) {                               //The Zero Defense: If a developer accidentally initializes the engine with a seed value of 0, this line auto-corrects it to UINT32_MAX. This ensures the
                                                                 state remains a non-zero value, preventing the generation engine from crashing or locking up
    rng.state = seed ? seed : UINT32_MAX;
}

uint32_t rngGetSeed(void) {
    return rng.state;
}
 
float rngNextFloat(void) {                                       //Generating a Decimal Fraction: Standard floating-point numbers (float) only have 24 bits of precision available for their fractional values.This function
                                                                   throws away the lower 8 bits of the random integer (>> 8) to harvest the most stable 24 bits. It then divides that result by \(2^{24}\) (1 << 24). This yields
                                                                   a decimal number cleanly ranging from 0.0f up to (but not quite including) 1.0f
    return (float)(rngNext(&rng) >> 8) / (float)(1 << 24);
}
