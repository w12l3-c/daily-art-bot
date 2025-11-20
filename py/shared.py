"""
shared.py
This file contains all global constants/variables/functions used by other scripts
"""

import discord # type: ignore
from discord.ext import commands # type: ignore
from datetime import datetime
import os
import aiohttp # type: ignore
from dotenv import load_dotenv  # type: ignore
import shutil
import logging
from pathlib import Path

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PROJECT_ROOT_PATH = Path(__file__).resolve().parent.parent

# Daily art tracking values
allowed_channels = [1281049819342831636, 1440845080742199426]
announcement_channel = 1281049819342831636  # Default announcement channel

tracked_users = {}
current_day = 45
season = 1
season_theme = "Testing"
season_days = 50

SAVED_DATA_PATH = PROJECT_ROOT_PATH / "backup.json"
BADGES_PATH = PROJECT_ROOT_PATH / "badges"

# Track when messages were last sent to prevent duplicates
last_daily_message_day = -1
last_warning_1_day = -1
last_warning_2_day = -1


time_debug = 30  # seconds
time_deploy = 1 # hours

# WCW tracking values
wcw_allowed_channels = [1419486211948413098, 1440845080742199426]
wcw_announcement_channel = 1419486211948413098

wcw_tracked_users = {}
WCW_SAVED_DATA_PATH = PROJECT_ROOT_PATH / "wcw.json"



# Configurable mod role name (case-insensitive)
MOD_ROLE_NAME = ["wal", "wal#0001", "bot mod", "AI"]  # Can use any case, comparison is case-insensitive


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
        if not os.path.exists(BADGES_PATH):
            os.makedirs(BADGES_PATH)
        
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    # Save the badge
                    badge_path = os.path.join(BADGES_PATH, attachment.filename)
                    
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