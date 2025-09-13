import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import json
import os
import logging
from dotenv import load_dotenv
import aiohttp
import os
import shutil
import asyncio
from duel import register_duel_commands, set_tracked_users_reference, update_duel_progress, cleanup_expired_duels, get_duel_rankings, get_duel_data, load_duel_data
from chain import register_chain_commands, set_tracked_users_reference as set_chain_tracked_users, process_chain_submission, get_chain_data, load_chain_data  

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
time_debug = 30  # seconds
time_deploy = 1 # hours

# Configurable mod role name (case-insensitive)
MOD_ROLE_NAME = ["wal", "wal#0001", "bot mod", "AI"]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
allowed_channels = [1281049819342831636]
announcement_channel = 1281049819342831636  # Default announcement channel

tracked_users = {}
current_day = 45
season = 1
season_theme = "Testing"
season_days = 50
saved_data = "backup.json"

def has_admin_or_mod_permissions(interaction: discord.Interaction) -> bool:
    """Check if user has administrator permissions or mod role"""
    # Check for administrator permissions
    if interaction.user.guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if hasattr(interaction.user, 'roles'):
        for role in interaction.user.roles:
            if role.name.lower() in MOD_ROLE_NAME:
                return True
    
    return False

def has_badge_permissions(member) -> bool:
    """Check if user has permissions to upload badges"""
    # Check for administrator permissions
    if member.guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if hasattr(member, 'roles'):
        for role in member.roles:
            if role.name.lower() in MOD_ROLE_NAME:
                return True
    
    return False

async def handle_badge_upload(message):
    """Handle badge upload with #badge tag"""
    # Check if user has permissions
    member = message.author
    if not has_badge_permissions(member):
        await message.channel.send(f"❌ {member.name}, you need administrator permissions or mod role to upload badges.")
        return True  # Return True to indicate message was handled
    
    # Check if attachment is PNG
    attachment = message.attachments[0]
    if not attachment.filename.lower().endswith('.png'):
        await message.channel.send(f"❌ {member.name}, badges must be PNG files.")
        return True
    
    try:
        # Create badges directory if it doesn't exist
        badges_dir = "badges"
        if not os.path.exists(badges_dir):
            os.makedirs(badges_dir)
        
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    # Save the badge
                    badge_path = os.path.join(badges_dir, attachment.filename)
                    
                    # If file exists, create a backup
                    if os.path.exists(badge_path):
                        backup_path = f"{badge_path}.backup_{int(datetime.now().timestamp())}"
                        shutil.copy2(badge_path, backup_path)
                        logger.info(f"Created backup: {backup_path}")
                    
                    with open(badge_path, 'wb') as f:
                        f.write(await resp.read())
                    
                    await message.channel.send(f"🏆 {member.name}, badge '{attachment.filename}' has been uploaded successfully!")
                    logger.info(f"Badge uploaded: {attachment.filename} by {member.name}")
                    return True
                else:
                    await message.channel.send(f"❌ {member.name}, failed to download the badge image.")
                    return True
    
    except Exception as e:
        logger.error(f"Error uploading badge: {e}")
        await message.channel.send(f"❌ {member.name}, there was an error uploading the badge.")
        return True

def load_data():
    global current_day, season, tracked_users, announcement_channel
    try:
        with open(saved_data, "r") as f:
            data = json.load(f)
            current_day = data.get("current_day", current_day)
            season = data.get("season", season)
            loaded_users = data.get("tracked_users", {})
            announcement_channel = data.get("announcement_channel", allowed_channels[0] if allowed_channels else None)
            
            # Convert string keys back to integers (JSON stores dict keys as strings)
            tracked_users = {}
            for user_id_str, user_data in loaded_users.items():
                try:
                    user_id_int = int(user_id_str)
                    tracked_users[user_id_int] = user_data
                except ValueError:
                    logger.warning(f"Could not convert user ID '{user_id_str}' to integer")
            
            # Load duel data if it exists
            duel_data = data.get("duel", None)
            load_duel_data(duel_data)
            
            # Load chain data if it exists
            chain_data = data.get("chain", None)
            load_chain_data(chain_data)
                    
            print(f"✅ Data loaded successfully! (Day {current_day}, Season {season})")
            logger.info(f"Data loaded successfully! (Day {current_day}, Season {season})")
            logger.info(f"Loaded {len(tracked_users)} users with IDs: {list(tracked_users.keys())}")
            logger.info(f"Announcement channel set to: {announcement_channel}")
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ No save file found. Starting fresh.")
        logger.warning("No save file found. Starting fresh.")
        current_day = 1
        season = 7
        tracked_users = {}
        announcement_channel = allowed_channels[0] if allowed_channels else None
        load_duel_data(None)  # Initialize empty duel data
        load_chain_data(None)  # Initialize empty chain data

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    logger.info(f'Bot logged in as {bot.user}')
    try:
        load_data()
        
        # Initialize duel system with tracked users reference
        try:
            set_tracked_users_reference(tracked_users)
            await register_duel_commands(bot)
            print("✅ Duel commands registered successfully")
            logger.info("Duel commands registered successfully")
        except Exception as e:
            print(f"❌ Failed to register duel commands: {e}")
            logger.error(f"Failed to register duel commands: {e}")
        
        # Initialize chain system with tracked users reference
        try:
            set_chain_tracked_users(tracked_users)
            await register_chain_commands(bot)
            print("✅ Chain commands registered successfully")
            logger.info("Chain commands registered successfully")
        except Exception as e:
            print(f"❌ Failed to register chain commands: {e}")
            logger.error(f"Failed to register chain commands: {e}")
        
        # Small delay to ensure commands are properly registered before syncing
        await asyncio.sleep(1)
        
        # Sync ALL commands (including duel and chain) AFTER registering them
        try:
            synced = await bot.tree.sync()  # Sync slash commands
            print(f"Synced {len(synced)} commands.")
            logger.info(f"Synced {len(synced)} commands.")
        except Exception as e:
            print(f"Error syncing commands: {e}")
            logger.error(f"Error syncing commands: {e}")
            
    except Exception as e:
        print(f"Error in on_ready: {e}")
        logger.error(f"Error in on_ready: {e}")

    send_daily_art_message.start()
    save_data_task.start()
    ping_jailed_users.start()
    cleanup_duels.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.channel.id not in allowed_channels:
        return

    if message.author.id == 374012168028291073 and message.content.startswith("🔥"):
        guild = message.guild
        member = guild.get_member(message.author.id)
        nickname = member.nick if member and member.nick else member.name
        await message.channel.send(f"Hi! {nickname} <3")

    # Check if the message has an image and if the user is being tracked
    if message.attachments and any(attachment.content_type.startswith("image/") for attachment in message.attachments):
        content_lower = message.content.lower()  # Convert message to lowercase for case-insensitive tagging
        
        # Handle badge uploads (specific role required)
        if "#badge" in content_lower:
            if await handle_badge_upload(message):
                return  # Badge handled, don't process as regular art
        
        if message.author.id in tracked_users:
            user_data = tracked_users[message.author.id]

            if "#daily" in content_lower:
                if user_data['sent_image']:
                    # User already submitted daily art, count this as buffer
                    user_data['buffer'] = user_data.get('buffer', 0) + 1
                    print(f"🛑 {message.author.name} submitted additional #daily art as buffer.")
                    logger.info(f"{message.author.name} submitted additional #daily art as buffer.")
                    await message.channel.send(f"📌 {message.author.name}, you've already submitted today's art! This has been recorded as buffer art.")
                else:
                    # First daily submission
                    user_data['sent_image'] = True  # Mark as official art submission
                    print(f"✅ {message.author.name} submitted official art.")
                    logger.info(f"{message.author.name} submitted official art.")
                    await message.channel.send(f"🎨 {message.author.name}, your art has been recorded for today!")
                
                # Update duel progress for this user (regardless of buffer or daily)
                updated_duels = update_duel_progress(message.author.id, datetime.now())
                if updated_duels:
                    logger.info(f"Updated {len(updated_duels)} duels for {message.author.name}")

            elif "#buffer" in content_lower:
                user_data['buffer'] = user_data.get('buffer', 0) + 1  # Increase buffer count
                print(f"🛑 {message.author.name} submitted buffer art.")
                logger.info(f"{message.author.name} submitted buffer art.")
                await message.channel.send(f"📌 {message.author.name}, your buffer art has been recorded! This will not count for today's submission.")

            elif "#chain" in content_lower:
                # Handle chain submission
                chain_processed = await process_chain_submission(message.author.id, message, message.attachments[0])
                if not chain_processed:
                    # If chain processing failed and user didn't tag it as anything else, show the regular untagged message
                    if user_data['ping']:
                        await message.channel.send(f"⚠️ {message.author.name}, please tag your submission with `#daily` if it's an official art entry.")

            else:
                print(f"📸 {message.author.name} uploaded an image but didn't tag it as art.")
                logger.info(f"{message.author.name} uploaded an image but didn't tag it as art.")
                if user_data['ping']:
                    await message.channel.send(f"⚠️ {message.author.name}, please tag your submission with `#daily` if it's an official art entry.")

    # Process other commands
    await bot.process_commands(message)

@bot.tree.command(name="add_channel", description="Add a channel or thread for tracking art submissions.")
@app_commands.describe(channel="Select or mention a channel or thread")
async def add_channel(interaction: discord.Interaction, channel: discord.abc.GuildChannel):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    # Check if it's a text channel or thread
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("❌ Only text channels and threads are supported for art tracking.", ephemeral=True)
        return
        
    if channel.id not in allowed_channels:
        allowed_channels.append(channel.id)
        channel_type = "Thread" if isinstance(channel, discord.Thread) else "Channel"
        await interaction.response.send_message(f"✅ {channel_type} {channel.mention} added to allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Channel {channel.mention} is already in the allowed list.", ephemeral=True)

@bot.tree.command(name="remove_channel", description="Remove a channel from tracking.")
@app_commands.describe(channel_id="Enter the channel ID")
async def remove_channel(interaction: discord.Interaction, channel_id: str):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    # Convert string to int and validate
    try:
        channel_id_int = int(channel_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid channel ID. Please enter a valid number.", ephemeral=True)
        return
        
    if channel_id_int in allowed_channels:
        allowed_channels.remove(channel_id_int)
        await interaction.response.send_message(f"✅ Channel {channel_id_int} removed from allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Channel {channel_id_int} not found in the allowed list.", ephemeral=True)

@bot.tree.command(name="list_channels", description="List all channels being tracked.")
@app_commands.describe()
async def list_channels(interaction: discord.Interaction):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    if not allowed_channels:
        await interaction.response.send_message("⚠️ No channels are currently being tracked.", ephemeral=True)
    else:
        channels = "\n".join([f"<#{channel_id}>" for channel_id in allowed_channels])
        await interaction.response.send_message(f"**Tracked Channels:**\n{channels}")

@bot.tree.command(name="set_announcement_channel", description="Set the channel for daily announcements and results.")
@app_commands.describe(channel="Select or mention the announcement channel or thread")
async def set_announcement_channel(interaction: discord.Interaction, channel: discord.abc.GuildChannel):
    global announcement_channel
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    # Check if it's a text channel or thread
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("❌ Only text channels and threads are supported for announcements.", ephemeral=True)
        return
    
    announcement_channel = channel.id
    channel_type = "Thread" if isinstance(channel, discord.Thread) else "Channel"
    await interaction.response.send_message(f"✅ Announcement {channel_type.lower()} set to {channel.mention}!\n"
                                          f"Daily messages and season results will be posted here.", ephemeral=True)
    logger.info(f"Announcement channel changed to {channel.id} ({channel.name}) by {interaction.user.name}")

@bot.tree.command(name="set_announcement_channel_by_id", description="Set announcement channel by ID (supports threads).")
@app_commands.describe(channel_id="Enter the channel or thread ID as text")
async def set_announcement_channel_by_id(interaction: discord.Interaction, channel_id: str):
    global announcement_channel
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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
            announcement_channel = channel_id_int
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
        announcement_channel = channel_id_int
        logger.warning(f"Announcement channel set to unknown ID {channel_id_int} by {interaction.user.name}")

@bot.tree.command(name="get_announcement_channel", description="Show the current announcement channel.")
async def get_announcement_channel(interaction: discord.Interaction):
    if announcement_channel:
        channel = bot.get_channel(announcement_channel)
        if channel:
            await interaction.response.send_message(f"📢 **Current announcement channel:** {channel.mention} ({channel.name})")
        else:
            await interaction.response.send_message(f"⚠️ **Current announcement channel ID:** {announcement_channel} (channel not accessible)")
    else:
        await interaction.response.send_message("❌ No announcement channel set. Use `/set_announcement_channel` to set one.")

@bot.tree.command(name="add_channel_by_id", description="Add a channel by ID (fallback method).")
@app_commands.describe(channel_id="Enter the channel ID as text")
async def add_channel_by_id(interaction: discord.Interaction, channel_id: str):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
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
    if not channel:
        await interaction.response.send_message(f"⚠️ Channel with ID {channel_id_int} not found or bot doesn't have access. Adding anyway...", ephemeral=True)
        
    if channel_id_int not in allowed_channels:
        allowed_channels.append(channel_id_int)
        channel_name = f" ({channel.name})" if channel else ""
        await interaction.response.send_message(f"✅ Channel {channel_id_int}{channel_name} added to allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Channel {channel_id_int} is already in the allowed list.", ephemeral=True)

@bot.tree.command(name="channel_info", description="Show tracking and announcement channel information.")
async def channel_info(interaction: discord.Interaction):
    info_message = "## 📋 **Channel Configuration**\n\n"
    
    # Tracking channels
    if allowed_channels:
        info_message += "**🎨 Art Tracking Channels:**\n"
        for channel_id in allowed_channels:
            channel = bot.get_channel(channel_id)
            channel_name = f" ({channel.name})" if channel else " (not accessible)"
            info_message += f"• <#{channel_id}>{channel_name}\n"
    else:
        info_message += "**🎨 Art Tracking Channels:** None\n"
    
    # Announcement channel
    info_message += "\n**📢 Announcement Channel:**\n"
    if announcement_channel:
        channel = bot.get_channel(announcement_channel)
        channel_name = f" ({channel.name})" if channel else " (not accessible)"
        info_message += f"• <#{announcement_channel}>{channel_name}\n"
    else:
        info_message += "• None set\n"
    
    info_message += "\n**ℹ️ How it works:**\n"
    info_message += "• Art can be submitted in any tracking channel\n"
    info_message += "• Daily messages and results post to announcement channel only\n"
    info_message += "• Bot responds to art submissions in the same channel they were posted"
    
    await interaction.response.send_message(info_message)

@bot.tree.command(name="add_user", description="Add a user to the art tracking system.")
@app_commands.describe(user="Select a user")
async def add_user(interaction: discord.Interaction, user: discord.User):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    member = await interaction.guild.fetch_member(user.id)
    user_nickname = member.nick if member and member.nick else user.name
    if user.id not in tracked_users:
        tracked_users[user.id] = {
            'username': user.name,
            'user_nickname': user_nickname,
            'sent_image': False,
            'parole_days': 0,
            'deceased': False,
            'deceased_days': 0,
            'missing_days': 0,
            'revival': 0,
            'buffer': 0,
            'probation': False,
            'ping': False,
            'duels_won': 0,
            'duels_lost': 0
        }
        await interaction.response.send_message(f"✅ {user.name} added to the tracking list!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {user.name} is already being tracked.", ephemeral=True)

@bot.tree.command(name="remove_user", description="Remove a user from tracking.")
@app_commands.describe(user="Select a user")
async def remove_user(interaction: discord.Interaction, user: discord.User):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    if user.id in tracked_users:
        del tracked_users[user.id]
        await interaction.response.send_message(f"✅ {user.name} removed from tracking!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ User not found in tracking.")

@bot.tree.command(name="list_users", description="List all users being tracked.")
async def list_users(interaction: discord.Interaction):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    if not tracked_users:
        await interaction.response.send_message("⚠️ No users are currently being tracked.", ephemeral=True)
    else:
        users = "\n".join([f"{user['username']} - {user['user_nickname']}" for user in tracked_users.values()])
        await interaction.response.send_message(f"**Tracked Users:**\n{users}")

@bot.tree.command(name="list_attributes", description="List all available user attributes.")
async def list_attributes(interaction: discord.Interaction):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    logger.info(f"list_attributes command called by {interaction.user.name}")
    if tracked_users:
        sample_user = next(iter(tracked_users.values()))
        attributes = list(sample_user.keys())
    else:
        attributes = [
            "username", "user_nickname", "sent_image", "parole_days", "deceased",
            "deceased_days", "missing_days", "revival", "buffer", "probation", "ping",
            "duels_won", "duels_lost"
        ]

    formatted = "\n".join(f"- {attr}" for attr in attributes)
    await interaction.response.send_message(
        "**Available User Attributes:**\n" + formatted,
        ephemeral=True
    )

@bot.tree.command(name="query_user", description="Check a user's submission stats.")
@app_commands.describe(user="Select a user")
async def query_user(interaction: discord.Interaction, user: discord.User):
    if user.id in tracked_users:
        u = tracked_users[user.id]
        message = (
            f"**User:** {u['username']}\n"
            f"**🔗 User Nickname: {u['user_nickname']}**\n"
            f"📌 Sent Image: {u['sent_image']}\n"
            f"🛑 Buffer: {u['buffer']}\n"
            f"⏳ Parole Days: {u['parole_days']}\n"
            f"💀 Deceased: {u['deceased']} ({u['deceased_days']} days)\n"
            f"🚫 Missing Days: {u['missing_days']}\n"
            f"🚀 Revivals: {u['revival']}\n"
            f"🔒 Probation: {u['probation']}\n"
            f"🔔 Ping Notifications: {u['ping']}\n"
            f"⚔️ Duels Won: {u.get('duels_won', 0)}\n"
            f"💔 Duels Lost: {u.get('duels_lost', 0)}\n"
        )
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("❌ User not found in tracking.")

async def attribute_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function for user attributes"""
    # Get all possible attributes
    if tracked_users:
        # Get attributes from an existing user
        sample_user = next(iter(tracked_users.values()))
        attributes = list(sample_user.keys())
    else:
        # Fallback to default attributes
        attributes = [
            "username", "user_nickname", "sent_image", "parole_days", "deceased",
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
        if tracked_users:
            sample_user = next(iter(tracked_users.values()))
            attr_value = sample_user.get(attr)
            attr_type = type(attr_value).__name__
            description = f"Type: {attr_type}"
            if isinstance(attr_value, bool):
                description += " (use 'true' or 'false')"
            choices.append(app_commands.Choice(name=f"{attr} - {description}", value=attr))
        else:
            choices.append(app_commands.Choice(name=attr, value=attr))
    
    return choices

async def value_autocomplete(
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
        
        if not attribute or not tracked_users:
            return []
        
        # Get a sample user to check the attribute type
        sample_user = next(iter(tracked_users.values()))
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

@bot.tree.command(name="edit_user", description="Edit a user's attribute.")
@app_commands.describe(user="Select a user", attribute="Attribute to change", value="New value")
@app_commands.autocomplete(attribute=attribute_autocomplete, value=value_autocomplete)
async def edit_user(interaction: discord.Interaction, user: discord.User, attribute: str, value: str):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    logger.info(f"edit_user called: user_id={user.id} (type: {type(user.id)}), attribute={attribute}, value={value}")
    logger.info(f"tracked_users keys: {list(tracked_users.keys())} (types: {[type(k) for k in tracked_users.keys()]})")
    
    # Check if user exists
    if user.id not in tracked_users:
        await interaction.response.send_message(f"❌ User {user.name} not found in tracking. Available users: {[u['username'] for u in tracked_users.values()]}")
        logger.warning(f"User {user.name} (ID: {user.id}) not found in tracked_users")
        return
    
    # Check if attribute exists
    if attribute not in tracked_users[user.id]:
        available_attrs = list(tracked_users[user.id].keys())
        await interaction.response.send_message(f"❌ Attribute '{attribute}' not found. Available attributes: {available_attrs}")
        logger.warning(f"Attribute '{attribute}' not found for user {user.name}. Available: {available_attrs}")
        return
    
    old_value = tracked_users[user.id][attribute]
    try:
        if isinstance(old_value, bool):
            value = value.lower() == 'true'
        elif isinstance(old_value, int):
            value = int(value)

        tracked_users[user.id][attribute] = value
        await interaction.response.send_message(f"✅ {tracked_users[user.id]['user_nickname']}'s `{attribute}` changed from `{old_value}` to `{value}`")
        logger.info(f"Successfully updated {user.name}'s {attribute} from {old_value} to {value}")
    except ValueError:
        await interaction.response.send_message("⚠️ Invalid value type.")
        logger.error(f"Invalid value type when editing user {user.name}'s {attribute} to {value}")

@bot.tree.command(name="sync_commands", description="Force sync all slash commands (Admin only).")
async def sync_commands(interaction: discord.Interaction):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    try:
        # Try guild-specific sync first (faster)
        guild = interaction.guild
        synced = await bot.tree.sync(guild=guild)
        await interaction.response.send_message(f"✅ Successfully synced {len(synced)} commands to this server!", ephemeral=True)
        logger.info(f"Commands manually synced to guild {guild.name} by {interaction.user.name}: {len(synced)} commands")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error syncing commands: {e}", ephemeral=True)
        logger.error(f"Error manually syncing commands: {e}")

@bot.tree.command(name="sync_global", description="Force sync commands globally (Admin only, slower).")
async def sync_global(interaction: discord.Interaction):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    try:
        synced = await bot.tree.sync()
        await interaction.response.send_message(f"✅ Successfully synced {len(synced)} commands globally!", ephemeral=True)
        logger.info(f"Commands manually synced globally by {interaction.user.name}: {len(synced)} commands")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error syncing commands: {e}", ephemeral=True)
        logger.error(f"Error manually syncing commands: {e}")

@bot.tree.command(name="list_badges", description="List all available badges.")
async def list_badges(interaction: discord.Interaction):
    badges_dir = "badges"
    
    if not os.path.exists(badges_dir):
        await interaction.response.send_message("📁 No badges directory found.", ephemeral=True)
        return
    
    badge_files = [f for f in os.listdir(badges_dir) if f.lower().endswith('.png')]
    
    if not badge_files:
        await interaction.response.send_message("🏆 No badges found in the badges directory.", ephemeral=True)
        return
    
    badges_list = "\n".join([f"• {badge}" for badge in sorted(badge_files)])
    await interaction.response.send_message(f"🏆 **Available Badges:**\n{badges_list}")

@bot.tree.command(name="badge_help", description="Show information about badge uploads.")
async def badge_help(interaction: discord.Interaction):
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
    
    await interaction.response.send_message(help_message, ephemeral=True)

@bot.tree.command(name="season_info", description="Show current season information.")
async def season_info(interaction: discord.Interaction):
    info_message = (
        f"## 📅 **Current Season Information** 📅\n\n"
        f"**🎭 Season**: {season}\n"
        f"**🎨 Theme**: {season_theme}\n"
        f"**📆 Current Day**: {current_day}\n"
        f"**📊 Total Days**: {season_days}\n"
        f"**⏳ Days Remaining**: {season_days - current_day + 1}\n"
        f"**👥 Active Users**: {len(tracked_users)}\n\n"
        f"**Progress**: {current_day}/{season_days} days ({(current_day/season_days)*100:.1f}%)"
    )
    await interaction.response.send_message(info_message)

@bot.tree.command(name="set_season_theme", description="Set the current season theme (Admin only).")
@app_commands.describe(theme="Enter the new season theme")
async def set_season_theme(interaction: discord.Interaction, theme: str):
    global season_theme
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    old_theme = season_theme
    season_theme = theme
    await interaction.response.send_message(f"✅ Season theme changed from **\"{old_theme}\"** to **\"{season_theme}\"**", ephemeral=True)
    logger.info(f"Season theme changed from '{old_theme}' to '{season_theme}' by {interaction.user.name}")

@bot.tree.command(name="set_season_days", description="Set the total days for current season (Admin only).")
@app_commands.describe(days="Enter the total number of days for the season")
async def set_season_days(interaction: discord.Interaction, days: int):
    global season_days
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if days < 1:
        await interaction.response.send_message("❌ Season days must be at least 1.", ephemeral=True)
        return
    
    if days < current_day:
        await interaction.response.send_message(f"⚠️ Warning: Setting season days ({days}) less than current day ({current_day}). Season will end immediately!", ephemeral=True)
    
    old_days = season_days
    season_days = days
    await interaction.response.send_message(f"✅ Season days changed from **{old_days}** to **{season_days}** days", ephemeral=True)
    logger.info(f"Season days changed from {old_days} to {season_days} by {interaction.user.name}")

@bot.tree.command(name="set_current_day", description="Set the current day number (Admin only).")
@app_commands.describe(day="Enter the current day number")
async def set_current_day(interaction: discord.Interaction, day: int):
    global current_day
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if day < 1:
        await interaction.response.send_message("❌ Current day must be at least 1.", ephemeral=True)
        return
    
    if day > season_days:
        await interaction.response.send_message(f"⚠️ Warning: Setting current day ({day}) greater than season days ({season_days}). Season will end immediately!", ephemeral=True)
    
    old_day = current_day
    current_day = day
    await interaction.response.send_message(f"✅ Current day changed from **{old_day}** to **{current_day}**", ephemeral=True)
    logger.info(f"Current day changed from {old_day} to {current_day} by {interaction.user.name}")

@bot.tree.command(name="set_season_number", description="Set the season number (Admin only).")
@app_commands.describe(season_num="Enter the season number")
async def set_season_number(interaction: discord.Interaction, season_num: int):
    global season
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if season_num < 1:
        await interaction.response.send_message("❌ Season number must be at least 1.", ephemeral=True)
        return
    
    old_season = season
    season = season_num
    await interaction.response.send_message(f"✅ Season number changed from **{old_season}** to **{season}**", ephemeral=True)
    logger.info(f"Season number changed from {old_season} to {season} by {interaction.user.name}")


# Edit the seconds 
@tasks.loop(minutes=30)  # Save data every 8 hours
async def send_daily_art_message():
    global current_day, season, season_theme, season_days

    users_not_sent = [u for u in tracked_users.values() if not u['sent_image']]
    users_sent = [u for u in tracked_users.values() if u['sent_image']]
    print(season_theme)
    logger.debug(f"Current season theme: {season_theme}")
    message = f"## **Season {season} - {season_theme}: Day {current_day} - Daily Art Challenge** 🎨\n"
    message += f"**🔄 On parole:** \n{', '.join([u['user_nickname'] for u in users_sent])}\n"
    message += "\n**⛓️ Jailed:**\n"
    message += "🧱"*20 + "\n"

    for user in users_not_sent:
        if not user['deceased']:
            message += f"|| {user['user_nickname']} 💨{user['missing_days']} || "
        if user != users_not_sent[-1]:
            message += r"\| "

    message += "\n" + "🧱"*20 + "\n"
    
    message += "\n**🪦 Deceased:**\n"
    message += "☁️"*20 + "\n"
    
    for user in users_not_sent:
        if user['deceased']:
            message += f"|| {user['user_nickname']}(💨{user['missing_days']} 💀{user['deceased_days']} 😇{user['revival']}) || "
        if user != users_not_sent[-1]:
            message += r"\| "
    
    message += "\n" + "☁️"*20

    channel = bot.get_channel(announcement_channel)
    if not channel:
        logger.error(f"Announcement channel {announcement_channel} not found or not accessible")
        return

    # Daily reset logic at 12:30 am, run loop of 30 min, check if time // 30 == 0 and hour == 1
    now = datetime.now()   
    if now.hour == 0 and now.minute >= 30:
        # Only send daily message and advance day if there are tracked users
        if tracked_users:
            if channel:
                print("Sending daily art message...")
                logger.info("Sending daily art message...")
                await channel.send(message)

            print(f"Day {current_day} has ended!")
            logger.info(f"Day {current_day} has ended!")
            current_day += 1
        else:
            print("No tracked users - pausing season progression")
            logger.info("No tracked users - season paused until users are added")
        if current_day == season_days + 1:
            badge_pathway = f"badges/UWVAC_Badges_Season{season}.png"
            if os.path.exists(badge_pathway):
                badge = discord.File(badge_pathway)
            results_message = f"# 🎉 **Season {season} has ended!** 🎉\n"
            results_message += f"🏆 **Congratulations to the all inmates!** 🏆\n"
            
            tracked_users_list = list(tracked_users.values())
            tracked_users_list.sort(key=lambda x: (-x['parole_days'], x['missing_days'], -x['revival']))
            
            rank = 1
            prev_user = None
            grouped_users = [] 

            for index, user in enumerate(tracked_users_list):
                # Check if this user has the same stats as the previous user
                if prev_user and (
                    prev_user['parole_days'] == user['parole_days'] and
                    prev_user['missing_days'] == user['missing_days'] and
                    prev_user['revival'] == user['revival']
                ):
                    grouped_users.append(user['user_nickname']) 
                else:
                    if grouped_users:
                        print(f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n")
                        logger.info(f"Rank {rank}: {', '.join(grouped_users)} | Parole: {prev_user['parole_days']} | Missing: {prev_user['missing_days']} | Revival: {prev_user['revival']}")
                        results_message += f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

                    rank = index + 1 
                    grouped_users = [user['user_nickname']]
                prev_user = user 
                print(grouped_users)
                logger.debug(f"Grouped users: {grouped_users}")
            if grouped_users:
                results_message += f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

            results_message += f"\n## **Funny Achievements:**\n"
            max_revival = max(user['revival'] for user in tracked_users.values())
            highest_revival_users = [user['user_nickname'] for user in tracked_users.values() if user['revival'] == max_revival]
            max_buffer = max(user['buffer'] for user in tracked_users.values())
            highest_buffer_users = [user['user_nickname'] for user in tracked_users.values() if user['buffer'] == max_buffer]
            results_message += f"**💾 Most Buffer Art:** {', '.join(highest_buffer_users)} - {max_buffer}\n"
            results_message += f"**😇 Most Revived:** {', '.join(highest_revival_users)} - {max_revival}\n"
            
            # Add duel rankings
            duel_rankings = get_duel_rankings()
            if duel_rankings:
                results_message += f"\n## **⚔️ Duel Champions:**\n"
                for i, duelist in enumerate(duel_rankings[:5], 1):  # Top 5 duelists
                    results_message += f"**{i}.** {duelist['user_nickname']} - {duelist['wins']}W/{duelist['losses']}L ({duelist['win_rate']:.1f}% win rate)\n"
                
                # Special achievements
                if duel_rankings:
                    most_wins = duel_rankings[0]
                    most_active = max(duel_rankings, key=lambda x: x['total'])
                    best_win_rate = max([d for d in duel_rankings if d['total'] >= 3], key=lambda x: x['win_rate'], default=None)
                    
                    results_message += f"\n🏆 **Most Duel Wins:** {most_wins['user_nickname']} ({most_wins['wins']} wins)\n"
                    results_message += f"⚔️ **Most Active Duelist:** {most_active['user_nickname']} ({most_active['total']} duels)\n"
                    if best_win_rate:
                        results_message += f"🎯 **Best Win Rate:** {best_win_rate['user_nickname']} ({best_win_rate['win_rate']:.1f}%)\n"
            
            results_message += f"\nCongratulations to all participants! See you all next season🎉\n"
            results_message += f"🎨 **The {season_theme} badge** 🎨\n"
            await channel.send(results_message, file=badge)

            current_day = 1
            season += 1
            season_theme = f"{season_theme}"
            season_message = f"# 🎉 **Season {season} begins tomorrow!** 🎉\n"
            await channel.send(season_message)

        for user in tracked_users.values():
            if not user['sent_image']:
                if not user['probation']:
                    if not user['deceased']:
                        user['deceased'] = True
                    user['deceased_days'] += 1
                    user['missing_days'] += 1
            else:
                user['parole_days'] += 1
                if user['deceased']:
                    user['revival'] += 1
                    user['deceased'] = False
                if user['missing_days'] > 0:
                    user['missing_days'] -= 1
            if user['missing_days'] > 0:
                reduction = min(user['missing_days'], user['buffer'])
                user['missing_days'] -= reduction
                user['buffer'] -= reduction
            user['sent_image'] = False
        


@tasks.loop(hours=time_deploy)  # Save data every 8 hours
async def save_data_task():
    data = {
        "current_day": current_day,
        "season": season,
        "tracked_users": tracked_users,
        "announcement_channel": announcement_channel,
        "duel": get_duel_data(),
        "chain": get_chain_data()
    }
    
    with open(saved_data, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

@tasks.loop(hours=time_deploy)  # Save data every hour
async def ping_jailed_users():
    ping_users = []
    for user_id, user in tracked_users.items():
        if user['ping'] and not user['sent_image']:
            ping_users.append(user_id)

    print(ping_users)
    logger.debug(f"Users to ping: {ping_users}")
    
    if ping_users:
        now = datetime.now()
        message = ""
        
        if now.hour == 22:  # 10 PM - 2 hours warning
            print("Pinging jailed users (2 hour warning)...")
            logger.info("Pinging jailed users (2 hour warning)...")
            message = "🚨 **Final Warning!** 🚨\n"
            
            for user_id, user in tracked_users.items():
                if user['ping'] and not user['sent_image']:
                    member = bot.get_user(user_id)
                    if member:
                        message += f"{member.mention} "
            
            message += "\n**You roughly have 2 hours before you're shipped to the graveyard!!** 🪦"
            
        elif now.hour == 23:  # 11 PM - 1 hour warning
            print("Pinging jailed users (1 hour warning)...")
            logger.info("Pinging jailed users (1 hour warning)...")
            message = "⚠️ **FINAL HOUR WARNING!** ⚠️\n"
            
            for user_id, user in tracked_users.items():
                if user['ping'] and not user['sent_image']:
                    member = bot.get_user(user_id)
                    if member:
                        message += f"{member.mention} "
            
            message += "\n**You have approximately 1 hour before the graveyard!!** ⏰💀"
        
        if message:  # Only send if we have a message (10 PM or 11 PM)
            channel = bot.get_channel(announcement_channel)
            if channel:
                await channel.send(message)

@tasks.loop(hours=time_deploy)  # Check every hour for expired duels
async def cleanup_duels():
    """Clean up expired duels every hour"""
    try:
        cleaned = await cleanup_expired_duels(bot, allowed_channels)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired duels")
    except Exception as e:
        logger.error(f"Error cleaning up duels: {e}")

bot.run(BOT_TOKEN)
