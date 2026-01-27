import discord
from discord import app_commands
from datetime import datetime

import shared
from shared import bot, logger, save_data_task
import daily
import wcw
from duel import cleanup_expired_duels


forced_daily = False  

@bot.tree.command(name="force_daily_rollover", description="[ADMIN] Manually trigger send_daily_art_message loop")
async def force_daily_rollover(interaction: discord.Interaction):
    global forced_daily
    """Force the send_daily_art_message task to run immediately (admin/mod only)"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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


@bot.tree.command(name="force_ping_jailed", description="[ADMIN] Manually trigger ping_jailed_users loop")
async def force_ping_jailed(interaction: discord.Interaction):
    """Force the ping_jailed_users task to run immediately (admin/mod only)"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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


@bot.tree.command(name="force_save_daily_data", description="[ADMIN] Manually trigger daily save_data_task loop")
async def force_save_daily_data(interaction: discord.Interaction):
    """Force the daily save_data_task to run immediately"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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


@bot.tree.command(name="force_save_wcw_data", description="[ADMIN] Manually trigger WCW save_data_task loop")
async def force_save_wcw_data(interaction: discord.Interaction):
    """Force the WCW save_data_task to run immediately"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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


@bot.tree.command(name="force_cleanup_duels", description="[ADMIN] Manually trigger cleanup_duels loop")
async def force_cleanup_duels_cmd(interaction: discord.Interaction):
    """Force the cleanup_duels task to run immediately"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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


@bot.tree.command(name="force_warning_1", description="[ADMIN] Send first warning without waiting for scheduled time")
async def force_warning_1(interaction: discord.Interaction):
    """Force the first warning message (normally sent at 10 PM EST)"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        message = daily.build_reminder_message(1)
        channel = bot.get_channel(shared.announcement_channel)
        
        if channel:
            await channel.send(message)
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


@bot.tree.command(name="force_warning_2", description="[ADMIN] Send final warning without waiting for scheduled time")
async def force_warning_2(interaction: discord.Interaction):
    """Force the final warning message (normally sent at 11 PM EST)"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        message = daily.build_reminder_message(2)
        channel = bot.get_channel(shared.announcement_channel)
        
        if channel:
            await channel.send(message)
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


@bot.tree.command(name="debug_event_status", description="[ADMIN] Show current status of daily event tracking")
async def debug_event_status(interaction: discord.Interaction):
    """Show debugging information about daily event state"""
    # Check permissions
    if not shared.has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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
    
    await interaction.response.send_message(status_message, ephemeral=True)
    logger.info(f"Debug event status checked by {interaction.user.name}")
