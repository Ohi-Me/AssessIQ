"""
Pydantic schemas — strict API contract.
The response schema is NON-NEGOTIABLE per assignment spec.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("user", "assistant", "system"):
            raise ValueError(f"Invalid role: {v}")
        return v


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str         # e.g. "A", "K", "P", "S"
    reason: Optional[str] = None   # why this assessment fits (populated by agent)
    score: Optional[float] = None  # normalized relevance score 0.0–1.0 (from retriever)

    @field_validator("url")
    @classmethod
    def url_must_be_shl(cls, v):
        if v and "shl.com" not in v:
            raise ValueError(f"URL must be from shl.com: {v}")
        return v


class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    end_of_conversation: bool = False

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations_count(cls, v):
        if len(v) > 10:
            raise ValueError("recommendations must have at most 10 items")
        return v


class HealthResponse(BaseModel):
    status: str = "ok"
