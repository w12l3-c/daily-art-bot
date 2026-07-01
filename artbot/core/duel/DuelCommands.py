import discord
from discord import app_commands
from discord.ext import commands

from artbot.core.duel.DuelService import DuelService


class DuelCog(commands.Cog):
    def __init__(self, bot_instance, app_context) -> None:
        self.bot = bot_instance
        self.app_context = app_context
        self.service: DuelService = app_context.duel_service

    async def duel_type_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.service.duel_type_autocomplete(interaction, current)

    async def user_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.service.user_autocomplete(interaction, current)

    @app_commands.command(name="duel", description="Challenge another user to an art duel!")
    @app_commands.describe(
        opponent="Select the user you want to duel",
        duel_type="Type of duel to challenge",
        period="Duration in days (1-365), or 120 for debug mode (2 minutes)",
        target_time="For time duels: target time in HH:MM format (24-hour)",
    )
    @app_commands.autocomplete(opponent=user_autocomplete, duel_type=duel_type_autocomplete)
    async def duel_challenge_command(
        self,
        interaction: discord.Interaction,
        opponent: str,
        duel_type: str,
        period: int,
        target_time: str = None,
    ) -> None:
        await self.service.duel_challenge_command(
            interaction,
            opponent,
            duel_type,
            period,
            target_time,
        )

    @app_commands.command(name="duel_respond", description="Accept or deny a duel challenge")
    @app_commands.describe(response="Your response to the duel challenge")
    @app_commands.choices(
        response=[
            app_commands.Choice(name="Accept", value="accept"),
            app_commands.Choice(name="Deny", value="deny"),
        ]
    )
    async def duel_respond_command(
        self,
        interaction: discord.Interaction,
        response: app_commands.Choice[str],
    ) -> None:
        await self.service.duel_respond_command(interaction, response.value)

    @app_commands.command(name="duel_status", description="Check your current duel status")
    async def duel_status_command(self, interaction: discord.Interaction) -> None:
        await self.service.duel_status_command(interaction)

    @app_commands.command(name="duel_leaderboard", description="View active duels and leaderboard")
    async def duel_leaderboard_command(self, interaction: discord.Interaction) -> None:
        await self.service.duel_leaderboard_command(interaction)

    @app_commands.command(name="duel_forfeit", description="Forfeit your current active duel")
    async def duel_forfeit_command(self, interaction: discord.Interaction) -> None:
        await self.service.duel_forfeit_command(interaction)


DuelCommands = DuelCog
