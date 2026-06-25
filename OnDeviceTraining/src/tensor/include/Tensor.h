#ifndef ODT_TENSOR_H
#define ODT_TENSOR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "Quantization.h"

typedef void *tensorStorageId;

typedef struct shape {                                                                               //numberOfDimensions: The rank of the tensor (e.g., 1 for a vector, 2 for a matrix, 4 for an image batch like
                                                                                                       [Batch, Height, Width, Channels]).dimensions: An array tracking the size of each dimension (e.g., [1, 28, 28, 3])
                                                                                                       .orderOfDimensions: A specialized layout tracker. This dictates memory stride configurations, allowing the engine 
                                                                                                        to know if the data is stored in Row-Major format, Column-Major format, or custom permutations
    size_t numberOfDimensions;
    size_t *dimensions;
    size_t *orderOfDimensions;
} shape_t;

typedef enum { SPARSITY_TYPE_1, SPARSITY_TYPE_2 } sparsityType_t;

typedef struct sparsityConfig {
} sparsityConfig;

typedef struct sparsity {                                                                              //Purpose: In neural networks, many weight matrices contain a high percentage of zeros (0.0). Sparsity mechanics compress
                                                                                                         these structures so the engine completely skips computing or saving zeroed weights, saving immense processing power.
                                                                                                         Like your quantization framework, this uses a generic configuration structure pointer.
    sparsityType_t type;
    sparsityConfig *config;
} sparsity_t;

typedef struct tensor {                                                                                //This is the master object. It encapsulates everything required to interpret raw memory:data: The raw byte array
                                                                                                         payload managed by your StorageApi and DataStorage systems.shape: Tells the machine how to slice the flat data pointer
                                                                                                         into dimensions.quantization: Dictates how to mathematically parse the raw bytes back into real-world floating point
                                                                                                         numbers.sparsity: Flags compressed data arrangements.
    uint8_t *data;
    shape_t *shape;
    quantization_t *quantization;
    sparsity_t *sparsity;
} tensor_t;

typedef struct parameter {                                                                              //Purpose: Combines a weight layer (param) together with its corresponding gradient tensor (grad). This structure 
                                                                                                          is vital if the embedded system performs On-Device Training (ODT), allowing it to track error derivatives back 
                                                                                                          through the layers during backward propagation
    tensor_t *param;
    tensor_t *grad;
} parameter_t;

uint32_t getBitmask(uint32_t startbit, uint32_t endbit);                                                 //Purpose: Standard datatypes map neatly to 8, 16, or 32 bits. However, advanced quantization configurations
                                                                                                           often compress data down to sub-byte structures (e.g., 4-bit quantization or 2-bit quantization).Mechanics: These
                                                                                                           functions read and write subsets of bits inside a single byte, allowing multiple quantized parameters to sit tightly
                                                                                                            squeezed side-by-side within the tensor_t->data buffer.

uint8_t writeByte(uint8_t existingData, uint8_t data, uint8_t startbit, uint8_t endbit);

uint8_t readByte(uint8_t data, uint8_t startbit, uint8_t endbit);

void byteConversion(uint8_t *dataIn, size_t dataInBits, uint8_t *dataOut, size_t dataOutBits,
                    size_t numValues);

bool tensorBoolGet(tensor_t const *tensor, size_t flatIndex);
void tensorBoolSet(tensor_t *tensor, size_t flatIndex, bool value);

tensor_t *getParamFromParameter(parameter_t *parameter);
tensor_t *getGradFromParameter(parameter_t *parameter);

size_t calcBytesPerElement(quantization_t *quantization);                                                //Purpose: Bridges structural metrics with your underlying memory allocation layout.Calculation Flow: To allocate
                                                                                                           a raw tensor via your reserveMemory(numberOfBytes) routine, the runtime engine will call 
                                                                                                           calcNumberOfElementsByTensor(tensor) (which multiplies dimensions out, e.g., 1 × 28 × 28 × 3 = 2352 elements)
                                                                                                           and then feeds that number into calcNumberOfBytesForData to evaluate how many total bytes are needed based on the
                                                                                                           target bit-width quantization layout.
size_t calcBitsPerElement(quantization_t *quantization);
size_t calcBytesPerTensor(tensor_t *tensor);
size_t calcNumberOfBytesForData(quantization_t *q, size_t numberOfElements);

size_t calcNumberOfElementsByShape(shape_t *shape);
size_t calcNumberOfElementsByTensor(tensor_t *tensor);
size_t calcNumberOfElementsByParameter(parameter_t *parameter);

void transposeTensor(tensor_t *tensor, size_t dim0Index, size_t dim1Index);

void setTensorValuesForConversion(uint8_t *data, quantization_t *q, tensor_t *originalTensor,
                                  tensor_t *outputTensor);
void setTensorValues(tensor_t *tensor, uint8_t *data, shape_t *shape, quantization_t *quantization,
                     sparsity_t *sparsity);                                                             //setTensorValues: The construct initializer that wires up data buffers, formatting layouts, and algorithmic
                                                                                                          quantizations onto a standalone tensor allocation.transposeTensor: Flips structural dimensions 
                                                                                                          (e.g., changing a shape from M × N to N × M). Rather than physically copying memory contents, a highly optimized
                                                                                                          engine can sometimes execute this just by swapping the values stored within the shape->orderOfDimensions array!
void setParameterValues(parameter_t *parameter, tensor_t *param, tensor_t *grad);
void setOrderOfDimsForNewTensor(size_t numberOfDimensions, size_t *orderOfDimensions);
void setShape(shape_t *shape, size_t *dims, size_t numberOfDims, size_t *orderOfDims);

void printTensor(tensor_t *t);
void printShape(shape_t *shape);

void copyTensor(tensor_t *dest, tensor_t *src);

#endif // ODT_TENSOR_H
