#ifndef ELASTIC_AI_RUNTIME_ENV5_DTYPES_H                                                            //This header file (elastic_ai_runtime_env5_dtypes.H) defines a C interface for serialization and deserialization—the process
                                                                                                      of converting raw byte arrays (uint8_t *) into structured data types (int32_t and float), and vice versa.In embedded 
                                                                                                      systems, edge AI accelerators, or hardware-software interfaces (like FPGA-to-CPU runtimes), data is typically streamed 
                                                                                                      or stored as flat arrays of raw bytes. This file provides the function declarations (prototypes) necessary to read and
                                                                                                      write multi-byte numbers safely across those boundaries.
#define ELASTIC_AI_RUNTIME_ENV5_DTYPES_H

#include <stddef.h>
#include <stdint.h>
 
int32_t readBytesAsInt32(uint8_t *bytes);                                                           //: A 32-bit integer is composed of exactly 4 bytes. This function will read 4 sequential bytes starting from the address
                                                                                                        pointed to by bytes. Note: The internal implementation must handle "Endianness" (whether the highest or lowest byte 
                                                                                                        comes first in memory).
int32_t readNumberOfBytesAsInt32(uint8_t *data, size_t numberOfBytes);                              //A more flexible integer reader. It reads a dynamic number of bytes (defined by numberOfBytes) and converts them into 
                                                                                                      a 32-bit container.
                                                                                                      
void readBytesAsInt32Array(size_t numberOfValues, uint8_t *bytes, int32_t *outputArray);            //It will read a total of numberOfValues * 4 bytes from the raw bytes buffer, unpack them, and store them sequentially 
                                                                                                      into outputArray.

float readBytesAsFloat(uint8_t *bytes);                                                             //Converts 4 raw bytes into a single-precision floating-point number (float).
void readBytesAsFloatArray(size_t numberOfValues, uint8_t *bytes, float *outputArray);              //Deserializes a large stream of bytes into an array of floating-point numbers. It reads a chunk of
                                                                                                      numberOfValues * 4 bytes out of the raw buffer and populates the outputArray. This is highly critical in AI runtime
                                                                                                      environments for loading large matrices of model weights or input tensors.

void writeInt32ToByteArray(int32_t value, uint8_t *bytes);                                          //Takes a 32-bit integer value, breaks it down into 4 individual bytes, and writes them into the memory address at bytes.
void writeInt32ArrayToByteArray(size_t numberOfValues, int32_t *valueArray, uint8_t *bytes);        //Serializes a whole array of integers into a flat sequence of bytes. It takes numberOfValues from valueArray and 
                                                                                                      packs them into a continuous block of bytes starting at bytes.

void writeFloatToByteArray(float value, uint8_t *bytes);                                            //Breaks down a 32-bit IEEE 754 float value into 4 raw constituent bytes and writes them to the bytes pointer destination.
void writeFloatArrayToByteArray(size_t numberOfValues, float *valueArray, uint8_t *bytes);          //Packs an array of floating-point numbers into a stream of raw bytes. This is commonly used when an AI model 
                                                                                                      finishes executing an inference step, and the output layer's floating-point activations need to be serialized so they
                                                                                                      can be transmitted back over a communication bus (like SPI, I2C, UART, or PCIe).

#endif // ELASTIC_AI_RUNTIME_ENV5_DTYPES_H
