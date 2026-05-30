#pragma once
#include <array>
#include <optional>
#include "pokemon.hpp"

namespace battle {

struct Team {
    std::array<Pokemon, 6> party       = {};

    // ── 6→3 selection ────────────────────────────────────────────────────────
    // Indices into `party` of the 3 Pokemon selected for this battle.
    // selection.size() == 3, all values distinct and in [0,6).
    // Order matters: selection[0] is the initial lead.
    std::array<int, 3> selection = {0, 1, 2};

    // 0..2: which of the 3 selected slots is currently active.
    int active_idx_in_selection = 0;

    // Legacy field kept for backwards compat during initialization; canonical
    // active is party[selection[active_idx_in_selection]].
    int active_slot = 0; // set from selection[active_idx_in_selection] at battle start

    // ── accessors ─────────────────────────────────────────────────────────────

    Pokemon&       active()       noexcept { return party[selection[active_idx_in_selection]]; }
    const Pokemon& active() const noexcept { return party[selection[active_idx_in_selection]]; }

    // True if any of the 3 selected Pokemon has HP > 0.
    bool any_selected_alive() const noexcept {
        for (int i = 0; i < 3; ++i) {
            if (!party[selection[i]].is_fainted()) return true;
        }
        return false;
    }

    // Kept for uses that still care about the full party (e.g. display).
    bool any_alive() const noexcept {
        for (auto& p : party) {
            if (!p.is_fainted()) return true;
        }
        return false;
    }

    // Returns idx_in_selection (0..2) of the first alive selected slot that is
    // not the given idx_in_selection, or -1 if none exists.
    int first_selected_alive_bench(int exclude_idx_in_sel) const noexcept {
        for (int i = 0; i < 3; ++i) {
            if (i == exclude_idx_in_sel) continue;
            if (!party[selection[i]].is_fainted()) return i;
        }
        return -1;
    }

    // Legacy helper — first alive bench slot by party index (kept for
    // non-selection-aware callers; during a battle this resolves through
    // selected slots via first_selected_alive_bench).
    int first_alive_bench() const noexcept {
        return first_selected_alive_bench(active_idx_in_selection);
    }
};

} // namespace battle
