#ifndef ENV5_RUNTIME_QUANTIZATION_H
#define ENV5_RUNTIME_QUANTIZATION_H

#include "Rounding.h"

typedef enum qtype { INT32, FLOAT32, SYM_INT32, SYM, ASYM, BOOL } qtype_t;                                 //This enumeration defines the target numeric representations supported by the runtime engine:INT32 / FLOAT32 / 
                                                                                                             BOOL: Standard unquantized or baseline data types (32-bit integers, 32-bit single-precision floats, and booleans).
                                                                                                             SYM_INT32 (Symmetric Int32): Quantization targeted specifically at 32-bit fixed-point/integer values.SYM 
                                                                                                             (Symmetric Quantization): Represents floating-point values where the range is mirrored symmetrically around zero
                                                                                                             (e.g., from -X to +X). The value 0.0 in float maps exactly to integer 0. It only requires a scale factor.ASYM 
                                                                                                             (Asymmetric Quantization): Maps a float range to a non-symmetrical integer range (e.g., 0 to 255 for unsigned 
                                                                                                             8-bit integers). It requires both a scale factor and a zeroPoint to shift the range so that float 0.0 can map 
                                                                                                             to an arbitrary integer integer.

typedef struct symInt32QConfig {                                                                            //scale: A multiplier used to scale numbers.roundingMode: Determines how fractional values are handled when 
                                                                                                              converting floats to integers (e.g., round to nearest, round down, etc., defined in "Rounding.h").qMaxBits: 
                                                                                                              Limits the bit-width boundaries (e.g., cap calculations to a maximum of 16 bits).
    float scale;
    roundingMode_t roundingMode;
    uint8_t qMaxBits;
} symInt32QConfig_t;

typedef struct symQConfig {                                                                                 //qBits: The exact target bit width of the quantized format (typically 8 bits for int8_t or 16 bits for int16_t).
    float scale;
    uint8_t qBits;
    roundingMode_t roundingMode;
} symQConfig_t;

typedef struct asymQConfig {                                                                                 //zeroPoint: The real-world integer value that represents exactly 0.0 in the unquantized float domain. This offsets 
                                                                                                               asymmetric data distributions safely.
    float scale;
    int16_t zeroPoint;
    uint8_t qBits;
    roundingMode_t roundingMode;
} asymQConfig_t;

typedef struct quantization {                                                                                 //This is a polymorphic design pattern in C. Instead of creating distinct structures for every unique quantization
                                                                                                                algorithm, this wrapper unifies them:type: An enum telling the system which configuration struct is being active
                                                                                                                ly used.*qConfig: A generic void * pointer pointing directly to one of the config structs above 
                                                                                                                (symQConfig_t, asymQConfig_t, etc.). The runtime casts this pointer dynamically depending on the type value.
    qtype_t type;
    void *qConfig;
} quantization_t;

// Important: This sets qMaxBits to 16
void initSymInt32QConfig(roundingMode_t roundingMode, symInt32QConfig_t *symInt32QConfig);                    //These populate the individual algorithm settings. Notice the comment in your file: initSymInt32QConfig natively defaults
                                                                                                                qMaxBits to 16 internally unless you call the explicitly parameterized WithQMaxBits alternative.
void initSymInt32QConfigWithQMaxBits(roundingMode_t roundingMode,
                                     symInt32QConfig_t *symInt32QConfig, uint8_t qMaxBits);
void initSymQConfig(uint8_t qBits, roundingMode_t roundingMode, symQConfig_t *symQConfig);
void initAsymQConfig(uint8_t qBits, roundingMode_t roundingMode, asymQConfig_t *asymQConfig);

void initInt32Quantization(quantization_t *quantization);                                                     //These flag the master object as a standard non-quantized pass-through structure, setting qConfig safely to NULL
void initFloat32Quantization(quantization_t *quantization);
void initBoolQuantization(quantization_t *quantization);

void initSymInt32Quantization(symInt32QConfig_t *symInt32QConfig, quantization_t *quantization);              //These bind a fully constructed config block directly into the quantization_t container and assign the matching 
                                                                                                                type enum.
void initSymQuantization(symQConfig_t *symQConfig, quantization_t *quantization);
void initAsymQuantization(asymQConfig_t *asymQConfig, quantization_t *quantization);

#endif // ENV5_RUNTIME_QUANTIZATION_H
