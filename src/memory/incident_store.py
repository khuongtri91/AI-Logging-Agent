from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from uuid import uuid4

from src.memory.storage import UserMemoryStorage, read_json_file, write_json
from src.memory.types import IncidentCreateInput, IncidentRecord
from src.utils import P1_SEVERITY, P2_INCIDENT_PROMPT_LIMIT, P2_SEVERITY


class IncidentStore:
    """File-backed incident memory."""

    def __init__(self, storage: UserMemoryStorage | None = None) -> None:
        self.storage = storage or UserMemoryStorage()

    def add(
        self,
        user_id: str,
        incident: IncidentCreateInput,
    ) -> IncidentRecord:
        """Save a new incident summary and return it."""
        incidents = self._load(user_id)
        record = IncidentRecord(
            id=uuid4().hex,
            timestamp=datetime.now().isoformat(),
            severity=incident.severity,
            summary=incident.summary,
            root_cause=incident.root_cause,
            affected_systems=incident.affected_systems,
            resolution=incident.resolution,
            session_id=incident.session_id,
        )
        incidents.append(record)
        self._save(user_id, incidents)
        return record

    def get_all(self, user_id: str) -> list[IncidentRecord]:
        """Return all stored incidents, newest first."""
        return list(reversed(self._load(user_id)))

    def get_recent(self, user_id: str, count: int = 5) -> list[IncidentRecord]:
        """Return the N most recent incidents."""
        if count <= 0:
            return []
        return self.get_all(user_id)[:count]

    def search(self, user_id: str, query: str) -> list[IncidentRecord]:
        """Return incidents whose searchable fields contain the query."""
        normalized_query = query.lower()
        results = []

        for incident in self._load(user_id):
            searchable = " ".join([
                incident.summary,
                incident.root_cause,
                incident.affected_systems,
                incident.resolution,
            ]).lower()
            if normalized_query in searchable:
                results.append(incident)

        return list(reversed(results))

    def count(self, user_id: str) -> int:
        """Return the number of stored incidents for a user."""
        return len(self._load(user_id))

    def get_incidents_for_prompt(self, user_id: str) -> list[IncidentRecord]:
        """Return all P1 incidents and the most recent P2 incidents for prompt context."""
        incidents = self.get_all(user_id)
        p1_incidents = [
            incident
            for incident in incidents
            if incident.severity == P1_SEVERITY
        ]
        p2_incidents = [
            incident
            for incident in incidents
            if incident.severity == P2_SEVERITY
        ]
        return p1_incidents + p2_incidents[:P2_INCIDENT_PROMPT_LIMIT]

    def format_for_prompt(self, incidents: Sequence[IncidentRecord]) -> str:
        """Format incident memory as system-prompt context."""
        if not incidents:
            return ""

        lines = ["PAST INCIDENTS (from long-term memory):\n"]
        for incident in incidents:
            incident_date = incident.timestamp[:10] if incident.timestamp else "unknown date"
            lines.append(
                f"- [{incident.severity}] {incident.summary} "
                f"({incident_date})"
            )
            if incident.root_cause:
                lines.append(f"  Root cause: {incident.root_cause}")
            if incident.resolution:
                lines.append(f"  Resolution: {incident.resolution}")
            lines.append("")

        lines.append(
            "Use this history to identify recurring patterns. "
            "If the current issue matches a past incident, reference it."
        )
        return "\n".join(lines)

    def clear(self, user_id: str) -> None:
        """Delete all incidents for a user."""
        incident_path = self.storage.get_incident_file(user_id)
        if incident_path.exists():
            incident_path.unlink()

    def _load(self, user_id: str) -> list[IncidentRecord]:
        incident_path = self.storage.get_incident_file(user_id)
        data = read_json_file(incident_path, default=[])
        return [IncidentRecord.model_validate(incident) for incident in data]

    def _save(self, user_id: str, incidents: Sequence[IncidentRecord]) -> None:
        incident_path = self.storage.get_incident_file(user_id)
        serialized_incidents = [
            IncidentRecord.model_validate(incident).model_dump(mode="json")
            for incident in incidents
        ]
        write_json(incident_path, serialized_incidents)


@lru_cache
def get_incident_store() -> IncidentStore:
    """Return the shared stateless incident store resource."""
    return IncidentStore()
