#include "battle/serialize.hpp"
#include "battle/move.hpp"
#include "battle/types.hpp"

#include <string>

namespace battle {

// rulebook_hash will be the SHA256 of the concatenated rulebook .md files;
// deferred until rulebook build script lands.
static constexpr const char* RULEBOOK_HASH = "TBD";

static std::string type_name(Type t) {
    switch (t) {
        case Type::Normal:   return "Normal";
        case Type::Fire:     return "Fire";
        case Type::Water:    return "Water";
        case Type::Electric: return "Electric";
        case Type::Grass:    return "Grass";
        case Type::Ice:      return "Ice";
        case Type::Fighting: return "Fighting";
        case Type::Poison:   return "Poison";
        case Type::Ground:   return "Ground";
        case Type::Flying:   return "Flying";
        case Type::Psychic:  return "Psychic";
        case Type::Bug:      return "Bug";
        case Type::Rock:     return "Rock";
        case Type::Ghost:    return "Ghost";
        case Type::Dragon:   return "Dragon";
        case Type::Dark:     return "Dark";
        case Type::Steel:    return "Steel";
        case Type::Fairy:    return "Fairy";
        default:             return "None";
    }
}

static std::string status_name(StatusCondition s) {
    switch (s) {
        case StatusCondition::Burn:      return "BRN";
        case StatusCondition::Poison:    return "PSN";
        case StatusCondition::Paralysis: return "PAR";
        case StatusCondition::Freeze:    return "FRZ";
        case StatusCondition::Sleep:     return "SLP";
        default:                         return "";
    }
}

nlohmann::json serialize_legal_action(const Action& a) {
    if (std::holds_alternative<MoveAction>(a)) {
        return {{"action", "move"}, {"target", std::get<MoveAction>(a).move_idx}};
    }
    if (std::holds_alternative<SwitchAction>(a)) {
        return {{"action", "switch"}, {"target", std::get<SwitchAction>(a).to}};
    }
    return {{"action", "none"}, {"target", -1}};
}

static nlohmann::json serialize_pokemon(const Pokemon& p) {
    nlohmann::json moves = nlohmann::json::array();
    for (int i = 0; i < 4; ++i) {
        const Move* m = find_move(p.move_ids[i]);
        nlohmann::json mj;
        if (m) {
            mj["id"]       = m->id;
            mj["name"]     = std::string(m->name);
            mj["type"]     = type_name(m->type);
            mj["power"]    = m->power;
            mj["accuracy"] = m->accuracy;
            mj["pp"]       = p.pp[i];
            mj["pp_max"]   = m->pp_max;
        } else {
            mj["id"]   = 0;
            mj["name"] = "None";
            mj["pp"]   = p.pp[i];
        }
        moves.push_back(mj);
    }

    nlohmann::json j;
    j["species_id"]  = p.species_id;
    j["name"]        = p.name;
    j["level"]       = p.level;
    j["type1"]       = type_name(p.type1);
    j["type2"]       = (p.type2 == Type::COUNT) ? "None" : type_name(p.type2);
    j["current_hp"]  = p.current_hp;
    j["max_hp"]      = p.stats.hp;
    j["status"]      = status_name(p.status);
    j["item_id"]     = p.item_id;
    j["stats"]       = {
        {"hp",  p.stats.hp},
        {"atk", p.stats.atk},
        {"def", p.stats.def},
        {"spa", p.stats.spa},
        {"spd", p.stats.spd},
        {"spe", p.stats.spe}
    };
    j["moves"]       = moves;
    return j;
}

nlohmann::json serialize_acting_team(const Team& team) {
    nlohmann::json party = nlohmann::json::array();
    for (int i = 0; i < 6; ++i) {
        nlohmann::json pj = serialize_pokemon(team.party[i]);
        pj["slot"]      = i;
        pj["is_active"] = (i == team.active_slot);
        party.push_back(pj);
    }
    return {{"active_slot", team.active_slot}, {"party", party}};
}

nlohmann::json serialize_opponent_visible(const Team& opponent, int active_slot) {
    nlohmann::json party = nlohmann::json::array();
    for (int i = 0; i < 6; ++i) {
        if (i == active_slot) {
            nlohmann::json pj = serialize_pokemon(opponent.party[i]);
            pj["slot"]      = i;
            pj["is_active"] = true;
            party.push_back(pj);
        } else {
            // Bench: only species exposed for MVP (treat as unrevealed).
            party.push_back({{"slot", i}, {"species", "unrevealed"}, {"is_active", false}});
        }
    }
    return {{"active_slot", active_slot}, {"party", party}};
}

nlohmann::json serialize_turn_state(const BattleState& state, int side) {
    Side s = (side == 0) ? Side::A : Side::B;
    const Team& acting   = state.team(s);
    const Team& opponent = state.opponent(s);

    auto legal = state.legal_actions(s);
    nlohmann::json legal_json = nlohmann::json::array();
    for (const auto& a : legal) {
        legal_json.push_back(serialize_legal_action(a));
    }

    nlohmann::json j;
    j["rulebook_hash"]     = RULEBOOK_HASH;
    j["acting_team"]       = serialize_acting_team(acting);
    j["opponent_visible"]  = serialize_opponent_visible(opponent, opponent.active_slot);
    j["turn_no"]           = state.turn_no;
    j["side"]              = (side == 0) ? "A" : "B";
    j["legal_actions"]     = legal_json;
    return j;
}

} // namespace battle
