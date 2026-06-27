#ifndef RNG_H
#define RNG_H

#include <stddef.h>
#include <stdint.h>

typedef struct {                                                                        //Computers cannot generate truly random numbers out of thin air. Instead, they use a mathematical formula that takes a number,
                                                                                          scrambles its bits, and outputs a new number.This struct acts as a tiny storage box holding a single 32-bit unsigned integer 
                                                                                          (uint32_t) called state.The state represents the current position in that sequence of scrambled numbers. Every time you ask for
                                                                                          a random number, the engine reads this state, changes it, and returns the result.
    uint32_t state;
} rng32_t;

// NOTE: not thread-safe — all functions below use module-global RNG state.
// When multi-threading support is added, migrate to context-passing variants.

void rngShuffleIndices(size_t *indices, size_t n);                                      //What it does: Takes an array of indices (whole numbers) and randomly reorders them.Why it matters: In AI training, you never 
                                                                                          want your model to memorize the exact order of your training files (like always seeing images of dogs before cats). Shuffling indices
                                                                                          allows you to read your training items in a completely mixed, random order every time. It likely implements a famous algorithm called
                                                                                          the Fisher-Yates Shuffle.

void rngSetSeed(uint32_t seed);                                                          //What it does: Sets or retrieves the starting number (the Seed) for your random engine.Why it matters: Because computer randomness is
                                                                                           just mathematical scrambling, if you start with the exact same seed number (like 42), the engine will always generate the exact same 
                                                                                           sequence of "random" numbers. This is a massive advantage in software development: it allows you to debug your code because you can
                                                                                           reproduce your exact results every time.

uint32_t rngGetSeed(void);

float rngNextFloat(void);                                                                 //What it does: Scrambles the internal state bits and converts them into a decimal float value, typically bounded between 0.0f and
                                                                                            1.0f.Why it matters: This is heavily used to initialize neural network layers or to simulate probabilities. For example, if you 
                                                                                            want a layer to drop 20% of its connections, you can generate an rngNextFloat(). If the number comes back less than 0.20f, you 
                                                                                            turn off that connection!

#endif // RNG_H
