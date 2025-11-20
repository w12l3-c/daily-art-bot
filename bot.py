"""
bot.py
This file contains global constants/variables and core functionality of the bot
"""

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
from duel import register_duel_commands, set_tracked_users_reference, cleanup_expired_duels, load_duel_data
from chain import register_chain_commands, set_tracked_users_reference as set_chain_tracked_users, load_chain_data 
from daily import send_daily_art_message, save_data_task, ping_jailed_users

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
MOD_ROLE_NAME = ["wal", "wal#0001", "bot mod", "AI"]  # Can use any case, comparison is case-insensitive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
allowed_channels = [1281049819342831636, 1440845080742199426]
announcement_channel = 1281049819342831636  # Default announcement channel

tracked_users = {}
current_day = 45
season = 1
season_theme = "Testing"
season_days = 50
saved_data = "backup.json"

# Track when messages were last sent to prevent duplicates
last_daily_message_day = -1
last_warning_1_day = -1
last_warning_2_day = -1

def has_admin_or_mod_permissions(interaction: discord.Interaction) -> bool:
    """Check if user has administrator permissions or mod role"""
    # Check for administrator permissions
    if interaction.user.guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if hasattr(interaction.user, 'roles'):
        mod_roles_lower = [role.lower() for role in MOD_ROLE_NAME]
        for role in interaction.user.roles:
            if role.name.lower() in mod_roles_lower:
                return True
    
    return False

def has_badge_permissions(member) -> bool:
    """Check if user has permissions to upload badges"""
    # Check for administrator permissions
    if member.guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if hasattr(member, 'roles'):
        mod_roles_lower = [role.lower() for role in MOD_ROLE_NAME]
        for role in member.roles:
            if role.name.lower() in mod_roles_lower:
                return True
    
    return False

async def handle_badge_upload(message):
    """Handle badge upload with #badge tag"""
    # Check if user has permissions
    member = message.author
    if not has_badge_permissions(member):
        await message.channel.send(f"❌ {member.display_name}, you need administrator permissions or mod role to upload badges.")
        return True  # Return True to indicate message was handled
    
    # Check if attachment is PNG
    attachment = message.attachments[0]
    if not attachment.filename.lower().endswith('.png'):
        await message.channel.send(f"❌ {member.display_name}, badges must be PNG files.")
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
                    
                    await message.channel.send(f"🏆 {member.display_name}, badge '{attachment.filename}' has been uploaded successfully!")
                    logger.info(f"Badge uploaded: {attachment.filename} by {member.name}")
                    return True
                else:
                    await message.channel.send(f"❌ {member.display_name}, failed to download the badge image.")
                    return True
    
    except Exception as e:
        logger.error(f"Error uploading badge: {e}")
        await message.channel.send(f"❌ {member.display_name}, there was an error uploading the badge.")
        return True

def load_data():
    global current_day, season, tracked_users, announcement_channel, allowed_channels
    try:
        with open(saved_data, "r") as f:
            data = json.load(f)
            current_day = data.get("current_day", current_day)
            season = data.get("season", season)
            loaded_users = data.get("tracked_users", {})
            announcement_channel = data.get("announcement_channel", allowed_channels[0] if allowed_channels else None)
            
            # Load allowed_channels if it exists, otherwise keep the current one
            loaded_allowed_channels = data.get("allowed_channels", allowed_channels)
            if loaded_allowed_channels:
                allowed_channels = loaded_allowed_channels
            
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
            logger.info(f"Allowed channels: {allowed_channels}")
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



@tasks.loop(hours=time_deploy)  # Check every hour for expired duels
async def cleanup_duels():
    """Clean up expired duels every hour"""
    try:
        cleaned = await cleanup_expired_duels(bot, allowed_channels, announcement_channel)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired duels")
    except Exception as e:
        logger.error(f"Error cleaning up duels: {e}")

bot.run(BOT_TOKEN)
