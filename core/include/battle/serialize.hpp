#pragma once
#include <nlohmann/json.hpp>
#include "state.hpp"
#include "action.hpp"

namespace battle {

// Serialize a legal action to {"action":"move|switch","target":N}.
nlohmann::json serialize_legal_action(const Action& a);

// Full own-team spec: all 6 mons, all moves, stats, items, status, current_hp, pp.
nlohmann::json serialize_acting_team(const Team& team);

// Opponent visible: active mon full info; bench slots show species or "unrevealed".
nlohmann::json serialize_opponent_visible(const Team& opponent, int active_slot);

// Full TurnState schema for the sidecar.
nlohmann::json serialize_turn_state(const BattleState& state, int side /*0=A,1=B*/);

// Team-preview state for the sidecar's 6->3 selection phase: all 6 party mons
// (slot, stats, types, moves) plus the number to select. `side` is "A"/"B".
nlohmann::json serialize_selection_state(const Team& team, const std::string& side);

} // namespace battle
