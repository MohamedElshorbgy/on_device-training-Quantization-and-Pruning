#define SOURCE_FILE "QUANTIZATION"

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

#include "Common.h"
#include "Quantization.h"
#include "Rounding.h"

void initSymInt32QConfig(roundingMode_t roundingMode, symInt32QConfig_t *symInt32QConfig) {            //Purpose: Sets up integer-to-integer/fixed-point scaling constraints.Difference: initSymInt32QConfig automatically
                                                                                                         defaults the maximum quantization bit boundaries to 16 bits, whereas the WithQMaxBits variant lets the application
                                                                                                         specify its own bounds (e.g., 8 bits or 32 bits) depending on hardware register limitations.
    symInt32QConfig->roundingMode = roundingMode;
    symInt32QConfig->scale = 1.f;
    symInt32QConfig->qMaxBits = ODT_SYM_OPERAND_QMAXBITS; /* was 16 — #227 int12 operands */
}

void initSymInt32QConfigWithQMaxBits(roundingMode_t roundingMode,
                                     symInt32QConfig_t *symInt32QConfig, uint8_t qMaxBits) {
    /* #202: qMaxBits > 31 makes the float32 clamp bound powf(2, qMaxBits - 1) - 1
     * round up past INT32_MAX, so the (int32_t) cast in the SYM_INT32 converters is
     * out of range (UB). 31 stays valid (raw-int/scale=1 regime, #227). This init is
     * the single chokepoint every SYM_INT32 qConfig passes through. */
    if (qMaxBits > 31) {
        PRINT_ERROR("qMaxBits (%u) exceeds the cast-safe SYM_INT32 ceiling of 31 (#202)",
                    (unsigned)qMaxBits);
        exit(1);
    }
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
    /* #246: qBits > 30 makes the unsigned code ceiling powf(2, qBits) - 1 round
     * to 2^31 in float, so the (int32_t) cast in the ASYM emit path is out of
     * range (UB) -- the unsigned twin of the #202 SYM_INT32 ceiling at 31. 0
     * would underflow the sub-byte packer. deriveAsymGridFromMinMax re-checks
     * for configs built without this init. */
    if (qBits == 0 || qBits > 30) {
        PRINT_ERROR("qBits (%u) outside the ASYM range [1, 30] (#246)", (unsigned)qBits);
        exit(1);
    }
    asymQConfig->qBits = qBits;
    asymQConfig->roundingMode = roundingMode;
    asymQConfig->scale = 1.f;
    asymQConfig->zeroPoint = 0;
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
