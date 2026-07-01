"""
Debug entrypoint for the Daily Art bot.
"""

import asyncio
import shutil

import artbot.shared as shared


def configure_debug_runtime() -> None:
    if not shared.DEBUG_SAVED_DATA_PATH.exists() and shared.SAVED_DATA_PATH.exists():
        shutil.copyfile(shared.SAVED_DATA_PATH, shared.DEBUG_SAVED_DATA_PATH)

    shared.DEBUG_MODE = True
    shared.SAVED_DATA_PATH = shared.DEBUG_SAVED_DATA_PATH
    shared.announcement_channel = shared.DEBUG_ANNOUNCEMENT_CHANNEL
    shared.time_deploy = shared.DEBUG_TIME_DEPLOY_MINUTES / 60
    shared.save_data_task.change_interval(minutes=shared.DEBUG_TIME_DEPLOY_MINUTES)


configure_debug_runtime()

from bot import main  # noqa: E402


if __name__ == "__main__":
    asyncio.run(main())
