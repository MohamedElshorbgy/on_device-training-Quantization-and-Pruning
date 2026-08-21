//This source file implements the serialization and deserialization functions declared in the header file you provided earlier. 
It relies heavily on the standard C library function memcpy from <string.h> to copy raw bit patterns directly between variables 
and raw byte blocks.Using memcpy is standard practice in embedded systems and AI runtimes because it avoids strict aliasing 
violations (undefined behavior when casting pointers directly, like *(int32_t*)bytes) and safely avoids alignment crashes on
hardware architectures that do not support unaligned memory access.





#define SOURCE_FILE "DTYPES"

#include <string.h>

#include "DTypes.h"
#include "Tensor.h"

int32_t readBytesAsInt32(uint8_t *bytes) {                                                          //Allocates a local variable (x) on the stack. It copies exactly 4 bytes (sizeof(int32_t) and sizeof(float)) from the memory
                                                                                                      address pointed to by bytes into the memory block allocated for x.Behavior: It takes the raw, uninterpreted bits from 
                                                                                                      memory and loads them into a CPU register as a standard numeric value.
                                                                                                      
    int32_t x;
    memcpy(&x, bytes, sizeof(int32_t));
    return x;
}

int32_t readNumberOfBytesAsInt32(uint8_t *data, size_t numberOfBytes) {                            //Mechanism: Initialises a 32-bit container (output) to 0. It then copies only a dynamic number of bytes specified by 
                                                                                                     numberOfBytes into that container.Critical Technical Detail: Because output is initialised to 0, any remaining bytes 
                                                                                                     that are not written to by memcpy remain zero.If numberOfBytes is 2, this successfully loads a 16-bit integer into 
                                                                                                     a 32-bit placeholder (zero-extended).Warning: This function assumes a Little-Endian system architecture. On a 
                                                                                                     Little-Endian system, the least significant bytes are stored first. 
                                                                                                     If you copy 2 bytes into output, they will occupy the lowest 16 bits of the integer. On a Big-Endian system, this would 
                                                                                                     mistakenly populate the most significant bits, resulting in incorrect calculations.
    int32_t output = 0;
    memcpy(&output, data, numberOfBytes);

    return output;
}

void readBytesAsInt32Array(size_t numberOfValues, uint8_t *bytes, int32_t *outputArray) {           //Mechanism: Loops through the required total count of numbers.Index Arithmetic: For each iteration i, it calculates
                                                                                                      the offset memory address inside the flat byte buffer using byteIndex = i * 4.Note on Optimization: While highly readable
                                                                                                      , this code calls readBytesAsInt32 and copies data 4 bytes at a time inside a loop. If bytes and outputArray are 
                                                                                                      guaranteed to share the same byte ordering, this whole function could be replaced with a single, highly-optimized block 
                                                                                                      copy:memcpy(outputArray, bytes, numberOfValues * sizeof(int32_t));(The same loop mechanics and optimization notes apply
                                                                                                      directly to readBytesAsFloatArray).
                                                                                                     
    for (size_t i = 0; i < numberOfValues; i++) {
        size_t byteIndex = i * sizeof(int32_t);
        int32_t value = readBytesAsInt32(&bytes[byteIndex]);
        outputArray[i] = value;
    }
}

float readBytesAsFloat(uint8_t *bytes) {                                                            //Converts 4 continuous bytes into a single floating-point number.How it works: It allocates a temporary local float 
                                                                                                      variables x. It then copies exactly sizeof(float) bytes (which is almost universally \(4\) bytes on modern systems) 
                                                                                                      from the memory address pointed to by bytes into the address of x.                                
    float x;
    memcpy(&x, bytes, sizeof(float));
    return x;
}

void readBytesAsFloatArray(size_t numberOfValues, uint8_t *bytes, float *outputArray) {             //Deserializes a large stream of bytes into an array of floats.How it works:It loops through the desired number 
                                                                                                      of float elements (numberOfValues).It calculates the offset in the byte buffer using byteIndex = i * 4. For example, 
                                                                                                      the 3rd float (\(i = 2\)) starts at byte index \(8\).It passes the memory address of that specific offset
                                                                                                      (&bytes[byteIndex]) to the readBytesAsFloat function.The returned float is stored sequentially into the outputArray.
    for (size_t i = 0; i < numberOfValues; i++) {
        size_t byteIndex = i * sizeof(float);
        float value = readBytesAsFloat(&bytes[byteIndex]);
        outputArray[i] = value;
    }
}

void writeInt32ToByteArray(int32_t value, uint8_t *bytes) {                                         //Packs a single 32-bit integer or a 32-bit float into a 4-byte destination buffer.How it works: They take the variable
                                                                                                      (value) and copy its raw memory footprint directly into the destination array pointed to by bytes.
    memcpy(bytes, &value, sizeof(int32_t));
}

void writeInt32ArrayToByteArray(size_t numberOfValues, int32_t *valueArray, uint8_t *bytes) {       //Serializes entire arrays of integers or floats into a single flat byte stream.How it works: Much like the array 
                                                                                                      reading function, these loop through the source arrays, calculate the byte index offset step-by-step 
                                                                                                      (\(0, 4, 8, 12 \dots\)), and copy the 4-byte blocks into the destination bytes buffer one after the other.
    for (size_t i = 0; i < numberOfValues; i++) {
        size_t byteIndex = i * sizeof(int32_t);
        memcpy(&bytes[byteIndex], &valueArray[i], sizeof(int32_t));
    }
}

void writeFloatToByteArray(float value, uint8_t *bytes) {
    memcpy(bytes, &value, sizeof(float));
}

void writeFloatArrayToByteArray(size_t numberOfValues, float *valueArray, uint8_t *bytes) {
    for (size_t i = 0; i < numberOfValues; i++) {
        size_t byteIndex = i * sizeof(float);
        memcpy(&bytes[byteIndex], &valueArray[i], sizeof(float));
    }
}
