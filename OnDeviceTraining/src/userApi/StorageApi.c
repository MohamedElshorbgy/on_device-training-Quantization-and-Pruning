#define SOURCE_FILE "STORAGE_API"

#include <stdlib.h>

#include "StorageApi.h"

void *reserveMemory(size_t numberOfBytes) {                             //How it works: Instead of using the standard malloc(), this implementation calls calloc(size_t num, size_t size).The calloc Advantage:malloc simply
                                                                          allocates memory but leaves whatever old data happened to be sitting in those hardware circuits intact (resulting in unpredictable "garbage" values).
                                                                          calloc takes two arguments (here, 1 allocation block of size numberOfBytes) and automatically clears all allocated memory bits to zero.Safety Benefit:
                                                                          This prevents uninitialized memory bugs. If you map a struct or an array to this memory later, all fields are guaranteed to start at zero or NULL, 
                                                                          ensuring highly predictable software execution.Return Behavior: If the operating system or microcontroller runs completely out of memory, calloc 
                                                                          returns NULL. Because this function directly returns the result of calloc, reserveMemory will also pass back NULL when memory is exhausted
    return calloc(1, numberOfBytes);
}

void freeReservedMemory(void *ptr) {                                   //How it works: This takes the generic memory pointer (ptr) and forwards it straight to the standard library's free() function.Fulfilling the 
                                                                        "NULL-Safe" Promise: As discussed in the header file documentation, the wrapper claims to be "NULL-safe (mirrors free(NULL))". In the standard C 
                                                                        specification, passing a NULL pointer to free() is completely safe and results in a no-operation (the function returns immediately without doing
                                                                        anything). Because it directly invokes free(ptr), it naturally inherits this exact same safe behavior.
    free(ptr);
}
