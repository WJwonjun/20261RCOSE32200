#include <catch2/catch_test_macros.hpp>

#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <atomic>
#include <cstring>
#include <string>
#include <thread>

#include "battle/ipc.hpp"
#include "battle/serialize.hpp"
#include "battle/state.hpp"
#include "battle/team.hpp"
#include "battle/pokemon.hpp"
#include "battle/move.hpp"

using namespace battle;

// Helper: pick a unique temp socket path per test.
static std::string tmp_sock(const char* tag) {
    return std::string("/tmp/test_ipc_") + tag + ".sock";
}

// Helper: build a minimal BattleState with one pokemon per side.
static BattleState minimal_state() {
    BattleState st;
    Pokemon p;
    p.species_id = 1; p.name = "Bulbasaur"; p.level = 50;
    p.type1 = Type::Grass; p.type2 = Type::Poison;
    p.base_stats = {45, 49, 49, 65, 65, 45};
    p.stats      = compute_stats(p.base_stats, p.ivs, p.evs, NATURE_HARDY, 50);
    p.current_hp = p.stats.hp;
    p.move_ids   = {1, 0, 0, 0};
    p.pp         = {35, 0, 0, 0};
    st.team_a.party[0] = p;
    st.team_b.party[0] = p;
    return st;
}

// Tiny mock server: listen on a unix socket, accept one connection,
// read one line, write back `response`, then close.
static void mock_server(const std::string& path, const std::string& response,
                         std::atomic<bool>& ready) {
    ::unlink(path.c_str());
    int srv = ::socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    ::strncpy(addr.sun_path, path.c_str(), sizeof(addr.sun_path) - 1);
    ::bind(srv, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));
    ::listen(srv, 1);
    ready.store(true);

    int cli = ::accept(srv, nullptr, nullptr);
    // drain input line
    char c;
    while (::read(cli, &c, 1) == 1 && c != '\n') {}
    // write response
    if (!response.empty()) {
        ::write(cli, response.c_str(), response.size());
    }
    ::close(cli);
    ::close(srv);
    ::unlink(path.c_str());
}

TEST_CASE("SidecarClient receives valid move action", "[ipc]") {
    const std::string path = tmp_sock("t1");
    const std::string resp =
        R"({"action":{"action":"move","target":0,"reason":"test"},)"
        R"("failure_reason":null,"latency_ms":5,"cached_tokens":0,"prompt_tokens":100})"
        "\n";

    std::atomic<bool> ready{false};
    std::thread srv([&] { mock_server(path, resp, ready); });

    // Wait for server to be listening.
    while (!ready.load()) std::this_thread::sleep_for(std::chrono::milliseconds(5));

    auto st = minimal_state();
    nlohmann::json ts = serialize_turn_state(st, 0);
    nlohmann::json team_spec = serialize_acting_team(st.team_a);

    SidecarClient client(path);
    SidecarResponse r = client.request_action(ts, "rulebook/rulebook.md",
                                               team_spec.dump(), "key1", 5000);
    srv.join();

    REQUIRE(r.action.has_value());
    REQUIRE(std::holds_alternative<MoveAction>(*r.action));
    CHECK(std::get<MoveAction>(*r.action).move_idx == 0);
    CHECK(r.failure_reason.empty());
    CHECK(r.prompt_tokens == 100);
}

TEST_CASE("SidecarClient handles failure_reason=timeout from server", "[ipc]") {
    const std::string path = tmp_sock("t2");
    const std::string resp =
        R"({"action":null,"failure_reason":"timeout","latency_ms":10000,)"
        R"("cached_tokens":0,"prompt_tokens":0})"
        "\n";

    std::atomic<bool> ready{false};
    std::thread srv([&] { mock_server(path, resp, ready); });
    while (!ready.load()) std::this_thread::sleep_for(std::chrono::milliseconds(5));

    auto st = minimal_state();
    nlohmann::json ts = serialize_turn_state(st, 0);
    nlohmann::json team_spec = serialize_acting_team(st.team_a);

    SidecarClient client(path);
    SidecarResponse r = client.request_action(ts, "rulebook/rulebook.md",
                                               team_spec.dump(), "key2", 5000);
    srv.join();

    REQUIRE_FALSE(r.action.has_value());
    CHECK(r.failure_reason == "timeout");
}

TEST_CASE("serialize_acting_team tracks active slot across a switch", "[ipc][serialize]") {
    // Regression: a voluntary switch updates active_idx_in_selection; the
    // serialized is_active flag (driven by active_slot) must follow it.
    BattleState st;

    Pokemon lead;
    lead.species_id = 1; lead.name = "Bulbasaur"; lead.level = 50;
    lead.type1 = Type::Grass; lead.type2 = Type::Poison;
    lead.base_stats = {45, 49, 49, 65, 65, 45};
    lead.stats      = compute_stats(lead.base_stats, lead.ivs, lead.evs, NATURE_HARDY, 50);
    lead.current_hp = lead.stats.hp;
    lead.move_ids   = {1, 0, 0, 0};
    lead.pp         = {35, 0, 0, 0};

    Pokemon bench = lead;
    bench.name = "Ivysaur";

    st.team_a.party[0] = lead;
    st.team_a.party[1] = bench;       // selection[1] target must be alive
    st.team_a.selection = {0, 1, 2};
    st.team_a.active_idx_in_selection = 0;
    st.team_a.active_slot = 0;
    st.team_b.party[0] = lead;        // opponent active alive so battle isn't terminal

    // Before the switch, party[0] is the active mon.
    nlohmann::json before = serialize_acting_team(st.team_a);
    CHECK(before["party"][0]["is_active"] == true);
    CHECK(before["party"][1]["is_active"] == false);

    // Side A switches to selection index 1; B does nothing.
    st.apply_action(SwitchAction{1}, NoAction{});

    CHECK(st.team_a.active_idx_in_selection == 1);
    CHECK(st.team_a.active_slot == 1);

    nlohmann::json after = serialize_acting_team(st.team_a);
    CHECK(after["party"][0]["is_active"] == false);
    CHECK(after["party"][1]["is_active"] == true);
    CHECK(after["active_slot"] == 1);
}

TEST_CASE("SidecarClient times out when server never responds", "[ipc]") {
    const std::string path = tmp_sock("t3");
    // Server accepts but never writes anything.
    std::atomic<bool> ready{false};
    std::thread srv([&] {
        ::unlink(path.c_str());
        int s = ::socket(AF_UNIX, SOCK_STREAM, 0);
        struct sockaddr_un addr{};
        addr.sun_family = AF_UNIX;
        ::strncpy(addr.sun_path, path.c_str(), sizeof(addr.sun_path) - 1);
        ::bind(s, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));
        ::listen(s, 1);
        ready.store(true);
        int cli = ::accept(s, nullptr, nullptr);
        // Drain input but never respond.
        char c;
        while (::read(cli, &c, 1) == 1 && c != '\n') {}
        // Hold connection open briefly then close.
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        ::close(cli);
        ::close(s);
        ::unlink(path.c_str());
    });
    while (!ready.load()) std::this_thread::sleep_for(std::chrono::milliseconds(5));

    auto st = minimal_state();
    nlohmann::json ts = serialize_turn_state(st, 0);
    nlohmann::json team_spec = serialize_acting_team(st.team_a);

    auto t0 = std::chrono::steady_clock::now();
    SidecarClient client(path);
    SidecarResponse r = client.request_action(ts, "rulebook/rulebook.md",
                                               team_spec.dump(), "key3", 200);
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                       std::chrono::steady_clock::now() - t0).count();

    srv.join();

    REQUIRE_FALSE(r.action.has_value());
    CHECK(r.failure_reason == "timeout");
    CHECK(elapsed < 600); // should complete within ~250ms + margin
}
