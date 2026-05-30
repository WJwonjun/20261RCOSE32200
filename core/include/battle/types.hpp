#pragma once
#include <cstdint>

namespace battle {

enum class Type : uint8_t {
    Normal = 0, Fire, Water, Electric, Grass, Ice,
    Fighting, Poison, Ground, Flying, Psychic, Bug,
    Rock, Ghost, Dragon, Dark, Steel, Fairy,
    COUNT
};

enum class StatusCondition : uint8_t {
    None = 0,
    Burn,      // BRN: -1/8 max hp per turn, Atk halved for physical
    Poison,    // PSN: -1/8 max hp per turn
    Paralysis, // PAR: 25% chance to skip turn, Spe halved
    Freeze,    // FRZ: cannot move, 20% thaw chance per turn
    Sleep,     // SLP: cannot move for 1-3 turns
};

enum class MoveCategory : uint8_t {
    Physical = 0,
    Special,
    Status,
};

struct Stats {
    int hp  = 0;
    int atk = 0;
    int def = 0;
    int spa = 0;
    int spd = 0;
    int spe = 0;
};

struct IVs {
    int hp  = 31;
    int atk = 31;
    int def = 31;
    int spa = 31;
    int spd = 31;
    int spe = 31;
};

struct EVs {
    int hp  = 0;
    int atk = 0;
    int def = 0;
    int spa = 0;
    int spd = 0;
    int spe = 0;
};

// Nature: (boosted_stat, nerfed_stat). Neutral = (None, None).
// Multiplier: 1.1 for boosted, 0.9 for nerfed, 1.0 for neutral.
enum class NatureStat : uint8_t {
    None = 0, Atk, Def, SpA, SpD, Spe
};

struct Nature {
    NatureStat boosted = NatureStat::None;
    NatureStat nerfed  = NatureStat::None;
};

// Common natures as constants
inline constexpr Nature NATURE_HARDY   { NatureStat::None, NatureStat::None };
inline constexpr Nature NATURE_ADAMANT { NatureStat::Atk,  NatureStat::SpA  };
inline constexpr Nature NATURE_MODEST  { NatureStat::SpA,  NatureStat::Atk  };
inline constexpr Nature NATURE_JOLLY   { NatureStat::Spe,  NatureStat::SpA  };
inline constexpr Nature NATURE_TIMID   { NatureStat::Spe,  NatureStat::Atk  };
inline constexpr Nature NATURE_BOLD    { NatureStat::Def,  NatureStat::Atk  };
inline constexpr Nature NATURE_CALM    { NatureStat::SpD,  NatureStat::Atk  };

} // namespace battle
