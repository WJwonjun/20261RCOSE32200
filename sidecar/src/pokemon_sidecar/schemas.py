from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TurnState(BaseModel):
    model_config = {"extra": "allow"}

    rulebook_hash: str
    acting_team: dict
    opponent_visible: dict
    turn_no: int
    side: str
    legal_actions: list


class Action(BaseModel):
    action: Literal["move", "switch"]
    target: int
    reason: str | None = None


class LLMCallResult(BaseModel):
    action: Action | None
    failure_reason: Literal[None, "timeout", "rate_limit", "parse_fail", "schema_violation"] = None
    latency_ms: int
    cached_tokens: int
    prompt_tokens: int
    idempotency_key: str
