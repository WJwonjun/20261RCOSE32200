#pragma once
#include <array>
#include "action.hpp"
#include "state.hpp"
#include "team.hpp"

namespace battle {

// Heuristic "max-damage" AI used both for the demo and as the LLM sidecar fallback.
// Selects the legal move with the highest expected damage against the opposing active.
// Deterministic: uses a fixed internal RNG seed, never touches state.rng.
Action choose_max_damage_action(const BattleState& state, Side side);

// Team-preview (6 -> 3) heuristic: returns the party indices of the three
// strongest Pokemon by total computed stats, strongest first (so result[0] is
// the lead). Deterministic — ties break by ascending party index. This is the
// offline default; LLM-driven selection can replace it at the same seam later.
std::array<int, 3> choose_selection(const Team& team);

} // namespace battle
