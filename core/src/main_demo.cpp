#include <iostream>
#include <string>
#include <cstring>
#include <array>
#include <memory>
#include "battle/state.hpp"
#include "battle/ai_stub.hpp"
#include "battle/pokemon.hpp"
#include "battle/move.hpp"
#include "battle/ipc.hpp"
#include "battle/serialize.hpp"
#include "battle/palette.hpp"
#include "battle/team_loader.hpp"
#include "battle/champions_data.hpp"
#include <nlohmann/json.hpp>

using namespace battle;

static Pokemon make_palette_pokemon(const std::string& species_id, Nature nature,
                                     const std::array<std::string, 4>& move_names,
                                     int level = 50) {
    const palette::SpeciesEntry* sp = palette::find_species(species_id);
    if (!sp) throw std::runtime_error("make_palette_pokemon: unknown species " + species_id);
    Pokemon p;
    p.species_id = static_cast<int>(sp - palette::species().data());
    p.name       = sp->display_name;
    p.level      = level;
    p.type1      = sp->types[0];
    p.type2      = sp->types[1];
    p.base_stats = sp->base;
    p.nature     = nature;
    p.stats      = compute_stats(sp->base, p.ivs, p.evs, nature, level);
    p.current_hp = p.stats.hp;
    for (int i = 0; i < 4; ++i) {
        const Move* m = palette::find_move(move_names[i]);
        if (!m) throw std::runtime_error("make_palette_pokemon: unknown move " + move_names[i]);
        p.move_ids[i] = m->id;
        p.pp[i]       = m->pp_max;
    }
    return p;
}

// Deterministic demo teams using species from the loaded Champions DB.
// Species: Snorlax, Charizard, Garchomp, Gengar, Dragonite, Scizor.
// All moves are verified to be in each species' Champions learnset.
static Team make_team_a() {
    Team t;
    t.party[0] = make_palette_pokemon("snorlax",   NATURE_ADAMANT,
        {"body_slam", "earthquake", "crunch", "rest"});
    t.party[1] = make_palette_pokemon("charizard", NATURE_MODEST,
        {"flamethrower", "air_slash", "dragon_claw", "earthquake"});
    t.party[2] = make_palette_pokemon("garchomp",  NATURE_JOLLY,
        {"dragon_claw", "earthquake", "crunch", "iron_head"});
    t.party[3] = make_palette_pokemon("gengar",    NATURE_TIMID,
        {"shadow_ball", "sludge_bomb", "dark_pulse", "thunderbolt"});
    t.party[4] = make_palette_pokemon("dragonite", NATURE_ADAMANT,
        {"dragon_claw", "earthquake", "flamethrower", "thunderbolt"});
    t.party[5] = make_palette_pokemon("scizor",    NATURE_ADAMANT,
        {"bullet_punch", "iron_head", "x_scissor", "brick_break"});
    t.active_slot = 0;
    return t;
}

static Team make_team_b() {
    Team t;
    t.party[0] = make_palette_pokemon("garchomp",  NATURE_JOLLY,
        {"earthquake", "dragon_claw", "iron_head", "crunch"});
    t.party[1] = make_palette_pokemon("gengar",    NATURE_TIMID,
        {"shadow_ball", "thunderbolt", "dark_pulse", "sludge_bomb"});
    t.party[2] = make_palette_pokemon("snorlax",   NATURE_ADAMANT,
        {"body_slam", "crunch", "earthquake", "rest"});
    t.party[3] = make_palette_pokemon("dragonite", NATURE_MODEST,
        {"flamethrower", "thunderbolt", "dragon_claw", "earthquake"});
    t.party[4] = make_palette_pokemon("scizor",    NATURE_ADAMANT,
        {"iron_head", "bullet_punch", "brick_break", "x_scissor"});
    t.party[5] = make_palette_pokemon("charizard", NATURE_TIMID,
        {"flamethrower", "dragon_claw", "air_slash", "earthquake"});
    t.active_slot = 0;
    return t;
}

static std::string type_name(Type t) {
    switch (t) {
        case Type::Normal:   return "normal";
        case Type::Fire:     return "fire";
        case Type::Water:    return "water";
        case Type::Electric: return "electric";
        case Type::Grass:    return "grass";
        case Type::Ice:      return "ice";
        case Type::Fighting: return "fighting";
        case Type::Poison:   return "poison";
        case Type::Ground:   return "ground";
        case Type::Flying:   return "flying";
        case Type::Psychic:  return "psychic";
        case Type::Bug:      return "bug";
        case Type::Rock:     return "rock";
        case Type::Ghost:    return "ghost";
        case Type::Dragon:   return "dragon";
        case Type::Dark:     return "dark";
        case Type::Steel:    return "steel";
        case Type::Fairy:    return "fairy";
        default:             return "unknown";
    }
}

static void print_palette_json() {
    nlohmann::json out;

    // species
    nlohmann::json sp_arr = nlohmann::json::array();
    for (const auto& s : palette::species()) {
        nlohmann::json e;
        e["id"]           = s.id;
        e["display_name"] = s.display_name;
        e["dex"]          = s.dex;
        nlohmann::json types = nlohmann::json::array();
        types.push_back(type_name(s.types[0]));
        if (s.types[1] != Type::COUNT) types.push_back(type_name(s.types[1]));
        e["types"] = types;
        e["base_hp"]  = s.base.hp;
        e["base_atk"] = s.base.atk;
        e["base_def"] = s.base.def;
        e["base_spa"] = s.base.spa;
        e["base_spd"] = s.base.spd;
        e["base_spe"] = s.base.spe;
        sp_arr.push_back(e);
    }
    out["species"] = sp_arr;

    // moves
    nlohmann::json mv_arr = nlohmann::json::array();
    for (const auto& m : palette::moves()) {
        nlohmann::json e;
        e["id"]           = m.name;
        e["display_name"] = m.display_name;
        e["power"]        = m.power;
        e["accuracy"]     = m.accuracy;
        e["pp"]           = m.pp_max;
        e["priority"]     = m.priority;
        mv_arr.push_back(e);
    }
    out["moves"] = mv_arr;

    // items and natures as plain arrays
    nlohmann::json items_arr = nlohmann::json::array();
    for (const auto& ie : palette::item_entries()) items_arr.push_back(ie.id);
    out["items"] = items_arr;

    nlohmann::json natures_arr = nlohmann::json::array();
    for (const auto& ne : palette::nature_entries()) natures_arr.push_back(ne.id);
    out["natures"] = natures_arr;

    std::cout << out.dump(2) << std::endl;
}

int main(int argc, char* argv[]) {
    // Load Champions regulation data first (populates palette tables).
    try {
        champions::load_data();
    } catch (const std::exception& e) {
        std::cerr << "# error: failed to load Champions data: " << e.what() << std::endl;
        return 1;
    }

    // CLI flag parsing
    bool        use_sidecar   = false;
    std::string socket_path   = "/tmp/pokemon_sidecar.sock";
    std::string rulebook_path = "rulebook/rulebook.md";
    uint64_t    rng_seed      = 42;
    std::string team_a_path;
    std::string team_b_path;
    bool        print_palette = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--sidecar") {
            use_sidecar = true;
        } else if (arg.rfind("--socket=", 0) == 0) {
            socket_path = arg.substr(9);
        } else if (arg.rfind("--rulebook=", 0) == 0) {
            rulebook_path = arg.substr(11);
        } else if (arg.rfind("--seed=", 0) == 0) {
            rng_seed = static_cast<uint64_t>(std::stoull(arg.substr(7)));
        } else if (arg.rfind("--team-a=", 0) == 0) {
            team_a_path = arg.substr(9);
        } else if (arg.rfind("--team-b=", 0) == 0) {
            team_b_path = arg.substr(9);
        } else if (arg == "--print-palette") {
            print_palette = true;
        }
    }

    if (print_palette) {
        print_palette_json();
        return 0;
    }

    // Check env var for socket path override (mirrors sidecar convention).
    const char* env_sock = std::getenv("POKEMON_SIDECAR_SOCK");
    if (env_sock && !use_sidecar) {
        socket_path = env_sock;
    } else if (env_sock) {
        socket_path = env_sock;
    }

    BattleState state;
    state.team_a = make_team_a();
    state.team_b = make_team_b();

    if (!team_a_path.empty()) {
        try {
            state.team_a = load_team_json(team_a_path);
        } catch (const std::exception& e) {
            std::cerr << "# error: failed to load team A: " << e.what() << std::endl;
            return 2;
        }
    }
    if (!team_b_path.empty()) {
        try {
            state.team_b = load_team_json(team_b_path);
        } catch (const std::exception& e) {
            std::cerr << "# error: failed to load team B: " << e.what() << std::endl;
            return 2;
        }
    }

    state.rng = PCG64(rng_seed);

    if (use_sidecar) {
        std::cout << "# mode: sidecar (socket=" << socket_path
                  << ") rulebook=" << rulebook_path << "\n";
    }

    // In sidecar mode the LLM also drives the 6->3 team preview, so create the
    // client up front (one connection serves selection + per-turn actions).
    std::unique_ptr<SidecarClient> client;
    if (use_sidecar) {
        client = std::make_unique<SidecarClient>(socket_path);
    }

    // Apply a concrete 6->3 selection to a team and log it (with its source).
    auto apply_selection = [](Team& t, const std::array<int, 3>& sel, int lead,
                              const std::string& side, const std::string& source) {
        t.selection = sel;
        int lead_pos = 0;
        for (int i = 0; i < 3; ++i) if (sel[i] == lead) lead_pos = i;
        t.active_idx_in_selection = lead_pos;
        t.active_slot             = t.selection[lead_pos];
        nlohmann::json lineup = nlohmann::json::array();
        for (int i = 0; i < 3; ++i) lineup.push_back(t.party[t.selection[i]].name);
        nlohmann::json ev;
        ev["event"]    = "team_selection";
        ev["side"]     = side;
        ev["selected"] = {t.selection[0], t.selection[1], t.selection[2]};
        ev["lineup"]   = lineup;
        ev["source"]   = source;
        std::cout << ev.dump() << std::endl;
    };

    // Pick 3-of-6 for one side: ask the LLM in sidecar mode, otherwise (or on
    // any sidecar failure) use the deterministic strongest-three heuristic.
    auto select_team = [&](Team& t, const std::string& side) {
        if (client) {
            nlohmann::json sel_state = serialize_selection_state(t, side);
            nlohmann::json spec      = serialize_acting_team(t);
            SelectionResponse r = client->request_team_selection(
                sel_state, rulebook_path, spec.dump(),
                "battle_0:select:" + side, 10000);
            if (r.selection.has_value()) {
                apply_selection(t, *r.selection, r.lead_idx_in_party, side, "sidecar");
                return;
            }
            nlohmann::json fail;
            fail["event"]  = "selection_failure";
            fail["side"]   = side;
            fail["reason"] = r.failure_reason;
            std::cout << fail.dump() << std::endl;
        }
        std::array<int, 3> sel = choose_selection(t);
        apply_selection(t, sel, sel[0], side, "heuristic");
    };
    select_team(state.team_a, "A");
    select_team(state.team_b, "B");

    std::cout << "{\"event\":\"battle_start\","
              << "\"team_a\":\"" << state.team_a.active().name << " lead\","
              << "\"team_b\":\"" << state.team_b.active().name << " lead\"}"
              << std::endl;

    constexpr int MAX_TURNS = 200;

    if (!use_sidecar) {
        // Pure C++ heuristic mode.
        while (!state.is_terminal() && state.turn_no < MAX_TURNS) {
            Action a = choose_max_damage_action(state, Side::A);
            Action b = choose_max_damage_action(state, Side::B);
            state.apply_action(a, b);

            static size_t printed = 0;
            for (; printed < state.log.size(); ++printed) {
                std::cout << state.log[printed] << "\n";
            }
            std::cout.flush();
        }
    } else {
        // Sidecar mode (client created above for the selection phase).
        size_t printed = 0;

        while (!state.is_terminal() && state.turn_no < MAX_TURNS) {
            int turn = state.turn_no + 1;

            std::string key_a = "battle_0:" + std::to_string(turn) + ":A";
            nlohmann::json ts_a   = serialize_turn_state(state, 0);
            nlohmann::json spec_a = serialize_acting_team(state.team_a);
            SidecarResponse resp_a = client->request_action(
                ts_a, rulebook_path, spec_a.dump(), key_a, 10000);

            Action action_a;
            std::string source_a;
            if (resp_a.action.has_value()) {
                action_a = *resp_a.action;
                source_a = "sidecar";
            } else {
                action_a = choose_max_damage_action(state, Side::A);
                source_a = "heuristic";
                nlohmann::json fail;
                fail["event"]  = "sidecar_failure";
                fail["reason"] = resp_a.failure_reason;
                fail["turn"]   = turn;
                fail["side"]   = "A";
                state.log.push_back(fail.dump());
            }

            std::string key_b = "battle_0:" + std::to_string(turn) + ":B";
            nlohmann::json ts_b   = serialize_turn_state(state, 1);
            nlohmann::json spec_b = serialize_acting_team(state.team_b);
            SidecarResponse resp_b = client->request_action(
                ts_b, rulebook_path, spec_b.dump(), key_b, 10000);

            Action action_b;
            std::string source_b;
            if (resp_b.action.has_value()) {
                action_b = *resp_b.action;
                source_b = "sidecar";
            } else {
                action_b = choose_max_damage_action(state, Side::B);
                source_b = "heuristic";
                nlohmann::json fail;
                fail["event"]  = "sidecar_failure";
                fail["reason"] = resp_b.failure_reason;
                fail["turn"]   = turn;
                fail["side"]   = "B";
                state.log.push_back(fail.dump());
            }

            state.apply_action(action_a, action_b);

            for (; printed < state.log.size(); ++printed) {
                const std::string& line = state.log[printed];
                if (line.find("\"turn_end\"") != std::string::npos) {
                    try {
                        nlohmann::json jl = nlohmann::json::parse(line);
                        jl["action_source_a"] = source_a;
                        jl["action_source_b"] = source_b;
                        std::cout << jl.dump() << "\n";
                    } catch (...) {
                        std::cout << line << "\n";
                    }
                } else {
                    std::cout << line << "\n";
                }
            }
            std::cout.flush();
        }
    }

    int w = state.winner();
    if (w == 0) {
        std::cout << "{\"event\":\"battle_end\",\"winner\":\"A\","
                  << "\"team\":\"" << state.team_a.party[0].name << " side\"}" << std::endl;
    } else if (w == 1) {
        std::cout << "{\"event\":\"battle_end\",\"winner\":\"B\","
                  << "\"team\":\"" << state.team_b.party[0].name << " side\"}" << std::endl;
    } else {
        std::cout << "{\"event\":\"battle_end\",\"winner\":\"draw_or_timeout\","
                  << "\"turns\":" << state.turn_no << "}" << std::endl;
    }

    return 0;
}
