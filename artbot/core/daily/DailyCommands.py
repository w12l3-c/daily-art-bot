"""
commands.py
This file contains implementations of Discord command functions
"""

import discord
from discord import app_commands
from discord.ext import commands
import os
import io
from artbot.core.daily.DailyService import reset_user_stats, build_reminder_message
import artbot.shared as shared
from artbot.shared import bot, logger
from collections import deque
from artbot.CommandChecks import requires_admin_or_mod


class DailyStatusEditModal(discord.ui.Modal, title="Edit Daily Status"):
    def __init__(self) -> None:
        super().__init__()
        self.season_number = discord.ui.TextInput(
            label="Season number",
            default=str(shared.season),
            max_length=4,
        )
        self.season_theme = discord.ui.TextInput(
            label="Season theme",
            default=shared.season_theme,
            max_length=100,
        )
        self.current_day = discord.ui.TextInput(
            label="Current day",
            default=str(shared.current_day),
            max_length=4,
        )
        self.season_days = discord.ui.TextInput(
            label="Season days",
            default=str(shared.season_days),
            max_length=4,
        )
        self.add_item(self.season_number)
        self.add_item(self.season_theme)
        self.add_item(self.current_day)
        self.add_item(self.season_days)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            season_number = int(str(self.season_number.value).strip())
            current_day = int(str(self.current_day.value).strip())
            season_days = int(str(self.season_days.value).strip())
        except ValueError:
            await interaction.response.send_message(
                "Season number, current day, and season days must be whole numbers.",
                ephemeral=True,
            )
            return

        season_theme = str(self.season_theme.value).strip()
        if season_number < 1 or current_day < 1 or season_days < 1:
            await interaction.response.send_message(
                "Season number, current day, and season days must be at least 1.",
                ephemeral=True,
            )
            return
        if not season_theme:
            await interaction.response.send_message("Season theme cannot be empty.", ephemeral=True)
            return
        if current_day > season_days:
            await interaction.response.send_message(
                f"Current day ({current_day}) cannot be greater than season days ({season_days}).",
                ephemeral=True,
            )
            return

        old_status = (
            shared.season,
            shared.season_theme,
            shared.current_day,
            shared.season_days,
        )
        shared.season = season_number
        shared.season_theme = season_theme
        shared.current_day = current_day
        shared.season_days = season_days

        await interaction.response.send_message(
            "Daily status updated:\n"
            f"Season: {old_status[0]} -> {shared.season}\n"
            f"Theme: {old_status[1]} -> {shared.season_theme}\n"
            f"Current day: {old_status[2]} -> {shared.current_day}\n"
            f"Season days: {old_status[3]} -> {shared.season_days}",
            ephemeral=True,
        )
        logger.info(
            "Daily status edited by %s: season=%s theme=%s current_day=%s season_days=%s",
            interaction.user.name,
            shared.season,
            shared.season_theme,
            shared.current_day,
            shared.season_days,
        )


class DailyCog(commands.Cog):
    def __init__(self, bot_instance, app_context) -> None:
        self.bot = bot_instance
        self.app_context = app_context

    @app_commands.command(name="add_channel", description="Add a channel by ID for tracking art submissions.")
    @app_commands.describe(channel_id="Enter the channel ID as text")
    @requires_admin_or_mod()
    async def add_channel(self, interaction: discord.Interaction, channel_id: str):
        # Check if user has admin permissions or mod role
        # Convert string to int and validate
        try:
            channel_id_int = int(channel_id.strip())
            if channel_id_int <= 0:
                raise ValueError("Channel ID must be positive")
        except ValueError:
            await interaction.response.send_message("❌ Invalid channel ID. Please enter a valid positive number.", ephemeral=True)
            return

        # Check if channel exists
        channel = bot.get_channel(channel_id_int)

        if channel_id_int not in shared.allowed_channels:
            shared.allowed_channels.append(channel_id_int)
            channel_name = f" ({channel.name})" if channel else ""
            warning = ""
            if not channel:
                warning = " Bot could not access this channel yet; make sure it has permissions there."
            await interaction.response.send_message(
                f"✅ Channel {channel_id_int}{channel_name} added to allowed channels!{warning}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(f"⚠️ Channel {channel_id_int} is already in the allowed list.", ephemeral=True)
    
    @app_commands.command(name="remove_channel", description="Remove a channel from tracking.")
    @app_commands.describe(channel_id="Enter the channel ID")
    @requires_admin_or_mod()
    async def remove_channel(self, interaction: discord.Interaction, channel_id: str):
        # Check if user has admin permissions or mod role
        # Convert string to int and validate
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            await interaction.response.send_message("❌ Invalid channel ID. Please enter a valid number.", ephemeral=True)
            return
            
        if channel_id_int in shared.allowed_channels:
            shared.allowed_channels.remove(channel_id_int)
            await interaction.response.send_message(f"✅ Channel {channel_id_int} removed from allowed channels!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Channel {channel_id_int} not found in the allowed list.", ephemeral=True)
    
    @app_commands.command(name="set_announcement_channel", description="Set announcement channel by ID.")
    @app_commands.describe(channel_id="Enter the channel or thread ID as text")
    @requires_admin_or_mod()
    async def set_announcement_channel(self, interaction: discord.Interaction, channel_id: str):
        # Check if user has admin permissions or mod role
        # Convert string to int and validate
        try:
            channel_id_int = int(channel_id.strip())
            if channel_id_int <= 0:
                raise ValueError("Channel ID must be positive")
        except ValueError:
            await interaction.response.send_message("❌ Invalid channel ID. Please enter a valid positive number.", ephemeral=True)
            return

        # Check if channel/thread exists
        channel = bot.get_channel(channel_id_int)
        if channel:
            # Validate it's a text channel or thread
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                shared.announcement_channel = channel_id_int
                channel_type = "Thread" if isinstance(channel, discord.Thread) else "Channel"
                await interaction.response.send_message(f"✅ Announcement {channel_type.lower()} set to {channel.mention} ({channel.name})!\n"
                                                    f"Daily messages and season results will be posted here.", ephemeral=True)
                logger.info(f"Announcement channel set to {channel_id_int} ({channel.name}) by {interaction.user.name}")
            else:
                await interaction.response.send_message("❌ Only text channels and threads are supported for announcements.", ephemeral=True)
        else:
            # Channel not found - might be a thread the bot can't see, or from another server
            await interaction.response.send_message(f"⚠️ Channel/thread with ID {channel_id_int} not found or bot doesn't have access. Setting anyway...\n"
                                                f"Make sure the bot has permissions to post in that channel/thread.", ephemeral=True)
            shared.announcement_channel = channel_id_int
            logger.warning(f"Announcement channel set to unknown ID {channel_id_int} by {interaction.user.name}")
    
    @app_commands.command(name="channel_info", description="Show tracking and announcement channel information.")
    async def channel_info(self, interaction: discord.Interaction):
        info_message = "## 📋 **Channel Configuration**\n\n"
        
        # Tracking channels
        if shared.allowed_channels:
            info_message += "**🎨 Art Tracking Channels:**\n"
            for channel_id in shared.allowed_channels:
                channel = bot.get_channel(channel_id)
                channel_name = f" ({channel.name})" if channel else " (not accessible)"
                info_message += f"• <#{channel_id}>{channel_name}\n"
        else:
            info_message += "**🎨 Art Tracking Channels:** None\n"
        
        # Announcement channel
        info_message += "\n**📢 Announcement Channel:**\n"
        if shared.announcement_channel:
            channel = bot.get_channel(shared.announcement_channel)
            channel_name = f" ({channel.name})" if channel else " (not accessible)"
            info_message += f"• <#{shared.announcement_channel}>{channel_name}\n"
        else:
            info_message += "• None set\n"
        
        info_message += "\n**ℹ️ How it works:**\n"
        info_message += "• Art can be submitted in any tracking channel\n"
        info_message += "• Daily messages and results post to announcement channel only\n"
        info_message += "• Bot responds to art submissions in the same channel they were posted"
        
        await shared.send_interaction_message(interaction, info_message)
    
    @app_commands.command(name="add_user", description="Add a user to the art tracking system.")
    @app_commands.describe(user="Select a user")
    @requires_admin_or_mod()
    async def add_user(self, interaction: discord.Interaction, user: discord.User):
        # Check if user has admin permissions or mod role
        member = await interaction.guild.fetch_member(user.id)
        user_nickname = member.nick if member and member.nick else user.name
        if user.id not in shared.tracked_users:
            shared.tracked_users[user.id] = shared.get_default_user_values(username = user.name, user_nickname=user_nickname)
            await interaction.response.send_message(f"✅ {user.name} added to the tracking list!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {user.name} is already being tracked.", ephemeral=True)
    
    @app_commands.command(name="remove_user", description="Remove a user from tracking.")
    @app_commands.describe(user="Select a user")
    @requires_admin_or_mod()
    async def remove_user(self, interaction: discord.Interaction, user: discord.User):
        # Check if user has admin permissions or mod role
        if user.id in shared.tracked_users:
            del shared.tracked_users[user.id]
            await interaction.response.send_message(f"✅ {user.name} removed from tracking!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ User not found in tracking.")
    
    @app_commands.command(name="join_daily", description="Join the daily art tracking system yourself!")
    async def join_tracking(self, interaction: discord.Interaction):
        user = interaction.user
        member = await interaction.guild.fetch_member(user.id)
        user_nickname = member.nick if member and member.nick else user.name
        
        # Restore archived stats if the user left before
        if user.id not in shared.tracked_users:
            restored = False
            if user.id in shared.archived_users:
                shared.tracked_users[user.id] = shared.archived_users.pop(user.id)
                restored = True
            else:
                shared.tracked_users[user.id] = shared.get_default_user_values(username=user.name, user_nickname=user_nickname)
            msg = "🎨 Welcome back! Your stats have been restored." if restored else "🎨 Welcome to daily art tracking!"
            await interaction.response.send_message(f"{msg} {user_nickname}, you're now tracked for daily submissions and duels.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ You're already being tracked in the daily art system!", ephemeral=True)
    
    @app_commands.command(name="leave_daily", description="Leave the daily art tracking system.")
    async def leave_tracking(self, interaction: discord.Interaction):
        user = interaction.user
        
        if user.id in shared.tracked_users:
            # Show final stats before leaving
            user_data = shared.tracked_users[user.id]
            stats_message = (
                f"📊 **Your Final Stats:**\n"
                f"🎨 Parole Days: {user_data.get('parole_days', 0)}\n"
                f"💀 Deceased Days: {user_data.get('deceased_days', 0)}\n"
                f"📅 Missing Days: {user_data.get('missing_days', 0)}\n"
                f"🔄 Revivals: {user_data.get('revival', 0)}\n"
                f"🛑 Buffer Art: {user_data.get('buffer', 0)}\n"
                f"⚔️ Duels Won: {user_data.get('duels_won', 0)}\n"
                f"⚔️ Duels Lost: {user_data.get('duels_lost', 0)}\n\n"
                f"Thanks for participating in daily art tracking! You can rejoin anytime with `/join`."
            )
    
            # Archive stats instead of deleting so rejoin restores progress
            shared.archived_users[user.id] = user_data
            del shared.tracked_users[user.id]
            await shared.send_interaction_message(interaction, stats_message, ephemeral=True)
        else:
            await interaction.response.send_message("❌ You're not currently being tracked in the daily art system.", ephemeral=True)
    
    @app_commands.command(name="list_users", description="List all users being tracked.")
    @requires_admin_or_mod()
    async def list_users(self, interaction: discord.Interaction):
        # Check if user has admin permissions or mod role
        if not shared.tracked_users:
            await interaction.response.send_message("⚠️ No users are currently being tracked.", ephemeral=True)
        else:
            users = "\n".join([f"{user['username']} - {user['user_nickname']}" for user in shared.tracked_users.values()])
            await shared.send_interaction_message(interaction, f"**Tracked Users:**\n{users}")
    
    @app_commands.command(name="list_attributes", description="List all available user attributes.")
    @requires_admin_or_mod()
    async def list_attributes(self, interaction: discord.Interaction):
        # Check if user has admin permissions or mod role
        logger.info(f"list_attributes command called by {interaction.user.name}")
        if shared.tracked_users:
            sample_user = next(iter(shared.tracked_users.values()))
            attributes = list(sample_user.keys())
        else:
            attributes = [
                "username", "user_nickname", "submission", "parole_days", "deceased",
                "deceased_days", "missing_days", "consecutive_missed_days", "revival", "buffer", "probation", "ping",
                "duels_won", "duels_lost"
            ]
    
        formatted = "\n".join(f"- {attr}" for attr in attributes)
        await shared.send_interaction_message(
            interaction,
            "**Available User Attributes:**\n" + formatted,
            ephemeral=True,
        )
    
    @app_commands.command(name="query_user", description="Check a user's submission stats.")
    @app_commands.describe(user="Select a user")
    async def query_user(self, interaction: discord.Interaction, user: discord.User):
        if user.id in shared.tracked_users:
            u = shared.tracked_users[user.id]
            message = (
                f"**User:** {u['username']}\n"
                f"**🔗 User Nickname: {u['user_nickname']}**\n"
                f"📌 Submission: {shared.get_submission_link(user.id)}\n"
                f"🛑 Buffer: {u['buffer']}\n"
                f"⏳ Parole Days: {u['parole_days']}\n"
                f"💀 Deceased: {u['deceased']} ({u['deceased_days']} days)\n"
                f"🚫 Missing Days: {u['missing_days']}\n"
                f"💔 Consecutive Missed: {u.get('consecutive_missed_days', 0)} days\n"
                f"🚀 Revivals: {u['revival']}\n"
                f"🔒 Probation: {u['probation']}\n"
                f"🔔 Ping Notifications: {u['ping']}\n"
                f"⚔️ Duels Won: {u.get('duels_won', 0)}\n"
                f"💔 Duels Lost: {u.get('duels_lost', 0)}\n"
            )
            await shared.send_interaction_message(interaction, message)
        else:
            await interaction.response.send_message("❌ User not found in tracking.")
    
    async def attribute_autocomplete(self, 
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for user attributes"""
        # Get all possible attributes
        if shared.tracked_users:
            # Get attributes from an existing user
            sample_user = next(iter(shared.tracked_users.values()))
            attributes = list(sample_user.keys())
        else:
            # Fallback to default attributes
            attributes = [
                "username", "user_nickname", "submission", "parole_days", "deceased",
                "deceased_days", "missing_days", "revival", "buffer", "probation", "ping",
                "duels_won", "duels_lost"
            ]
        
        # Filter attributes based on what the user is typing
        current_lower = current.lower()
        filtered_attributes = [
            attr for attr in attributes 
            if current_lower in attr.lower()
        ]
        
        # Discord only allows 25 choices maximum
        filtered_attributes = filtered_attributes[:25]
        
        # Return as Choice objects with descriptions
        choices = []
        for attr in filtered_attributes:
            # Add type hints in the description
            if shared.tracked_users:
                sample_user = next(iter(shared.tracked_users.values()))
                attr_value = sample_user.get(attr)
                attr_type = type(attr_value).__name__
                description = f"Type: {attr_type}"
                if isinstance(attr_value, bool):
                    description += " (use 'true' or 'false')"
                choices.append(app_commands.Choice(name=f"{attr} - {description}", value=attr))
            else:
                choices.append(app_commands.Choice(name=attr, value=attr))
        
        return choices
    
    async def value_autocomplete(self, 
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for values based on the selected attribute"""
        # Try to get the attribute from the interaction
        try:
            # Get the attribute parameter if it exists
            attribute = None
            for option in interaction.data.get('options', []):
                if option.get('name') == 'attribute':
                    attribute = option.get('value')
                    break
            
            if not attribute or not shared.tracked_users:
                return []
            
            # Get a sample user to check the attribute type
            sample_user = next(iter(shared.tracked_users.values()))
            if attribute not in sample_user:
                return []
                
            attr_value = sample_user[attribute]
            
            # Provide suggestions based on type
            if isinstance(attr_value, bool):
                suggestions = ['true', 'false']
            elif isinstance(attr_value, int):
                # Suggest some common numbers
                suggestions = ['0', '1', '5', '10']
            else:
                # For strings, can't really predict, return empty
                return []
            
            # Filter based on current input
            current_lower = current.lower()
            filtered = [s for s in suggestions if current_lower in s.lower()]
            
            return [app_commands.Choice(name=value, value=value) for value in filtered]
            
        except Exception:
            return []
    
    @app_commands.command(name="edit_user", description="Edit a user's attribute.")
    @app_commands.describe(user="Select a user", attribute="Attribute to change", value="New value")
    @app_commands.autocomplete(attribute=attribute_autocomplete, value=value_autocomplete)
    @requires_admin_or_mod()
    async def edit_user(self, interaction: discord.Interaction, user: discord.User, attribute: str, value: str = ""):
        # Check if user has admin permissions or mod role
        logger.info(f"edit_user called: user_id={user.id} (type: {type(user.id)}), attribute={attribute}, value={value}")
        logger.info(f"shared.tracked_users keys: {list(shared.tracked_users.keys())} (types: {[type(k) for k in shared.tracked_users.keys()]})")
        
        # Check if user exists
        if user.id not in shared.tracked_users:
            await interaction.response.send_message(f"❌ User {user.name} not found in tracking.")
            logger.warning(f"User {user.name} (ID: {user.id}) not found in shared.tracked_users")
            return
        
        # Check if attribute exists
        if attribute not in shared.tracked_users[user.id]:
            available_attrs = list(shared.tracked_users[user.id].keys())
            await interaction.response.send_message(f"❌ Attribute '{attribute}' not found. Available attributes: {available_attrs}")
            logger.warning(f"Attribute '{attribute}' not found for user {user.name}. Available: {available_attrs}")
            return
        
        old_value = shared.tracked_users[user.id][attribute]
        try:
            if isinstance(old_value, bool):
                value = value.lower() == 'true'
            elif isinstance(old_value, int):
                value = int(value)
    
            shared.tracked_users[user.id][attribute] = value
            await interaction.response.send_message(f"✅ {shared.tracked_users[user.id]['user_nickname']}'s `{attribute}` changed from `{old_value}` to `{value}`")
            logger.info(f"Successfully updated {user.name}'s {attribute} from {old_value} to {value}")
        except ValueError:
            await interaction.response.send_message("⚠️ Invalid value type.")
            logger.error(f"Invalid value type when editing user {user.name}'s {attribute} to {value}")
    
    @app_commands.command(name="sync_commands", description="Force sync all slash commands (Admin only).")
    @requires_admin_or_mod()
    async def sync_commands(self, interaction: discord.Interaction):
        # Check if user has admin permissions or mod role
        # Defer the response to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Try guild-specific sync first (faster)
            guild = interaction.guild
            await interaction.followup.send("🔄 Syncing commands to this server...", ephemeral=True)
            synced = await bot.tree.sync(guild=guild)
            await interaction.followup.send(f"✅ Successfully synced {len(synced)} commands to this server!", ephemeral=True)
            logger.info(f"Commands manually synced to guild {guild.name} by {interaction.user.name}: {len(synced)} commands")
        except Exception as e:
            await interaction.followup.send(f"❌ Error syncing commands: {e}", ephemeral=True)
            logger.error(f"Error manually syncing commands: {e}")
    
    @app_commands.command(name="sync_global", description="Force sync commands globally (Admin only, slower).")
    @requires_admin_or_mod()
    async def sync_global(self, interaction: discord.Interaction):
        # Check if user has admin permissions or mod role
        # Defer the response since global sync can take a while
        await interaction.response.defer(ephemeral=True)
        
        try:
            await interaction.followup.send("🔄 Starting global command sync... This may take a moment.", ephemeral=True)
            synced = await bot.tree.sync()
            await interaction.followup.send(f"✅ Successfully synced {len(synced)} commands globally!", ephemeral=True)
            logger.info(f"Commands manually synced globally by {interaction.user.name}: {len(synced)} commands")
        except Exception as e:
            await interaction.followup.send(f"❌ Error syncing commands: {e}", ephemeral=True)
            logger.error(f"Error manually syncing commands: {e}")
    
    @app_commands.command(name="list_badges", description="List all available badges.")
    async def list_badges(self, interaction: discord.Interaction):
        
        if not os.path.exists(shared.BADGES_PATH):
            await interaction.response.send_message("📁 No badges directory found.", ephemeral=True)
            return
        
        badge_files = [f for f in os.listdir(shared.BADGES_PATH) if f.lower().endswith('.png')]
        
        if not badge_files:
            await interaction.response.send_message("🏆 No badges found in the badges directory.", ephemeral=True)
            return
        
        badges_list = "\n".join([f"• {badge}" for badge in sorted(badge_files)])
        await shared.send_interaction_message(interaction, f"🏆 **Available Badges:**\n{badges_list}")
    
    @app_commands.command(name="badge_help", description="Show information about badge uploads.")
    async def badge_help(self, interaction: discord.Interaction):
        help_message = (
            "🏆 **Badge Upload System** 🏆\n\n"
            "**How to upload a badge:**\n"
            "1. Upload a PNG image file\n"
            "2. Include `#badge` in your message\n"
            "3. Must have admin permissions or mod role\n\n"
            "**Badge naming convention:**\n"
            "• `UWVAC_Badges_Season{number}.png`\n"
            "• Example: `UWVAC_Badges_Season8.png`\n\n"
            "**Features:**\n"
            "• Automatic backup of existing badges\n"
            "• Only PNG files accepted\n"
            "• Stored in the `/badges` directory\n\n"
            "**Commands:**\n"
            "• `/list_badges` - View all available badges\n"
            "• `/badge_help` - Show this help message"
        )
        
        await shared.send_interaction_message(interaction, help_message, ephemeral=True)
    
    @app_commands.command(name="clear_duels_and_chains", description="Clear all active duels and chains (Admin only).")
    @requires_admin_or_mod()
    async def clear_duels_and_chains(self, interaction: discord.Interaction):
        # Check if user has admin permissions or mod role
        # Defer the response since this might take a moment
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Clear all duels
            cleared_duels = 0
            try:
                from artbot.core.duel.DuelService import clear_all_duels
                cleared_duels = clear_all_duels()
            except Exception as e:
                logger.warning(f"Could not clear duels: {e}")
            
            # Clear all chains
            cleared_chains = 0
            cleared_submissions = 0
            try:
                from artbot.core.chain.ChainService import clear_all_chains
                cleared_chains, cleared_submissions = clear_all_chains()
            except Exception as e:
                logger.warning(f"Could not clear chains: {e}")
            
            success_message = f"✅ **Duels and Chains cleared!**\n\n"
            success_message += f"⚔️ **Duels cleared:** {cleared_duels}\n"
            success_message += f"🔗 **Chains cleared:** {cleared_chains}\n"
            success_message += f"📸 **Submissions cleared:** {cleared_submissions}\n\n"
            success_message += f"🧹 All active duels and chains have been removed!"
            
            await shared.send_followup_message(interaction, success_message, ephemeral=True)
            
            # Also announce in the announcement channel if configured
            if shared.announcement_channel:
                channel = bot.get_channel(shared.announcement_channel)
                if channel:
                    announce_message = f"🧹 **Duels & Chains Cleared** 🧹\n"
                    announce_message += f"All active duels and art chains have been cleared by {interaction.user.display_name}.\n"
                    if cleared_duels > 0 or cleared_chains > 0:
                        announce_message += f"⚔️ {cleared_duels} duels and 🔗 {cleared_chains} chains were removed."
                    else:
                        announce_message += f"No active duels or chains were found."
                    await shared.send_discord_message(channel, announce_message)
            
            logger.info(f"Admin {interaction.user.name} cleared {cleared_duels} duels and {cleared_chains} chains")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error clearing duels and chains: {e}", ephemeral=True)
            logger.error(f"Error clearing duels and chains: {e}")
    
    @app_commands.command(name="reset_season_stats", description="Reset all user stats for new season (Admin only).")
    @requires_admin_or_mod()
    async def reset_season_stats(self, interaction: discord.Interaction):
        # Check if user has admin permissions or mod role
        # Defer the response since this might take a moment
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Reset all user stats
            user_count = len(shared.tracked_users)
            reset_user_stats()
            
            # Clear all duels
            cleared_duels = 0
            try:
                from artbot.core.duel.DuelService import clear_all_duels
                cleared_duels = clear_all_duels()
            except Exception as e:
                logger.warning(f"Could not clear duels: {e}")
            
            success_message = f"✅ **Season stats reset completed!**\n"
            success_message += f"📊 Reset stats for {user_count} users\n"
            success_message += f"⚔️ Cleared {cleared_duels} duels\n"
            success_message += f"🔄 All users now have fresh stats for the new season!"
            
            await shared.send_followup_message(interaction, success_message, ephemeral=True)
            
            # Also announce in the announcement channel if configured
            if shared.announcement_channel:
                channel = bot.get_channel(shared.announcement_channel)
                if channel:
                    announce_message = f"🔄 **Season Stats Reset** 🔄\n"
                    announce_message += f"All user stats have been manually reset by {interaction.user.display_name}!\n"
                    announce_message += f"Everyone starts fresh! 🎉"
                    await shared.send_discord_message(channel, announce_message)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error resetting season stats: {e}", ephemeral=True)
            logger.error(f"Error resetting season stats: {e}")
    
    @app_commands.command(name="season_info", description="Show current season information.")
    async def season_info(self, interaction: discord.Interaction):
        info_message = (
            f"## 📅 **Current Season Information** 📅\n\n"
            f"**🎭 Season**: {shared.season}\n"
            f"**🎨 Theme**: {shared.season_theme}\n"
            f"**📆 Current Day**: {shared.current_day}\n"
            f"**📊 Total Days**: {shared.season_days}\n"
            f"**⏳ Days Remaining**: {shared.season_days - shared.current_day + 1}\n"
            f"**👥 Active Users**: {len(shared.tracked_users)}\n\n"
            f"**Progress**: {shared.current_day}/{shared.season_days} days ({(shared.current_day/shared.season_days)*100:.1f}%)"
        )
        await shared.send_interaction_message(interaction, info_message)
    
    @app_commands.command(name="daily_status_edit", description="Edit season number, theme, current day, and season length.")
    @requires_admin_or_mod()
    async def daily_status_edit(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DailyStatusEditModal())
    
    @app_commands.command(name="ping", description="Decide if you want the bot to ping you if you haven't submitted a daily before the deadline")
    @app_commands.describe(value="If the bot should ping you")
    async def ping(self, interaction: discord.Interaction, value: bool):
        user = interaction.user
        if user.id not in shared.tracked_users:
            await interaction.response.send_message(f"❌ User {user.name} not found in tracking.")
            logger.warning(f"User {user.name} (ID: {user.id}) not found in shared.tracked_users")
            return
    
        old_value = shared.tracked_users[user.id]["ping"]
        try:
            shared.tracked_users[user.id]["ping"] = value
            await interaction.response.send_message(f"✅ {shared.tracked_users[user.id]['user_nickname']}'s `{'ping'}` is now `{value}`")
            logger.info(f"Successfully updated {user.name}'s {'ping'} from {old_value} to {value}")
        except ValueError:
            await interaction.response.send_message("⚠️ Invalid value type.")
            logger.error(f"Invalid value type when editing user {user.name}'s {'ping'} to {value}")
    
    
    
    @app_commands.command(name="get_log", description="Get last 10k lines of log file")
    @app_commands.describe(ephemeral="Send ephemerally (sent by DM if False)")
    @requires_admin_or_mod()
    async def get_log(self, interaction: discord.Interaction, ephemeral: bool = False):
        lines = 10000
    
        if not os.path.exists(shared.LOG_PATH):
            await interaction.response.send_message(f"Log file not found: `{shared.LOG_PATH}`", ephemeral=True)
            return
    
        # Read last N lines efficiently (streaming; no full-file read into memory)
        try:
            last_lines = deque(maxlen=lines)
            with open(shared.LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    last_lines.append(line)
            content = "".join(last_lines)
        except Exception as e:
            await interaction.response.send_message(f"Failed to read log: `{type(e).__name__}: {e}`", ephemeral=True)
            return
    
        # Send as a file (Discord messages have length limits; file is safer)
        # Use an in-memory buffer so you don’t need to write a temp file
        data = content.encode("utf-8", errors="replace")
        fp = io.BytesIO(data)
        fp.seek(0)
    
        filename = f"bot_{shared.now_et()}.log"
        discord_file = discord.File(fp=fp, filename=filename)
    
        if ephemeral:
            await interaction.response.send_message(
                f"Last {lines} lines from `{shared.LOG_PATH}`:",
                file=discord_file,
                ephemeral=True
            )
            return
    
        # DM delivery
        await interaction.response.send_message("Sending log via DM…", ephemeral=True)
        try:
            await interaction.user.send(
                content=f"Last {lines} lines from `{shared.LOG_PATH}`:",
                file=discord_file
            )
        except discord.Forbidden:
            # User has DMs disabled
            await interaction.followup.send(
                "Could not DM you (DMs disabled). Try ephemerally instead.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Failed to DM log: `{type(e).__name__}: {e}`",
                ephemeral=True
            )
    
    @app_commands.command(name="force_yell_at_zak", description="Bully Zak (Admin only)")
    @app_commands.describe(val="If Zak will get bullied by WalBot when next submitting")
    @requires_admin_or_mod()
    async def force_yell_at_zak(self, interaction: discord.Interaction, val: bool):
        shared.force_yell_at_zak = val
        await interaction.response.send_message(f"Should yell at Zak set to: {val}", ephemeral=True)

DailyCommands = DailyCog
