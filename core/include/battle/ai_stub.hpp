#pragma once
#include "action.hpp"
#include "state.hpp"

namespace battle {

// Heuristic "max-damage" AI used both for the demo and as the LLM sidecar fallback.
// Selects the legal move with the highest expected damage against the opposing active.
// Deterministic: uses a fixed internal RNG seed, never touches state.rng.
Action choose_max_damage_action(const BattleState& state, Side side);

} // namespace battle
