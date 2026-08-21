\\DTypes is a translator between numbers (float, int32_t) and bytes (uint8_t). It converts in both directions — numbers → bytes and bytes → numbers.
DTypes sits at the boundary between computation (numbers) and communication (bytes). Without it, you could not move tensor data between 
your PC and the MCU.

#ifndef ELASTIC_AI_RUNTIME_ENV5_DTYPES_H
#define ELASTIC_AI_RUNTIME_ENV5_DTYPES_H

#include <stddef.h>
\\is a standard C library header that defines fundamental system types, constants, and utility macros used across mainstream and 
embedded C programming such as size_t
#include <stdint.h>
is a standard C library header that provides fixed-width integer types
int32_t readBytesAsInt32(uint8_t *bytes);
\\Read 4 consecutive bytes and interpret them as a signed 32-bit integer. "uint8_t *bytes" is a pointer to the start of the byte buffer. uint8_t
is an unsigned 8-bit integer — the smallest addressable unit of memory. A 32-bit integer occupies exactly 4 bytes, so this function reads 4 bytes.
int32_t readNumberOfBytesAsInt32(uint8_t *data, size_t numberOfBytes);
\\Takes: a pointer to bytes + how many bytes to read (can be less than 4).
Returns: one int32_t with the remaining bytes filled as zero.
This exists for protocols that pack small numbers into fewer than 4 bytes to save space. For example, a value that fits in 2 bytes 
does not need to be sent as 4 bytes.
void readBytesAsInt32Array(size_t numberOfValues, uint8_t *bytes, int32_t *outputArray);
\\Takes: how many integers to read + source byte array + destination integer array.
Returns: nothing — fills outputArray directly.
float readBytesAsFloat(uint8_t *bytes);
\\Takes: pointer to at least 4 bytes.
Returns: one float — those 4 bytes interpreted as an IEEE 754 floating-point number.
void readBytesAsFloatArray(size_t numberOfValues, uint8_t *bytes, float *outputArray);
\\Takes: count + source bytes + destination float array.
Returns: nothing — fills outputArray with floats.
Used to deserialize an entire weight tensor. A tensor of 1000 floats arrives as 4000 bytes — this function converts all 4000 bytes back
into 1000 floats in one call.
void writeInt32ToByteArray(int32_t value, uint8_t *bytes);
Takes: one integer + a destination byte array (must have room for at least 4 bytes).
Returns: nothing — writes 4 bytes into bytes.
The exact reverse of readBytesAsInt32.
void writeInt32ArrayToByteArray(size_t numberOfValues, int32_t *valueArray, uint8_t *bytes);
\\Takes: count + source integer array + destination byte array.
Returns: nothing — serializes every integer into 4 consecutive bytes.
void writeFloatToByteArray(float value, uint8_t *bytes);
Takes: one float + destination byte array.
Returns: nothing — copies the float's 4 raw bytes into bytes.
void writeFloatArrayToByteArray(size_t numberOfValues, float *valueArray, uint8_t *bytes);
\\Takes: count + source float array + destination byte array.
Returns: nothing — serializes all floats into a flat byte stream.
This is the function used when the training is done and you want to pack the learned weights into bytes to send to the STM32.
#endif // ELASTIC_AI_RUNTIME_ENV5_DTYPES_H

--------------------------------------------------------------------------------------------------------------------------------------------------

#define SOURCE_FILE "DTYPES"

#include <string.h>

#include "DTypes.h"
#include "Tensor.h"

int32_t readBytesAsInt32(uint8_t *bytes) {
    int32_t x;
    memcpy(&x, bytes, sizeof(int32_t));
    return x;
}
\\memcpy copies the sizeof(int32_t) which is 4 bytes from variable bytes into variable x  
int32_t readNumberOfBytesAsInt32(uint8_t *data, size_t numberOfBytes) {
    int32_t output = 0;
    memcpy(&output, data, numberOfBytes);

    return output;
}
\\uint8_t *data — a pointer to the first byte of the raw memory you want to read.
\\size_t numberOfBytes — how many bytes to read from data.
void readBytesAsInt32Array(size_t numberOfValues, uint8_t *bytes, int32_t *outputArray) {
    for (size_t i = 0; i < numberOfValues; i++) {
        size_t byteIndex = i * sizeof(int32_t);
        int32_t value = readBytesAsInt32(&bytes[byteIndex]);
        outputArray[i] = value;
    }
}
\\numberOfValues — how many int32 numbers to read
bytes — the raw byte buffer to read from
outputArray — where to write the converted int32 values
Loop once for each int32 value you want to read. If numberOfValues is 3, the loop runs 3 times (i = 0, 1, 2).
Calculates where in the byte buffer the current int32 starts. Each int32 occupies 4 bytes, so:

i=0 → byteIndex = 0 * 4 = 0   ← first  int32 starts at byte 0
i=1 → byteIndex = 1 * 4 = 4   ← second int32 starts at byte 4
i=2 → byteIndex = 2 * 4 = 8   ← third  int32 starts at byte 8
Takes 4 bytes starting at byteIndex and converts them into one int32_t using readBytesAsInt32. 
The & gives the address of that specific byte in the buffer.
float readBytesAsFloat(uint8_t *bytes) {
    float x;
    memcpy(&x, bytes, sizeof(float));
    return x;
}

void readBytesAsFloatArray(size_t numberOfValues, uint8_t *bytes, float *outputArray) {
    for (size_t i = 0; i < numberOfValues; i++) {
        size_t byteIndex = i * sizeof(float);
        float value = readBytesAsFloat(&bytes[byteIndex]);
        outputArray[i] = value;
    }
}

void writeInt32ToByteArray(int32_t value, uint8_t *bytes) {
    memcpy(bytes, &value, sizeof(int32_t));
}

void writeInt32ArrayToByteArray(size_t numberOfValues, int32_t *valueArray, uint8_t *bytes) {
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

