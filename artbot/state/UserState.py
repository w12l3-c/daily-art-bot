from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserState:
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return self.data
