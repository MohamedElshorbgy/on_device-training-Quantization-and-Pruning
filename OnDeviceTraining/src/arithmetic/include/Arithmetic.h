#ifndef ENV5_RUNTIME_TENSOR_MATH_H
#define ENV5_RUNTIME_TENSOR_MATH_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "Tensor.h"

typedef int32_t (*int32ElementArithmeticFunc_t)(int32_t a, int32_t b);                                  //These declarations define generic blueprints for math operators. Instead of writing separate, massive loops for 
                                                                                                          tensor addition, subtraction, multiplication, and division, the loops are written once inside a core engine function.
                                                                                                          The engine then receives one of these function pointers to determine the actual math operation to execute.a: 
                                                                                                          An element from Tensor A (or the scalar base).b: An element from Tensor B.
typedef float (*floatElementArithmeticFunc_t)(float a, float b);

bool doDimensionsMatch(tensor_t *a, tensor_t *b);                                                       //doDimensionsMatch: A critical defensive guard. For standard point-wise arithmetic, both input tensors must share
                                                                                                          identical layouts (e.g., you cannot add a [2, 4] matrix straight to a [3, 3] matrix). This returns true only if the
                                                                                                          shapes are perfectly aligned.orderDims: Sorts or extracts the dimensional structures based on the tensor's native 
                                                                                                          layout properties (shape->orderOfDimensions), which is necessary for flattening multi-dimensional spaces accurately.

void orderDims(tensor_t *tensor, size_t *orderedDims);

size_t getDimensionsByIndex(tensor_t *tensor, size_t index);
size_t calcTensorIndexByIndices(size_t numberOfDimensions, size_t *dimensions, size_t *indices);    //: Converts a multi-dimensional coordinate array (e.g., [0, 14, 22, 3]) into a standard flat sequential index number 
                                                                                                       (e.g., element 4250).

void calcIndicesByRawIndex(size_t numberOfDims, size_t *dims, size_t rawIndex, size_t *indices);   //Purpose: Performs the inverse operation. It takes a flat memory index (like element 4250) and deconstructs it back into
                                                                                                      a multi-dimensional coordinate array ([0, 14, 22, 3]). This is crucial when calculating offsets for sliding convolutional
                                                                                                      windows or pooling operations.

size_t calcElementIndexByIndices(size_t numberOfDims, size_t *dims, size_t *indices,                
                                 size_t *orderOfDimensions);                                           //Purpose: This is the most vital indexing function. It maps multidimensional coordinates to a flat memory slot 
                                                                                                         while respecting custom memory strides (orderOfDimensions). This allows your math functions to correctly calculate
                                                                                                         elements even if one tensor is stored Row-Major and the other is Column-Major or transposed!

void int32PointWiseArithmetic(tensor_t *aTensor, tensor_t *bTensor,
                              int32ElementArithmeticFunc_t arithmeticFunc, tensor_t *outputTensor);     //Standard (Out-of-place): Takes aTensor and bTensor, runs them through the loop with arithmeticFunc, and populates 
                                                                                                          the results into a distinct third container, outputTensor
void floatPointWiseArithmetic(tensor_t *aTensor, tensor_t *bTensor,
                              floatElementArithmeticFunc_t arithmeticFunc, tensor_t *outputTensor);

void int32PointWiseArithmeticInplace(tensor_t *aTensor, tensor_t *bTensor,                               //In-place: Overwrites the results directly on top of aTensor (\(A[i] = A[i] \text{ op } B[i]\)). This completely
                                                                                                           eliminates the need to allocate memory for an output tensor, saving substantial RAM.
                                     int32ElementArithmeticFunc_t arithmeticFunc);
void floatPointWiseArithmeticInplace(tensor_t *aTensor, tensor_t *bTensor,
                                     floatElementArithmeticFunc_t arithmeticFunc);

void int32ElementWithTensorArithmetic(tensor_t *aTensor, int32_t x,                                      //These functions apply a single fixed value (x) across every single element inside a target tensor 
                                                                                                           (e.g., \(Output[i] = A[i] \text{ op } x\)). This is heavily used for adding fixed biases to neural layers, 
                                                                                                           or multiplying an entire activation field by a scaling factor. Mirroring the point-wise structures, these 
                                                                                                          are cleanly split into integer (int32_t) and floating-point (float) configurations, as well as out-of-place 
                                                                                                          and memory-saving in-place variations.
                                      int32ElementArithmeticFunc_t arithmeticFunc,
                                      tensor_t *outputTensor);
void floatElementWithTensorArithmetic(tensor_t *aTensor, float x,
                                      floatElementArithmeticFunc_t arithmeticFunc,
                                      tensor_t *outputTensor);

void int32ElementWithTensorArithmeticInplace(tensor_t *aTensor, int32_t x,
                                             int32ElementArithmeticFunc_t arithmeticFunc);
void floatElementWithTensorArithmeticInplace(tensor_t *aTensor, float x,
                                             floatElementArithmeticFunc_t arithmeticFunc);

#endif // ENV5_RUNTIME_TENSOR_MATH_H
