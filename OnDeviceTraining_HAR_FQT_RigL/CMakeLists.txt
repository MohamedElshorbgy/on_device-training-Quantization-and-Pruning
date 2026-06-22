cmake_minimum_required(VERSION 3.20)
project(har_fqt_rigl C)
set(CMAKE_C_STANDARD 11)

# ── Path to the OnDeviceTraining framework ────────────────────────
# Assumes this project lives at:
#   <root>/OnDeviceTraining_HAR_FQT_RigL/
# and the framework lives at:
#   <root>/OnDeviceTraining/
# Override by passing -DODT_DIR=/absolute/path at cmake configure time.
if(NOT DEFINED ODT_DIR)
    set(ODT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../OnDeviceTraining")
endif()

# Pull in the framework (builds all library targets; skips tests/examples
# because ODT_TOP_LEVEL_PROJECT will be false).
add_subdirectory("${ODT_DIR}" odt_build)

# ── Our executable ────────────────────────────────────────────────
add_executable(har_fqt_rigl
    src/main.c
    src/rigl.c
    src/fqt.c          # INT8 inference utilities (post-training quant)
)

# ── Include paths ─────────────────────────────────────────────────
target_include_directories(har_fqt_rigl PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# ── Compiler flags ────────────────────────────────────────────────
target_compile_options(har_fqt_rigl PRIVATE
    -O2 -Wall -Wextra -Wno-unused-parameter)

# ── Link framework libraries (same set as har_classifier_v2) ──────
target_link_libraries(har_fqt_rigl PRIVATE
    # Data loading
    DataLoaderApi
    DataLoader
    NPYLoaderApi
    NPYLoader

    # Layers
    Layer
    Conv1dApi
    Conv1d
    LinearApi
    Linear
    ReluApi
    Relu
    FlattenApi
    Flatten
    Pool1dApi
    MaxPool1d
    AvgPool1d
    SoftmaxApi
    Softmax

    # Quantization
    QuantizationApi
    Quantization

    # Tensor
    TensorApi
    Tensor
    Rounding

    # Training
    TrainingLoopApi
    CalculateGradsSequential
    TrainingBatchDefault
    TrainingEpochDefault
    Optimizer
    LossFunction
    CrossEntropy
    Sgd
    SgdApi
    InferenceApi

    # Layer utilities
    LayerQuant
    LayerCommon
    StateDictApi
    LayerWeightsApi
    Distributions

    # Framework core
    Common
    StorageApi
    RNG

    # Math
    m
)

# ── Build instructions ────────────────────────────────────────────
#
# Run from OnDeviceTraining_HAR_FQT_RigL/ :
#
#   mkdir build_pc && cd build_pc
#   cmake .. -f ../CMakeLists_PC.txt
#   make -j$(nproc)
#
# Then run from the OnDeviceTraining root so data paths resolve:
#
#   cd ../../OnDeviceTraining
#   ../OnDeviceTraining_HAR_FQT_RigL/build_pc/har_fqt_rigl
#
# Or pass the data path explicitly:
#
#   ./build_pc/har_fqt_rigl  /absolute/path/to/har_classifier/data
