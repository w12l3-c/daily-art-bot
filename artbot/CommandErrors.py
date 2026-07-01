from discord import app_commands

import artbot.shared as shared


async def handle_app_command_error(interaction, error: app_commands.AppCommandError) -> None:
    shared.logger.error(f"Command error in {interaction.command}: {error}")

    message = "An unexpected command error occurred."
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) or "You do not have permission to use this command."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"This command is on cooldown. Try again in {error.retry_after:.1f}s."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
