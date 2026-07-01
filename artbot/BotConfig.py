from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BotConfig:
    project_root_path: Path
    daily_state_path: Path
    wcw_state_path: Path
    badges_path: Path
    log_path: Path

    @classmethod
    def from_project_root(cls, project_root_path: Path) -> "BotConfig":
        return cls(
            project_root_path=project_root_path,
            daily_state_path=project_root_path / "backup.json",
            wcw_state_path=project_root_path / "wcw.json",
            badges_path=project_root_path / "badges",
            log_path=project_root_path / "bot.log",
        )

    @classmethod
    def from_shared(cls, shared_module) -> "BotConfig":
        return cls(
            project_root_path=shared_module.PROJECT_ROOT_PATH,
            daily_state_path=shared_module.SAVED_DATA_PATH,
            wcw_state_path=shared_module.WCW_SAVED_DATA_PATH,
            badges_path=shared_module.BADGES_PATH,
            log_path=shared_module.LOG_PATH,
        )
