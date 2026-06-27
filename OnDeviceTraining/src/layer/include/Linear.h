#ifndef ENV5_RUNTIME_LINEAR_H
#define ENV5_RUNTIME_LINEAR_H
#include <stdbool.h>

#include "Tensor.h"

typedef struct layer layer_t;

typedef struct linearConfig {                                                                                //This structure holds all the state data, trainable parameters, and metadata configurations required to manage
                                                                                                               a single Linear layer instance:weights and bias: Pointers to the layer's learnable parameters. The weights
                                                                                                               represent the connection strengths between input and output neurons, while the bias represents the trainable
                                                                                                               offset.Quantization Contexts (forwardQ, weightGradQ, etc.): Separate quantization metadata structures for 
                                                                                                               different stages of the execution graph (Forward pass, Weight updates, Bias updates, and Loss propagation). 
                                                                                                               This allows different parts of the calculation graph to scale or compress dynamically.ownsQuantizations Flag:
                                                                                                               A memory lifecycle tracking safety mechanism. If set to true, the layer's cleanup destructor function takes
                                                                                                               responsibility for freeing the memory of the sub-quantization configurations automatically. If false, it 
                                                                                                               treats them as shared references managed by an external parent engine block.
    parameter_t *weights;
    parameter_t *bias;

    quantization_t *forwardQ;
    quantization_t *weightGradQ;
    quantization_t *biasGradQ;
    quantization_t *propLossQ;

    bool ownsQuantizations; /* true → free* will tear down forwardQ/weightGradQ/biasGradQ/propLossQ
                               and their qConfigs */
} linearConfig_t;

void linearInitConfig(linearConfig_t *linearConfig, parameter_t *weights, parameter_t *bias,
                      quantization_t *forwardQ, quantization_t *weightGradQ,
                      quantization_t *biasGradQ, quantization_t *propLossQ);

// IMPORTANT: Assumes all tensors have FLOAT32 quantization
void linearForwardFloat(tensor_t *w, tensor_t *b, tensor_t *input, tensor_t *output);                           //linearForwardFloat: The high-precision routine. It bypasses quantization scaling and maps directly to the 
                                                                                                                  floating-point matrix math algorithms we reviewed earlier (matmulFloat32TensorsWithBias).
                                                                                                                  linearForwardSymInt32: The highly optimized embedded routine. It processes compressed integer weights and
                                                                                                                  activations, leveraging fast hardware-level integer multiply-accumulate registers.linearForward: The generic
                                                                                                                  polymorphic wrapper. It conforms precisely to the forwardFn_t signature defined in your layout plugin 
                                                                                                                  manager (ODT_Layer.h). When triggered by the network graph loop, this function reads the data profiles of 
                                                                                                                  incoming tensors and dynamically routes the execution to either the Float or SymInt32 core functions.
// IMPORTANT: Assumes all tensors have SYM_INT32 quantization
void linearForwardSymInt32(tensor_t *w, tensor_t *b, tensor_t *input, tensor_t *output);
// IMPORTANT: Used for mismatched quantizations
void linearForward(layer_t *linearLayer, tensor_t *input, tensor_t *output);

// IMPORTANT: Assumes all tensors have FLOAT32 quantization
void backwardFloat(linearConfig_t *linearConfig, tensor_t *forwardInput, tensor_t *loss,
                   tensor_t *propLossTensor);
// IMPORTANT: Assumes all tensors have SYM_INT32 quantization
void backwardSymInt32(linearConfig_t *linearConfig, tensor_t *forwardInput, tensor_t *loss,
                      tensor_t *propLossTensor);
// IMPORTANT: Used for mismatched quantizations
void linearBackward(layer_t *linearLayer, tensor_t *forwardInput, tensor_t *loss,
                    tensor_t *propLossTensor);                                                                  //Just like the forward companion, this generic function unifies the workflow. It reads the structural parameters
                                                                                                                  packed into linearLayer, invokes the gradient calculators sequentially, and routes execution to either the
                                                                                                                  Float or SymInt32 math backends.

void linearCalcWeightGradsFloat32(tensor_t *loss, tensor_t *forwardInput, tensor_t *weightGrads);              //Calculates how much the error changes with respect to each individual connection weight. It multiplies the 
                                                                                                                 incoming error matrix (loss) by the transposed input values saved from the forward pass (forwardInput).
void linearCalcBiasGradsFloat32(tensor_t *biasGrads, tensor_t *loss);                                          //Calculates how much the error changes with respect to the bias offsets. Because biases add linearly, this 
                                                                                                                 operation simplifies to accumulating or summing the errors across the batch rows
void linearCalcPropLossFloat32(tensor_t *weights, tensor_t *loss, tensor_t *propLoss);                         //Computes the error gradient relative to the layer's inputs. This passes the error backward down the graph 
                                                                                                                 pipeline to preceding layers, multiplying the incoming loss matrix by the layer's internal weights.

void linearCalcWeightGradsSymInt32(tensor_t *loss, tensor_t *forwardInput, tensor_t *weightGrads);
void linearCalcBiasGradsSymInt32(tensor_t *biasGrads, tensor_t *loss);
void linearCalcPropLossSymInt32(tensor_t *weights, tensor_t *loss, tensor_t *propLoss);

void linearCalcOutputShape(layer_t *linearLayer, shape_t *inputShape, shape_t *outputShape);                 //Before any math can execute, memory must be explicitly allocated in a C environment. This routine looks at the
                                                                                                               rows of the inputShape (batch size) and the structural parameters inside the layer's weights matrix to 
                                                                                                               calculate exactly how large the destination outputShape buffer needs to be, preventing memory access bounds 
                                                                                                               faults.

#endif // ENV5_RUNTIME_LINEAR_H
