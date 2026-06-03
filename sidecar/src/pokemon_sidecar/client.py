from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .prompt import build_messages
from .schemas import Action, LLMCallResult, TurnState

CHOOSE_ACTION_TOOL: dict[str, Any] = {
    "name": "choose_action",
    "description": "Select the action to take this turn.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["move", "switch"]},
            "target": {"type": "integer"},
            "reason": {"type": "string"},
        },
        "required": ["action", "target"],
    },
}


def _active_member(team: dict) -> dict:
    """Return the acting team's active Pokemon dict (or {} if unavailable)."""
    party = team.get("party", []) if isinstance(team, dict) else []
    for p in party:
        if isinstance(p, dict) and p.get("is_active"):
            return p
    return party[0] if party and isinstance(party[0], dict) else {}


def _best_move_target(active: dict, legal: list) -> int | None:
    """Pick the legal move with the highest STAB-weighted power.

    Uses only the data already present in the serialized turn state (each move
    carries `power` and `type`; the active mon carries `type1`/`type2`). Returns
    the move index, or None when no damaging move is legal (forcing the caller
    to fall back to whatever first legal action exists, e.g. a switch)."""
    moves = active.get("moves", []) if isinstance(active, dict) else []
    atk_types = {active.get("type1"), active.get("type2")}
    best_target: int | None = None
    best_score = 0.0
    for a in legal:
        if not isinstance(a, dict) or a.get("action") != "move":
            continue
        idx = a.get("target")
        if not isinstance(idx, int) or idx < 0 or idx >= len(moves):
            continue
        power = moves[idx].get("power") or 0
        if power <= 0:
            continue
        score = float(power)
        if moves[idx].get("type") in atk_types:
            score *= 1.5  # STAB
        if score > best_score:
            best_score = score
            best_target = idx
    return best_target


def _stub_result(turn_state: TurnState, idempotency_key: str) -> LLMCallResult:
    legal = turn_state.legal_actions or []
    first = legal[0] if legal else {"action": "move", "target": 0}
    action_type = first.get("action", "move") if isinstance(first, dict) else "move"
    target = first.get("target", 0) if isinstance(first, dict) else 0

    # Offline policy: instead of blindly taking legal_actions[0] (always move
    # slot 0 -> monotonous battles), choose the highest-power STAB-weighted move
    # from the serialized turn state. Falls back to the first legal action when
    # no damaging move is available (e.g. only status moves, or a forced switch).
    best = _best_move_target(_active_member(turn_state.acting_team), legal)
    if best is not None:
        action_type, target = "move", best

    return LLMCallResult(
        action=Action(action=action_type, target=target, reason="stub"),
        failure_reason=None,
        latency_ms=0,
        cached_tokens=0,
        prompt_tokens=0,
        idempotency_key=idempotency_key,
    )


def _use_stub() -> bool:
    return not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("POKEMON_SIDECAR_STUB") == "1"


def _is_legal(action: Action | None, legal_actions: list) -> bool:
    """True if the action exactly matches one of the turn's legal {action, target}
    pairs. Guards against an LLM hallucinating an out-of-PP move or invalid
    switch target — an illegal pick is treated as a schema violation so the
    caller (C++ demo / loop) falls back to its own legal heuristic."""
    if action is None:
        return False
    for la in legal_actions:
        if (
            isinstance(la, dict)
            and la.get("action") == action.action
            and la.get("target") == action.target
        ):
            return True
    return False


def _parse_tool_call(response: Any) -> Action | None:
    for block in response.content:
        if block.type == "tool_use" and block.name == "choose_action":
            inp = block.input
            return Action(
                action=inp["action"],
                target=int(inp["target"]),
                reason=inp.get("reason"),
            )
    return None


class LLMClient:
    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(timeout=10.0)
        return self._client

    async def choose_action(
        self,
        turn_state: TurnState,
        rulebook_path: str,
        team_spec: str,
        idempotency_key: str,
    ) -> LLMCallResult:
        if _use_stub():
            return _stub_result(turn_state, idempotency_key)

        rulebook_text = Path(rulebook_path).read_text()
        system_blocks, user_messages = build_messages(
            rulebook_text, team_spec, turn_state.model_dump()
        )

        start = time.monotonic()
        failure_reason = None
        action = None
        cached_tokens = 0
        prompt_tokens = 0

        for attempt in range(2):
            try:
                import anthropic

                client = self._get_client()
                response = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=256,
                    system=system_blocks,
                    messages=user_messages,
                    tools=[CHOOSE_ACTION_TOOL],
                    tool_choice={"type": "tool", "name": "choose_action"},
                )

                if hasattr(response, "usage"):
                    cached_tokens = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                    prompt_tokens = getattr(response.usage, "input_tokens", 0) or 0

                parsed = _parse_tool_call(response)
                if parsed is None:
                    action = None
                    failure_reason = "parse_fail"
                elif _is_legal(parsed, turn_state.legal_actions):
                    action = parsed
                    failure_reason = None
                    break
                else:
                    # Parsed but not a legal {action, target} pair (e.g. out-of-PP
                    # move, invalid switch target). Retry once; if it persists the
                    # caller falls back to its own legal heuristic action.
                    action = None
                    failure_reason = "schema_violation"

            except anthropic.RateLimitError:
                failure_reason = "rate_limit"
                break
            except TimeoutError:
                failure_reason = "timeout"
                break
            except Exception:
                failure_reason = "parse_fail"

        latency_ms = int((time.monotonic() - start) * 1000)

        return LLMCallResult(
            action=action,
            failure_reason=failure_reason,
            latency_ms=latency_ms,
            cached_tokens=cached_tokens,
            prompt_tokens=prompt_tokens,
            idempotency_key=idempotency_key,
        )
