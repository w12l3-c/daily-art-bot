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

from artbot.DiscordMessageSender import DiscordMessageSender
from artbot.persistence.DailyStateRepository import DailyStateRepository
# sketchy, shared shouldn't be importing from elsewhere
from artbot.core.duel.DuelService import get_duel_data
from artbot.core.chain.ChainService import get_chain_data

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PROJECT_ROOT_PATH = Path(__file__).resolve().parent.parent

LOG_PATH = PROJECT_ROOT_PATH / "bot.log"

# Server values
guild_id = 748707282690244739

# Daily art tracking values
allowed_channels = [1281049819342831636, 1440845080742199426, 1419517897134440520]
announcement_channel = 1419517897134440520  # Default announcement channel

tracked_users = {}
archived_users = {}  # users who opted out but keep their stats for later rejoin
current_day = 45
season = 1
season_theme = "Testing"
season_days = 50

SAVED_DATA_PATH = PROJECT_ROOT_PATH / "backup.json"
DEBUG_SAVED_DATA_PATH = PROJECT_ROOT_PATH / "backup_debug.json"
BADGES_PATH = PROJECT_ROOT_PATH / "badges"
DEBUG_MODE = False
DEBUG_ANNOUNCEMENT_CHANNEL = 1281049819342831636
DEBUG_TIME_DEPLOY_MINUTES = 1

# Track when messages were last sent to prevent duplicates
last_daily_message_day = ""
last_warning_1_day = ""
last_warning_2_day = ""


time_debug = 30  # seconds
time_deploy = 1 # hours

DISCORD_MESSAGE_LIMIT = 2000
DISCORD_SAFE_MESSAGE_LIMIT = 1900
DISCORD_MARKDOWN_BREAK = "\n\u200b\n"
message_sender = DiscordMessageSender()

# WCW tracking values
wcw_allowed_channels = [1419486211948413098, 1440845080742199426, 1441228179434897479, 1468981683536527604]
wcw_announcement_channel = 1440845080742199426 

wcw_tracked_users = {}
WCW_SAVED_DATA_PATH = PROJECT_ROOT_PATH / "wcw.json"
wcw_current_week = 10
wcw_tracked_users = {}

wcw_last_message_week = 0
wcw_last_reminder_1_week = 0
wcw_last_reminder_2_week = 0

WCW_WARDENS = [516344918566764594, 414612223273598986]  # Ryan, Deceased

# Configurable mod role name (case-insensitive)
MOD_ROLE_NAME = ["wal", "wal#0001", "bot moderator", "ai"]  # Can use any case, comparison is case-insensitive

# Configurable mod IDs
MOD_IDS = [516344918566764594, 666772080162766910]  # Ryan, Wal

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

force_yell_at_zak = False

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


def split_discord_message(
    message: str,
    max_length: int = DISCORD_SAFE_MESSAGE_LIMIT,
) -> list[str]:
    """Split message text into Discord-safe chunks.

    Args:
        message: Discord message content.
        max_length: Maximum chunk length. Defaults below Discord's hard 2000
            character limit to leave room for markdown boundary padding.

    Returns:
        Message chunks, preserving line boundaries when possible.
    """
    return message_sender.split_message(message, max_length=max_length)


async def send_discord_message(destination, message: str, **kwargs) -> list[discord.Message]:
    """Send content to a channel/user, splitting it into safe chunks."""
    return await message_sender.send_channel(destination, message, **kwargs)


async def send_interaction_message(
    interaction: discord.Interaction,
    message: str,
    ephemeral: bool = False,
    **kwargs,
) -> None:
    """Send an interaction response, using followups for overflow chunks."""
    await message_sender.send_interaction(
        interaction,
        message,
        ephemeral=ephemeral,
        **kwargs,
    )


async def send_followup_message(
    interaction: discord.Interaction,
    message: str,
    ephemeral: bool = False,
    **kwargs,
) -> None:
    """Send interaction followups, splitting content into safe chunks."""
    await message_sender.send_followup(
        interaction,
        message,
        ephemeral=ephemeral,
        **kwargs,
    )


def normalize_role_name(role_name: str) -> str:
    return role_name.strip().casefold()


def has_named_role(member, role_names: list[str]) -> bool:
    roles = getattr(member, "roles", [])
    normalized_role_names = {normalize_role_name(role_name) for role_name in role_names}
    return any(
        normalize_role_name(role.name) in normalized_role_names
        for role in roles
    )


def describe_member_roles(member, max_roles: int = 30) -> str:
    if member is None:
        return "member=None roles=[]"

    roles = list(getattr(member, "roles", []))
    role_names = [getattr(role, "name", "<unnamed>") for role in roles]
    normalized_names = [normalize_role_name(role_name) for role_name in role_names]
    truncated = len(role_names) > max_roles

    if truncated:
        role_names = role_names[:max_roles]
        normalized_names = normalized_names[:max_roles]

    return (
        f"member_type={type(member).__name__} "
        f"role_count={len(roles)} "
        f"truncated={truncated} "
        f"role_names={role_names!r} "
        f"normalized_role_names={normalized_names!r}"
    )


def has_admin_or_mod_permissions(param) -> bool:
    user = None
    if isinstance(param, discord.Interaction):
        user = param.user
    elif isinstance(param, discord.User):
        user = param
    elif isinstance(param, discord.Message):
        user = param.author
    elif hasattr(param, "id"):
        user = param
    else:
        return False
    

    """Check if user has administrator permissions or mod role"""
    # Check for administrator permissions
    guild_permissions = getattr(user, "guild_permissions", None)
    if guild_permissions and guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if has_named_role(user, MOD_ROLE_NAME):
        return True
            
    # Check for IDs
    if user.id in MOD_IDS:
        return True
    
    return False

def has_badge_permissions(member) -> bool:
    """Check if user has permissions to upload badges"""
    # Check for administrator permissions
    guild_permissions = getattr(member, "guild_permissions", None)
    if guild_permissions and guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if has_named_role(member, MOD_ROLE_NAME):
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
    
    DailyStateRepository(SAVED_DATA_PATH).save(data)
    
    print(f"Data saved at {now_et().strftime('%Y-%m-%d %H:%M:%S')}")
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


def now_et() -> datetime:
    return datetime.now(ZoneInfo("America/Toronto"))

# Returns a string of today's date (e.g. 2026-02-16)
def now_et_day_str():
    return now_et().strftime("%Y-%m-%d")
