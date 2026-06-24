#ifndef ODT_COMMON_H                                                                                     //mean that if the file ODT_COMMON_H not defined , define it and read the file otherwise skip the file
#define ODT_COMMON_H
                                                                                                        
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#ifndef SOURCE_FILE
#define SOURCE_FILE "no Source file defined!"
#endif

#ifdef DEBUG_MODE_DEBUG
#define DLEVEL 3
#elif defined(DEBUG_MODE_INFO)
#define DLEVEL 2
#elif defined(DEBUG_MODE_ERROR)
#define DLEVEL 1
#else
#define DLEVEL 0
#endif

#define PRINT_DEBUG(str, ...)                                                                      \        //Logging Macros: Logging means writing down notes while the program runs
                                                                                               
                                                                                                          ##__VA_ARGS__ is a special trick used in macros to handle a variable number of arguments (inputs)                                                                                                          #define PRINT_INFO(str, ...)  printf(str, ##__VA_ARGS__):This tells the compiler,
                                                                                                          "Hey, after the first text string (str),                                                                                                         the user might type a bunch of other variables. Just grab them all."
                                                                                                          __VA_ARGS__: This is a placeholder. The compiler will take whatever extra variables it grabbed in the ...                                                                                                           and paste them right here
    do {                                                                                           \
        if (DLEVEL >= 3) {                                                                         \
            printf("\033[0;33m[%s: %s] ", SOURCE_FILE, __FUNCTION__);                              \
            printf(str, ##__VA_ARGS__);                                                            \
            printf("\033[0m\n");                                                                   \
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
    do {                                                                                           \
        printf("[%s: %s] ", SOURCE_FILE, __FUNCTION__);                                            \
        printf(prefix);                                                                            \
        for (size_t index = 0; index < numberOfBytes; index++) {                                   \
            printf("0x%02X ", byteArray[index]);                                                   \
        }                                                                                          \
        printf("\n");                                                                              \
    } while (false)

#endif
