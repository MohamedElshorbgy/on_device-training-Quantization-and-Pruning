#ifndef ODT_COMMON_H                                                                                   
\\  it is a guard symbol for OnDeviceTraining which means if this symbol not defined , the compiler will process everything tell endif                                                                          
#define ODT_COMMON_H

#include <stdbool.h>
\\ it is a header file for boolean (0,1)
#include <stdio.h>
#include <string.h>

#ifndef SOURCE_FILE
\\ each .c file is expected to define the source file
#define SOURCE_FILE "no Source file defined!"
#endif

#ifdef DEBUG_MODE_DEBUG
\\ if the compiler was invoked with the flag DEBUG_MODE_DEBUG , set the DLEVEL to 3
#define DLEVEL 3
#elif defined(DEBUG_MODE_INFO)
#define DLEVEL 2
#elif defined(DEBUG_MODE_ERROR)
#define DLEVEL 1
#else
#define DLEVEL 0
#endif

#define PRINT_DEBUG(str, ...)  
\\it is a macro that accept a string and any other arguments                                                                    \
    do {                                                                                           \
        if (DLEVEL >= 3) {                                                                         \
            printf("\033[0;33m[%s: %s] ", SOURCE_FILE, __FUNCTION__);                              \    \\change the terminal to yellow and mention the source file
            printf(str, ##__VA_ARGS__);                                                            \
            printf("\033[0m\n");                                                                   \     \\ reset the colour to the normal
        }                                                                                          \
    } while (false)

#define PRINT_INFO(str, ...)                                                                       \
    do {                                                                                           \
        if (DLEVEL >= 2) {                                                                         \
            printf("[%s: %s] ", SOURCE_FILE, __FUNCTION__);                                        \
            printf(str, ##__VA_ARGS__);                                                            \
            printf("\n");                                                                          \
        }                                                                                          \
    } while (false)

#define PRINT_ERROR(str, ...)                                                                      \
    do {                                                                                           \
        if (DLEVEL >= 1) {                                                                         \
            printf("\033[0;31m[%s: %s] ", SOURCE_FILE, __FUNCTION__);                              \
            printf(str, ##__VA_ARGS__);                                                            \
            printf("\033[0m\n");                                                                   \
        }                                                                                          \
    } while (false)

// TODO

#define PRINT_BYTE_ARRAY(prefix, byteArray, numberOfBytes)                                         \
\\it is a macro to dump the raw content of the a memory buffer. prefix is a label string(weight ,gradient,...) the caller provides. byteArray is a pointer to the memory to inspect. numberOfBytes is how many bytes to print    
	do {                                                                                           \
        printf("[%s: %s] ", SOURCE_FILE, __FUNCTION__);                                            \
        printf(prefix);                                                                            \
        for (size_t index = 0; index < numberOfBytes; index++) {                                   \
\\loop over every bytes in the buffer. size_t is the unsigned integer that used for the count  
			printf("0x%02X ", byteArray[index]);                                                   \
\\print each byte in hexadecimal form wher 0x is the conventional prefix to hexadecimal and %02X means print as uppercase hexa with at least two digits
		}                                                                                          \
        printf("\n");                                                                              \
    } while (false)

#endif
