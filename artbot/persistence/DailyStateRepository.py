import json
from pathlib import Path
from typing import Any


class DailyStateRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        with open(self.path, "r") as f:
            return json.load(f)

    def save(self, data: dict[str, Any]) -> None:
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)
