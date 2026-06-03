from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .prompt import build_messages, build_selection_messages
from .schemas import Action, LLMCallResult, SelectionResult, TurnState

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


CHOOSE_SELECTION_TOOL: dict[str, Any] = {
    "name": "choose_selection",
    "description": "Pick which 3 of your 6 Pokemon to bring to this battle.",
    "input_schema": {
        "type": "object",
        "properties": {
            "selection": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Three distinct party slot indices (0-5), lead first.",
            },
            "lead_idx_in_party": {
                "type": "integer",
                "description": "Party slot of the lead Pokemon (must be one of selection).",
            },
            "reason": {"type": "string"},
        },
        "required": ["selection"],
    },
}


def _party_totals(party: list) -> list[float]:
    totals: list[float] = []
    for p in party:
        s = p.get("stats", {}) if isinstance(p, dict) else {}
        totals.append(sum(float(v) for v in s.values() if isinstance(v, (int, float))))
    return totals


def _valid_selection(sel: Any, party_size: int) -> bool:
    return (
        isinstance(sel, list)
        and len(sel) == 3
        and all(isinstance(i, int) and 0 <= i < party_size for i in sel)
        and len(set(sel)) == 3
    )


def _stub_selection(state: dict, idempotency_key: str) -> SelectionResult:
    """Offline team preview: field the 3 highest-stat-total party members,
    strongest as lead — mirrors the C++ choose_selection heuristic."""
    party = state.get("party", []) if isinstance(state, dict) else []
    if len(party) < 3:
        return SelectionResult(
            selection=None, failure_reason="schema_violation", idempotency_key=idempotency_key
        )
    totals = _party_totals(party)
    ranked = sorted(range(len(party)), key=lambda i: (-totals[i], i))[:3]
    return SelectionResult(
        selection=ranked, lead_idx_in_party=ranked[0], idempotency_key=idempotency_key
    )


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


def _openai_config() -> tuple[str, str, str] | None:
    """(base_url, api_key, model) for an OpenAI-compatible provider, or None.

    Checked before ANTHROPIC_API_KEY so a free key (Gemini/Groq/OpenAI/Ollama)
    takes precedence. The model can always be overridden with
    POKEMON_SIDECAR_MODEL; OPENAI_BASE_URL overrides the endpoint (e.g. Ollama
    at http://localhost:11434/v1)."""
    model = os.environ.get("POKEMON_SIDECAR_MODEL")
    if os.environ.get("GEMINI_API_KEY"):
        return (
            os.environ.get(
                "OPENAI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            ),
            os.environ["GEMINI_API_KEY"],
            model or "gemini-2.0-flash",
        )
    if os.environ.get("GROQ_API_KEY"):
        return (
            os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
            os.environ["GROQ_API_KEY"],
            model or "llama-3.3-70b-versatile",
        )
    if os.environ.get("OPENAI_API_KEY"):
        return (
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            os.environ["OPENAI_API_KEY"],
            model or "gpt-4o-mini",
        )
    return None


def _provider() -> str:
    """Which backend choose_action/choose_selection use this call."""
    if os.environ.get("POKEMON_SIDECAR_STUB") == "1":
        return "stub"
    if _openai_config() is not None:
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "stub"


def _use_stub() -> bool:
    return _provider() == "stub"


def _openai_tool(anthropic_tool: dict) -> dict:
    """Convert an Anthropic tool spec to OpenAI function-tool format."""
    return {
        "type": "function",
        "function": {
            "name": anthropic_tool["name"],
            "description": anthropic_tool.get("description", ""),
            "parameters": anthropic_tool["input_schema"],
        },
    }


def _flatten_messages(system_blocks: list, user_messages: list) -> list[dict]:
    """Collapse Anthropic system blocks + user messages into OpenAI chat msgs."""
    system_text = "\n\n".join(
        b["text"] for b in system_blocks if isinstance(b, dict) and "text" in b
    )
    msgs: list[dict] = [{"role": "system", "content": system_text}]
    for m in user_messages:
        msgs.append({"role": m["role"], "content": m["content"]})
    return msgs


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


class LLMClient:
    def __init__(self) -> None:
        self._client: Any = None
        self._openai: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(timeout=10.0)
        return self._client

    def _get_openai_client(self, base_url: str, api_key: str) -> Any:
        if self._openai is None:
            from openai import AsyncOpenAI
            self._openai = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=15.0)
        return self._openai

    async def _call_tool(
        self, system_blocks: list, user_messages: list, anthropic_tool: dict
    ) -> tuple[dict | None, int, int, str | None]:
        """Force one tool call on the configured provider (OpenAI-compatible if a
        free/OpenAI key is set, else Anthropic). Returns
        (tool_input | None, cached_tokens, prompt_tokens, failure_reason)."""
        tool_name = anthropic_tool["name"]
        cfg = _openai_config()

        for attempt in range(2):
            try:
                if cfg is not None:
                    base_url, api_key, model = cfg
                    client = self._get_openai_client(base_url, api_key)
                    resp = await client.chat.completions.create(
                        model=model,
                        max_tokens=256,
                        messages=_flatten_messages(system_blocks, user_messages),
                        tools=[_openai_tool(anthropic_tool)],
                        tool_choice={"type": "function", "function": {"name": tool_name}},
                    )
                    usage = getattr(resp, "usage", None)
                    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0 if usage else 0
                    details = getattr(usage, "prompt_tokens_details", None)
                    cached_tokens = (getattr(details, "cached_tokens", 0) or 0) if details else 0
                    calls = getattr(resp.choices[0].message, "tool_calls", None)
                    if calls:
                        return json.loads(calls[0].function.arguments), cached_tokens, prompt_tokens, None
                    return None, cached_tokens, prompt_tokens, "parse_fail"
                else:
                    client = self._get_client()
                    resp = await client.messages.create(
                        model=os.environ.get("POKEMON_SIDECAR_MODEL", "claude-haiku-4-5-20251001"),
                        max_tokens=256,
                        system=system_blocks,
                        messages=user_messages,
                        tools=[anthropic_tool],
                        tool_choice={"type": "tool", "name": tool_name},
                    )
                    usage = getattr(resp, "usage", None)
                    cached_tokens = (getattr(usage, "cache_read_input_tokens", 0) or 0) if usage else 0
                    prompt_tokens = (getattr(usage, "input_tokens", 0) or 0) if usage else 0
                    for block in resp.content:
                        if block.type == "tool_use" and block.name == tool_name:
                            return block.input, cached_tokens, prompt_tokens, None
                    return None, cached_tokens, prompt_tokens, "parse_fail"

            except Exception as exc:  # SDK-agnostic classification
                name = type(exc).__name__.lower()
                if "ratelimit" in name:
                    return None, 0, 0, "rate_limit"
                if isinstance(exc, TimeoutError) or "timeout" in name:
                    return None, 0, 0, "timeout"
                if attempt == 0:
                    continue  # transient — retry once
                return None, 0, 0, "parse_fail"

        return None, 0, 0, "parse_fail"

    async def choose_action(
        self,
        turn_state: TurnState,
        rulebook_path: str,
        team_spec: str,
        idempotency_key: str,
    ) -> LLMCallResult:
        if _provider() == "stub":
            return _stub_result(turn_state, idempotency_key)

        rulebook_text = Path(rulebook_path).read_text()
        system_blocks, user_messages = build_messages(
            rulebook_text, team_spec, turn_state.model_dump()
        )

        start = time.monotonic()
        inp, cached_tokens, prompt_tokens, failure_reason = await self._call_tool(
            system_blocks, user_messages, CHOOSE_ACTION_TOOL
        )

        action = None
        if inp is not None:
            try:
                cand = Action(
                    action=inp["action"], target=int(inp["target"]), reason=inp.get("reason")
                )
            except Exception:
                cand = None
            if cand is not None and _is_legal(cand, turn_state.legal_actions):
                action, failure_reason = cand, None
            else:
                # Hallucinated illegal/malformed pick — caller falls back to a
                # legal heuristic action.
                failure_reason = "schema_violation"

        latency_ms = int((time.monotonic() - start) * 1000)
        return LLMCallResult(
            action=action,
            failure_reason=failure_reason,
            latency_ms=latency_ms,
            cached_tokens=cached_tokens,
            prompt_tokens=prompt_tokens,
            idempotency_key=idempotency_key,
        )

    async def choose_selection(
        self,
        selection_state: dict,
        rulebook_path: str,
        team_spec: str,
        idempotency_key: str,
    ) -> SelectionResult:
        """Team preview (6 -> 3): pick which three party slots to field."""
        party_size = len(selection_state.get("party", []))
        if _provider() == "stub":
            return _stub_selection(selection_state, idempotency_key)

        rulebook_text = Path(rulebook_path).read_text()
        system_blocks, user_messages = build_selection_messages(
            rulebook_text, team_spec, selection_state
        )

        start = time.monotonic()
        inp, cached_tokens, prompt_tokens, failure_reason = await self._call_tool(
            system_blocks, user_messages, CHOOSE_SELECTION_TOOL
        )

        selection: list[int] | None = None
        lead: int | None = None
        if inp is not None:
            sel = inp.get("selection")
            if isinstance(sel, list):
                sel = [int(i) for i in sel if isinstance(i, (int, float))]
            parsed_lead = inp.get("lead_idx_in_party")
            if not _valid_selection(sel, party_size):
                failure_reason = "schema_violation"
            else:
                lead = parsed_lead if parsed_lead in sel else sel[0]
                selection = sel
                failure_reason = None

        latency_ms = int((time.monotonic() - start) * 1000)
        return SelectionResult(
            selection=selection,
            lead_idx_in_party=lead,
            failure_reason=failure_reason,
            latency_ms=latency_ms,
            cached_tokens=cached_tokens,
            prompt_tokens=prompt_tokens,
            idempotency_key=idempotency_key,
        )
