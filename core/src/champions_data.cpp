#include "battle/champions_data.hpp"
#include "battle/palette.hpp"
#include "battle/types.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <nlohmann/json.hpp>

namespace fs = std::filesystem;

namespace battle::champions {

// ── helpers ────────────────────────────────────────────────────────────────────

std::string normalize_id(std::string_view sv) {
    std::string out;
    out.reserve(sv.size());
    for (char c : sv) {
        if (c == ' ' || c == '-') {
            out += '_';
        } else {
            out += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        }
    }
    return out;
}

static Type parse_type(std::string_view s) {
    if (s == "Normal")   return Type::Normal;
    if (s == "Fire")     return Type::Fire;
    if (s == "Water")    return Type::Water;
    if (s == "Electric") return Type::Electric;
    if (s == "Grass")    return Type::Grass;
    if (s == "Ice")      return Type::Ice;
    if (s == "Fighting") return Type::Fighting;
    if (s == "Poison")   return Type::Poison;
    if (s == "Ground")   return Type::Ground;
    if (s == "Flying")   return Type::Flying;
    if (s == "Psychic")  return Type::Psychic;
    if (s == "Bug")      return Type::Bug;
    if (s == "Rock")     return Type::Rock;
    if (s == "Ghost")    return Type::Ghost;
    if (s == "Dragon")   return Type::Dragon;
    if (s == "Dark")     return Type::Dark;
    if (s == "Steel")    return Type::Steel;
    if (s == "Fairy")    return Type::Fairy;
    throw std::runtime_error("champions_data: unknown type \"" + std::string(s) + "\"");
}

static MoveCategory parse_category(std::string_view s) {
    if (s == "Physical") return MoveCategory::Physical;
    if (s == "Special")  return MoveCategory::Special;
    if (s == "Status")   return MoveCategory::Status;
    throw std::runtime_error("champions_data: unknown category \"" + std::string(s) + "\"");
}

static std::optional<NatureStat> parse_nature_stat(const nlohmann::json& j) {
    if (j.is_null()) return std::nullopt;
    std::string s = j.get<std::string>();
    if (s == "attack")      return NatureStat::Atk;
    if (s == "defense")     return NatureStat::Def;
    if (s == "sp_attack")   return NatureStat::SpA;
    if (s == "sp_defense")  return NatureStat::SpD;
    if (s == "speed")       return NatureStat::Spe;
    throw std::runtime_error("champions_data: unknown nature stat \"" + s + "\"");
}

static nlohmann::json load_json(const fs::path& p) {
    std::ifstream f(p);
    if (!f.is_open())
        throw std::runtime_error("champions_data: cannot open " + p.string());
    nlohmann::json j;
    try {
        f >> j;
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error("champions_data: malformed JSON in " + p.string() + ": " + e.what());
    }
    return j;
}

// ── path resolution ────────────────────────────────────────────────────────────

static fs::path resolve_data_root(std::optional<fs::path> override_root) {
    if (override_root.has_value()) {
        if (!fs::exists(*override_root))
            throw std::runtime_error("champions_data: override path does not exist: " + override_root->string());
        return *override_root;
    }

    // 1. $POKEMON_CHAMPIONS_DB
    const char* env = std::getenv("POKEMON_CHAMPIONS_DB");
    if (env && *env) {
        fs::path p(env);
        if (!fs::exists(p))
            throw std::runtime_error("champions_data: $POKEMON_CHAMPIONS_DB path does not exist: " + p.string());
        return p;
    }

    // 2. Search upward from cwd for pokemon-champions-db/data/json/
    fs::path cur = fs::current_path();
    for (int depth = 0; depth < 8; ++depth) {
        fs::path candidate = cur / "pokemon-champions-db" / "data" / "json";
        if (fs::exists(candidate)) return candidate;
        fs::path parent = cur.parent_path();
        if (parent == cur) break; // reached root
        cur = parent;
    }

    throw std::runtime_error(
        "champions_data: cannot locate pokemon-champions-db/data/json/. "
        "Set $POKEMON_CHAMPIONS_DB or run from within the repo.");
}

// ── loader ─────────────────────────────────────────────────────────────────────

static fs::path g_data_root;
static std::once_flag g_load_flag;
static bool g_loaded = false;

static void do_load(std::optional<fs::path> override_root) {
    fs::path root = resolve_data_root(override_root);
    g_data_root = root;

    // ── pokemon.json ──────────────────────────────────────────────────────────
    auto jpokemon = load_json(root / "pokemon.json");
    if (!jpokemon.is_array())
        throw std::runtime_error("champions_data: pokemon.json must be a JSON array");

    // Build learnset map from learnsets.json first (need it for SpeciesEntry)
    auto jlearnsets = load_json(root / "learnsets.json");
    if (!jlearnsets.is_object())
        throw std::runtime_error("champions_data: learnsets.json must be a JSON object");

    // ── moves.json ────────────────────────────────────────────────────────────
    auto jmoves = load_json(root / "moves.json");
    if (!jmoves.is_array())
        throw std::runtime_error("champions_data: moves.json must be a JSON array");

    std::vector<Move>& move_table = palette::mutable_moves();
    move_table.clear();
    // Map from normalized move ID → move index for learnset population
    std::unordered_map<std::string, int> move_id_to_index;

    int move_id = 1;
    for (const auto& jm : jmoves) {
        // Filter: must have category in {Physical, Special, Status} and champions_legal == true
        if (!jm.value("champions_legal", false)) continue;
        auto cat_val = jm["category"];
        if (cat_val.is_null()) continue;
        std::string cat_str = cat_val.get<std::string>();
        if (cat_str != "Physical" && cat_str != "Special" && cat_str != "Status") continue;

        // Skip moves with null type (e.g. "Forest's Curse" has no type_en in DB)
        if (jm["type_en"].is_null()) continue;

        std::string disp = jm.at("name_en").get<std::string>();
        std::string id   = normalize_id(disp);

        Move m;
        m.id           = move_id++;
        m.name         = id;
        m.display_name = disp;
        m.type         = parse_type(jm.at("type_en").get<std::string>());
        m.category     = parse_category(cat_str);
        m.power        = jm["power"].is_null() ? 0 : jm["power"].get<int>();
        // accuracy: null means always hits (0)
        m.accuracy     = jm["accuracy"].is_null() ? 0 : jm["accuracy"].get<int>();
        m.pp_max       = jm["pp"].is_null() ? 10 : jm["pp"].get<int>();
        m.priority     = jm["priority"].is_null() ? 0 : jm["priority"].get<int>();
        m.status_effect = StatusCondition::None; // derived from effect is complex; keep None

        move_id_to_index[id] = static_cast<int>(move_table.size());
        move_table.push_back(std::move(m));
    }

    // ── natures.json ──────────────────────────────────────────────────────────
    auto jnatures = load_json(root / "natures.json");
    if (!jnatures.is_array())
        throw std::runtime_error("champions_data: natures.json must be a JSON array");

    std::vector<palette::NatureEntry>& nature_table = palette::mutable_nature_entries();
    nature_table.clear();

    for (const auto& jn : jnatures) {
        if (!jn.value("champions_legal", false)) continue;

        palette::NatureEntry ne;
        ne.display_name    = jn.at("name_en").get<std::string>();
        ne.id              = normalize_id(ne.display_name);
        ne.increased_stat  = parse_nature_stat(jn["increased"]);
        ne.decreased_stat  = parse_nature_stat(jn["decreased"]);

        // Build the Nature struct
        ne.nature.boosted = ne.increased_stat.value_or(NatureStat::None);
        ne.nature.nerfed  = ne.decreased_stat.value_or(NatureStat::None);

        nature_table.push_back(std::move(ne));
    }

    // ── items.json ────────────────────────────────────────────────────────────
    auto jitems = load_json(root / "items.json");
    if (!jitems.is_array())
        throw std::runtime_error("champions_data: items.json must be a JSON array");

    std::vector<palette::ItemEntry>& item_table = palette::mutable_item_entries();
    item_table.clear();

    // Insert sentinel "none" first (item_id = 0 means no item)
    {
        palette::ItemEntry none_item;
        none_item.id = "none";
        none_item.display_name = "None";
        none_item.category = "None";
        none_item.has_runtime_effect = false;
        item_table.push_back(std::move(none_item));
    }

    for (const auto& ji : jitems) {
        if (!ji.value("champions_legal", false)) continue;

        palette::ItemEntry ie;
        ie.display_name = ji.at("name_en").get<std::string>();
        ie.id = normalize_id(ie.display_name);
        ie.category = ji.value("category", "");
        ie.has_runtime_effect = (ie.id == "leftovers" || ie.id == "life_orb");

        item_table.push_back(std::move(ie));
    }

    // ── species (pokemon.json) ────────────────────────────────────────────────
    std::vector<palette::SpeciesEntry>& species_table = palette::mutable_species();
    species_table.clear();

    // Build normalized move-id set from learnsets for O(1) lookup
    // learnsets.json: { "Snorlax": ["move1", ...], ... }
    // filter out "-Champions Attackdex" junk entry; normalize move names
    std::unordered_map<std::string, std::vector<std::string>> learnset_map;
    for (auto& [key, val] : jlearnsets.items()) {
        if (key == "-Champions Attackdex") continue;
        std::string species_key = key; // e.g. "Snorlax"
        std::vector<std::string> normalized_moves;
        for (const auto& mv : val) {
            std::string mv_str = mv.get<std::string>();
            if (mv_str == "-Champions Attackdex") continue;
            normalized_moves.push_back(normalize_id(mv_str));
        }
        learnset_map[species_key] = std::move(normalized_moves);
    }

    for (const auto& jp : jpokemon) {
        if (!jp.value("champions_legal", false)) continue;

        palette::SpeciesEntry se;
        se.display_name = jp.at("name_en").get<std::string>();
        se.id = normalize_id(se.display_name);
        se.name = se.display_name; // string_view into display_name — set after push_back

        se.dex = jp.at("dex").get<int>();

        std::string t1_str = jp.at("type1").get<std::string>();
        se.types[0] = parse_type(t1_str);
        se.types[1] = Type::COUNT; // default: no second type
        if (!jp["type2"].is_null()) {
            se.types[1] = parse_type(jp["type2"].get<std::string>());
        }

        se.base.hp  = jp.at("hp").get<int>();
        se.base.atk = jp.at("atk").get<int>();
        se.base.def = jp.at("def").get<int>();
        se.base.spa = jp.at("spa").get<int>();
        se.base.spd = jp.at("spd").get<int>();
        se.base.spe = jp.at("spe").get<int>();

        // Learnset (normalized move IDs that exist in the move table)
        auto it = learnset_map.find(se.display_name);
        if (it != learnset_map.end()) {
            for (const auto& mv_id : it->second) {
                if (move_id_to_index.count(mv_id)) {
                    se.learnset.push_back(mv_id);
                }
            }
        }

        // Abilities
        if (jp.contains("abilities") && jp["abilities"].is_array()) {
            for (const auto& ab : jp["abilities"]) {
                se.legal_abilities.push_back(normalize_id(ab.get<std::string>()));
            }
        }

        species_table.push_back(std::move(se));
    }

    // Fix string_view name pointers — must be done after push_back (stable storage)
    // Re-assign after the vector is complete.
    for (auto& se : species_table) {
        se.name = se.display_name;
    }

    // Log summary
    std::cerr << "# champions data: "
              << species_table.size() << " species / "
              << move_table.size()    << " moves / "
              << (item_table.size() > 0 ? item_table.size() - 1 : 0) << " items / "
              << "18 types loaded from " << root.string() << "\n";

    g_loaded = true;
}

void load_data(std::optional<fs::path> override_root) {
    // If override is provided we allow re-loading (for tests).
    if (override_root.has_value()) {
        do_load(override_root);
        return;
    }
    std::call_once(g_load_flag, [&]() {
        do_load(std::nullopt);
    });
}

fs::path data_root() {
    if (!g_loaded)
        throw std::runtime_error("champions_data: load_data() has not been called");
    return g_data_root;
}

} // namespace battle::champions
