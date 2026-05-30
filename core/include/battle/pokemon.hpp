#pragma once
#include <array>
#include <cstdint>
#include <string>
#include "types.hpp"
#include "move.hpp"

namespace battle {

struct Pokemon {
    int              species_id  = 0;
    std::string      name        = "Unknown";
    int              level       = 50;
    Type             type1       = Type::Normal;
    Type             type2       = Type::COUNT; // COUNT = no second type

    Stats            base_stats  = {};
    IVs              ivs         = {};
    EVs              evs         = {};
    Nature           nature      = NATURE_HARDY;

    Stats            stats       = {}; // computed final stats
    int              current_hp  = 0;

    std::array<int, 4> move_ids  = {0, 0, 0, 0};
    std::array<int, 4> pp        = {0, 0, 0, 0};

    int              item_id     = 0;

    StatusCondition  status      = StatusCondition::None;
    int              status_turns = 0; // turns remaining (Sleep), turns elapsed (Poison/Burn)

    bool is_fainted() const noexcept { return current_hp <= 0; }
};

// Gen 9 stat formula.
// HP:  floor((2*base + iv + floor(ev/4)) * level / 100) + level + 10
// Other: floor((floor((2*base + iv + floor(ev/4)) * level / 100) + 5) * nature_mult)
inline double nature_multiplier(Nature n, NatureStat stat) noexcept {
    if (n.boosted == n.nerfed) return 1.0; // neutral
    if (n.boosted == stat) return 1.1;
    if (n.nerfed  == stat) return 0.9;
    return 1.0;
}

inline Stats compute_stats(const Stats& base, const IVs& iv, const EVs& ev,
                            const Nature& nature, int level) noexcept {
    Stats s;
    auto calc_other = [&](int b, int i, int e, NatureStat ns) -> int {
        int inner = (2 * b + i + e / 4) * level / 100 + 5;
        return (int)(inner * nature_multiplier(nature, ns));
    };

    s.hp  = (2 * base.hp  + iv.hp  + ev.hp  / 4) * level / 100 + level + 10;
    s.atk = calc_other(base.atk, iv.atk, ev.atk, NatureStat::Atk);
    s.def = calc_other(base.def, iv.def, ev.def, NatureStat::Def);
    s.spa = calc_other(base.spa, iv.spa, ev.spa, NatureStat::SpA);
    s.spd = calc_other(base.spd, iv.spd, ev.spd, NatureStat::SpD);
    s.spe = calc_other(base.spe, iv.spe, ev.spe, NatureStat::Spe);
    return s;
}

// Applies paralysis Spe halving for in-battle effective speed.
inline int effective_spe(const Pokemon& p) noexcept {
    int spe = p.stats.spe;
    if (p.status == StatusCondition::Paralysis) spe /= 2;
    return spe;
}

// Effective Attack (physical) — Burn halves Atk.
inline int effective_atk(const Pokemon& p) noexcept {
    int atk = p.stats.atk;
    if (p.status == StatusCondition::Burn) atk /= 2;
    return atk;
}

} // namespace battle
