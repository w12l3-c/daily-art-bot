import discord
from discord import app_commands
from discord.ext import commands

from artbot.core.chain.ChainService import ChainService


class ChainStartModal(discord.ui.Modal, title="Start Art Chain"):
    def __init__(self, service: ChainService) -> None:
        super().__init__()
        self.service = service
        self.chain_name = discord.ui.TextInput(
            label="Chain name",
            placeholder="sketch relay",
            max_length=80,
        )
        self.amount = discord.ui.TextInput(
            label="Number of submissions",
            placeholder="10",
            max_length=2,
        )
        self.fps = discord.ui.TextInput(
            label="GIF FPS",
            placeholder="1.0",
            default="1.0",
            max_length=4,
            required=False,
        )
        self.add_item(self.chain_name)
        self.add_item(self.amount)
        self.add_item(self.fps)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            amount = int(str(self.amount.value).strip())
            fps = float(str(self.fps.value or "1.0").strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ Chain amount must be a whole number and FPS must be a number.",
                ephemeral=True,
            )
            return

        await self.service.chain_start_command(
            interaction,
            str(self.chain_name.value).strip(),
            amount,
            fps,
        )


class ChainCog(commands.Cog):
    def __init__(self, bot_instance, app_context) -> None:
        self.bot = bot_instance
        self.app_context = app_context
        self.service: ChainService = app_context.chain_service

    @app_commands.command(name="chain_start", description="Start a new art chain collaboration!")
    async def chain_start_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ChainStartModal(self.service))

    @app_commands.command(name="chain_on", description="Join an existing art chain!")
    @app_commands.describe(name="Name of the chain you want to join")
    async def chain_on_command(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        await self.service.chain_on_command(interaction, name)

    @app_commands.command(name="chain_off", description="Stop sending #chain uploads to your selected chain")
    async def chain_off_command(self, interaction: discord.Interaction) -> None:
        await self.service.chain_off_command(interaction)

    @app_commands.command(name="chain_list", description="List all active art chains")
    async def chain_list_command(self, interaction: discord.Interaction) -> None:
        await self.service.chain_list_command(interaction)

    @app_commands.command(name="chain_cancel", description="Cancel an art chain (creator or admin only)")
    @app_commands.describe(name="Name of the chain to cancel")
    async def chain_cancel_command(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        await self.service.chain_cancel_command(interaction, name)


ChainCommands = ChainCog
