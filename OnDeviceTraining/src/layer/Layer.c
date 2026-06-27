#define SOURCE_FILE "LAYER"

#include "Layer.h"
#include "AdaptiveAvgPool1d.h"
#include "AvgPool1d.h"
#include "Conv1d.h"
#include "Conv1dTransposed.h"
#include "Dropout.h"
#include "Flatten.h"
#include "LayerNorm.h"
#include "Linear.h"
#include "MaxPool1d.h"
#include "QuantizationLayer.h"
#include "Relu.h"
#include "Softmax.h"

layerFunctions_t layerFunctions[] = {                                                                  //This technique uses a powerful C feature called Designated Initializers (indicated by the brackets [LINEAR]).Standard
                                                                                                         Arrays: In a regular C array, items are organized sequentially by numbers (\(0, 1, 2...\)). If you rearrange your 
                                                                                                         enum list, a standard array will map to the wrong locations and break your application.Designated Arrays: By 
                                                                                                         using [LINEAR], you tell the computer: "Put this group of function pointers exactly at the slot number that matches
                                                                                                         the LINEAR value inside our identity enum tag."This maps your layer identity enum cleanly to three distinct 
                                                                                                         behaviors:Forward Pass: The mathematical logic to run data forward (generate predictions).Backward Pass: The 
                                                                                                         calculus derivative math used to adjust weights during training.Shape Calculator: The layout logic used to 
                                                                                                         determine how large the output memory block needs to be
    [LINEAR] = {linearForward, linearBackward, linearCalcOutputShape},
    [RELU] = {reluForward, reluBackward, reluCalcOutputShape},
    [CONV1D] = {conv1dForward, conv1dBackward, conv1dCalcOutputShape},
    [CONV1D_TRANSPOSED] = {conv1dTransposedForward, conv1dTransposedBackward,
                           conv1dTransposedCalcOutputShape},
    [MAXPOOL1D] = {maxPool1dForward, maxPool1dBackward, maxPool1dCalcOutputShape},
    [AVGPOOL1D] = {avgPool1dForward, avgPool1dBackward, avgPool1dCalcOutputShape},
    [SOFTMAX] = {softmaxForward, softmaxBackward, softmaxCalcOutputShape},
    [FLATTEN] = {flattenForward, flattenBackward, flattenCalcOutputShape},
    [QUANTIZATION] = {quantizationForward, quantizationBackward, quantizationCalcOutputShape},
    [ADAPTIVE_AVGPOOL1D] = {adaptiveAvgPool1dForward, adaptiveAvgPool1dBackward,
                            adaptiveAvgPool1dCalcOutputShape},
    [DROPOUT] = {dropoutForward, dropoutBackward, dropoutCalcOutputShape},
    [LAYERNORM] = {layerNormForward, layerNormBackward, layerNormCalcOutputShape}};

void initLayer(layer_t *layer, layerType_t type, layerConfig_t *config) {                               //This is a standard constructor function used to build a new network block. It takes a raw, blank memory structural
                                                                                                          pointer (layer) and:Sets its identity tag variable (type) so the lookup table knows how to route it later.Binds its
                                                                                                          unique parameter values pointer (config) containing specific variables like dimensions, weights, or thresholds.
    layer->type = type;
    layer->config = config;
}
