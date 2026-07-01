import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

import artbot.shared as shared
from artbot.shared import bot, logger, save_data_task
import artbot.core.daily.DailyService as daily
import artbot.core.wcw.WcwService as wcw
from artbot.core.duel.DuelService import cleanup_expired_duels
from artbot.CommandChecks import requires_admin_or_mod


forced_daily = False


class DebugCog(commands.Cog):
    def __init__(self, bot_instance, app_context) -> None:
        self.bot = bot_instance
        self.app_context = app_context

    @app_commands.command(name="force_daily_rollover", description="[ADMIN] Manually trigger send_daily_art_message loop")
    @requires_admin_or_mod()
    async def force_daily_rollover(self, interaction: discord.Interaction):
        global forced_daily
        """Force the send_daily_art_message task to run immediately (admin/mod only)"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            old_day = shared.current_day
            forced_daily = True
            
            await daily.send_daily_art_message()
            
            await interaction.followup.send(
                f"✅ **Daily rollover task executed!**\n"
                f"Day: {old_day} → {shared.current_day}\n"
                f"Check the announcement channel for results.",
                ephemeral=True
            )
            
            logger.info(f"send_daily_art_message manually triggered by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error forcing daily rollover: {e}")
            await interaction.followup.send(f"❌ Error forcing rollover: {e}", ephemeral=True)
    
        if forced_daily:
            forced_daily = False
    
    
    @app_commands.command(name="force_ping_jailed", description="[ADMIN] Manually trigger ping_jailed_users loop")
    @requires_admin_or_mod()
    async def force_ping_jailed(self, interaction: discord.Interaction):
        """Force the ping_jailed_users task to run immediately (admin/mod only)"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Call the actual task function
            await daily.ping_jailed_users()
            
            await interaction.followup.send(
                f"✅ **ping_jailed_users task executed!**\n"
                f"Check the announcement channel for any warnings sent.",
                ephemeral=True
            )
            
            logger.info(f"ping_jailed_users manually triggered by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error forcing ping_jailed_users: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    
    @app_commands.command(name="force_save_daily_data", description="[ADMIN] Manually trigger daily save_data_task loop")
    @requires_admin_or_mod()
    async def force_save_daily_data(self, interaction: discord.Interaction):
        """Force the daily save_data_task to run immediately"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Call the actual task function
            await shared.save_data_task()
            
            await interaction.followup.send(
                f"✅ **Daily data saved!**\n"
                f"Saved to: `{shared.SAVED_DATA_PATH}`\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ephemeral=True
            )
            
            logger.info(f"daily.save_data_task manually triggered by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error forcing save_data_task: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    
    @app_commands.command(name="force_save_wcw_data", description="[ADMIN] Manually trigger WCW save_data_task loop")
    @requires_admin_or_mod()
    async def force_save_wcw_data(self, interaction: discord.Interaction):
        """Force the WCW save_data_task to run immediately"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Call the actual task function
            await wcw.save_data_task()
            
            await interaction.followup.send(
                f"✅ **WCW data saved!**\n"
                f"Saved to: `{shared.WCW_SAVED_DATA_PATH}`\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ephemeral=True
            )
            
            logger.info(f"wcw.save_data_task manually triggered by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error forcing WCW save_data_task: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    
    @app_commands.command(name="force_cleanup_duels", description="[ADMIN] Manually trigger cleanup_duels loop")
    @requires_admin_or_mod()
    async def force_cleanup_duels_cmd(self, interaction: discord.Interaction):
        """Force the cleanup_duels task to run immediately"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Call the cleanup function directly
            cleaned = await cleanup_expired_duels(bot, shared.allowed_channels, shared.announcement_channel)
            
            await interaction.followup.send(
                f"✅ **Duel cleanup executed!**\n"
                f"Expired duels cleaned: {cleaned}",
                ephemeral=True
            )
            
            logger.info(f"cleanup_duels manually triggered by {interaction.user.name}, cleaned {cleaned} duels")
        except Exception as e:
            logger.error(f"Error forcing cleanup_duels: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    
    @app_commands.command(name="force_warning_1", description="[ADMIN] Send first warning without waiting for scheduled time")
    @requires_admin_or_mod()
    async def force_warning_1(self, interaction: discord.Interaction):
        """Force the first warning message (normally sent at 10 PM EST)"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            messages = daily.build_reminder_message(1)
            channel = bot.get_channel(shared.announcement_channel)
            
            if channel:
                for message in messages:
                    await shared.send_discord_message(channel, message)
                shared.last_warning_1_day = shared.current_day
                await interaction.followup.send(
                    f"✅ **First warning message sent!**\n"
                    f"Sent to: {channel.mention}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Announcement channel {shared.announcement_channel} not found",
                    ephemeral=True
                )
            
            logger.info(f"Warning 1 message manually sent by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error sending warning 1: {e}")
            await interaction.followup.send(f"❌ Error sending warning: {e}", ephemeral=True)
    
    
    @app_commands.command(name="force_warning_2", description="[ADMIN] Send final warning without waiting for scheduled time")
    @requires_admin_or_mod()
    async def force_warning_2(self, interaction: discord.Interaction):
        """Force the final warning message (normally sent at 11 PM EST)"""
        # Check permissions
        await interaction.response.defer(ephemeral=True)
        
        try:
            messages = daily.build_reminder_message(2)
            channel = bot.get_channel(shared.announcement_channel)
            
            if channel:
                for message in messages:
                    await shared.send_discord_message(channel, message)
                shared.last_warning_2_day = shared.current_day
                await interaction.followup.send(
                    f"✅ **Final warning message sent!**\n"
                    f"Sent to: {channel.mention}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Announcement channel {shared.announcement_channel} not found",
                    ephemeral=True
                )
            
            logger.info(f"Warning 2 message manually sent by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error sending warning 2: {e}")
            await interaction.followup.send(f"❌ Error sending warning: {e}", ephemeral=True)
    
    
    @app_commands.command(name="debug_event_status", description="[ADMIN] Show current status of daily event tracking")
    @requires_admin_or_mod()
    async def debug_event_status(self, interaction: discord.Interaction):
        """Show debugging information about daily event state"""
        # Check permissions
        now = shared.now_et()
        
        status_message = (
            f"## 🔍 **Daily Event Debug Status**\n\n"
            f"**Current Time:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"**Current Day:** {shared.current_day}\n"
            f"**Season:** {shared.season} ({shared.season_theme})\n"
            f"**Season Days:** {shared.season_days}\n\n"
            f"**Last Event Tracking:**\n"
            f"• Last daily rollover day: {shared.last_daily_message_day}\n"
            f"• Last warning 1 day: {shared.last_warning_1_day}\n"
            f"• Last warning 2 day: {shared.last_warning_2_day}\n\n"
            f"**User Stats:**\n"
            f"• Tracked users: {len(shared.tracked_users)}\n"
            f"• Archived users: {len(shared.archived_users)}\n"
            f"• Submitted today: {sum(1 for u in shared.tracked_users.values() if u['submission'])}\n"
            f"• Not submitted: {sum(1 for u in shared.tracked_users.values() if not u['submission'])}\n\n"
            f"**Channels:**\n"
            f"• Announcement: <#{shared.announcement_channel}>\n"
            f"• Tracking: {', '.join(f'<#{cid}>' for cid in shared.allowed_channels)}"
        )
        
        await shared.send_interaction_message(interaction, status_message, ephemeral=True)
        logger.info(f"Debug event status checked by {interaction.user.name}")

DebugCommands = DebugCog
