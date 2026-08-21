#ifndef ENV5_RUNTIME_MATMUL_H
#define ENV5_RUNTIME_MATMUL_H

#include <stddef.h>

#include "Tensor.h"

typedef void (*matmulFunc_t)(tensor_t *aTensor, tensor_t *bTensor, tensor_t outputTensor);           //Purpose: Declares a generic function pointer type for matrix multiplication.Usage: Allows the runtime to dynamically 
                                                                                                       switch between different matrix multiplication implementations (e.g., swapping a purely software-based loop with a 
                                                                                                       hardware-accelerated version) at runtime.Design Note: Notice that outputTensor is passed by value here (tensor_t), 
                                                                                                       whereas the main functions pass it by pointer (tensor_t *). If this isn't a typo, passing the struct by value means 
                                                                                                       copying its shape metadata onto the stack, which is atypical for modification.

void matmulInt32Tensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor);               //Purpose: Performs classical 2D matrix multiplication (\(C = A \times B\)) for 32-bit integers and 32-bit 
                                                                                                       floating-point numbers.Expected Validation: Inside their implementations, these functions must verify that the inner
                                                                                                       dimensions match: the columns of matrix A (dimension 1) must equal the rows of matrix B (dimension 0).

void matmulFloat32Tensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor);

void matmulSymInt32Tensors(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor);            //Purpose: "Sym" stands for Symmetric Quantization. This routine is designed for running compressed Neural Network models
                                                                                                       (like INT8 or INT16 quantized models) whose weights have been scaled or accumulated into a 32-bit integer container 
                                                                                                       (Int32).Under the Hood: It typically multiplies low-bitwidth integers (e.g., quantized weights) and accumulates the 
                                                                                                       intermediate values into int32_t to avoid overflow before applying a quantization scale/zero-point factor.

void matmulFloat32TensorsWithBias(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor, 
                                  tensor_t *bias);                                                    //Purpose: Implements a fused Fully Connected / Linear Layer operation common in Neural Networks 
                                                                                                        (\(C = A \times B + \text{bias}\)).Performance Benefit: Fusing the addition of the bias tensor directly into the matrix
                                                                                                        multiplication loop avoids sweeping through the entire memory buffer a second time. This drastically cuts down on 
                                                                                                        memory bandwidth usage, which is often the tightest bottleneck in embedded hardware deployments.

void matmulSymInt32TensorsWithBias(tensor_t *aTensor, tensor_t *bTensor, tensor_t *outputTensor,
                                   tensor_t *bias);

size_t getMatmulInstructionCounter();                                                                  //Purpose: A profiling tool used to track performance metrics, cycle counts, or hardware accelerator invocations.Usage:
                                                                                                         In a simulation or hardware environment, this returns how many dedicated GEMM (General Matrix Multiply) instructions
                                                                                                         or clock cycles were consumed by the operations. This is vital for bench-marking deep learning models. 

#endif // ENV5_RUNTIME_MATMUL_H
