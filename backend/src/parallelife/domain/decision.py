from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ActionType = Literal["move", "enter", "exit", "interact", "post_sns", "idle", "reply"]


class Destination(BaseModel):
    lat: float
    lon: float


class Decision(BaseModel):
    action: ActionType
    target: str | None = None
    destination: Destination | None = None
    speech: str | None = None
    reply_to_user: str | None = None
    internal_thought: str = Field(default="")
    mood_change: int = Field(default=0, ge=-10, le=10)
    estimated_cost: int = Field(default=0, ge=0)

