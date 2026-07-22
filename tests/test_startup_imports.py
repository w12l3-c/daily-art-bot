import importlib
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch

import discord
from discord.ext import commands

from artbot.AppContext import AppContext
from artbot.cogs import register_cogs


class StartupImportTest(unittest.TestCase):
    def test_entrypoints_import_without_starting_bot(self) -> None:
        importlib.import_module("bot")
        importlib.import_module("bot_debug")

    def test_debug_entrypoint_uses_debug_daily_state(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import bot_debug, bot, artbot.shared as shared; "
                    "print(bot.app_context.config.daily_state_path.name); "
                    "print(shared.SAVED_DATA_PATH.name); "
                    "print(shared.announcement_channel); "
                    "print(shared.DEBUG_MODE); "
                    "print(shared.time_deploy)"
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        lines = result.stdout.strip().splitlines()
        self.assertEqual("backup_debug.json", lines[0])
        self.assertEqual("backup_debug.json", lines[1])
        self.assertEqual("1281049819342831636", lines[2])
        self.assertEqual("True", lines[3])
        self.assertEqual(str(1 / 60), lines[4])

    def test_no_module_level_bot_tree_commands_remain(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        needle = "@bot.tree" + ".command"
        offenders = []
        for path in (source_root / "artbot").rglob("*.py"):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if needle in text:
                offenders.append(str(path.relative_to(source_root)))

        self.assertEqual([], offenders)

    def test_command_permissions_use_decorators(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        command_paths = [
            source_root / "artbot" / "core" / "daily" / "DailyCommands.py",
            source_root / "artbot" / "core" / "wcw" / "WcwCommands.py",
            source_root / "artbot" / "core" / "challenge" / "ChallengeCommands.py",
            source_root / "artbot" / "debug" / "DebugCommands.py",
        ]
        forbidden_patterns = [
            "has_admin_or_mod_permissions(interaction)",
            "wcw.has_perms(interaction.user)",
            "interaction.user.id not in shared.CHALLENGE_MODS",
        ]

        offenders = []
        for path in command_paths:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if pattern in text:
                    offenders.append(f"{path.relative_to(source_root)}: {pattern}")

        self.assertEqual([], offenders)


class CogRegistrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_before_ready_does_not_overwrite_saved_state(self) -> None:
        intents = discord.Intents.default()
        test_bot = commands.Bot(command_prefix="!", intents=intents)
        app_context = AppContext.from_shared()
        app_context.wcw_service.save_data = AsyncMock()
        lifecycle = importlib.import_module("artbot.BotLifecycleCog").BotLifecycleCog(
            test_bot, app_context
        )

        with patch("artbot.shared.save_data_task", new=AsyncMock()) as save_daily:
            await lifecycle.persist_runtime_state()

        save_daily.assert_not_awaited()
        app_context.wcw_service.save_data.assert_not_awaited()

    async def test_register_cogs_adds_expected_commands(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        test_bot = commands.Bot(command_prefix="!", intents=intents)
        app_context = AppContext.from_shared()

        await register_cogs(test_bot, app_context)

        command_names = {command.name for command in test_bot.tree.get_commands()}
        expected_names = {
            "add_user",
            "daily_status_edit",
            "wcw_join",
            "wcw_edit_week",
            "challenge_start",
            "duel",
            "chain_start",
            "chain_off",
            "force_daily_rollover",
        }
        self.assertTrue(expected_names.issubset(command_names))

        removed_names = {
            "debug",
            "list_channels",
            "get_announcement_channel",
            "set_season_theme",
            "set_season_days",
            "set_current_day",
            "set_season_number",
            "find_submissions",
        }
        self.assertTrue(command_names.isdisjoint(removed_names))

        duel_command = next(command for command in test_bot.tree.get_commands() if command.name == "duel")
        duel_parameters = [param.name for param in duel_command.parameters]
        self.assertEqual(["opponent", "duel_type", "period", "target_time"], duel_parameters)

    async def test_register_cogs_is_idempotent(self) -> None:
        intents = discord.Intents.default()
        test_bot = commands.Bot(command_prefix="!", intents=intents)
        app_context = AppContext.from_shared()

        await register_cogs(test_bot, app_context)
        await register_cogs(test_bot, app_context)

        command_names = [command.name for command in test_bot.tree.get_commands()]
        self.assertEqual(len(command_names), len(set(command_names)))


if __name__ == "__main__":
    unittest.main()
