#include <catch2/catch_test_macros.hpp>
#include "battle/state.hpp"
#include "battle/ai_stub.hpp"
#include "battle/pokemon.hpp"
#include "battle/move.hpp"
#include "battle/palette.hpp"
#include "battle/champions_data.hpp"

using namespace battle;

// Load Champions data once before determinism tests.
struct DeterminismFixture {
    DeterminismFixture() {
        static bool loaded = false;
        if (!loaded) {
            champions::load_data();
            loaded = true;
        }
    }
};

static int move_id(const char* name) {
    const Move* m = palette::find_move(name);
    if (!m) throw std::runtime_error(std::string("test: unknown move ") + name);
    return m->id;
}

static Pokemon make_test_pokemon(int id, const std::string& name,
                                  Type t1, Stats base,
                                  std::array<int,4> moves) {
    Pokemon p;
    p.species_id = id;
    p.name       = name;
    p.level      = 50;
    p.type1      = t1;
    p.type2      = Type::COUNT;
    p.base_stats = base;
    p.nature     = NATURE_HARDY;
    p.stats      = compute_stats(base, p.ivs, p.evs, p.nature, 50);
    p.current_hp = p.stats.hp;
    p.move_ids   = moves;
    for (int i = 0; i < 4; ++i) {
        const Move* m = find_move(moves[i]);
        p.pp[i] = m ? m->pp_max : 0;
    }
    return p;
}

static BattleState make_reference_state(uint64_t seed) {
    // Move IDs resolved from the loaded palette by name for stability.
    int thunderbolt = move_id("thunderbolt");
    int surf        = move_id("surf");
    int earthquake  = move_id("earthquake");
    int flamethrower= move_id("flamethrower");
    int shadow_ball = move_id("shadow_ball");
    int dragon_claw = move_id("dragon_claw");
    int crunch      = move_id("crunch");
    int toxic       = move_id("toxic");
    int will_o_wisp = move_id("will_o_wisp");
    int body_slam   = move_id("body_slam");

    BattleState s;
    s.rng = PCG64(seed);

    // Team A
    s.team_a.party[0] = make_test_pokemon(1, "TestA0", Type::Electric,
        {65, 65, 60, 90, 70, 90}, {thunderbolt, body_slam, surf, earthquake});
    s.team_a.party[1] = make_test_pokemon(2, "TestA1", Type::Water,
        {79, 83, 100, 85, 105, 78}, {surf, flamethrower, toxic, body_slam});
    s.team_a.party[2] = make_test_pokemon(3, "TestA2", Type::Fire,
        {78, 84, 78, 109, 85, 100}, {will_o_wisp, earthquake, body_slam, flamethrower});
    s.team_a.party[3] = make_test_pokemon(4, "TestA3", Type::Normal,
        {90, 130, 80, 65, 85, 55}, {earthquake, body_slam, crunch, body_slam});
    s.team_a.party[4] = make_test_pokemon(5, "TestA4", Type::Psychic,
        {55, 50, 45, 135, 95, 120}, {thunderbolt, flamethrower, will_o_wisp, body_slam});
    s.team_a.party[5] = make_test_pokemon(6, "TestA5", Type::Normal,
        {160, 110, 65, 65, 110, 30}, {body_slam, earthquake, toxic, crunch});
    s.team_a.active_slot = 0;

    // Team B: mirror
    s.team_b.party[0] = make_test_pokemon(7, "TestB0", Type::Ghost,
        {60, 65, 60, 130, 75, 110}, {thunderbolt, flamethrower, will_o_wisp, shadow_ball});
    s.team_b.party[1] = make_test_pokemon(8, "TestB1", Type::Dragon,
        {91, 134, 95, 100, 100, 80}, {earthquake, crunch, body_slam, flamethrower});
    s.team_b.party[2] = make_test_pokemon(9, "TestB2", Type::Water,
        {60, 75, 85, 100, 85, 115}, {surf, thunderbolt, flamethrower, body_slam});
    s.team_b.party[3] = make_test_pokemon(10, "TestB3", Type::Ground,
        {105, 130, 120, 45, 45, 40}, {earthquake, body_slam, crunch, body_slam});
    s.team_b.party[4] = make_test_pokemon(11, "TestB4", Type::Grass,
        {95, 95, 85, 125, 75, 55}, {surf, flamethrower, toxic, body_slam});
    s.team_b.party[5] = make_test_pokemon(12, "TestB5", Type::Fire,
        {90, 110, 80, 100, 80, 95}, {earthquake, crunch, will_o_wisp, body_slam});
    s.team_b.active_slot = 0;

    return s;
}

static std::vector<std::string> run_battle(uint64_t seed) {
    BattleState state = make_reference_state(seed);
    constexpr int MAX_TURNS = 200;
    while (!state.is_terminal() && state.turn_no < MAX_TURNS) {
        Action a = choose_max_damage_action(state, Side::A);
        Action b = choose_max_damage_action(state, Side::B);
        state.apply_action(a, b);
    }
    return state.log;
}

TEST_CASE("Determinism: same seed produces bit-identical log", "[determinism]") {
    DeterminismFixture f;
    constexpr uint64_t SEED = 0xDEAD'BEEF'1234'5678ULL;

    std::vector<std::string> first_log = run_battle(SEED);
    REQUIRE_FALSE(first_log.empty());

    for (int i = 0; i < 100; ++i) {
        std::vector<std::string> log = run_battle(SEED);
        REQUIRE(log.size() == first_log.size());
        for (size_t j = 0; j < log.size(); ++j) {
            REQUIRE(log[j] == first_log[j]);
        }
    }
}

TEST_CASE("Determinism: same seed produces same winner", "[determinism]") {
    DeterminismFixture f;
    constexpr uint64_t SEED = 0xCAFE'BABE'DEAD'BEEFULL;

    BattleState ref = make_reference_state(SEED);
    while (!ref.is_terminal() && ref.turn_no < 200) {
        Action a = choose_max_damage_action(ref, Side::A);
        Action b = choose_max_damage_action(ref, Side::B);
        ref.apply_action(a, b);
    }
    int ref_winner = ref.winner();

    for (int i = 0; i < 100; ++i) {
        BattleState s = make_reference_state(SEED);
        while (!s.is_terminal() && s.turn_no < 200) {
            Action a = choose_max_damage_action(s, Side::A);
            Action b = choose_max_damage_action(s, Side::B);
            s.apply_action(a, b);
        }
        REQUIRE(s.winner() == ref_winner);
    }
}
