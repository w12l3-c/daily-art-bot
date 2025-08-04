import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import json
import os
import logging
from dotenv import load_dotenv
from duel import register_duel_commands, set_tracked_users_reference, update_duel_progress, cleanup_expired_duels, get_duel_rankings, get_duel_data, load_duel_data  

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
time_deploy = 8 # hours

# Configurable mod role name (case-insensitive)
MOD_ROLE_NAME = "wally"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
allowed_channels = [1281049819342831636]

tracked_users = {}
current_day = 1
season = 3
season_theme = "Testing"
season_days = 10
saved_data = "backup.json"

def has_admin_or_mod_permissions(interaction: discord.Interaction) -> bool:
    """Check if user has administrator permissions or mod role"""
    # Check for administrator permissions
    if interaction.user.guild_permissions.administrator:
        return True
    
    # Check for mod role (case-insensitive)
    if hasattr(interaction.user, 'roles'):
        for role in interaction.user.roles:
            if role.name.lower() == MOD_ROLE_NAME.lower():
                return True
    
    return False

def load_data():
    global current_day, season, tracked_users
    try:
        with open(saved_data, "r") as f:
            data = json.load(f)
            current_day = data.get("current_day", 1)
            season = data.get("season", 1)
            loaded_users = data.get("tracked_users", {})
            
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
                    
            print(f"✅ Data loaded successfully! (Day {current_day}, Season {season})")
            logger.info(f"Data loaded successfully! (Day {current_day}, Season {season})")
            logger.info(f"Loaded {len(tracked_users)} users with IDs: {list(tracked_users.keys())}")
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ No save file found. Starting fresh.")
        logger.warning("No save file found. Starting fresh.")
        current_day = 1
        season = 7
        tracked_users = {}
        load_duel_data(None)  # Initialize empty duel data

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    logger.info(f'Bot logged in as {bot.user}')
    try:
        load_data()
        
        # Initialize duel system with tracked users reference
        set_tracked_users_reference(tracked_users)
        await register_duel_commands(bot)
        
        synced = await bot.tree.sync()  # Sync slash commands
        print(f"Synced {len(synced)} commands.")
        logger.info(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")
        logger.error(f"Error syncing commands: {e}")

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
        if message.author.id in tracked_users:
            content_lower = message.content.lower()  # Convert message to lowercase for case-insensitive tagging
            user_data = tracked_users[message.author.id]

            if "#daily" in content_lower:
                user_data['sent_image'] = True  # Mark as official art submission
                print(f"✅ {message.author.name} submitted official art.")
                logger.info(f"{message.author.name} submitted official art.")
                await message.channel.send(f"🎨 {message.author.name}, your art has been recorded for today!")
                
                # Update duel progress for this user
                updated_duels = update_duel_progress(message.author.id, datetime.now())
                if updated_duels:
                    logger.info(f"Updated {len(updated_duels)} duels for {message.author.name}")

            elif "#buffer" in content_lower:
                user_data['buffer'] = user_data.get('buffer', 0) + 1  # Increase buffer count
                print(f"🛑 {message.author.name} submitted buffer art.")
                logger.info(f"{message.author.name} submitted buffer art.")
                await message.channel.send(f"📌 {message.author.name}, your buffer art has been recorded! This will not count for today's submission.")

            else:
                print(f"📸 {message.author.name} uploaded an image but didn't tag it as art.")
                logger.info(f"{message.author.name} uploaded an image but didn't tag it as art.")
                if user_data['ping']:
                    await message.channel.send(f"⚠️ {message.author.name}, please tag your submission with `#daily` if it's an official art entry.")

    # Process other commands
    await bot.process_commands(message)

@bot.tree.command(name="add_channel", description="Add a channel for tracking art submissions.")
@app_commands.describe(channel_id="Enter the channel ID")
async def add_channel(interaction: discord.Interaction, channel_id: int):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    if channel_id not in allowed_channels:
        allowed_channels.append(channel_id)
        await interaction.response.send_message(f"✅ Channel {channel_id} added to allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Channel {channel_id} is already in the allowed list.", ephemeral=True)

@bot.tree.command(name="remove_channel", description="Remove a channel from tracking.")
@app_commands.describe(channel_id="Enter the channel ID")
async def remove_channel(interaction: discord.Interaction, channel_id: int):
    # Check if user has admin permissions or mod role
    if not has_admin_or_mod_permissions(interaction):
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
        
    if channel_id in allowed_channels:
        allowed_channels.remove(channel_id)
        await interaction.response.send_message(f"✅ Channel {channel_id} removed from allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Channel {channel_id} not found in the allowed list.", ephemeral=True)

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


# Edit the seconds 
@tasks.loop(seconds=time_debug)
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

    channel = bot.get_channel(allowed_channels[0])

    # Daily reset logic at 12:30 am, run loop of 30 min, check if time // 30 == 0 and hour == 1
    now = datetime.now()   
    if now.second % 30 != 0:
        if channel:
            print("Sending daily art message...")
            logger.info("Sending daily art message...")
            await channel.send(message)

        print(f"Day {current_day} has ended!")
        logger.info(f"Day {current_day} has ended!")
        current_day += 1
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
        


@tasks.loop(seconds=time_debug)
async def save_data_task():
    data = {
        "current_day": current_day,
        "season": season,
        "tracked_users": tracked_users,
        "duel": get_duel_data()
    }
    
    with open(saved_data, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

@tasks.loop(seconds=time_debug)
async def ping_jailed_users():
    ping_users = []
    for user_id, user in tracked_users.items():
        if user['ping'] and not user['sent_image']:
            ping_users.append(user_id)

    print(ping_users)
    logger.debug(f"Users to ping: {ping_users}")
    if ping_users:
        print("Pinging jailed users...")
        logger.info("Pinging jailed users...")
        message = "🚨 **Final Warning!** 🚨\n"

        for user_id, user in tracked_users.items():
            if user['ping'] and not user['sent_image']:
                member = bot.get_user(user_id)
                if member:
                    message += f"{member.mention} "

        message += "\n**You have 2 hours before you're shipped to the graveyard!!** 🪦"
        
        channel = bot.get_channel(allowed_channels[0])
        if channel:
            await channel.send(message)

@tasks.loop(seconds=60)  # Check every minute for debug mode
async def cleanup_duels():
    """Clean up expired duels every minute in debug mode"""
    try:
        cleaned = await cleanup_expired_duels(bot, allowed_channels)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired duels")
    except Exception as e:
        logger.error(f"Error cleaning up duels: {e}")
            
# @tasks.loop(hours=24)
# async def ping_jailed_users():
#     # Exactly at 10 pm
#     if datetime.now().hour == 22 and datetime.now().minute == 0:
#         print("Pinging jailed users...")
#         message = ""
#         for user_id, user in tracked_users.items():
#             if user['ping'] and user['sent_image'] == False:
#                 # message += f"@{user['username']} "
#                 member = bot.get_user(user_id)
#                 message += f"{member.mention} "
#         message += "\nYou Have 2 Hours Before Shipping to Graveyard!!! 🪦🪦🪦"
#         channel = bot.get_channel()
#         if channel:
#             await channel.send(message)

bot.run(BOT_TOKEN)
