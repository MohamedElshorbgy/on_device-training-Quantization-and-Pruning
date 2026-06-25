//
// Created by Leo Buron on 20.10.25.
//

#ifndef ENV5_RUNTIME_DATASTORAGE_H
#define ENV5_RUNTIME_DATASTORAGE_H
#include <stddef.h>
#include <stdint.h>

typedef struct Entry {                                                                              //This structure acts like an entry in a book's index. It does not hold the actual data values; instead, 
                                                                                                      it points to where they live.uint8_t *dataPTR: A pointer holding the starting memory address of the data 
                                                                                                      segment inside the master array.size_t numberOfElements: Tracks how many elements (or bytes) belong to this specific entry.
    uint8_t *dataPTR; // PTR for starting address in uint8_t array
    size_t numberOfElements;
} dataEntry_t;

typedef struct DataStorage {                                                                       //This is the main structural manager that encapsulates the entire memory arena.uint8_t *data: A pointer to the massive,
                                                                                                     raw block of memory where all actual payloads are stored sequentially.size_t size: The maximum capacity (in bytes) 
                                                                                                     allocated for the data block.dataEntry_t *entries: A pointer to an array of index entries (dataEntry_t). This acts as
                                                                                                     the registry table.size_t numberOfEntries: The current count of registered entries currently saved in the entries array.
    uint8_t *data;
    size_t size;
    dataEntry_t *entries;
    size_t numberOfEntries;
} dataStorage_t;

uint8_t *getDataFromStorage(dataStorage_t storage, void *dataPTR);                                //Purpose: Finds and extracts a data block out of the pool.How it likely works under the hood: It takes the storage manager
                                                                                                    and searches through the entries array, looking for an entry where the metadata's internal pointer matches the requested 
                                                                                                    dataPTR. It then returns the exact address of the data block.Note: The input uses a generic void * pointer, allowing you
                                                                                                    to pass any data type pointer (like a float* or int32_t*) without explicit casting
dataEntry_t *addDataToStorage(dataStorage_t storage, void *dataPTR, size_t numberOfElements);     //Purpose: Registers a new block of data into the storage network.How it likely works under the hood: It appends a new
                                                                                                    dataEntry_t record into the entries array, saving the memory address (dataPTR) and its length (numberOfElements). It then
                                                                                                    increments numberOfEntries.Return Value: It returns a pointer to the newly created index entry, allowing the calling 
                                                                                                    application to track or modify the metadata definition.

#endif // ENV5_RUNTIME_DATASTORAGE_H
