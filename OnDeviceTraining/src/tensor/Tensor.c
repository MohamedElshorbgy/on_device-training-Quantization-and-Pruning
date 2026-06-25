#define SOURCE_FILE "TENSOR"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "Common.h"
#include "DTypes.h"
#include "MinMax.h"
#include "Quantization.h"
#include "Tensor.h"

size_t calcNumberOfElementsByShape(shape_t *shape) {                                       //How it works: It sets a counter to 1 and loops through every value in the shape->dimensions array, multiplying them together.
                                                                                             For a 3D video layer shaped [10, 28, 28], it computes \(10 \times 28 \times 28 = 7,840\) total elements.
    size_t numElem = 1;
    size_t numberOfDimensions = shape->numberOfDimensions;
    size_t *dimensions = shape->dimensions;
    for (size_t i = 0; i < numberOfDimensions; i++) {
        numElem *= dimensions[i];
    }
    return numElem;
}

size_t calcNumberOfElementsByTensor(tensor_t *tensor) {
    return calcNumberOfElementsByShape(tensor->shape);
}

size_t calcNumberOfElementsByParameter(parameter_t *parameter) {
    return calcNumberOfElementsByShape(parameter->param->shape);
}

size_t calcBytesPerElement(quantization_t *quantization) {                                   //How it works: These check the quantization->type enum using a switch statement:For standard types (INT32, FLOAT32, SYM_INT32),
                                                                                               they cleanly return 4 bytes (\(32\) bits).For quantized types (SYM, ASYM), they dynamically read the nested configuration's qBits
                                                                                               value.The Ceiling Logic: In calcBytesPerElement, if a quantized tensor uses an odd bit width like 9-bit quantization, it 
                                                                                               calculates ceil(9.0 / 8.0) and returns 2 bytes, avoiding memory truncation.
    switch (quantization->type) {
    case INT32:
        return sizeof(int32_t);
    case FLOAT32:
        return sizeof(float);
    case SYM_INT32:
        return sizeof(int32_t);
    case SYM: {
        symQConfig_t *symQC = quantization->qConfig;
        return (size_t)ceilf((float)symQC->qBits / 8.0f);
    }
    case ASYM:
        asymQConfig_t *asymQConfig = quantization->qConfig;
        uint32_t qBits = asymQConfig->qBits;
        return ceil((float)qBits / (float)8);
    case BOOL:
        return 1;
    default:
        PRINT_ERROR("Unknown QType!");
        exit(1);
    }
}

size_t calcBitsPerElement(quantization_t *quantization) {
    switch (quantization->type) {
    case INT32:
        return sizeof(int32_t) * 8;
    case FLOAT32:
        return sizeof(float) * 8;
    case SYM_INT32:
        return sizeof(int32_t) * 8;
    case SYM: {
        symQConfig_t *symQC = quantization->qConfig;
        return symQC->qBits;
    }
    case ASYM:
        asymQConfig_t *asymQConfig = quantization->qConfig;
        return asymQConfig->qBits;
    case BOOL:
        return 1;
    default:
        PRINT_ERROR("Unknown QType!");
        exit(1);
    }
}

size_t calcBitsPerTensor(tensor_t *tensor) {
    size_t bitsPerElement = calcBitsPerElement(tensor->quantization);
    size_t numElements = calcNumberOfElementsByShape(tensor->shape);
    return bitsPerElement * numElements;
}

size_t calcBytesPerTensor(tensor_t *tensor) {                                                           //The Bug: calcBytesPerTensor utilizes standard integer division / 8. If you have a 1-bit boolean tensor with 3 
                                                                                                          elements, bitsPerTensor equals 3. 3 / 8 in C integer math results in 0 bytes, causing a critical buffer overflow 
                                                                                                          if used for memory allocation.The Correction: It should use the same ceiling-rounding padding math found in 
                                                                                                          calcNumberOfBytesForData: return (bitsPerTensor + 7) / 8;.
    size_t bitsPerTensor = calcBitsPerTensor(tensor);
    return bitsPerTensor / 8;
}

size_t calcNumberOfBytesForData(quantization_t *q, size_t numberOfElements) {
    switch (q->type) {
    case FLOAT32:
        return numberOfElements * sizeof(float);
    case INT32:
        return numberOfElements * sizeof(int32_t);
    case SYM_INT32:
        return numberOfElements * sizeof(int32_t);
    case SYM:
        return (calcBitsPerElement(q) * numberOfElements + 7) / 8;
    case ASYM:
        size_t bitsPerElement = calcBitsPerElement(q);
        return (bitsPerElement * numberOfElements + 7) / 8;
    case BOOL:
        return (numberOfElements + 7) / 8;
    default:
        PRINT_ERROR("Unknown QType!");
        exit(1);
    }
}

bool tensorBoolGet(tensor_t const *tensor, size_t flatIndex) {                                 //Retrieval Example: To get index 11, it searches byte 11 / 8 = 1 and isolates bit 11 % 8 = 3. It shifts the byte down 
                                                                                                 by 3 bits and masks it with 1u to extract a clean true/false state.tensorBoolSet: Operates inversely. It uses bitwise
                                                                                                 OR (|=) with a shifted mask to change a single bit to 1, or a bitwise AND with a inverted mask (&= ~) to clear a bit to 0.
    if (tensor->quantization->type != BOOL) {
        PRINT_ERROR("tensorBoolGet called on non-BOOL tensor");
        exit(1);
    }
    size_t byteIndex = flatIndex / 8;
    size_t bitIndex = flatIndex % 8;
    return ((tensor->data[byteIndex] >> bitIndex) & 1u) != 0;
}

void tensorBoolSet(tensor_t *tensor, size_t flatIndex, bool value) {
    if (tensor->quantization->type != BOOL) {
        PRINT_ERROR("tensorBoolSet called on non-BOOL tensor");
        exit(1);
    }
    size_t byteIndex = flatIndex / 8;
    size_t bitIndex = flatIndex % 8;
    if (value) {
        tensor->data[byteIndex] |= (uint8_t)(1u << bitIndex);
    } else {
        tensor->data[byteIndex] &= (uint8_t)~(1u << bitIndex);
    }
}

void setOrderOfDimsForNewTensor(size_t numberOfDimensions, size_t *orderOfDimensions) {
    for (size_t i = 0; i < numberOfDimensions; i++) {
        orderOfDimensions[i] = i;
    }
}

void print_binary_uint8(uint8_t x) {
    /* Show the most‑significant bit first */
    printf("Byte ");
    for (int i = 7; i >= 0; --i) {
        putchar((x >> i) & 1 ? '1' : '0');
    }
    putchar('\n'); /* newline for convenience */
}

uint32_t getBitmask(uint32_t startbit, uint32_t endbit) {                                          //Generates a 1-byte mask containing continuous 1s only between the startbit and endbit intervals. This isolations 
                                                                                                     window lets the engine update or read a sub-section of a byte without corrupting surrounding variables.
    uint32_t endbitInternal = endbit - (startbit / 8) * 8;
    uint32_t startbitInternal = startbit - (startbit / 8) * 8;
    uint32_t counter = 0;
    uint32_t value = 1;
    for (size_t i = 0; i < 8; i++) {
        if ((i >= startbitInternal) & (endbitInternal > i)) {
            counter += value;
        }
        value *= 2;
    }
    // printf("bitmask ");
    // print_binary_uint8(counter);
    return counter;
}

uint8_t readByte(uint8_t data, uint8_t startbit, uint8_t endbit) {                                //readByte: Masks a raw byte and shifts the internal data window down so that the requested bit field becomes a standard 
                                                                                                    right-aligned integer value.writeByte: Takes a sub-byte integer payload, shifts it up to match the targeted start bit 
                                                                                                    position, applies a protective mask, and fuses it onto the existingData byte using a bitwise OR (|).
    uint8_t bitmask = getBitmask(startbit, endbit);
    uint8_t intermediate = data & bitmask;
    intermediate >>= startbit - (startbit / 8) * 8;
    return intermediate;
}

uint8_t writeByte(uint8_t existingData, uint8_t data, uint8_t startbit, uint8_t endbit) {
    uint8_t startbitInternal = startbit - (startbit / 8) * 8;
    uint8_t endbitInternal = endbit - (startbit / 8) * 8;
    uint8_t bitmask = getBitmask(startbitInternal, endbitInternal);
    data <<= startbitInternal;
    // print_binary_uint8(data);
    uint8_t intermediate = data & bitmask;
    // print_binary_uint8(bitmask);
    // print_binary_uint8(intermediate);
    existingData = intermediate | existingData;
    // print_binary_uint8(existingData);
    return existingData;
}

int max(int a, int b) {
    return (a > b) ? a : b;
}

int min(int a, int b) {
    return (a < b) ? a : b;
}

void byteConversion(uint8_t *dataIn, size_t dataInBits, uint8_t *dataOut, size_t dataOutBits,
                    size_t numValues) {                                                                     //The function runs a nested state-machine loop that tracks input data indexes, output data indexes, and bit 
                                                                                                              offset heads simultaneously.Widening (e.g., 4-bit to 8-bit): The loop reads small bit windows via readByte, 
                                                                                                              writes them to larger targets via writeByte, and steps the output trackers forward faster than the input 
                                                                                                              trackers.Narrowing (e.g., 16-bit to 8-bit): Squeezes larger variables down.The min() Stepper Engine: The 
                                                                                                              calculations valuesRead and valuesWritten check how many bits remain before the current byte boundary is hit.
                                                                                                              The loop then advances its bit offsets by the minValue delta, gracefully transitioning array indexes 
                                                                                                              (dataInIndex++, dataOutIndex++) precisely when crossing byte thresholds.
    memset(dataOut, 0, (numValues * dataOutBits - 1) / 8 + 1);
    size_t dataOutIndex = 0;
    size_t dataInIndex = 0;
    int dataOutStartbit = 0;
    int dataInStartbit = 0;
    int dataInEndbit = (int)dataInBits;
    int dataOutEndbit = (int)dataOutBits;
    for (size_t i = 0; i < numValues; i++) {
        /*
        printf("\n");
        printf("\n");
        printf("Value %i\n", i);*/
        while ((dataInStartbit < dataInEndbit) | (dataOutStartbit < dataOutEndbit)) {
            /* Guard each side: input may exhaust before output (widening) or
             * output may fill before input (narrowing); skipping the out-of-range
             * access avoids OOB while preserving zero-fill semantics. */
            uint8_t data = 0;
            if (dataInStartbit < dataInEndbit) {
                data = readByte(dataIn[dataInIndex], dataInStartbit, dataInEndbit);
            }
            if (dataOutStartbit < dataOutEndbit) {
                dataOut[dataOutIndex] =
                    writeByte(dataOut[dataOutIndex], data, dataOutStartbit, dataOutEndbit);
            }

            /*
            printf("dataInStartbit %d\n", dataInStartbit);
            printf("dataInEndbit %d\n", dataInEndbit);
            printf("dataOutStartbit %d\n", dataOutStartbit);
            printf("dataOutEndbit %d\n", dataOutEndbit);
            printf("dataInIndex %d\n", dataInIndex);
            printf("dataOutIndex %d\n", dataOutIndex);
            printf("data");
            print_binary_uint8(data);
            printf("dataOut[dataOutIndex]");
            print_binary_uint8(dataOut[dataOutIndex]);
            */
            int valuesRead = min(dataInEndbit - dataInStartbit, 8 - dataInStartbit % 8);
            int valuesWritten = min(dataOutEndbit - dataOutStartbit, 8 - dataOutStartbit % 8);
            int minValue = min(valuesRead, valuesWritten);

            /*
            printf("valuesRead %d\n", valuesRead);
            printf("valuesWritten %d\n", valuesWritten);
            printf("minValue %d\n", minValue);*/

            uint8_t deltaIn = minValue;
            uint8_t deltaOut = minValue;
            if (dataInStartbit == dataInEndbit) {
                dataOutStartbit += valuesWritten;
                deltaOut = valuesWritten;

            } else {
                dataOutStartbit += minValue;
            }
            if (dataOutStartbit == dataOutEndbit) {
                dataInStartbit += valuesRead;
                deltaIn = valuesRead;
            } else {
                dataInStartbit += minValue;
            }

            if (dataInStartbit / 8 > (dataInStartbit - deltaIn) / 8) {
                dataInIndex += 1;
            }
            if (dataOutStartbit / 8 > (dataOutStartbit - deltaOut) / 8) {
                dataOutIndex += 1;
            }
            // printf("\n");
        }
        dataInStartbit = dataInEndbit % 8;
        dataInEndbit = dataInStartbit + dataInBits;
        dataOutStartbit = dataOutEndbit % 8;
        dataOutEndbit = dataOutStartbit + dataOutBits;
    }
}

tensor_t *getParamFromParameter(parameter_t *parameter) {
    return parameter->param;
}

tensor_t *getGradFromParameter(parameter_t *parameter) {
    return parameter->grad;
}

void transposeTensor(tensor_t *tensor, size_t dim0Index, size_t dim1Index) {
    if (tensor->shape->numberOfDimensions < 2) {
        return;
    }
    size_t temp = tensor->shape->orderOfDimensions[dim0Index];
    tensor->shape->orderOfDimensions[dim0Index] = tensor->shape->orderOfDimensions[dim1Index];
    tensor->shape->orderOfDimensions[dim1Index] = temp;
}

void setTensorValuesForConversion(uint8_t *data, quantization_t *q, tensor_t *originalTensor,
                                  tensor_t *outputTensor) {
    outputTensor->data = data;
    outputTensor->shape = originalTensor->shape;
    outputTensor->quantization = q;
    outputTensor->sparsity = originalTensor->sparsity;
}

void setTensorValues(tensor_t *tensor, uint8_t *data, shape_t *shape, quantization_t *quantization,
                     sparsity_t *sparsity) {
    tensor->data = data;
    tensor->shape = shape;
    tensor->quantization = quantization;
    tensor->sparsity = sparsity;
}

void setParameterValues(parameter_t *parameter, tensor_t *param, tensor_t *grad) {
    parameter->param = param;
    parameter->grad = grad;
}

void setShape(shape_t *shape, size_t *dims, size_t numberOfDims, size_t *orderOfDims) {
    shape->dimensions = dims;
    shape->numberOfDimensions = numberOfDims;
    shape->orderOfDimensions = orderOfDims;
}

void printTensor(tensor_t *t) {
    quantization_t *q = t->quantization;
    printf("TENSOR BEGIN \n");
    size_t numValues = calcNumberOfElementsByTensor(t);
    int32_t data[numValues];

    switch (q->type) {
    case INT32:
        printf("INT32Q \n");
        readBytesAsInt32Array(numValues, t->data, data);
        for (size_t i = 0; i < numValues; i++) {
            printf("%i\n", data[i]);
        }
        break;
    case FLOAT32:
        printf("FLOAT32Q \n");
        for (size_t i = 0; i < numValues; i++) {
            size_t byteIndex = i * sizeof(float);
            float currentElement = readBytesAsFloat(&t->data[byteIndex]);
            printf("%f\n", currentElement);
        }
        break;
    case SYM_INT32:
        symInt32QConfig_t *symQC = q->qConfig;
        printf("SYM_INT32 \n");
        printf("scale=%e\n", symQC->scale);
        printf("Data \n");
        for (size_t i = 0; i < numValues; i++) {
            size_t byteIndex = i * sizeof(int32_t);
            int32_t currentElement = readBytesAsInt32(&t->data[byteIndex]);
            printf("%i\n", currentElement);
        }
        break;
    case ASYM:
        asymQConfig_t *lq = q->qConfig;
        printf("ASYM\n");
        printf("scale=%e\n", lq->scale);
        printf("offset=%i\n", lq->zeroPoint);
        printf("Data \n");
        for (size_t i = 0; i < numValues; i++) {
            printf("%i\n", t->data[i]);
        }
        break;
    case BOOL:
        printf("BOOL\n");
        printf("[");
        for (size_t i = 0; i < numValues; i++) {
            printf("%d", tensorBoolGet(t, i) ? 1 : 0);
            if (i + 1 < numValues) {
                printf(", ");
            }
        }
        printf("]\n");
        break;
    default:
        printf("WTF\n");
    }

    printf("TENSOR END \n");
    printf("_____________________\n");
}

void printShape(shape_t *shape) {
    size_t numberOfDims = shape->numberOfDimensions;

    printf("NumberOfDims: %lu\n", numberOfDims);

    printf("Dims: \n");
    for (size_t i = 0; i < numberOfDims; i++) {
        printf("%lu\n", shape->dimensions[i]);
    }

    printf("OrderOfDims: \n");
    for (size_t i = 0; i < numberOfDims; i++) {
        printf("%lu\n", shape->orderOfDimensions[i]);
    }
    printf("__________\n");
}

void initOrderOfDimensions(size_t *orderOfDims, size_t numberOfDims) {
    for (size_t i = 0; i < numberOfDims; i++) {
        orderOfDims[i] = i;
    }
}

void copyData(tensor_t *dest, tensor_t *src) {
    size_t numberOfValues = calcNumberOfElementsByShape(dest->shape);
    size_t sizeData = calcNumberOfBytesForData(src->quantization, numberOfValues);

    memcpy(dest->data, src->data, sizeData);

    if (src->sparsity != NULL) {
        memcpy(dest->sparsity, src->sparsity, sizeof(sparsity_t));
    }
}

void copyShape(shape_t *dest, shape_t *src) {
    memcpy(dest->dimensions, src->dimensions, src->numberOfDimensions * sizeof(size_t));
    memcpy(dest->orderOfDimensions, src->orderOfDimensions,
           src->numberOfDimensions * sizeof(size_t));
    dest->numberOfDimensions = src->numberOfDimensions;
}

void copyQuantization(quantization_t *dest, quantization_t *src) {
    switch (src->type) {
    case FLOAT32:
        dest->type = FLOAT32;
        dest->qConfig = NULL;
        break;
    case SYM_INT32:
        dest->type = SYM_INT32;
        symInt32QConfig_t *destQC = dest->qConfig;
        symInt32QConfig_t *srcQC = src->qConfig;
        memcpy(destQC, srcQC, sizeof(symInt32QConfig_t));
        break;
    case BOOL:
        dest->type = BOOL;
        dest->qConfig = NULL;
        break;
    default:
        PRINT_ERROR("Unknown QType!");
        exit(1);
    }
}

// TODO copy sparsity
void copyTensor(tensor_t *dest, tensor_t *src) {
    copyShape(dest->shape, src->shape);
    copyQuantization(dest->quantization, src->quantization);
    copyData(dest, src);
}
