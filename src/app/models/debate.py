from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

# --- Literal型定義 ---

Speaker = Literal["persona_a", "persona_b"]

ToolName = Literal["web_search"]

EventType = Literal[
    "turn_start",
    "token",
    "tool_start",
    "tool_end",
    "turn_end",
    "summary_start",
    "summary_token",
    "complete",
    "error",
]


# --- Enum ---


class DebateStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


# --- 内部ドメインモデル（dataclass） ---


@dataclass
class Persona:
    name: str
    description: str


DEFAULT_PERSONA_A = Persona(
    name="賛成派",
    description="議論テーマに対して賛成・肯定的な立場から論理的に主張する",
)
DEFAULT_PERSONA_B = Persona(
    name="反対派",
    description="議論テーマに対して反対・否定的な立場から論理的に主張する",
)


@dataclass
class DebateConfig:
    persona_a: Persona
    persona_b: Persona
    theme: str
    max_turns: int = 2


@dataclass
class ToolCall:
    tool_name: ToolName
    input: dict[str, object]
    output: str


@dataclass
class DebateTurn:
    speaker: Speaker
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class DebateSession:
    session_id: str
    config: DebateConfig
    turns: list[DebateTurn] = field(default_factory=list)
    summary: str | None = None
    status: DebateStatus = DebateStatus.RUNNING


# --- APIスキーマ（Pydantic BaseModel） ---


class PersonaInput(BaseModel):
    name: str = Field(default="", max_length=50)
    description: str = Field(default="", max_length=200)


class DebateStartRequest(BaseModel):
    persona_a: PersonaInput = Field(default_factory=PersonaInput)
    persona_b: PersonaInput = Field(default_factory=PersonaInput)
    theme: str = Field(min_length=1, max_length=200)
    max_turns: int = Field(default=2, ge=1, le=6)


class DebateStartResponse(BaseModel):
    session_id: str


# --- SSEイベントキューの型エイリアス ---

DebateEventQueue = asyncio.Queue[dict[str, object]]
