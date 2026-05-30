#include "battle/ipc.hpp"

#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>

#include <chrono>
#include <stdexcept>
#include <thread>

namespace battle {

using Clock = std::chrono::steady_clock;

static int64_t elapsed_ms(Clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               Clock::now() - start)
        .count();
}

SidecarClient::SidecarClient(std::string socket_path)
    : socket_path_(std::move(socket_path)) {}

SidecarClient::~SidecarClient() {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

void SidecarClient::ensure_connected_() {
    if (fd_ >= 0) return;

    // Exponential backoff: 100, 200, 400, 800, 1600, 3200, 5000 ms cap.
    int delays_ms[] = {100, 200, 400, 800, 1600, 3200, 5000};
    constexpr int64_t TIMEOUT_MS = 10000;
    auto start = Clock::now();

    for (int attempt = 0; ; ++attempt) {
        int sock = ::socket(AF_UNIX, SOCK_STREAM, 0);
        if (sock < 0) throw std::runtime_error("socket() failed");

        struct sockaddr_un addr {};
        addr.sun_family = AF_UNIX;
        ::strncpy(addr.sun_path, socket_path_.c_str(), sizeof(addr.sun_path) - 1);

        int rc;
        do {
            rc = ::connect(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));
        } while (rc < 0 && errno == EINTR);

        if (rc == 0) {
            fd_ = sock;
            return;
        }

        ::close(sock);

        int64_t now_ms = elapsed_ms(start);
        if (now_ms >= TIMEOUT_MS) {
            throw std::runtime_error("sidecar unreachable");
        }

        int delay = delays_ms[std::min(attempt, 6)];
        // Don't sleep longer than remaining budget.
        int64_t remaining = TIMEOUT_MS - now_ms;
        if (delay > remaining) delay = static_cast<int>(remaining);
        std::this_thread::sleep_for(std::chrono::milliseconds(delay));

        if (elapsed_ms(start) >= TIMEOUT_MS) {
            throw std::runtime_error("sidecar unreachable");
        }
    }
}

void SidecarClient::reconnect_() {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
    ensure_connected_();
}

// Write all bytes, retrying on EINTR.
static bool write_all(int fd, const char* buf, size_t len) {
    size_t written = 0;
    while (written < len) {
        ssize_t n;
        do {
            n = ::write(fd, buf + written, len - written);
        } while (n < 0 && errno == EINTR);
        if (n <= 0) return false;
        written += static_cast<size_t>(n);
    }
    return true;
}

// Read until '\n', retrying on EINTR.
static bool read_line(int fd, std::string& out) {
    out.clear();
    char c;
    while (true) {
        ssize_t n;
        do {
            n = ::read(fd, &c, 1);
        } while (n < 0 && errno == EINTR);
        if (n <= 0) return false;
        if (c == '\n') return true;
        out += c;
    }
}

static SidecarResponse parse_response(const std::string& line, int64_t lat_ms) {
    SidecarResponse resp;
    resp.latency_ms = static_cast<int>(lat_ms);

    nlohmann::json j = nlohmann::json::parse(line); // throws parse_error on bad input

    resp.cached_tokens = j.value("cached_tokens", 0);
    resp.prompt_tokens = j.value("prompt_tokens", 0);

    // failure_reason: null or string
    if (!j["failure_reason"].is_null() && j["failure_reason"].get<std::string>() != "") {
        resp.failure_reason = j["failure_reason"].get<std::string>();
        return resp;
    }

    // action field
    if (j.contains("action") && !j["action"].is_null()) {
        auto& a = j["action"];
        std::string atype = a.value("action", "");
        int target = a.value("target", 0);
        if (atype == "move") {
            resp.action = MoveAction{target};
        } else if (atype == "switch") {
            resp.action = SwitchAction{target};
        } else {
            resp.failure_reason = "schema_violation";
        }
    } else {
        resp.failure_reason = "schema_violation";
    }

    return resp;
}

// Validate a selection array: 3 distinct ints all in [0,6).
// Returns "" on success, error string on failure.
static std::string validate_selection(const std::array<int,3>& sel) {
    for (int v : sel) {
        if (v < 0 || v >= 6) return "index_out_of_range";
    }
    if (sel[0] == sel[1] || sel[1] == sel[2] || sel[0] == sel[2]) {
        return "duplicate_indices";
    }
    return "";
}

static SelectionResponse parse_selection_response(const std::string& line, int64_t lat_ms) {
    SelectionResponse resp;
    resp.latency_ms = static_cast<int>(lat_ms);

    nlohmann::json j = nlohmann::json::parse(line); // throws on bad JSON

    // Check explicit failure_reason first
    if (j.contains("failure_reason") && !j["failure_reason"].is_null()) {
        std::string fr = j["failure_reason"].get<std::string>();
        if (!fr.empty()) {
            resp.failure_reason = fr;
            return resp;
        }
    }

    // Parse selection array
    if (!j.contains("selection") || !j["selection"].is_array() ||
        j["selection"].size() != 3) {
        resp.failure_reason = "schema_violation";
        return resp;
    }

    std::array<int,3> sel{};
    for (int i = 0; i < 3; ++i) {
        sel[i] = j["selection"][i].get<int>();
    }

    std::string err = validate_selection(sel);
    if (!err.empty()) {
        resp.failure_reason = err;
        return resp;
    }

    int lead = j.value("lead_idx_in_party", sel[0]);
    // lead must be one of the selected indices
    if (lead != sel[0] && lead != sel[1] && lead != sel[2]) {
        resp.failure_reason = "lead_not_in_selection";
        return resp;
    }

    resp.selection = sel;
    resp.lead_idx_in_party = lead;
    return resp;
}

SidecarResponse SidecarClient::request_action(
    const nlohmann::json& turn_state,
    std::string_view      rulebook_path,
    std::string_view      team_spec,
    std::string_view      idempotency_key,
    int                   timeout_ms)
{
    auto t0 = Clock::now();

    // Build request JSON: server reads a flat object where TurnState fields
    // (rulebook_hash, acting_team, opponent_visible, turn_no, side, legal_actions)
    // are merged at the top level alongside rulebook_path, team_spec, idempotency_key.
    nlohmann::json req = turn_state; // copy all TurnState fields
    req["rulebook_path"]   = rulebook_path;
    req["team_spec"]       = team_spec;
    req["idempotency_key"] = idempotency_key;
    std::string payload = req.dump() + "\n";

    // Set receive timeout on socket.
    auto set_timeout = [&](int fd) {
        struct timeval tv {};
        tv.tv_sec  = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO,
                     reinterpret_cast<const char*>(&tv), sizeof(tv));
    };

    auto do_request = [&](bool allow_retry) -> SidecarResponse {
        ensure_connected_();
        set_timeout(fd_);

        bool ok = write_all(fd_, payload.c_str(), payload.size());
        if (!ok) {
            if (allow_retry) {
                reconnect_();
                set_timeout(fd_);
                ok = write_all(fd_, payload.c_str(), payload.size());
            }
            if (!ok) {
                return SidecarResponse{std::nullopt, "timeout",
                                       static_cast<int>(elapsed_ms(t0)), 0, 0};
            }
        }

        std::string line;
        bool got = read_line(fd_, line);
        if (!got) {
            if (allow_retry) {
                reconnect_();
                set_timeout(fd_);
                ok = write_all(fd_, payload.c_str(), payload.size());
                if (!ok) {
                    return SidecarResponse{std::nullopt, "timeout",
                                           static_cast<int>(elapsed_ms(t0)), 0, 0};
                }
                got = read_line(fd_, line);
            }
            if (!got) {
                return SidecarResponse{std::nullopt, "timeout",
                                       static_cast<int>(elapsed_ms(t0)), 0, 0};
            }
        }

        int64_t lat = elapsed_ms(t0);
        try {
            return parse_response(line, lat);
        } catch (const nlohmann::json::parse_error&) {
            return SidecarResponse{std::nullopt, "parse_fail",
                                   static_cast<int>(lat), 0, 0};
        } catch (...) {
            return SidecarResponse{std::nullopt, "parse_fail",
                                   static_cast<int>(lat), 0, 0};
        }
    };

    return do_request(true);
}

SelectionResponse SidecarClient::request_team_selection(
    const nlohmann::json& selection_state,
    std::string_view      rulebook_path,
    std::string_view      team_spec,
    std::string_view      idempotency_key,
    int                   timeout_ms)
{
    auto t0 = Clock::now();

    // Build request envelope with phase="selection" so sidecar can route it.
    nlohmann::json req = selection_state;
    req["phase"]          = "selection";
    req["rulebook_path"]  = rulebook_path;
    req["team_spec"]      = team_spec;
    req["idempotency_key"] = idempotency_key;
    std::string payload = req.dump() + "\n";

    auto set_timeout = [&](int fd) {
        struct timeval tv {};
        tv.tv_sec  = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO,
                     reinterpret_cast<const char*>(&tv), sizeof(tv));
    };

    auto do_request = [&](bool allow_retry) -> SelectionResponse {
        ensure_connected_();
        set_timeout(fd_);

        bool ok = write_all(fd_, payload.c_str(), payload.size());
        if (!ok) {
            if (allow_retry) {
                reconnect_();
                set_timeout(fd_);
                ok = write_all(fd_, payload.c_str(), payload.size());
            }
            if (!ok) {
                return SelectionResponse{std::nullopt, -1, "timeout",
                                         static_cast<int>(elapsed_ms(t0))};
            }
        }

        std::string line;
        bool got = read_line(fd_, line);
        if (!got) {
            if (allow_retry) {
                reconnect_();
                set_timeout(fd_);
                ok = write_all(fd_, payload.c_str(), payload.size());
                if (!ok) {
                    return SelectionResponse{std::nullopt, -1, "timeout",
                                             static_cast<int>(elapsed_ms(t0))};
                }
                got = read_line(fd_, line);
            }
            if (!got) {
                return SelectionResponse{std::nullopt, -1, "timeout",
                                         static_cast<int>(elapsed_ms(t0))};
            }
        }

        int64_t lat = elapsed_ms(t0);
        try {
            return parse_selection_response(line, lat);
        } catch (const nlohmann::json::parse_error&) {
            return SelectionResponse{std::nullopt, -1, "parse_fail",
                                     static_cast<int>(lat)};
        } catch (...) {
            return SelectionResponse{std::nullopt, -1, "parse_fail",
                                     static_cast<int>(lat)};
        }
    };

    return do_request(true);
}

} // namespace battle
