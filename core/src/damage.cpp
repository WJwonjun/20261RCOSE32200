#include "battle/state.hpp"
#include "battle/damage.hpp"
#include "battle/typechart.hpp"
#include "battle/pokemon.hpp"
#include "battle/move.hpp"

namespace battle {

// Gen 9 damage formula:
// damage = floor( floor( floor(2*level/5 + 2) * power * A/D / 50 + 2 )
//                 * type_mult * stab * crit * random )
// random in [0.85, 1.0] sampled as integer 85..100 / 100.
int compute_damage(const Pokemon& attacker, const Pokemon& defender,
                   const Move& move, PCG64& rng) noexcept {
    if (move.category == MoveCategory::Status || move.power == 0) return 0;

    int A, D;
    if (move.category == MoveCategory::Physical) {
        A = effective_atk(attacker);
        D = defender.stats.def;
    } else {
        A = attacker.stats.spa;
        D = defender.stats.spd;
    }

    int level = attacker.level;

    // Base damage
    int base = (2 * level / 5 + 2) * move.power * A / D / 50 + 2;

    // STAB (Same Type Attack Bonus): 1.5x if move type matches attacker type
    bool stab = (move.type == attacker.type1) ||
                (attacker.type2 != Type::COUNT && move.type == attacker.type2);
    // Use integer arithmetic: multiply by 3/2 if stab
    if (stab) base = base * 3 / 2;

    // Type effectiveness (x100 integer)
    int eff = effectiveness(move.type, defender.type1, defender.type2);
    base = base * eff / 100;

    if (base == 0) return 0; // immune

    // rng: crit roll (1/24 chance in Gen 9)
    bool crit = (rng.range(0, 23) == 0);
    if (crit) base = base * 3 / 2;

    // rng: damage roll (85-100 inclusive, uniform)
    int roll = rng.range(85, 100);
    base = base * roll / 100;

    return (base < 1) ? 1 : base;
}

} // namespace battle
