#include "battle/palette.hpp"
#include <algorithm>

namespace battle::palette {

// ── Storage (populated by champions::load_data()) ─────────────────────────────
static std::vector<SpeciesEntry> SPECIES_TABLE;
static std::vector<Move>         MOVE_TABLE;
static std::vector<NatureEntry>  NATURE_TABLE;
static std::vector<ItemEntry>    ITEM_TABLE;

// Legacy string_view vectors rebuilt after each load.
static std::vector<std::string_view> ITEM_IDS;
static std::vector<std::string_view> NATURE_IDS;

// ── Public read accessors ─────────────────────────────────────────────────────

const std::vector<SpeciesEntry>& species()  { return SPECIES_TABLE; }
const std::vector<Move>&         moves()    { return MOVE_TABLE; }
const std::vector<NatureEntry>&  nature_entries() { return NATURE_TABLE; }
const std::vector<ItemEntry>&    item_entries()   { return ITEM_TABLE; }

const std::vector<std::string_view>& items() {
    // Rebuild lazily if stale (size mismatch).
    if (ITEM_IDS.size() != ITEM_TABLE.size()) {
        ITEM_IDS.clear();
        ITEM_IDS.reserve(ITEM_TABLE.size());
        for (const auto& e : ITEM_TABLE) ITEM_IDS.push_back(e.id);
    }
    return ITEM_IDS;
}

const std::vector<std::string_view>& natures() {
    if (NATURE_IDS.size() != NATURE_TABLE.size()) {
        NATURE_IDS.clear();
        NATURE_IDS.reserve(NATURE_TABLE.size());
        for (const auto& e : NATURE_TABLE) NATURE_IDS.push_back(e.id);
    }
    return NATURE_IDS;
}

// ── Mutable write accessors (used by champions_data.cpp) ─────────────────────

std::vector<SpeciesEntry>& mutable_species()        { return SPECIES_TABLE; }
std::vector<Move>&         mutable_moves()          { return MOVE_TABLE; }
std::vector<NatureEntry>&  mutable_nature_entries() { return NATURE_TABLE; }
std::vector<ItemEntry>&    mutable_item_entries()   { return ITEM_TABLE; }

// ── Lookup functions ──────────────────────────────────────────────────────────

const SpeciesEntry* find_species(std::string_view id) {
    for (const auto& e : SPECIES_TABLE) {
        if (e.id == id) return &e;
    }
    return nullptr;
}

const Move* find_move(std::string_view id) {
    for (const auto& m : MOVE_TABLE) {
        if (m.name == id) return &m;
    }
    return nullptr;
}

const NatureEntry* find_nature(std::string_view id) {
    for (const auto& n : NATURE_TABLE) {
        if (n.id == id) return &n;
    }
    return nullptr;
}

const ItemEntry* find_item(std::string_view id) {
    for (const auto& i : ITEM_TABLE) {
        if (i.id == id) return &i;
    }
    return nullptr;
}

// ── battle::find_move(int) — used by damage/state/test code ──────────────────
// Defined here so it can access MOVE_TABLE directly.
// Declaration is in move.hpp.
namespace _find_move_impl {
    const Move* by_id(int id) {
        for (const auto& m : MOVE_TABLE) {
            if (m.id == id) return &m;
        }
        return nullptr;
    }
} // namespace _find_move_impl

} // namespace battle::palette

namespace battle {

const Move* find_move(int id) {
    return palette::_find_move_impl::by_id(id);
}

} // namespace battle
