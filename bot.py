import discord
from discord.ext import commands, tasks
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

tracked_users = {}
current_day = 1

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    send_daily_art_message.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the message has an image and if the user is being tracked
    if message.attachments and any(attachment.content_type.startswith("image/") for attachment in message.attachments):
        if message.author.id in tracked_users:
            tracked_users[message.author.id]['sent_image'] = True  # Mark as true when an image is sent
            print(f"User {message.author.name} sent an image.")
            await message.channel.send(f"{message.author.name}, you have sent an image today!")

    # Process other commands
    await bot.process_commands(message)

@bot.command()
async def add_user(ctx, user: discord.User):
    print(f"Received command to add user: {user.name} (ID: {user.id})")  # Print when the command is called
    
    if user.id not in tracked_users:
        tracked_users[user.id] = {
            'username': user.name,
            'sent_image': False,
        }
        print(f"User {user.name} has been added to the tracking list.")
        await ctx.send(f"{user.name} has been added to the tracking list!")
    else:
        print(f"User {user.name} is already being tracked.")
        await ctx.send(f"{user.name} is already being tracked.")

@bot.command()
async def remove_user(ctx, user: discord.User):
    print(f"Received command to remove user: {user.name} (ID: {user.id})")
    if user.id in tracked_users:
        del tracked_users[user.id]
        print(f"User {user.name} has been removed from the tracking list.")
        await ctx.send(f"{user.name} has been removed from the tracking list!")

@bot.command()
async def list_users(ctx):
    print(f"Received command to list all users being tracked.")
    if len(tracked_users) == 0:
        print("No users are being tracked.")
        await ctx.send("No users are being tracked.")
    else:
        users = "\n".join([f"{user['username']} " for user_id, user in tracked_users.items()])
        print(f"Users being tracked:\n{users}")
        await ctx.send(f"Users being tracked:\n{users}")



# Task to send the daily message every minute
@tasks.loop(minutes=1)
async def send_daily_art_message():
    global current_day
    print("Sending daily art message...")

    # Message
    users_not_sent = [user['username'] for user_id, user in tracked_users.items() if not user['sent_image']]
    users_sent = [user['username'] for user_id, user in tracked_users.items() if user['sent_image']]

    message = f"Day {current_day} - Daily Art:\n"
    jailling = ""
    for user_id, user in tracked_users.items():
        if user['sent_image']:
            jailling += f"{user['username']}, "
        else:
            jailling += f"|| {user['username']} ||, \n"
    message += jailling

    # Send the message to a specific channel (replace with channel ID integer)
    channel = bot.get_channel()
    if channel:
        await channel.send(message)
    print("Daily art message sent!")
    # Increment the day after 24 hours 
    if datetime.now().hour == 0 and datetime.now().minute == 0:
        current_day += 1
        # Reset all users' `sent_image` status at the beginning of a new day
        for user_id in tracked_users:
            tracked_users[user_id]['sent_image'] = False

# replace with bot token
bot.run('')
