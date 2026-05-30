#pragma once
#include <stdexcept>
#include <string>
#include "team.hpp"

namespace battle {

// Loads a team from a JSON file matching the GA genome schema.
// Throws std::runtime_error on file errors, invalid JSON, schema violations,
// unknown species/move IDs, wrong member count, or IV/EV constraint failures.
//
// Move–species restriction: any palette move is legal for any species (MVP
// relaxation — GA mutation space would be too narrow with real movepools, and
// the sim treats moves independently of species biology).
Team load_team_json(const std::string& path);

} // namespace battle
