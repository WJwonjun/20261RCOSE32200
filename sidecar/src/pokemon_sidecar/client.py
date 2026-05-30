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


def _stub_result(turn_state: TurnState, idempotency_key: str) -> LLMCallResult:
    first = turn_state.legal_actions[0] if turn_state.legal_actions else {"action": "move", "target": 0}
    action_type = first.get("action", "move") if isinstance(first, dict) else "move"
    target = first.get("target", 0) if isinstance(first, dict) else 0
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

                action = _parse_tool_call(response)
                if action is not None:
                    failure_reason = None
                    break
                failure_reason = "parse_fail"

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
