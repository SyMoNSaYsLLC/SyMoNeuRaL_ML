cmake_minimum_required(VERSION 3.20)
project(SyMoNeuRaL_ML LANGUAGES C CXX)

# This is the SyMoNeuRaL_ML aggregate project wrapper.
# It does not rewrite llama.cpp or stable-diffusion.cpp; it builds the vendored engines
# in the same CMake style as their upstream examples while the production API remains Python/FastAPI.

option(SYMON_BUILD_LLAMA "Build vendored llama.cpp" ON)
option(SYMON_BUILD_SD "Build vendored stable-diffusion.cpp" ON)
option(SYMON_CUDA "Enable CUDA backends" ON)

if(SYMON_BUILD_LLAMA AND EXISTS "${CMAKE_SOURCE_DIR}/engines/llama.cpp/CMakeLists.txt")
  add_custom_target(symon_llama_cuda
    COMMAND ${CMAKE_COMMAND} -S ${CMAKE_SOURCE_DIR}/engines/llama.cpp -B ${CMAKE_SOURCE_DIR}/engines/llama.cpp/build
      -DCMAKE_BUILD_TYPE=$<IF:$<CONFIG:Debug>,Debug,Release>
      -DGGML_CUDA=$<IF:$<BOOL:${SYMON_CUDA}>,ON,OFF>
      -DLLAMA_BUILD_SERVER=ON
      -DLLAMA_BUILD_TOOLS=ON
      -DLLAMA_BUILD_EXAMPLES=ON
      -DLLAMA_BUILD_TESTS=OFF
    COMMAND ${CMAKE_COMMAND} --build ${CMAKE_SOURCE_DIR}/engines/llama.cpp/build --config $<IF:$<CONFIG:Debug>,Debug,Release> -j
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Building llama.cpp CUDA engine"
  )
endif()

if(SYMON_BUILD_SD AND EXISTS "${CMAKE_SOURCE_DIR}/engines/stable-diffusion.cpp/CMakeLists.txt")
  add_custom_target(symon_stable_diffusion_cuda
    COMMAND ${CMAKE_COMMAND} -S ${CMAKE_SOURCE_DIR}/engines/stable-diffusion.cpp -B ${CMAKE_SOURCE_DIR}/engines/stable-diffusion.cpp/build
      -DCMAKE_BUILD_TYPE=$<IF:$<CONFIG:Debug>,Debug,Release>
      -DSD_CUDA=$<IF:$<BOOL:${SYMON_CUDA}>,ON,OFF>
      -DGGML_CUDA=$<IF:$<BOOL:${SYMON_CUDA}>,ON,OFF>
      -DSD_BUILD_SERVER=ON
      -DSD_BUILD_EXAMPLES=ON
      -DSD_BUILD_TESTS=OFF
    COMMAND ${CMAKE_COMMAND} --build ${CMAKE_SOURCE_DIR}/engines/stable-diffusion.cpp/build --config $<IF:$<CONFIG:Debug>,Debug,Release> -j
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Building stable-diffusion.cpp CUDA engine"
  )
endif()

add_custom_target(symon_all_cuda
  COMMAND ${CMAKE_SOURCE_DIR}/scripts/build_all_cuda.sh
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  COMMENT "Building all SyMoNeuRaL CUDA engines"
)
