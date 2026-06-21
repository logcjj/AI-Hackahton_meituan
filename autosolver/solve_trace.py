from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SolveTrace:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, event: str, **payload) -> None:
        self.events.append({'event': event, **payload})

    def to_dict(self) -> dict[str, Any]:
        return {'events': list(self.events)}
