#pragma once
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

namespace battle::champions {

// Loads Champions regulation data from JSON files.
// Path resolved as:
//   1. override_root if provided
//   2. $POKEMON_CHAMPIONS_DB env var
//   3. Search upward from cwd for pokemon-champions-db/data/json/
// Throws std::runtime_error if data is missing or malformed.
// Safe to call multiple times — loads once, caches result.
void load_data(std::optional<std::filesystem::path> override_root = std::nullopt);

// Returns the data root path after load_data() has been called.
// Throws std::runtime_error if load_data() has not been called.
std::filesystem::path data_root();

// Normalizes a display name to a code ID:
// lowercase, whitespace and '-' replaced with '_'.
std::string normalize_id(std::string_view display_name);

} // namespace battle::champions
