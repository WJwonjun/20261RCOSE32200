#include "battle/ai_stub.hpp"
#include "battle/damage.hpp"
#include "battle/move.hpp"
#include "battle/state.hpp"
#include <algorithm>
#include <array>
#include <limits>

namespace battle {

std::array<int, 3> choose_selection(const Team& team) {
    std::array<int, 6> idx = {0, 1, 2, 3, 4, 5};
    auto total = [&](int i) {
        const Stats& s = team.party[i].stats;
        return s.hp + s.atk + s.def + s.spa + s.spd + s.spe;
    };
    // stable_sort: equal totals keep ascending party-index order (deterministic).
    std::stable_sort(idx.begin(), idx.end(),
                     [&](int a, int b) { return total(a) > total(b); });
    return {idx[0], idx[1], idx[2]};
}

// Picks the legal action with the highest expected damage against the opponent's active.
// For status moves, expected damage is 0. Switches are considered only if no
// damaging move is available (expected damage = 0 for all).
// Uses a fixed PCG64 seed so the evaluation is deterministic and does not
// consume any entropy from the battle RNG.
Action choose_max_damage_action(const BattleState& state, Side side) {
    const Team& my_team  = state.team(side);
    const Team& opp_team = state.opponent(side);

    const Pokemon& attacker = my_team.active();
    const Pokemon& defender = opp_team.active();

    std::vector<Action> legal = state.legal_actions(side);

    int    best_dmg    = -1;
    Action best_action = NoAction{};

    for (const Action& a : legal) {
        if (std::holds_alternative<MoveAction>(a)) {
            int idx = std::get<MoveAction>(a).move_idx;
            int mid = attacker.move_ids[idx];
            const Move* move = find_move(mid);
            if (!move) continue;

            // Use fixed-seed RNG for evaluation — does not affect battle state.
            PCG64 eval_rng(0xDEADBEEFCAFEBABEULL);
            // Simulate with neutral rolls: no crit, roll=100 (consume rng to match signature)
            int dmg = compute_damage(attacker, defender, *move, eval_rng);

            if (dmg > best_dmg) {
                best_dmg    = dmg;
                best_action = a;
            }
        }
    }

    // If no damaging move found (all status / no PP), prefer any move over switch
    if (best_dmg <= 0) {
        for (const Action& a : legal) {
            if (std::holds_alternative<MoveAction>(a)) {
                return a;
            }
        }
        // No moves at all — switch to first alive bench or NoAction
        for (const Action& a : legal) {
            if (std::holds_alternative<SwitchAction>(a)) return a;
        }
    }

    return best_action;
}

} // namespace battle
