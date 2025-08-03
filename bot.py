import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import json
import os
from dotenv import load_dotenv  

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
allowed_channels = [1281049819342831636]

tracked_users = {}
current_day = 1
season = 7
season_theme = "The Great Escape"
season_days = 5
saved_data = "backup.json"

def load_data():
    global current_day, season, tracked_users
    try:
        with open(saved_data, "r") as f:
            data = json.load(f)
            current_day = data.get("current_day", 1)
            season = data.get("season", 1)
            tracked_users = data.get("tracked_users", {})
            print(f"✅ Data loaded successfully! (Day {current_day}, Season {season})")
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ No save file found. Starting fresh.")
        current_day = 1
        season = 7
        tracked_users = {}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        load_data()
        synced = await bot.tree.sync()  # Sync slash commands
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    send_daily_art_message.start()
    save_data_task.start()
    ping_jailed_users.start()

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
                await message.channel.send(f"🎨 {message.author.name}, your art has been recorded for today!")

            elif "#buffer" in content_lower:
                user_data['buffer'] = user_data.get('buffer', 0) + 1  # Increase buffer count
                print(f"🛑 {message.author.name} submitted buffer art.")
                await message.channel.send(f"📌 {message.author.name}, your buffer art has been recorded! This will not count for today's submission.")

            else:
                print(f"📸 {message.author.name} uploaded an image but didn't tag it as art.")
                if user_data['ping']:
                    await message.channel.send(f"⚠️ {message.author.name}, please tag your submission with `#daily` if it's an official art entry.")

    # Process other commands
    await bot.process_commands(message)

@bot.tree.command(name="add_channel", description="Add a channel for tracking art submissions.")
@app_commands.describe(channel_id="Enter the channel ID")
async def add_channel(interaction: discord.Interaction, channel_id: int):
    if channel_id not in allowed_channels:
        allowed_channels.append(channel_id)
        await interaction.response.send_message(f"✅ Channel {channel_id} added to allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Channel {channel_id} is already in the allowed list.", ephemeral=True)

@bot.tree.command(name="remove_channel", description="Remove a channel from tracking.")
@app_commands.describe(channel_id="Enter the channel ID")
async def remove_channel(interaction: discord.Interaction, channel_id: int):
    if channel_id in allowed_channels:
        allowed_channels.remove(channel_id)
        await interaction.response.send_message(f"✅ Channel {channel_id} removed from allowed channels!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Channel {channel_id} not found in the allowed list.", ephemeral=True)

@bot.tree.command(name="list_channels", description="List all channels being tracked.")
@app_commands.describe()
async def list_channels(interaction: discord.Interaction):
    if not allowed_channels:
        await interaction.response.send_message("⚠️ No channels are currently being tracked.", ephemeral=True)
    else:
        channels = "\n".join([f"<#{channel_id}>" for channel_id in allowed_channels])
        await interaction.response.send_message(f"**Tracked Channels:**\n{channels}")

@bot.tree.command(name="add_user", description="Add a user to the art tracking system.")
@app_commands.describe(user="Select a user")
async def add_user(interaction: discord.Interaction, user: discord.User):
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
            'ping': False
        }
        await interaction.response.send_message(f"✅ {user.name} added to the tracking list!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {user.name} is already being tracked.", ephemeral=True)

@bot.tree.command(name="remove_user", description="Remove a user from tracking.")
@app_commands.describe(user="Select a user")
async def remove_user(interaction: discord.Interaction, user: discord.User):
    if user.id in tracked_users:
        del tracked_users[user.id]
        await interaction.response.send_message(f"✅ {user.name} removed from tracking!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ User not found in tracking.")

@bot.tree.command(name="list_users", description="List all users being tracked.")
async def list_users(interaction: discord.Interaction):
    if not tracked_users:
        await interaction.response.send_message("⚠️ No users are currently being tracked.", ephemeral=True)
    else:
        users = "\n".join([f"{user['username']} - {user['user_nickname']}" for user in tracked_users.values()])
        await interaction.response.send_message(f"**Tracked Users:**\n{users}")

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
        )
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("❌ User not found in tracking.")

@bot.tree.command(name="edit_user", description="Edit a user's attribute.")
@app_commands.describe(user="Select a user", attribute="Attribute to change", value="New value")
async def edit_user(interaction: discord.Interaction, user: discord.User, attribute: str, value: str):
    if user.id in tracked_users and attribute in tracked_users[user.id]:
        old_value = tracked_users[user.id][attribute]
        try:
            if isinstance(old_value, bool):
                value = value.lower() == 'true'
            elif isinstance(old_value, int):
                value = int(value)

            tracked_users[user.id][attribute] = value
            await interaction.response.send_message(f"✅ {tracked_users[user.id]["user_nickname"]}'s `{attribute}` changed from `{old_value}` to `{value}`")
        except ValueError:
            await interaction.response.send_message("⚠️ Invalid value type.")
    else:
        await interaction.response.send_message("⚠️ Invalid user or attribute.")


@tasks.loop(seconds=30)
async def send_daily_art_message():
    global current_day, season, season_theme, season_days

    users_not_sent = [u for u in tracked_users.values() if not u['sent_image']]
    users_sent = [u for u in tracked_users.values() if u['sent_image']]
    print(season_theme)
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
            await channel.send(message)

        print(f"Day {current_day} has ended!")
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
                        results_message += f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

                    rank = index + 1 
                    grouped_users = [user['user_nickname']]
                prev_user = user 
                print(grouped_users)
            if grouped_users:
                results_message += f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

            results_message += f"\n## **Funny Achievements:**\n"
            max_revival = max(user['revival'] for user in tracked_users.values())
            highest_revival_users = [user['user_nickname'] for user in tracked_users.values() if user['revival'] == max_revival]
            max_buffer = max(user['buffer'] for user in tracked_users.values())
            highest_buffer_users = [user['user_nickname'] for user in tracked_users.values() if user['buffer'] == max_buffer]
            results_message += f"**💾 Most Buffer Art:** {', '.join(highest_buffer_users)} - {max_buffer}\n"
            results_message += f"**😇 Most Revived:** {', '.join(highest_revival_users)} - {max_revival}\n"
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
        


@tasks.loop(seconds=30)
async def save_data_task():
    data = {
        "current_day": current_day,
        "season": season,
        "tracked_users": tracked_users
    }
    
    with open(saved_data, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

@tasks.loop(seconds=30)
async def ping_jailed_users():
    ping_users = []
    for user_id, user in tracked_users.items():
        if user['ping'] and not user['sent_image']:
            ping_users.append(user_id)

    print(ping_users)
    if ping_users:
        print("Pinging jailed users...")
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

# replace with bot token
bot.run(BOT_TOKEN)
