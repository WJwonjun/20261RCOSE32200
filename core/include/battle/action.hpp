#pragma once
#include <variant>
#include <cstdint>

namespace battle {

struct MoveAction {
    int move_idx; // 0-3, index into pokemon.move_ids[]
};

// `to` is idx_in_selection (0..2): an index into team.selection[], NOT a
// raw party slot.  The actual party slot is team.party[team.selection[to]].
struct SwitchAction {
    int to; // 0-2, idx_in_selection of the target bench slot
};

// Sentinel for "no action available" (all fainted, etc.)
struct NoAction {};

using Action = std::variant<MoveAction, SwitchAction, NoAction>;

} // namespace battle
