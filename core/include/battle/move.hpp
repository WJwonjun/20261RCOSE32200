#pragma once
#include <cstdint>
#include <string>
#include <string_view>
#include "types.hpp"

namespace battle {

struct Move {
    int            id           = 0;
    std::string    name         = "";    // normalized ID: "thunderbolt"
    std::string    display_name = "";    // original: "Thunderbolt"
    Type           type         = Type::Normal;
    MoveCategory   category     = MoveCategory::Physical;
    int            power        = 0;   // 0 for status moves
    int            accuracy     = 100; // 0 = always hits
    int            pp_max       = 32;
    int            priority     = 0;
    StatusCondition status_effect = StatusCondition::None; // inflicted on target
};

// Lookup by integer move ID (used by damage/state code).
// Delegates to the palette (populated after load_data()).
const Move* find_move(int id);

} // namespace battle
