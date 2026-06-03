#include "battle/state.hpp"
#include "battle/damage.hpp"
#include "battle/move.hpp"
#include <algorithm>
#include <sstream>

namespace battle {

// ── helpers ──────────────────────────────────────────────────────────────────

static std::string pname(const Pokemon& p) { return p.name; }

static void log_append(BattleState& st, std::string msg) {
    st.log.push_back(std::move(msg));
}

// Returns move priority for ordering. SwitchAction always goes first (priority 6).
static int action_priority(const Action& a, const Pokemon& user) {
    if (std::holds_alternative<SwitchAction>(a)) return 6;
    if (std::holds_alternative<NoAction>(a))     return -99;
    int idx = std::get<MoveAction>(a).move_idx;
    int mid = user.move_ids[idx];
    const Move* m = find_move(mid);
    return m ? m->priority : 0;
}

// ── accuracy check ────────────────────────────────────────────────────────────

static bool accuracy_check(const Move& move, PCG64& rng) noexcept {
    if (move.accuracy == 0) return true; // always hits (Protect, etc.)
    // rng: accuracy roll
    return rng.range(1, 100) <= move.accuracy;
}

// ── status tick (end of turn) ─────────────────────────────────────────────────

static void apply_status_tick(Pokemon& p, BattleState& st) {
    switch (p.status) {
        case StatusCondition::Burn:
        case StatusCondition::Poison: {
            int dmg = std::max(1, p.stats.hp / 8);
            p.current_hp -= dmg;
            if (p.current_hp < 0) p.current_hp = 0;
            std::ostringstream oss;
            oss << "{\"event\":\"status_damage\",\"pokemon\":\"" << pname(p)
                << "\",\"status\":\"" << (p.status == StatusCondition::Burn ? "BRN" : "PSN")
                << "\",\"damage\":" << dmg << "}";
            log_append(st, oss.str());
            break;
        }
        default: break;
    }
}

// ── try-to-move-check (paralysis/sleep/freeze) ────────────────────────────────

static bool can_move(Pokemon& p, BattleState& st) {
    switch (p.status) {
        case StatusCondition::Paralysis:
            // rng: paralysis skip roll (25%)
            if (st.rng.range(1, 4) == 1) {
                log_append(st, "{\"event\":\"paralysis_skip\",\"pokemon\":\"" + pname(p) + "\"}");
                return false;
            }
            return true;
        case StatusCondition::Sleep:
            if (p.status_turns > 0) {
                p.status_turns--;
                log_append(st, "{\"event\":\"asleep\",\"pokemon\":\"" + pname(p) + "\",\"turns_left\":" + std::to_string(p.status_turns) + "}");
                return false;
            }
            p.status = StatusCondition::None;
            log_append(st, "{\"event\":\"woke_up\",\"pokemon\":\"" + pname(p) + "\"}");
            return true;
        case StatusCondition::Freeze:
            // rng: thaw roll (20%)
            if (st.rng.range(1, 5) == 1) {
                p.status = StatusCondition::None;
                log_append(st, "{\"event\":\"thawed\",\"pokemon\":\"" + pname(p) + "\"}");
                return true;
            }
            log_append(st, "{\"event\":\"frozen\",\"pokemon\":\"" + pname(p) + "\"}");
            return false;
        default:
            return true;
    }
}

// ── inflict status ────────────────────────────────────────────────────────────

static void try_inflict_status(Pokemon& target, StatusCondition sc, BattleState& st) {
    if (target.status != StatusCondition::None) return; // already statused
    if (target.is_fainted()) return;
    target.status = sc;
    if (sc == StatusCondition::Sleep) {
        // rng: sleep duration 1-3 turns
        target.status_turns = st.rng.range(1, 3);
    }
    const char* names[] = {"none","BRN","PSN","PAR","FRZ","SLP"};
    std::ostringstream oss;
    oss << "{\"event\":\"status_inflicted\",\"pokemon\":\"" << pname(target)
        << "\",\"status\":\"" << names[(int)sc] << "\"}";
    log_append(st, oss.str());
}

// ── execute one move ──────────────────────────────────────────────────────────

static void execute_move(Pokemon& attacker, Pokemon& defender,
                         int move_idx, BattleState& st) {
    if (attacker.is_fainted()) return;

    int mid = attacker.move_ids[move_idx];
    const Move* move = find_move(mid);
    if (!move) return;

    // PP check
    if (attacker.pp[move_idx] <= 0) {
        log_append(st, "{\"event\":\"no_pp\",\"pokemon\":\"" + pname(attacker) + "\"}");
        return;
    }
    attacker.pp[move_idx]--;

    std::ostringstream oss;
    oss << "{\"event\":\"move\",\"pokemon\":\"" << pname(attacker)
        << "\",\"move\":\"" << move->name << "\"}";
    log_append(st, oss.str());

    // Protect: skip damage for this turn (simplified: just log)
    if (move->id == 9) {
        log_append(st, "{\"event\":\"protect\",\"pokemon\":\"" + pname(attacker) + "\"}");
        return;
    }

    // Accuracy check
    if (!accuracy_check(*move, st.rng)) {
        log_append(st, "{\"event\":\"miss\",\"pokemon\":\"" + pname(attacker) + "\"}");
        return;
    }

    if (move->category != MoveCategory::Status) {
        int dmg = compute_damage(attacker, defender, *move, st.rng);
        defender.current_hp -= dmg;
        if (defender.current_hp < 0) defender.current_hp = 0;
        std::ostringstream dmg_oss;
        dmg_oss << "{\"event\":\"damage\",\"target\":\"" << pname(defender)
                << "\",\"damage\":" << dmg
                << ",\"hp_remaining\":" << defender.current_hp << "}";
        log_append(st, dmg_oss.str());
    }

    // Status effect on target (30% chance for secondary effects, 100% for pure status moves)
    if (move->status_effect != StatusCondition::None && !defender.is_fainted()) {
        bool apply = false;
        if (move->category == MoveCategory::Status) {
            apply = true; // status moves always attempt
        } else {
            // rng: secondary effect roll (30%)
            apply = (st.rng.range(1, 10) <= 3);
        }
        if (apply) try_inflict_status(defender, move->status_effect, st);
    }
}

// ── force switch for fainted active (selection-aware) ────────────────────────
// Switches to the first alive selected bench slot.  If none remain, the side
// is eliminated and is_terminal() will return true on the next check.

static void force_switch_if_fainted(Team& team, BattleState& st, const std::string& side_name) {
    if (!team.active().is_fainted()) return;
    int next_sel = team.first_selected_alive_bench(team.active_idx_in_selection);
    if (next_sel < 0) return; // no selected mon remains → battle_end
    log_append(st, "{\"event\":\"force_switch\",\"side\":\"" + side_name +
               "\",\"out\":\"" + pname(team.active()) +
               "\",\"in\":\"" + pname(team.party[team.selection[next_sel]]) + "\"}");
    team.active_idx_in_selection = next_sel;
    team.active_slot = team.selection[next_sel]; // keep party-slot view in sync
}

// ── execute voluntary switch (idx_in_selection) ───────────────────────────────

static void execute_switch(Team& team, int to_idx_in_sel, BattleState& st, const std::string& side_name) {
    if (to_idx_in_sel < 0 || to_idx_in_sel >= 3) return;
    Pokemon& target = team.party[team.selection[to_idx_in_sel]];
    if (target.is_fainted()) return;
    log_append(st, "{\"event\":\"switch\",\"side\":\"" + side_name +
               "\",\"out\":\"" + pname(team.active()) +
               "\",\"in\":\"" + pname(target) + "\"}");
    team.active_idx_in_selection = to_idx_in_sel;
    team.active_slot = team.selection[to_idx_in_sel]; // keep party-slot view in sync
}

// ── legal_actions (selection-aware) ──────────────────────────────────────────

std::vector<Action> BattleState::legal_actions(Side side) const {
    std::vector<Action> actions;
    const Team& t = team(side);
    const Pokemon& active = t.active();

    // Move actions — only moves with PP > 0
    for (int i = 0; i < 4; ++i) {
        if (active.move_ids[i] != 0 && active.pp[i] > 0) {
            actions.push_back(MoveAction{i});
        }
    }

    // Switch actions — only the OTHER TWO selected slots (not the full party).
    // SwitchAction::to is idx_in_selection (0..2).
    for (int i = 0; i < 3; ++i) {
        if (i != t.active_idx_in_selection && !t.party[t.selection[i]].is_fainted()) {
            actions.push_back(SwitchAction{i});
        }
    }

    if (actions.empty()) actions.push_back(NoAction{});
    return actions;
}

// ── is_terminal / winner ──────────────────────────────────────────────────────
// A side loses when ALL 3 of its selected Pokemon are fainted.

bool BattleState::is_terminal() const noexcept {
    return !team_a.any_selected_alive() || !team_b.any_selected_alive();
}

int BattleState::winner() const noexcept {
    bool a_alive = team_a.any_selected_alive();
    bool b_alive = team_b.any_selected_alive();
    if (!b_alive && a_alive) return 0;
    if (!a_alive && b_alive) return 1;
    return -1;
}

// ── apply_action (one full turn) ──────────────────────────────────────────────

bool BattleState::apply_action(Action action_a, Action action_b) {
    if (is_terminal()) return false;

    turn_no++;
    std::ostringstream toss;
    toss << "{\"event\":\"turn_start\",\"turn\":" << turn_no << "}";
    log_append(*this, toss.str());

    // Determine turn order by priority then speed.
    int prio_a = action_priority(action_a, team_a.active());
    int prio_b = action_priority(action_b, team_b.active());

    bool a_first;
    if (prio_a != prio_b) {
        a_first = prio_a > prio_b;
    } else {
        int spe_a = effective_spe(team_a.active());
        int spe_b = effective_spe(team_b.active());
        if (spe_a != spe_b) {
            a_first = spe_a > spe_b;
        } else {
            // rng: speed tie break
            a_first = (rng.range(0, 1) == 0);
        }
    }

    // Helper: resolve one side's action
    auto resolve = [&](Side mover, Action& action) {
        Team& atk_team = team(mover);
        Team& def_team = opponent(mover);
        const std::string side_name = (mover == Side::A) ? "A" : "B";

        if (std::holds_alternative<SwitchAction>(action)) {
            int to = std::get<SwitchAction>(action).to;
            execute_switch(atk_team, to, *this, side_name);
        } else if (std::holds_alternative<MoveAction>(action)) {
            if (!atk_team.active().is_fainted() && !def_team.active().is_fainted()) {
                if (can_move(atk_team.active(), *this)) {
                    int idx = std::get<MoveAction>(action).move_idx;
                    execute_move(atk_team.active(), def_team.active(), idx, *this);
                }
            }
            // Force switch if defender fainted after this move
            if (def_team.active().is_fainted()) {
                force_switch_if_fainted(def_team, *this,
                    (mover == Side::A) ? "B" : "A");
            }
        }
    };

    if (a_first) {
        resolve(Side::A, action_a);
        if (!is_terminal()) resolve(Side::B, action_b);
    } else {
        resolve(Side::B, action_b);
        if (!is_terminal()) resolve(Side::A, action_a);
    }

    // End-of-turn status ticks
    if (!team_a.active().is_fainted())
        apply_status_tick(team_a.active(), *this);
    if (!team_b.active().is_fainted())
        apply_status_tick(team_b.active(), *this);

    // Force switch for any fainted actives after status damage
    force_switch_if_fainted(team_a, *this, "A");
    force_switch_if_fainted(team_b, *this, "B");

    std::ostringstream tend;
    tend << "{\"event\":\"turn_end\",\"turn\":" << turn_no
         << ",\"hp_a\":" << team_a.active().current_hp
         << ",\"hp_b\":" << team_b.active().current_hp << "}";
    log_append(*this, tend.str());

    return true;
}

} // namespace battle
