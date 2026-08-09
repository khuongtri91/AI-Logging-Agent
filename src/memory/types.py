from typing import Literal

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant"]
IncidentSeverity = Literal["P1", "P2", "P3", "info"]


class ProgressStepRecord(BaseModel):
    """One persisted progress item shown under an assistant message."""

    label: str
    detail: str


class ChatMessageRecord(BaseModel):
    """One persisted chat message."""

    role: ChatRole
    content: str
    steps: list[ProgressStepRecord] = Field(default_factory=list)


class ChatSessionRecord(BaseModel):
    """One persisted chat session payload."""

    user_id: str
    session_id: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageRecord] = Field(default_factory=list)


class IncidentCreateInput(BaseModel):
    """Validated incident data coming from the UI."""

    summary: str
    severity: IncidentSeverity = "P2"
    root_cause: str = ""
    affected_systems: str = ""
    resolution: str = ""
    session_id: str = ""


class IncidentRecord(BaseModel):
    """One persisted incident memory record."""

    id: str
    timestamp: str = ""
    severity: IncidentSeverity = "P2"
    summary: str = ""
    root_cause: str = ""
    affected_systems: str = ""
    resolution: str = ""
    session_id: str = ""
