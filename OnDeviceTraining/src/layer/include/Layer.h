#ifndef ODT_LAYER_H
#define ODT_LAYER_H

#include "Tensor.h"

typedef struct linearConfig linearConfig_t;                                          //These lines tell the compiler, "Hey, structures like linearConfig exist somewhere in other files, but don't worry about their exact 
                                                                                       size or internal variables yet." This technique keeps the header lightweight and avoids circular dependency compilation loops 
                                                                                       between files.
typedef struct reluConfig reluConfig_t;
typedef struct softmaxConfig softmaxConfig_t;
typedef struct conv1dConfig conv1dConfig_t;
typedef struct conv1dTransposedConfig conv1dTransposedConfig_t;
typedef struct maxPool1dConfig maxPool1dConfig_t;
typedef struct avgPool1dConfig avgPool1dConfig_t;
typedef struct adaptiveAvgPool1dConfig adaptiveAvgPool1dConfig_t;
typedef struct dropoutConfig dropoutConfig_t;
typedef struct layerNormConfig layerNormConfig_t;
typedef struct quantizationConfig quantizationConfig_t;

typedef enum layerType {                                                             //This is a standard C enumeration (enum). It assigns distinct ID numbers to every type of neural network layer your framework supports.
                                                                                       When the code processes a generic layer, it reads this enum tag first to determine what structural configuration math it needs to
                                                                                       apply.
    LINEAR,
    RELU,
    CONV1D,
    CONV1D_TRANSPOSED,
    MAXPOOL1D,
    AVGPOOL1D,
    SOFTMAX,
    FLATTEN,
    QUANTIZATION,
    ADAPTIVE_AVGPOOL1D,
    DROPOUT,
    LAYERNORM
} layerType_t;

typedef enum layerQType { FLOAT_LAYER, ASYM_LAYER } layerQType_t;

typedef union layerConfig {                                                     //A Union is a special container where all internal pointer members share the exact same memory address.The Reason: A single layer can only 
                                                                                  be one thing at a time (it cannot be a LINEAR layer and a MAXPOOL1D layer simultaneously).The Benefit: Instead of allocating massive chunks
                                                                                  of heap memory to hold variables for every single possible layer type, a union only takes up enough memory to hold one single pointer 
                                                                                  (usually 8 bytes on a 64-bit computer). It dynamically shifts its personality depending on which pointer you target.
    linearConfig_t *linear;
    reluConfig_t *relu;
    softmaxConfig_t *softmax;
    conv1dConfig_t *conv1d;
    conv1dTransposedConfig_t *conv1dTransposed;
    maxPool1dConfig_t *maxPool1d;
    avgPool1dConfig_t *avgPool1d;
    adaptiveAvgPool1dConfig_t *adaptiveAvgPool1d;
    dropoutConfig_t *dropout;
    layerNormConfig_t *layerNorm;
    quantizationConfig_t *quantization;
} layerConfig_t;

typedef struct layer {                                                                                 //This ties the components together. Every single layer in your neural network will be initialized as a layer_t.It
                                                                                                         contains the identity tag (type) telling you what it is.It contains the polymorphic data box (config) holding its 
                                                                                                         weights, dimensions, or specific parameter variables.
    layerType_t type;
    layerConfig_t *config;
} layer_t;

typedef void (*forwardFn_t)(layer_t *layer, tensor_t *inputTensor, tensor_t *outputTensor);            //These statements define type definitions for Function Pointers. In simple terms, they treat function behaviors
                                                                                                         like variables that can be passed around.forward: The interface for running data straight through the layer to 
                                                                                                         generate predictions.backward: The interface for calculating mathematical derivatives during neural network 
                                                                                                         backpropagation (training) to adjust weights.calcOutputShape: A utility function that determines how big the output
                                                                                                         tensor needs to be based on the shape of the incoming input tensor.
typedef void (*backwardFn_t)(layer_t *layer, tensor_t *forwardInput, tensor_t *loss,
                             tensor_t *propLoss);
typedef void (*calcOutputShapeFn_t)(layer_t *layer, shape_t *inputShape, shape_t *outputShape);

typedef struct layerFunctions {                                                                         //This is the centerpiece of the polymorphic architecture, mimicking a C++ Virtual Method Table (V-Table).The
                                                                                                          extern array means that inside a corresponding .c source file, there is a giant lookup table indexed exactly by 
                                                                                                          your layerType_t enum values.This structure allows the library to run abstract execution loops without complex 
                                                                                                          switch or if/else statement branches:
    forwardFn_t forward;
    backwardFn_t backward;
    calcOutputShapeFn_t calcOutputShape;
} layerFunctions_t;

extern layerFunctions_t layerFunctions[];

void initLayer(layer_t *layer, layerType_t layerType, layerConfig_t *config);                           //This function serves as the construction mechanic. It takes an uninitialized pointer block, sets its identity 
                                                                                                          marker to the specified layerType, and binds the corresponding configuration metadata pointers.

#endif
