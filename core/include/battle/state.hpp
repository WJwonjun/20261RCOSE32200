#pragma once
#include <vector>
#include <string>
#include "team.hpp"
#include "action.hpp"
#include "rng.hpp"

namespace battle {

enum class Side : int { A = 0, B = 1 };

struct BattleState {
    Team   team_a;
    Team   team_b;
    int    turn_no = 0;
    PCG64  rng;
    std::vector<std::string> log;

    // Returns list of legal actions for the given side.
    // Always non-empty while is_terminal() is false.
    std::vector<Action> legal_actions(Side side) const;

    // Advances state by one full turn (both actions resolved).
    // Returns false if terminal before resolution.
    bool apply_action(Action action_a, Action action_b);

    bool is_terminal() const noexcept;

    // Returns 0 for Side A win, 1 for Side B win, -1 if ongoing.
    int winner() const noexcept;

    Team&       team(Side s)       noexcept { return s == Side::A ? team_a : team_b; }
    const Team& team(Side s) const noexcept { return s == Side::A ? team_a : team_b; }

    Team&       opponent(Side s)       noexcept { return s == Side::A ? team_b : team_a; }
    const Team& opponent(Side s) const noexcept { return s == Side::A ? team_b : team_a; }
};

} // namespace battle
