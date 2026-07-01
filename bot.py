"""
Production entrypoint for the Daily Art bot.
"""

import asyncio
import signal

from artbot.AppContext import AppContext
from artbot.BotLifecycleCog import BotLifecycleCog
from artbot.cogs import register_cogs
import artbot.shared as shared
from artbot.shared import bot, logger


shutdown_in_progress = False
app_context = AppContext.from_shared()


async def setup_bot() -> None:
    await register_cogs(bot, app_context)


async def persist_runtime_state() -> None:
    lifecycle_cog = bot.get_cog(BotLifecycleCog.__name__)
    if isinstance(lifecycle_cog, BotLifecycleCog):
        await lifecycle_cog.persist_runtime_state()
        return

    try:
        await shared.save_data_task()
    except Exception as e:
        logger.error(f"Error saving daily data during shutdown: {e}")

    try:
        await app_context.wcw_service.save_data()
    except Exception as e:
        logger.error(f"Error saving WCW data during shutdown: {e}")


async def shutdown_bot(signal_name: str) -> None:
    global shutdown_in_progress

    if shutdown_in_progress:
        return

    shutdown_in_progress = True
    logger.info(f"Shutdown requested via {signal_name}")

    await persist_runtime_state()

    if not bot.is_closed():
        await bot.close()


async def main() -> None:
    await setup_bot()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(
                sig,
                lambda sig=sig: asyncio.create_task(shutdown_bot(sig.name)),
            )
        except NotImplementedError:
            pass

    try:
        await bot.start(shared.BOT_TOKEN)
    finally:
        if not shutdown_in_progress:
            await persist_runtime_state()


if __name__ == "__main__":
    asyncio.run(main())
