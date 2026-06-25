#define SOURCE_FILE "QUANTIZATION"

#include <stddef.h>
#include <stdint.h>

#include "Quantization.h"
#include "Rounding.h"

void initSymInt32QConfig(roundingMode_t roundingMode, symInt32QConfig_t *symInt32QConfig) {            //Purpose: Sets up integer-to-integer/fixed-point scaling constraints.Difference: initSymInt32QConfig automatically
                                                                                                         defaults the maximum quantization bit boundaries to 16 bits, whereas the WithQMaxBits variant lets the application
                                                                                                         specify its own bounds (e.g., 8 bits or 32 bits) depending on hardware register limitations.
    symInt32QConfig->roundingMode = roundingMode;
    symInt32QConfig->scale = 1.f;
    symInt32QConfig->qMaxBits = 16;
}

void initSymInt32QConfigWithQMaxBits(roundingMode_t roundingMode,
                                     symInt32QConfig_t *symInt32QConfig, uint8_t qMaxBits) {
    symInt32QConfig->roundingMode = roundingMode;
    symInt32QConfig->scale = 1.f;
    symInt32QConfig->qMaxBits = qMaxBits;
}

void initSymQConfig(uint8_t qBits, roundingMode_t roundingMode, symQConfig_t *symQConfig) {             //Purpose: Prepares settings for float-to-integer conversion pipelines.Key detail: The asymmetric configuration
                                                                                                          explicitly explicitly sets its zeroPoint shift parameter to 0. During actual network runtime execution, a specialized
                                                                                                          calculation function will recompute this scale and zeroPoint based on the true minimum and maximum ranges of the 
                                                                                                          underlying layer weights or activations.
    symQConfig->qBits = qBits;
    symQConfig->roundingMode = roundingMode;
    symQConfig->scale = 1.f;
}

void initAsymQConfig(uint8_t qBits, roundingMode_t roundingMode, asymQConfig_t *asymQConfig) {
    asymQConfig->qBits = qBits;
    asymQConfig->roundingMode = roundingMode;
    asymQConfig->scale = 1.f;
    asymQConfig->zeroPoint = (uint16_t)0;
}

void initInt32Quantization(quantization_t *quantization) {                                                //Purpose: Sets up standard primitives like regular integers, 32-bit floating points, or booleans.Design Note:
                                                                                                            Because these are native data types that do not undergo compression or scaling math, they do not need structural 
                                                                                                            algorithm rules. Therefore, their generic qConfig pointer is explicitly set to NULL to prevent dangling memory
                                                                                                            access bugs.
    quantization->type = INT32;
    quantization->qConfig = NULL;
}

void initFloat32Quantization(quantization_t *quantization) {
    quantization->type = FLOAT32;
    quantization->qConfig = NULL;
}

void initBoolQuantization(quantization_t *quantization) {
    quantization->type = BOOL;
    quantization->qConfig = NULL;
}

void initSymInt32Quantization(symInt32QConfig_t *symInt32QConfig, quantization_t *quantization) {        //Purpose: Completes the object linkage for active compression profiles.How it binds: 
                                                                                                           It tags the quantization->type flag with the corresponding enum variant and saves the address of the specific
                                                                                                           algorithm configuration structure directly inside the polymorphic void *qConfig pointer.
    quantization->type = SYM_INT32;
    quantization->qConfig = symInt32QConfig;
}

void initSymQuantization(symQConfig_t *symQConfig, quantization_t *quantization) {
    quantization->type = SYM;
    quantization->qConfig = symQConfig;
}

void initAsymQuantization(asymQConfig_t *asymQConfig, quantization_t *quantization) {
    quantization->type = ASYM;
    quantization->qConfig = asymQConfig;
}
