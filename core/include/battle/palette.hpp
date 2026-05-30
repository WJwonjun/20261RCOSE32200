#pragma once
#include <array>
#include <optional>
#include <string>
#include <string_view>
#include <vector>
#include "types.hpp"
#include "move.hpp"

namespace battle::palette {

struct SpeciesEntry {
    std::string               id;           // normalized: "snorlax"
    std::string               display_name; // original: "Snorlax"
    // Legacy alias used in existing code (maps to display_name)
    std::string_view          name;         // points into display_name
    int                       dex          = 0;
    std::array<Type, 2>       types        = { Type::Normal, Type::COUNT };
    Stats                     base         = {};
    // Legacy alias (maps to base)
    Stats&                    base_stats   = base;
    std::vector<std::string>  learnset;    // normalized move IDs
    std::vector<std::string>  legal_abilities; // normalized ability IDs
};

// NatureEntry — richer representation loaded from natures.json
struct NatureEntry {
    std::string              id;           // normalized: "adamant"
    std::string              display_name; // "Adamant"
    std::optional<NatureStat> increased_stat; // std::nullopt for neutral
    std::optional<NatureStat> decreased_stat;
    Nature                   nature;       // the existing Nature struct
};

// ItemEntry — loaded from items.json
struct ItemEntry {
    std::string  id;              // normalized: "leftovers"
    std::string  display_name;   // "Leftovers"
    std::string  category;
    bool         has_runtime_effect = false; // true only for leftovers / life_orb
};

// The palette tables (populated by champions::load_data()).
// All returned references are stable after load_data().
const std::vector<SpeciesEntry>& species();
const std::vector<Move>&         moves();
const std::vector<std::string_view>& items();   // legacy: returns item IDs
const std::vector<std::string_view>& natures(); // legacy: returns nature IDs
const std::vector<NatureEntry>&  nature_entries();
const std::vector<ItemEntry>&    item_entries();

const SpeciesEntry* find_species(std::string_view id);
const Move*         find_move(std::string_view id);
const NatureEntry*  find_nature(std::string_view id);
const ItemEntry*    find_item(std::string_view id);

// Mutable access used by champions_data.cpp to populate the tables.
std::vector<SpeciesEntry>& mutable_species();
std::vector<Move>&         mutable_moves();
std::vector<NatureEntry>&  mutable_nature_entries();
std::vector<ItemEntry>&    mutable_item_entries();

} // namespace battle::palette
