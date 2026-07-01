from dataclasses import dataclass, field
from typing import Any


@dataclass
class WcwState:
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "WcwState":
        return cls(data=data)

    def to_json(self) -> dict[str, Any]:
        return self.data
