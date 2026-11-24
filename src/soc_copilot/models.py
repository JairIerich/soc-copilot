"""Modelos de domínio independentes dos SDKs de armazenamento e LLM."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: str
    source: str
    record: int
    timestamp: str
    kind: str
    rule_id: str = ""
    level: int = 0
    agent: str = ""
    src_ip: str = ""
    text: str


class Chunk(Event):
    chunk_id: str
    chunk_index: int


class SearchHit(BaseModel):
    chunk: Chunk
    score: float
    vector_score: float = 0
    keyword_score: float = 0


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""
    # Conteúdo opaco para round-trip de assinaturas Gemini e itens Responses.
    native: dict[str, Any] = Field(default_factory=dict, repr=False)


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    provider: str
    model: str
    native: dict[str, Any] = Field(default_factory=dict, repr=False)
    failures: list[str] = Field(default_factory=list)

    def as_message(self) -> Message:
        return Message(
            role="assistant", content=self.content, tool_calls=self.tool_calls, native=self.native
        )


class Citation(BaseModel):
    id: str
    chunk_id: str
    event_id: str
    source: str
    record: int
    timestamp: str
    excerpt: str


class Answer(BaseModel):
    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved: list[Citation] = Field(default_factory=list)
    provider: str
    model: str
    warnings: list[str] = Field(default_factory=list)
    tool_trace: list[str] = Field(default_factory=list)
