#define SOURCE_FILE "MATMUL"

#ifdef TRACK_INSTRUCTIONS
#define MATMUL_FUNC_INT matmulIntTensorsWithInstructionCounter
#define MATMUL_FUNC_FLOAT matmulFloatTensorsWithInstructionCounter
#define MATMUL_FUNC_SYM_INT32 matmulSymIntTensorsWithInstructionCounter
#else
#define MATMUL_FUNC_INT matmulIntTensors
#define MATMUL_FUNC_FLOAT matmulFloatTensors
#define MATMUL_FUNC_SYM_INT32 matmulSymIntTensors
#endif

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "Arithmetic.h"
#include "Common.h"
#include "DTypes.h"
#include "Matmul.h"
#include "Mul.h"
#include "Tensor.h"

size_t matmulInstructionCounter = 0;

static void matmulIntCore(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor,
                          const int32_t *biasSeed) {
    if (aTensor->shape->numberOfDimensions > 2 || bTensor->shape->numberOfDimensions > 2) {
        PRINT_ERROR("Matmul only supports up to 2D Tensors");
        exit(1);
    }                                                                                                        //Computers get easily confused if you give them the wrong shapes. First, the code checks if you handed it 
                                                                                                               something more complicated than a 2D grid (like a 3D video file). If you did, it throws an error and 
                                                                                                               completely stops the program (exit(1)).

    size_t aNumberOfDims = aTensor->shape->numberOfDimensions;
    size_t *aDims = aTensor->shape->dimensions;
    size_t bNumberOfDims = bTensor->shape->numberOfDimensions;
    size_t *bDims = bTensor->shape->dimensions;

    size_t aRows, aColumns;
    if (aNumberOfDims < 2) {                                                                                  //If you pass the engine a simple 1D list of numbers (a vector) instead of a 2D grid, the code auto-corrects.
                                                                                                                It pretends your list is a grid with just 1 row. This makes the rest of the code simpler because it can treat
                                                                                                                everything as a 2D grid.
        aRows = 1;
        aColumns = getDimensionsByIndex(aTensor, 0);
    } else {
        aRows = getDimensionsByIndex(aTensor, 0);
        aColumns = getDimensionsByIndex(aTensor, 1);
    }

    size_t bRows = getDimensionsByIndex(bTensor, 0);
    size_t bColumns = (bNumberOfDims < 2) ? 1 : getDimensionsByIndex(bTensor, 1);

    size_t resultCounter = 0;

    if (aColumns != bRows) {                                                                                   //In math, you cannot multiply two grids together unless the width (Columns) of the first grid matches the height
                                                                                                                 (Rows) of the second grid. If they don't line up perfectly, the math is impossible, so the code cancels the 
                                                                                                                 operation.Step 4: The 3-Layer Loop (The Engine Room)This is where the actual math happens. The code spins up three 
                                                                                                                 nested loops:Row Loop (rowIndex): Locks onto a row in Grid A.Column Loop (columnIndex): Locks onto a column in Grid
                                                                                                                 B.Inner Dot-Product Loop (i): Moves across that row and down that column at the exact same time.Inside the 
                                                                                                                 innermost loop, it reads a value from Grid A (aValue) and a value from Grid B (bValue), multiplies them together
                                                                                                                 using mulInt32s(), and adds them to a running total called result.
        PRINT_ERROR("Rows dont match Columns");
        PRINT_DEBUG("aColumns: %lu, bRows: %lu\n", aColumns, bRows);
        exit(1);
    }

    for (size_t rowIndex = 0; rowIndex < aRows; rowIndex++) {
        for (size_t columnIndex = 0; columnIndex < bColumns; columnIndex++) {
            int32_t result = biasSeed ? biasSeed[columnIndex] : 0;
            for (size_t i = 0; i < aColumns; i++) {
                size_t aByteIndex = 0;
                if (aNumberOfDims == 1) {
                    aByteIndex = i * sizeof(int32_t);
                } else {
                    size_t aIndices[] = {rowIndex, i};
                    size_t aValueIndex = calcElementIndexByIndices(
                        aNumberOfDims, aDims, aIndices, aTensor->shape->orderOfDimensions);                     //This is the most unique part of this specific library. Sometimes a program "rotates" or transposes a matrix in its
                                                                                                                   mind without actually moving the numbers around in the computer's RAM.This line calls a helper function to translate the
                                                                                                                   logical grid coordinates (like "Row 2, Column 3") into the exact physical byte location in the memory sticks, ensuring the
                                                                                                                   computer never grabs the wrong data.
                    aByteIndex = aValueIndex * sizeof(int32_t);
                }
                int32_t aValue = readBytesAsInt32(&aTensor->data[aByteIndex]);

                size_t bByteIndex = 0;
                if (bNumberOfDims == 1) {
                    bByteIndex = i * sizeof(int32_t);
                } else {
                    size_t bIndices[] = {i, columnIndex};
                    size_t bValueIndex = calcElementIndexByIndices(
                        bNumberOfDims, bDims, bIndices, bTensor->shape->orderOfDimensions);
                    bByteIndex = bValueIndex * sizeof(int32_t);
                }
                int32_t bValue = readBytesAsInt32(&bTensor->data[bByteIndex]);

                result += mulInt32s(aValue, bValue);
            }

            size_t outputByteIndex = resultCounter * sizeof(int32_t);                                   //Once the inner loop finishes calculating the total for that specific slot, it takes the final result number and saves it into 
                                                                                                        the outputTensor data buffer. It then bumps up the resultCounter and moves to the next slot until the entire new grid is filled.
            writeInt32ToByteArray(result, &outputTensor->data[outputByteIndex]);
            resultCounter++;
        }
    }
}

void matmulIntTensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor) {
    matmulIntCore(aTensor, bTensor, outputTensor, NULL);
}

void matmulIntTensorsWithInstructionCounter(tensor_t *aTensor, tensor_t *bTensor,
                                            tensor_t *outputTensor) {
    matmulIntCore(aTensor, bTensor, outputTensor, NULL);
    ++matmulInstructionCounter;
}

void matmulInt32Tensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor) {
    MATMUL_FUNC_INT(aTensor, bTensor, outputTensor);
}

static void matmulFloatCore(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor,
                            const uint8_t *biasSeed) {
    if (aTensor->shape->numberOfDimensions > 2 || bTensor->shape->numberOfDimensions > 2) {
        PRINT_ERROR("Matmul only supports up to 2D Tensors");
        exit(1);
    }

    size_t aNumberOfDims = aTensor->shape->numberOfDimensions;
    size_t *aDims = aTensor->shape->dimensions;
    size_t bNumberOfDims = bTensor->shape->numberOfDimensions;
    size_t *bDims = bTensor->shape->dimensions;

    size_t aRows, aColumns = 0;
    if (aNumberOfDims < 2) {
        aRows = 1;
        aColumns = getDimensionsByIndex(aTensor, 0);
    } else {
        aRows = getDimensionsByIndex(aTensor, 0);
        aColumns = getDimensionsByIndex(aTensor, 1);
    }

    size_t bRows, bColumns = 0;
    if (bNumberOfDims < 2) {
        bRows = getDimensionsByIndex(bTensor, 0);
        bColumns = 1;
    } else {
        bRows = getDimensionsByIndex(bTensor, 0);
        bColumns = getDimensionsByIndex(bTensor, 1);
    }

    size_t resultCounter = 0;

    if (aColumns != bRows) {
        PRINT_ERROR("Rows dont match Columns");
        PRINT_DEBUG("aColumns: %lu, bRows: %lu\n", aColumns, bRows);
        exit(1);
    }

    for (size_t rowIndex = 0; rowIndex < aRows; rowIndex++) {
        for (size_t columnIndex = 0; columnIndex < bColumns; columnIndex++) {
            float result = biasSeed
                               ? readBytesAsFloat((uint8_t *)&biasSeed[columnIndex * sizeof(float)])
                               : 0.0f;
            for (size_t i = 0; i < aColumns; i++) {
                size_t aByteIndex = 0;
                if (aNumberOfDims == 1) {
                    aByteIndex = i * sizeof(float);
                } else {
                    size_t aIndices[] = {rowIndex, i};
                    size_t aValueIndex = calcElementIndexByIndices(
                        aNumberOfDims, aDims, aIndices, aTensor->shape->orderOfDimensions);
                    aByteIndex = aValueIndex * sizeof(float);
                }
                float aValue = readBytesAsFloat(&aTensor->data[aByteIndex]);

                size_t bByteIndex = 0;
                if (bNumberOfDims == 1) {
                    bByteIndex = i * sizeof(float);
                } else {
                    size_t bIndices[] = {i, columnIndex};
                    size_t bValueIndex = calcElementIndexByIndices(
                        bNumberOfDims, bDims, bIndices, bTensor->shape->orderOfDimensions);
                    bByteIndex = bValueIndex * sizeof(float);
                }
                float bValue = readBytesAsFloat(&bTensor->data[bByteIndex]);
                result += mulFloat32s(aValue, bValue);
            }

            size_t outputByteIndex = resultCounter * sizeof(float);
            writeFloatToByteArray(result, &outputTensor->data[outputByteIndex]);
            resultCounter++;
        }
    }
}

void matmulFloatTensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor) {
    matmulFloatCore(aTensor, bTensor, outputTensor, NULL);
}

void matmulFloatTensorsWithInstructionCounter(tensor_t *aTensor, tensor_t *bTensor,
                                              tensor_t *outputTensor) {
    matmulFloatCore(aTensor, bTensor, outputTensor, NULL);
    ++matmulInstructionCounter;
}

void matmulFloat32TensorsWithBias(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor,
                                  tensor_t *bias) {                                                            //The Check: It verifies that you have exactly one bias number for every column in your output matrix. If your 
                                                                                                                 output has 4 columns, you must supply exactly 4 bias values.The "Seed" Secret: Instead of performing matrix 
                                                                                                                 multiplication and then running a whole new loop to add the bias later, it passes the bias memory directly 
                                                                                                                 into matmulFloatCore via the seed pointer.Look Back inside matmulFloatCore: If you look closely inside 
                                                                                                                 matmulFloatCore, the variable that holds the running total (float result) starts at 0.0f only if biasSeed
                                                                                                                 is empty. If a bias exists, it loads the bias value first:
    const uint8_t *seed = NULL;
    if (bias != NULL) {
        size_t bColumns =
            (bTensor->shape->numberOfDimensions < 2) ? 1 : getDimensionsByIndex(bTensor, 1);
        if (calcNumberOfElementsByTensor(bias) != bColumns) {
            PRINT_ERROR("matmulFloat32TensorsWithBias: bias element count != output columns");
            exit(1);
        }
        seed = bias->data;
    }
    matmulFloatCore(aTensor, bTensor, outputTensor, seed);
}

void matmulFloat32Tensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor) {
    MATMUL_FUNC_FLOAT(aTensor, bTensor, outputTensor);
}

void matmulSymIntTensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor) {
    matmulInt32Tensors(aTensor, bTensor, outputTensor);

    symInt32QConfig_t *aSymInt32QC = aTensor->quantization->qConfig;
    symInt32QConfig_t *bSymInt32QC = bTensor->quantization->qConfig;
    symInt32QConfig_t *outputSymInt32QC = outputTensor->quantization->qConfig;

    outputSymInt32QC->scale = aSymInt32QC->scale * bSymInt32QC->scale;
}

void matmulSymIntTensorsWithInstructionCounter(tensor_t *aTensor, tensor_t *bTensor,
                                               tensor_t *outputTensor) {
    matmulInt32Tensors(aTensor, bTensor, outputTensor);

    symInt32QConfig_t *aSymInt32QC = aTensor->quantization->qConfig;
    symInt32QConfig_t *bSymInt32QC = bTensor->quantization->qConfig;
    symInt32QConfig_t *outputSymInt32QC = outputTensor->quantization->qConfig;
    outputSymInt32QC->scale = aSymInt32QC->scale * bSymInt32QC->scale;

    ++matmulInstructionCounter;
}

void matmulSymInt32Tensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor) {                  
    MATMUL_FUNC_SYM_INT32(aTensor, bTensor, outputTensor);
}

void matmulSymInt32TensorsWithBias(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor,
                                   tensor_t *bias) {                                                        
    if (bias == NULL) {
        matmulIntCore(aTensor, bTensor, outputTensor, NULL);
    } else {
        size_t bColumns =
            (bTensor->shape->numberOfDimensions < 2) ? 1 : getDimensionsByIndex(bTensor, 1);
        if (calcNumberOfElementsByTensor(bias) != bColumns) {
            PRINT_ERROR("matmulSymInt32TensorsWithBias: bias element count != output columns");
            exit(1);
        }

        float aScale = ((symInt32QConfig_t *)aTensor->quantization->qConfig)->scale;
        float bScale = ((symInt32QConfig_t *)bTensor->quantization->qConfig)->scale;
        float biasScale = ((symInt32QConfig_t *)bias->quantization->qConfig)->scale;
        float outputScale = aScale * bScale;

        /* Rescale the bias into the accumulator's scale: one fixed-point op per
         * output column (small: == outFeatures), outside the MAC loop. */
        int32_t seed[bColumns];
        for (size_t c = 0; c < bColumns; c++) {
            int32_t biasIntC = readBytesAsInt32(&bias->data[c * sizeof(int32_t)]);
            seed[c] = (int32_t)roundf((float)biasIntC * biasScale / outputScale);
        }
        matmulIntCore(aTensor, bTensor, outputTensor, seed);
    }

    symInt32QConfig_t *aQC = aTensor->quantization->qConfig;
    symInt32QConfig_t *bQC = bTensor->quantization->qConfig;
    symInt32QConfig_t *outputQC = outputTensor->quantization->qConfig;
    outputQC->scale = aQC->scale * bQC->scale;
}

size_t getMatmulInstructionCounter() {
    return matmulInstructionCounter;
}
