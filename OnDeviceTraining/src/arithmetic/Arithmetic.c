#define SOURCE_FILE "ARITHMETIC"

#include <stdio.h>
#include <stdlib.h>

#include "Arithmetic.h"
#include "Common.h"
#include "DTypes.h"
#include "Matmul.h"

size_t getDimensionsByIndex(tensor_t *tensor, size_t index) {                                    //Purpose: Finds the size of a specific logical dimension (axis) based on its semantic layout position rather than its 
                                                                                                   physical position in memory.Mechanism: It loops through the metadata array orderOfDimensions. If it finds a match for the
                                                                                                   target logical index, it returns the corresponding size from the dimensions array.Error Handling: If the requested logical
                                                                                                   index is invalid, it throws a macro-driven error (PRINT_ERROR) and abruptly terminates execution with exit code 1.
    size_t numberOfDims = tensor->shape->numberOfDimensions;
    for (size_t i = 0; i < numberOfDims; i++) {
        if (tensor->shape->orderOfDimensions[i] == index) {
            return tensor->shape->dimensions[i];
        }
    }
    PRINT_ERROR("Tensor doesn't have %lu dimensions!", index);
    exit(1);
}
 
void orderDims(tensor_t *tensor, size_t *orderedDims) {                                          //Purpose: Generates an ordered array of physical dimensions for flat index parsing.Mechanism: It iterates over the tensor's
                                                                                                   rank (numberOfDimensions) and fills the external orderedDims array sequentially using the getDimensionsByIndex helper.
    for (size_t i = 0; i < tensor->shape->numberOfDimensions; i++) {
        orderedDims[i] = getDimensionsByIndex(tensor, i);
    }
}

bool doDimensionsMatch(tensor_t *a, tensor_t *b) {                                               //Purpose: Assures that two tensors are element-wise broadcast-compatible or strictly identical in shape before executing
                                                                                                   element-wise operations (e.g., adding two tensors).Mechanism:It first compares tensor ranks (numberOfDimensions). If they
                                                                                                   differ, execution terminates.Allocates variable-length arrays (aOrderedDims, bOrderedDims) on the stack to store the 
                                                                                                   canonical physical dimensions.Iterates through the dimensions element-by-element. Returns false if any dimension size 
                                                                                                   mismatches; returns true if identical.
    size_t aNumberOfDims = a->shape->numberOfDimensions;
    size_t bNumberOfDims = b->shape->numberOfDimensions;

    if (aNumberOfDims != bNumberOfDims) {
        PRINT_ERROR("Rank mismatch: %lu vs %lu\n", aNumberOfDims, bNumberOfDims);
        exit(1);
    }

    size_t aOrderedDims[aNumberOfDims];
    size_t bOrderedDims[bNumberOfDims];

    orderDims(a, aOrderedDims);
    orderDims(b, bOrderedDims);

    for (size_t i = 0; i < aNumberOfDims; i++) {
        if (aOrderedDims[i] != bOrderedDims[i]) {
            PRINT_DEBUG("Dim 1: %lu, Dims 2: %lu\n", aOrderedDims[i], bOrderedDims[i]);
            return false;
        }
    }
    return true;
}

size_t calcTensorIndexByIndices(size_t numberOfDimensions, size_t *dimensions, size_t *indices) {        //Purpose: Implements row-major (C-style) continuous indexing. It maps an array of dimensional coordinates
                                                                                                           (like [z, y, x]) to a 1D index array pointer.Mechanism:It starts tracking from the last dimension 
                                                                                                           (numberOfDimensions - 1) and loops backward.Accumulates indices into index by multiplying coordinates by a
                                                                                                           shifting dimension stride offset.
    size_t index = indices[numberOfDimensions - 1];
    size_t offset = dimensions[numberOfDimensions - 1];
    for (int i = (int)numberOfDimensions - 2; i >= 0; i--) {
        index += indices[i] * offset;
        offset *= dimensions[i];
    }
    return index;
}

void calcIndicesByRawIndex(size_t numberOfDims, size_t *dims, size_t rawIndex, size_t *indices) {        //Purpose: Converts a single continuous 1D raw memory index offset back into multi-dimensional coordinates.Mechanism:
                                                                                                           Calculates the total volume of elements (offset).Iterates forward through dimensions.Divides and takes remainders 
                                                                                                           (restIndex -= indices[i] * offset) to progressively peel off coordinate offsets for each axis.

    size_t offset = 1;
    // equal to numberOfElements
    for (size_t i = 0; i < numberOfDims; i++) {
        offset *= dims[i];
    }

    size_t restIndex = rawIndex;
    for (size_t i = 0; i < numberOfDims; i++) {
        offset /= dims[i];
        indices[i] = restIndex / offset;
        restIndex -= indices[i] * offset;
    }
}

size_t calcElementIndexByIndices(size_t numberOfDims, size_t *dims, size_t *indices,        
                                 size_t *orderOfDimensions) {                                                //Purpose: Maps generic logical index coordinates to their exact physical data pointer locations inside 
                                                                                                               non-contiguous or transposed layout structures.Mechanism:Captures total volume offsets.Reorders user-provided 
                                                                                                               logical target points into an intermediate container array (orderedIndices) matching the memory dimension layout 
                                                                                                               map (orderOfDimensions).Accumulates stride offsets using row-major calculation principles on the mutated order 
                                                                                                               array maps.
    size_t offset = 1;
    // equal to numberOfElements
    for (size_t i = 0; i < numberOfDims; i++) {
        offset *= dims[i];
    }

    size_t orderedIndices[numberOfDims];
    for (size_t d = 0; d < numberOfDims; d++) {
        orderedIndices[orderOfDimensions[d]] = indices[d];
    }

    size_t outputIndex = 0;
    for (size_t i = 0; i < numberOfDims; i++) {
        offset /= dims[i];
        outputIndex += orderedIndices[i] * offset;
    }
    return outputIndex;
}

void int32PointWiseArithmetic(tensor_t *aTensor, tensor_t *bTensor,
                              int32ElementArithmeticFunc_t arithmeticFunc, tensor_t *outputTensor) {       //Purpose: Performs math on aTensor and bTensor, then writes the results to a separate, pre-allocated outputTensor.
                                                                                                             Safety: Preserves both input tensors completely.
    if (!doDimensionsMatch(aTensor, bTensor)) {
        PRINT_ERROR("Dimensions don't match!");
        exit(1);
    }

    size_t numberOfElements = calcNumberOfElementsByTensor(aTensor);
    size_t bytesPerElement = sizeof(int32_t);
    size_t numberOfDims = aTensor->shape->numberOfDimensions;
    size_t *aDims = aTensor->shape->dimensions;
    size_t *bDims = bTensor->shape->dimensions;

    size_t aOrderedDims[numberOfDims];
    size_t bOrderedDims[numberOfDims];

    orderDims(aTensor, aOrderedDims);
    orderDims(bTensor, bOrderedDims);

    for (size_t i = 0; i < numberOfElements; i++) {
        size_t aIndices[numberOfDims];

        calcIndicesByRawIndex(numberOfDims, aDims, i, aIndices);

        size_t aElementIndex = calcElementIndexByIndices(numberOfDims, aDims, aIndices,
                                                         aTensor->shape->orderOfDimensions);

        size_t bIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, bDims, i, bIndices);
        size_t bElementIndex = calcElementIndexByIndices(numberOfDims, bDims, bIndices,
                                                         bTensor->shape->orderOfDimensions);

        size_t aByteIndex = aElementIndex * bytesPerElement;
        size_t bByteIndex = bElementIndex * bytesPerElement;

        int32_t aValue = readBytesAsInt32(&aTensor->data[aByteIndex]);
        int32_t bValue = readBytesAsInt32(&bTensor->data[bByteIndex]);

        int32_t result = arithmeticFunc(aValue, bValue);

        size_t outputByteIndex = i * bytesPerElement;

        writeInt32ToByteArray(result, &outputTensor->data[outputByteIndex]);
    }
}

// Important: result will be written into aTensor datafield
void int32PointWiseArithmeticInplace(tensor_t *aTensor, tensor_t *bTensor,
                                     int32ElementArithmeticFunc_t arithmeticFunc) {                    //Purpose: Performs math on aTensor and bTensor, then overwrites aTensor's memory with the results.Caution 
                                                                                                         (The In-Place Mutation Bug): Because it writes back to aTensor sequentially while iterating, this function assumes 
                                                                                                         outputByteIndex follows a predictable, contiguous 1D path (i * bytesPerElement). If aTensor has a non-standard custom 
                                                                                                         memory layout (orderOfDimensions), this sequential overwrite will destroy data required for subsequent iterations of 
                                                                                                         the loop.
    if (!doDimensionsMatch(aTensor, bTensor)) {                                                         //Verifies that both tensors have the exact same rank and matching dimension lengths. If they do not match, the program
                                                                                                           aborts.
        PRINT_ERROR("Dimensions don't match");
        exit(1);
    }

    size_t numberOfElements = calcNumberOfElementsByTensor(aTensor);
    size_t bytesPerElement = sizeof(int32_t);
    size_t numberOfDims = aTensor->shape->numberOfDimensions;
    size_t *aDims = aTensor->shape->dimensions;
    size_t *bDims = bTensor->shape->dimensions;

    size_t aOrderedDims[numberOfDims];
    size_t bOrderedDims[numberOfDims];

    orderDims(aTensor, aOrderedDims);
    orderDims(bTensor, bOrderedDims);

    for (size_t i = 0; i < numberOfElements; i++) { 
        size_t aIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, aDims, i, aIndices);                                        //Takes the flat loop sequence index i.Converts i into absolute coordinates (e.g., [row, col, channel]) via 
                                                                                                          calcIndicesByRawIndex.Translates those multidimensional coordinates into the specific physical memory slot 
                                                                                                          (aElementIndex) via calcElementIndexByIndices, taking the internal tensor layout order into account.
        size_t aElementIndex = calcElementIndexByIndices(numberOfDims, aDims, aIndices,
                                                         aTensor->shape->orderOfDimensions);

        size_t bIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, bDims, i, bIndices);
        size_t bElementIndex = calcElementIndexByIndices(numberOfDims, bDims, bIndices,
                                                         bTensor->shape->orderOfDimensions);

        size_t aByteIndex = aElementIndex * bytesPerElement;                                           //Multiplies the element position by sizeof(int32_t) (4 bytes) to get the exact raw byte position within the 
                                                                                                         underlying memory array (tensor->data).
        size_t bByteIndex = bElementIndex * bytesPerElement;

        int32_t aValue = readBytesAsInt32(&aTensor->data[aByteIndex]);                                  //Rather than directly casting a raw pointer, it calls a helper function readBytesAsInt32. This protects the engine 
                                                                                                          from alignment faults and hardware endianness differences.
        int32_t bValue = readBytesAsInt32(&bTensor->data[bByteIndex]);

        int32_t result = arithmeticFunc(aValue, bValue);                                               //Invokes a function pointer containing the specific operation. This decoupling allows the same loop to handle addition,
                                                                                                         subtraction, division, or custom bitwise scaling operations dynamically.

        size_t outputByteIndex = i * bytesPerElement;                                                  //Serializes the evaluation output into a flat, contiguous target memory layout.

        writeInt32ToByteArray(result, &aTensor->data[outputByteIndex]);
    }
}

void int32ElementWithTensorArithmeticInplace(tensor_t *tensor, int32_t x,
                                             int32ElementArithmeticFunc_t arithmeticFunc) {            //Purpose: Modifies a 32-bit integer tensor by applying a scalar value x (e.g., adding 5 or multiplying by 10) 
                                                                                                         directly to every single element.Mechanism: Loops contiguously through the raw memory buffer, reads the value, applies
                                                                                                         the function pointer arithmeticFunc(currentElement, x), and immediately overwrites the data slot.         

    size_t numberOfElements = calcNumberOfElementsByTensor(tensor);
    size_t bytesPerElement = sizeof(int32_t);

    for (size_t i = 0; i < numberOfElements; i++) {
        size_t byteIndex = i * bytesPerElement;
        int32_t currentElement = readBytesAsInt32(&tensor->data[byteIndex]);
        int32_t result = arithmeticFunc(currentElement, x);

        writeInt32ToByteArray(result, &tensor->data[byteIndex]);
    }
}

void int32ElementWithTensorArithmetic(tensor_t *tensor, int32_t x,
                                      int32ElementArithmeticFunc_t arithmeticFunc,
                                      tensor_t *outputTensor) {                                       //Purpose: Performs the same scalar operation as above, but preserves the original tensor and streams the outputs to a 
                                                                                                        dedicated outputTensor.

    size_t numberOfElements = calcNumberOfElementsByTensor(tensor);
    size_t bytesPerElement = sizeof(int32_t);

    for (size_t i = 0; i < numberOfElements; i++) {
        size_t byteIndex = i * bytesPerElement;
        int32_t currentElement = readBytesAsInt32(&tensor->data[byteIndex]);
        int32_t result = arithmeticFunc(currentElement, x);

        writeInt32ToByteArray(result, &outputTensor->data[byteIndex]);
    }
}

void floatPointWiseArithmetic(tensor_t *aTensor, tensor_t *bTensor,
                              floatElementArithmeticFunc_t arithmeticFunc, tensor_t *outputTensor) {      //Purpose: Executes element-wise math between two multidimensional tensors using float 
                                                                                                            (usually 4-byte single-precision values) instead of integers.Mechanism: Mirrors the complex index translation
                                                                                                            architecture from your previous int32 point-wise function to safely handle transpositions and dimension 
                                                                                                            reordering
    if (!doDimensionsMatch(aTensor, bTensor)) {
        PRINT_ERROR("Dimensions don't match");
        exit(1);
    }

    size_t numberOfElements = calcNumberOfElementsByTensor(aTensor);
    size_t bytesPerElement = sizeof(float);
    size_t numberOfDims = aTensor->shape->numberOfDimensions;
    size_t *aDims = aTensor->shape->dimensions;
    size_t *bDims = bTensor->shape->dimensions;

    size_t aOrderedDims[numberOfDims];
    size_t bOrderedDims[numberOfDims];

    orderDims(aTensor, aOrderedDims);
    orderDims(bTensor, bOrderedDims);

    for (size_t i = 0; i < numberOfElements; i++) {
        size_t aIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, aDims, i, aIndices);
        size_t aElementIndex = calcElementIndexByIndices(numberOfDims, aDims, aIndices,
                                                         aTensor->shape->orderOfDimensions);

        size_t bIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, bDims, i, bIndices);
        size_t bElementIndex = calcElementIndexByIndices(numberOfDims, bDims, bIndices,
                                                         bTensor->shape->orderOfDimensions);

        size_t aByteIndex = aElementIndex * bytesPerElement;
        size_t bByteIndex = bElementIndex * bytesPerElement;

        float aValue = readBytesAsFloat(&aTensor->data[aByteIndex]);
        float bValue = readBytesAsFloat(&bTensor->data[bByteIndex]);

        float result = arithmeticFunc(aValue, bValue);

        size_t outputByteIndex = i * bytesPerElement;

        writeFloatToByteArray(result, &outputTensor->data[outputByteIndex]);
    }
}

void floatPointWiseArithmeticInplace(tensor_t *aTensor, tensor_t *bTensor,
                                     floatElementArithmeticFunc_t arithmeticFunc) {              //Purpose: Performs element-wise math between two floating-point tensors and saves the final calculations directly back into
                                                                                                   aTensor.Mechanism: It maps complex non-contiguous layouts for both inputs using the library's coordinate mapping pipeline.
                                                                                                   However, it forces the output back into a flat, contiguous layout in aTensor sequence step by sequence step
    if (!doDimensionsMatch(aTensor, bTensor)) {
        PRINT_ERROR("Dimensions don't match");
        exit(1);
    }

    size_t numberOfElements = calcNumberOfElementsByTensor(aTensor);
    size_t bytesPerElement = sizeof(float);
    size_t numberOfDims = aTensor->shape->numberOfDimensions;
    size_t *aDims = aTensor->shape->dimensions;
    size_t *bDims = bTensor->shape->dimensions;

    size_t aOrderedDims[numberOfDims];
    size_t bOrderedDims[numberOfDims];

    orderDims(aTensor, aOrderedDims);
    orderDims(bTensor, bOrderedDims);

    for (size_t i = 0; i < numberOfElements; i++) {

        size_t aIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, aDims, i, aIndices);
        size_t aElementIndex = calcElementIndexByIndices(numberOfDims, aDims, aIndices,
                                                         aTensor->shape->orderOfDimensions);

        size_t bIndices[numberOfDims];
        calcIndicesByRawIndex(numberOfDims, bDims, i, bIndices);

        size_t bElementIndex = calcElementIndexByIndices(numberOfDims, bDims, bIndices,
                                                         bTensor->shape->orderOfDimensions);

        size_t aByteIndex = aElementIndex * bytesPerElement;
        size_t bByteIndex = bElementIndex * bytesPerElement;

        float aValue = readBytesAsFloat(&aTensor->data[aByteIndex]);
        float bValue = readBytesAsFloat(&bTensor->data[bByteIndex]);

        float result = arithmeticFunc(aValue, bValue);

        size_t outputByteIndex = i * bytesPerElement;

        writeFloatToByteArray(result, &aTensor->data[outputByteIndex]);
    }
}

void floatElementWithTensorArithmetic(tensor_t *tensor, float x,
                                      floatElementArithmeticFunc_t arithmeticFunc,
                                      tensor_t *outputTensor) {                                     //Purpose: Broadly applies a single floating-point scalar value x to an entire float tensor, keeping the original tensor
                                                                                                      untouched and writing results to outputTensor.Mechanism: Bypasses dimension mappings entirely. It runs directly through
                                                                                                      the physical memory blocks sequentially.

    size_t numberOfElements = calcNumberOfElementsByTensor(tensor);
    size_t bytesPerElement = sizeof(float);

    for (size_t i = 0; i < numberOfElements; i++) {
        size_t byteIndex = i * bytesPerElement;
        float currentValue = readBytesAsFloat(&tensor->data[byteIndex]);
        float result = arithmeticFunc(currentValue, x);

        writeFloatToByteArray(result, &outputTensor->data[byteIndex]);
    }
}

void floatElementWithTensorArithmeticInplace(tensor_t *tensor, float x,
                                             floatElementArithmeticFunc_t arithmeticFunc) {          //Purpose: Modifies a floating-point tensor directly in memory by combining every internal element with a single scalar
                                                                                                       value x (e.g., multiplying all values by a scalar weight factor of 0.5f).Mechanism: Reads, calculates, and overwrites
                                                                                                       each individual element block using a flat 1D sequence loop.

    size_t numberOfElements = calcNumberOfElementsByTensor(tensor);
    size_t bytesPerElement = sizeof(float);

    for (size_t i = 0; i < numberOfElements; i++) {
        size_t byteIndex = i * bytesPerElement;
        float currentValue = readBytesAsFloat(&tensor->data[byteIndex]);

        float result = arithmeticFunc(currentValue, x);

        writeFloatToByteArray(result, &tensor->data[byteIndex]);
    }
}
