from dataclasses import dataclass, field
from typing import Any


@dataclass
class DailyState:
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "DailyState":
        return cls(data=data)

    def to_json(self) -> dict[str, Any]:
        return self.data
