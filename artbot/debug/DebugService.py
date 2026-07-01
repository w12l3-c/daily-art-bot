from artbot.AppContext import AppContext


class DebugService:
    def __init__(self, app_context: AppContext) -> None:
        self.app_context = app_context

    @classmethod
    def from_shared(cls) -> "DebugService":
        return cls(AppContext.from_shared())
