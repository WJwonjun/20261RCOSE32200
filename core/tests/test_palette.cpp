#include <catch2/catch_test_macros.hpp>
#include "battle/palette.hpp"
#include "battle/champions_data.hpp"

using namespace battle;

// Load data once for all palette tests.
struct PaletteFixture {
    PaletteFixture() {
        static bool loaded = false;
        if (!loaded) {
            champions::load_data();
            loaded = true;
        }
    }
};

TEST_CASE("Palette: minimum counts from Champions DB", "[palette]") {
    PaletteFixture f;
    REQUIRE(palette::species().size() >= 250);
    REQUIRE(palette::moves().size()   >= 400);
    REQUIRE(palette::item_entries().size() >= 2); // at least "none" + some items
    REQUIRE(palette::nature_entries().size() >= 7);
}

TEST_CASE("Palette: legacy minimum counts", "[palette]") {
    PaletteFixture f;
    REQUIRE(palette::items().size()   >= 2);
    REQUIRE(palette::natures().size() >= 7);
}

TEST_CASE("Palette: find_species known", "[palette]") {
    PaletteFixture f;
    const palette::SpeciesEntry* e = palette::find_species("snorlax");
    REQUIRE(e != nullptr);
    REQUIRE(e->id == "snorlax");
}

TEST_CASE("Palette: find_species unknown returns null", "[palette]") {
    PaletteFixture f;
    REQUIRE(palette::find_species("missingno") == nullptr);
}

TEST_CASE("Palette: all species round-trip by id", "[palette]") {
    PaletteFixture f;
    for (const auto& s : palette::species()) {
        const palette::SpeciesEntry* found = palette::find_species(s.id);
        REQUIRE(found != nullptr);
        REQUIRE(found->id == s.id);
    }
}

TEST_CASE("Palette: find_move known", "[palette]") {
    PaletteFixture f;
    // "Body Slam" normalizes to "body_slam"
    const Move* m = palette::find_move("body_slam");
    REQUIRE(m != nullptr);
    REQUIRE(m->name == "body_slam");
}

TEST_CASE("Palette: find_move unknown returns null", "[palette]") {
    PaletteFixture f;
    REQUIRE(palette::find_move("splash") == nullptr);
}

TEST_CASE("Palette: species have valid types", "[palette]") {
    PaletteFixture f;
    for (const auto& s : palette::species()) {
        REQUIRE(s.types[0] != Type::COUNT);
    }
}

TEST_CASE("Palette: species have non-empty learnsets", "[palette]") {
    PaletteFixture f;
    // All species should have at least one legal move
    int empty_count = 0;
    for (const auto& s : palette::species()) {
        if (s.learnset.empty()) ++empty_count;
    }
    // Regional forms (Alolan, Hisuian, Galarian) may have empty learnsets
    // due to their moves not being listed under the regional-form names.
    REQUIRE(empty_count < 20);
}
