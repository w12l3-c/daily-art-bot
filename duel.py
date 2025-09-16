import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

# Global duel storage - in production you might want to persist this
active_duels = {}
pending_duels = {}

class DuelType:
    VOLUME = "volume"
    STREAK = "streak"
    TIME = "time"

class DuelStatus:
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

def get_tracked_users():
    """Import tracked_users from bot.py - this will be set by the main bot"""
    # This will be imported from the main bot file
    return getattr(get_tracked_users, 'tracked_users', {})

def set_tracked_users_reference(tracked_users_ref):
    """Set reference to tracked_users from main bot"""
    get_tracked_users.tracked_users = tracked_users_ref

async def duel_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for duel types"""
    choices = [
        app_commands.Choice(name="volume - Amount of dailies in X period", value=DuelType.VOLUME),
        app_commands.Choice(name="streak - Dailies in a row in X period", value=DuelType.STREAK),
        app_commands.Choice(name="time - First to daily at X time for Y period", value=DuelType.TIME),
    ]
    
    # Filter based on current input
    if current:
        choices = [choice for choice in choices if current.lower() in choice.name.lower()]
    
    return choices

async def user_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for tracked users"""
    tracked_users = get_tracked_users()
    
    if not tracked_users:
        return []
    
    # Get user choices
    choices = []
    for user_id, user_data in tracked_users.items():
        username = user_data.get('user_nickname', user_data.get('username', 'Unknown'))
        choices.append(app_commands.Choice(name=username, value=str(user_id)))
    
    # Filter based on current input
    if current:
        current_lower = current.lower()
        choices = [choice for choice in choices if current_lower in choice.name.lower()]
    
    # Limit to 25 choices (Discord limit)
    return choices[:25]

async def validate_duel_challenge(challenger_id: int, target_id: int, duel_type: str, period: int) -> tuple[bool, str]:
    """Validate if a duel challenge is valid"""
    tracked_users = get_tracked_users()
    
    # Check if challenger exists in tracking
    if challenger_id not in tracked_users:
        return False, "❌ You are not in the art tracking system."
    
    # Check if target exists in tracking
    if target_id not in tracked_users:
        return False, "❌ Target user is not in the art tracking system."
    
    # Check if trying to duel themselves
    if challenger_id == target_id:
        return False, "❌ You cannot duel yourself!"
    
    # Check if either user already has a pending duel
    for duel_id, duel in pending_duels.items():
        if challenger_id in [duel['challenger'], duel['target']] or target_id in [duel['challenger'], duel['target']]:
            return False, "❌ One of the users already has a pending duel."
    
    # Check if either user is in an active duel
    for duel_id, duel in active_duels.items():
        if challenger_id in [duel['challenger'], duel['target']] or target_id in [duel['challenger'], duel['target']]:
            return False, "❌ One of the users is already in an active duel."
    
    # Validate duel type
    if duel_type not in [DuelType.VOLUME, DuelType.STREAK, DuelType.TIME]:
        return False, "❌ Invalid duel type."
    
    # Validate period
    if period < 1 or period > 365:
        # Allow special debug period of 120 seconds for testing
        if period != 120:
            return False, "❌ Period must be between 1 and 365 days (or 120 for debug testing)."
    
    return True, "✅ Duel challenge is valid."

async def create_duel_challenge(challenger_id: int, target_id: int, duel_type: str, period: int, target_time: str = None) -> str:
    """Create a new duel challenge"""
    tracked_users = get_tracked_users()
    
    # Generate unique duel ID
    duel_id = f"{challenger_id}_{target_id}_{int(datetime.now().timestamp())}"
    
    # Create duel data
    duel_data = {
        'id': duel_id,
        'challenger': challenger_id,
        'target': target_id,
        'type': duel_type,
        'period': period,
        'status': DuelStatus.PENDING,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=24),  # 24 hour expiry
        'challenger_name': tracked_users[challenger_id]['user_nickname'],
        'target_name': tracked_users[target_id]['user_nickname'],
    }
    
    # Add type-specific data
    if duel_type == DuelType.TIME and target_time:
        try:
            # Parse target time (HH:MM format)
            time_parts = target_time.split(':')
            if len(time_parts) != 2:
                raise ValueError("Invalid time format")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("Invalid time values")
            duel_data['target_time'] = target_time
        except (ValueError, IndexError):
            return "❌ Invalid time format. Use HH:MM (24-hour format)."
    
    # Store the duel
    pending_duels[duel_id] = duel_data
    
    logger.info(f"Duel challenge created: {duel_id} - {duel_data['challenger_name']} vs {duel_data['target_name']}")
    
    return duel_id

def format_duel_description(duel_data: dict) -> str:
    """Format a human-readable duel description"""
    duel_type = duel_data['type']
    period = duel_data['period']
    
    # Handle debug period
    if period == 120:
        period_text = "120 seconds (DEBUG MODE)"
    else:
        period_text = f"{period} days"
    
    if duel_type == DuelType.VOLUME:
        return f"**Volume Duel**: Most daily art submissions in {period_text}"
    elif duel_type == DuelType.STREAK:
        return f"**Streak Duel**: Longest consecutive daily streak in {period_text}"
    elif duel_type == DuelType.TIME:
        target_time = duel_data.get('target_time', 'midnight')
        return f"**Time Duel**: First to submit daily art at {target_time} for {period_text}"
    else:
        return f"**Duel**: {duel_type} over {period_text}"

async def duel_challenge_command(interaction: discord.Interaction, opponent: str, duel_type: str, period: int, target_time: str = None):
    """Main duel challenge command logic"""
    challenger_id = interaction.user.id
    
    try:
        target_id = int(opponent)
    except ValueError:
        await interaction.response.send_message("❌ Invalid opponent ID.", ephemeral=True)
        return
    
    # Validate the challenge
    is_valid, validation_message = await validate_duel_challenge(challenger_id, target_id, duel_type, period)
    
    if not is_valid:
        await interaction.response.send_message(validation_message, ephemeral=True)
        return
    
    # Create the duel
    result = await create_duel_challenge(challenger_id, target_id, duel_type, period, target_time)
    
    # Check if creation failed
    if result.startswith("❌"):
        await interaction.response.send_message(result, ephemeral=True)
        return
    
    duel_id = result
    duel_data = pending_duels[duel_id]
    
    # Create challenge message
    description = format_duel_description(duel_data)
    
    # Handle debug period display
    if period == 120:
        duration_text = "120 seconds (DEBUG MODE)"
    else:
        duration_text = f"{period} days"
    
    challenge_message = (
        f"⚔️ **DUEL CHALLENGE** ⚔️\n\n"
        f"**Challenger:** {duel_data['challenger_name']}\n"
        f"**Target:** {duel_data['target_name']}\n\n"
        f"{description}\n\n"
        f"**Duration:** {duration_text}\n"
        f"**Expires:** <t:{int(duel_data['expires_at'].timestamp())}:R>\n\n"
        f"<@{target_id}>, use `/duel_respond accept` or `/duel_respond deny` to respond!"
    )
    
    await interaction.response.send_message(challenge_message)
    logger.info(f"Duel challenge sent: {duel_data['challenger_name']} challenged {duel_data['target_name']}")

async def duel_respond_command(interaction: discord.Interaction, response: str):
    """Handle duel accept/deny responses"""
    user_id = interaction.user.id
    
    # Find pending duel for this user
    user_duel = None
    duel_id = None
    
    for d_id, duel in pending_duels.items():
        if duel['target'] == user_id:
            user_duel = duel
            duel_id = d_id
            break
    
    if not user_duel:
        await interaction.response.send_message("❌ You have no pending duel challenges.", ephemeral=True)
        return
    
    # Check if duel has expired
    if datetime.now() > user_duel['expires_at']:
        del pending_duels[duel_id]
        await interaction.response.send_message("❌ This duel challenge has expired.", ephemeral=True)
        return
    
    if response.lower() == "accept":
        # Move duel to active duels
        user_duel['status'] = DuelStatus.ACTIVE
        user_duel['started_at'] = datetime.now()
        
        # Handle debug period (120 seconds) vs normal period (days)
        if user_duel['period'] == 120:
            user_duel['end_at'] = datetime.now() + timedelta(seconds=120)
        else:
            user_duel['end_at'] = datetime.now() + timedelta(days=user_duel['period'])
        
        # Initialize tracking data
        user_duel['challenger_score'] = 0
        user_duel['target_score'] = 0
        user_duel['challenger_streak'] = 0
        user_duel['target_streak'] = 0
        
        active_duels[duel_id] = user_duel
        del pending_duels[duel_id]
        
        description = format_duel_description(user_duel)
        accept_message = (
            f"⚔️ **DUEL ACCEPTED** ⚔️\n\n"
            f"**{user_duel['challenger_name']} vs {user_duel['target_name']}**\n\n"
            f"{description}\n\n"
            f"**Start:** <t:{int(user_duel['started_at'].timestamp())}:F>\n"
            f"**End:** <t:{int(user_duel['end_at'].timestamp())}:F>\n\n"
            f"**Let the battle begin!** 🎨"
        )
        
        await interaction.response.send_message(accept_message)
        logger.info(f"Duel accepted: {user_duel['challenger_name']} vs {user_duel['target_name']}")
        
    elif response.lower() == "deny":
        challenger_name = user_duel['challenger_name']
        target_name = user_duel['target_name']
        
        del pending_duels[duel_id]
        
        deny_message = (
            f"❌ **DUEL DECLINED** ❌\n\n"
            f"**{target_name}** has declined the duel challenge from **{challenger_name}**.\n"
            f"Maybe next time! 🎨"
        )
        
        await interaction.response.send_message(deny_message)
        logger.info(f"Duel declined: {target_name} declined challenge from {challenger_name}")
        
    else:
        await interaction.response.send_message("❌ Invalid response. Use `accept` or `deny`.", ephemeral=True)

async def duel_status_command(interaction: discord.Interaction):
    """Show current duel status for the user"""
    user_id = interaction.user.id
    
    # Check for pending duels
    pending_as_challenger = []
    pending_as_target = []
    
    for duel_id, duel in pending_duels.items():
        if duel['challenger'] == user_id:
            pending_as_challenger.append(duel)
        elif duel['target'] == user_id:
            pending_as_target.append(duel)
    
    # Check for active duels
    active_as_participant = []
    
    for duel_id, duel in active_duels.items():
        if user_id in [duel['challenger'], duel['target']]:
            active_as_participant.append(duel)
    
    if not pending_as_challenger and not pending_as_target and not active_as_participant:
        await interaction.response.send_message("📊 You have no active or pending duels.", ephemeral=True)
        return
    
    status_message = "📊 **YOUR DUEL STATUS** 📊\n\n"
    
    # Pending challenges sent
    if pending_as_challenger:
        status_message += "**🔄 Challenges Sent:**\n"
        for duel in pending_as_challenger:
            description = format_duel_description(duel)
            status_message += f"• vs {duel['target_name']} - {description}\n"
        status_message += "\n"
    
    # Pending challenges received
    if pending_as_target:
        status_message += "**⏳ Challenges Received:**\n"
        for duel in pending_as_target:
            description = format_duel_description(duel)
            status_message += f"• from {duel['challenger_name']} - {description}\n"
            status_message += f"  Use `/duel_respond accept` or `/duel_respond deny`\n"
        status_message += "\n"
    
    # Active duels
    if active_as_participant:
        status_message += "**⚔️ Active Duels:**\n"
        for duel in active_as_participant:
            opponent_name = duel['target_name'] if duel['challenger'] == user_id else duel['challenger_name']
            description = format_duel_description(duel)
            
            # Calculate time remaining differently for debug mode
            if duel['period'] == 120:
                time_remaining = duel['end_at'] - datetime.now()
                seconds_left = int(time_remaining.total_seconds())
                time_text = f"{seconds_left} seconds remaining"
            else:
                days_left = (duel['end_at'] - datetime.now()).days
                time_text = f"{days_left} days remaining"
            
            status_message += f"• vs {opponent_name} - {description}\n"
            status_message += f"  {time_text}\n"
        status_message += "\n"
    
    await interaction.response.send_message(status_message, ephemeral=True)

# Command functions to be imported by bot.py
async def register_duel_commands(bot):
    """Register all duel commands with the bot"""
    
    @bot.tree.command(name="duel", description="Challenge another user to an art duel!")
    @app_commands.describe(
        opponent="Select the user you want to duel",
        duel_type="Type of duel to challenge",
        period="Duration in days (1-365), or 120 for debug mode (2 minutes)",
        target_time="For time duels: target time in HH:MM format (24-hour)"
    )
    @app_commands.autocomplete(opponent=user_autocomplete, duel_type=duel_type_autocomplete)
    async def duel_command(interaction: discord.Interaction, opponent: str, duel_type: str, period: int, target_time: str = None):
        await duel_challenge_command(interaction, opponent, duel_type, period, target_time)
    
    @bot.tree.command(name="duel_respond", description="Accept or deny a duel challenge")
    @app_commands.describe(response="Your response to the duel challenge")
    @app_commands.choices(response=[
        app_commands.Choice(name="Accept", value="accept"),
        app_commands.Choice(name="Deny", value="deny")
    ])
    async def duel_respond(interaction: discord.Interaction, response: app_commands.Choice[str]):
        await duel_respond_command(interaction, response.value)
    
    @bot.tree.command(name="duel_status", description="Check your current duel status")
    async def duel_status(interaction: discord.Interaction):
        await duel_status_command(interaction)
    
    @bot.tree.command(name="duel_leaderboard", description="View active duels and leaderboard")
    async def duel_leaderboard(interaction: discord.Interaction):
        await duel_leaderboard_command(interaction)
    
    @bot.tree.command(name="duel_forfeit", description="Forfeit your current active duel")
    async def duel_forfeit(interaction: discord.Interaction):
        await duel_forfeit_command(interaction)

async def duel_leaderboard_command(interaction: discord.Interaction):
    """Show all active duels and stats"""
    if not active_duels:
        await interaction.response.send_message("🏆 No active duels currently!", ephemeral=True)
        return
    
    leaderboard_message = "🏆 **ACTIVE DUELS LEADERBOARD** 🏆\n\n"
    
    for duel_id, duel in active_duels.items():
        description = format_duel_description(duel)
        
        # Calculate time remaining differently for debug mode
        if duel['period'] == 120:
            time_remaining = duel['end_at'] - datetime.now()
            seconds_left = int(time_remaining.total_seconds())
            time_text = f"{seconds_left} seconds remaining"
        else:
            days_left = (duel['end_at'] - datetime.now()).days
            time_text = f"{days_left} days remaining"
        
        leaderboard_message += f"⚔️ **{duel['challenger_name']} vs {duel['target_name']}**\n"
        leaderboard_message += f"  {description}\n"
        leaderboard_message += f"  {time_text}\n"
        
        # Show current scores based on duel type
        if duel['type'] == DuelType.VOLUME:
            leaderboard_message += f"  📊 {duel['challenger_name']}: {duel['challenger_score']} | {duel['target_name']}: {duel['target_score']}\n"
        elif duel['type'] == DuelType.STREAK:
            leaderboard_message += f"  🔥 {duel['challenger_name']}: {duel['challenger_streak']} | {duel['target_name']}: {duel['target_streak']}\n"
        elif duel['type'] == DuelType.TIME:
            leaderboard_message += f"  ⏰ First to {duel.get('target_time', 'target time')}\n"
        
        leaderboard_message += "\n"
    
    await interaction.response.send_message(leaderboard_message)

async def duel_forfeit_command(interaction: discord.Interaction):
    """Allow a user to forfeit their active duel"""
    user_id = interaction.user.id
    
    # Find active duel for this user
    user_duel = None
    duel_id = None
    
    for d_id, duel in active_duels.items():
        if user_id in [duel['challenger'], duel['target']]:
            user_duel = duel
            duel_id = d_id
            break
    
    if not user_duel:
        await interaction.response.send_message("❌ You are not currently in an active duel.", ephemeral=True)
        return
    
    # Determine who forfeited and who won
    if user_id == user_duel['challenger']:
        forfeiter_name = user_duel['challenger_name']
        winner_name = user_duel['target_name']
        winner_id = user_duel['target']
    else:
        forfeiter_name = user_duel['target_name']
        winner_name = user_duel['challenger_name']
        winner_id = user_duel['challenger']
    
    # Update duel win/loss records
    tracked_users = get_tracked_users()
    if tracked_users:
        # Initialize duel stats if they don't exist
        if 'duels_won' not in tracked_users[winner_id]:
            tracked_users[winner_id]['duels_won'] = 0
        if 'duels_lost' not in tracked_users[user_id]:
            tracked_users[user_id]['duels_lost'] = 0
        
        # Update records
        tracked_users[winner_id]['duels_won'] += 1
        tracked_users[user_id]['duels_lost'] += 1
    
    # Remove from active duels
    del active_duels[duel_id]
    
    forfeit_message = (
        f"🏳️ **DUEL FORFEITED** 🏳️\n\n"
        f"**{forfeiter_name}** has forfeited the duel!\n"
        f"**{winner_name}** wins by forfeit! 🏆\n\n"
        f"Sometimes discretion is the better part of valor! 🎨"
    )
    
    await interaction.response.send_message(forfeit_message)
    logger.info(f"Duel forfeited: {forfeiter_name} forfeited to {winner_name}")

def get_duel_rankings():
    """Get duel win/loss rankings for all users"""
    tracked_users = get_tracked_users()
    if not tracked_users:
        return []
    
    duel_stats = []
    for user_id, user_data in tracked_users.items():
        wins = user_data.get('duels_won', 0)
        losses = user_data.get('duels_lost', 0)
        
        if wins > 0 or losses > 0:  # Only include users who have participated in duels
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
            duel_stats.append({
                'user_nickname': user_data['user_nickname'],
                'wins': wins,
                'losses': losses,
                'total': wins + losses,
                'win_rate': win_rate
            })
    
    # Sort by wins first, then by win rate
    duel_stats.sort(key=lambda x: (-x['wins'], -x['win_rate']))
    return duel_stats

def determine_duel_winner(duel_data):
    """Determine and announce the winner of a completed duel"""
    duel_type = duel_data['type']
    challenger_score = duel_data.get('challenger_score', 0)
    target_score = duel_data.get('target_score', 0)
    
    # Determine winner based on duel type
    if duel_type == DuelType.VOLUME:
        winner_is_challenger = challenger_score > target_score
    elif duel_type == DuelType.STREAK:
        winner_is_challenger = challenger_score > target_score
    elif duel_type == DuelType.TIME:
        winner_is_challenger = challenger_score > target_score
    else:
        winner_is_challenger = challenger_score > target_score
    
    # Handle ties
    is_tie = challenger_score == target_score
    
    # Update win/loss records
    tracked_users = get_tracked_users()
    if tracked_users:
        challenger_id = duel_data['challenger']
        target_id = duel_data['target']
        
        # Initialize duel stats if they don't exist
        for user_id in [challenger_id, target_id]:
            if 'duels_won' not in tracked_users[user_id]:
                tracked_users[user_id]['duels_won'] = 0
            if 'duels_lost' not in tracked_users[user_id]:
                tracked_users[user_id]['duels_lost'] = 0
        
        # Update records
        if is_tie:
            # For ties, no one gets a win or loss
            winner_name = "TIE"
            loser_name = None
            logger.info(f"Duel ended in tie: {duel_data['challenger_name']} vs {duel_data['target_name']} ({challenger_score}-{target_score})")
        elif winner_is_challenger:
            tracked_users[challenger_id]['duels_won'] += 1
            tracked_users[target_id]['duels_lost'] += 1
            winner_name = duel_data['challenger_name']
            loser_name = duel_data['target_name']
            logger.info(f"Duel completed: {winner_name} defeated {loser_name} ({challenger_score}-{target_score})")
        else:
            tracked_users[target_id]['duels_won'] += 1
            tracked_users[challenger_id]['duels_lost'] += 1
            winner_name = duel_data['target_name']
            loser_name = duel_data['challenger_name']
            logger.info(f"Duel completed: {winner_name} defeated {loser_name} ({target_score}-{challenger_score})")
        
        return winner_name, loser_name, challenger_score, target_score, is_tie
    
    return None, None, challenger_score, target_score, is_tie

async def announce_duel_completion(duel_data, bot=None, allowed_channels=None, announcement_channel=None):
    """Announce duel completion to participants"""
    logger.info(f"Starting duel completion announcement for: {duel_data['challenger_name']} vs {duel_data['target_name']}")
    
    winner_name, loser_name, challenger_score, target_score, is_tie = determine_duel_winner(duel_data)
    
    # Create completion message
    description = format_duel_description(duel_data)
    
    if is_tie:
        completion_message = (
            f"⚔️ **DUEL COMPLETED - TIE!** ⚔️\n\n"
            f"**{duel_data['challenger_name']} vs {duel_data['target_name']}**\n\n"
            f"{description}\n\n"
            f"**Final Score:** {challenger_score} - {target_score}\n"
            f"**Result:** It's a tie! Both warriors fought valiantly! 🤝\n\n"
            f"<@{duel_data['challenger']}> <@{duel_data['target']}> Honor to both participants! 🎨"
        )
    else:
        completion_message = (
            f"⚔️ **DUEL COMPLETED** ⚔️\n\n"
            f"**{duel_data['challenger_name']} vs {duel_data['target_name']}**\n\n"
            f"{description}\n\n"
            f"**Final Score:** {challenger_score} - {target_score}\n"
            f"**Winner:** {winner_name} 🏆\n\n"
            f"<@{duel_data['challenger']}> <@{duel_data['target']}> Congratulations to the victor! 🎨"
        )
    
    logger.info(f"Duel completion message created: {len(completion_message)} characters")
    
    # Post to the announcement channel if available, otherwise fallback to first allowed channel
    if bot:
        try:
            channel_id = announcement_channel if announcement_channel else (allowed_channels[0] if allowed_channels else None)
            
            if channel_id:
                channel = bot.get_channel(channel_id)
                logger.info(f"Attempting to post to channel {channel_id}, found channel: {channel is not None}")
                
                if channel:
                    await channel.send(completion_message)
                    logger.info(f"✅ Successfully posted duel completion to channel: {duel_data['challenger_name']} vs {duel_data['target_name']}")
                    print(f"✅ Duel completion message posted to channel!")
                else:
                    logger.error(f"❌ Could not find channel {channel_id}")
            else:
                logger.error(f"❌ No announcement channel or allowed channels available")
        except Exception as e:
            logger.error(f"❌ Failed to post duel completion to channel: {e}")
    else:
        logger.warning(f"⚠️ No bot instance provided to announce_duel_completion")
    
    return completion_message

# Helper function to update duel progress (called from main bot when art is submitted)
def update_duel_progress(user_id: int, submission_time: datetime = None):
    """Update duel progress when a user submits art"""
    if submission_time is None:
        submission_time = datetime.now()
    
    updated_duels = []
    
    for duel_id, duel in active_duels.items():
        if user_id not in [duel['challenger'], duel['target']]:
            continue
            
        # Check if duel has ended
        if datetime.now() > duel['end_at']:
            continue
            
        is_challenger = user_id == duel['challenger']
        
        if duel['type'] == DuelType.VOLUME:
            # Increment submission count
            if is_challenger:
                duel['challenger_score'] += 1
            else:
                duel['target_score'] += 1
                
        elif duel['type'] == DuelType.STREAK:
            # Update streak count (this would need more sophisticated tracking)
            if is_challenger:
                duel['challenger_streak'] += 1
            else:
                duel['target_streak'] += 1
                
        elif duel['type'] == DuelType.TIME:
            # Check if submission was at target time
            target_time = duel.get('target_time')
            if target_time:
                target_hour, target_minute = map(int, target_time.split(':'))
                submission_hour = submission_time.hour
                submission_minute = submission_time.minute
                
                # Allow 30-minute window around target time
                target_total_minutes = target_hour * 60 + target_minute
                submission_total_minutes = submission_hour * 60 + submission_minute
                
                if abs(target_total_minutes - submission_total_minutes) <= 30:
                    if is_challenger:
                        duel['challenger_score'] += 1
                    else:
                        duel['target_score'] += 1
        
        updated_duels.append(duel_id)
    
    return updated_duels

# Cleanup function to remove expired duels
async def cleanup_expired_duels(bot=None, allowed_channels=None, announcement_channel=None):
    """Remove expired pending duels and completed active duels"""
    current_time = datetime.now()
    
    # Remove expired pending duels
    expired_pending = [duel_id for duel_id, duel in pending_duels.items() 
                      if current_time > duel['expires_at']]
    
    for duel_id in expired_pending:
        logger.info(f"Removing expired pending duel: {duel_id}")
        del pending_duels[duel_id]
    
    # Check for completed active duels
    completed_active = [duel_id for duel_id, duel in active_duels.items() 
                       if current_time > duel['end_at']]
    
    for duel_id in completed_active:
        duel = active_duels[duel_id]
        logger.info(f"Duel completed: {duel['challenger_name']} vs {duel['target_name']}")
        
        # Announce completion to both participants
        await announce_duel_completion(duel, bot, allowed_channels, announcement_channel)
        
        del active_duels[duel_id]
    
    return len(expired_pending) + len(completed_active)

def get_duel_data():
    """Get duel data for saving to backup"""
    # Convert datetime objects to ISO strings for JSON serialization
    pending_serializable = {}
    active_serializable = {}
    
    for duel_id, duel in pending_duels.items():
        serializable_duel = duel.copy()
        serializable_duel['created_at'] = duel['created_at'].isoformat()
        serializable_duel['expires_at'] = duel['expires_at'].isoformat()
        pending_serializable[duel_id] = serializable_duel
    
    for duel_id, duel in active_duels.items():
        serializable_duel = duel.copy()
        serializable_duel['created_at'] = duel['created_at'].isoformat()
        serializable_duel['expires_at'] = duel['expires_at'].isoformat()
        if 'started_at' in duel:
            serializable_duel['started_at'] = duel['started_at'].isoformat()
        if 'end_at' in duel:
            serializable_duel['end_at'] = duel['end_at'].isoformat()
        active_serializable[duel_id] = serializable_duel
    
    return {
        'pending_duels': pending_serializable,
        'active_duels': active_serializable
    }

def load_duel_data(duel_data):
    """Load duel data from backup"""
    global pending_duels, active_duels
    
    if not duel_data:
        return
    
    # Load pending duels
    pending_data = duel_data.get('pending_duels', {})
    for duel_id, duel in pending_data.items():
        # Convert ISO strings back to datetime objects
        duel['created_at'] = datetime.fromisoformat(duel['created_at'])
        duel['expires_at'] = datetime.fromisoformat(duel['expires_at'])
        pending_duels[duel_id] = duel
    
    # Load active duels
    active_data = duel_data.get('active_duels', {})
    for duel_id, duel in active_data.items():
        # Convert ISO strings back to datetime objects
        duel['created_at'] = datetime.fromisoformat(duel['created_at'])
        duel['expires_at'] = datetime.fromisoformat(duel['expires_at'])
        if 'started_at' in duel:
            duel['started_at'] = datetime.fromisoformat(duel['started_at'])
        if 'end_at' in duel:
            duel['end_at'] = datetime.fromisoformat(duel['end_at'])
        active_duels[duel_id] = duel
    
    logger.info(f"Loaded {len(pending_duels)} pending duels and {len(active_duels)} active duels")

