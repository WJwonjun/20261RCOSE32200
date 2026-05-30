#include <catch2/catch_test_macros.hpp>
#include <fstream>
#include <cstdlib>
#include "battle/team_loader.hpp"
#include "battle/champions_data.hpp"

using namespace battle;

// Load Champions data once before any team-loader tests.
struct TeamLoaderFixture {
    TeamLoaderFixture() {
        static bool loaded = false;
        if (!loaded) {
            champions::load_data();
            loaded = true;
        }
    }
};

static void write_file(const std::string& path, const std::string& content) {
    std::ofstream f(path);
    REQUIRE(f.is_open());
    f << content;
}

// All moves here are confirmed in each species' Champions learnset.
static const std::string VALID_TEAM_JSON = R"({
  "name": "TestTeam",
  "members": [
    {"species":"snorlax","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":252},"nature":"adamant","moves":["body_slam","earthquake","crunch","rest"],"item":"leftovers"},
    {"species":"charizard","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":0,"atk":0,"def":4,"spa":252,"spd":0,"spe":252},"nature":"timid","moves":["flamethrower","air_slash","dragon_claw","earthquake"],"item":"life_orb"},
    {"species":"garchomp","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":252},"nature":"jolly","moves":["dragon_claw","earthquake","crunch","iron_head"],"item":"none"},
    {"species":"gengar","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":0,"def":0,"spa":252,"spd":0,"spe":252},"nature":"timid","moves":["shadow_ball","sludge_bomb","dark_pulse","thunderbolt"],"item":"none"},
    {"species":"dragonite","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":252},"nature":"adamant","moves":["dragon_claw","earthquake","flamethrower","thunderbolt"],"item":"none"},
    {"species":"scizor","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":252},"nature":"adamant","moves":["bullet_punch","iron_head","x_scissor","brick_break"],"item":"none"}
  ]
})";

TEST_CASE("TeamLoader: valid team loads correctly", "[team_loader]") {
    TeamLoaderFixture f;
    const std::string path = "/tmp/test_valid_team.json";
    write_file(path, VALID_TEAM_JSON);

    Team t = load_team_json(path);
    REQUIRE(t.party.size() == 6);
    // First member should be snorlax
    REQUIRE(t.party[0].name == "Snorlax");
    REQUIRE(t.party[0].level == 50);
    REQUIRE(t.party[0].current_hp > 0);
    // Move IDs should be non-zero
    for (int i = 0; i < 4; ++i) {
        REQUIRE(t.party[0].move_ids[i] != 0);
    }
}

TEST_CASE("TeamLoader: invalid JSON throws", "[team_loader]") {
    TeamLoaderFixture f;
    const std::string path = "/tmp/test_invalid_json.json";
    write_file(path, "{ this is not valid JSON !!!");

    REQUIRE_THROWS_AS(load_team_json(path), std::runtime_error);
}

TEST_CASE("TeamLoader: wrong member count throws with '6 members' message", "[team_loader]") {
    TeamLoaderFixture f;
    const std::string path = "/tmp/test_5members.json";
    write_file(path, R"({
  "name": "Short",
  "members": [
    {"species":"snorlax","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":0},"nature":"adamant","moves":["body_slam","earthquake","crunch","rest"],"item":"none"},
    {"species":"charizard","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":0,"def":0,"spa":252,"spd":0,"spe":0},"nature":"timid","moves":["flamethrower","air_slash","dragon_claw","earthquake"],"item":"none"},
    {"species":"garchomp","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":0},"nature":"jolly","moves":["dragon_claw","earthquake","crunch","iron_head"],"item":"none"},
    {"species":"gengar","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":0,"def":0,"spa":252,"spd":0,"spe":0},"nature":"timid","moves":["shadow_ball","sludge_bomb","dark_pulse","thunderbolt"],"item":"none"},
    {"species":"dragonite","level":50,"ivs":{"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},"evs":{"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":0},"nature":"adamant","moves":["dragon_claw","earthquake","flamethrower","thunderbolt"],"item":"none"}
  ]
})");

    try {
        load_team_json(path);
        FAIL("should have thrown");
    } catch (const std::runtime_error& e) {
        std::string msg = e.what();
        REQUIRE(msg.find("6") != std::string::npos);
    }
}

TEST_CASE("TeamLoader: unknown species throws with species name in message", "[team_loader]") {
    TeamLoaderFixture f;
    const std::string path = "/tmp/test_bad_species.json";
    std::string json = VALID_TEAM_JSON;
    auto pos = json.find("\"snorlax\"");
    REQUIRE(pos != std::string::npos);
    json.replace(pos, 9, "\"missingno\"");
    write_file(path, json);

    try {
        load_team_json(path);
        FAIL("should have thrown");
    } catch (const std::runtime_error& e) {
        std::string msg = e.what();
        REQUIRE(msg.find("missingno") != std::string::npos);
    }
}

TEST_CASE("TeamLoader: unknown move throws", "[team_loader]") {
    TeamLoaderFixture f;
    const std::string path = "/tmp/test_bad_move.json";
    std::string json = VALID_TEAM_JSON;
    // Replace "body_slam" with a move that doesn't exist in the DB at all
    auto pos = json.find("\"body_slam\"");
    REQUIRE(pos != std::string::npos);
    json.replace(pos, 11, "\"totally_fake_move_xyz\"");
    write_file(path, json);

    REQUIRE_THROWS_AS(load_team_json(path), std::runtime_error);
}

TEST_CASE("TeamLoader: rejects move not in learnset", "[team_loader]") {
    TeamLoaderFixture f;
    // "Accelerock" is a valid Champions move but Charizard cannot learn it.
    const std::string path = "/tmp/test_learnset_violation.json";
    std::string json = VALID_TEAM_JSON;
    // Replace "flamethrower" in charizard's slot with "accelerock"
    auto pos = json.find("\"flamethrower\"");
    REQUIRE(pos != std::string::npos);
    json.replace(pos, 14, "\"accelerock\"");
    write_file(path, json);

    try {
        load_team_json(path);
        FAIL("should have thrown for learnset violation");
    } catch (const std::runtime_error& e) {
        std::string msg = e.what();
        REQUIRE(msg.find("accelerock") != std::string::npos);
        REQUIRE(msg.find("learnset") != std::string::npos);
    }
}

TEST_CASE("TeamLoader: EV total over 508 throws", "[team_loader]") {
    TeamLoaderFixture f;
    const std::string path = "/tmp/test_ev_overflow.json";
    std::string json = VALID_TEAM_JSON;
    // First member has evs hp:4,atk:252,spe:252 = 508 (valid). Push it over by changing hp to 5.
    auto pos = json.find("\"evs\":{\"hp\":4");
    REQUIRE(pos != std::string::npos);
    json.replace(pos, 13, "\"evs\":{\"hp\":5");
    write_file(path, json);

    REQUIRE_THROWS_AS(load_team_json(path), std::runtime_error);
}

TEST_CASE("TeamLoader: file not found throws", "[team_loader]") {
    TeamLoaderFixture f;
    REQUIRE_THROWS_AS(load_team_json("/tmp/definitely_does_not_exist_12345.json"), std::runtime_error);
}
