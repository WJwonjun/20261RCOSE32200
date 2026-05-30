#pragma once
#include "pokemon.hpp"
#include "move.hpp"
#include "rng.hpp"

namespace battle {

// Computes damage dealt by attacker to defender using the given move.
// Consumes 2 rng calls: crit roll, then damage roll.
// Returns 0 for status moves or immune matchups.
int compute_damage(const Pokemon& attacker, const Pokemon& defender,
                   const Move& move, PCG64& rng) noexcept;

} // namespace battle
