#include <catch2/catch_test_macros.hpp>
#include "battle/damage.hpp"
#include "battle/pokemon.hpp"
#include "battle/move.hpp"
#include "battle/palette.hpp"
#include "battle/champions_data.hpp"
#include "battle/rng.hpp"

using namespace battle;

struct DamageFixture {
    DamageFixture() {
        static bool loaded = false;
        if (!loaded) {
            champions::load_data();
            loaded = true;
        }
    }
};

static Pokemon make_attacker(int atk, int spa, int level = 50) {
    Pokemon p;
    p.name       = "Attacker";
    p.level      = level;
    p.type1      = Type::Normal;
    p.type2      = Type::COUNT;
    p.stats.atk  = atk;
    p.stats.spa  = spa;
    p.stats.spe  = 100;
    p.stats.hp   = 200;
    p.current_hp = 200;
    p.status     = StatusCondition::None;
    return p;
}

static Pokemon make_defender(int def, int spd) {
    Pokemon p;
    p.name       = "Defender";
    p.level      = 50;
    p.type1      = Type::Normal;
    p.type2      = Type::COUNT;
    p.stats.def  = def;
    p.stats.spd  = spd;
    p.stats.hp   = 300;
    p.current_hp = 300;
    p.status     = StatusCondition::None;
    return p;
}

TEST_CASE("Damage: Body Slam neutral, known stats", "[damage]") {
    DamageFixture f;
    // Body Slam: Normal, Physical, power=85
    const Move* body_slam = palette::find_move("body_slam");
    REQUIRE(body_slam != nullptr);
    REQUIRE(body_slam->power == 85);
    REQUIRE(body_slam->category == MoveCategory::Physical);

    Pokemon atk = make_attacker(100, 100);
    Pokemon def = make_defender(100, 100);

    // Manual formula at level 50, Atk=100, Def=100, power=85:
    // base = (2*50/5 + 2) * 85 * 100 / 100 / 50 + 2
    //      = 22 * 85 / 50 + 2 = 1870/50 + 2 = 37 + 2 = 39
    // STAB: Normal attacker, Normal move → STAB: 39 * 3/2 = 58
    // Type eff: Normal vs Normal = 1x
    // Roll range (no crit): 58 * 85/100 .. 58 = 49..58
    // Crit range: 58 * 3/2 = 87 → 73..87

    int min_dmg = 9999, max_dmg = 0;
    for (int i = 0; i < 1000; ++i) {
        PCG64 rng(uint64_t(i) * 6364136223846793005ULL + 1442695040888963407ULL);
        int d = compute_damage(atk, def, *body_slam, rng);
        if (d < min_dmg) min_dmg = d;
        if (d > max_dmg) max_dmg = d;
    }
    REQUIRE(min_dmg >= 49);
    REQUIRE(max_dmg <= 87);
    REQUIRE(min_dmg <= 52); // should see near-minimum values
}

TEST_CASE("Damage: Status move returns 0", "[damage]") {
    DamageFixture f;
    const Move* toxic = palette::find_move("toxic");
    REQUIRE(toxic != nullptr);
    REQUIRE(toxic->category == MoveCategory::Status);

    Pokemon atk = make_attacker(100, 100);
    Pokemon def = make_defender(100, 100);
    PCG64 rng(42ULL);

    int d = compute_damage(atk, def, *toxic, rng);
    REQUIRE(d == 0);
}

TEST_CASE("Damage: Immune type returns 0", "[damage]") {
    DamageFixture f;
    // Earthquake (Ground, Physical) vs Flying type: immune
    const Move* eq = palette::find_move("earthquake");
    REQUIRE(eq != nullptr);
    REQUIRE(eq->type == Type::Ground);

    Pokemon atk = make_attacker(120, 80);
    atk.type1 = Type::Ground;

    Pokemon def = make_defender(80, 80);
    def.type1 = Type::Flying; // immune to Ground

    PCG64 rng(99ULL);
    int d = compute_damage(atk, def, *eq, rng);
    REQUIRE(d == 0);
}

TEST_CASE("Damage: STAB bonus applied", "[damage]") {
    DamageFixture f;
    // Thunderbolt: Electric special, power=90
    const Move* tbolt = palette::find_move("thunderbolt");
    REQUIRE(tbolt != nullptr);

    // Electric attacker vs neutral defender
    Pokemon atk_stab = make_attacker(80, 100);
    atk_stab.type1   = Type::Electric;

    Pokemon atk_nostab = make_attacker(80, 100);
    atk_nostab.type1   = Type::Normal;

    Pokemon def = make_defender(80, 100);
    def.type1 = Type::Normal;

    // Use same seed for both — same crit/roll
    PCG64 rng_a(77777ULL);
    PCG64 rng_b(77777ULL);
    int d_stab   = compute_damage(atk_stab,   def, *tbolt, rng_a);
    int d_nostab = compute_damage(atk_nostab, def, *tbolt, rng_b);

    REQUIRE(d_stab > d_nostab);
}

TEST_CASE("Damage: Super-effective is stronger than neutral", "[damage]") {
    DamageFixture f;
    // Surf (Water) vs Fire: 2x effective
    const Move* surf = palette::find_move("surf");
    REQUIRE(surf != nullptr);

    Pokemon atk = make_attacker(80, 100);
    atk.type1 = Type::Water;

    Pokemon def_fire = make_defender(80, 100);
    def_fire.type1 = Type::Fire;

    Pokemon def_normal = make_defender(80, 100);
    def_normal.type1 = Type::Normal;

    PCG64 rng_a(12345ULL);
    PCG64 rng_b(12345ULL);
    int d_super   = compute_damage(atk, def_fire,   *surf, rng_a);
    int d_neutral = compute_damage(atk, def_normal, *surf, rng_b);

    REQUIRE(d_super > d_neutral);
}
