"""
py
This file contains all global constants/variables/functions used by other scripts
"""

import discord
from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import aiohttp
import json
from dotenv import load_dotenv 
import shutil
import logging
from pathlib import Path

# sketchy, shared shouldn't be importing from elsewhere
from duel import get_duel_data
from chain import get_chain_data

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PROJECT_ROOT_PATH = Path(__file__).resolve().parent.parent

LOG_PATH = PROJECT_ROOT_PATH / "bot.log"

# Server values
guild_id = 1468981682169450703 # 1359790250729148466

# Daily art tracking values
allowed_channels = [1281049819342831636, 1440845080742199426]
announcement_channel = 1281049819342831636  # Default announcement channel

tracked_users = {}
archived_users = {}  # users who opted out but keep their stats for later rejoin
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
wcw_allowed_channels = [1419486211948413098, 1440845080742199426, 1441228179434897479, 1468981683536527604]
wcw_announcement_channel = 1468981683536527604 

wcw_tracked_users = {}
WCW_SAVED_DATA_PATH = PROJECT_ROOT_PATH / "wcw.json"
wcw_current_week = 10
wcw_tracked_users = {}

wcw_last_message_week = 0
wcw_last_reminder_1_week = 0
wcw_last_reminder_2_week = 0

WCW_WARDENS = [516344918566764594, 414612223273598986]

# Configurable mod role name (case-insensitive)
MOD_ROLE_NAME = ["wal", "wal#0001", "bot mod", "AI"]  # Can use any case, comparison is case-insensitive

# Configurable mod IDs
MOD_IDS = [516344918566764594, 666772080162766910]

# Challenge tracking values
# data will be stored in backup.json
challenge_day = 0
challenge_length = 7
CHALLENGE_MODS = [
    742551555240230963, # Orsafia
]
challenge_theme = ""
challenge_number = 1
challenge_threshold = 7

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


def has_admin_or_mod_permissions(param) -> bool:
    user = None
    if isinstance(param, discord.Interaction):
        user = param.user
    elif isinstance(param, discord.User):
        user = param
    else:
        return False
    

    """Check if user has administrator permissions or mod role"""
    # Check for administrator permissions
    if user.guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if hasattr(user, 'roles'):
        mod_roles_lower = [role.lower() for role in MOD_ROLE_NAME]
        for role in user.roles:
            if role.name.lower() in mod_roles_lower:
                return True
            
    # Check for IDs
    if user.id in MOD_IDS:
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
    
# thank you stackoverflow user Łukasz Kwieciński
class ConfirmationPrompt(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__ (*args, **kwargs)
        self.confirmed: bool = False

    @discord.ui.button(label = '❌', style = discord.ButtonStyle.blurple)
    async def returnFalse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label = '✅', style = discord.ButtonStyle.blurple)
    async def returnTrue(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()
        
# usage:
# confirmation, msg = await confirmation_prompt(interaction, warning="...")
# if confirmation: 
#   await msg.edit(content="...", view=None, embed=None)
async def confirmation_prompt(interaction: discord.Interaction, title: str = "", description: str = "", ephemeral: bool = True) -> tuple[bool, discord.Message]:
    view = ConfirmationPrompt()
    await interaction.response.send_message(
        embed=discord.Embed(title=title, description=description),
        view=view,
        ephemeral=ephemeral
    )
    await view.wait()

    msg = await interaction.original_response()

    return view.confirmed, msg


@tasks.loop(hours=time_deploy)  # Save data every 8 hours
async def save_data_task():
    data = {
        "current_day": current_day,
        "season": season,
        "season_days": season_days,
        "challenge_day": challenge_day,
        "challenge_length": challenge_length,
        "challenge_theme": challenge_theme,
        "challenge_number": challenge_number,
        "challenge_threshold": challenge_threshold,
        "season_theme": season_theme,
        "guild_id": guild_id,
        "tracked_users": tracked_users,
        "archived_users": archived_users,
        "announcement_channel": announcement_channel,
        "allowed_channels": allowed_channels,
        "duel": get_duel_data(),
        "chain": get_chain_data()
    }
    
    with open(SAVED_DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Data saved at {now_et().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data saved at {now_et().strftime('%Y-%m-%d %H:%M:%S')}")

def format_username(username):
    # escapes all special formatting characters
    username = (
        username
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("~", "\\~")
    )

    # add other formatting options as needed
    return username


def get_submission_link(id: int, wcw: bool = False) -> str:
    if wcw:
        return f"https://discord.com/channels/{guild_id}/{wcw_tracked_users[id]['submission']}" if id in wcw_tracked_users and wcw_tracked_users[id]['submission'] else 'None'
    else:
        return f"https://discord.com/channels/{guild_id}/{tracked_users[id]['submission']}" if id in tracked_users and tracked_users[id]['submission'] else 'None'
    
def get_default_user_values(
    username: str = "",
    user_nickname: str = "",
    submission: str = "",
    parole_days: int = 0,
    deceased: bool = False,
    deceased_days: int = 0,
    missing_days: int = 0,
    consecutive_missed_days: int = 0,
    revival: int = 0,
    buffer: int = 0,
    probation: bool = False,
    ping: bool = False,
    duels_won: int = 0,
    duels_lost: int = 0,
    in_challenges: bool = False,
    challenge_participations: int = 0,
    challenge_completions: int = 0,
    challenge_streak: int = 0,
    challenge_submissions: int = 0,
):
    return {
        "username": username,
        "user_nickname": user_nickname,
        "submission": submission,
        "parole_days": parole_days,
        "deceased": deceased,
        "deceased_days": deceased_days,
        "missing_days": missing_days,
        "consecutive_missed_days": consecutive_missed_days,
        "revival": revival,
        "buffer": buffer,
        "probation": probation,
        "ping": ping,
        "duels_won": duels_won,
        "duels_lost": duels_lost,
        "in_challenges": in_challenges,
        "challenge_participations": challenge_participations,
        "challenge_completions": challenge_completions,
        "challenge_streak": challenge_streak,
        "challenge_submissions": challenge_submissions,
    }


def now_et():
    return datetime.now(ZoneInfo("America/Toronto"))