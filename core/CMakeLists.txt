cmake_minimum_required(VERSION 3.20)
project(battle_core CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

# ── nlohmann/json (header-only) ───────────────────────────────────────────────
FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.11.3
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(nlohmann_json)

# ── Catch2 (tests) ────────────────────────────────────────────────────────────
FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG        v3.5.3
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(Catch2)

# ── battle_core static library ────────────────────────────────────────────────
add_library(battle_core STATIC
    src/state.cpp
    src/damage.cpp
    src/ai_stub.cpp
    src/ipc.cpp
    src/serialize.cpp
    src/palette.cpp
    src/champions_data.cpp
    src/team_loader.cpp
)

target_include_directories(battle_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(battle_core PUBLIC
    nlohmann_json::nlohmann_json
)

target_compile_options(battle_core PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic>
)

# ── battle_demo executable ────────────────────────────────────────────────────
add_executable(battle_demo
    src/main_demo.cpp
)

target_link_libraries(battle_demo PRIVATE battle_core)

# ── tests ─────────────────────────────────────────────────────────────────────
enable_testing()

add_executable(test_determinism
    tests/test_determinism.cpp
)
target_link_libraries(test_determinism PRIVATE battle_core Catch2::Catch2WithMain)

add_executable(test_damage
    tests/test_damage.cpp
)
target_link_libraries(test_damage PRIVATE battle_core Catch2::Catch2WithMain)

add_executable(test_ipc
    tests/test_ipc.cpp
)
target_link_libraries(test_ipc PRIVATE battle_core Catch2::Catch2WithMain)

add_executable(test_palette
    tests/test_palette.cpp
)
target_link_libraries(test_palette PRIVATE battle_core Catch2::Catch2WithMain)

add_executable(test_team_loader
    tests/test_team_loader.cpp
)
target_link_libraries(test_team_loader PRIVATE battle_core Catch2::Catch2WithMain)

include(CTest)
include(Catch)
catch_discover_tests(test_determinism)
catch_discover_tests(test_damage)
catch_discover_tests(test_ipc)
catch_discover_tests(test_palette)
catch_discover_tests(test_team_loader)
