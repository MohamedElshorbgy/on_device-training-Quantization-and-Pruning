#ifndef STORAGEAPI_H
#define STORAGEAPI_H

#include <stddef.h>

void *reserveMemory(size_t numberOfBytes);                         //Purpose: Requests a continuous block of memory of a specific size (in bytes).Return Type (void *): Returns a generic untyped pointer.
                                                                     In C, a void * can be automatically implicitly cast into any specific pointer type (such as float *, int32_t *, or custom structures
                                                                     like dataStorage_t *) without requiring manual casting.How it works under the hood: Depending on the backend platform, this function 
                                                                     will typically do one of two things:Dynamic (Heap-based): Call standard malloc(numberOfBytes) behind the scenes.Static (Arena/Pool-based)
                                                                    : Carve out a chunk of a pre-allocated static byte array (common in microcontrollers to guarantee deterministic behavior).Defensive Design:
                                                                     If memory runs out or cannot be allocated, this function should return NULL.

/* NULL-safe (mirrors free(NULL)). */
void freeReservedMemory(void *ptr);                                 //Purpose: Releases a previously allocated block of memory back to the system so it can be reused.The "NULL-safe" Promise: The comment
                                                                      specifies that it explicitly mirrors standard free(NULL). In standard C, calling free(NULL) is completely safe and does nothing. 
                                                                      This means the implementation of freeReservedMemory must explicitly check if the incoming ptr is NULL, and if so, safely exit immediately 
                                                                      without throwing a hardware exception or segmentation fault.Why it matters: It removes the burden from the developer to write safety checks
                                                                      like if (ptr != NULL) freeReservedMemory(ptr); everywhere in the codebase.

#endif // STORAGEAPI_H
