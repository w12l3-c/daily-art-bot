import asyncio
import json

from discord.ext import commands, tasks

from artbot.AppContext import AppContext
import artbot.core.daily.DailyService as daily
import artbot.shared as shared
from artbot.shared import logger


class BotLifecycleCog(commands.Cog):
    def __init__(self, bot_instance, app_context: AppContext) -> None:
        self.bot = bot_instance
        self.app_context = app_context
        self.started = False
        # Do not overwrite persisted state if Discord login fails before on_ready
        # has had a chance to load it.
        self.state_initialized = False

    def cog_unload(self) -> None:
        self._stop_loop(daily.send_daily_art_message)
        self._stop_loop(shared.save_data_task)
        self._stop_loop(daily.ping_jailed_users)
        self._stop_loop(self.cleanup_duels)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(f"We have logged in as {self.bot.user}")
        logger.info(f"Bot logged in as {self.bot.user}")

        if self.started:
            logger.info("Bot lifecycle already started; skipping startup work.")
            return

        self.started = True
        try:
            self.load_data()
            self.state_initialized = True
            self.app_context.duel_service.set_tracked_users_reference(shared.tracked_users)
            self.app_context.chain_service.set_tracked_users_reference(shared.tracked_users)

            await asyncio.sleep(1)
            synced = await self.bot.tree.sync()
            print(f"Synced {len(synced)} commands.")
            logger.info(f"Synced {len(synced)} commands.")
        except Exception as e:
            print(f"Error in on_ready: {e}")
            logger.error(f"Error in on_ready: {e}")

        self._start_loop(daily.send_daily_art_message)
        self._start_loop(shared.save_data_task)
        self._start_loop(daily.ping_jailed_users)
        self._start_loop(self.cleanup_duels)

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if message.author == self.bot.user:
            return

        if message.channel.id in shared.allowed_channels:
            await self.app_context.daily_service.on_message_daily(message)

        if message.channel.id in shared.wcw_allowed_channels:
            await self.app_context.wcw_service.on_message_wcw(message)

        await self.bot.process_commands(message)

    @tasks.loop(hours=shared.time_deploy)
    async def cleanup_duels(self) -> None:
        try:
            cleaned = await self.app_context.duel_service.cleanup_expired_duels(
                self.bot,
                shared.allowed_channels,
                shared.announcement_channel,
            )
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired duels")
        except Exception as e:
            logger.error(f"Error cleaning up duels: {e}")

    async def persist_runtime_state(self) -> None:
        if not self.state_initialized:
            logger.warning(
                "Skipping shutdown save because persisted state was never loaded."
            )
            return

        try:
            await shared.save_data_task()
        except Exception as e:
            logger.error(f"Error saving daily data during shutdown: {e}")

        try:
            await self.app_context.wcw_service.save_data()
        except Exception as e:
            logger.error(f"Error saving WCW data during shutdown: {e}")

    def load_data(self) -> None:
        try:
            data = self.app_context.daily_state_repository.load()
            shared.guild_id = data.get("guild_id", shared.guild_id)
            shared.current_day = data.get("current_day", shared.current_day)
            shared.season = data.get("season", shared.season)
            shared.season_days = data.get("season_days", shared.season_days)
            shared.season_theme = data.get("season_theme", shared.season_theme)
            loaded_users = data.get("tracked_users", {})
            loaded_archived = data.get("archived_users", {})
            shared.announcement_channel = data.get(
                "announcement_channel",
                shared.allowed_channels[0] if shared.allowed_channels else shared.announcement_channel,
            )
            if shared.DEBUG_MODE:
                shared.announcement_channel = shared.DEBUG_ANNOUNCEMENT_CHANNEL
            shared.challenge_day = data.get("challenge_day", shared.challenge_day)
            shared.challenge_length = data.get("challenge_length", shared.challenge_length)
            shared.challenge_theme = data.get("challenge_theme", shared.challenge_theme)
            shared.challenge_number = data.get("challenge_number", shared.challenge_number)

            loaded_allowed_channels = data.get("allowed_channels", shared.allowed_channels)
            if loaded_allowed_channels:
                shared.allowed_channels = loaded_allowed_channels

            shared.tracked_users = {}
            for user_id_str, user_data in loaded_users.items():
                try:
                    shared.tracked_users[int(user_id_str)] = user_data
                except ValueError:
                    logger.warning(f"Could not convert user ID '{user_id_str}' to integer")

            shared.archived_users = {}
            for user_id_str, user_data in loaded_archived.items():
                try:
                    shared.archived_users[int(user_id_str)] = user_data
                except ValueError:
                    logger.warning(f"Could not convert archived user ID '{user_id_str}' to integer")

            self.app_context.duel_service.load_duel_data(data.get("duel", None))
            self.app_context.chain_service.load_chain_data(data.get("chain", None))

            print(f"Data loaded successfully! (Day {shared.current_day}, Season {shared.season})")
            logger.info(f"Data loaded successfully! (Day {shared.current_day}, Season {shared.season})")
            logger.info(f"Loaded {len(shared.tracked_users)} users with IDs: {list(shared.tracked_users.keys())}")
            logger.info(f"Announcement channel set to: {shared.announcement_channel}")
            logger.info(f"Allowed channels: {shared.allowed_channels}")
        except (FileNotFoundError, json.JSONDecodeError):
            print("No save file found. Starting fresh.")
            logger.warning("No save file found. Starting fresh.")
            shared.current_day = 1
            shared.season = 7
            shared.tracked_users = {}
            shared.announcement_channel = shared.allowed_channels[0] if shared.allowed_channels else None
            if shared.DEBUG_MODE:
                shared.announcement_channel = shared.DEBUG_ANNOUNCEMENT_CHANNEL
            self.app_context.duel_service.load_duel_data(None)
            self.app_context.chain_service.load_chain_data(None)

        try:
            data = self.app_context.wcw_state_repository.load()
            shared.wcw_current_week = data.get("current_week", shared.wcw_current_week)
            loaded_users = data.get("tracked_users", {})
            shared.wcw_announcement_channel = data.get(
                "announcement_channel",
                shared.wcw_allowed_channels[0] if shared.wcw_allowed_channels else None,
            )
            shared.wcw_last_message_week = data.get("last_message_week", shared.wcw_last_message_week)
            shared.wcw_last_reminder_1_week = data.get(
                "last_reminder_1_week",
                shared.wcw_last_reminder_1_week,
            )
            shared.wcw_last_reminder_2_week = data.get(
                "last_reminder_2_week",
                shared.wcw_last_reminder_2_week,
            )

            loaded_allowed_channels = data.get("allowed_channels", shared.wcw_allowed_channels)
            if loaded_allowed_channels:
                shared.wcw_allowed_channels = loaded_allowed_channels

            shared.wcw_tracked_users = {}
            for user_id_str, user_data in loaded_users.items():
                try:
                    shared.wcw_tracked_users[int(user_id_str)] = user_data
                except ValueError:
                    logger.warning(f"Could not convert user ID '{user_id_str}' to integer")

            print(f"WCW data loaded successfully! (Week {shared.wcw_current_week})")
            logger.info(f"WCW data loaded successfully! (Week {shared.wcw_current_week})")
            logger.info(f"Loaded {len(shared.wcw_tracked_users)} users with IDs: {list(shared.wcw_tracked_users.keys())}")
            logger.info(f"WCW announcement channel set to: {shared.wcw_announcement_channel}")
            logger.info(f"WCW allowed channels: {shared.wcw_allowed_channels}")
        except (FileNotFoundError, json.JSONDecodeError):
            print("No WCW save file found. Starting fresh.")
            logger.warning("No WCW save file found. Starting fresh.")
            shared.wcw_current_week = 10
            shared.wcw_tracked_users = {}
            shared.wcw_announcement_channel = shared.wcw_allowed_channels[0] if shared.wcw_allowed_channels else None

    def _start_loop(self, loop) -> None:
        if not loop.is_running():
            loop.start()

    def _stop_loop(self, loop) -> None:
        if loop.is_running():
            loop.stop()
