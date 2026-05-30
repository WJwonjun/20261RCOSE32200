#include "battle/team_loader.hpp"
#include "battle/palette.hpp"
#include "battle/pokemon.hpp"
#include "battle/champions_data.hpp"
#include <fstream>
#include <nlohmann/json.hpp>

namespace battle {

namespace {

Nature parse_nature(const std::string& s) {
    const palette::NatureEntry* ne = palette::find_nature(s);
    if (ne) return ne->nature;
    throw std::runtime_error("team_loader: unknown nature \"" + s + "\"");
}

int item_id_for(const std::string& s) {
    // Scan item table by index (0 = none sentinel).
    const auto& items = palette::item_entries();
    for (int i = 0; i < static_cast<int>(items.size()); ++i) {
        if (items[i].id == s) return i;
    }
    throw std::runtime_error("team_loader: unknown item \"" + s + "\"");
}

// Loads a single team member from JSON.
// Enforces that all moves are in the species' learnset.
Pokemon load_member(const nlohmann::json& j) {
    // --- species ---
    const std::string species_str = j.at("species").get<std::string>();
    const palette::SpeciesEntry* sp = palette::find_species(species_str);
    if (!sp) throw std::runtime_error("team_loader: unknown species \"" + species_str + "\"");

    // --- level ---
    int level = j.at("level").get<int>();

    // --- IVs ---
    IVs ivs;
    {
        const auto& jivs = j.at("ivs");
        ivs.hp  = jivs.at("hp").get<int>();
        ivs.atk = jivs.at("atk").get<int>();
        ivs.def = jivs.at("def").get<int>();
        ivs.spa = jivs.at("spa").get<int>();
        ivs.spd = jivs.at("spd").get<int>();
        ivs.spe = jivs.at("spe").get<int>();
        for (int v : {ivs.hp, ivs.atk, ivs.def, ivs.spa, ivs.spd, ivs.spe}) {
            if (v < 0 || v > 31)
                throw std::runtime_error("team_loader: IV out of range [0,31]");
        }
    }

    // --- EVs ---
    EVs evs;
    {
        const auto& jevs = j.at("evs");
        evs.hp  = jevs.at("hp").get<int>();
        evs.atk = jevs.at("atk").get<int>();
        evs.def = jevs.at("def").get<int>();
        evs.spa = jevs.at("spa").get<int>();
        evs.spd = jevs.at("spd").get<int>();
        evs.spe = jevs.at("spe").get<int>();
        for (int v : {evs.hp, evs.atk, evs.def, evs.spa, evs.spd, evs.spe}) {
            if (v < 0 || v > 252)
                throw std::runtime_error("team_loader: EV out of range [0,252]");
        }
        int total = evs.hp + evs.atk + evs.def + evs.spa + evs.spd + evs.spe;
        if (total > 508)
            throw std::runtime_error("team_loader: EV total " + std::to_string(total) + " exceeds 508");
    }

    // --- nature ---
    Nature nature = parse_nature(j.at("nature").get<std::string>());

    // --- moves (exactly 4) ---
    const auto& jmoves = j.at("moves");
    if (jmoves.size() != 4)
        throw std::runtime_error("team_loader: each member must have exactly 4 moves");

    std::array<int, 4> move_ids = {0, 0, 0, 0};
    for (int i = 0; i < 4; ++i) {
        const std::string mid = jmoves[i].get<std::string>();
        const Move* m = palette::find_move(mid);
        if (!m) throw std::runtime_error("team_loader: unknown move \"" + mid + "\"");

        // Enforce learnset: move must be in species' learnset.
        // sp->learnset contains normalized move IDs.
        bool in_learnset = false;
        for (const auto& lm : sp->learnset) {
            if (lm == mid) { in_learnset = true; break; }
        }
        if (!in_learnset)
            throw std::runtime_error(
                "team_loader: move '" + mid + "' not in " + species_str + "'s learnset");

        move_ids[i] = m->id;
    }

    // --- item (optional, default "none") ---
    int iid = 0;
    if (j.contains("item")) {
        iid = item_id_for(j.at("item").get<std::string>());
    }

    // --- assemble Pokemon ---
    Pokemon p;
    // Use the species index as species_id (position in palette vector).
    p.species_id = static_cast<int>(sp - palette::species().data());
    p.name       = sp->display_name;
    p.level      = level;
    p.type1      = sp->types[0];
    p.type2      = sp->types[1];
    p.base_stats = sp->base;
    p.ivs        = ivs;
    p.evs        = evs;
    p.nature     = nature;
    p.item_id    = iid;
    p.stats      = compute_stats(sp->base, ivs, evs, nature, level);
    p.current_hp = p.stats.hp;
    p.move_ids   = move_ids;
    for (int i = 0; i < 4; ++i) {
        const Move* m = battle::find_move(move_ids[i]);
        p.pp[i] = m ? m->pp_max : 0;
    }
    return p;
}

} // namespace

Team load_team_json(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open())
        throw std::runtime_error("team_loader: cannot open file \"" + path + "\"");

    nlohmann::json j;
    try {
        f >> j;
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error("team_loader: " + std::string(e.what()));
    }

    const auto& members = j.at("members");
    if (members.size() != 6)
        throw std::runtime_error(
            "team_loader: expected exactly 6 members, got " +
            std::to_string(members.size()));

    Team t;
    try {
        for (int i = 0; i < 6; ++i) {
            t.party[i] = load_member(members[i]);
        }
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error("team_loader: " + std::string(e.what()));
    }
    t.active_slot = 0;
    return t;
}

} // namespace battle
