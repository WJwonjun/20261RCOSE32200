#pragma once
#include <string>
#include <optional>
#include <array>
#include <nlohmann/json.hpp>
#include "action.hpp"

namespace battle {

struct SidecarResponse {
    std::optional<Action> action;   // nullopt if failure_reason set
    std::string failure_reason;     // "", "timeout", "rate_limit", "parse_fail", "schema_violation"
    int latency_ms   = 0;
    int cached_tokens = 0;
    int prompt_tokens = 0;
};

// Response from the sidecar's team-selection phase.
// selection[i] is idx into team.party (0..5), 3 distinct values.
// lead_idx_in_party is selection[0] (the initial active mon's party index).
struct SelectionResponse {
    std::optional<std::array<int, 3>> selection; // nullopt on failure
    int lead_idx_in_party = -1;
    std::string failure_reason; // "", "timeout", "parse_fail", "schema_violation"
    int latency_ms = 0;
};

class SidecarClient {
public:
    explicit SidecarClient(std::string socket_path);
    ~SidecarClient();

    // Blocking. Sends one JSONL turn request, reads one JSONL response.
    SidecarResponse request_action(
        const nlohmann::json& turn_state,
        std::string_view      rulebook_path,
        std::string_view      team_spec,
        std::string_view      idempotency_key,
        int                   timeout_ms = 10000);

    // Blocking. Sends a team-selection request (phase="selection") and reads
    // one JSONL response.  team_spec is a JSON string describing the 6-mon
    // entry for this side.
    // Idempotency key format: "{battle_id}:select:{side}"
    SelectionResponse request_team_selection(
        const nlohmann::json& selection_state,
        std::string_view      rulebook_path,
        std::string_view      team_spec,
        std::string_view      idempotency_key,
        int                   timeout_ms = 10000);

private:
    std::string socket_path_;
    int fd_ = -1;

    void ensure_connected_();  // exponential backoff 100ms–5s, give up after 10s
    void reconnect_();         // EPIPE forces single reconnect+retry per design contract
};

} // namespace battle
