#define SOURCE_FILE "TENSOR_CONVERSION"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "Common.h"
#include "DTypes.h"
#include "MinMax.h"
#include "Tensor.h"
#include "TensorConversion.h"
#include "math.h"

void zeroTensorData(tensor_t *tensor) {                                                             //Purpose: Resets a tensor's data memory area safely.Mechanics: It multiplies total items by the size required per element.
                                                                                                      It then issues a memset to flush every bit to zero. This prevents left-over memory data from contaminating new 
                                                                                                      mathematical results.
    size_t numberOfElements = calcNumberOfElementsByTensor(tensor);
    size_t bytesPerElement = calcBytesPerElement(tensor->quantization);
    memset(tensor->data, 0, numberOfElements * bytesPerElement);
}

void copyDimsAndSparsityToTensor(tensor_t *inputTensor, tensor_t *outputTensor) {                   //Purpose: Synchronizes metadata properties between tensor instances during transformations.Mechanics: It binds
                                                                                                      the identical multidimensional shape configuration to the output tensor, and deeply copies the zero-skipping data 
                                                                                                      maps (sparsity_t) if they exist.
    outputTensor->shape = inputTensor->shape;
    if (inputTensor->sparsity) {
        memcpy(outputTensor->sparsity, inputTensor->sparsity, sizeof(sparsity_t));
    }
}

void convertInt32TensorToFloatTensor(tensor_t *inputTensor, tensor_t *outputTensor) {             //This functions performs standard type transformation to map raw integers directly into true engineering 
                                                                                                    floating-point representations.The Routine:Pulls the raw binary arrays into a native stack array (inputData) using byte 
                                                                                                    parsing functions.Iterates over elements, manually type-casting each individual number: 
                                                                                                    outputData[i] = (float)inputData[i];.flattens the resulting values right back down into sequential raw byte positions
                                                                                                    within the target buffer via your writeFloatArrayToByteArray utility.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    int32_t inputData[numberOfElements];
    float outputData[numberOfElements];
    readBytesAsInt32Array(numberOfElements, inputTensor->data, inputData);
    zeroTensorData(outputTensor);
    for (size_t i = 0; i < numberOfElements; i++) {
        outputData[i] = (float)inputData[i];
    }
    writeFloatArrayToByteArray(numberOfElements, outputData, outputTensor->data);
    copyDimsAndSparsityToTensor(inputTensor, outputTensor);
}

void convertInt32TensorToSymInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {       //Purpose: Acts as an unscaled transformation mapping into standard symmetric fixed-point integer limits.
                                                                                                 Because both configurations store data using native 32-bit parameters, it cleanly bypasses complex data transformations
                                                                                                 and issues a fast memcpy to sync data.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    symInt32QConfig_t *outputSymInt32QConfig = outputTensor->quantization->qConfig;
    outputSymInt32QConfig->scale = 1;

    memcpy(outputTensor->data, inputTensor->data, numberOfElements * sizeof(int32_t));
}

void convertInt32TensorToAsymTensor(tensor_t *inputTensor, tensor_t *outputTensor) {                   //Dynamic Scanning: It scans the tensor memory block using helper routines to extract the real numeric maximum (max)
                                                                                                         and minimum (min).Bit Boundaries: It reads the destination bit constraint (qBits). For an 8-bit quantization format,
                                                                                                         \(q_{max} = 2^8 - 1 = 255\)
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    int32_t min = findMinInt32(inputTensor->data, numberOfElements);
    int32_t max = findMaxInt32(inputTensor->data, numberOfElements);
    asymQConfig_t *linearQConfig = outputTensor->quantization->qConfig;
    int32_t qMax = pow(2, linearQConfig->qBits) - 1;

    float scale = (float)(max - min) / (float)qMax;                                                  //Scale Factor Calculation: Scale defines the resolution mapping window. It distributes the real range evenly over the
                                                                                                       integer range steps.Zero-Point Extraction: Finds exactly where real-world 0.0 lands in the output tracking system. 
                                                                                                       It applies the target configuration's custom rounding rules (roundingMode) to keep the mapping accurately aligned.
    int16_t zeroPoint = (int16_t)roundByMode((float)min / scale, linearQConfig->roundingMode);

    int32_t outputElements[numberOfElements];
    for (size_t elementIndex = 0; elementIndex < numberOfElements; elementIndex++) {                      //Execution Loop: For each integer element, it:Translates bytes into local variables.Scales the value and applies
                                                                                                            the zero-point offset shift.Employs a clamp wrapper to force values cleanly into safe integer boundaries
                                                                                                            (\(0\) to \(254\)), eliminating numeric underflow or overflow crashes.Resolves fractional variables precisely
                                                                                                            using your "Rounding.h" configurations
        int32_t inputElement = readBytesAsInt32(&inputTensor->data[elementIndex * sizeof(int32_t)]);

        outputElements[elementIndex] =
            roundByMode(clamp((float)inputElement / scale - (float)zeroPoint, 0.f, qMax - 1),
                        linearQConfig->roundingMode);
    }
    linearQConfig->scale = scale;
    linearQConfig->zeroPoint = zeroPoint;
    uint8_t outputElement[numberOfElements * sizeof(int32_t)];
    writeInt32ArrayToByteArray(numberOfElements, outputElements, outputElement);

    byteConversion(outputElement, 32, outputTensor->data, linearQConfig->qBits, numberOfElements);
    copyDimsAndSparsityToTensor(inputTensor, outputTensor);
}

void convertFloatTensorToInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {                       //This function performs an unscaled truncation conversion from floating-point values into standard, 32-bit integers.
                                                                                                              How it works:It reads raw bytes from inputTensor->data and deserializes them into a float array (inputData)
                                                                                                              using your previously defined readBytesAsFloatArray.It flushes the output tensor data buffer to zero via
                                                                                                              zeroTensorData to remove legacy artifacts.It runs a loop that explicitly drops the fractional part of each 
                                                                                                              floating-point value via type-casting: outputData[i] = (int32_t)inputData[i];.It uses writeInt32ArrayToByteArray
                                                                                                              to pack the raw 4-byte integer blocks back down into sequential bytes, then copies over shape and zero-skipping
                                                                                                              dimensions.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    float inputData[numberOfElements];
    int32_t outputData[numberOfElements];
    readBytesAsFloatArray(numberOfElements, inputTensor->data, inputData);
    zeroTensorData(outputTensor);
    for (size_t i = 0; i < numberOfElements; i++) {
        outputData[i] = (int32_t)inputData[i];
    }
    writeInt32ArrayToByteArray(numberOfElements, outputData, outputTensor->data);
    copyDimsAndSparsityToTensor(inputTensor, outputTensor);
}

void convertFloatTensorToSymInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {               //This function performs Symmetric Uniform Quantization down to a dynamic 32-bit signed fixed-point integer layout.
                                                                                                         "Symmetric" means the zero point is locked mathematically to exactly 0, mapping real-world 0.0 directly to integer 0.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    float absMax = findAbsMaxFloat(inputTensor->data, numberOfElements);                               //It scans the floating-point vector to extract the single largest absolute magnitude value (absMax). This bounds the 
                                                                                                         symmetrical conversion window from [-absMax, +absMax].

    symInt32QConfig_t *symInt32QC = outputTensor->quantization->qConfig;
    uint8_t qMaxBits = symInt32QC->qMaxBits;

    const float qMax = powf(2, (float)qMaxBits - 1) - 1;                                              //It queries the output tensor's configuration (qMaxBits). If it is configured to use your default 16-bit boundaries,
                                                                                                        it sets the integer ceilings to:\(q_{Max} = 2^{(16-1)} - 1 = 32767\)\(q_{Min} = -2^{(16-1)} = -32768\)
    const float qMin = -powf(2, (float)qMaxBits - 1);

    float scale;
    if (absMax == 0.f) {
        scale = 1.f;
    } else {
        scale = absMax / qMax;
    }

    symInt32QConfig_t *outputSymInt32QC = outputTensor->quantization->qConfig;
    outputSymInt32QC->scale = scale;

    int32_t *outputInt32 = (int32_t *)outputTensor->data;                                             //Instead of utilizing deserializer functions, this block forces pointer aliases straight onto the raw byte memory
                                                                                                        pools. While faster, this skips byte serialization safeguards. If outputTensor->data is not aligned to a 4-byte 
                                                                                                        boundary in hardware memory, executing the loop can trigger strict hardware alignment exceptions or performance 
                                                                                                        penalties on microcontrollers.Transformation Loop:It divides the floats by the calculated scale factor, drops 
                                                                                                        values safely into integer ceilings via clamp(), and applies your "Rounding.h" layout behaviors.
    float *inputFloat = (float *)inputTensor->data;

    for (size_t i = 0; i < numberOfElements; i++) {
        outputInt32[i] =
            roundByMode(clamp(inputFloat[i] / scale, qMin, qMax), outputSymInt32QC->roundingMode);
    }
}

// I DON'T HAVE TO IMPLEMENT SYM CONVERSIONS!
void convertFloatTensorToSymTensor(tensor_t *inputTensor, tensor_t *outputTensor) {                    //Despite your source code comment "I DON'T HAVE TO IMPLEMENT SYM CONVERSIONS!", this function contains 
                                                                                                         a highly broken mathematical attempt at Asymmetric Quantization masquerading as Symmetric Quantization.Here is the 
                                                                                                         functional breakdown followed by its fatal logical bugs:What it tries to do: It reads the minimum and maximum float 
                                                                                                         ranges, computes a mapping scale, reads the inputs via serialization, executes a conversion loop, and uses memcpy to 
                                                                                                         deploy the output data stream.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    float min = findMinFloat(inputTensor->data, numberOfElements);
    float max = findMaxFloat(inputTensor->data, numberOfElements);

    symQConfig_t *outputSymQConfig = outputTensor->quantization->qConfig;
    float qMax = powf(2, outputSymQConfig->qBits);

    float scale = (min - max) / qMax;
    outputSymQConfig->scale = scale;

    float inputs[numberOfElements];
    readBytesAsFloatArray(numberOfElements, inputTensor->data, inputs);

    size_t bytesPerOutputElement = calcBytesPerElement(outputTensor->quantization);
    uint8_t outputs[numberOfElements * bytesPerOutputElement];

    for (size_t i = 0; i < numberOfElements; i++) {                                                  //As flagged previously, this code concludes with severe memory bugs:The Slicing Defect: If bytesPerOutputElement 
                                                                                                       evaluates to 2 (meaning 16-bit quantization), your stack allocation array outputs receives a total capacity of 
                                                                                                       numberOfElements * 2 bytes.The Corruption Mechanics: The assignment loop indexes via outputs[i]. It writes single,
                                                                                                       8-bit values exclusively into the first half of the array block. It completely neglects the sub-byte slots required 
                                                                                                       for 16-bit encoding. The subsequent memcpy reads the entire buffer, transferring uninitialized hardware memory 
                                                                                                       artifacts straight into your active outputTensor->data buffer.
        outputs[i] =
            roundByMode(clamp(inputs[i] / scale, 0.f, qMax - 1), outputSymQConfig->roundingMode);
    }

    memcpy(outputTensor->data, outputs, numberOfElements * bytesPerOutputElement);
}

// conversion from float to asym should not be needed/used
void convertFloatTensorToAsymTensor(tensor_t *inputTensor, tensor_t *outputTensor) {                   //This function contains a fully realized, structurally sound algorithm for True Asymmetric Linear Quantization, 
                                                                                                         complete with dynamic parameter extraction and custom bit-stream packaging
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    float min = findMinFloat(inputTensor->data, numberOfElements);
    float max = findMaxFloat(inputTensor->data, numberOfElements);

    asymQConfig_t *asymQConfig = outputTensor->quantization->qConfig;
    float qMax = pow(2, asymQConfig->qBits);

    float scale;
    int16_t zeroPoint;
    if (min == max) {                                                                                 //The Safeguard: If the input vector contains only a single uniform number (e.g., all values are exactly 4.5f),
                                                                                                        min == max triggers. This overrides the math to prevent a fatal divide-by-zero (scale = 0.0f) hardware crash.The Standard 
                                                                                                        Math: When a true numerical range exists, it computes the resolution grid spacing (scale) correctly as (max - min) / qMax.
                                                                                                        It then divides the minimum floating boundary by this scale factor to map real-world 0.0f precisely to an integer coordinate
                                                                                                        (zeroPoint).
        scale = min;
        zeroPoint = 1;
    } else {
        scale = (max - min) / qMax;
        zeroPoint = (int16_t)roundByMode(min / scale, asymQConfig->roundingMode);
    }

    int32_t outputElements[numberOfElements];
    float *inputFloat = (float *)inputTensor->data;

    for (size_t i = 0; i < numberOfElements; i++) {                                                  //For each individual floating-point value, it scales the intensity and subtracts the extracted integer offset (zeroPoint).
                                                                                                       It uses clamp to lock values inside the target bit range boundary (\(0\) to \(q_{Max} - 1\)). It then resolves fractional 
                                                                                                       steps using your "Rounding.h" configurations, storing the intermediate outputs inside a temporary 32-bit stack array 
                                                                                                       (outputElements).
        outputElements[i] =
            roundByMode(clamp(inputFloat[i] / scale - (float)zeroPoint, 0.f, qMax - 1),
                        asymQConfig->roundingMode);
    }

    asymQConfig->scale = scale;
    asymQConfig->zeroPoint = zeroPoint;
    uint8_t outputElement[numberOfElements * sizeof(int32_t)];
    writeInt32ArrayToByteArray(numberOfElements, outputElements, outputElement);                    //This is a highly optimized memory design sequence:Serialization: It dumps the 32-bit integers down into standard continuous
                                                                                                      raw bytes using writeInt32ArrayToByteArray.Bit-Squeezing Transformation: It calls your specialized bit-stream engine,
                                                                                                      byteConversion. This takes the 32-bit blocks and strips away unnecessary leading zero-bits. It tightly compresses the 
                                                                                                      fields down to match the designated qBits configuration (e.g., packing them as tightly packed 4-bit or 6-bit integers) 
                                                                                                      directly inside outputTensor->data

    byteConversion(outputElement, 32, outputTensor->data, asymQConfig->qBits, numberOfElements);

    copyDimsAndSparsityToTensor(inputTensor, outputTensor);
}

// Important: Scale is ignored!
void extractInt32TensorFromSymInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {          //The Behavior: As explicit in your developer code comment, the mathematical scaling multiplier is completely ignored.
                                                                                                      The Purpose: It acts purely as a bit-level structural strip. It does not perform actual "de-quantization" back into 
                                                                                                      floating-point numbers. Instead, it reads the underlying raw bit arrangements using a safe wrapper (readBytesAsInt32Array) 
                                                                                                      and transfers them via memcpy to cast the output type metadata as a clean, unquantized integer container (INT32).
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    size_t bytesPerElement = sizeof(int32_t);

    int32_t inputAsInt32[numberOfElements];
    readBytesAsInt32Array(numberOfElements, inputTensor->data, inputAsInt32);

    memcpy(outputTensor->data, inputAsInt32, numberOfElements * bytesPerElement);
}

void convertSymInt32TensorToFloat32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {        //This function performs de-quantization, transforming compressed 32-bit fixed-point integers back into standard real-world
                                                                                                    engineering floats (FLOAT32).The Math: Symmetric quantization scales a value using the formula:\(\text{Real\ Float\ Value}=
                                                                                                    \text{Quantized\ Integer}\times \text{Scale}\)Mechanics:It reads the specific conversion scale out of the input configuration
                                                                                                    layout.It iterates through the elements, casting the integer bits into a local floating-point register and multiplying it by
                                                                                                    the scale factor.It saves the resulting calculations inside a temporary stack array (output) and writes them to the
                                                                                                    destination buffer via memcpy.
    size_t numberOfValues = calcNumberOfElementsByTensor(inputTensor);
    size_t bytesPerOutputElement = sizeof(float);

    int32_t *inputAsInt32 = (int32_t *)inputTensor->data;
    float output[numberOfValues];

    symInt32QConfig_t *inputSymInt32QConfig = inputTensor->quantization->qConfig;
    float scale = inputSymInt32QConfig->scale;

    for (size_t i = 0; i < numberOfValues; i++) {
        output[i] = (float)inputAsInt32[i] * scale;
    }
    memcpy(outputTensor->data, output, numberOfValues * bytesPerOutputElement);
}

void requantSymInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {                 //This function handles dynamic re-quantization. It takes an integer tensor quantized with one scaling factor, finds its optimal 
                                                                                              new range, and changes its bit-width parameters or scale footprint.  
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    symInt32QConfig_t *inputSymInt32QC = inputTensor->quantization->qConfig;
    symInt32QConfig_t *outputSymInt32QC = outputTensor->quantization->qConfig;
    /* latch BEFORE writing outputSymInt32QC->scale: when called in-place
     * (inputTensor == outputTensor) both pointers alias the same config */
    float inScale = inputSymInt32QC->scale;                                                 //If this function is run in-place (inputTensor == outputTensor), the input and output configuration pointers alias the exact 
                                                                                              same chunk of memory. By saving (latching) the inScale variable immediately to the CPU stack before writing any output parameters,
                                                                                              the function prevents the old scaling factor from being overwritten and corrupted.

    const float qMax = powf(2, (float)outputSymInt32QC->qMaxBits - 1) - 1;
    const float qMin = -powf(2, (float)outputSymInt32QC->qMaxBits - 1);

    int32_t *inputInt32 = (int32_t *)inputTensor->data;
    int32_t *outputInt32 = (int32_t *)outputTensor->data;

    /* pass A: absmax over dequantized values — reads only (alias-safe) */
    float absMax = 0.f;
    for (size_t i = 0; i < numberOfElements; i++) {                                      //The algorithm loops through the dataset to evaluate what the real-world floating-point maximum absolute value (absMax) would be.
                                                                                           It then recalculates a brand new, highly optimized output scale constraint based on the target qMaxBits hardware limit.
        float dequant = fabsf((float)inputInt32[i] * inScale);
        if (dequant > absMax) {
            absMax = dequant;
        }
    }

    float scale;
    if (absMax == 0.f) {
        scale = 1.f;
    } else {
        scale = absMax / qMax;
    }
    outputSymInt32QC->scale = scale;

    /* pass B: same-index read-then-write — in-place safe (int32 both sides) */
    for (size_t i = 0; i < numberOfElements; i++) {                                                   //Because this loop reads element [i] and writes right back to element [i], it is in-place safe. It mathematically
                                                                                                        cancels out the old scale and applies the new scale step directly:\(\text{New\ Value}=\frac{\text{Old\ Value}\times 
                                                                                                        \text{InScale}}{\text{New\ Scale}}\)The final results are capped securely inside hardware integer registers (qMin to qMax)
                                                                                                        and rounded to integers via "Rounding.h".
        outputInt32[i] = roundByMode(clamp(((float)inputInt32[i] * inScale) / scale, qMin, qMax),
                                     outputSymInt32QC->roundingMode);
    }
}

void requantSymInt32TensorToScale(tensor_t *inputTensor, tensor_t *outputTensor) {                    //Unlike the function above which calculates a scale dynamically, this function forces a tensor to fit a pre-determined target 
                                                                                                        scale. This is highly important when preparing inputs for layer nodes (like Element-wise Add or Concat blocks) that require 
                                                                                                        all incoming data matrices to share an identical scaling factor.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    symInt32QConfig_t *inputSymInt32QC = inputTensor->quantization->qConfig;
    symInt32QConfig_t *outputSymInt32QC = outputTensor->quantization->qConfig;
    float inScale = inputSymInt32QC->scale;
    float targetScale = outputSymInt32QC->scale;

    /* NaN-robust: !(x > 0.f) is also true for NaN, unlike (x <= 0.f) */
    if (!(targetScale > 0.f)) {                                                                     //The Logic: In standard C, if a variable somehow corrupts into a NaN (Not a Number) value, traditional condition statements like
                                                                                                      if (targetScale <= 0.f) will evaluate to false.The Solution: By structuring the guard as an inverted positive check 
                                                                                                      !(targetScale > 0.f), the software detects NaN values, 0.0f, and negative bounds equally well, triggering an error exit 
                                                                                                      before a zero-division runtime crash can manifest
        PRINT_ERROR("requantSymInt32TensorToScale: target scale must be pre-set and > 0 on "
                    "the output qConfig, got %f",
                    targetScale);
        exit(1);
    }

    const float qMax = powf(2, (float)outputSymInt32QC->qMaxBits - 1) - 1;
    const float qMin = -powf(2, (float)outputSymInt32QC->qMaxBits - 1);

    int32_t *inputInt32 = (int32_t *)inputTensor->data;
    int32_t *outputInt32 = (int32_t *)outputTensor->data;

    /* single same-index read-then-write pass — shared-buffer in-place safe;
     * clamp saturates at qMin/qMax BY DESIGN (Deutel Eq. 4 analog) */
    for (size_t i = 0; i < numberOfElements; i++) {                                              //It runs a single, clean loop that re-projects the dataset straight onto the requested targetScale. If any number exceeds the 
                                                                                                   mathematical range of the target scale, the clamp functionality safely saturates the data limits directly at qMin or qMax without
                                                                                                   causing overflow errors.
        outputInt32[i] =
            roundByMode(clamp(((float)inputInt32[i] * inScale) / targetScale, qMin, qMax),
                        outputSymInt32QC->roundingMode);
    }
}

void convertSymInt32TensorToAsymTensor(tensor_t *inputTensor, tensor_t *outputTensor) {        //This function transforms data from an uncentered 32-bit symmetric integer form into a tight, bit-squeezed asymmetric layout.
                                                                                                 De-quantization Step: It multiplies the raw integers (inputAsInt32) by inputScale to unpack them into a temporary 32-bit float
                                                                                                 array (inputAsFloat).
    size_t numberOfValues = calcNumberOfElementsByTensor(inputTensor);

    symInt32QConfig_t *inputSymInt32QConfig = inputTensor->quantization->qConfig;
    asymQConfig_t *outputAsymQConfig = outputTensor->quantization->qConfig;

    float inputScale = inputSymInt32QConfig->scale;

    int32_t *inputAsInt32 = (int32_t *)inputTensor->data;

    float inputAsFloat[numberOfValues];
    for (size_t i = 0; i < numberOfValues; i++) {
        inputAsFloat[i] = inputScale * (float)inputAsInt32[i];
    }

    float min = findMinFloat((uint8_t *)inputAsFloat, numberOfValues);                      //The code casts a float * to a uint8_t * when passing it to findMinFloat. If findMinFloat expects a pointer to an array of
                                                                                              raw floats, this cast is unnecessary but safe. However, if findMinFloat treats the buffer as individual bytes under the hood, this
                                                                                              will read the binary bit representation of the floats instead of their actual numerical value, leading to completely broken min and
                                                                                              max limits.Asymmetric Mapping: It evaluates outputScale and computes the zeroPoint shift parameter.Bit-Squeezing: The quantized integer
                                                                                              values are stored in a temporary 32-bit stack array (outputInt). It then passes this array to byteConversion, which drops leading zeros
                                                                                              and compresses the data down into the target bit-width (qBits) inside outputTensor->data.
    float max = findMaxFloat((uint8_t *)inputAsFloat, numberOfValues);
    int32_t qMax = (1 << outputAsymQConfig->qBits) - 1;

    float outputScale = (max - min) / (float)qMax;
    outputAsymQConfig->scale = outputScale;

    int16_t zeroPoint = (int16_t)roundByMode(min / outputScale, outputAsymQConfig->roundingMode);
    outputAsymQConfig->zeroPoint = zeroPoint;

    int32_t outputInt[numberOfValues];
    for (size_t i = 0; i < numberOfValues; i++) {
        outputInt[i] =
            roundByMode(clamp(inputAsFloat[i] / outputScale - (float)zeroPoint, 0.f, qMax),
                        outputAsymQConfig->roundingMode);
    }

    byteConversion((uint8_t *)outputInt, 32, outputTensor->data, outputAsymQConfig->qBits,
                   numberOfValues);
}

void convertAsymTensorToInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {              //This function strips away asymmetric scaling properties, restoring compressed data to an unscaled, offset-corrected 32-bit
                                                                                                    standard integer format.Bit-Unpacking: It utilizes your sub-byte engine (byteConversion) to expand the compressed, low 
                                                                                                    bit-width elements (asymQConfig->qBits) out into full, uncompressed 32-bit chunks (32) stored in dataOut.
    asymQConfig_t *asymQConfig = inputTensor->quantization->qConfig;
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    int16_t zeroPoint = asymQConfig->zeroPoint;
    uint8_t dataOut[numberOfElements * sizeof(int32_t)];
    memset(dataOut, 0, numberOfElements * sizeof(int32_t));
    byteConversion(inputTensor->data, asymQConfig->qBits, dataOut, 32, numberOfElements);
    int32_t outputElements[numberOfElements];
    readBytesAsInt32Array(numberOfElements, dataOut, outputElements);

    for (size_t elementIndex = 0; elementIndex < numberOfElements; elementIndex++) {
        outputElements[elementIndex] = outputElements[elementIndex] + zeroPoint;                  //This formula is mathematically inverted. The core equation for asymmetric de-quantization is:\(\text{Real\ Float}=
                                                                                                    (\text{Quantized\ Integer}-\text{ZeroPoint})\times \text{Scale}\)To transition directly from an asymmetric integer to a regular
                                                                                                    integer, you must subtract the zeroPoint, not add it. Adding it shifts the entire array even further away from its correct 
                                                                                                    coordinates.
    }
    writeInt32ArrayToByteArray(numberOfElements, outputElements, outputTensor->data);
    copyDimsAndSparsityToTensor(inputTensor, outputTensor);
}

void convertAsymTensorToFloatTensor(tensor_t *inputTensor, tensor_t *outputTensor) {            //This function fully de-quantizes compressed asymmetric data layers back into raw, single-precision 32-bit floats.Unpacking: 
                                                                                                  It calls byteConversion to inflate the bit-packed tensor contents directly into a native 32-bit integer stack register buffer 
                                                                                                  (inputInt).
void convertAsymTensorToFloatTensor(tensor_t *inputTensor, tensor_t *outputTensor) {            
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);

    zeroTensorData(outputTensor);
    asymQConfig_t *asymQConfig = inputTensor->quantization->qConfig;
    int16_t zeroPoint = asymQConfig->zeroPoint;
    int32_t inputInt[numberOfElements];
    byteConversion(inputTensor->data, asymQConfig->qBits, (uint8_t *)inputInt, 32,
                   numberOfElements);
    float *outputElements = (float *)outputTensor->data;

    for (size_t elementIndex = 0; elementIndex < numberOfElements; elementIndex++) {
        outputElements[elementIndex] =
            ((float)inputInt[elementIndex] + (float)zeroPoint) * asymQConfig->scale;
    }

    copyDimsAndSparsityToTensor(inputTensor, outputTensor);
}

void convertAsymTensorToSymInt32Tensor(tensor_t *inputTensor, tensor_t *outputTensor) {     //This function shifts an asymmetrical compressed block into a symmetrical 32-bit layout.Unpacking: It inflates low bit-width
                                                                                              variables to 32-bit slots inside the inputAsInt32 buffer using byteConversion.The Repeated Mathematical Bug: It once again adds 
                                                                                              the zeroPoint (inputAsInt32[i] += zeroPoint;) instead of subtracting it.Scale Synchronization: It updates the output metadata 
                                                                                              container by transferring the scale parameter straight over: outputSymInt32QConfig->scale = inputAsymQConfig->scale;.
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    size_t bitsPerInputElement = calcBitsPerElement(inputTensor->quantization);
    size_t bytesPerOutputElement = sizeof(int32_t);

    asymQConfig_t *inputAsymQConfig = inputTensor->quantization->qConfig;
    symInt32QConfig_t *outputSymInt32QConfig = outputTensor->quantization->qConfig;

    int16_t zeroPoint = inputAsymQConfig->zeroPoint;

    int32_t inputAsInt32[numberOfElements];

    byteConversion(inputTensor->data, bitsPerInputElement, (uint8_t *)inputAsInt32, 32,
                   numberOfElements);

    for (size_t i = 0; i < numberOfElements; i++) {
        inputAsInt32[i] += zeroPoint;
    }

    memcpy(outputTensor->data, inputAsInt32, numberOfElements * bytesPerOutputElement);
    outputSymInt32QConfig->scale = inputAsymQConfig->scale;
}

char *quantTypeToString(qtype_t t) {                                                           //Purpose: A clean debugging utility that maps your runtime's quantization enumeration values (qtype_t) to human-readable
                                                                                                 string constants.Behavior: It maps variants like SYM_INT32 straight to "SYMINT32". If an invalid or unmapped value hits the 
                                                                                                 block, it falls through to a safe default of "UNKNOWN". This is highly useful for console logging and framework diagnostics 
                                                                                                 (printf("Layer Type: %s\n", quantTypeToString(tensor->quantization->type));).
    switch (t) {
    case INT32:
        return "INT32";
    case FLOAT32:
        return "FLOAT32";
    case SYM_INT32:
        return "SYMINT32";
    case SYM:
        return "SYM";
    case ASYM:
        return "ASYM";
    case BOOL:
        return "BOOL";
    default:
        return "UNKNOWN";
    }
}

void unsupportedConversionTypes(tensor_t *inputTensor, tensor_t *outputTensor) {
    qtype_t inputQType = inputTensor->quantization->type;
    qtype_t outputQType = outputTensor->quantization->type;

    PRINT_ERROR("Conversion from %s to %s is not supported", quantTypeToString(inputQType),
                quantTypeToString(outputQType));
    exit(1);
}

_Static_assert(BOOL + 1 == 6, "extend conversionMatrix when adding qtype_t entries");

conversionFunction_t conversionMatrix[6][6] = {
    [INT32] = {[INT32] = NULL,
               [FLOAT32] = convertInt32TensorToFloatTensor,
               [SYM_INT32] = convertInt32TensorToSymInt32Tensor,
               [SYM] = unsupportedConversionTypes,
               [ASYM] = convertInt32TensorToAsymTensor,
               [BOOL] = unsupportedConversionTypes},
    [FLOAT32] = {[INT32] = convertFloatTensorToInt32Tensor,
                 [FLOAT32] = NULL,
                 [SYM_INT32] = convertFloatTensorToSymInt32Tensor,
                 [SYM] = unsupportedConversionTypes,
                 [ASYM] = convertFloatTensorToAsymTensor,
                 [BOOL] = unsupportedConversionTypes},
    [SYM_INT32] = {[INT32] = extractInt32TensorFromSymInt32Tensor,
                   [FLOAT32] = convertSymInt32TensorToFloat32Tensor,
                   [SYM_INT32] = requantSymInt32Tensor,
                   [SYM] = unsupportedConversionTypes,
                   [ASYM] = convertSymInt32TensorToAsymTensor,
                   [BOOL] = unsupportedConversionTypes},
    [SYM] = {[INT32] = unsupportedConversionTypes,
             [FLOAT32] = unsupportedConversionTypes,
             [SYM_INT32] = unsupportedConversionTypes,
             [SYM] = NULL,
             [ASYM] = unsupportedConversionTypes,
             [BOOL] = unsupportedConversionTypes},
    [ASYM] = {[INT32] = convertAsymTensorToInt32Tensor,
              [FLOAT32] = convertAsymTensorToFloatTensor,
              [SYM_INT32] = convertAsymTensorToSymInt32Tensor,
              [SYM] = unsupportedConversionTypes,
              [ASYM] = NULL,
              [BOOL] = unsupportedConversionTypes},
    [BOOL] = {[INT32] = unsupportedConversionTypes,
              [FLOAT32] = unsupportedConversionTypes,
              [SYM_INT32] = unsupportedConversionTypes,
              [SYM] = unsupportedConversionTypes,
              [ASYM] = unsupportedConversionTypes,
              [BOOL] = NULL}};

static void convertTensorsWithSameType(tensor_t *inputTensor, tensor_t *outputTensor,
                                       qtype_t qType) {
    size_t numberOfElements = calcNumberOfElementsByTensor(inputTensor);
    size_t numberOfBytes = calcNumberOfBytesForData(inputTensor->quantization, numberOfElements);

    memmove(outputTensor->data, inputTensor->data, numberOfBytes);

    switch (qType) {
    case SYM_INT32:
        symInt32QConfig_t *inputSymIntQC = inputTensor->quantization->qConfig;
        symInt32QConfig_t *outputSymIntQC = outputTensor->quantization->qConfig;
        outputSymIntQC->scale = inputSymIntQC->scale;
        break;
    case ASYM:
        asymQConfig_t *inputAsymQC = inputTensor->quantization->qConfig;
        asymQConfig_t *outputAsymQC = outputTensor->quantization->qConfig;
        outputAsymQC->scale = inputAsymQC->scale;
        outputAsymQC->zeroPoint = inputAsymQC->zeroPoint;
        break;
    default:
        break;
    }
}

void convertTensor(tensor_t *inputTensor, tensor_t *outputTensor) {
    qtype_t inputDType = inputTensor->quantization->type;
    qtype_t outputDType = outputTensor->quantization->type;

    if (inputDType == outputDType) {
        convertTensorsWithSameType(inputTensor, outputTensor, inputDType);
    } else {
        conversionFunction_t conversionFn = conversionMatrix[inputDType][outputDType];
        if (conversionFn == NULL) {
            PRINT_ERROR("No conversion function registered for %s to %s",
                        quantTypeToString(inputDType), quantTypeToString(outputDType));
            exit(1);
        }
        conversionFn(inputTensor, outputTensor);
    }
}
