cmake_minimum_required(VERSION 3.20)
project(pokemon_champions_sim CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

# Include subdirectories if they exist
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/core/CMakeLists.txt")
  add_subdirectory(core)
endif()
